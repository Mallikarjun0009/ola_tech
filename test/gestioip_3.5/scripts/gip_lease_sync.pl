#!/usr/bin/perl

# This script passes changes in the DHCP leases to
# GestioIP

# version 3.5.7 20210525

# usage: gip_lease_sync.pl --help


use warnings;
use strict;

use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
    $dir = $Bin;
    $gipfunc_path = $dir . '/include';
}

use lib "$gipfunc_path";
use Gipfuncs;

use Net::IP;
use Net::IP qw(:PROC);
use Carp;
use Fcntl qw(:flock);
use FindBin qw($Bin);
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use HTTP::Request::Common;
use LWP::UserAgent;
use JSON;
use Data::Dumper;
use Date::Parse;
use Text::CSV;
use Time::Local;
use DBI;

my $verbose = 0;
my $debug = 0;
my $init_gip = 0;

my ($help, $type, $leases_file, $kea_url, $kea_basic_auth, $run_once, $client, $logdir, $gip_job_id, $user, $combined_job, $mail, $smtp_server, $mail_from, $mail_to, $changes_only, $log, $leases_file_old, $ipv4, $ipv6, $tag);
$help=$type=$leases_file=$kea_url=$kea_basic_auth=$run_once=$client=$logdir=$gip_job_id=$user=$combined_job=$mail=$smtp_server=$mail_from=$mail_to=$changes_only=$log=$leases_file_old=$ipv4=$ipv6=$tag="";

GetOptions(
	"help!"=>\$help,
	"init_gip!"=>\$init_gip,
    "ipv4!"=>\$ipv4,
    "ipv6!"=>\$ipv6,
	"kea_url=s"=>\$kea_url,
	"kea_basic_auth!"=>\$kea_basic_auth,

	"leases_file=s"=>\$leases_file,
	"leases_file_old=s"=>\$leases_file_old,
	"type=s"=>\$type,
	"verbose!"=>\$verbose,

	"combined_job!"=>\$combined_job,
    "changes_only!"=>\$changes_only,
    "mail!"=>\$mail,
    "smtp_server=s"=>\$smtp_server,
    "mail_from=s"=>\$mail_from,
    "mail_to=s"=>\$mail_to,
    "help!"=>\$help,
    "run_once!"=>\$run_once,
    "tag=s"=>\$tag,
    "user=s"=>\$user,
    "verbose!"=>\$verbose,
    "x!"=>\$debug,

    "A=s"=>\$client,
    "M=s"=>\$logdir,
    "W=s"=>\$gip_job_id,

) or print_help();

if ( $help ) {
    print_help();
    exit;
}

$dir =~ /^(.*)\/bin/;
$base_dir=$1;
$verbose = 1 if $debug;
$type = "" if ! $type;
$leases_file = "" if ! $leases_file;

# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = get_db_parameter();

if ( ! $pass_gestioip ) {
    print "Database password not found\n";
    exit 1;
}

my $client_count = count_clients();
if ( $client_count == 1 && ! $client ) {
    $client = "DEFAULT";
}
if ( ! $client ) {
    print "Please specify a client name\n";
    exit 1;
}
my $client_id=get_client_id_from_name("$client") || "";
if ( ! $client_id ) {
    print "$client: client not found\n";
    exit 1;
}

my $vars_file=$base_dir . "/etc/vars/vars_update_gestioip_en";

my ($kea_user, $kea_password);
if ( $kea_basic_auth ) {
    ($kea_user, $kea_password) = get_kea_user();
}

my $dyn_dns_updates = 3;
my $file;
if ( $leases_file_old ) {
	$file = $base_dir . "/var/data/$leases_file_old";
} else {
	$file = $base_dir . "/var/data/lease_records_check.txt";
}
#my $exclude_file = $base_dir . "/var/data/exclude_records_check.txt";

my $update_type_audit = "15";
my $event = "";

if ( $gip_job_id) {

    my $job_status = Gipfuncs::check_disabled("$gip_job_id");
    if ( $job_status != 1 ) {
        exit;
    }

    if ( ! $run_once) {
        my $check_start_date = Gipfuncs::check_start_date("$gip_job_id", "5") || "";
        if ( $check_start_date eq "TOO_EARLY" ) {
            exit;
        }
    }

    if ( ! $combined_job) {
        my $job_name = Gipfuncs::get_job_name("$gip_job_id");
        my $audit_type="176";
        my $audit_class="36";

        $event="$job_name ($gip_job_id)";
        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
    }
}

my $exit_message = "";

my $start_time=time();

my $datetime;
my $gip_job_status_id = "";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "gip_leases_sync.pl");

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;

my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime gip_leases_sync.pl $gip_job_id_message\n\n";
print LOG "\n######## Synchronization against DHCP ($datetime) ########\n\n";


my $logfile_name = $log;
$logfile_name =~ s/^(.*\/)//;

my $delete_job_error;
if ( $gip_job_id && ! $combined_job) {
    if ( $run_once ) {
        $delete_job_error = delete_cron_entry("$gip_job_id");
        if ( $delete_job_error ) {
            print LOG "ERROR: Job not deleted from crontab: $delete_job_error";
        }
    } else {
        my $check_end_date = Gipfuncs::check_end_date("$gip_job_id", "5") || "";
        if ( $check_end_date eq "TOO_LATE" ) {
            $delete_job_error = delete_cron_entry("$gip_job_id");
            if ( $delete_job_error ) {
                $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
                exit_error("ERROR: Job not deleted from crontab: $delete_job_error", "$gip_job_status_id", 4 );
            } else {
                exit;
            }
        }
    }
    # status 2: running
    $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
}


my @mail_to;
if ( $mail && ! $smtp_server ) {
        exit_error("Missing argument --smtp_server", "$gip_job_status_id", 4);
}
if ( $smtp_server ) {
    if ( ! $mail_from ) {
            exit_error("Missing argument --mail_from", "$gip_job_status_id", 4);
    }
    if ( ! $mail_to ) {
            exit_error("Missing argument --mail_to", "$gip_job_status_id", 4);
    }
    @mail_to = split(",",$mail_to);
}





my $count = 0;
my $countu = 0;
my $counti = 0;
my $countd = 0;
my $countu6 = 0;
my $counti6 = 0;
my $countd6 = 0;

my $values_lease_data_hash;

if ( $leases_file ) {
    $leases_file = $base_dir . "/var/data/" . $leases_file;
}

print "Processing $leases_file\n" if $leases_file && $debug;
print LOG "Processing $leases_file\n" if $leases_file && $debug;

if ( $type eq "kea_api" ) {
    $ipv4 = 1 if ! $ipv4 && ! $ipv6;
    exit_error("Only one of the options --ipv4 or --ipv6 allowed", "$gip_job_status_id", 4) if $ipv4 && $ipv6; 
    exit_error("Insert the URL of the Kea API", "$gip_job_status_id", 4) if ! $kea_url; 
    exit_error("Option --kea_url does not support the --leases_file option", "$gip_job_status_id", 4) if $leases_file;
    $values_lease_data_hash = get_lease_data_hash_kea_api();

} elsif ( $type eq "kea_lease_file" ) {
	exit_error("No leases_file specified", "$gip_job_status_id", 4) if ! $leases_file;
    exit_error("Option --keas_lease_file does not allow the option --kea_url", "$gip_job_status_id", 4) if $kea_url;
    $values_lease_data_hash = get_lease_data_hash_kea_file();

} elsif ( $type eq "dhcpd_lease_file" ) {
	exit_error("No leases_file specified", "$gip_job_status_id", 4) if ! $leases_file;
    exit_error("Option --keas_lease_file does not allow the option --kea_url", "$gip_job_status_id", 4) if $kea_url;
    $values_lease_data_hash = get_lease_data_hash_dhcpd_file();

} elsif ( $type eq "ms_lease_file" ) {
    exit_error("Option --keas_lease_file does not allow the option --kea_url", "$gip_job_status_id", 4) if $kea_url;
	exit_error("No leases_file specified", "$gip_job_status_id", 4) if ! $leases_file;
    $values_lease_data_hash = get_lease_data_hash_ms_file();

} elsif ( $type eq "generic_lease_file" ) {
    exit_error("Option --keas_lease_file does not allow the option --kea_url", "$gip_job_status_id", 4) if $kea_url;
	exit_error("No leases_file specified", "$gip_job_status_id", 4) if ! $leases_file;
    $values_lease_data_hash = get_lease_data_hash_generic_file();

} elsif ( ! $type) {
    exit_error("No type specified", "$gip_job_status_id", 4);
} else {
    exit_error("Unsupported type", "$gip_job_status_id", 4);
}

if ( ! %$values_lease_data_hash ) {
    exit_error("Did not received valid lease data", "$gip_job_status_id", 6); # 6 > skipped
}
my %values_lease_data_hash = %$values_lease_data_hash;

#TAGs
my @tag;
my $tag_ref = "";
if ( $tag ) {
    $tag =~ s/\s//g;
    @tag = split(",", $tag);
    $tag_ref = \@tag;
}

my @values_host_redes4 = get_host_redes_no_rootnet("$client_id","v4", $tag_ref);
my $values_host_redes4_count = @values_host_redes4;
print LOG "Number networks IPv4: $values_host_redes4_count\n" if $debug;
my @values_host_redes6 = get_host_redes_no_rootnet("$client_id","v6", $tag_ref);
my $values_host_redes6_count = @values_host_redes6;
print LOG "Number networks IPv6: $values_host_redes6_count\n" if $debug;
my @values_lease_data;
my @values_lease_data_old;

my %values_lease_data_hash_old;
my %values_lease_data_hash_delete;
my @values_lease_data_n = get_lease_data($values_lease_data_hash);
my @custom_columns = get_custom_host_columns("$client_id");
my @redes_usage_array;
my %duplicated_entries_hash;


# Get changed entries
print LOG "reading $file\n";
my $j = 0;
if ( -e $file ) {
    open(FILE,"<$file") or exit_error("Can not open $file: $!", "$gip_job_status_id", 4);
    while (<FILE>) {
        # read check file with old records
        # name ip mac lft
        my ($name, $ip, $mac, $lft);
        $_ =~ /^(.+)\s(.+)\s(.+)\s(.+)\s/;
        $name = $1; # hostname
        $ip = $2;
        $mac = $3;
        $lft = $4;

        if ( ! $name || ! $ip || ! $mac || ! $lft ) {
            next;
        }

#        if ( exists $ignore_records{$content} && $ignore_records{$content}->[1] eq $name ) {
#            # ignore record if it exists in ignore records
#            next;
#        }

        print LOG "Old record: $name - $ip - $mac - $lft\n" if $debug;

        if ( exists $values_lease_data_hash_old{$ip} ) {
            $duplicated_entries_hash{$ip} = 1;
            print LOG "Duplicate record detected: $name - $ip - $mac\n" if $debug;
        }

        push @{$values_lease_data_hash_old{$ip}},"$name","$ip","$mac","$lft";
        $values_lease_data_old[$j] = ["$name","$ip","$mac","$lft"];
        $j++;
    }
    close FILE;
}

my $count_lease_data_old = @values_lease_data_old;
print LOG "Found $count_lease_data_old old records\n" if $verbose;

$j = 0;
my $k = 0;
my $i = 0;
foreach ( @values_lease_data_old ) {
    # find CHANGED and DELETED entries

    # do nothing if init_gip
    last if $init_gip;

    my $hostname = $values_lease_data_old[$j]->[0];
    my $ip = $values_lease_data_old[$j]->[1];
    my $mac = $values_lease_data_old[$j]->[2];
    my $lft = $values_lease_data_old[$j]->[3];

    if ( exists $duplicated_entries_hash{$ip} ) {
		print LOG "IP ignored - duplicated A records: $hostname - $ip - $mac\n" if $debug;
		$j++;
        next;
    }

	if ( ! $hostname || ! $ip || ! $mac || ! $lft ) {
		print LOG "Host ignored - parameter missing: $hostname - $ip - $mac - $lft\n" if $debug;
		$j++;
		next;
	}


    if ( exists $values_lease_data_hash{"$ip"} ) {  # Actual lease data
		my $hostname_new = $values_lease_data_hash{"$ip"}->[1];
		print "comparing hostnames: $hostname - $hostname_new\n" if $debug;
		print LOG "comparing hostnames: $hostname - $hostname_new\n" if $debug;
		if ( $hostname_new ne $hostname ) {
			### IP for hostname has changed
			# hostname for IP has changed

            # Insert or update new entry
			$values_lease_data[$k]->[0] = $hostname_new;
			$values_lease_data[$k]->[1] = $ip;
			$values_lease_data[$k]->[2] = $mac;
			$values_lease_data[$k]->[3] = $lft;
			$k++;

			print LOG "prepare UPDATE: $ip - $hostname -> $hostname_new\n" if $debug;
		}

    } else {
		# old hashkey does not exist in new -> delete
        $values_lease_data_hash_delete{$ip} = $hostname;
        $values_lease_data[$k]->[0] = $hostname;
        $values_lease_data[$k]->[1] = $ip;
        $values_lease_data[$k]->[2] = $mac;
        $values_lease_data[$k]->[3] = $lft;
        $k++;

		print LOG "prepare DELETE: $hostname - $ip\n" if $debug;
    }
	$j++;
}


# Overwrite old file. Write all actual lease data to $file
$j = 0;

print LOG "overwriting $file\n" if $debug;
open(FILE,">$file") or exit_error("Can not open $file for writing: $!", "$gip_job_status_id", 4);
foreach ( @values_lease_data_n ) {

    # do nothing if init_gip
# TEST
#    last if $init_gip;

    my $hostname = $values_lease_data_n[$j]->[0];
    my $ip = $values_lease_data_n[$j]->[1];
    my $mac = $values_lease_data_n[$j]->[2];
    my $lft = $values_lease_data_n[$j]->[3];

    if ( $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/ ) {
        # invalid IP
        $j++;
        next;
    }
    print LOG "Current record: $hostname - $ip - $mac - $lft\n" if $debug;
    print "Current record: $hostname - $ip - $mac - $lft\n" if $debug;

	# find values which are in actual but not in old hash -> add value
    if ( ! exists $values_lease_data_hash_old{$ip} ) {
        $values_lease_data[$k]->[0] = $hostname;
        $values_lease_data[$k]->[1] = $ip;
        $values_lease_data[$k]->[2] = $mac;
        $values_lease_data[$k]->[3] = $lft;
		$k++;
        print LOG "prepare ADD: $hostname - $ip\n" if $debug;
        print "prepare ADD: $hostname - $ip\n" if $debug;
	}

    # Create new check_file
	print FILE $hostname . " " . $ip . " " . $mac . " " . $lft . "\n";

	$j++;
}
close FILE;


# IF INITIALIZE PROCESS WHOLE DATABASE
if ( $init_gip ) {
    @values_lease_data = @values_lease_data_n;
}

$j = 0;

my $neto_old;
my $red_num_old;
my $loc_id_old;
my $ip_version_old;
my %host_hash_old;

# delete duplicated values from @values_lease_data

my %seen;
my @values_lease_data_uniq;
foreach my $val ( @values_lease_data ) {
    my $helper = join("%%%%", @$val);
    print LOG "Duplicated entry deleted: @$val\n" if exists $seen{$helper} && $debug;
    $seen{$helper} = 1;
}

my $l=0;
foreach my $key (keys %seen) {
    my @arr = split("%%%%", $key);
    $values_lease_data_uniq[$l] = \@arr;
    $l++;
}
@values_lease_data = @values_lease_data_uniq;
my $count_lease_data = @values_lease_data;
print LOG "Found $count_lease_data new records\n" if $verbose;

foreach ( @values_lease_data ) {
    my $hostname = $values_lease_data[$j]->[0];
    my $ip = $values_lease_data[$j]->[1];
    my $mac = $values_lease_data[$j]->[2];

    my $ip_version = "v4";
    if ( $ip !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $ip_version = "v6";
    }

    print LOG "Processing: \"$hostname - $ip - $mac\" - $j\n" if $debug;
    print "Processing: \"$hostname - $ip - $mac\" - $j\n" if $debug;

	$j++;

	# check if IP is from same network as the IP before - to find network for IP
	my $ipo = new Net::IP ($ip);
	my $ipo_int = $ipo->intip();
	my $mydatetime = time();
	if ( $neto_old ) {
		if ( $ipo->overlaps($neto_old) ) {
            print LOG "Found net_old with overlap: $neto_old\n" if $debug;
			if ( $host_hash_old{$ipo_int} ) {
				my $host_id = $host_hash_old{$ipo_int}[1] || "";
				my $hostname_check = $host_hash_old{$ipo_int}[0] || "";
                my $ut = $host_hash_old{$ipo_int}[4] || "-1";
                my $red_num_usage = $host_hash_old{$ipo_int}[5] || "";

                print LOG "$host_id - $hostname_check\n" if $debug;

                # Delete host if it exits in host_hash and if is in %values_lease_data_hash_delete
                if ( exists $values_lease_data_hash_delete{$ip} && $values_lease_data_hash_delete{$ip} eq $hostname ) {
                    print LOG "DELETE (1): $ip - $hostname_check - $ut\n" if $verbose;
                    if ( $ut ne 1 ) {
                        # update type not "man"
                        delete_or_clear("$client_id", "$ip", \%host_hash_old, "$ip_version_old");

						my $audit_type="14";
						my $audit_class="1";
						$event = "$ip - $hostname_check";
						insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                        push @redes_usage_array, $red_num_usage;
                    }
                    next;
                } elsif ( exists $values_lease_data_hash_delete{$ip} ) {
                # TEST TEST TEST
                    print LOG "Not deleted - hostname and hostname-old differ: $values_lease_data_hash_delete{$ip} - $hostname\n" if $debug;
                    next;
                }

                if ( $hostname ne $hostname_check ) {
                    if ( $ut ne 1 ) {
                        update_hostname("$client_id", "$host_id", "$hostname");
                        $countu++;

                        print LOG "UPDATE (1): $ip - $host_id\n" if $verbose;
						
						my $audit_type="1";
						my $audit_class="1";
						$event = "$ip - $hostname_check > $hostname";
						insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
                    } else {
                        print LOG "update type man - ignored: $ip - $host_id\n" if $debug;
                    }
                    next;
                }
			} else {
				insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id_old, "", "", "", "2", "$mydatetime", "$red_num_old", "-1", "$ip_version_old", "$dyn_dns_updates");
				$counti++;
				print LOG "INSERT (1): $ip\n" if $verbose;
						
				my $audit_type="15";
				my $audit_class="1";
				$event = "$ip - $hostname";
				insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                push @redes_usage_array, $red_num_old;
                next;
			}
		} else {
            print LOG "Found net_old but no overlap: $neto_old\n" if $debug;
        }
	}

    if ( $ip_version eq "v4" ) {
        if ( ! $hostname || ! $ip ) {
            print LOG "Missing hostname or ip: $hostname - $ip\n" if $debug;
            next;
        }

        my $k = 0;
        foreach ( @values_host_redes4 ) {

            if ( ! $values_host_redes4[$k]->[0] || $values_host_redes4[$k]->[5] == 1 ) {
                my $igno_net_ip = $values_host_redes4[$k]->[0] || "";
                print LOG "No IP or rootnet: $igno_net_ip\n" if $debug;
                print "No IP or rootnet: $igno_net_ip\n" if $debug;
                $k++;
                next;
            }

            my $n = $values_host_redes4[$k]->[0];
            my $bm = $values_host_redes4[$k]->[1];
            my $red_num = $values_host_redes4[$k]->[2];
            my $loc_id = $values_host_redes4[$k]->[3];

            $n =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $second_host_red_oct=$2;
            my $third_host_red_oct=$3;
            $ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $second_host_oct=$2;
            my $third_host_oct=$3;
            if (  $bm >= 24 && $third_host_red_oct != $third_host_oct ) {
                $count++;
                $k++;
                next;
            } elsif (  $bm >= 16 && $second_host_red_oct != $second_host_oct ) {
                $count++;
                $k++;
                next;
            }

            my $net = "$n/$bm";
            my $neto = new Net::IP ($net);

            if ( $ipo->overlaps($neto) ) {
                print "Found network for host: $hostname - $net\n" if $debug;
                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");
                print LOG "Found network for host: $hostname - $net\n" if $debug;

                if ( exists $host_hash{$ipo_int} ) {
                    my $hn = $host_hash{$ipo_int}[0] || "";
                    my $hip = $host_hash{$ipo_int}[2] || "";
                    print LOG "Found host: $hn - $hip - $net\n" if $debug;
                    print "Found host: $hn - $ip - $net\n" if $debug;
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;

                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    # Delete host if it exits in host_hash and if is in %values_lease_data_hash_delete
                    if ( exists $values_lease_data_hash_delete{$ip} && $values_lease_data_hash_delete{$ip} eq $hostname ) {
                        print LOG "DELETE (2): $ip - $hn\n" if $verbose;
                        if ( $ut ne 1 ) {
                            # update type not "man"
                            delete_or_clear("$client_id", "$ip", \%host_hash, "$ip_version");

							my $audit_type="14";
							my $audit_class="1";
							$event = "$ip - $hn - $ut";
							insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                            push @redes_usage_array, $red_num_usage;
                        }
                        last;
                    } elsif ( exists $values_lease_data_hash_delete{$ip} ) {
                        print LOG "Not deleted - hostname and hostname-old differ: $values_lease_data_hash_delete{$ip} - $hostname\n" if $debug;
                        print "Not deleted - hostname and hostname-old differ: $values_lease_data_hash_delete{$ip} - $hostname\n" if $debug;
                        last;
                    }

                    if ( $ut eq 1 ) {
                        # update type "man"
                        print LOG "UPDATE: update type: man - ignored - $n/$bm - $ip - $host_id - $ut\n" if $debug;
                    } else {
						if ( $hn eq $hostname ) {
							print LOG "Hostname has not changed $ip - $hostname - ignored\n" if $verbose;
						} else {
							update_hostname("$client_id", "$host_id", "$hostname");
							$countu++;
							
							print LOG "UPDATE (2): $n/$bm - $ip - $host_id\n" if $verbose;

							my $audit_type="1";
							my $audit_class="1";
							$event = "$ip - $hn > $hostname";
							insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
						}
                    }
                } else {
                    insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates");
                    $counti++;
						
                    print LOG "INSERT (2): $n/$bm - $ip \n" if $verbose;
					my $audit_type="15";
					my $audit_class="1";
					$event = "$ip - $hostname";
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                    push @redes_usage_array, $red_num;
                }

				$neto_old = $neto;
				$red_num_old = $red_num;
				$ip_version_old = $ip_version;
				$loc_id_old = $loc_id;
				%host_hash_old = %host_hash;

                $count++;
                last;
            }

            $k++;
            $count++;
        }
    } elsif ( $ip_version eq "v6" ) {

        if ( ! $hostname || ! $mac || ! $ip ) {
            next;
        }
        my $ip_version = "v6";

        my $k = 0;
        foreach ( @values_host_redes6 ) {

            if ( ! $values_host_redes6[$k]->[0] || $values_host_redes6[$k]->[5] == 1 ) {
                $k++;
                next;
            }

            my $n = $values_host_redes6[$k]->[0];
            my $bm = $values_host_redes6[$k]->[1];
            my $red_num = $values_host_redes6[$k]->[2];
            my $loc_id = $values_host_redes6[$k]->[3];

            print LOG "Processing: $hostname\n" if $debug;

			my $n_exp = ip_expand_address ($n, 6);
			my $content_exp = ip_expand_address ($ip, 6);

            print LOG "IP expanded: $n_exp - $content_exp\n" if $debug;

            $n_exp =~ /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np=$1;
            $content_exp = /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np_host=$1;
            if ( $bm == 64 && $np ne $np_host ) {
                $count++;
                $k++;
                next;
			}

            my $net = "$n/$bm";
            my $neto = new Net::IP ($net);

            if ( $ipo->overlaps($neto) ) {
                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");

                if ( exists $host_hash{$ipo_int} ) {
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;
                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    my $hn = $host_hash{$ipo_int}[0] || "";
                    my $hip = $host_hash{$ipo_int}[2] || "";
                    print LOG "Found host: $hn - $hip - $net\n" if $debug;
                    print "Found host: $hn - $ip - $net\n" if $debug;
                    last if ! $host_id;

                    # Delete host if it exits in host_hash and if is in %values_lease_data_hash_delete
                    if ( exists $values_lease_data_hash_delete{$ip} && $values_lease_data_hash_delete{$ip} eq $hostname ) {
                        print LOG "DELETE (3): $ip - $hn - $ut\n" if $verbose;
                        if ( $ut ne 1 ) {
                            # update type not "man"
                            delete_or_clear("$client_id", "$ip", \%host_hash, "$ip_version");

							my $audit_type="14";
							my $audit_class="1";
							$event = "$ip - $hn - $ut";
							insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                            push @redes_usage_array, $red_num_usage;
                        }
                        last;
                    } elsif ( exists $values_lease_data_hash_delete{$ip} ) {
                        print LOG "Not deleted - hostname and hostname-old differ: $values_lease_data_hash_delete{$ip} - $hostname\n" if $debug;
                        last;
                    }

                    if ( $host_id ) {
                        if ( $ut ne 1 ) {
							if ( $hn eq $hostname ) {
								print LOG "Hostname has not changed $ip - $hostname - ignored\n" if $verbose;
							} else {
								update_hostname("$client_id", "$host_id", "$hostname");
								$countu++;

								print LOG "UPDATE (3): $n/$bm - $ip - $host_id\n" if $verbose;

								my $audit_type="1";
								my $audit_class="1";
								$event = "$ip - $hn > $hostname";
								insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
							}
                        } else {
                            print LOG "UPDATE: update type: man - ignored - $n/$bm - $ip - $host_id - $ut\n" if $debug;
                        }
                    }
                } else {
                    insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates");
                    $counti++;
                    print LOG "INSERT (3): $n/$bm - $ip \n" if $debug;
						
					my $audit_type="15";
					my $audit_class="1";
					$event = "$ip - $hostname";
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

                    push @redes_usage_array, $red_num;
                }

                $neto_old = $neto;
                $red_num_old = $red_num;
                $ip_version_old = $ip_version;
                $loc_id_old = $loc_id;
                %host_hash_old = %host_hash;

                $count++;
                last;
            }

            $k++;
            $count++;
		}

    }
}

# update net usage
%seen = ();
my $item;
my @uniq;
foreach $item(@redes_usage_array) {
	next if ! $item;
	push(@uniq, $item) unless $seen{$item}++;
}
@redes_usage_array = @uniq;

foreach my $rn ( @redes_usage_array) {
		print LOG "updating net usage cc\n" if $verbose;
        update_net_usage_cc_column("$client_id", "", "$rn","","no_rootnet");
}

print "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;
print LOG "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;

close LOG;

Gipfuncs::send_mail (
    debug       =>  "$debug",
    mail_from   =>  $mail_from,
    mail_to     =>  \@mail_to,
    subject     => "result $type",
    smtp_server => "$smtp_server",
    smtp_message    => "",
    log         =>  "$log",
    gip_job_status_id   =>  "$gip_job_status_id",
    changes_only   =>  "$changes_only",
) if $mail;

my $end_time=time();

if ( $gip_job_id && ! $combined_job ) {
    update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
}

print "Job successfully finished\n";
exit 0;







###################
## Subroutines
###################

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}

sub get_host_redes_no_rootnet {
    my ( $client_id, $ip_version, $tag ) = @_;
    my @host_redes;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qip_version = $dbh->quote( $ip_version );

	my $tag_expr = "";

	if ( $tag ) {
		my %tags = get_tag_hash("$client_id", "name");
		if ( %tags ) {
			$tag_expr = " AND red_num IN ( SELECT net_id from tag_entries_network WHERE (";
			foreach my $item ( @${tag} ) {
				if ( ! defined $tags{$item}->[0] ) {
					$exit_message = "$item: Tag NOT FOUND - exiting";
					exit_error("$exit_message", "$gip_job_status_id", 4);
				}
				$tag_expr .= " tag_id=\"$tags{$item}->[0]\" OR";
			}
			$tag_expr =~ s/OR$//;
			$tag_expr .= " ))";
		}
	}

    my $sth = $dbh->prepare("SELECT n.red, n.BM, n.red_num, n.loc, n.ip_version, n.rootnet FROM net n WHERE n.rootnet = '0' AND n.ip_version=$qip_version AND n.client_id=$qclient_id $tag_expr")
        or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @host_redes, [ @$ip_ref ];
    }
    $dbh->disconnect;
    return @host_redes;
}


sub get_lease_data_hash_kea_api {

	my %seen;
	my $now = time();

	my $json_result;
	my %result_hash = ();

    my $dhcp_ip_version = "dhcp4";
    $dhcp_ip_version = "dhcp6" if $ipv6;
	my $json = '{ "command": "lease4-get-all", "service": [ "dhcp4" ] }';

	my $URL = $kea_url;
	my $ua = new LWP::UserAgent;
	$ua->agent("GipKeaClient/0.1");
	$ua->timeout(20);
	my $request = POST $URL,
					Content_Type    => [ 'application/json' ],
					Content         => "$json";

	if ( $kea_user ) {
		$request->authorization_basic($kea_user, $kea_password);
	}

	my $res = $ua->request($request);

	if ($res->is_success) {
		$json_result = $res->content;
		my $text = decode_json($json_result);

		#print  Dumper($text);

		my $arr = $text->[0]{arguments}->{leases};

		foreach my $lv ( @$arr ) {
            my $hostname = $lv->{hostname};
            my $ip = $lv->{'ip-address'};
            my $mac = $lv->{'hw-address'};
            my $lft = $lv->{'valid-lft'};
            my $cltt = $lv->{'cltt'};

			next if ! $hostname;
            next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;

			my $valid_to = $cltt + $lft;
            
			# ignore expired_entries
			if ($valid_to < $now) {
				print LOG "expired: $ip, $hostname, $mac, $valid_to\n" if $debug; 
				next;
			}

			$seen{$ip}=0 if ! $seen{$ip};
			next if $seen{$ip} > $valid_to;
			$seen{$ip}=$valid_to;

            push @{$result_hash{$ip}},"$ip","$hostname","$mac","$valid_to";
        }
		return \%result_hash;

	} else {
        print "CAN NOT CONNECT: " . $res->status_line . "\n";

		return;
	}
}

sub get_lease_data_hash_kea_file {

	my %result_hash;
	my %seen;
	my $now = time;

	# Read/parse CSV
	my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1 });
	open my $fh, "<:encoding(utf8)", "$leases_file" or exit_error("Can not open leases file $leases_file: $!", "$gip_job_status_id", 4);
	while (my $row = $csv->getline ($fh)) {
		my $hostname = $row->[8] || "";
		my $ip = $row->[0] || "";
		my $mac = $row->[1] || "";
		my $valid_to = $row->[4] || 0;


		next if ! $hostname;
        next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;
        
		# ignore expired_entries
		if ($valid_to < $now) {
			print LOG "expired: $ip, $hostname, $mac, $valid_to\n" if $debug; 
			next;
		}

		$seen{$ip}=0 if ! $seen{$ip};
		next if $seen{$ip} > $valid_to;
		$seen{$ip}=$valid_to;

		push @{$result_hash{$ip}},"$ip","$hostname","$mac","$valid_to";
	}
	close $fh;

	return \%result_hash;
}

sub get_lease_data_hash_dhcpd_file {

	my $now = time;
	my %seen;
    my %result_hash;

	open(L, $leases_file) or exit_error("Can not open leases file $leases_file: $!", "$gip_job_status_id", 4);
	local $/ = undef;
	my @records = split /^lease\s+([\d\.]+)\s*\{/m, <L>;
	shift @records; # remove stuff before first "lease" block

	## process 2 array elements at a time: ip and data
	foreach my $i (0 .. $#records) {
		next if $i % 2;
		my $ip;
		($ip, $_) = @records[$i, $i+1];

		s/^\n+//;
		s/[\s\}]+$//;

        next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;

		my ($s) = /^\s* starts \s+ \d+ \s+ (.*?);/xm;
		my ($e) = /^\s* ends   \s+ \d+ \s+ (.*?);/xm;

		my $start = str2time($s);
		my $valid_to   = str2time($e);
		$valid_to = 0 if ! $valid_to;

		my %h;

		foreach my $rx ('binding', 'hardware', 'client-hostname') {
			my ($val) = /^\s*$rx.*?(\S+);/sm;
			$h{$rx} = $val;
		}


		my $hostname = $h{'client-hostname'};
		my $mac = $h{'hardware'};

		next if ! $ip || ! $hostname;
		
		# ignore expired_entries
		if ($valid_to < $now) {
			print LOG "expired: $ip, $hostname, $mac, $valid_to\n" if $debug; 
			print "expired: $ip, $hostname, $mac, $valid_to\n" if $debug; 
			next;
		}

		$seen{$ip}=0 if ! $seen{$ip};
		next if $seen{$ip} > $valid_to;
		$seen{$ip}=$valid_to;

		push @{$result_hash{$ip}},"$ip","$hostname","$mac","$valid_to";

	}

	return \%result_hash;
}

sub get_lease_data_hash_ms_file {

#    my $lease_file = "leases_microsoft_dhcp.csv";
    my %result_hash;
    my %seen;
	my $now = time;

    # Read/parse CSV
    my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1 });
    open my $fh, "<:encoding(utf8)", "$leases_file" or exit_error("Can not open leases file $leases_file: $!", "$gip_job_status_id", 4);
    while (my $row = $csv->getline ($fh)) {
        my $hostname = $row->[8];
        my $ip = $row->[0];
        my $mac = $row->[3];
        my $valid_to_date = $row->[9]; # 10/31/2020 3:22:23 PM"

        my $valid_to;
        if ( $valid_to_date =~ /(\d{1,2})\/(\d{1,2})\/(\d{1,4}) (\d{1,2}):(\d{1,2}):(\d{1,2})/ ) {
            $valid_to_date =~ /(\d{1,2})\/(\d{1,2})\/(\d{1,4}) (\d{1,2}):(\d{1,2}):(\d{1,2})/;
            my $sec = $6;
            my $min = $5;
            my $hours = $4;
            my $day = $2;
            my $month = $1;
            my $year = $2;

            $valid_to = timelocal($sec,$min,$hours,$day,$month-1,$year);
        } else {
            $valid_to = 0;
        }

		next if ! $hostname;
        next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;
		
		# ignore expired_entries
		if ($valid_to < $now) {
			print LOG "expired: $ip, $hostname, $mac, $valid_to\n" if $debug; 
			next;
		}

        $seen{$ip}=0 if ! $seen{$ip};
        next if $seen{$ip} > $valid_to;
        $seen{$ip}=$valid_to;

        push @{$result_hash{$ip}},"$ip","$hostname","$mac","$valid_to";
    }
    close $fh;

    return \%result_hash;

}

sub get_lease_data_hash_generic_file {

	my %result_hash;
	my %seen;
	my $now = time;

	# Read/parse CSV
	my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1 });
	open my $fh, "<:encoding(utf8)", "$leases_file" or exit_error("Can not open leases file $leases_file: $!", "$gip_job_status_id", 4);
	while (my $row = $csv->getline ($fh)) {
		my $ip = $row->[0] || "";
		my $hostname = $row->[1] || "";
		my $mac = $row->[2] || "";
		my $valid_to = $row->[3] || 0;


		next if ! $hostname;
        next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;
        if ( $valid_to !~ /^\d+$/ ) {
			print LOG "invalid expire date" if $debug;
            next;
        }
        
		# ignore expired_entries
		if ($valid_to < $now) {
			print LOG "expired: $ip, $hostname, $mac, $valid_to - $now\n" if $debug; 
			next;
		}

		$seen{$ip}=0 if ! $seen{$ip};
		next if $seen{$ip} > $valid_to;
		$seen{$ip}=$valid_to;

		push @{$result_hash{$ip}},"$ip","$hostname","$mac","$valid_to";
	}
	close $fh;

	return \%result_hash;
}

sub get_lease_data {

	my ( $hash ) = @_;

    my @values;
    foreach my $key ( keys %$hash ) {
        my $hostname = $hash->{$key}[0]; 
        my $ip = $hash->{$key}[1]; 
        my $mac = $hash->{$key}[2]; 
        my $lft = $hash->{$key}[3]; 
		my @row = ( "$ip","$hostname","$mac","$lft" );
        push @values,[@row]; 
    }

    return @values;
}


sub get_host_hash {
    my ( $client_id, $red_num, $ip_version ) = @_;

	my %host_hash;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qred_num = $dbh->quote( $red_num );

    my $sth = $dbh->prepare("SELECT ip, INET_NTOA(ip), hostname, id, range_id, update_type, red_num FROM host WHERE red_num=$qred_num AND client_id=$qclient_id")
        or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $ip_int = $ip_ref->{'ip'};
        my $ip = "";
        $ip = $ip_ref->{'INET_NTOA(ip)'} if $ip_version eq "v4";
        my $ip_version = $ip_ref->{'ip_version'};
        my $hostname = $ip_ref->{'hostname'} || "";
        my $id = $ip_ref->{'id'};
        my $range_id = $ip_ref->{'range_id'};
        my $update_type = $ip_ref->{'update_type'};
        my $red_num = $ip_ref->{'red_num'};

	    push @{$host_hash{$ip_int}},"$hostname","$id","$ip","$range_id","$update_type","$red_num";
	}

    $dbh->disconnect;
    return %host_hash;

}

sub insert_ip_mod {
    my ( $client_id, $ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $dyn_dns_updates ) = @_;

    my $dbh = mysql_connection();
    my $sth;
    $loc="-1" if ! $loc;
    $cat="-1" if ! $cat;
    my $qhostname = $dbh->quote( $hostname );
    my $qhost_descr = $dbh->quote( $host_descr );
    my $qloc = $dbh->quote( $loc );
    my $qint_admin = $dbh->quote( $int_admin );
    my $qcat = $dbh->quote( $cat );
    my $qcomentario = $dbh->quote( $comentario );
    my $qupdate_type = $dbh->quote( $update_type );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qip_int = $dbh->quote( $ip_int );
    my $qred_num = $dbh->quote( $red_num );
    $alive = "-1" if ! defined($alive);
    my $qclient_id = $dbh->quote( $client_id );
    my $qdyn_dns_updates = $dbh->quote( $dyn_dns_updates );
    my $qip_version = $dbh->quote( $ip_version );
    if ( $alive != "-1" ) {
        my $qalive = $dbh->quote( $alive );
        my $qlast_response = $dbh->quote( time() );
        $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qip_version,$qclient_id,$qdyn_dns_updates)"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qip_version,$qclient_id,$qdyn_dns_updates)"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}


sub update_hostname {
    my ( $client_id, $id, $hostname ) = @_;

    print LOG "UPDATE HOSTNAME: $hostname - $id\n" if $verbose;

    my $dbh = mysql_connection();
    my $sth;
    my $qhostname = $dbh->quote( $hostname );
    my $qid = $dbh->quote( $id );
    my $qclient_id = $dbh->quote( $client_id );

    $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname WHERE id=$qid AND client_id=$qclient_id"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}

sub delete_ip {
    my ( $client_id, $first_ip_int, $last_ip_int ) = @_;

    my $dbh = mysql_connection();
    my $qfirst_ip_int = $dbh->quote( $first_ip_int );
    my $qlast_ip_int = $dbh->quote( $last_ip_int );
    my $qclient_id = $dbh->quote( $client_id );

    my $match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";

    my $sth = $dbh->prepare("DELETE FROM host WHERE $match AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}

sub clear_ip {
    my ( $client_id, $first_ip_int, $last_ip_int ) = @_;

    my $dbh = mysql_connection();
    my $qfirst_ip_int = $dbh->quote( $first_ip_int );
    my $qlast_ip_int = $dbh->quote( $last_ip_int );
    my $qclient_id = $dbh->quote( $client_id );

    my $match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";

    my $sth = $dbh->prepare("UPDATE host SET hostname='', host_descr='', int_admin='n', alive='-1', last_response=NULL WHERE $match AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}

sub get_client_id_from_name {
    my ( $name ) = @_;
    my $id;
    my $dbh = mysql_connection();
    my $qname = $dbh->quote( $name );

    my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qname
                    ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $id;
}

sub exit_error {
    my ( $message, $gip_job_status_id, $status, $exit_signal ) = @_;

    $exit_signal = "1" if ! $exit_signal;
    $exit_signal = "0" if $exit_signal eq "OK";

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;
    close LOG if fileno LOG;

    if ( $gip_job_status_id && ! $combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning, 6 skipped

        my $time=time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");

		Gipfuncs::send_mail (
			debug       =>  "$debug",
			mail_from   =>  $mail_from,
			mail_to     =>  \@mail_to,
			subject     => "result $type",
			smtp_server => "$smtp_server",
			smtp_message    => "",
			log         =>  "$log",
			gip_job_status_id   =>  "$gip_job_status_id",
			changes_only   =>  "$changes_only",
		) if $mail;
    }

    exit $exit_signal;
}


sub delete_or_clear {
    my ( $client_id, $content, $host_hash, $ip_version ) = @_;

	my $ipo = new Net::IP ($content);
	my $ipo_int = $ipo->intip();
    $content = ip_compress_address ($content, 6) if $ip_version eq "v6";
	if ( exists $host_hash->{$ipo_int} ) {
		my $range_id = $host_hash->{$ipo_int}[3];
		my $host_id = $host_hash->{$ipo_int}[1];
	
		# Delete host
		if ( $range_id != -1 ) {
			# reserved range -> update
			clear_ip("$client_id","$ipo_int","$ipo_int");
		} else {
			# delete
			delete_ip("$client_id","$ipo_int","$ipo_int");
			
		}
		$countd++;

		my $linked_cc_id = get_custom_host_column_id_from_name_client("$client_id","linked IP") || "";
		if ( $linked_cc_id ) {
			# delete linked IP entries if exist

			my %cc_value=get_custom_host_columns_from_net_id_hash("$client_id","$host_id") if $host_id;
			my $audit_entry_cc="";

			my $cm_config_host=0;
			if ( $custom_columns[0] ) {

				my $n=0;
				foreach my $cc_ele(@custom_columns) {
					my $cc_name = $custom_columns[$n]->[0];
					my $pc_id = $custom_columns[$n]->[3];
					my $cc_id = $custom_columns[$n]->[1];
					my $cc_entry = $cc_value{$cc_id}[1] || "";

					$cm_config_host=1;

					if ( $cc_id == $linked_cc_id ) {
						my $linked_ips=$cc_entry;
						my @linked_ips=split(",",$linked_ips);
						foreach my $linked_ip_delete(@linked_ips){
							delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$content");
						}
					}

					if ( $cc_entry ) {
						if ( $audit_entry_cc ) {
							$audit_entry_cc = $audit_entry_cc . "," . $cc_entry;
						} else {
							$audit_entry_cc = $cc_entry;
						}
					}
					$n++;
				}
			}
		}

		delete_custom_host_column_entry("$client_id", "$host_id");

	} else {
		print LOG "HOST NOT FOUND - DO NOT DELETE NOTHING: $content - $ipo_int\n" if $debug > 0;
	} 
}

sub delete_custom_host_column_entry {
    my ( $client_id, $host_id ) = @_;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND client_id = $qclient_id"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_host_column_id_from_name_client {
    my ( $client_id, $column_name ) = @_;
    my $cc_id;
    my $dbh = mysql_connection();
    my $qcolumn_name = $dbh->quote( $column_name );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcolumn_name AND ( client_id = $qclient_id OR client_id = '9999' )
                    ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $cc_id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $cc_id;
}

sub delete_linked_ip {
    my ( $client_id,$ip_version,$linked_ip_old,$ip,$host_id_linked ) = @_;

    my $ip_version_ip_old;
    if ( $linked_ip_old =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $ip_version_ip_old="v4";
    } else {
        $ip_version_ip_old="v6";
    }

    my $cc_name="linked IP";
    my $cc_id="";
    my $pc_id="";
    $host_id_linked="" if ! $host_id_linked;
    if ( ! $host_id_linked ) {
        my $ip_int_linked=ip_to_int("$client_id","$linked_ip_old","$ip_version_ip_old") || "";
        $host_id_linked=get_host_id_from_ip_int("$client_id","$ip_int_linked") || "";
    }
    return if ! $host_id_linked;
    my %custom_host_column_values=get_custom_host_columns_from_net_id_hash("$client_id","$host_id_linked");
    while ( my ($key, @value) = each(%custom_host_column_values) ) {
        if ( $value[0]->[0] eq $cc_name ) {
            $cc_id=$key;
            $pc_id=$value[0]->[2];
            last;
        }
    }

    my $linked_cc_entry=get_custom_host_column_entry("$client_id","$host_id_linked","$cc_name","$pc_id") || "";
    my $linked_ip_comp=$ip;
    $linked_ip_comp = ip_compress_address ($linked_ip_comp, 6) if $ip_version eq "v6";
    $linked_cc_entry =~ s/\b${linked_ip_comp}\b//;
    $linked_cc_entry =~ s/^,//;
    $linked_cc_entry =~ s/,$//;
    $linked_cc_entry =~ s/,,/,/;
    # delete entry from linked host
    if ( $linked_cc_entry ) {
        update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$host_id_linked","$linked_cc_entry");
    } else {
        delete_single_custom_host_column_entry("$client_id","$host_id_linked","$linked_ip_comp","$pc_id");
    }
}

sub get_custom_host_columns_from_net_id_hash {
    my ( $client_id,$host_id ) = @_;

    my %cc_values;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT DISTINCT cce.cc_id,cce.entry,cc.name,cc.column_type_id FROM custom_host_column_entries cce, custom_host_columns cc WHERE  cce.cc_id = cc.id AND host_id = $host_id AND cce.client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $id = $ip_ref->{cc_id};
		my $name = $ip_ref->{name};
		my $entry = $ip_ref->{entry};
		my $column_type_id = $ip_ref->{column_type_id};
		push @{$cc_values{$id}},"$name","$entry","$column_type_id";
	}
	$dbh->disconnect;
	return %cc_values;
}

sub ip_to_int {
    my ($client_id,$ip,$ip_version)=@_;
    my ( $ip_bin, $ip_int);
    if ( $ip_version eq "v4" ) {
        $ip_bin = ip_iptobin ($ip,4);
        $ip_int = new Math::BigInt (ip_bintoint($ip_bin));
    } else {
		my $ip=ip_expand_address ($ip,6);
        $ip_bin = ip_iptobin ($ip,6);
        $ip_int = new Math::BigInt (ip_bintoint($ip_bin));
    }
    return $ip_int;
}

sub get_host_id_from_ip_int {
    my ( $client_id,$ip_int,$red_num ) = @_;
    my $val;
    my $dbh = mysql_connection();
    my $qip_int = $dbh->quote( $ip_int );
    my $qclient_id = $dbh->quote( $client_id );
    my $qred_num = $dbh->quote( $red_num );
    my $red_num_expr="";
    $red_num_expr="AND red_num = $qred_num" if $red_num;
    my $sth = $dbh->prepare("SELECT id FROM host WHERE ip=$qip_int AND client_id=$qclient_id $red_num_expr");
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $val = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $val;
}

sub update_custom_host_column_value_host_modip {
    my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;

    my $dbh = mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qhost_id = $dbh->quote( $host_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id AND cc_id=$qcc_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}

sub delete_single_custom_host_column_entry {
    my ( $client_id, $host_id, $cc_entry_host, $pc_id, $cc_id ) = @_;

    $cc_id="" if ! $cc_id;
    $cc_entry_host = "" if ! $cc_entry_host;

    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qcc_entry_host = $dbh->quote( $cc_entry_host );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qcc_id = $dbh->quote( $cc_id );
    my $qclient_id = $dbh->quote( $client_id );

    my $cc_id_expr="";
    $cc_id_expr="AND cc_id=$qcc_id" if $cc_id;
    my $sth;
    if ( $cc_entry_host ) {
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND entry = $qcc_entry_host AND pc_id = $qpc_id $cc_id_expr") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND pc_id = $qpc_id $cc_id_expr") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_host_column_entry {
    my ( $client_id, $host_id, $cc_name, $pc_id ) = @_;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qcc_name = $dbh->quote( $cc_name );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT cce.cc_id,cce.entry from custom_host_column_entries cce, custom_host_columns cc, predef_host_columns pc WHERE cc.name=$qcc_name AND cce.host_id = $qhost_id AND cce.cc_id = cc.id AND cc.column_type_id= pc.id AND pc.id = $qpc_id AND cce.client_id = $qclient_id
					") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	my $entry = $sth->fetchrow_array;
	$sth->finish();
	$dbh->disconnect;

	return $entry;
}

sub get_custom_host_columns {
    my ( $client_id ) = @_;

    my @values;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $sth;
    $sth = $dbh->prepare("SELECT cc.name,cc.id,cc.client_id,pc.id FROM custom_host_columns cc, predef_host_columns pc WHERE cc.column_type_id = pc.id AND (client_id = $qclient_id OR client_id = '9999') ORDER BY cc.id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $dbh->disconnect;

    return @values;
}

sub print_help {
        print "\nusage: gip_leases_sync.pl [OPTIONS...]\n\n";
		print "-A client                client name\n";
        print "-c, --changes_only       report only changed endries\n";
        print "-d, --debug              debug\n";
        print "-h, --help               help\n";
        print "-i, --init_gip           initalze GestioIP database\n";
        print "-k, --kea_url=URL            URL KEA API. For example: http://kea_dhcp.domain.com:8000\n";
        print "-k, --kea_basic_auth     Use credencials when connect to the Kea API. Store the user/passwordo\n";
        print "                         in /usr/share/gestioip/etc/kea-users\n";
        print "-l, --leases_file        name of the file with the lease information to import\n";

		print "-M logdir                directory where the log file should be stored\n";
        print "--mail                   send result by mail\n";
        print "--mail_from=mail_address mail sender\n";
        print "--mail_to=mail_address   mail recipient\n";
#        print "-r, --run_once           run only once\n";
        print "--smtp_server=server     SMTP server name or IP\n";
        print "-t, --type               import type [kea_api|kea_lease_file|dhcpd_lease_file|ms_lease_file]\n";
		print "-W job_id\n";
        print "-v, --verbose            verbose\n\n";

        exit;
}

sub update_net_usage_cc_column {
    my ($client_id, $ip_version, $red_num, $BM, $no_rootnet) = @_;
    
    my $rootnet = "";
    if ( ! $BM || ! $ip_version || ! $no_rootnet ) {
        my @values_redes=get_red("$client_id","$red_num");
        $BM = "$values_redes[0]->[1]" || "";
        $ip_version = "$values_redes[0]->[7]" || "";
        $rootnet = "$values_redes[0]->[9]" || "";
    }
    
    # no usage value for rootnetworks
    return if $rootnet eq 1;

    my ($ip_total, $ip_ocu, $free) = get_red_usage("$client_id", "$ip_version", "$red_num", "$BM");
    my $cc_id_usage = get_custom_column_id_from_name("$client_id", "usage") || "";
    my $cc_usage_entry = "$ip_total,$ip_ocu,$free" || "";
    update_or_insert_custom_column_value_red("$client_id", "$cc_id_usage", "$red_num", "$cc_usage_entry") if $cc_id_usage && $cc_usage_entry;
}

sub get_red {
    my ( $client_id, $red_num ) = @_;

    my $error;
    my $ip_ref;
    my @values_redes;
    my $dbh = mysql_connection();
    my $qred_num = $dbh->quote( $red_num );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT red, BM, descr, loc, vigilada, comentario, categoria, ip_version, red_num, rootnet, dyn_dns_updates FROM net WHERE red_num=$qred_num AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_redes, [ @$ip_ref ];
    }
    $dbh->disconnect;

    return @values_redes;
}

sub get_red_usage {
    my ( $client_id, $ip_version, $red_num, $BM) = @_;

    if ( ! $BM || ! $ip_version ) {
        my @values_redes=get_red("$client_id","$red_num");
        $BM = "$values_redes[0]->[1]" || "";
        $ip_version = "$values_redes[0]->[7]" || "";
    }

    my %anz_hosts = get_anz_hosts_bm_hash("$client_id","$ip_version");
    my $ip_total=$anz_hosts{$BM};
    $ip_total =~ s/,//g;

    if ( $ip_version eq "v4" ) {
           $ip_total = $ip_total - 2;
           $ip_total = 2 if $BM == 31;
           $ip_total = 1 if $BM == 32;
    }

    my $ip_ocu=count_host_entries("$client_id","$red_num");
    my $free=$ip_total-$ip_ocu;
    my ($free_calc,$percent_free,$ip_total_calc,$percent_ocu,$ocu_color);

    if ( $free == 0 ) {
        $percent_free = '0%';
    } elsif ( $free == $ip_total ) {
        $percent_free = '100%';
    } else {
        $free_calc = $free . ".0";
        $ip_total_calc = $ip_total . ".0";
        $percent_free=100*$free_calc/$ip_total_calc;
        $percent_free =~ /^(\d+\.?\d?).*/;
        $percent_free = $1 . '%';
    }
    if ( $ip_ocu == 0 ) {
        $percent_ocu = '0%';
    } elsif ( $ip_ocu == $ip_total ) {
        $percent_ocu = '100%';
    } else {
        $ip_total_calc = $ip_total . ".0";
        $percent_ocu=100*$ip_ocu/$ip_total_calc;
        if ( $percent_ocu =~ /e/ ) {
            $percent_ocu="0.1"
        } else {
            $percent_ocu =~ /^(\d+\.?\d?).*/;
            $percent_ocu = $1;
        }
        $percent_ocu = $percent_ocu . '%';
    }

    return ($ip_total, $ip_ocu, $free);
}

sub get_anz_hosts_bm_hash {
    my ( $client_id, $ip_version ) = @_;
    my %bm;
    if ( $ip_version eq "v4" ) {
        %bm = (
            8 => '16777216',
            9 => '8388608',
            10 => '4194304',
            11 => '2097152',
            12 => '1048576',
            13 => '524288',
            14 => '262144',
            15 => '131072',
            16 => '65536',
            17 => '32768',
            18 => '16384',
            19 => '8192',
            20 => '4096',
            21 => '2048',
            22 => '1024',
            23 => '512',
            24 => '256',
            25 => '128',
            26 => '64',
            27 => '32',
            28 => '16',
            29 => '8',
            30 => '4',
            31 => '1',
            32 => '1'
        );
    } else {
        %bm = (
#           1 => '9,223,372,036,854,775,808',
#           2 => '4,611,686,018,427,387,904',
#           3 => '2,305,843,009,213,693,952',
#           4 => '1,152,921,504,606,846,976',
#           5 => '576,460,752,303,423,488',
#           6 => '288,230,376,151,711,744',
#           7 => '144,115,188,075,855,872',
            8 => '72,057,594,037,927,936',
            9 => '36,028,797,018,963,968',
            10 => '18,014,398,509,481,984',
            11 => '9,007,199,254,740,992',
            12 => '4,503,599,627,370,496',
            13 => '2,251,799,813,685,248',
            14 => '1,125,899,906,842,624',
            15 => '562,949,953,421,312',
            16 => '281,474,976,710,656',
            17 => '140,737,488,355,328',
            18 => '70,368,744,177,664',
            19 => '35,184,372,088,832',
            20 => '17,592,186,044,416',
            21 => '8,796,093,022,208',
            22 => '4,398,046,511,104',
            23 => '2,199,023,255,552',
            24 => '1,099,511,627,776',
            25 => '549,755,813,888',
            26 => '274,877,906,944',
            27 => '137,438,953,472',
            28 => '68,719,476,736',
            29 => '34,359,738,368',
            30 => '17,179,869,184',
            31 => '8,589,934,592',
            32 => '4,294,967,296',
            33 => '2,147,483,648',
            34 => '1,073,741,824',
            35 => '536,870,912',
            36 => '268,435,456',
            37 => '134,217,728',
            38 => '67,108,864',
            39 => '33,554,432',
            40 => '16,777,216',
            41 => '8,388,608',
            42 => '4,194,304',
            43 => '2,097,152',
            44 => '1,048,576',
            45 => '524,288',
            46 => '262,144',
            47 => '131,072',
            48 => '65,536',
            49 => '32,768',
            50 => '16,384',
            51 => '8,192',
            52 => '4,096',
            53 => '2,048',
            54 => '1,024',
            55 => '512',
            56 => '256',
            57 => '128',
            58 => '64',
            59 => '32',
            60 => '16',
            61 => '8',
            62 => '4',
            63 => '2',
# hosts
            64 => '18,446,744,073,709,551,616',
            65 => '9,223,372,036,854,775,808',
            66 => '4,611,686,018,427,387,904',
            67 => '2,305,843,009,213,693,952',
            68 => '1,152,921,504,606,846,976',
            69 => '576,460,752,303,423,488',
            70 => '288,230,376,151,711,744',
            71 => '144,115,188,075,855,872',
            72 => '72,057,594,037,927,936',
            73 => '36,028,797,018,963,968',
            74 => '18,014,398,509,481,984',
            75 => '9,007,199,254,740,992',
            76 => '4,503,599,627,370,496',
            77 => '2,251,799,813,685,248',
            78 => '1,125,899,906,842,624',
            79 => '562,949,953,421,312',
            80 => '281,474,976,710,656',
            81 => '140,737,488,355,328',
            82 => '70,368,744,177,664',
            83 => '35,184,372,088,832',
            84 => '17,592,186,044,416',
            85 => '8,796,093,022,208',
            86 => '4,398,046,511,104',
            87 => '2,199,023,255,552',
            88 => '1,099,511,627,776',
            89 => '549,755,813,888',
            90 => '274,877,906,944',
            91 => '137,438,953,472',
            92 => '68,719,476,736',
            93 => '34,359,738,368',
            94 => '17,179,869,184',
            95 => '8,589,934,592',
            96 => '4,294,967,296',
            97 => '2,147,483,648',
            98 => '1,073,741,824',
            99 => '536,870,912',
            100 => '268,435,456',
            101 => '134,217,728',
            102 => '67,108,864',
            103 => '33,554,432',
            104 => '16,777,216',
            105 => '8,388,608',
            106 => '4,194,304',
            107 => '2,097,152',
            108 => '1,048,576',
            109 => '524,288',
            110 => '262,144',
            111 => '131,072',
            112 => '65,536',
            113 => '32,768',
            114 => '16,384',
            115 => '8,192',
            116 => '4,096',
            117 => '2,048',
            118 => '1,024',
            119 => '512',
            120 => '256',
            121 => '128',
            122 => '64',
            123 => '32',
            124 => '16',
            125 => '8',
            126 => '4',
            127 => '2',
           128 => '1'
        );
    }
    return %bm;
}

sub update_or_insert_custom_column_value_red {
    my ( $client_id, $cc_id, $net_id, $entry ) = @_;
    my $error;

    my $dbh = mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qnet_id = $dbh->quote( $net_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    my $entry_found = $sth->fetchrow_array;

    if ( $entry_found ) {
        $sth = $dbh->prepare("UPDATE custom_net_column_entries SET entry=$qentry WHERE cc_id=$qcc_id AND net_id=$qnet_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("INSERT INTO custom_net_column_entries (cc_id,net_id,entry,client_id) VALUES ($qcc_id,$qnet_id,$qentry,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_column_id_from_name {
    my ( $client_id, $name ) = @_;
    my $dbh = mysql_connection();
    my $qname = $dbh->quote( $name );
    my $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qname
                    ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $id;
}

sub count_host_entries {
    my ( $client_id, $red_num ) = @_;
    my $count_host_entries;
    my $dbh = mysql_connection();
    my $qred_num = $dbh->quote( $red_num );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT COUNT(*) FROM host WHERE red_num=$qred_num AND hostname != 'NULL' AND hostname != '' AND client_id = $qclient_id");
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $count_host_entries = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $count_host_entries;
}

sub count_clients {
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT count(*) FROM clients
                        ") or die "Mysql ERROR: ". $DBI::errstr;
        $sth->execute() or die "Mysql ERROR: ". $DBI::errstr;
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}


sub get_db_parameter {
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or exit_error("Can not open $priv_file: $!", "$gip_job_status_id", 4);
            while (<OUT>) {
                if ( $_ =~ /^sid=/ ) {
                    $_ =~ /^sid=(.*)$/;
                    $sid_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_host=/ ) {
                    $_ =~ /^bbdd_host=(.*)$/;
                    $bbdd_host_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_port=/ ) {
                    $_ =~ /^bbdd_port=(.*)$/;
                    $bbdd_port_gestioip = $1;
                } elsif ( $_ =~ /^user=/ ) {
                    $_ =~ /^user=(.*)$/;
                    $user_gestioip = $1;
                } elsif ( $_ =~ /^password=/ ) {
                    $_ =~ /^password=(.*)$/;
                    $pass_gestioip = $1;
                }
            }
            close OUT;
            last;
        }
    }

    return ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip);
}


sub delete_cron_entry {
    my ($id) = @_;

    $ENV{PATH} = "";

    my $crontab = "/usr/bin/crontab";

    my $echo = "/bin/echo";

    my $grep = "/bin/grep";

    my $command = $crontab . ' -l | ' . $grep . ' -v \'#ID: ' . $id . '$\' | ' . $crontab . ' -';

    my $output = `$command 2>&1`;
    if ( $output ) {
        return $output;
    }
}

sub insert_audit_auto {
        my ($client_id,$event_class,$event_type,$event,$update_type_audit,$vars_file) = @_;

        my $remote_host = "N/A";

        $user=$ENV{'USER'} if ! $user;
        my $mydatetime=time();
        my $dbh = mysql_connection();
        my $qevent_class = $dbh->quote( $event_class );
        my $qevent_type = $dbh->quote( $event_type );
        my $qevent = $dbh->quote( $event );
        my $quser = $dbh->quote( $user );
        my $qupdate_type_audit = $dbh->quote( $update_type_audit );
        my $qmydatetime = $dbh->quote( $mydatetime );
        my $qremote_host = $dbh->quote( $remote_host );
        my $qclient_id = $dbh->quote( $client_id );

        my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,remote_host,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qremote_host,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
}


sub insert_job_status {
    my ( $gip_job_id, $status, $log_file ) = @_;

    $log_file = "" if ! $log_file;
    $status = 2 if ! $status; # "running"

    my $time = time();

    my $dbh = mysql_connection();

    my $qgip_job_id = $dbh->quote( $gip_job_id );
    my $qstatus = $dbh->quote( $status );
    my $qtime = $dbh->quote( $time );
    my $qlog_file = $dbh->quote( $log_file );

    my $sth = $dbh->prepare("INSERT INTO scheduled_job_status (job_id, status, start_time, log_file) values ($qgip_job_id, $status, $time, $qlog_file)");
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $id = $sth->fetchrow_array;

    $sth->finish();
    $dbh->disconnect;

    return $id;
}

sub update_job_status {
    my ( $gip_job_status_id, $status, $end_time, $exit_message, $log_file ) = @_;

    $status = "" if ! $status;
    $exit_message = "" if ! $exit_message;
    $end_time = "" if ! $end_time;
    $log_file = "" if ! $log_file;

    if ( $delete_job_error ) {
        if ( $status != 4 ) {
            # warning
            $status = 5;
        }
    }

    my $dbh = mysql_connection();

    my $qgip_job_status_id = $dbh->quote( $gip_job_status_id );
    my $qstatus = $dbh->quote( $status );
    my $qend_time = $dbh->quote( $end_time );
    my $qlog_file = $dbh->quote( $log_file );
    my $qexit_message = $dbh->quote( $exit_message );

    if ( ! $status && ! $exit_message && ! $end_time && ! $log_file ) {
        return;
    }

    my $expr = "";
    $expr .= ", status=$qstatus" if $status;
    $expr .= ", exit_message=$qexit_message" if $exit_message;
    $expr .= ", end_time=$qend_time" if $end_time;
    $expr .= ", log_file=$qlog_file" if $log_file;
    $expr =~ s/^,//;

    print "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug;
#   print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug && fileno LOG;
    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}

sub get_kea_user {
    my $user_file = $base_dir . "/etc/kea_user.conf";

    my ( $user, $password);
    open(KEA_CONF,"<$user_file") or exit_error("Can not open $user_file: $!", "", 4);
    while(<KEA_CONF>) {
        if ( $_ =~ /^user/ ) {
            $_ =~ /^user=?(.+)$/;
            $user=$1;
        } elsif ( $_ =~ /^password=/ ) {
            $_ =~ /^password=?(.+)$/;
            $password=$1;
        }
    }

    close KEA_CONF;

    return ($user, $password);
}

sub get_tag_hash {
    my ( $client_id, $key ) = @_;

    my %values;
    my $ip_ref;
    $key = "id" if ! $key;

    my $dbh = mysql_connection();

    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT id, name, description, color, client_id FROM tag WHERE ( client_id = $qclient_id OR client_id = '9999' ) ORDER BY name"
        ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{id};
        my $name = $ip_ref->{name};
        my $description = $ip_ref->{description};
        my $color = $ip_ref->{color};
        my $client_id = $ip_ref->{client_id};
        if ( $key eq "id" ) {
            push @{$values{$id}},"$name","$description","$color","$client_id";
        } elsif ( $key eq "name" ) {
            push @{$values{$name}},"$id","$description","$color","$client_id";
        }
    }
    $sth->finish();
    $dbh->disconnect;

    return %values;
}
