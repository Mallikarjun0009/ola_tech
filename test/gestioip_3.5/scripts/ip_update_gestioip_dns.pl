#!/usr/bin/perl -w


# Copyright (C) 2015 Marc Uebel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# ip_update_gestioip_dns.pl Version 3.5.7.1 20210816
# not compatible with version <= 3.5.3

# script para actualizar la BBDD del sistema GestioIP against the DNS

# This scripts synchronizes only the networks of GestioIP with marked "sync"-field
# see documentation for further information (www.gestioip.net)


# Usage: ./ip_update_gestioip_dns.pl --help

# execute it from cron. Example crontab:
# 30 10 * * * /usr/share/gestioip/bin/ip_update_gestioip_dns.pl -C 192.169.0.0/24 > /dev/null 2>&1


use strict;
use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
    $dir = $Bin;
    $gipfunc_path = $dir . '/include';
}

use lib "$gipfunc_path";
use Gipfuncs;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use DBI;
use Time::Local;
use Time::HiRes qw(sleep);
use Date::Calc qw(Add_Delta_Days); 
use Date::Manip qw(UnixDate);
use Net::IP;
use Net::IP qw(:PROC);
#use Net::Ping::External qw(ping);
#use Mail::Mailer;
use Socket;
use Parallel::ForkManager;
use Fcntl qw(:flock);
use Net::DNS;
use POSIX;
use HTTP::Cookies;
use LWP::UserAgent;
use XML::LibXML;
use HTTP::Request::Common;


#sub LWP::UserAgent::get_basic_credentials {
#    warn "@_\n";
#}
use Data::Dumper;


my $VERSION="3.5.0";
my $CHECK_VERSION="3";

$dir =~ /^(.*)\/bin/;
$base_dir=$1;

my $ping_timeout = 4;
my $ping_count = 1;

my ( $disable_audit, $test, $help, $version_arg, $location_args, $ignore_dns );
my $config_name="";
my $network_file="";
my $network_list="";
my $only_added_mail="";
my $run_once="";

our $verbose = 0;
our $debug = 0;
our $client = "";
our $create_csv = "";
our $ignore_generic_auto = "no";
our $smtp_server = "";
our $mail_from = "";
our $mail_to = "";
our $changes_only = "";
our $log = "";
our $mail = "";
our $document_root = "";
my ( $logdir, $actualize_ipv4, $actualize_ipv6, $generic_dyn_host_name, $ignorar, $dyn_ranges_only, $max_sinc_procs, $tag, $ip_range, $use_zone_transfer, $gip_job_id, $user, $combined_job, $delete_down_hosts, $location_scan);
$logdir=$actualize_ipv4=$actualize_ipv6=$generic_dyn_host_name=$ignorar=$dyn_ranges_only=$max_sinc_procs=$debug=$tag=$ip_range=$use_zone_transfer=$combined_job=$gip_job_id=$delete_down_hosts=$location_scan=$create_csv="";

GetOptions(
    "log=s"=>\$log,
    "config_file_name=s"=>\$config_name,
    "changes_only!"=>\$changes_only,
    "combined_job!"=>\$combined_job,
    "create_csv!"=>\$create_csv,
    "CSV_networks=s"=>\$network_list,
    "disable_audit!"=>\$disable_audit,
    "delete_down_hosts!"=>\$delete_down_hosts,
    "document_root=s"=>\$document_root,
    "Location=s"=>\$location_args,
    "Location_scan=s"=>\$location_scan,
    "mail!"=>\$mail,
	"smtp_server=s"=>\$smtp_server,
	"mail_from=s"=>\$mail_from,
	"mail_to=s"=>\$mail_to,
    "Network_file=s"=>\$network_file,
    "only_added_mail!"=>\$only_added_mail,
    "help!"=>\$help,
    "ignore_dns!"=>\$ignore_dns,
    "range=s"=>\$ip_range,
    "run_once!"=>\$run_once,
    "tag=s"=>\$tag,
    "user=s"=>\$user,
    "verbose!"=>\$verbose,
    "Version!"=>\$version_arg,
    "x!"=>\$debug,
    "ztest!"=>\$test,

    "A=s"=>\$client,
    "B=s"=>\$ignore_generic_auto,
#        "C=s"=>\$descend,
    "M=s"=>\$logdir,
    "T=s"=>\$actualize_ipv4,
    "O=s"=>\$actualize_ipv6,
    "P=s"=>\$generic_dyn_host_name,
    "Q=s"=>\$ignorar,
    "R!"=>\$dyn_ranges_only,
    "S=s"=>\$max_sinc_procs,
    "W=s"=>\$gip_job_id,
    "Z!"=>\$use_zone_transfer,


) or print_help("Argument error");

$debug=0 if ! $debug;
$verbose = 1 if $debug;
$mail=1 if $only_added_mail;

my $client_id;

my $vars_file=$base_dir . "/etc/vars/vars_update_gestioip_en";

my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip);

my $enable_audit = "1";
$enable_audit = "0" if $test || $disable_audit;

if ( $document_root && ! -r "$document_root" ) {
    print "document_root not readable\n";
    exit 1;
}

my $job_name = "";
if ( ! $create_csv ) {

	# Get mysql parameter from priv
	($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = Gipfuncs::get_db_parameter();

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
	$client_id=get_client_id_from_name("$client") || "";

	if ( ! $client_id ) {
		print "$client: client not found\n";
		exit 1;
	}


	if ( $gip_job_id ) {

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
			$job_name = Gipfuncs::get_job_name("$gip_job_id");
			my $audit_type="176";
			my $audit_class="33";
			my $update_type_audit="2";

			my $event="$job_name ($gip_job_id)";
			insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
		}
	}
}

my $exit_message = "";

my $start_time=time();

my $datetime;
my $gip_job_status_id = "";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "ip_update_gestioip_dns");

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or Gipfuncs::exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;

my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime ip_update_gestioip_dns.pl $gip_job_id_message\n\n";

my $logfile_name = $log;
$logfile_name =~ s/^(.*\/)//;

my $delete_job_error;
if ( $gip_job_id && ! $combined_job && ! $create_csv) {
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
                Gipfuncs::exit_error("ERROR: Job not deleted from crontab: $delete_job_error", "$gip_job_status_id", 4 );
            } else {
                exit;
            }
        }
    }
    # status 2: running
    $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
}

$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
	$exit_message = "Can't find configuration file \"$config_name\"";
	Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
}
my $conf = $base_dir . "/etc/" . $config_name;

our %params = Gipfuncs::get_params("$conf");
#print "TEST CONF: $conf\n";
#
#open(VARS,"<$conf") or Gipfuncs::exit_error("Can not open $conf: $!", "$gip_job_status_id", 4);
#while (<VARS>) {
#chomp;
#s/#.*//;
#s/^\s+//;
#s/\s+$//;
#next unless length;
#my ($var, $value) = split(/\s*=\s*/, $_, 2);
#    $params{$var} = $value;
#}
#close VARS;


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
	my $csv_file = $base_dir . "/var/data/csv_host_dns_" . $client_id . ".csv";
	$csv_string = "action,ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,client_id,ip_version,dyn_dns_updates,update_type_audit\n";
	open(CSV,">$csv_file") or Gipfuncs::exit_error("Can not open csv_file $csv_file: $!", "", 4);
	print CSV $csv_string;
}


if ( $help ) { print_help(); }
if ( $version_arg ) { print_version(); }
if ( $test && ! $verbose ) {
	$exit_message = "test option needs the -v arg";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
	} else {
		print_help("$exit_message");
	}
}

$delete_down_hosts = "yes" if $delete_down_hosts;
#$delete_down_hosts = $params{delete_dns_hosts_down_all} if ! $delete_down_hosts;

my $gip_version = Gipfuncs::get_version();

my $global_dyn_dns_updates_enabled = Gipfuncs::get_dyn_dns_updates_enabled();

if ( $gip_version !~ /$CHECK_VERSION/ ) {
	$exit_message= "Script and GestioIP version are not compatible - GestioIP version: $gip_version - script version: $VERSION";
	Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
}

my %lang_vars;


open(LANGVARS,"<$vars_file") or Gipfuncs::exit_error("Can not open $vars_file: $!", "$gip_job_status_id", 4);
while (<LANGVARS>) {
chomp;
s/#.*//;
s/^\s+//;
s/\s+$//;
next unless length;
my ($var, $value) = split(/\s*=\s*/, $_, 2);
$lang_vars{$var} = $value;
}
close LANGVARS;

$params{pass_gestioip} = "" if ! $params{pass_gestioip};
if ( ! $pass_gestioip && $params{pass_gestioip} !~ /.+/ && ! $create_csv ) {
	$exit_message = "ERROR - $lang_vars{no_pass_message} $conf)";
	Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
}

### PING HISTORY PATCH to add ping status changes to host history####
### require new event_type: INSERT INTO event_types (id,event_type) VALUES (100,"ping status changed");
### disabled 0; enabled 1;
my $enable_ping_history=1;
my $update_type_audit="4";

#$ignore_generic_auto = $ignore_generic_auto || $params{ignore_generic_auto};
if ( $ignore_generic_auto && $ignore_generic_auto !~ /^yes|no/i ) {
    $exit_message = "ignore_generic_auto (-B) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}

my $lockfile = $base_dir . "/var/run/" . $client . "_ip_update_gestioip_dns.lock";

no strict 'refs';
open($lockfile, '<', $0) or Gipfuncs::exit_error("Unable to create lock file: $!", "$gip_job_status_id", 4);
use strict;

unless (flock($lockfile, LOCK_EX|LOCK_NB)) {
	$exit_message = "$0 is already running - exiting";
	Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 6);
}

#my $ipv4 = $actualize_ipv4 || $params{actualize_ipv4_dns};
my $ipv4 = $actualize_ipv4;
if ( $ipv4 && $ipv4 !~ /^yes|no/i ) {
    $exit_message = "actualize_ipv4 (-T) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
$ipv4="yes" if $ipv4 !~ /^no$/i;

#my $ipv6 = $actualize_ipv6 || $params{actualize_ipv6_dns};
my $ipv6 = $actualize_ipv6;
if ( $ipv6 && $ipv6 !~ /^yes|no/i ) {
    $exit_message="actualize_ipv4 (-O) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
$ipv6="yes" if $ipv6 !~ /^no$/i;

#TAGs
my @tag;
my $tag_ref = "";
if ( $tag ) {
	$tag =~ s/\s//g;
    @tag = split(",", $tag);
    $tag_ref = \@tag;
}

#$generic_dyn_host_name = $generic_dyn_host_name || $params{'generic_dyn_host_name'};
$generic_dyn_host_name= "_NO_GENERIC_DYN_NAME_" if ! $generic_dyn_host_name;
$generic_dyn_host_name =~ s/,/|/g;

my @mail_to;
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


my $count_entradas_dns=0;
my $count_entradas_dns_timeout=0;

print LOG "\n######## Synchronization against DNS ($datetime) ########\n\n";
if ( $test ) {
    print LOG "\n--- $lang_vars{test_mod_message} ---\n";
    print "\n--- $lang_vars{test_mod_message} ---\n";
}

my @vigilada_redes=();
my $redes_hash=get_redes_hash_key_red("$client_id");

if (($network_file && $network_list) || ($network_file && $tag) || ($network_list && $tag) || ($network_list && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
if (($ip_range && $network_list) || ($ip_range && $network_file) || ($ip_range && $tag) || ($ip_range && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
if (($location_scan && $network_list) || ($location_scan && $network_file) || ($location_scan && $tag) || ($ip_range && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}

$network_file = "$base_dir/var/data/$network_file" if $network_file;

my %ip_range_ips;
my $first_ip_int_ip_range = "";
my $last_ip_int_ip_range = "";
my %red_ip_range_int_ips;
my $db_locations = Gipfuncs::get_loc_hash("$client_id");
my $host_categories_hash = Gipfuncs::get_cat_hash("$client_id");

if ( $network_file || $network_list) {
    my @pnetworks=();

    if ( $network_list ) {
        @pnetworks=split(",",$network_list);

        print "Reading networks from csv list...\n" if $verbose;
        print LOG  "Reading networks from csv list...\n";
            

    } elsif ( $network_file ) {
        open(NETWORKS,"<$network_file") or Gipfuncs::exit_error("Can not open $network_file: $!", "$gip_job_status_id", 4);
        while (<NETWORKS>) {
            push @pnetworks,"$_";
        }
        close NETWORKS;

        print "Reading networks from $network_file...\n" if $verbose;
        print LOG  "Reading networks from $network_file...\n";
    }

    my $network_count=0;
    foreach (@pnetworks) {
        chomp;
        if ( $_ !~ /^([0-9a-fA-F:.]{3,47})\/(\d{1,3})$/ ) {
            print "Network format invalid: $_ - $lang_vars{ignorado_message}\n" if $verbose;
            print LOG "Network format invalid: $_ - $lang_vars{ignorado_message}\n";
            next;
        }
        $_ =~ /^([0-9a-fA-F:.]{3,47})\/(\d{1,3})$/;
        my $red=$1;
        if ( ! $red ) {
            print "Network format invalid: $_ - $lang_vars{ignorado_message}\n" if $verbose;
            print LOG "Network format invalid: $_ - $lang_vars{ignorado_message}\n";
            next;
        }
        my $BM=$2;
        if ( ! $BM ) {
            print "Bitmask format invalid: $_ - $lang_vars{ignorado_message}\n" if $verbose;
            print LOG "Bitmask format invalid: $_ - $lang_vars{ignorado_message}\n";
            next;
        }

        if ( $_ =~ /:/ ) {
            $red= ip_expand_address ($red,6);
        }

        if ( ${$redes_hash}{$red} ) {
            my $rBM=${$redes_hash}{$red}->[1];
            next if $rBM ne $BM;
            my $rred_num=${$redes_hash}{$red}->[0];
            my $rloc_id=${$redes_hash}{$red}->[10];
            my $rdyn_dns_updates=${$redes_hash}{$red}->[11];
            my @red_arr=("$red","$BM","$rred_num","$rloc_id","$rdyn_dns_updates");
            push (@vigilada_redes,\@red_arr);

            $network_count++;
        } else {
            print "Network not found in database: $red/$BM - $lang_vars{ignorado_message}\n" if $verbose;
            print LOG  "Network not found in database: $red/$BM - $lang_vars{ignorado_message}\n";
        }
    }
#	close NETWORKS;
    print "Found $network_count networks to process\n" if $verbose;

    if ( $network_count == 0 ) {
        $exit_message = "Found $network_count networks to process";
		Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 3, "OK");
    }

} elsif ( $ip_range ) {
    my $ip_version;
    my ($ip1, $ip2);
    $ip_range =~ s/\s//g;

    if ( $ip_range =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})-(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/ ) {
        $ip_range =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})-(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/;
        $ip1 = $1;
        $ip2 = $2;
        $ip_version = "v4";
    } elsif ( $ip_range =~ /^([0-9a-fA-F:]{3,47})-([0-9a-fA-F:]{3,47})$/ ) {
        $ip_range =~ /^([0-9a-fA-F:]{3,47})-([0-9a-fA-F:]{3,47})$/;
        $ip1 = $1;
        $ip2 = $2;
        $ip_version = "v6";
    } else {
        $exit_message = "range must be introduced in the format --range=IP1-IP2. Ejemplo: --range=1.1.1.3-1.1.1.10";
        if ( $gip_job_status_id ) {
            Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
        } else {
            print_help("$exit_message");
        }
    }

    if ( ! $ip1 || ! $ip2 ) {
        $exit_message = "range must be introduced in the format --range=IP1-IP2. Ejemplo: --range=1.1.1.3-1.1.1.10";
        if ( $gip_job_status_id ) {
            Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
        } else {
            print_help("$exit_message");
        }
    }

    my $err;
    my $ipob = new Net::IP ("$ip1 - $ip2") or $err = "Can not create range $ip1 - $ip2\n";
    if ( $err ) {
        $exit_message = "$err";
        Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
    }

    $first_ip_int_ip_range = ip_to_int("$ip1","$ip_version");
    $last_ip_int_ip_range = ip_to_int("$ip2","$ip_version");
    $first_ip_int_ip_range = Math::BigInt->new("$first_ip_int_ip_range");
    $last_ip_int_ip_range = Math::BigInt->new("$last_ip_int_ip_range");

    # OK
    my @values_host_redes = Gipfuncs::get_host_redes_no_rootnet("$client_id");

    my ($red, $BM, $red_num);
    $red=$BM=$red_num="";
    my $red_num_old = "";
    do {
        my $r_ip = $ipob->ip();
        my $r_ip_int;
        if ( $ip_version eq "v4") {
            $r_ip_int=ip_to_int("$r_ip","$ip_version") if $ip_version eq "v4";
            $ip_range_ips{$r_ip_int}++;
        } else {
            $r_ip= ip_expand_address ($r_ip,6);
            $ip_range_ips{$r_ip}++;
        }

        $red_num_old = $red_num;

        ($red, $BM, $red_num) = get_host_red_num("$client_id", \@values_host_redes, "$r_ip", "$ip_version", "$red", "$BM", "$red_num" );

        print LOG "$r_ip: no red ID found - ignored\n" if ! $red_num && $verbose;
        print "$r_ip: no red ID found - ignored\n" if ! $red_num && $verbose;

        if ( $red_num ) {
            my @red_arr=("$red","$BM","$red_num","-1","");
            push (@vigilada_redes,\@red_arr) if $red_num ne $red_num_old;
        }

    } while (++$ipob);

    print "Found addresses from " . scalar @vigilada_redes . " networks\n" if $verbose;
    print LOG "Found addresses from " . scalar @vigilada_redes . " networks\n" if $verbose;

} elsif ( $location_scan ) {
    $location_scan =~ s/^\s+//g;
    $location_scan =~ s/\s+$//g;
    $location_scan =~ s/,\s+/,/g;
    my @location_array_names_scan = split /,/, $location_scan;
    my $location_scan_ids = "";
    my $location_scan_locs = "";
    foreach ( @location_array_names_scan ) {
        if ( defined($db_locations->{$_} )) {
            $location_scan_ids .= "," .  $db_locations->{$_};
            $location_scan_locs .= "," .  $_;
        } else {
            print "\nWARNING: Site not found: $_: ignored\n" if $verbose;
            print LOG "\nWARNING: Site not found: $_: ignored\n";
        }
        $location_scan_ids =~ s/^,//;
        $location_scan_locs =~ s/^,//;
    }
	my $loc_vals = $location_scan_ids;
	$loc_vals = $location_scan_locs if $create_csv;

#    @vigilada_redes=get_vigilada_redes("$client_id", "", "v4", "", "$loc_vals");
    @vigilada_redes=Gipfuncs::get_vigilada_redes("$client_id", "", "", "", "$loc_vals");

} elsif ( $ipv4 eq "yes" && $ipv6 eq "no" ) {
    @vigilada_redes=Gipfuncs::get_vigilada_redes("$client_id", "", "v4", $tag_ref);

} elsif ( $ipv4 eq "no" && $ipv6 eq "yes" ) {
    @vigilada_redes=Gipfuncs::get_vigilada_redes("$client_id", "", "v6", $tag_ref);

} else {
    @vigilada_redes=Gipfuncs::get_vigilada_redes("$client_id", "", "", $tag_ref);

}

my %location_ids_args=();
my @location_array_names=();
$location_args="" if ! $location_args;
#my $locations_conf=$params{process_only_locations} || "";
my $process_locations=$location_args || "";
#if ( $process_locations ) {
#    $process_locations=$process_locations . ","  . $locations_conf if $process_locations;
#} else {
#    $process_locations=$locations_conf if $locations_conf;
#}


$process_locations =~ s/^\s+//g if $process_locations;
$process_locations =~ s/\s+$//g if $process_locations;
$process_locations =~ s/,\s+/,/g if $process_locations;
if ( $process_locations ) {
	# filter vigilada_redes for networks from $process_locations
    my @location_array_names = split /,/, $process_locations;
    foreach ( @location_array_names ) {
        if ( ! defined($db_locations->{$_} )) {
            $exit_message = "\nLocation \"$_\" doesn't exists - location must be equal to the location in the GestioIP database";
			Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
        }
        $location_ids_args{$db_locations->{$_}}="1";
    }

    my @vigilada_redes_new=();
    foreach my $ele(@vigilada_redes) {
        my $loc_id_check=@{$ele}[3];
        if ( exists($location_ids_args{$loc_id_check}) ) {
            push @vigilada_redes_new,$ele;
        }
        
    }
    @vigilada_redes=@vigilada_redes_new;
}


if ( ! $vigilada_redes[0] ) {
    my $location_arg_message="";
    $location_arg_message="(for locations \"$location_args\")" if $location_args;
    $exit_message = "$lang_vars{no_sync_redes} $location_arg_message";
	Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4, "OK");
}

my @values_ignorar;
#$ignorar = $ignorar || $params{'ignorar'};
if ( $ignorar ) {
    @values_ignorar=split(",",$ignorar);
} else {
    $values_ignorar[0]="__IGNORAR__";
}

my @linked_cc_id=get_custom_host_column_ids_from_name("$client_id","linked IP");
my $linked_cc_id=$linked_cc_id[0]->[0] || "";

my @client_entries=Gipfuncs::get_client_entries("$client_id");

my %res_sub;
my %res;

my @zone_records;
my %zone_records_hash;

my $l=0;
foreach (@vigilada_redes) {

    my $default_resolver = $client_entries[0]->[20];

    my $red="$vigilada_redes[$l]->[0]";
    my $BM="$vigilada_redes[$l]->[1]";
    my $red_num="$vigilada_redes[$l]->[2]";
    my $dyn_dns_updates="";
    # set only dyn_dns_updates if globaly enabled 
    $dyn_dns_updates=$vigilada_redes[$l]->[4] if $global_dyn_dns_updates_enabled eq "yes";

    my @dns_servers;

    my $dns_server_group_id = Gipfuncs::get_custom_column_entry("$client_id","$red_num","DNSSG") || "";
    print "DNS Server Group: $dns_server_group_id\n" if $debug;
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

    print "\n$red/$BM\n" if $verbose;
    print LOG "\n$red/$BM\n";
    print "using DNS server group $dns_server_group_name\n" if $dns_server_group_name && $verbose;
    print LOG "using DNS server group $dns_server_group_name\n" if $dns_server_group_name && $verbose;

    # dyn_ranges_only can not be set by scheduled_job_form, only by config file or manually via command line argument
    if ( $dyn_ranges_only ) {
        $dyn_ranges_only = "yes";
    } elsif ( $params{dyn_rangos_only} && $params{dyn_rangos_only} eq "yes" ) {
        $dyn_ranges_only = "yes";
    } else {
        $dyn_ranges_only = "";
    }

    if ( $dyn_ranges_only eq "yes" ) {
        print "\n($lang_vars{sync_only_rangos_message})\n\n" if $verbose;
        print LOG "\n($lang_vars{sync_only_rangos_message})\n\n";
    } else {
        print "\n" if $verbose;
    }

    my @reserved_ranges_found = ();
    if ( $dyn_ranges_only eq "yes" ) {
         @reserved_ranges_found=check_for_reserved_range("$client_id","$red_num");
    }

    if ( ! $reserved_ranges_found[0] && $dyn_ranges_only eq "yes" ) {
        print "$lang_vars{no_range_message}\n\n";
        $l++;
        next;
    }

    my %cc_values=get_custom_host_column_values_host_hash("$client_id","$red_num");

    my $descr = ${$redes_hash}{$red}->[2];
    my $loc_id = ${$redes_hash}{$red}->[10];
    my $ip_version = ${$redes_hash}{$red}->[7];

    if ( ! $ipv4 && $ip_version eq "v4" ) {
        $l++;
        next;
    } elsif ( ! $ipv6 &&  $ip_version eq "v6" ) {
        $l++;
        next;
    }


    if ( $BM > 30 && $ip_version eq "v4" ) {
        print "Bitmask > 30 - $lang_vars{ignorado_message}\n" if $verbose;
        print LOG "Bitmask > 30 - $lang_vars{ignorado_message}\n";
        $l++;
        next;
    }

    my $audit_type="23";
    my $audit_class="2";
    my $event="$red/$BM";
    insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";

    my $smallest_bm4="16";
    my $smallest_bm6="64";

    my $zone_name = Gipfuncs::get_custom_column_entry("$client_id","$red_num","DNSZone") || "";
    my $reverse_zone_name = Gipfuncs::get_custom_column_entry("$client_id","$red_num","DNSPTRZone") || "";
    print "Zone/Reverse-Zone: $zone_name - $reverse_zone_name\n" if $debug;
    print LOG "Zone/Reverse-Zone: $zone_name - $reverse_zone_name\n" if $debug;

    if ( $use_zone_transfer && ! $zone_name && ! $reverse_zone_name ) {
        print "No zones for this network found - skipping network\n" if $verbose;
        $l++;
        next;
    }

    my %records_zone=();
    my %reverse_records_zone=();
    

    if ( $ip_version eq "v6" ) {
        if ( ! $reverse_zone_name ) { # TEST
            my ($nibbles, $rest);
            my $red_exp = ip_expand_address ($red,6) if $ip_version eq "v6";
            my $nibbles_pre=$red_exp;
            $nibbles_pre =~ s/://g;
            my @nibbles=split(//,$nibbles_pre);
            my @nibbles_reverse=reverse @nibbles;
            $nibbles="";
            $rest=128-$BM;
            my $red_part_helper = ($rest+1)/4;
            $red_part_helper = ceil($red_part_helper);
            my $n=1;
            foreach my $num (@nibbles_reverse ) {
                if ( $n<$red_part_helper ) {
                    $n++;
                    next;		
                } elsif ( $nibbles =~ /\w/) {
                    $nibbles .= "." . $num;
                } else {
                    $nibbles = $num;
                }
                $n++;
            }
            $nibbles .= ".ip6.arpa.";
            $zone_name=$nibbles;
        } 

        @zone_records=fetch_zone("$zone_name","$default_resolver",\@dns_servers);
    } elsif ( $ip_version eq "v4" && $use_zone_transfer ) {
# TEST
        my @x_zone_records=fetch_zone("$zone_name","$default_resolver",\@dns_servers);
        foreach my $rec ( @x_zone_records ) {
            if ( $rec =~ /^([\w\.-]+)[\s\t]+.+A[\s\t]+(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})/ ) {
                my $ip = $2;
                my $hname = $1;
                $hname =~ s/\.$//;
                print LOG "A RECORD: $hname - $ip\n" if $debug;
                $records_zone{$ip} = $hname;
            }

        }
        my @reverse_zone_records=fetch_zone("$reverse_zone_name","$default_resolver",\@dns_servers);
        foreach my $rec ( @reverse_zone_records ) {
            if ( $rec =~ /^(.+in-addr.arpa)\.[\s\t]+.+PTR[\s\t]+(.+)$/ ) {
                my $rev = $1;
                my $rev_name = $2;
                $rev_name =~ s/\.$//;
                $rev =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.in-addr.arpa$/;
                my $ip = $4 . "." . $3 . "." . $2 . "." . $1;
                print LOG "PTR RECORD: $rev_name - $ip\n" if $debug;
                $reverse_records_zone{$ip} = $rev_name;
            }
        }

        my $zone_records_hash_ref = compare_hashes(\%records_zone, \%reverse_records_zone, $ip_version);
        %zone_records_hash = %$zone_records_hash_ref;
    }

	if ((! $zone_records[0] && $ip_version eq "v6") || ( ! %zone_records_hash && $ip_version eq "v4" && $use_zone_transfer)) {
		print LOG "$lang_vars{no_zone_data_message} $zone_name\n";
		print "$lang_vars{no_zone_data_message} $zone_name\n" if $verbose;
		$l++;
		next;
	}


	if ( $ip_version eq "v4" && $BM < $smallest_bm4 ) {
		print LOG "$lang_vars{smalles_bm_manage_message} - Smallest allowed Bitmask: $smallest_bm4 - $lang_vars{ignorado_message}\n\n";
		print "$lang_vars{smalles_bm_manage_message} - Smallest allowed Bitmask: $smallest_bm4 $lang_vars{ignorado_message}\n\n" if $verbose;
		$l++;
		next;
	} elsif ( $ip_version eq "v6" && $BM < $smallest_bm6 ) {
		print LOG "$lang_vars{smalles_bm_manage_message} - Smallest allowed Bitmask: $smallest_bm6 $lang_vars{ignorado_message}\n\n";
		print "$lang_vars{smalles_bm_manage_message} - Smallest allowed Bitmask: $smallest_bm6 $lang_vars{ignorado_message}\n\n" if $verbose;
		$l++;
		next;
	}

	my $redob = "$red/$BM";
	my $host_loc = Gipfuncs::get_loc_from_redid("$client_id","$red_num") || "-1";
	$host_loc = "---" if $host_loc eq "NULL";
	my $host_cat = "---";


	if ( $dyn_ranges_only eq "yes" ) {
		print LOG "\n($lang_vars{sync_only_rangos_message})\n\n";
		print "\n($lang_vars{sync_only_rangos_message})\n\n" if $verbose;;
	} else {
		print LOG "\n";
	}

    my $ipob = new Net::IP ($redob) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $red/$BM\n";
    my $redint=($ipob->intip());
    $redint = Math::BigInt->new("$redint");
    my $first_ip_int = $redint + 1;
    $first_ip_int = Math::BigInt->new("$first_ip_int");
    my $last_ip_int = ($ipob->last_int());
    $last_ip_int = Math::BigInt->new("$last_ip_int");
    $last_ip_int = $last_ip_int - 1;
    
    if ( $first_ip_int_ip_range && $last_ip_int_ip_range ) {
        if ( $first_ip_int < $first_ip_int_ip_range ) {
            $first_ip_int = $first_ip_int_ip_range;
        }
        if ( $last_ip_int > $last_ip_int_ip_range ) {
            $last_ip_int = $last_ip_int_ip_range;
        }
    }

#	if ( $ip_version eq "v6" ) {
#		$first_ip_int--;
#		$last_ip_int++;
#	}

    #check if DNS servers are alive

	my $res_dns;
	my $dns_error = "";

	if ( $default_resolver eq "yes" ) {
		$res_dns = Net::DNS::Resolver->new(
		retry       => 2,
		udp_timeout => 5,
		tcp_timeout => 5,
		recurse     => 1,
		debug       => 0,
                );
	} else {
		$res_dns = Net::DNS::Resolver->new(
		retry       => 2,
		udp_timeout => 5,
		tcp_timeout => 5,
		nameservers => [@dns_servers],
		recurse     => 1,
		debug       => 0,
		);
	}

	my $test_ip_int=$first_ip_int;
	my $test_ip=int_to_ip("$test_ip_int","$ip_version");

	my $ptr_query=$res_dns->query("$test_ip");

	if ( ! $ptr_query) {
		if ( $res_dns->errorstring eq "query timed out" ) {
			print LOG "$lang_vars{no_dns_server_message} (1): " . $res_dns->errorstring . "\n\n";
			print "$lang_vars{no_dns_server_message} (1): " . $res_dns->errorstring . "\n\n" if $verbose;
			$l++;
			next;
		}
	}

	my $used_nameservers = $res_dns->nameservers;

	my $all_used_nameservers = join (" ",$res_dns->nameserver());

	if ( $used_nameservers eq "0" ) {
		print LOG "$lang_vars{no_dns_server_message} (2)\n\n";
		print "$lang_vars{no_dns_server_message} (2)\n\n" if $verbose;
		$l++;
		next;
	}

# TEST 
#	if ( $all_used_nameservers eq "127.0.0.1" && $default_resolver eq "yes" ) {
#		print LOG "$lang_vars{no_answer_from_dns_message} - $lang_vars{nameserver_localhost_message}\n\n$lang_vars{exiting_message}\n\n";
#		print "$lang_vars{no_answer_from_dns_message} - $lang_vars{nameserver_localhost_message}\n\n$lang_vars{exiting_message}\n\n" if $verbose;
#		$l++;
#		next;
#	}

	my $mydatetime = time();

	my $j=0;
    my @ip;
    if ( $ip_range ) {
        @ip=get_host_range("$client_id","$first_ip_int","$last_ip_int","$ip_version");
        if ( ! $first_ip_int || ! $last_ip_int ) {
            print LOG "$lang_vars{no_range_message}\n\n";
            $l++;
            next;
        }
    } else {
        if ( $ip_version eq "v4" ) {
            @ip=get_host("$client_id","$first_ip_int","$last_ip_int","$ip_version");
        } else {
            @ip=get_host_from_red_num("$client_id","$red_num");
        }
    }

	my @found_ip;
	my $p=0;
	foreach my $found_ips (@ip) {
		if ( $found_ips->[0] ) {
			$found_ips->[0]=int_to_ip("$found_ips->[0]","$ip_version");
			$found_ip[$p]=$found_ips->[0];
		}
		$p++;
	}


	my @records=();
	if ( $ip_version eq "v4" ) {
		for (my $m = $first_ip_int; $m <= $last_ip_int; $m++) {
            push (@records,"$m");
		}
	} else {
		@records=@zone_records;
		my @records_new=();
		my $n=0;
		foreach (@zone_records) {
			if ( $_ =~ /(IN.?SOA|IN.?NS)/ ) {
				next;
			}
			$_=/^(.*)\.ip6.arpa/;
			my $nibbles=$1;
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
			$records_new[$n]=$ip_nibbles;
			$n++;
		}
		
		@records=@records_new;
		@records=(@records,@found_ip);
		my %seen;
		for ( my $q = 0; $q <= $#records; ) {
			splice @records, --$q, 1
			if $seen{$records[$q++]}++;
		}
		@records=sort(@records)
	}

	my @records_check=();
	foreach ( @records ) {
		next if ! $_;
		next if $_ !~ /\w+/;
        if ( $ip_range ) {
            push (@records_check,"$_") if exists $ip_range_ips{$_};
        } else {
            push (@records_check,"$_");
        }
	}
	@records=sort(@records_check);


	my ( $ip_int, $ip_bin, $ip_ad, $pm, $res, $pid, $ip );
	my ( %res_sub, %res, %result);

	my $MAX_PROCESSES = $max_sinc_procs || $params{max_sinc_procs};
	$MAX_PROCESSES = "256" if ! $MAX_PROCESSES;
    if ( $MAX_PROCESSES !~ /^4|8|16|32|64|128|254|256/ ) {
		$exit_message = "--max_sinc_procs must be one of this numbers: 4|8|16|32|64|128|256";
        if ( $gip_job_status_id ) {
            Gipfuncs::exit_error("$exit_message", "$gip_job_status_id", 4);
        } else {
            print_help("$exit_message");
        }
    }
	$pm = new Parallel::ForkManager($MAX_PROCESSES);

	$pm->run_on_finish(
		sub { my ($pid, $exit_code, $ident) = @_;
			$res_sub{$ident}=$exit_code;
		}
	);

	my $i;
	foreach ( @records ) {

		next if ! $_;
		$i=$_;

		$count_entradas_dns++;
		my $exit;

		if ( $ip_version eq "v4" ) {
			$ip_ad=int_to_ip("$i","$ip_version");
		} else {
			$ip_ad=$_;
		}

		##fork

        my $ping = "/bin/ping";
        my $ping6 = "/bin/ping6";

		$pid = $pm->start("$ip_ad") and next;
			#child

			my $p;
			if ( $ip_version eq "v4" ) {
				my $command= $ping . ' -c ' . $ping_count . ' -W ' . $ping_timeout . " " .  $ip_ad;
				my $result=ping_system("$command");
				$p=1 if $result == "0";
			} else {
				my $command=$ping6 . ' -c 1 ' .  $ip_ad;
				my $result=ping6_system("$command");
				$p=1 if $result == "0";
			}
			if ( $p ) {
				#ping successful
				$exit=0;
			} else {
				$exit=1;
			}

            my $dns_result_ip="";
            if ( $ignore_dns ) {
#                if ( $exit == 0 ) {
                    $dns_result_ip = "unknown";
#                }
            } elsif ( ! $use_zone_transfer || $ip_version eq "v6" ) {
                my $ptr_query="";

                if ( $default_resolver eq "yes" ) {
                    $res_dns = Net::DNS::Resolver->new(
                    retry       => 2,
                    udp_timeout => 5,
                    tcp_timeout => 5,
                    recurse     => 1,
                    debug       => 0,
                    );
                } else {
                    $res_dns = Net::DNS::Resolver->new(
                    retry       => 2,
                    udp_timeout => 5,
                    tcp_timeout => 5,
                    nameservers => [@dns_servers],
                    recurse     => 1,
                    debug       => 0,
                    );
                }

                $ptr_query = $res_dns->send("$ip_ad");

                $dns_error = $res_dns->errorstring;

                if ( $dns_error eq "NOERROR" ) {
                    if ($ptr_query) {
                        foreach my $rr ($ptr_query->answer) {
                            next unless $rr->type eq "PTR";
                            $dns_result_ip = $rr->ptrdname;
                        }
                    }
                }
            } elsif ( $ip_version eq "v4" ) {
				$dns_result_ip = $zone_records_hash{$ip_ad} if $zone_records_hash{$ip_ad};
            }

            # exit = 0 > success
			if ( $dns_result_ip && $exit == 0 ) {
				$exit=2;
			} elsif ( $dns_result_ip && $exit == 1 ) {
				$exit=3;
			} elsif ( ! $dns_result_ip && $exit == 0 ) {
				$exit=4;
			}

		$pm->finish($exit); # Terminates the child process

	}


	$pm->wait_all_children;

	my $host_hash_ref=get_host_hash_check("$client_id","$first_ip_int","$last_ip_int","$red_num");

	my $ip_ad_int="";
	foreach ( @records ) {
		if ( ! $_ ) {
			next;
		}

        if ( $ip_range ) {
            if ( exists $ip_range_ips{$_} ) {
                if ( $ip_version eq "v4" ) {
                    $ip_ad_int=$_;
                    $ip_ad = int_to_ip("$ip_ad_int","$ip_version");
                } else {
                    $ip_ad=$_;
                    $ip_ad_int = ip_to_int("$ip_ad","$ip_version");
                }
            } else {
                next;
            }
        } else {
            if ( $ip_version eq "v4" ) {
                $ip_ad_int=$_;
                $ip_ad = int_to_ip("$ip_ad_int","$ip_version");
            } else {
                $ip_ad=$_;
                $ip_ad_int = ip_to_int("$ip_ad","$ip_version");
            }
        }

		my $exit=$res_sub{$ip_ad}; 

        if ( ! $exit ) {
            next;
        }

        my $host_exists = "";
		my $hostname_bbdd = "";
		my $cat_id="-1";
        my $loc_id_host="-1";
		my $int_admin="n";
		my $utype="dns";
		my $utype_id;
		my $host_descr = "";
		my $comentario = "";
		my $alive = "";
		my $range_id="-1";
		my $host_id="";

        if ( exists $host_hash_ref->{"$ip_ad_int"} ) {
            $host_exists = 1;
            $hostname_bbdd = $host_hash_ref->{"$ip_ad_int"}[1];
            $host_descr = $host_hash_ref->{"$ip_ad_int"}[2] || "";
            $host_id = $host_hash_ref->{"$ip_ad_int"}[6] || "";
            $loc_id_host = $host_hash_ref->{"$ip_ad_int"}[10] || "-1";
            $cat_id = $host_hash_ref->{"$ip_ad_int"}[11] || "-1";
            $comentario = $host_hash_ref->{"$ip_ad_int"}[3] || "";
            $utype_id = $host_hash_ref->{"$ip_ad_int"}[12] || "-1";
			$utype=get_utype("$utype_id") || "---";
            $utype= "dns" if $utype eq "NULL";
            $alive = $host_hash_ref->{"$ip_ad_int"}[14] || "-1";
            $int_admin = $host_hash_ref->{"$ip_ad_int"}[13];
            $range_id = $host_hash_ref->{"$ip_ad_int"}[4];
            print LOG "D2: $ip_ad - $hostname_bbdd - $host_descr - $loc_id_host - $cat_id - $utype_id - $range_id - $host_id\n" if $debug;
        }

		if ( $dyn_ranges_only eq "yes" ) {
			if ( $host_exists && $range_id == "-1" ) {
				next;
			} elsif ( ! $host_exists ) {
				next;
			}
		}

        $loc_id = $loc_id_host if $loc_id_host;

		print "$ip_ad: " if $verbose; 
		print LOG "$ip_ad: "; 
        print LOG "\nOLD ENTRY: $hostname_bbdd - $host_descr - $cat_id - $loc_id - $utype\n" if $hostname_bbdd && $debug;

		$utype_id=Gipfuncs::get_utype_id("$utype") if ! $utype_id;

		my $ping_result=0;
		$ping_result=1 if $exit == "0" || $exit == "2" || $exit == "4"; #ping OK

		# Ignor IP if update type has higher priority than "dns" 
		if ( $utype ne "dns" && $utype ne "---" ) {
			if ( $hostname_bbdd ) {
				print "$hostname_bbdd - update type: $utype - $lang_vars{ignorado_message}\n" if $verbose;
				print LOG "$hostname_bbdd - update type: $utype - $lang_vars{ignorado_message}\n";
				update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num") if ! $test;
			} else {
				print "update type: $utype - $lang_vars{ignorado_message}\n" if $verbose;
				print LOG "update type: $utype - $lang_vars{ignorado_message}\n";
			}
			next;
		}

        # Ignore "reserved" entries
		if ( $hostname_bbdd =~ /^reserved$/i ) {
            print "reserved IP - ignored\n";
            print LOG "reserved IP - ignored\n";
            next;
        }
			
		my $ignore_reason=0; 
        # 1: no dns entry; 2: hostname matches generic-auto-name; 3: hostname matches ignore-string 4: hostname matches generic-dynamic name 5: ignore_dns activated

		my @dns_result_ip;
		my $hostname;
		my $igno_name;
		my $igno_set = 0;
		if ( $ignore_dns ) {
			$igno_set = 1;
			$hostname="unknown";
			$igno_name="unknown";
			$ignore_reason=5;

		} elsif (( $exit == 2 || $exit == 3 ) && ! $use_zone_transfer )  {
			# exit = 1|2: dns entry found

			my $ptr_query="";
			my $dns_result_ip="";

			if ( $default_resolver eq "yes" ) {
				$res_dns = Net::DNS::Resolver->new(
				retry       => 2,
				udp_timeout => 5,
				tcp_timeout => 5,
				recurse     => 1,
				debug       => 0,
				);
			} else {
				$res_dns = Net::DNS::Resolver->new(
				retry       => 2,
				udp_timeout => 5,
				tcp_timeout => 5,
				nameservers => [@dns_servers],
				recurse     => 1,
				debug       => 0,
				);
			}

			$ptr_query = $res_dns->send("$ip_ad");

			$dns_error = $res_dns->errorstring;

			if ( $dns_error eq "NOERROR" ) {
				if ($ptr_query) {
					foreach my $rr ($ptr_query->answer) {
						next unless $rr->type eq "PTR";
						$dns_result_ip = $rr->ptrdname;
					}
				}
			}

			$hostname = $dns_result_ip || "unknown";


			if ( $hostname eq "unknown" ) {
				$count_entradas_dns_timeout++;
				$ignore_reason=1;
			}
		} elsif ( $ip_version eq "v4" ) {
			if ( $zone_records_hash{$ip_ad} ) {
				$hostname = $zone_records_hash{$ip_ad};
			} else {
				$hostname = "unknown";
				$ignore_reason=1;
			}
		} else {
			$hostname = "unknown";
			$ignore_reason=1;
		}

		my $ptr_name = $ip_ad;
		my $generic_auto="";

		$generic_auto = get_generic_auto("$ip_ad", "$ip_version");

		if ( $hostname =~ /$generic_auto/ && $ignore_generic_auto eq "yes" ) {
			$igno_set = 1;
			$hostname="unknown";
			$igno_name="$generic_auto";
			$ignore_reason=2;
		}

		foreach my $ignorar_val(@values_ignorar) {
			if ( $hostname =~ /$ignorar_val/ ) {
				$igno_set = 1;
				$hostname="unknown";
				$igno_name="$_";
				$ignore_reason=3;
			}
			next;
		}

		if ( $hostname =~ /$generic_dyn_host_name/ ) {
			$igno_set = 1;
			$hostname="unknown";
			$igno_name="$generic_dyn_host_name";
			$ignore_reason=4;
		}

		my $duplicated_entry=0;

		if ( $hostname_bbdd ) {

            my $message = "";

			if ( $hostname_bbdd eq $hostname && $hostname ne "unknown" && $igno_set == "0") {
				print "$lang_vars{tiene_entrada_message}: $hostname_bbdd - $lang_vars{ignorado_message}\n" if $verbose;
				print LOG "$lang_vars{tiene_entrada_message}: $hostname_bbdd - $lang_vars{ignorado_message}\n";
				update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num") if ! $test;

			} else {
#				if ( $hostname eq "unknown" && $ping_result == "0"  && ! $ignore_dns) 
				if ( $hostname eq "unknown" && $ping_result == "0") {
					print LOG "MATCH1\n" if $debug;

					# no dns entry
					if ( $ignore_reason == "1" ) {
						$message = "$hostname_bbdd ($lang_vars{no_dns_message} + $lang_vars{no_ping_message})";
					# hostname matches generic man auto name
					} elsif ( $ignore_reason == "2" ) {
						$message = "$hostname_bbdd ($lang_vars{auto_generic_name_message} + $lang_vars{no_ping_message})";
					# hostname matches ignore-string
					} elsif ( $ignore_reason == "3" ) {
						$message = "$hostname_bbdd ($lang_vars{tiene_man_string_no_ping_message})";
					# hostname matches generic_dyn_hostname (not used in form)
					} elsif ( $ignore_reason == "4" ) {
						$message = "$hostname_bbdd ($lang_vars{generic_dyn_host_message} + $lang_vars{no_ping_message})";
					} elsif ( $ignore_reason == "5" ) {
						$message = "$hostname_bbdd ('IGNORE DNS' activated + $lang_vars{no_ping_message})";
					} else {
						$message = "$hostname_bbdd ($lang_vars{no_ping_message})";
					}

                    if ( $delete_down_hosts ne "yes" ) {
                        if ( $hostname_bbdd eq "unknown" ) {
#                            $message .= ' - ignored (no DNS entry + no response to ping)';
                            $message .= ' - ignored';
                        } else {
                            update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$dyn_dns_updates") if ! $test;
                            $message = "$hostname ($lang_vars{entrada_antigua_message}: $hostname_bbdd)" if ! $message;
                            print "$lang_vars{entrada_actualizada_message}: $message\n" if $verbose;
                            print LOG "$lang_vars{entrada_actualizada_message}: $message\n";

                            my $audit_type="1";
                            my $audit_class="1";
                            my $host_descr_audit = $host_descr;
                            $host_descr_audit = "---" if $host_descr_audit eq "NULL";
                            my $comentario_audit = $comentario;
                            $comentario_audit = "---" if $comentario_audit eq "NULL";
                            my $event="$ip_ad,$hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
                            insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
                        }
                        next;
                    } else {
                        if ( $range_id eq "-1" ) {
#                            my $host_id=get_host_id_from_ip_int("$client_id","$ip_ad_int");
                            delete_custom_host_column_entry("$client_id","$host_id") if ! $test;
                            if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
                                my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
                                my @linked_ips=split(",",$linked_ips);
                                foreach my $linked_ip_delete(@linked_ips){
                                    delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad") if ! $test;
                                }
                            }
                            delete_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version") if ! $test;
                        } else {
#                            my $host_id=get_host_id_from_ip_int("$client_id","$ip_ad_int");
                            delete_custom_host_column_entry("$client_id","$host_id") if ! $test;
                            if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
                                my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
                                my @linked_ips=split(",",$linked_ips);
                                foreach my $linked_ip_delete(@linked_ips){
                                    delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad") if ! $test;
                                }
                            }
                            clear_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version") if ! $test;
                        }

                        print "$lang_vars{entrada_borrado_message}: $message\n" if $verbose;
                        print LOG "$lang_vars{entrada_borrado_message}: $message\n";

                        my $audit_type="14";
                        my $audit_class="1";
                        my $host_descr_audit = $host_descr;
                        $host_descr_audit = "---" if $host_descr_audit eq "NULL";
                        my $comentario_audit = $comentario;
                        $comentario_audit = "---" if $comentario_audit eq "NULL";
                        my $event="$ip_ad,$hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
                        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
                        next;
                    }

				} elsif ( $ignore_dns && $ping_result == 0 && $delete_down_hosts ) {
					print LOG "MATCH3\n" if $debug;
					if ( $range_id eq "-1" ) {
#						my $host_id=get_host_id_from_ip_int("$client_id","$ip_ad_int");
						delete_custom_host_column_entry("$client_id","$host_id") if ! $test;
						if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
							my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
							my @linked_ips=split(",",$linked_ips);
							foreach my $linked_ip_delete(@linked_ips){
								delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
							}
						}
						delete_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version") if ! $test;
					} else {
#						my $host_id=get_host_id_from_ip_int("$client_id","$ip_ad_int");
						delete_custom_host_column_entry("$client_id","$host_id") if ! $test;
						if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
							my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
							my @linked_ips=split(",",$linked_ips);
							foreach my $linked_ip_delete(@linked_ips){
								delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
							}
						}
						clear_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version") if ! $test;
					}
					print "$lang_vars{entrada_borrado_message}: $hostname_bbdd ('IGNORE DNS' activated + $lang_vars{no_ping_message})\n" if $verbose;
					print LOG "$lang_vars{entrada_borrado_message}: $hostname_bbdd ('IGNORE DNS' activated + $lang_vars{no_ping_message})\n" if $verbose;

					my $audit_type="14";
					my $audit_class="1";
					my $host_descr_audit = $host_descr;
					$host_descr_audit = "---" if $host_descr_audit eq "NULL";
					my $comentario_audit = $comentario;
					$comentario_audit = "---" if $comentario_audit eq "NULL";
					my $event="$ip_ad,$hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
					next;

				} elsif ( $ignore_dns && $ping_result == 0 && ! $delete_down_hosts ) {
					print LOG "MATCH3A\n" if $debug;
                    print "Updating ping status\n" if $verbose;
                    print LOG "updating ping status\n";
					update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num");
					next;

				} elsif ( $hostname eq "unknown" && $ping_result == "1" ) {
                    # 1 no DNS entry
                    # 2 generic auto name
                    # 3 hostname matches ignore-string
                    # 4 hostname matches generic-dynamic name (not used in form)
                    # 5 ignore dns activated
					if ( $ignore_reason == "1" ) {
						print LOG "MATCH4a\n" if $debug;
						print "$lang_vars{tiene_entrada_message}: $hostname_bbdd ($lang_vars{no_dns_message}) - $lang_vars{ignorado_message}\n" if $verbose;
						print LOG "$lang_vars{tiene_entrada_message}: $hostname_bbdd ($lang_vars{no_dns_message}) - $lang_vars{ignorado_message}\n";
					} elsif ( $ignore_reason == "5" ) {
						print LOG "MATCH4c\n" if $debug;
						print "Updating ping status\n" if $verbose;
						print LOG "updating ping status\n";
					} elsif ( $ignore_reason == "2" || $ignore_reason == "3" || $ignore_reason == "4" ) {
						print LOG "MATCH4b\n" if $debug;
						print "$lang_vars{tiene_entrada_message}: $hostname_bbdd - $lang_vars{ignorado_message}\n" if $verbose;
						print LOG "$lang_vars{tiene_entrada_message}: $hostname_bbdd - $lang_vars{ignorado_message}\n";
					}
					update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num");
					next;
				} else {
                    print LOG "NO MATCH: $hostname_bbdd, $hostname, $host_descr, $exit, $ping_result\n" if $debug;
                }


				if ( $hostname_bbdd ne $hostname  ) {
					print LOG "MATCH7\n" if $debug;
					update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$dyn_dns_updates") if ! $test;
                    $message = "$hostname ($lang_vars{entrada_antigua_message}: $hostname_bbdd)" if ! $message;
					print "$lang_vars{entrada_actualizada_message}: $message\n" if $verbose;
					print LOG "$lang_vars{entrada_actualizada_message}: $message\n";

					my $audit_type="1";
					my $audit_class="1";
					my $host_descr_audit = $host_descr;
					$host_descr_audit = "---" if $host_descr_audit eq "NULL";
					my $comentario_audit = $comentario;
					$comentario_audit = "---" if $comentario_audit eq "NULL";
					my $event="$ip_ad,$hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";

				} elsif ( $hostname_bbdd eq "unknown" && $hostname eq "unknown" ) {
					print "$lang_vars{tiene_entrada_message}: $hostname_bbdd - ($lang_vars{generico_message}) $lang_vars{ignorado_message}\n" if $verbose;
					print LOG "$lang_vars{tiene_entrada_message}: $hostname_bbdd - $lang_vars{ignorado_message}\n";
					update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num") if $ping_result != $alive && ! $test;
				} elsif ( $hostname_bbdd eq $hostname ) {
					update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file","$alive","$red_num") if $ping_result != $alive && ! $test;
					print LOG "$lang_vars{no_changes_message} - $lang_vars{ignorado_message}\n";
					print "$lang_vars{no_changes_message} - $lang_vars{ignorado_message}\n" if $verbose;

#				} else {
#					update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file") if ! $test;
#					print "$hostname_bbdd: $lang_vars{entrada_cambiado_message} (DNS: $hostname) - $lang_vars{ignorado_message} ($lang_vars{update_type_message}: $utype)\n" if $verbose;
#					print LOG "$hostname_bbdd: $lang_vars{entrada_cambiado_message} (DNS: $hostname) - $lang_vars{ignorado_message} ($lang_vars{update_type_message}: $utype)\n";
				}
			}
			next;
		}


		# no hostname_bbdd; 2: dns ok, ping ok; 3: dns ok, ping failed, 4: DNS not ok, ping OK
		if ( $exit eq 2 || $exit eq 3 || $exit eq 4 ) {
			if ( $exit eq 3 && $hostname eq "unknown" && $igno_set == "1" ) {
				if ( $ignore_reason == "2" ) {
					print "$lang_vars{tiene_string_no_ping_message} - $lang_vars{ignorado_message}\n" if $verbose;
					print LOG "$lang_vars{tiene_string_no_ping_message} - $lang_vars{ignorado_message}\n";
                } elsif ( $ignore_reason == "5" ) {
                    print "down - ignored\n" if $verbose;
                    print LOG "down - ignored\n";
				} else {
					print "$lang_vars{tiene_man_string_no_ping_message} - $lang_vars{ignorado_message}\n" if $verbose;
					print LOG "$lang_vars{tiene_man_string_no_ping_message} - $lang_vars{ignorado_message}\n";
				}
				next;
			} elsif ( $exit eq 3 && $ignore_dns ) {
				print "'IGNORE DNS' activated + $lang_vars{no_ping_message} - $lang_vars{ignorado_message}\n";
				print LOG "'IGNORE DNS' activated + $lang_vars{no_ping_message} - $lang_vars{ignorado_message}\n";
				next;
			}

			if ( $range_id eq "-1" ) {
				if ( ! $host_exists ) {
					print LOG "INSERT IP: $hostname, exit: $exit\n" if $debug;
					insert_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$ip_version","$dyn_dns_updates") if ! $test;
				} else {
					print LOG "DUPLICATED ENTRY IGNORED: $host_hash_ref->{$ip_ad_int}[0], $host_hash_ref->{$ip_ad_int}[1] - $ip_ad, $hostname\n";
					$duplicated_entry=1;
				}
			} else {
                # range
                print LOG "UPDATE (range_id: $range_id), (exit: $exit)\n" if $debug;
				update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$dyn_dns_updates") if ! $test;
			}
			if ( $duplicated_entry == 0 ) {
				if ( $exit eq 2 && $hostname eq "unknown" && $igno_set == "1") {
					if ( $ignore_reason == "2" ) {
						print "$lang_vars{auto_generic_name_message} - $lang_vars{host_anadido_message}: unknown\n" if $verbose;
						print LOG "$lang_vars{auto_generic_name_message} - $lang_vars{host_anadido_message}: unknown\n";
					} else {
						print "$lang_vars{generic_dyn_host_message} - $lang_vars{host_anadido_message}: unknown\n" if $verbose;
						print LOG "$lang_vars{generic_dyn_host_message} - $lang_vars{host_anadido_message}: unknown\n";
					}
				} else {
					print "$lang_vars{host_anadido_message}: $hostname\n" if $verbose;
					print LOG "$lang_vars{host_anadido_message}: $hostname\n";
				}
				my $audit_type="15";
				my $audit_class="1";
				my $host_descr_audit = $host_descr;
				$host_descr_audit = "---" if $host_descr_audit eq "NULL";
				my $comentario_audit = $comentario;
				$comentario_audit = "---" if $comentario_audit eq "NULL";
				my $event="$ip_ad,$hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
				insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
			}
		} else {
			print "$lang_vars{no_dns_message} + $lang_vars{no_ping_message} - $lang_vars{ignorado_message}\n" if $verbose;
			print LOG "$lang_vars{no_dns_message} + $lang_vars{no_ping_message} - $lang_vars{ignorado_message}\n";
		} 
	}
    $l++;

    # update net usage column
    update_net_usage_cc_column("$client_id", "$ip_version", "$red_num", "$BM","no_rootnet") if ! $test;

}

if ( $create_csv ) {
 close CSV;
}

$count_entradas_dns ||= "0";

my $count_entradas = $count_entradas_dns;

my @smtp_server_values;
if ( $mail ) {
    @smtp_server_values = Gipfuncs::get_smtp_server_by_name("$smtp_server");

    if ( $smtp_server_values[0] ) {
        Gipfuncs::send_mail (
            debug       =>  "$debug",
            mail_from   =>  $mail_from,
            mail_to     =>  \@mail_to,
			subject     => "Result Job $job_name",
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
my $duration=$end_time - $start_time;
my @parts = gmtime($duration);
my $duration_string = "";
$duration_string = $parts[2] . "h, " if $parts[2] != "0";
$duration_string = $duration_string . $parts[1] . "m";
$duration_string = $duration_string . " and " . $parts[0] . "s";

print "\nExecution time: $duration_string\n" if $verbose;
print LOG "\nExecution time: $duration_string\n";
close LOG;

if ( $gip_job_id && ! $combined_job && ! $create_csv ) {
    Gipfuncs::update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
}


print "Job successfully finished\n";
exit 0;


#######################
# Subroutiens
#######################

sub print_help {
	my ( $message ) = @_;

    print "$message\n" if $message;

	print "\nusage: ip_update_gestioip_dns.pl [OPTIONS...]\n\n";
	print "--config_file_name=config_file_name  name of the configuration file (without path)\n";
	print "--changes_only                           report changed entries only\n";
	print "--combined_job                           combined job\n";
	print "-C, --CSV_networks=csv-list              coma separated list of networks to process\n";
    print "                                             (e.g. --CVS_networks=1.1.1.0/24,2.2.2.0/25)\n";
	print "--delete_down_hosts                      delete all IPs which do not respond to ping and which do not have rDNS entries\n";
	print "--disable_audit                          disable audit\n";
	print "--document_root                          GestioIP's Apache DocumentRoot\n";
	print "-h, --help                               this help\n";
	print "-i, --ignore_dns                         Ignore result of rDNS query. Only add IP if it\n";
    print "                                             responds to ping\n";
	print "-l, --log=logfile                        logfile\n";
	print "--Location=locations   		            Ignore networks from other sites than --Locations (coma separted list of locations)\n";
	print "--Location_scan=locations                Process all networks of this sites (coma separted list of locations)\n";
	print "--mail                                   send the result by mail\n";
	print "--mail_from                              Mail \"from\" of the summary mail\n";
	print "--mail_to                                Where to send the summary mail to. Coma separated list of mail recipients\n";
	print "-N, --Network_file=networks.list         File with the list of networks to process (without path)\n";
	print "-o, --only_added_mail                    Send only a summary for new added hosts by mail\n";
	print "-r, --range=ip-range                     Range of IPs to scan. Format: --range=IP1-IP2\n";
    print "                                             (e.g. --range=1.1.1.3-1.1.1.10)\n";
	print "-t, --tag=tag-list                       Use networks with this tags to process\n";
    print "                                             (e.g. --tag=tag1,tag2,tag3)\n";
	print "-v, --verbose                            Verbose\n";
	print "-V, --Version                            Print version and exit\n";
	print "-x, --debug                              Run in debug mode\n";
    print "\n";
    print "Options to overwrite values from the configuration file:\n";
    print "-A client\n";
    print "-B ignore_generic_auto ([yes|no])\n";
    print "-M logdir\n";
    print "-T actualize_ipv4 ([yes|no]), Default: yes\n";
    print "-O actualize_ipv6 ([yes|no]), Default: no\n";
    print "-P generic_dyn_host_name\n";
    print "-Q ignorar\n";
    print "-S max_sinc_procs ([4|8|16|32|64|128|256])\n";
    print "-W job_id\n";
    print "-Z Use DNS zone transfers. Requiers to allow DNS zone transfers\n";
    print "   on the DNS server from the GestioIP server\n";

	print "\n\nconfiguration file: $conf\n\n" if $conf;
	exit;
}

sub print_version {
	print "\n$0 Version $VERSION\n\n";
	exit 0;
}


sub int_to_ip {
	my ($ip_int,$ip_version)=@_;
	my ( $ip_bin, $ip_ad);
	if ( $ip_version eq "v4" ) {
		$ip_bin = ip_inttobin ($ip_int,4);
		$ip_ad = ip_bintoip ($ip_bin,4);
	} else {
		$ip_bin = ip_inttobin ($ip_int,6);
		$ip_ad = ip_bintoip ($ip_bin,6);
	}
	return $ip_ad;
}

sub ip_to_int {
        my ($ip,$ip_version)=@_;
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


sub mysql_connection {
	my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip)  or die "Mysql ERROR: ". $DBI::errstr;

    return $dbh;
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

sub get_red {
        my ( $client_id, $red_num ) = @_;
        my $ip_ref;
        my @values_redes;
        my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $sth = $dbh->prepare("SELECT red, BM, descr, loc, vigilada, comentario, categoria, ip_version FROM net WHERE red_num=$qred_num  AND client_id=\"$client_id\"") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_redes;
}


sub get_host {
	my ( $client_id, $first_ip_int, $last_ip_int,$ip_version ) = @_;

	my @values_ip;

	if ( ! $create_csv ) {
		my $ip_ref;
		my $dbh = mysql_connection();
		my $qfirst_ip_int = $dbh->quote( $first_ip_int );
		my $qlast_ip_int = $dbh->quote( $last_ip_int );

		my $match="h.ip BETWEEN $qfirst_ip_int AND $qlast_ip_int";
		if ( $ip_version eq "v4" ) {
			$match="CAST(h.ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";
		}

        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id FROM host h, locations l, categorias c, update_type ut WHERE $match AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND h.client_id=\"$client_id\" ORDER BY h.ip") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
			push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;

	} else {
		my $ip1 = int_to_ip("$first_ip_int","$ip_version");
		my $ip2 = int_to_ip("$last_ip_int","$ip_version");
		my $ip_range = ${ip1} . "-" . ${ip2};
		my $path = '/listHostsResult/HostList/Host';
		my $content = "request_type=listHosts&client_name=$client&no_csv=yes&ip_range=$ip_range";
		my @values = ("IP", "hostname", "descr", "site", "cat", "int_admin", "comment", "update_type", "alive", "last_response", "");
		@values_ip = Gipfuncs::make_call_array("$path", "$content", \@values);
	}

   return @values_ip;
}

sub get_host_range {
	my ( $client_id,$first_ip_int, $last_ip_int,$ip_version ) = @_;
	my @values_ip;

	if ( ! $create_csv ) {
        my $ip_ref;
        my $dbh = mysql_connection();

		my $match="h.ip BETWEEN $first_ip_int AND $last_ip_int";
		if ( $ip_version eq "v4" ) {
			$match="CAST(h.ip AS BINARY) BETWEEN $first_ip_int AND $last_ip_int";
		}

        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id FROM host h, locations l, categorias c, update_type ut WHERE $match AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND range_id != '-1' AND h.client_id=\"$client_id\" ORDER BY h.ip") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;

	} else {
		my $ip1 = int_to_ip("$first_ip_int","$ip_version");
		my $ip2 = int_to_ip("$last_ip_int","$ip_version");
		my $ip_range = ${ip1} . "-" . ${ip2};
		my $path = '/listHostsResult/HostList/Host';
		my $content = "request_type=listHosts&client_name=$client&no_csv=yes&ip_range=$ip_range";
		my @values = ("IP", "hostname", "descr", "site", "cat", "int_admin", "comment", "update_type", "alive", "last_response", "");
		@values_ip = Gipfuncs::make_call_array("$path", "$content", \@values);
	}

	return @values_ip;
}


sub get_utype {
	my ( $utype_id ) = @_;

	my $utype;

	if ( ! $create_csv ) {
        my $dbh = mysql_connection();
        my $qutype_id = $dbh->quote( $utype_id );
        my $sth = $dbh->prepare("SELECT type FROM update_type WHERE id=$qutype_id
                        ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $utype = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
    } else {

		$utype_id = 10 if $utype_id eq "-1";
		my %update_types = (
			1 => "man",
			2 => "dns",
			3 => "ocs",
			10 => "NULL",
		);

		$utype = $update_types{$utype_id} || "";
	}

	return $utype;
}


sub update_host_ping_info {
	my ( $client_id,$ip_int,$ping_result_new,$enable_ping_history,$ip_ad,$update_type_audit,$vars_file,$ping_result_old,$red_num) = @_;

	$enable_ping_history="" if ! $enable_ping_history;
	$update_type_audit="4" if ! $update_type_audit;
    $ping_result_new = 0 if ! $ping_result_new;
	$ping_result_old = 0 if ! $ping_result_old;

    if ( ! $create_csv ) {
        my $dbh = mysql_connection();
        my $qip_int = $dbh->quote( $ip_int );

        my $qmydatetime = $dbh->quote( time() );
        my $alive = $dbh->quote( $ping_result_new );
        my $qclient_id = $dbh->quote( $client_id );

        my $sth;

#        $sth = $dbh->prepare("SELECT alive FROM host WHERE ip=$qip_int AND client_id = $qclient_id
#            ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
#        $sth->execute();
#        $ping_result_old = $sth->fetchrow_array || "";
#        $ping_result_old = 0 if ! $ping_result_old || $ping_result_old eq "NULL";

        $sth = $dbh->prepare("UPDATE host SET alive=$alive, last_response=$qmydatetime WHERE ip=$qip_int AND client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;

        if ( $enable_ping_history eq 1 && $ping_result_old ne $ping_result_new ) {
            my $ping_state_old;
            my $ping_state_new;
            if ( $ping_result_old eq 1 ) {
                $ping_state_old="up";
                $ping_state_new="down";
            } else {
                $ping_state_old="down";
                $ping_state_new="up";
            }
            
            my $audit_type="100";
            my $audit_class="1";
            my $event="$ip_ad: $ping_state_old -> $ping_state_new";
            insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
        }
	} else {
#    "action,ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,client_id,ip_version,dyn_dns_updates";
        my $mydatetime = time();
        $csv_string = "UPDATE_PING_INFO,$ip_int,,,,$red_num,,,,,,$ping_result_new,$mydatetime,,,,4";
        $csv_string =~ s/,/","/g;
        $csv_string = '"' . $csv_string . '"' . "\n";
        print CSV $csv_string;
	}
}

sub delete_ip {
    my ( $client_id,$first_ip_int, $last_ip_int,$ip_version ) = @_;

	if ( ! $create_csv ) {
		my $dbh = mysql_connection();
		my $qfirst_ip_int = $dbh->quote( $first_ip_int );
		my $qlast_ip_int = $dbh->quote( $last_ip_int );

		my $match="ip BETWEEN $qfirst_ip_int AND $qlast_ip_int";
		if ( $ip_version eq "v4" ) {
			$match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";
		}

		my $sth = $dbh->prepare("DELETE FROM host WHERE $match AND client_id=\"$client_id\""
									) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->finish();
		$dbh->disconnect;

	} else {
        $csv_string = "DELETE,$first_ip_int,,,,,,,,,,,,,,,4";
        $csv_string =~ s/,/","/g;
        $csv_string = '"' . $csv_string . '"' . "\n";
        print CSV $csv_string;
	}

}

sub clear_ip {
        my ( $client_id,$first_ip_int, $last_ip_int, $ip_version ) = @_;

        # TEST why not create CSV entry
        return if $create_csv;

        my $dbh = mysql_connection();
        my $qfirst_ip_int = $dbh->quote( $first_ip_int );
        my $qlast_ip_int = $dbh->quote( $last_ip_int );

	my $match="ip BETWEEN $qfirst_ip_int AND $qlast_ip_int";
	if ( $ip_version eq "v4" ) {
		$match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";
	}

        my $sth = $dbh->prepare("UPDATE host SET hostname='', host_descr='', int_admin='n', alive='-1', last_response=NULL, comentario='' WHERE $match AND client_id=\"$client_id\""
                                ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}

sub insert_ip_mod {
        my ( $client_id,$ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $dyn_dns_updates ) = @_;

        $dyn_dns_updates = 1 if ! $dyn_dns_updates;

        if ( ! $create_csv ) {
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
            my $qclient_id = $dbh->quote( $client_id );
            my $qdyn_dns_updates = $dbh->quote( $dyn_dns_updates );
            my $qip_version = $dbh->quote( $ip_version );
            if ( defined($alive) ) {
                    my $qalive = $dbh->quote( $alive );
                    my $qlast_response = $dbh->quote( time() );
                    $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,client_id,ip_version,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qclient_id,$qip_version,$qdyn_dns_updates)"
                                    ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            } else {
                    $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,client_id,ip_version,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qclient_id,$qip_version,$qdyn_dns_updates)"
                                    ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            }
            $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            $sth->finish();
            $dbh->disconnect;
            print LOG "INSERT: $hostname - $host_descr - $loc - $cat - $comentario - $update_type\n" if $debug;

        } else {
            my $last_response = time();
            $csv_string = "INSERT,$ip_int,$hostname,$host_descr,$loc,$red_num,$int_admin,$cat,$comentario,$update_type,$mydatetime,$alive,$last_response,$client_id,$ip_version,$dyn_dns_updates,4";
            $csv_string =~ s/"/\\"/g;
            $csv_string =~ s/,/","/g;
            $csv_string = '"' . $csv_string . '"' . "\n";
            print CSV $csv_string;
        }
}

sub update_ip_mod {
        my ( $client_id,$ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $dyn_dns_updates ) = @_;

        $dyn_dns_updates = 1 if ! $dyn_dns_updates;

        if ( ! $create_csv ) {
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
            my $qred_num = $dbh->quote( $red_num );
            my $qip_int = $dbh->quote( $ip_int );
            my $qclient_id = $dbh->quote( $client_id );
            my $qdyn_dns_updates = $dbh->quote( $dyn_dns_updates );
            if ( defined($alive) ) {
                my $qalive = $dbh->quote( $alive );
                my $qlast_response = $dbh->quote( time() );
                $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname, host_descr=$qhost_descr, loc=$qloc, int_admin=$qint_admin, categoria=$qcat, comentario=$qcomentario, update_type=$qupdate_type, last_update=$qmydatetime, red_num=$qred_num, alive=$qalive, last_response=$qlast_response, dyn_dns_updates=$qdyn_dns_updates WHERE ip=$qip_int AND client_id=$qclient_id"
                                    ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            } else {
                $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname, host_descr=$qhost_descr, loc=$qloc, int_admin=$qint_admin, categoria=$qcat, comentario=$qcomentario, update_type=$qupdate_type, last_update=$qmydatetime, red_num=$qred_num, dyn_dns_updates=$qdyn_dns_updates WHERE ip=$qip_int AND client_id=$qclient_id"
                                    ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            }
            $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
            $sth->finish();
            $dbh->disconnect;
            print LOG "UPDATE: $hostname - $host_descr - $loc - $cat - $comentario - $update_type\n" if $debug;

        } else {
            my $last_response = time();
            $csv_string = "UPDATE,$ip_int,$hostname,$host_descr,$loc,$red_num,$int_admin,$cat,$comentario,$update_type,$mydatetime,$alive,$last_response,$client_id,,$dyn_dns_updates,4";
            $csv_string =~ s/"/\\"/g;
            $csv_string =~ s/,/","/g;
            $csv_string = '"' . $csv_string . '"' . "\n";
            print CSV $csv_string;
        }
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

sub check_one_client_name {
	my ($client_name) = @_; 

    my $val;
    if ( ! $create_csv ) {
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT client FROM clients WHERE client=\"$client_name\"
                        ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
    } else {
        my $path = '/listClientsResult/Client/';
        my $content = "request_type=listClients";
        my $value = "client";
        $val = Gipfuncs::make_call_value("$path", "$content", "$value");
    }

    return $val;
}

#sub get_client_id_one {
#	my ($client_name) = @_; 
#        my $val;
#        my $dbh = mysql_connection();
#        my $sth = $dbh->prepare("SELECT id FROM clients
#                        ") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
#        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
#        $val = $sth->fetchrow_array;
#        $sth->finish();
#        $dbh->disconnect;
#        return $val;
#}

sub get_client_id_from_name {
        my ( $client_name ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qclient_name = $dbh->quote( $client_name );
        my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qclient_name") or die "Mysql ERROR: ". $DBI::errstr;
        $sth->execute() or die "Mysql ERROR: ". $DBI::errstr;
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_host_id_from_ip_int {
        my ( $client_id,$ip_int ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qip_int = $dbh->quote( $ip_int );
        my $qclient_id = $dbh->quote( $client_id );
	my $sth;
        $sth = $dbh->prepare("SELECT id FROM host WHERE ip=$qip_int AND client_id=$qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub delete_custom_host_column_entry {
	my ( $client_id, $host_id ) = @_;

	return if $create_csv;

	my $dbh = mysql_connection();
	my $qhost_id = $dbh->quote( $host_id );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth;
	$sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND client_id = $qclient_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}

sub ping_system {
	my ($command) = @_;
	my $devnull = "/dev/null";
	$command .= " 1>$devnull 2>$devnull";
	my $exit_status = system($command) >> 8;
	return $exit_status;
}

sub ping6_system {
	my ($command) = @_;
	my $devnull = "/dev/null";
	$command .= " 1>$devnull 2>$devnull";
	my $exit_status = system($command) >> 8;
	return $exit_status;
}


sub fetch_zone {
        my ($zone_name,$default_resolver,$dns_servers)=@_;
        $default_resolver="" if ! $default_resolver;
        my @zone_records;
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


        print LOG "FETCHING ZONE: $zone_name - @$dns_servers - $default_resolver\n" if $debug;

        my @fetch_zone = $res->axfr("$zone_name");

        my $i=0;
        my $rr;
        foreach $rr (@fetch_zone) {
                $zone_records[$i]=$rr->string;
                print LOG "FOUND RECORD: $zone_records[$i]\n" if $debug;
                $i++;
        }
        return @zone_records;
}

sub get_host_from_red_num {
        my ( $client_id, $red_num ) = @_;
        my @values_ip;
		if ( ! $create_csv ) {
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id, h.id FROM host h, locations l, categorias c, update_type ut WHERE h.red_num=$qred_num AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND h.client_id = $qclient_id ORDER BY h.ip"
                ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;

    } else {
        my $path = '/usedNetworkAddressesResult/Network/HostList/Host';
        my $content = "request_type=usedNetworkAddresses&client_name=$client&no_csv=yes&id=$red_num";
        my @values = ("IP", "hostname", "descr", "site", "cat", "int_admin", "comment", "update_type", "alive", "last_response", "range_id","id");
        @values_ip = Gipfuncs::make_call_array("$path", "$content", \@values);
	}


	return @values_ip;
}



sub get_custom_host_columns_from_net_id_hash {
	my ( $client_id,$host_id ) = @_;

	return if $create_csv;

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



sub delete_linked_ip {
	my ( $client_id,$ip_version,$linked_ip_old,$ip,$host_id_linked ) = @_;

	return if $create_csv;

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
		my $ip_int_linked=ip_to_int("$linked_ip_old","$ip_version_ip_old") || "";
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
		update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$host_id_linked","$linked_cc_entry") if ! $test;
	} else {
		delete_single_custom_host_column_entry("$client_id","$host_id_linked","$linked_ip_comp","$pc_id") if ! $test;
	}
}



sub delete_single_custom_host_column_entry {
	my ( $client_id, $host_id, $cc_entry_host, $pc_id ) = @_;

	return if $create_csv;

        my $dbh = mysql_connection();
	my $qhost_id = $dbh->quote( $host_id );
	my $qcc_entry_host = $dbh->quote( $cc_entry_host );
	my $qpc_id = $dbh->quote( $pc_id );
	my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND entry = $qcc_entry_host AND pc_id = $qpc_id"
                                ) or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}


sub update_custom_host_column_value_host_modip {
	my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;

	return if $create_csv;

        my $dbh = mysql_connection();
	my $qcc_id = $dbh->quote( $cc_id );
	my $qpc_id = $dbh->quote( $pc_id );
	my $qhost_id = $dbh->quote( $host_id );
	my $qentry = $dbh->quote( $entry );
	my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id AND cc_id=$qcc_id");
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}


sub get_custom_host_column_entry {
	my ( $client_id, $host_id, $cc_name, $pc_id ) = @_;

	return if $create_csv;

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


sub get_linked_custom_columns_hash {
	my ( $client_id,$red_num,$cc_id,$ip_version ) = @_;

	return if $create_csv;

	my %cc_values;
	my $ip_ref;
        my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qcc_id = $dbh->quote( $cc_id );
	my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT ce.cc_id,ce.pc_id,ce.host_id,ce.entry,h.ip,INET_NTOA(h.ip) FROM custom_host_column_entries ce, host h WHERE ce.cc_id=$qcc_id AND ce.host_id=h.id AND ce.host_id IN ( select id from host WHERE red_num=$qred_num ) AND (h.client_id = $qclient_id OR h.client_id = '9999')")
		or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $ip="";
		my $ip_int = $ip_ref->{'ip'};
		if ( $ip_version eq "v4" ) {
			$ip = $ip_ref->{'INET_NTOA(h.ip)'};
		} else {
			$ip = int_to_ip("$ip_int","$ip_version");
		}
		my $entry = $ip_ref->{entry};
		my $host_id = $ip_ref->{host_id};
		push @{$cc_values{$ip_int}},"$entry","$ip","$host_id";
        }
        $dbh->disconnect;
        return %cc_values;
}

sub get_custom_host_column_values_host_hash {
	my ( $client_id, $red_num ) = @_;

	return if $create_csv;

	my %redes;
	my $ip_ref;
	my $red_num_expr = "" if ! $red_num;
	$red_num_expr = "AND host.red_num = '" . $red_num . "'" if $red_num;
        my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );

	my $sth = $dbh->prepare("SELECT DISTINCT cce.cc_id,cce.host_id,cce.entry,pc.name,pc.id FROM custom_host_column_entries cce INNER JOIN predef_host_columns pc INNER JOIN custom_host_columns cc INNER JOIN host ON cc.column_type_id = pc.id AND cce.cc_id = cc.id AND cce.host_id = host.id WHERE cce.client_id = $qclient_id $red_num_expr ORDER BY pc.id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $cc_id = $ip_ref->{cc_id};
		my $host_id = $ip_ref->{host_id};
		my $entry = $ip_ref->{entry};
		my $name = $ip_ref->{name};
		push @{$redes{"${cc_id}_${host_id}"}},"$entry","$name";
        }
        $dbh->disconnect;
        return %redes;
}



sub get_custom_host_column_ids_from_name {
	my ( $client_id, $column_name ) = @_;

	return if $create_csv;

	my @values;
	my $ip_ref;
        my $dbh = mysql_connection();
	my $qcolumn_name = $dbh->quote( $column_name );
	my $sth;
	$sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcolumn_name") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @values, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values;
}


sub get_host_hash_check {
	my ( $client_id,$first_ip_int,$last_ip_int,$red_num ) = @_;

    my %values_ip = ();
    my $values_ip;

    if ( ! $create_csv ) {
		my $ip_ref;
		my $dbh = mysql_connection();
		my $qfirst_ip_int = $dbh->quote( $first_ip_int );
		my $qlast_ip_int = $dbh->quote( $last_ip_int );
		my $qclient_id = $dbh->quote( $client_id );
		my $qred_num = $dbh->quote( $red_num );

		my $sth = $dbh->prepare("SELECT h.ip, INET_NTOA(h.ip),h.hostname, h.host_descr, h.comentario, h.range_id, h.id, h.red_num, h.ip_version, h.loc, h.categoria, h.update_type, h.int_admin, h.alive FROM host h WHERE h.red_num=$qred_num AND h.client_id = $qclient_id ORDER BY h.ip") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		my $i=0;
		my $j=0;
		my $k=0;
		while ( $ip_ref = $sth->fetchrow_hashref ) {
			my $ip_version = $ip_ref->{'ip_version'};
			my $hostname = $ip_ref->{'hostname'} || "";
			my $range_id = $ip_ref->{'range_id'} || "";
			my $ip_int = $ip_ref->{'ip'} || "";
			my $ip;
			if ( $ip_version eq "v4" ) {
				$ip = $ip_ref->{'INET_NTOA(h.ip)'};
			} else {
				$ip = int_to_ip("$ip_int","$ip_version");
			}
			my $host_descr = $ip_ref->{'host_descr'} || "";
			my $comentario = $ip_ref->{'comentario'} || "";
			my $id = $ip_ref->{'id'} || "";
			my $red_num = $ip_ref->{'red_num'} || "";
			my $loc_id = $ip_ref->{'loc'} || "";
			my $cat_id = $ip_ref->{'categoria'} || "";
			my $utype_id = $ip_ref->{'update_type'} || "";
			my $int_admin = $ip_ref->{'int_admin'} || "";
			my $alive = $ip_ref->{'alive'} || "";
			push @{$values_ip{$ip_int}},"$ip","$hostname","$host_descr","$comentario","$range_id","$ip_int","$id","$red_num","$client_id","$ip_version","$loc_id","$cat_id","$utype_id","$int_admin","$alive";

		}

		$values_ip = \%values_ip;

		$dbh->disconnect;

	} else {
		my $path = '/usedNetworkAddressesResult/Network/HostList/Host';
		my $content = "request_type=usedNetworkAddresses&client_name=$client&no_csv=yes&id=$red_num";
		my @values = ("IP", "hostname", "descr", "comment", "range_id", "ip_int", "id", "red_num", "client_id", "ip_version", "loc_id", "cat_id", "utype_id", "int_admin", "alive");

		$values_ip = Gipfuncs::make_call_hash("$path", "$content", \@values, "ip_int");
	}

    return $values_ip;
}



sub get_redes_hash_key_red {
	my ( $client_id,$ip_version,$return_int ) = @_;
	my $ip_ref;
	$ip_version="" if ! $ip_version;
	$return_int="" if ! $return_int;
	my %values_redes;
	my $values_redes;
	if ( ! $create_csv ) {
		my $dbh = mysql_connection();
		my $qclient_id = $dbh->quote( $client_id );

		my $ip_version_expr="";
		$ip_version_expr="AND n.ip_version='$ip_version'" if $ip_version;

		my $sth = $dbh->prepare("SELECT n.red_num, n.red, n.BM, n.descr, l.loc, l.id, n.vigilada, n.comentario, c.cat, n.ip_version, INET_ATON(n.red), n.rootnet, n.dyn_dns_updates FROM net n, categorias_net c, locations l WHERE c.id = n.categoria AND l.id = n.loc AND n.rootnet = 0 AND n.client_id=$qclient_id $ip_version_expr") 
			or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
			$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
			while ( $ip_ref = $sth->fetchrow_hashref ) {
				my $red_num = $ip_ref->{'red_num'} || "";
				my $red = $ip_ref->{'red'} || "";
				my $BM = $ip_ref->{'BM'};
				my $descr = $ip_ref->{'descr'};
				my $loc = $ip_ref->{'loc'} || "";
				my $loc_id = $ip_ref->{'id'} || "";
				my $cat = $ip_ref->{'cat'} || "";
				my $vigilada = $ip_ref->{'vigilada'} || "";
				my $comentario = $ip_ref->{'comentario'} || "";
				my $ip_version = $ip_ref->{'ip_version'} || "";
				my $red_int;
				if ( ! $return_int ) {
					$red_int="";
				} else {
					if ( $ip_version eq "v4" ) {
						$red_int=$ip_ref->{'INET_ATON(n.red)'};
					} else {
						# macht die sache langsam ....
						$red_int = ip_to_int("$client_id",$red,"$ip_version");
					}
				}
				my $rootnet=$ip_ref->{'rootnet'};
				my $dyn_dns_updates=$ip_ref->{'dyn_dns_updates'} || "";

				push @{$values_redes{$red}},"$red_num","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$loc_id","$dyn_dns_updates";
				
				$values_redes = \%values_redes;
			}

			$dbh->disconnect;
		} else {
			my $path = '/listNetworksResult/NetworkList/Network';
			my $content = "request_type=listNetworks&client_name=$client&no_csv=yes";
			my @values = ("id", "BM", "descr", "site", "cat", "sync", "comment", "ip_version", "ip_int", "rootnet", "loc_id", "dyn_dns_updates");

			$values_redes = Gipfuncs::make_call_hash("$path", "$content", \@values, "ip");
		}

        return $values_redes;
}


### Network usage column

sub update_net_usage_cc_column {
    my ($client_id, $ip_version, $red_num, $BM) = @_;

	return if $create_csv;

    my ($ip_total, $ip_ocu, $free) = get_red_usage("$client_id", "$ip_version", "$red_num", "$BM");
    my $cc_id_usage = get_custom_column_id_from_name("$client_id", "usage") || "";
    my $cc_usage_entry = "$ip_total,$ip_ocu,$free" || "";
    update_or_insert_custom_column_value_red("$client_id", "$cc_id_usage", "$red_num", "$cc_usage_entry") if $cc_id_usage && $cc_usage_entry && ! $test;
}


sub get_red_usage {
    my ( $client_id, $ip_version, $red_num, $BM) = @_;

    if ( ! $BM || ! $ip_version ) {
		if ( ! $create_csv ) {
			my @values_redes=get_red("$client_id","$red_num");
			$BM = "$values_redes[0]->[1]" || "";
			$ip_version = "$values_redes[0]->[7]" || "";
		} else {
			# not used
			my $path = '/readNetworkResult/Network';
			my $content = "request_type=readNetwork&client_name=$client&id=$red_num";
			my @values = ("BM", "ip_version");
			my @res = Gipfuncs::make_call_array("$path", "$content", \@values);
			$BM = $res[0]->[0];
			$ip_version = $res[0]->[1];
		}
    }

    my %anz_hosts = get_anz_hosts_bm_hash("$client_id","$ip_version");
    my $ip_total=$anz_hosts{$BM};
	$ip_total =~ s/,//g;


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
#        $ocu_color = "green";
    } elsif ( $ip_ocu == $ip_total ) {
        $percent_ocu = '100%';
#        $ocu_color = "red";
    } else {
        $ip_total_calc = $ip_total . ".0";
        $percent_ocu=100*$ip_ocu/$ip_total_calc;
        if ( $percent_ocu =~ /e/ ) {
            $percent_ocu="0.1"
        } else {
            $percent_ocu =~ /^(\d+\.?\d?).*/;
            $percent_ocu = $1;
        }
        if ( $percent_ocu >= 90 ) {
#            $ocu_color = "red";
        } elsif ( $percent_ocu >= 80 ) {
#            $ocu_color = "darkorange";
        } else {
#            $ocu_color = "green";
        }
        $percent_ocu = $percent_ocu . '%';
    }

    return ($ip_total, $ip_ocu, $free);
}


sub get_custom_column_id_from_name {
    my ( $client_id, $name ) = @_;

    my $id;
	if ( ! $create_csv ) {
		my $dbh = mysql_connection();
		my $qname = $dbh->quote( $name );
		my $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qname
							") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$id = $sth->fetchrow_array;
		$sth->finish();
		$dbh->disconnect;
	} else {
		# not used
#        my $path = '/listCustomNetworkColumns/networkColumns/column';
#        my $content = "request_type=listNetworks&client_name=$client";
#        my @values = ("id", "name", "mandatory");
#        my @column_values = Gipfuncs::make_call_array("$path", "$content", \@values);
#
#		foreach $val ( @column_values ) {
#			my $id_found = $val->[0] || "";
#			my $name_found = $val->[1] || "";
#			if ( $name eq $name_found ) {
#				$id = $id_found;
#			}
#		}
	}
    return $id;
}


sub update_or_insert_custom_column_value_red {
    my ( $client_id, $cc_id, $net_id, $entry ) = @_;

	return if $create_csv;

    my $dbh = mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qnet_id = $dbh->quote( $net_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id");
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

sub count_host_entries {
    my ( $client_id, $red_num ) = @_;
    my $count_host_entries;
	if ( ! $create_csv ) {
		my $dbh = mysql_connection();
		my $qred_num = $dbh->quote( $red_num );
		my $qclient_id = $dbh->quote( $client_id );
		my $sth = $dbh->prepare("SELECT COUNT(*) FROM host WHERE red_num=$qred_num AND hostname != 'NULL' AND hostname != '' AND client_id = $qclient_id");
		$sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$count_host_entries = $sth->fetchrow_array;
		$sth->finish();
		$dbh->disconnect;
	} else {
		# not used
		my $path = '/readNetworkResult/Network/customColumns';
		my $content = "request_type=readNetwork&client_name=$client&id=$red_num";
		my @values = ("usage");
		my $usage = Gipfuncs::make_call_value("$path", "$content", \@values);
		$usage =~ /\d+,(\d+),\d+/;
		$count_host_entries = $1;
	}
    return $count_host_entries;
}

sub get_host_red_num {
    my ( $client_id, $values_host_redes, $check_ip, $ip_version, $last_red, $last_BM, $last_red_num ) = @_;

	if ( $last_red ) {
		# check if ip is from the same network of the last ip
        my $last_redob = "$last_red/$last_BM";
        my $ipob_redes = new Net::IP ($last_redob) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $last_redob\n";
        my $ipm = "$check_ip/32";
        $ipm = "$check_ip/128" if $ip_version eq "v6";
        my $ipm_ip = new Net::IP ($ipm) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $ipm\n";
        if ( $ipm_ip->overlaps($ipob_redes) == $IP_A_IN_B_OVERLAP ) {
            # ip is within the last network
			return ( $last_red, $last_BM, $last_red_num);
        }
	}

	my @values_host_redes = @$values_host_redes;
	my ($red, $BM, $red_num);
	$red=$BM=$red_num="";

    my $k = 0;
    foreach ( @values_host_redes ) {
        if ( ! $values_host_redes[$k]->[0] || $values_host_redes[$k]->[5] == 1  ) {
            $k++;
            next;
        }

        my $ip_version_checkred = $values_host_redes[$k]->[4];

        if ( $ip_version ne $ip_version_checkred ) {
            $k++;
            next;
        }

        $red = $values_host_redes[$k]->[0];
        $BM = $values_host_redes[$k]->[1];
        $red_num = $values_host_redes[$k]->[2];

        if ( $ip_version eq "v4" ) {
            $red =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $third_host_red_oct=$3;
            $check_ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $third_host_oct=$3;
            if (  $BM >= 24 && $third_host_red_oct != $third_host_oct ) {
                $k++;
                next;
            }
        }

        my $redob_redes = "$red/$BM";
        my $ipob_redes = new Net::IP ($redob_redes) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $redob_redes\n";
        my $ipm = "$check_ip/32";
        $ipm = "$check_ip/128" if $ip_version eq "v6";
        my $ipm_ip = new Net::IP ($ipm) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $ipm\n";
        if ( $ipm_ip->overlaps($ipob_redes) == $IP_A_IN_B_OVERLAP ) {
            # overlap
            return ($red, $BM, $red_num);
        }

        $k++;
    }
	
	return ("", "", "");
}

sub compare_hashes {
    my ($reverse_records, $reverse_records_zone, $ip_version) = @_;

    my %new_hash;

	# prefere PTR records
	my $generic_auto;
    foreach my $k (keys %{ $reverse_records_zone }) {
		$generic_auto = get_generic_auto("$k", "$ip_version");
        if ( $ignore_generic_auto =~ /^yes$/i && $reverse_records_zone->{$k} !~ /$generic_auto/) {
			$new_hash{$k} = $reverse_records_zone->{$k};
		} elsif ( $ignore_generic_auto =~ /^no$/i ) {
			$new_hash{$k} = $reverse_records_zone->{$k};
		}
    }

	# use A record if no PTR record defined
    foreach my $k (keys %{ $reverse_records }) {
        if (not exists $new_hash{$k}) {
			$generic_auto = get_generic_auto("$k", "$ip_version");
			if ( $ignore_generic_auto =~ /^yes$/i && $reverse_records->{$k} !~ /$generic_auto/) {
				$new_hash{$k} = $reverse_records->{$k};
			} elsif ( $ignore_generic_auto =~ /^no$/i ) {
				$new_hash{$k} = $reverse_records->{$k};
			}
        }
    }

    return \%new_hash;
}


sub get_generic_auto {
    my ($ip, $ip_version) = @_;

	my $generic_auto = "";
	if ( $ip_version eq "v4" ) {
		$ip =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
		$generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
	} else {
		$ip =~ /^(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+)$/;
		$generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
	}

	return $generic_auto;
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

#sub update_job_status {
#    my ( $gip_job_status_id, $status, $end_time, $exit_message, $log_file ) = @_;
#
#    $status = "" if ! $status;
#    $exit_message = "" if ! $exit_message;
#    $end_time = "" if ! $end_time;
#    $log_file = "" if ! $log_file;
#
#    if ( $delete_job_error ) {
#        if ( $status != 4 ) {
#            # warning
#            $status = 5;
#        }
#    }
#
#    my $dbh = mysql_connection();
#
#    my $qgip_job_status_id = $dbh->quote( $gip_job_status_id );
#    my $qstatus = $dbh->quote( $status );
#    my $qend_time = $dbh->quote( $end_time );
#    my $qlog_file = $dbh->quote( $log_file );
#    my $qexit_message = $dbh->quote( $exit_message );
#
#    if ( ! $status && ! $exit_message && ! $end_time && ! $log_file ) {
#        return;
#    }
#
#    my $expr = "";
#    $expr .= ", status=$qstatus" if $status;
#    $expr .= ", exit_message=$qexit_message" if $exit_message;
#    $expr .= ", end_time=$qend_time" if $end_time;
#    $expr .= ", log_file=$qlog_file" if $log_file;
#    $expr =~ s/^,//;
#
#    print "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug;
##   print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug && fileno LOG;
#    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
#
#    $sth->execute() or Gipfuncs::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
#    $sth->finish();
#    $dbh->disconnect;
#}

#sub exit_error {
#    my ( $message, $gip_job_status_id, $status, $exit_signal ) = @_;
#
#	$exit_signal = "1" if ! $exit_signal;
#    $exit_signal = "0" if $exit_signal eq "OK";
#
#    print $message . "\n";
#    print LOG $message . "\n" if fileno LOG;
#
#    if ( $gip_job_status_id && ! $combined_job ) {
#        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning
#
##        my $time = scalar(localtime(time + 0));
#        my $time=time();
#
#        Gipfuncs::update_job_status("$gip_job_status_id", "$status", "$time", "$message");
#    }
#
#    close LOG if fileno LOG;
#
#    Gipfuncs::send_mail (
#        debug       =>  "$debug",
#        mail_from   =>  $mail_from,
#        mail_to     =>  \@mail_to,
#        subject     => "Result $job_name",
#        smtp_server => "$smtp_server",
#        smtp_message    => "",
#        log         =>  "$log",
#        gip_job_status_id   =>  "$gip_job_status_id",
#        changes_only   =>  "$changes_only",
#    ) if $mail;
#
#    exit $exit_signal;
#}

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

__DATA__
