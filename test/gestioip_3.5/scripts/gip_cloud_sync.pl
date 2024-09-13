#!/usr/bin/perl -T

# This script passes changes in the DHCP leases to
# GestioIP

# version 3.5.7 20210424

# usage: gip_cloud_sync.pl --help


use warnings;
use strict;

use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
    $dir = $Bin;
    $dir =~ /^(.*)$/;
    $dir =~ $1;
    $gipfunc_path = $dir . '/include';
    $gipfunc_path =~ /^(.*)$/;
    $gipfunc_path = $1;
}

use lib "$gipfunc_path";
use Gipfuncs;

use Net::IP;
use Net::IP qw(:PROC);
use Carp;
use Fcntl qw(:flock);
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
use Net::DNS;


our $verbose = 0;
our $debug = 0;
my $init_gip = 0;

my ($help, $run_once, $logdir, $gip_job_id, $user, $check_file, $ipv4, $ipv6, $tag, $use_zone_transfer, $use_api, $ignore_dns);
$help=$run_once=$logdir=$gip_job_id=$user=$check_file=$ipv4=$ipv6=$tag=$use_zone_transfer=$use_api=$ignore_dns="";
our $client = "";
our $create_csv = "";
our $ignore_generic_auto = "no";
our $smtp_server = "";
our $mail_from = "";
our $mail_to = "";
our $changes_only = "";
our $log = "";
our $mail = "";
our $type = "";
our $document_root = "";

my $azure_dns = "";
my $azure_resource_group = "";
my $azure_tenant_id = "";
my $azure_app_id = "";
my $azure_cert_file = "";
my $azure_secret_key_value = "";
my $azure_cert_file_full ="";

my $aws_dns = "";
my $aws_access_key_id = "";
my $aws_secret_access_key = "";
my $aws_region = "";

my $gcp_dns = "";
my $gcp_project = "";
my $gcp_zone = "";
my $gcp_key_file = "";
my $gcp_key_file_full;

GetOptions(
    "aws_dns!"=>\$aws_dns,
    "aws_access_key_id=s"=>\$aws_access_key_id,
    "aws_secret_access_key=s"=>\$aws_secret_access_key,
    "aws_region=s"=>\$aws_region,
    "azure_dns!"=>\$azure_dns,
    "azure_resource_group=s"=>\$azure_resource_group,
    "azure_tenant_id=s"=>\$azure_tenant_id,
    "azure_app_id=s"=>\$azure_app_id,
    "azure_cert_file=s"=>\$azure_cert_file,
    "azure_secret_key_value=s"=>\$azure_secret_key_value,
    "gcp_dns!"=>\$gcp_dns,
	"gcp_project=s"=>\$gcp_project,
	"gcp_zone=s"=>\$gcp_zone,
    "gcp_key_file=s"=>\$gcp_key_file,
	"help!"=>\$help,
    "create_csv!"=>\$create_csv,
    "document_root=s"=>\$document_root,
    "ignore_dns!"=>\$ignore_dns,
	"init_gip!"=>\$init_gip,
    "ipv4!"=>\$ipv4,
    "ipv6!"=>\$ipv6,

	"check_file=s"=>\$check_file,
	"type=s"=>\$type,
	"verbose!"=>\$verbose,

    "changes_only!"=>\$changes_only,
    "mail!"=>\$mail,
    "smtp_server=s"=>\$smtp_server,
    "mail_from=s"=>\$mail_from,
    "mail_to=s"=>\$mail_to,
    "help!"=>\$help,
    "run_once!"=>\$run_once,
    "tag=s"=>\$tag,
    "user=s"=>\$user,
    "use_api!"=>\$use_api,
    "verbose!"=>\$verbose,
    "x!"=>\$debug,

    "A=s"=>\$client,
	"B=s"=>\$ignore_generic_auto,
    "M=s"=>\$logdir,
    "W=s"=>\$gip_job_id,
    "Z!"=>\$use_zone_transfer,
) or print_help();

if ( $help ) {
    print_help();
    exit;
}

$ENV{PATH} = "/bin:/usr/bin:/usr/local/bin";

my $enable_audit = 1;

$dir =~ /^(.*)\/bin/;
$base_dir=$1;
$verbose = 1 if $debug;
$type = "" if ! $type;
our $client_id;
our $job_name = "";
my $config_name = "";

if ( $document_root && ! -r "$document_root" ) {
    print "document_root not readable\n";
    exit 1;
}

# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = Gipfuncs::get_db_parameter();

if ( ! $pass_gestioip ) {
    print "Database password not found\n";
    exit 1;
}


my $vars_file=$base_dir . "/etc/vars/vars_update_gestioip_en";
if ( ! $create_csv ) {

    my $client_count = count_clients();
    if ( $client_count == 1 && ! $client ) {
        $client = "DEFAULT";
    }
    if ( ! $client ) {
        print "Please specify a client name\n";
        exit 1;
    }
    $client_id=get_client_id_from_name("$client") || "" if ! $create_csv;

    if ( ! $client_id ) {
        print "$client: client not found\n";
        exit 1;
    }
}


my $dyn_dns_updates = 1;
my $file;
if ( $check_file ) {
	$file = $base_dir . "/var/data/$check_file";
} else {
	$file = $base_dir . "/var/data/cloud_records_check.txt";
}

my $update_type_audit = "19";
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

    $job_name = Gipfuncs::get_job_name("$gip_job_id");
    my $audit_type="176";
    my $audit_class="36";

    $event="$job_name ($gip_job_id)";
    insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
}


my $start_time=time();

my $datetime;
our $gip_job_status_id = "";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "${type}_cloud_sync");

$log =~ /^([\w.\-_\/]{0,100})$/;
$log = $1;
print "Logfile: $log\n" if $verbose;
if ( ! $log ) {
	Gipfuncs::exit_error("ERROR untainted log: $log", "", 4);
}

open(LOG,">$log") or Gipfuncs::exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;

my $exit_message = "";

$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
    $exit_message = "Can't find configuration file \"$config_name\"";
    Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
}
my $conf = $base_dir . "/etc/" . $config_name;
$conf =~ /^([\w.\-_\/]{0,100})$/;
$conf = $1;
if ( ! $conf ) {
	Gipfuncs::exit_error("ERROR untainted conf: $conf", "", 4);
}

our %params = Gipfuncs::get_params("$conf");

if ( $ignore_generic_auto && $ignore_generic_auto !~ /^yes|no/i ) {
    $exit_message = "ignore_generic_auto (-B) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}


my $csv_string;
if ( $create_csv ) {
    if ( ! $client ) {
        print "Specifiy the client name (-A client_name)\n";
        exit 1;
    }

    my $path = '/listClientsResult/client';
    my $content = "request_type=listClients&client_name=$client";
    my $value = "id";
    $client_id = Gipfuncs::make_call_value("$path", "$content", "$value") || "";

    if ( ! $client_id ) {
        print "Client not found\n";
        exit 1;
    }

    # create csv file
    my $csv_file = $base_dir . "/var/data/csv_cloud_" . $client_id . ".csv";
    $csv_string = "action,ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,client_id,ip_version,dyn_dns_updates,update_type_audit\n";
    open(CSV,">$csv_file") or Gipfuncs::exit_error("Can not open csv_file $csv_file: $!", "", 4);
    print CSV $csv_string;
}


my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime gip_cloud_sync.pl $gip_job_id_message\n\n";
print LOG "\n######## Synchronization against cloud environment ($datetime) ########\n\n";


my $logfile_name = $log;
$logfile_name =~ s/^(.*\/)//;

my $delete_job_error;
if ( $gip_job_id ) {
    if ( $run_once ) {
        $delete_job_error = delete_cron_entry("$gip_job_id");
        if ( $delete_job_error ) {
            print LOG "ERROR: Job not deleted from crontab: $delete_job_error";
        }
    } else {
        my $check_end_date = Gipfuncs::check_end_date("$gip_job_id", "5") || "";
        if ( $check_end_date eq "TOO_LATE" && ! $use_api ) {
            $delete_job_error = delete_cron_entry("$gip_job_id");
            if ( $delete_job_error ) {
                $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
                Gipfuncs::exit_error("ERROR: Job not deleted from crontab: $delete_job_error", "$gip_job_status_id", 4 );
            } else {
                exit;
            }
        }
    }
    # status 2: running
    $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
}


our @mail_to;
if ( $mail && ! $smtp_server ) {
        Gipfuncs::exit_error("Missing argument --smtp_server", "$gip_job_status_id", 4);
}
if ( $smtp_server ) {
    if ( ! $mail_from ) {
            Gipfuncs::exit_error("Missing argument --mail_from", "$gip_job_status_id", 4);
    }
    if ( ! $mail_to ) {
            Gipfuncs::exit_error("Missing argument --mail_to", "$gip_job_status_id", 4);
    }
    @mail_to = split(",",$mail_to);
}


my @client_entries=Gipfuncs::get_client_entries("$client_id");

my $default_resolver = $client_entries[0]->[20] || "";
print LOG "DEFAULT RESOLVER: $default_resolver\n";

my $count = 0;
my $countu = 0;
my $counti = 0;
my $countd = 0;
my $countu6 = 0;
my $counti6 = 0;
my $countd6 = 0;

my $values_data_hash;

# FETCH DATA FROM CLOUD

my $values_dns_azure;
my $values_dns_aws;
my $values_dns_gcp;
my $azure_auth_value;
if ( $type eq "aws" ) {
    $ipv4 = 1 if ! $ipv4 && ! $ipv6;
    Gipfuncs::exit_error("Only one of the options --ipv4 or --ipv6 allowed", "$gip_job_status_id", 4) if $ipv4 && $ipv6; 
#    Gipfuncs::exit_error("Insert the URL of the Kea API", "$gip_job_status_id", 4) if ! $kea_url; 
#    Gipfuncs::exit_error("Option --kea_url does not support the --leases_file option", "$gip_job_status_id", 4) if $leases_file;
    make_auth_aws();
    $values_data_hash = get_data_aws();
	$values_dns_aws = get_dns_data_aws("") if $aws_dns;
} elsif ( $type eq "azure" ) {
    $ipv4 = 1 if ! $ipv4 && ! $ipv6;
    Gipfuncs::exit_error("Only one of the options --azure_cert_file or --azure_secret_key_value allowed", "$gip_job_status_id", 4) if $azure_cert_file && $azure_secret_key_value; 
    Gipfuncs::exit_error("with option --azure_dns you need to specify a azure_resource_group", "$gip_job_status_id", 4) if $azure_dns && ! $azure_resource_group;
    Gipfuncs::exit_error("Argument --azure_tenant_id missing", "$gip_job_status_id", 4) if ! $azure_tenant_id;
    Gipfuncs::exit_error("Argument --azure_app_id missing", "$gip_job_status_id", 4) if ! $azure_app_id;
    Gipfuncs::exit_error("Argument --azure_secret_key_value or --azure_cert_file missing", "$gip_job_status_id", 4) if ! $azure_secret_key_value && ! $azure_cert_file;
	if ( $azure_cert_file ) {
		$azure_cert_file_full = "${base_dir}/etc/auth/azure/${azure_cert_file}";
		$azure_cert_file_full =~ /^([\w.\-_\/]{0,100})$/;
		$azure_cert_file_full = $1;
		if ( ! -r $azure_cert_file_full ) {
			Gipfuncs::exit_error("--azure_cert_file not readable: $azure_cert_file_full: $! ", "$gip_job_status_id", 4);
		}
		$azure_auth_value = $azure_cert_file_full;
	} else {
		$azure_auth_value = $azure_secret_key_value;
	}
	make_auth_azure();
    $values_data_hash = get_data_azure();
	$values_dns_azure = get_dns_data_azure("$azure_resource_group") if $azure_dns;
} elsif ( $type eq "gcp" ) {
    $ipv4 = 1 if ! $ipv4 && ! $ipv6;
    Gipfuncs::exit_error("Only one of the options --ipv4 or --ipv6 allowed", "$gip_job_status_id", 4) if $ipv4 && $ipv6; 

    Gipfuncs::exit_error("Specify a project (--gcp_project)", "$gip_job_status_id", 4) if ! $gcp_project;
    Gipfuncs::exit_error("Specify a key file (--gcp_key_file)", "$gip_job_status_id", 4) if ! $gcp_key_file;
	$gcp_key_file_full = "${base_dir}/etc/auth/gcloud/${gcp_key_file}";
    if ( ! -r $gcp_key_file_full ) {
        Gipfuncs::exit_error("--gcp_key_file not readable: $gcp_key_file_full: $! ", "$gip_job_status_id", 4);
    }
	if ( ! -r "$gcp_key_file_full" ) {
		Gipfuncs::exit_error("Error reading key file (--gcp_key_file): $gcp_key_file_full", "$gip_job_status_id", 4) if ! $gcp_key_file;
	}
	make_auth_gcp();

    $values_data_hash = get_data_gcp();
    Gipfuncs::exit_error("with option --azure_dns you need to specify a azure_resource_group", "$gip_job_status_id", 4) if $azure_dns && ! $azure_resource_group;
	$values_dns_gcp = get_dns_data_gcp("$azure_resource_group") if $gcp_dns;
} elsif ( ! $type) {
    Gipfuncs::exit_error("No type specified", "$gip_job_status_id", 4);
} else {
    Gipfuncs::exit_error("Unsupported type", "$gip_job_status_id", 4);
}

if ( ! %$values_data_hash ) {
    Gipfuncs::exit_error("Did not received data from cloud", "$gip_job_status_id", 6); # 6 > skipped
}
my %values_data_hash = %$values_data_hash;

#TAGs
my @tag;
my $tag_ref = "";
if ( $tag ) {
    $tag =~ s/\s//g;
    @tag = split(",", $tag);
    $tag_ref = \@tag;
}

my @values_host_redes4 = Gipfuncs::get_host_redes_no_rootnet("$client_id","v4", $tag_ref);

my $values_host_redes4_count = @values_host_redes4;
print LOG "Number networks IPv4: $values_host_redes4_count\n" if $debug;
my @values_host_redes6 = Gipfuncs::get_host_redes_no_rootnet("$client_id","v6", $tag_ref);
my $values_host_redes6_count = @values_host_redes6;
print LOG "Number networks IPv6: $values_host_redes6_count\n" if $debug;
my @values_data;
my @values_data_old;

my %values_data_hash_old;
my %values_data_hash_delete;
my @values_data_n = get_data_array($values_data_hash);
my @custom_columns = get_custom_host_columns("$client_id") if ! $create_csv;
my @redes_usage_array;
my %duplicated_entries_hash;


my $j = 0;
my $k = 0;
my $i = 0;

my $neto_old;
my $red_num_old;
my $loc_id_old;
my $ip_version_old;
my %host_hash_old;

## delete duplicated values from @values_data
#my %seen;
#my @values_data_uniq;
#foreach my $val ( @values_data ) {
#    my $helper = join("%%%%", @$val);
#    print LOG "Duplicated entry deleted: @$val\n" if exists $seen{$helper} && $debug;
#    $seen{$helper} = 1;
#}
#
#my $l=0;
#foreach my $key (keys %seen) {
#    my @arr = split("%%%%", $key);
#    $values_data_uniq[$l] = \@arr;
#    $l++;
#}
#@values_data = @values_data_uniq;
#my $count_data = @values_data;
#print LOG "Found $count_data new records\n" if $verbose;

my $sites = Gipfuncs::get_loc_hash("$client_id","id");
my $cats = Gipfuncs::get_cat_hash("$client_id","id");

my %networks_dns_checked_hash;
my %networks_dns_zone_hash;
my %networks_dns_server_hash;
my %networks_dns_server_ok_hash;

my %host_hash_red;
my %host_hash_red6;

$j = 0;
foreach ( @values_data_n ) {
    my $hostname = $values_data_n[$j]->[0];
    my $ip = $values_data_n[$j]->[1];
    my $mac = $values_data_n[$j]->[2] || "";
    my $dns_name = $values_data_n[$j]->[3] || "";
	my $instance = $hostname;

    my $ip_version = "v4";
    if ( $ip !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $ip_version = "v6";
    }

	# use DNS name as hostname if DNS name exists. Use instance as cc-column "Instance" allways
	my $generic_auto = Gipfuncs::get_generic_auto("$ip", "$ip_version");
    print LOG "Processing: \"$hostname - $ip - $mac - $dns_name - $instance - $generic_auto\" - $j\n" if $debug;

	if ( $dns_name !~ /${generic_auto}/ ) {
		$hostname = $dns_name if $dns_name;
	}

	if ( ! $hostname || ! $ip ) {
		print LOG "Missing hostname or ip: $hostname - $ip\n" if $debug;
		next;
	}


	$j++;

	# check if IP is from same network as the IP before - to find network for IP
	my $ipo = new Net::IP ($ip);
	my $ipo_int = $ipo->intip();
	my $mydatetime = time();
	if ( $neto_old ) {
		if ( $ipo->overlaps($neto_old) ) {
            print LOG "Found net_old with overlap: $neto_old\n" if $debug;

            my $dns_name_query = get_dns_entry("$ip", "$ip_version", "$dns_name", "$red_num_old", "$generic_auto") || "";
            if ( $dns_name_query && $dns_name_query !~ /${generic_auto}/ ) {
                # use queried DNS name if exists
                $hostname = $dns_name_query;
            }

			if ( $host_hash_old{$ipo_int} ) {
				my $host_id = $host_hash_old{$ipo_int}[1] || "";
				my $hostname_check = $host_hash_old{$ipo_int}[0] || "";
                my $ut = $host_hash_old{$ipo_int}[4] || "-1";
                my $red_num_usage = $host_hash_old{$ipo_int}[5] || "";

                print LOG "$host_id - $hostname_check\n" if $debug;

                if ( $hostname ne $hostname_check ) {
                    if ( $ut ne 1 ) {
                        update_hostname("$client_id", "$host_id", "$hostname", "$ip", "$ip_version");
                        $countu++;

                        print LOG "UPDATE (1): $ip - $host_id\n" if $verbose;

                        update_predef_host_column_value("$client_id", "Instance", "$host_id", "$instance");
						
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
				my $new_id = insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id_old, "", "", "", "2", "$mydatetime", "$red_num_old", "-1", "$ip_version_old", "$dyn_dns_updates") || "";
				$counti++;
				print LOG "INSERT (1): $ip\n" if $verbose;

				insert_predef_host_column_value("$client_id", "Instance", "$new_id", "$instance") if $new_id;
						
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

            my $n = $values_host_redes4[$k]->[0] || "";
			my $rootnet = $values_host_redes4[$k]->[5] || 0;
            if ( ! $n || $rootnet == 1 ) {
                $k++;
                next;
            }

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
                print LOG "Found network for host: $hostname - $net - $red_num\n" if $debug;

                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");
                $host_hash_red{$red_num} = \%host_hash if ! $host_hash_red{$red_num};

				my $dns_name_query = get_dns_entry("$ip", "$ip_version", "$dns_name", "$red_num", "$generic_auto") || "";
				if ( $dns_name_query && $dns_name_query !~ /${generic_auto}/ ) {
					# use queried DNS name if exists
					$hostname = $dns_name_query;
				}
				
                if ( exists $host_hash{$ipo_int} ) {
                    my $hn = $host_hash{$ipo_int}[0] || "";
                    my $hip = $host_hash{$ipo_int}[2] || "";
                    print LOG "Found host: $hn - $hip - $net\n" if $debug;
                    print "Found host: $hn - $ip - $net\n" if $debug;
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;

                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    if ( $ut eq 1 ) {
                        # update type "man"
                        print LOG "UPDATE: update type: man - ignored - $n/$bm - $ip - $host_id - $ut\n" if $debug;
                    } else {
						if ( $hn eq $hostname ) {
							print LOG "Hostname has not changed $ip - $hostname - ignored\n" if $verbose;
						} else {
							update_hostname("$client_id", "$host_id", "$hostname", "$ip", "$ip_version");
							$countu++;
							
							print LOG "UPDATE (2): $n/$bm - $ip - $host_id\n" if $verbose;

                            update_predef_host_column_value("$client_id", "Instance", "$host_id", "$instance");

							my $audit_type="1";
							my $audit_class="1";
							$event = "$ip - $hn > $hostname";
							insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
						}
                    }
                } else {
                    my $new_id = insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates") || "";
                    $counti++;
                    print LOG "INSERT (2): $n/$bm - $ip \n" if $verbose;

					insert_predef_host_column_value("$client_id", "Instance", "$new_id", "$instance") if $new_id;

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

        if ( ! $hostname || ! $ip ) {
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

            print LOG "Processing V6: $hostname\n" if $debug;

			my $n_exp = ip_expand_address ($n, 6);
			my $ip_exp = ip_expand_address ($ip, 6);

            print LOG "IP expanded: $n_exp - $ip_exp\n" if $debug;

            $n_exp =~ /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np=$1;
            $ip_exp =~ /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np_host=$1;
            if ( $bm == 64 && $np ne $np_host ) {
                $count++;
                $k++;
                next;
			}

            my $net = "$n/$bm";
            my $neto = new Net::IP ($net);


            if ( $ipo->overlaps($neto) ) {
                print LOG "Found network for host V6: $hostname - $net - $red_num\n" if $debug;

                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");
                $host_hash_red6{$red_num} = \%host_hash if ! $host_hash_red{$red_num};

				my $dns_name_query = get_dns_entry("$ip_exp", "$ip_version", "$dns_name", "$red_num", "$generic_auto") || "";
				if ( $dns_name_query && $dns_name_query !~ /${generic_auto}/ ) {
					# use queried DNS name if exists
					$hostname = $dns_name_query;
				}

                if ( exists $host_hash{$ipo_int} ) {
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;
                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    my $hn = $host_hash{$ipo_int}[0] || "";
                    my $hip = $host_hash{$ipo_int}[2] || "";
                    print LOG "Found host6: $hn - $hip - $net - $host_id\n" if $debug;
                    print "Found host6: $hn - $ip - $net - $host_id\n" if $debug;
                    last if ! $host_id;

                    # Delete host if it exits in host_hash and if is in %values_data_hash_delete
                    if ( exists $values_data_hash_delete{$ip} && $values_data_hash_delete{$ip} eq $hostname ) {
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
                    } elsif ( exists $values_data_hash_delete{$ip} ) {
                        print LOG "Not deleted - hostname and hostname-old differ: $values_data_hash_delete{$ip} - $hostname\n" if $debug;
                        last;
                    }

                    if ( $host_id ) {
                        if ( $ut ne 1 ) {
							if ( $hn eq $hostname ) {
								print LOG "Hostname has not changed $ip - $hostname - ignored\n" if $verbose;
							} else {
								update_hostname("$client_id", "$host_id", "$hostname", "$ip", "$ip_version");
								$countu++;

								print LOG "UPDATE (3): $n/$bm - $ip - $host_id\n" if $verbose;

                                update_predef_host_column_value("$client_id", "Instance", "$host_id", "$instance");

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
                    my $new_id = insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates") || "";
                    $counti++;
                    print LOG "INSERT (3): $n/$bm - $ip \n" if $debug;

					insert_predef_host_column_value("$client_id", "Instance", "$new_id", "$instance") if $new_id;
						
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

# Delete not found entries
foreach my $red_num ( keys %host_hash_red ) {
    my $host_hash_ref = $host_hash_red{$red_num};
    foreach my $int_ip ( keys %$host_hash_ref ) {
         my $hn = $host_hash_ref->{$int_ip}[0] || "";
         my $ip = $host_hash_ref->{$int_ip}[2] || "";
         my $ut = $host_hash_ref->{$int_ip}[4] || "-1";
         my $ip_version = $host_hash_ref->{$int_ip}[6] || "";
         if ( ! $values_data_hash{$int_ip} ) {
			print LOG "DELETE: $ip - $hn - $ut\n" if $debug;
			print LOG "DELETE: $ip - $hn - $ut\n" if $verbose;
			if ( $ut ne 1 ) {
				# update type not "man"
				delete_or_clear("$client_id", "$ip", $host_hash_ref, "$ip_version");

			   my $audit_type="14";
			   my $audit_class="1";
			   $event = "$ip - $hn - $ut";
			   insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
             }
         }
    }
}


if ( ! $create_csv ) {
    # update net usage
    my %seen = ();
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
}

print "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;
print LOG "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;

close CSV;
close LOG;

my @smtp_server_values;
if ( $mail ) {
	@smtp_server_values = Gipfuncs::get_smtp_server_by_name("$smtp_server");
	
	if ( $smtp_server_values[0] ) {
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
			smtp_server_values   =>  \@smtp_server_values,

		);
	} else {
		print "Can not determine SMTP values - mail not send\n";
		print LOG "Can not determine SMTP values - mail not send\n";
	}
}

my $end_time=time();

if ( $gip_job_id ) {
    Gipfuncs::update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
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

sub get_data_aws {

	my $now = time();

	my %result_hash;
	my $json_result = "";
    my ( $ip, $v6ip, $instance_id, $mac, $interface_id, $dns_name );

	my $command = "aws ec2 describe-instances --no-cli-pager";
    $command =~ /^(.*)$/;
    $command = $1;

	my $output_json = `$command 2>&1`;
#      my  $output_json = get_data_file("/tmp/aws_ec2_describe-instances.json") || "";

	$output_json = '[' . $output_json . ']';
	my $text = gip_decode_json("$output_json");

    my $count_test = 0;
	my $reservations = $text->[0]->{Reservations};
	foreach my $res ( @$reservations ) {
        $count_test++;
		my $instances = $res->{Instances};
		foreach my $ins ( @$instances ) {
			$instance_id = $ins->{InstanceId} || "unknown";
			print LOG "InstanceID: $instance_id\n";
			my $network_interface = $ins->{NetworkInterfaces};

			foreach my $NI ( @$network_interface ) {
				$interface_id = $NI->{NetworkInterfaceId} || "";
				$mac = $NI->{MacAddress} || "";
				print LOG "interfaceID: $interface_id - MAC: $mac\n";	

				my $privat_ip_addresses = $NI->{PrivateIpAddresses};
				foreach my $PADS (@$privat_ip_addresses) {
					$ip = $PADS->{PrivateIpAddress} || "";
					print LOG "PrivateIpAddress: $ip\n";
					next if $ip !~ /^\d{1,3}\./ && $ip !~ /^([a-fA-F0-9]){1,4}:/;

					$dns_name = $PADS->{PrivateDnsName} || "";
					print LOG "PrivateDnsName: $dns_name\n";

					my $ip_int = Gipfuncs::ip_to_int("$ip");
					push @{$result_hash{$ip_int}},"$ip","$instance_id","$mac","$dns_name";
				}

				my $ipv6_ip_addresses = $NI->{Ipv6Addresses};
				foreach my $V6ADS (@$ipv6_ip_addresses) {
					$ip = $V6ADS->{Ipv6Address} || "";
					print LOG "Ipv6Address: $ip\n";
					next if $ip !~ /^([a-fA-F0-9]){1,4}:/;

					my $ip_int = Gipfuncs::ip_to_int("$ip");
					push @{$result_hash{$ip_int}},"$ip","$instance_id","$mac","";
				}
			}
		}
	}
    print LOG "count reservations: $count_test\n" if $debug;

	return \%result_hash;
}

sub get_dns_data_aws {
    my ($resource_group) = @_;

    $resource_group = "" if ! $resource_group;
    my $now = time();

    my %result_hash;
    my $output_json = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name, $text );
    my @zones;

    # get zones
#	$output_json = get_data_file("aws_route53_list-zones-by-name.json");
    my $command = "aws route53 list-hosted-zones";
    $command =~ /^(.*)$/;
    $command = $1;
    $output_json = `$command 2>&1`;

	$output_json = '[' . $output_json . ']';
	$text = gip_decode_json("$output_json");

    foreach my $z ( @$text ) {
        my $hosted_zones = $z->{HostedZones} || "";
		foreach my $hz ( @$hosted_zones ) {
			my $name = $hz->{Name} || "";
			my $id = $hz->{Id} || "";
			print LOG "HostedZone: $id - $name\n" if $verbose;
			$id =~ s/^.*\///;
			push @zones, "$id" if $id;
		}
    }

    foreach my $zone ( @zones ) {
#        $output_json = get_data_file("aws_route53_list-resource-record-sets.json") || "";
        my $command = "az network dns record-set a list --resource-group $resource_group --zone-name $zone";
		$command =~ /^(.*)$/;
		$command = $1;
        $output_json = `$command 2>&1`;

        $output_json = '[' . $output_json . ']';
        my $text1 = gip_decode_json("$output_json");

		foreach my $m ( @$text1 ) {
			my $resource_record_set = $m->{ResourceRecordSets};
			foreach my $rrs ( @$resource_record_set ) {

				my $type = $rrs->{Type} || "";

				next if $type ne "A" && $type ne "AAAA";

				my $name = $rrs->{Name} || "";
				print LOG "NAME DNS: $name\n" if $debug;

				next if ! $name;

				my $resource_record = $rrs->{ResourceRecords} || "";
				foreach my $rr ( @$resource_record ) {
					my $ip = $rr->{Value} || "";
					print LOG "IP DNS: $ip\n" if $debug;
					$result_hash{$ip} = "$name";
				}
			}
		}
	}

    return \%result_hash;
}


sub get_data_azure {

    my $now = time();

    my %result_hash;
    my $json_result = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name );

	my $command = "az vm list-ip-addresses";
    $command =~ /^(.*)$/;
    $command = $1;
	my $output_json = `$command 2>&1`;

	my $text = gip_decode_json("$output_json");

	foreach my $f_vm ( @$text ) {
		my $name = $f_vm->{virtualMachine}->{name} || "";
		print "NAME get_azure_data: $name\n";

		my $private_ips = $f_vm->{virtualMachine}->{network}->{privateIpAddresses} || "";
		foreach ( @$private_ips ) {
			my $ip = $_;
			my $ip_int = Gipfuncs::ip_to_int("$ip");
			push @{$result_hash{$ip_int}},"$ip","$name","","";
		}

		my $public_ips = $f_vm->{virtualMachine}->{network}->{publicIpAddresses} || "";
		foreach my $arr ( @$public_ips ) {
			my $ip = $arr->{ipAddress};
			my $ip_int = Gipfuncs::ip_to_int("$ip");
			push @{$result_hash{$ip_int}},"$ip","$name","","";
		}
	}

    return \%result_hash;
}

sub get_dns_data_azure {
	my ($resource_group) = @_;

	$resource_group = "" if ! $resource_group;
    my $now = time();

    my %result_hash;
    my $json_result = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name, $text );
	my @zones;

	# get zones
	my $command = "az network dns zone list";
    $command =~ /^(.*)$/;
    $command = $1;
	my $output_json = `$command 2>&1`;
	$text = gip_decode_json("$output_json");

	foreach my $z ( @$text ) {
		my $name = $z->{name} || "";
		my $resource_group_zone = $z->{resourceGroup} || "";
		print LOG "Zone name: $name - $resource_group\n";
		push @zones, "$name" if $resource_group eq $resource_group_zone;
	}

	foreach my $zone ( @zones ) {
		my $command = "az network dns record-set a list --resource-group $resource_group --zone-name $zone";
		$command =~ /^(.*)$/;
		$command = $1;
		my $output_json = `$command 2>&1`;

		my $text1 = gip_decode_json("$output_json");

		foreach my $f_vm ( @$text1 ) {
			my $name = $f_vm->{fqdn} || "";
			my $a_records = $f_vm->{aRecords};
			
			foreach my $rec ( @$a_records ) {
				my $ip = $rec->{ipv4Address} || "";
				$result_hash{$ip} = "$name";
                print LOG "FOUND DNS ENTRY SUB: $ip - $result_hash{$ip}\n";
			}
		}
	}

    return \%result_hash;
}

sub make_auth_gcp {

	$ENV{HOME} = "/${base_dir}/etc/auth/gcloud";
    $ENV{CLOUDSDK_CORE_PROJECT} = "$gcp_project";
	my $command = "gcloud auth activate-service-account --key-file=${gcp_key_file_full}";
    $command =~ /^(.*)$/;
    $command = $1;
	print LOG "auth command: $command\n";

	my $exit_code=system($command);

	if ( $exit_code != 0 ) {
		my $output_json = `$command 2>&1`;
		print LOG "make_auth_gcp output: $output_json\n" if $debug;
		Gipfuncs::exit_error("Authentication failed", "$gip_job_status_id", 4);
	}

    return;
}

sub make_auth_azure {

    my %result_hash;
    my $json_result = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name );
    $ENV{AZURE_CONFIG_DIR} = "/${base_dir}/etc/auth/azure/.azure";

	my $command = "/usr/bin/az login --service-principal -u $azure_app_id -p $azure_auth_value --tenant $azure_tenant_id";
    $command =~ /^(.*)$/;
    $command = $1;
	print LOG "make_auth_azure: $command\n";
	my $output_json = `$command 2>&1`;


	my $text = gip_decode_json("$output_json");

	my $tenant_id_found = "";
	foreach my $auth ( @$text ) {
		$tenant_id_found = $auth->{tenantId} || "";
		print "TenantID: $tenant_id_found\n";
    }

	if ( ! $tenant_id_found ) {
		print LOG "make_auth_azure_out: $output_json\n" if $debug;
		Gipfuncs::exit_error("Authentication failed", "$gip_job_status_id", 4);
	}

    return;
}

sub make_auth_aws {

    # set environment variables with credenciales
    $ENV{'AWS_ACCESS_KEY_ID'} = $aws_access_key_id;
    $ENV{'AWS_SECRET_ACCESS_KEY'} = $aws_secret_access_key;
    $ENV{'AWS_DEFAULT_REGION'} = $aws_region;

#	$ENV{'AWS_CONFIG_FILE'} = "/tmp/.aws/config
#	$ENV{'AWS_SHARED_CREDENTIALS_FILE'} = "/tmp/.aws/config

    # verify key
	my $command = "aws sts get-caller-identity";
    $command =~ /^(.*)$/;
    $command = $1;
	print LOG "auth command: $command\n";
	my $output_json = `$command 2>&1`;

	print LOG "make_auth_aws: $output_json\n";
    
	$output_json = '[' . $output_json . ']';
    my $text = gip_decode_json("$output_json");

    my $user_id = "";
	foreach my $caller_id ( @$text ) {
		$user_id = $caller_id->{UserId} || "";
    }

    Gipfuncs::exit_error("Authentication failed", "$gip_job_status_id", 4) if ! $user_id;

    return;
}


sub get_data_gcp {

    my %result_hash;
    my $json_result = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name );

	my $command = "gcloud compute instances list --zones=$gcp_zone --format='json(name, networkInterfaces[].networkIP, networkInterfaces[].accessConfigs[])'";
    $command =~ /^(.*)$/;
    $command = $1;
	print LOG "get_data_gcp: $command\n";
	my $output_json = `$command 2>&1`;

	my $text = gip_decode_json("$output_json");

	foreach my $f_vm ( @$text ) {
		my $name = $f_vm->{name} || "";
		print "NAME get_data_gcp: $name\n";

		my $network_interfaces = $f_vm->{networkInterfaces} || "";
		foreach my $ni ( @$network_interfaces ) {
			my $ip = $ni->{networkIP};
			my $ip_int = Gipfuncs::ip_to_int("$ip");
			push @{$result_hash{$ip_int}},"$ip","$name","","";
		print "NAME get_data_gcp: $ip - $name\n";

            my $access_configs = $ni->{accessConfigs};

            foreach my $ac ( @$access_configs ) {
                my $public_ip = $ac->{natIP} || "";
                my $ip_int = Gipfuncs::ip_to_int("$public_ip");
                push @{$result_hash{$ip_int}},"$public_ip","$name","","";
		print "NAME get_data_gcp pub: $public_ip - $name\n";
            }
		}

	}

    return \%result_hash;
}

sub get_dns_data_gcp {
	my () = @_;

    my %result_hash;
    my $json_result = "";
    my ( $ip, $name, $mac, $interface_id, $dns_name, $text );
	my @zones;

	# get zones
    my $command = "gcloud dns managed-zones list --format='json(name)'";
    $command =~ /^(.*)$/;
    $command = $1;
	print LOG "get_dns_data_gcp: $command\n";
    my $output_json = `$command 2>&1`;
    $text = eval { decode_json($output_json) };
	if($@) {
		print LOG "JSON: $output_json\n" if $debug;
		Gipfuncs::exit_error("get_data_gcp: ERROR $@", "$gip_job_status_id", 4);
	}

    foreach my $z ( @$text ) {
        my $name = $z->{name} || "";
        print LOG "Zone name: $name\n";
        push @zones, "$name" if $name;
    }


	foreach my $zone ( @zones ) {
		print LOG "prosessing zone: $zone\n" if $debug;
        my $command = "gcloud dns record-sets list --zone=$zone --format='json(name, type, rrdatas[])'";
		$command =~ /^(.*)$/;
		$command = $1;
		print LOG "get_dns_data_gcp rr: $command\n";
        my $output_json = `$command 2>&1`;
		my $text = eval { decode_json($output_json) };
		if($@) {
			print LOG "JSON: $output_json\n" if $debug;
			Gipfuncs::exit_error("get_data_gcp rr: ERROR $@", "$gip_job_status_id", 4);
		}

        foreach my $z ( @$text ) {
            my $name = $z->{name} || "";
            my $type = $z->{type} || "";
            print LOG "DNS name: $name - $type\n";

            if ( $type eq "A" ) {
                my $rrdatas = $z->{rrdatas} || "";
                foreach my $rr ( @$rrdatas ) {
                    my $ip = $rr;
                    print LOG "DNS IP: $ip\n";
                    $result_hash{$ip} = "$name";
                    
                }
            }
        }
    }

    return \%result_hash;
}

sub get_data_array {

	my ( $hash ) = @_;

    my @values;
    foreach my $ip_int ( sort keys %$hash ) {
        my $hostname = $hash->{$ip_int}[0]; 
        my $ip = $hash->{$ip_int}[1]; 
        my $mac = $hash->{$ip_int}[2]; 
        my $lft = $hash->{$ip_int}[3]; 
		my @row = ( "$ip","$hostname","$mac","$lft" );
        push @values,[@row]; 
    }

    return @values;
}


sub get_host_hash {
    my ( $client_id, $red_num, $ip_version ) = @_;

	my %host_hash;

	if ( ! $create_csv ) { 
		my $ip_ref;
		my $dbh = mysql_connection();
		my $qclient_id = $dbh->quote( $client_id );
		my $qred_num = $dbh->quote( $red_num );

		my $sth = $dbh->prepare("SELECT ip, INET_NTOA(ip), hostname, id, range_id, update_type, red_num FROM host WHERE red_num=$qred_num AND client_id=$qclient_id")
			or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		while ( $ip_ref = $sth->fetchrow_hashref ) {
			my $ip_int = $ip_ref->{'ip'};
			my $ip = "";
			$ip = $ip_ref->{'INET_NTOA(ip)'} if $ip_version eq "v4";
			my $hostname = $ip_ref->{'hostname'} || "";
			my $id = $ip_ref->{'id'};
			my $range_id = $ip_ref->{'range_id'};
			my $update_type = $ip_ref->{'update_type'};
			my $red_num = $ip_ref->{'red_num'};

			push @{$host_hash{$ip_int}},"$hostname","$id","$ip","$range_id","$update_type","$red_num","$ip_version";
		}

		$dbh->disconnect;

    } else {
        my $path = '/usedNetworkAddressesResult/Network/HostList/Host';
        my $content = "request_type=usedNetworkAddresses&client_name=$client&no_csv=yes&id=$red_num";
#        my @values = ("IP", "hostname", "descr", "comment", "range_id", "ip_int", "id", "red_num", "client_id", "ip_version", "loc_id", "cat_id", "utype_id", "int_admin", "alive");
        my @values = ("hostname", "id", "IP", "range_id", "update_type", "red_num", "ip_version");

        my $host_hash = Gipfuncs::make_call_hash("$path", "$content", \@values, "ip_int");
		%host_hash = %$host_hash;
    }

    return %host_hash;

}

sub insert_ip_mod {
    my ( $client_id, $ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $dyn_dns_updates ) = @_;

	$loc="" if ! $loc;
	$cat="" if ! $cat;

	my ($ip, $id);

	if ( ! $create_csv && ! $use_api ) {
		$loc="-1" if ! $loc;
		$cat="-1" if ! $cat;
		my $dbh = mysql_connection();
		my $sth;
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
									) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		} else {
			$sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qip_version,$qclient_id,$qdyn_dns_updates)"
									) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		}
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$id = $sth->fetchrow_array;

		$sth->finish();
		$dbh->disconnect;

	} elsif ( $use_api ) {
		$ip = Gipfuncs::int_to_ip("$ip_int","$ip_version");
		my $site = $sites->{$loc} || "";
		my $category = $cats->{$cat} || "";
		my $path = '/createHostResult/Host';
		my $content = "request_type=createHost&ip=$ip&client_name=$client&new_hostname=$hostname&new_comment=$comentario&new_site=$site&new_cat=$category&new_int_admin=n&new_dyn_dns_update_type=$dyn_dns_updates&red_num=$red_num";
		my $value = "new_id";
		my $return = Gipfuncs::make_call_value("$path", "$content", "$value") || "";

		if ( ! $return ) {
			print "$ip - host not created (did not got result from API)\n" if $verbose;
			print LOG "$ip - host not created (did not got result from API)\n" if $verbose;
		}

		$id = $return if $return =~ /^\d{1,8}$/;

	} else {
		my $last_response = time();
		$csv_string = "INSERT,$ip_int,$hostname,$host_descr,$loc,$red_num,$int_admin,$cat,$comentario,$update_type,$mydatetime,$alive,$last_response,$client_id,$ip_version,$dyn_dns_updates,4";
		$csv_string =~ s/"/\\"/g;
		$csv_string =~ s/,/","/g;
		$csv_string = '"' . $csv_string . '"' . "\n";
		print CSV $csv_string;
	}

	return $id;
}


sub update_hostname {
    my ( $client_id, $id, $hostname, $ip, $ip_version ) = @_;

    print LOG "UPDATE HOSTNAME: $hostname - $id\n" if $verbose;

	if ( ! $create_csv && ! $use_api ) {
		my $dbh = mysql_connection();
		my $sth;
		my $qhostname = $dbh->quote( $hostname );
		my $qid = $dbh->quote( $id );
		my $qclient_id = $dbh->quote( $client_id );

		$sth = $dbh->prepare("UPDATE host SET hostname=$qhostname WHERE id=$qid AND client_id=$qclient_id"
									) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->finish();
		$dbh->disconnect;
	} elsif ( $use_api ) {
		my $path = '/updateHostResult/Host';
		my $content = "request_type=updateHost&ip=$ip&client_name=$client&new_hostname=$hostname";
		my $value = "new_hostname";
		my $return = Gipfuncs::make_call_value("$path", "$content", "$value") || "";
		if ( ! $return ) {
			print "$ip - hostname not updated (did not got result from API)\n" if $verbose;
			print LOG "$ip - hostname not updated (did not got result from API)\n" if $verbose;
		}
	} else {
		my $last_response = time();

		my $ip_int = Gipfuncs::ip_to_int("$ip","$ip_version") || "";
#		$csv_string = "UPDATE,$ip_int,$hostname,$host_descr,$loc,$red_num,$int_admin,$cat,$comentario,$update_type,$mydatetime,$alive,$last_response,$client_id,,$dyn_dns_updates,4";
        $csv_string = "UPDATE_HOSTNAME,$ip_int,$hostname,,,,,,,,,,,,,,4";
		$csv_string =~ s/"/\\"/g;
		$csv_string =~ s/,/","/g;
		$csv_string = '"' . $csv_string . '"' . "\n";
		print CSV $csv_string;
	}

}

sub delete_ip {
    my ( $client_id, $first_ip_int, $last_ip_int, $ip_version ) = @_;

	if ( ! $create_csv && ! $use_api ) {
		my $dbh = mysql_connection();
		my $qfirst_ip_int = $dbh->quote( $first_ip_int );
		my $qlast_ip_int = $dbh->quote( $last_ip_int );
		my $qclient_id = $dbh->quote( $client_id );

		my $match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";

		my $sth = $dbh->prepare("DELETE FROM host WHERE $match AND client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->finish();
		$dbh->disconnect;
	} elsif ( $use_api ) {
		my $ip = Gipfuncs::int_to_ip("$first_ip_int","$ip_version");
		my $path = '/deleteHostResult/Host';
		my $content = "request_type=deleteHost&ip=$ip&client_name=$client";
		my $value = "hostname";
		my $return = Gipfuncs::make_call_value("$path", "$content", "$value") || "";
    } else {
        $csv_string = "DELETE,$first_ip_int,,,,,,,,,,,,,,,4";
        $csv_string =~ s/,/","/g;
        $csv_string = '"' . $csv_string . '"' . "\n";
        print CSV $csv_string;
    }
}

sub clear_ip {
    my ( $client_id, $ip_int, $ip_version ) = @_;

#	return if $create_csv;

	if ( ! $create_csv && ! $use_api ) {
		my $dbh = mysql_connection();
		my $qip_int = $dbh->quote( $ip_int );
		my $qclient_id = $dbh->quote( $client_id );

		my $sth = $dbh->prepare("UPDATE host SET hostname='', host_descr='', int_admin='n', alive='-1', last_response=NULL WHERE ip=$qip_int AND client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->finish();
		$dbh->disconnect;
	} elsif ( $use_api ) {
		my $ip = Gipfuncs::int_to_ip("$ip_int","$ip_version");
		my $path = '/deleteHostResult/Host';
		my $content = "request_type=deleteHost&ip=$ip&client_name=$client";
		my $value = "hostname";
		my $return = Gipfuncs::make_call_value("$path", "$content", "$value") || "";
    } else {
        $csv_string = "DELETE,$ip_int,,,,,,,,,,,,,,,4";
        $csv_string =~ s/,/","/g;
        $csv_string = '"' . $csv_string . '"' . "\n";
        print CSV $csv_string;
    }
}

sub get_client_id_from_name {
    my ( $name ) = @_;
    my $id;
    my $dbh = mysql_connection();
    my $qname = $dbh->quote( $name );

    my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qname
                    ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $id;
}

sub delete_or_clear {
    my ( $client_id, $ip, $host_hash, $ip_version ) = @_;

	my $ipo = new Net::IP ($ip);
	my $ipo_int = $ipo->intip();
    $ip = ip_compress_address ($ip, 6) if $ip_version eq "v6";
	if ( ! $create_csv ) {
		if ( exists $host_hash->{$ipo_int} ) {
			my $range_id = $host_hash->{$ipo_int}[3];
			my $host_id = $host_hash->{$ipo_int}[1];
		
			# Delete host
			if ( $range_id != -1 ) {
				# reserved range -> update
				clear_ip("$client_id","$ipo_int","$ip_version");
			} else {
				# delete
				delete_ip("$client_id","$ipo_int","$ipo_int","$ip_version");
				
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
								delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip");
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
			print LOG "HOST NOT FOUND - DO NOT DELETE NOTHING: $ip - $ipo_int\n" if $debug > 0;
		} 
	} else {
		$csv_string = "DELETE,$ipo_int,,,,,,,,,,,,,,,4";
        $csv_string =~ s/,/","/g;
        $csv_string = '"' . $csv_string . '"' . "\n";
        print CSV $csv_string;
	}
}

sub delete_custom_host_column_entry {
    my ( $client_id, $host_id ) = @_;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND client_id = $qclient_id"
                                ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
                    ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
        my $ip_int_linked=Gipfuncs::ip_to_int("$linked_ip_old","$ip_version_ip_old") || "";
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
    my $sth = $dbh->prepare("SELECT DISTINCT cce.cc_id,cce.entry,cc.name,cc.column_type_id FROM custom_host_column_entries cce, custom_host_columns cc WHERE  cce.cc_id = cc.id AND host_id = $host_id AND cce.client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

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
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
    my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id AND cc_id=$qcc_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

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
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND entry = $qcc_entry_host AND pc_id = $qpc_id $cc_id_expr") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND pc_id = $qpc_id $cc_id_expr") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

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
					") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
    $sth = $dbh->prepare("SELECT cc.name,cc.id,cc.client_id,pc.id FROM custom_host_columns cc, predef_host_columns pc WHERE cc.column_type_id = pc.id AND (client_id = $qclient_id OR client_id = '9999') ORDER BY cc.id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

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
		print "-M logdir                directory where the log file should be stored\n";
        print "--mail                   send result by mail\n";
        print "--mail_from=mail_address mail sender\n";
        print "--mail_to=mail_address   mail recipient\n";
#        print "-r, --run_once           run only once\n";
        print "--smtp_server=server     SMTP server name or IP\n";
        print "-t, --type               import type [aws|azure|gcp]\n";
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
    my $sth = $dbh->prepare("SELECT red, BM, descr, loc, vigilada, comentario, categoria, ip_version, red_num, rootnet, dyn_dns_updates FROM net WHERE red_num=$qred_num AND client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

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

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    my $entry_found = $sth->fetchrow_array;

    if ( $entry_found ) {
        $sth = $dbh->prepare("UPDATE custom_net_column_entries SET entry=$qentry WHERE cc_id=$qcc_id AND net_id=$qnet_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("INSERT INTO custom_net_column_entries (cc_id,net_id,entry,client_id) VALUES ($qcc_id,$qnet_id,$qentry,$qclient_id)") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_column_id_from_name {
    my ( $client_id, $name ) = @_;
    my $dbh = mysql_connection();
    my $qname = $dbh->quote( $name );
    my $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qname
                    ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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


sub delete_cron_entry {
    my ($id) = @_;

    my $crontab = "/usr/bin/crontab";
    $crontab =~ /^(.*)$/;
	$crontab = $1;

    my $echo = "/bin/echo";
    $echo =~ /^(.*)$/;
	$echo = $1;

    my $grep = "/bin/grep";
    $grep =~ /^(.*)$/;
	$grep = $1;

    my $command = $crontab . ' -l | ' . $grep . ' -v \'#ID: ' . $id . '$\' | ' . $crontab . ' -';
    $command =~ /^(.*)$/;
	$command = $1;

    my $output = `$command 2>&1`;
    if ( $output ) {
        return $output;
    }
}

sub insert_audit_auto {
        my ($client_id,$event_class,$event_type,$event,$update_type_audit,$vars_file) = @_;

        return if $create_csv;

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

        my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,remote_host,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qremote_host,$qclient_id)") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $id = $sth->fetchrow_array;

    $sth->finish();
    $dbh->disconnect;

    return $id;
}

sub get_tag_hash {
    my ( $client_id, $key ) = @_;

    my %values;
    my $ip_ref;
    $key = "id" if ! $key;

    my $dbh = mysql_connection();

    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT id, name, description, color, client_id FROM tag WHERE ( client_id = $qclient_id OR client_id = '9999' ) ORDER BY name"
        ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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


sub fetch_zone {
    my ($scanzones, $default_resolver, $dns_servers, $zone_type, $ip_version)=@_;

    $default_resolver="" if ! $default_resolver;
    my $res;

    if ( $default_resolver eq "yes" ) {
            $res = Net::DNS::Resolver->new(
            retry       => 2,
            udp_timeout => 5,
            recurse     => 1,
            debug       => 0,
            );
    } else {
            $res = Net::DNS::Resolver->new(
            retry       => 2,
            udp_timeout => 5,
            nameservers => [@$dns_servers],
            recurse     => 1,
            debug       => 0,
            );
    }

	my %records_zone;
	foreach my $zone_arr ( @$scanzones ) {
        my $zone_name = $zone_arr->[1];
		print LOG "FETCHING ZONE: $zone_name - @$dns_servers - $default_resolver - $zone_type\n" if $debug;

		my @fetch_zone = $res->axfr("$zone_name");

		my $error = $res->errorstring;
		if ( $error ) {
			print LOG "Error fetchig zone $zone_name: $error\n";
		}

		print LOG "FETCHING ZONE $zone_name: @fetch_zone\n" if $debug;

		my $i=0;
		my $rr;
		my @zone_records;
		foreach $rr (@fetch_zone) {
				$zone_records[$i]=$rr->string;
				print LOG "FOUND RECORD: $zone_records[$i]\n" if $debug;
				$i++;
		}

		if ( $ip_version eq "v4" ) {
			if ( $zone_type eq "A" ) {
				foreach my $rec ( @zone_records ) {
					if ( $rec =~ /^([\w\.-]+)[\s\t]+.+A[\s\t]+(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})/ ) {
						my $ip = $2;
						my $hname = $1;
						$hname =~ s/\.$//;
						print LOG "A RECORD: $hname - $ip\n" if $debug;
						$records_zone{$ip} = $hname;
					}
				}
			} elsif ( $zone_type eq "PTR" ) {
				foreach my $rec ( @zone_records ) {
					if ( $rec =~ /^(.+in-addr.arpa)\.[\s\t]+.+PTR[\s\t]+(.+)$/ ) {
						my $rev = $1;
						my $rev_name = $2;
						$rev_name =~ s/\.$//;
						$rev =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.in-addr.arpa$/;
						my $ip = $4 . "." . $3 . "." . $2 . "." . $1;
						print LOG "PTR RECORD: $rev_name - $ip\n" if $debug;
						$records_zone{$ip} = $rev_name;
					}
				}
			} else {
				print LOG "UNKNOWN ZONE TYPE: $zone_name\n";
				return;
			}
		} else {
			# v6
			if ( $zone_type eq "AAAA" ) {
				foreach my $rec ( @zone_records ) {
                    print LOG "REC AAAA: $rec\n" if $debug;
                    # ns.aws-v6-test.net.   3600    IN  AAAA    2600:1f16:8f8:7e00::50
					if ( $rec =~ /^([\w\.-]+)[\s\t]+.+AAAA[\s\t]+([a-zA-z0-9:]{2,39})$/ ) {
						my $ip = $2;
						my $hname = $1;
						$hname =~ s/\.$//;
						print LOG "AAAA RECORD: $hname - $ip\n" if $debug;

                        $ip=ip_expand_address ($ip,6);

						$records_zone{$ip} = $hname;
					}
				}
			} elsif ( $zone_type eq "PTR" ) {
				foreach my $rec ( @zone_records ) {
                    print LOG "REC V6 PTR: $rec\n" if $debug;
					if ( $rec =~ /^([a-zA-z0-9.]+).ip6/ ) {
						$rec =~ /^([a-zA-z0-9.]+).ip6(.*[\s\t]+)(.*)$/;
                        my $nibbles = $1;
						my $rev_name = $3;
						$rev_name =~ s/\.$//;

                        my @nibbles=split('\.',$nibbles);
                        @nibbles=reverse(@nibbles);
                        my $ip_nibbles="";
                        my $o=0;
                        foreach (@nibbles) {
                            if ( $o == 4 || $o==8 || $o==12 || $o==16 || $o==20 || $o==24 || $o==28 ) {
                                $ip_nibbles .= ":" . $_;
                            } else {
                                $ip_nibbles .= $_;
                            }
                            $o++;
                        }

						print LOG "PTR RECORD: $rev_name - $ip_nibbles\n" if $debug;
						$records_zone{$ip_nibbles} = $rev_name;
					}
				}
			} else {
				print LOG "UNKNOWN ZONE TYPE: $zone_name\n";
				return;
			}
		}
	}

	return %records_zone;
}


sub check_DNS_server_alive {
	my ($ip, $default_resolver, $dns_servers, $ip_version)=@_;

    #check if DNS servers are alive

    my $res_dns;
    my $dns_error = "";

	my @dns_servers;
	if ( $dns_servers ) {
		@dns_servers = @$dns_servers;
	}

    if ( @dns_servers ) {
		print LOG "Checking if DNS server is alive: @dns_servers\n" if $debug;
        $res_dns = Net::DNS::Resolver->new(
        retry       => 2,
        udp_timeout => 5,
        tcp_timeout => 5,
        nameservers => [@$dns_servers],
        recurse     => 1,
        debug       => 0,
        );
    } else {
		print LOG "Checking if DNS server is alive: default resolver\n" if $debug;
        $res_dns = Net::DNS::Resolver->new(
        retry       => 2,
        udp_timeout => 5,
        tcp_timeout => 5,
        recurse     => 1,
        debug       => 0,
		);
	}

    my $ptr_query=$res_dns->query("$ip");

    if ( ! $ptr_query) {
        if ( $res_dns->errorstring eq "query timed out" ) {
            print LOG "$ip: No DNS server available (1): " . $res_dns->errorstring . "\n\n";
            print "No DNS server available (1): " . $res_dns->errorstring . "\n\n" if $verbose;
            return;
        }
    }

    my $used_nameservers = $res_dns->nameservers;

    my $all_used_nameservers = join (" ",$res_dns->nameserver());

    if ( $used_nameservers eq "0" ) {
        print LOG "No DNS server available (2)\n\n";
        print "No DNS server available (2)\n\n" if $verbose;
        return;
    }

	return 1;
}

sub resolv_DNS_PTR_entry {
	my ($ip_ad, $dns_servers)=@_;

    my $ptr_query="";
    my $dns_result="";
	my $res_dns = "";

	my @dns_servers;
	if ( $dns_servers ) {
		@dns_servers = @$dns_servers;
	}

#    if ( $default_resolver eq "yes" ) {
#        $res_dns = Net::DNS::Resolver->new(
#        retry       => 2,
#        udp_timeout => 5,
#        tcp_timeout => 5,
#        recurse     => 1,
#        debug       => 0,
#        );
#    } else {
#        $res_dns = Net::DNS::Resolver->new(
#        retry       => 2,
#        udp_timeout => 5,
#        tcp_timeout => 5,
#        nameservers => [@dns_servers],
#        recurse     => 1,
#        debug       => 0,
#        );
#    }

    if ( @dns_servers ) {
		print LOG "RESOLVING IP: $ip_ad using DNS servers @dns_servers\n" if $verbose;
        $res_dns = Net::DNS::Resolver->new(
        retry       => 2,
        udp_timeout => 5,
        tcp_timeout => 5,
        nameservers => [@$dns_servers],
        recurse     => 1,
        debug       => 0,
        );
    } else {
		print LOG "RESOLVING IP: $ip_ad using DNS default resolver\n" if $verbose;
        $res_dns = Net::DNS::Resolver->new(
        retry       => 2,
        udp_timeout => 5,
        tcp_timeout => 5,
        recurse     => 1,
        debug       => 0,
		);
	}

    $ptr_query = $res_dns->send("$ip_ad");

    my $dns_error = $res_dns->errorstring;

    if ( $dns_error eq "NOERROR" ) {
        if ($ptr_query) {
            foreach my $rr ($ptr_query->answer) {
                next unless $rr->type eq "PTR";
                $dns_result = $rr->ptrdname;
            }
        }
    }

	return $dns_result;
}


sub get_dns_server {
	my ($red_num) = @_;

    return if $ignore_dns;

    my @dns_servers;

    my $dns_server_group_id = Gipfuncs::get_custom_column_entry("$client_id","$red_num","DNSSG") || "";
    print LOG "DNS Server Group: $dns_server_group_id\n" if $debug;
    my $dns_server_group_name;
    my @dns_server_group_values;
    if ( $dns_server_group_id ) {
        # check for DNS server group
        @dns_server_group_values = Gipfuncs::get_dns_server_group_from_id("$client_id","$dns_server_group_id");
    }
    if ( @dns_server_group_values ) {

        $default_resolver = 0;

        $dns_server_group_name = $dns_server_group_values[0]->[0];
        push @dns_servers, $dns_server_group_values[0]->[2] if $dns_server_group_values[0]->[2];
        push @dns_servers, $dns_server_group_values[0]->[3] if $dns_server_group_values[0]->[3];
        push @dns_servers, $dns_server_group_values[0]->[4] if $dns_server_group_values[0]->[4];
        print "DNS Server group: $dns_server_group_name\n" if $debug;
    } else {
        push @dns_servers, $client_entries[0]->[21] if $client_entries[0]->[21];
        push @dns_servers, $client_entries[0]->[22] if $client_entries[0]->[22];
        push @dns_servers, $client_entries[0]->[23] if $client_entries[0]->[23];
    }

    print LOG "get_dns_server: @dns_servers - " . scalar(@dns_servers) . "\n" if @dns_servers;

	return @dns_servers;
}



sub get_dns_entry {
	my ( $ip, $ip_version, $dns_name, $red_num, $generic_auto ) = @_;

    my @dns_servers;
    my $dns_servers;
    if ( ! $networks_dns_server_hash{"$red_num"} && ! $networks_dns_checked_hash{"$red_num"} ) {
		$networks_dns_checked_hash{"$red_num"}++;
        @dns_servers = get_dns_server("$red_num");
        $networks_dns_server_hash{"$red_num"} = \@dns_servers;
        $dns_servers = \@dns_servers;
    } else {
        $dns_servers = $networks_dns_server_hash{"$red_num"} || ();
    }

	print LOG "DNS servers $ip: @$dns_servers\n";

    if ( ! $networks_dns_server_ok_hash{$red_num} ) {
		if ( $azure_dns || $aws_dns || $gcp_dns  ) {
			$networks_dns_server_ok_hash{$red_num}++;
		} else {
			$networks_dns_server_ok_hash{$red_num} = check_DNS_server_alive("$ip", "$default_resolver", $dns_servers, "$ip_version") || "";
			print LOG "DNS CHECK: $networks_dns_server_ok_hash{$red_num} - $ip - $default_resolver - @$dns_servers\n";
		}
    }

    if ( $use_zone_transfer && $networks_dns_server_ok_hash{$red_num} && ! exists $networks_dns_zone_hash{$red_num} ) {
        # fetch scam zones for this network

		my @scanazones = Gipfuncs::get_network_scan_zones("$red_num","A");
		my $sca;
		$sca = $scanazones[0] if @scanazones;
		my @scanptrzones = Gipfuncs::get_network_scan_zones("$red_num","PTR");
		my $scptr;
		$scptr = $scanptrzones[0] if @scanptrzones;
		my @scanaaaazones = Gipfuncs::get_network_scan_zones("$red_num","AAAA");

        print LOG "ScanAZonese: @scanazones\n" if $debug;
        print LOG "ScanAAAAZonese: @scanaaaazones\n" if $debug;
        print LOG "ScanPTRZones: @scanptrzones\n" if $debug;

        if ( ! @scanazones && ! @scanptrzones ) {
            print "$ip - $red_num: No zones found - skipping DNS query\n" if $debug;
            print LOG "$ip - $red_num: No zones found - skipping DNS query\n" if $debug;
            my %empty_hash;
            $networks_dns_zone_hash{$red_num} = \%empty_hash;
        } else {
            my %records_zone;
            if ( $ip_version eq "v6" ) {
                print LOG "Fetching zone - $scanaaaazones[0]->[0]\n" if @scanaaaazones;
                %records_zone = fetch_zone(\@scanaaaazones, "$default_resolver", $dns_servers, "AAAA", "$ip_version") if @scanaaaazones;
            } else {
                %records_zone = fetch_zone(\@scanazones, "$default_resolver", $dns_servers, "A", "$ip_version") if @scanazones;
            }
            my %reverse_records_zone = fetch_zone(\@scanptrzones, "$default_resolver", $dns_servers, "PTR", "$ip_version") if @scanptrzones;

            my $zone_records_hash_ref = Gipfuncs::compare_hashes(\%records_zone, \%reverse_records_zone, $ip_version);
            $networks_dns_zone_hash{$red_num} = $zone_records_hash_ref;
        }
    }

	my $dns_name_query = "";
    if ($networks_dns_server_ok_hash{$red_num} ) {
        if ( ! $dns_name || $dns_name =~ /${generic_auto}/ ) {
            if ( $azure_dns ) {
				$dns_name_query = $values_dns_azure->{$ip} if $values_dns_azure->{$ip};
                print LOG "FOUND DNS ENTRY AZURE DNS: $ip - $dns_name_query\n" if $debug;
            } elsif ( $aws_dns ) {
				$dns_name_query = $values_dns_aws->{$ip} if $values_dns_aws->{$ip};
                print LOG "FOUND DNS ENTRY AWS DNS: $ip - $dns_name_query\n" if $debug;
            } elsif ( $gcp_dns ) {
				$dns_name_query = $values_dns_gcp->{$ip} if $values_dns_gcp->{$ip};
                print LOG "FOUND DNS ENTRY GCP DNS: $ip - $dns_name_query\n" if $debug;

            } elsif ( $use_zone_transfer ) {
                print LOG "DNS ZONE SEARCH: $ip\n" if $debug;
                my $zone_records_hash_ref = $networks_dns_zone_hash{$red_num};
                print LOG "DUMPER ZONE: " . Dumper($zone_records_hash_ref) . "\n" if $debug;
                $dns_name_query = $zone_records_hash_ref->{$ip} if $zone_records_hash_ref->{$ip};

            } else {
                $dns_name_query = resolv_DNS_PTR_entry("$ip", $dns_servers) || "";
            }

            print LOG "DNS result: $ip - $dns_name - $dns_name_query\n" if $debug;
        }
    }

	return $dns_name_query;
}

sub get_data_file {
	my ( $data_file ) = @_;

	my $output = "";
    open(DATA_FILE,"<$data_file") or Gipfuncs::exit_error("Cannot execute open $data_file: $!", "$gip_job_status_id", 4);
    while (<DATA_FILE>) {
        $output .= $_;
    }
    close DATA_FILE;

	return $output;
}

sub gip_decode_json {
	my ( $output_json ) = @_;

	my $this_function = (caller(1))[3];

	my $text = eval { decode_json($output_json) };
    if($@) {
        print LOG "JSON: $output_json\n$@" if $debug;
        Gipfuncs::exit_error("ERROR - command returned invalid JSON ($this_function)", "$gip_job_status_id", 4);
    }

	print LOG "$this_function: JSON:\n " .  Dumper($text) . "\n" if $debug;

	return $text;
}

sub insert_predef_host_column_value {
	my ( $client_id, $cc_name, $host_id, $entry ) = @_;

	my ($cc_id, $pc_id);
    my $dbh = mysql_connection();
	my $qcc_name = $dbh->quote( $cc_name );

    my $sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcc_name
                    ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $cc_id = $sth->fetchrow_array;

	if ( $cc_id ) {
		my $sth = $dbh->prepare("SELECT id FROM predef_host_columns WHERE name=$qcc_name
						") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$pc_id = $sth->fetchrow_array;


		my $qclient_id = $dbh->quote( $client_id );
		my $qhost_id = $dbh->quote( $host_id );
		my $qentry = $dbh->quote( $entry );
		my $qcc_id = $dbh->quote( $cc_id );
		my $qpc_id = $dbh->quote( $pc_id );

		$sth = $dbh->prepare("INSERT INTO custom_host_column_entries (cc_id,pc_id,host_id,entry,client_id) VALUES ($qcc_id,$pc_id,$qhost_id,$qentry,$qclient_id)"
				) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	}

	$sth->finish();
	$dbh->disconnect;
}


sub update_predef_host_column_value {
	my ( $client_id, $cc_name, $host_id, $entry ) = @_;

	my ($cc_id, $pc_id);
    my $dbh = mysql_connection();
	my $qcc_name = $dbh->quote( $cc_name );

    my $sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcc_name
                    ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $cc_id = $sth->fetchrow_array;

	if ( $cc_id ) {
		my $sth = $dbh->prepare("SELECT id FROM predef_host_columns WHERE name=$qcc_name
						") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$pc_id = $sth->fetchrow_array;


		my $qclient_id = $dbh->quote( $client_id );
		my $qhost_id = $dbh->quote( $host_id );
		my $qentry = $dbh->quote( $entry );
		my $qcc_id = $dbh->quote( $cc_id );
		my $qpc_id = $dbh->quote( $pc_id );

		$sth = $dbh->prepare("UPDATE custom_host_column_entries SET entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id AND cc_id=$qcc_id"
				) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	}

	$sth->finish();
	$dbh->disconnect;
}

