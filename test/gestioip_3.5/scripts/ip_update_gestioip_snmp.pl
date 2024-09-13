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


# ip_update_gestioip_snmp.pl Version 3.5.6 20210416
# not compatible with version <= 3.5.3

# script to actualize GestioIP's database via SNMP queries

# This scripts synchronizes only the networks of GestioIP with marked "sync"-field
# see documentation for further information (www.gestioip.net)
 

# Usage: ./ip_update_gestioip_snmp.pl --help

# execute it from cron. Example crontab:
# 30 10 * * * /usr/share/gestioip/bin/ip_update_gestioip_snmp.pl -o -m > /dev/null 2>&1


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
use Mail::Mailer;
use Socket;
use Parallel::ForkManager;
use Fcntl qw(:flock);
use Net::DNS;
use SNMP;
use SNMP::Info;
use POSIX;


my $VERSION="3.5.0";
my $CHECK_VERSION="3";

	 
$dir =~ /^(.*)\/bin/;
$base_dir=$1;

my ( $disable_audit, $test, $help, $version_arg, $community_arg, $location_args, $snmp_port_arg, $use_arp_cache_devices_file, $process31, $ignore_arp_cache );
my $config_name="";
my $network_file="";
my $network_list="";
my $only_added_mail=0;

my ( $snmp_version_arg, $snmp_user_name_arg, $sec_level_arg, $auth_proto_arg, $auth_pass_arg, $priv_proto_arg, $priv_pass_arg, $logdir, $actualize_ipv4, $actualize_ipv6, $dyn_ranges_only, $max_sinc_procs, $tag, $ip_range, $gip_job_id, $user, $combined_job, $snmp_group_arg, $run_once, $location_scan, $document_root);
$snmp_version_arg=$snmp_user_name_arg=$sec_level_arg=$auth_proto_arg=$auth_pass_arg=$priv_proto_arg=$priv_pass_arg=$logdir=$actualize_ipv4=$actualize_ipv6=$dyn_ranges_only=$max_sinc_procs=$tag=$ip_range=$gip_job_id=$user=$combined_job=$document_root=$snmp_group_arg=$run_once=$location_scan="";

our $verbose = 0;
our $debug = 0;
our $client = "";
our $ignore_generic_auto = "no";
our $smtp_server = "";
our $mail_from = "";
our $mail_to = "";
our $changes_only = "";
our $log = "";
our $mail = "";

GetOptions(
	"verbose!"=>\$verbose,
	"Version!"=>\$version_arg,
	"x!"=>\$debug,
	"log=s"=>\$log,
	"config_file_name=s"=>\$config_name,
    "changes_only!"=>\$changes_only,
    "combined_job!"=>\$combined_job,
	"Location=s"=>\$location_args,
    "Location_scan=s"=>\$location_scan,
	"disable_audit!"=>\$disable_audit,
    "document_root=s"=>\$document_root,
	"ignore_arp_cache!"=>\$ignore_arp_cache,
	"Network_file=s"=>\$network_file,
	"CSV_networks=s"=>\$network_list,
	"mail!"=>\$mail,
	"smtp_server=s"=>\$smtp_server,
	"mail_from=s"=>\$mail_from,
	"mail_to=s"=>\$mail_to,
	"only_added_mail!"=>\$only_added_mail,
	"process31!"=>\$process31,
    "range=s"=>\$ip_range,
	"run_once!"=>\$run_once,
	"use_arp_cache_devices_file=s"=>\$use_arp_cache_devices_file,
    "user=s"=>\$user,
	"snmp_port=s"=>\$snmp_port_arg,
	"snmp_group=s"=>\$snmp_group_arg,
	"tag=s"=>\$tag,
	"help!"=>\$help,

	"A=s"=>\$client,
	"B=s"=>\$ignore_generic_auto,
#        "C=s"=>\$descend,
	"D=s"=>\$snmp_version_arg,
    "E=s"=>\$community_arg,
	"F=s"=>\$snmp_user_name_arg,
	"G=s"=>\$sec_level_arg,
	"H=s"=>\$auth_proto_arg,
	"I=s"=>\$auth_pass_arg,
	"J=s"=>\$priv_proto_arg,
	"K=s"=>\$priv_pass_arg,
	"M=s"=>\$logdir,
	"T=s"=>\$actualize_ipv4,
	"O=s"=>\$actualize_ipv6,
#	"R!"=>\$dyn_ranges_only,
	"S=s"=>\$max_sinc_procs,
    "W=s"=>\$gip_job_id,
) or print_help("Argument error");

$debug=0 if ! $debug;
$verbose=1 if $debug;
$mail=1 if $only_added_mail;

if ( $document_root && ! -r "$document_root" ) {
    print "document_root not readable\n";
    exit 1;
}

# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = get_db_parameter("$document_root");

if ( ! $pass_gestioip ) {
    print "Database password not found\n";
    exit 1;
}

my $client_count = count_clients();
if ( $client_count = 1 && ! $client ) {
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

my $enable_audit = "1";
$enable_audit = "0" if $test || $disable_audit;

my $job_name;
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
        $job_name = Gipfuncs::get_job_name("$gip_job_id") || "";
        my $audit_type="176";
        my $audit_class="33";
        my $update_type_audit="2";

        my $event="$job_name ($gip_job_id)";
        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
    }
}


my $exit_message = "";

print "Debugging enabled\n" if $debug;

my $start_time=time();

my $datetime;
my $gip_job_status_id = "";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "ip_update_gestioip_snmp");

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;

my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime get_networks_snmp.pl $gip_job_id_message\n\n";

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

$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
    $exit_message = "Can't find configuration file \"$config_name\"";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}
my $conf = $base_dir . "/etc/" . $config_name;


if ( $help ) { print_help(); }
if ( $version_arg ) { print_version(); }
if ( $test && ! $verbose ) {
    $exit_message = "test option needs the -v arg";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}




my %params;

open(VARS,"<$conf") or exit_error("Can not open $conf: $!", "$gip_job_status_id", 4);
while (<VARS>) {
	chomp;
	s/#.*//;
	s/^\s+//;
	s/\s+$//;
	next unless length;
	my ($var, $value) = split(/\s*=\s*/, $_, 2);
	$params{$var} = $value;
}
close VARS;



my $gip_version=get_version();

if ( $gip_version !~ /^$CHECK_VERSION/ ) {
	$exit_message = "Script and GestioIP version are not compatible\n\nGestioIP version: $gip_version - script version: ${CHECK_VERSION}.x";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}

my %lang_vars;

open(LANGVARS,"<$vars_file") or exit_error("Can not open $vars_file: $!", "$gip_job_status_id", 4);
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

my $lockfile = $base_dir . "/var/run/" . $client . "_ip_update_gestioip_snmp.lock";

no strict 'refs';
open($lockfile, '<', $0) or exit_error("Unable to create lock file: $!", "$gip_job_status_id", 4);
use strict;

unless (flock($lockfile, LOCK_EX|LOCK_NB)) {
	$exit_message = "$0 is already running - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 6 );
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


my @global_config = get_global_config("$client_id");
my $mib_dir=$global_config[0]->[3] || "";
my $vendor_mib_dirs=$global_config[0]->[4] || "";

my @vendor_mib_dirs = split(",",$vendor_mib_dirs);
my @mibdirs_array;
foreach ( @vendor_mib_dirs ) {
        my $mib_vendor_dir = $mib_dir . "/" . $_;
        if ( ! -e $mib_vendor_dir ) {
			$exit_message = "$lang_vars{mib_dir_not_exists} - exiting";
			exit_error("$exit_message", "$gip_job_status_id", 4 );

			if ( ! -r $mib_vendor_dir ) {
				$exit_message = "$lang_vars{mib_dir_not_readable}: $mib_vendor_dir - exiting";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			}
        }
        push (@mibdirs_array,$mib_vendor_dir);

}

my $mibdirs_ref = \@mibdirs_array;


my $ipv4 = $actualize_ipv4 || $params{actualize_ipv4_dns};
if ( $ipv4 && $ipv4 !~ /^yes|no/i ) {
#    print "actualize_ipv4 (-T) must be \"yes\" or \"no\"\n";
    $exit_message = "actualize_ipv4 (-T) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4 );
    } else {
        print_help("$exit_message");
    }
}
$ipv4="yes" if $ipv4 !~ /^no$/i;
my $ipv6 = $actualize_ipv6 || $params{actualize_ipv6_dns};
if ( $ipv6 && $ipv6 !~ /^yes|no/i ) {
    $exit_message = "actualize_ipv4 (-O) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4 );
    } else {
        print_help("$exit_message");
    }
}
$ipv6="yes" if $ipv6 !~ /^no$/i;


#TAGs

my @tag;
my $tag_ref = "";
if ( $tag ) {
    @tag = split(",", $tag);
    $tag_ref = \@tag;
}


#### SNMP

$ignore_generic_auto = $ignore_generic_auto || $params{ignore_generic_auto};
if ( $ignore_generic_auto && $ignore_generic_auto !~ /^yes|no/i ) {
	$exit_message = "ignore_generic_auto (-B) must be \"yes\" or \"no\"";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4 );
    } else {
        print_help("$exit_message");
    }
}

my $snmp_group_id_arg = "";
if ( $snmp_group_arg ) {
    $snmp_group_id_arg = get_snmp_group_id_from_name("$client_id","$snmp_group_arg");
    exit_error("SNMP group not found", "$gip_job_status_id", 4 ) if ! $snmp_group_id_arg;
}

my $count_entradas_dns=0;
my $count_entradas_dns_timeout=0;

print LOG "\n######## Update via SNMP ($datetime) ########\n\n";
if ( $test ) {
	print LOG "\n--- $lang_vars{test_mod_message} ---\n";
	print "\n--- $lang_vars{test_mod_message} ---\n";
}

my @vigilada_redes=();
#my $redes_hash=get_redes_hash_key_red("$client_id", "", "", $tag_ref);
my $redes_hash=get_redes_hash_key_red("$client_id");

if (($network_file && $network_list) || ($network_file && $tag) || ($network_list && $tag) || ($network_list && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
if (($ip_range && $network_list) || ($ip_range && $network_file) || ($ip_range && $tag) || ($ip_range && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}
if (($location_scan && $network_list) || ($location_scan && $network_file) || ($location_scan && $tag) || ($ip_range && $location_scan)) {
    $exit_message = "Only one of the option \"network_file\" or \"list_of_networks\" or \"tag\" or \"ip_range\" or \"Location_scan\" is allowed";
    if ( $gip_job_status_id ) {
        exit_error("$exit_message", "$gip_job_status_id", 4);
    } else {
        print_help("$exit_message");
    }
}

if ( $network_file ) {
    my $network_file_full = "";
    $network_file_full = "$base_dir/etc/$network_file";
    if ( ! -e $network_file_full && -r "$base_dir/var/data/$network_file" ) {
        $network_file_full = "$base_dir/var/data/$network_file";
    }
    $network_file = $network_file_full;
	print LOG "\nUsing network file $network_file\n" if $debug;
    exit_error("Network file not found ($network_file)", "$gip_job_status_id", 4) if ! -e $network_file;
}

my %ip_range_ips;
if ( $network_file || $network_list ) {
	my @pnetworks=();

	if ( $network_list ) {
		@pnetworks=split(",",$network_list);


		print "Reading networks from csv list...\n" if $verbose;
		print LOG  "Reading networks from csv list...\n";
        print LOG "DEBUG: network_list: $network_list\n" if $debug; 
        if ( $debug ) {
            foreach ( @pnetworks ) {
                print LOG "DEBUG P_NETWORK: $_\n";
            }
        }
	} elsif ( $network_file ) {
		open(NETWORKS,"<$network_file") or exit_error("Can not open networks file: $network_file: $!", "$gip_job_status_id", 4);
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
			my @red_arr=("$red","$BM","$rred_num","$rloc_id");
			push (@vigilada_redes,\@red_arr);

		} else {
			print "Network not found in database: $red/$BM - $lang_vars{ignorado_message}\n" if $verbose;
			print LOG  "Network not found in database: $red/$BM - $lang_vars{ignorado_message}\n";
		}
	}

	$network_count=scalar(@vigilada_redes);

	if ( $network_count == 0 ) {
        $exit_message = "Found $network_count networks to process";
		exit_error("$exit_message", "$gip_job_status_id", 3, "OK" );
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
        $exit_message = "IP range invalid. Range must be introduced in the format --range=IP1-IP2. Ejemplo: --range=1.1.1.3-1.1.1.10";
        if ( $gip_job_status_id ) {
            exit_error("$exit_message", "$gip_job_status_id", 4 );
        } else {
            print_help("$exit_message");
        }
    }

    if ( ! $ip1 || ! $ip2 ) {
        $exit_message = "IP range invalid. Range must be introduced in the format --range=IP1-IP2. Ejemplo: --range=1.1.1.3-1.1.1.10";
        if ( $gip_job_status_id ) {
            exit_error("$exit_message", "$gip_job_status_id", 4 );
        } else {
            print_help("$exit_message");
        }
    }

    my $err;
    my $ipob = new Net::IP ("$ip1 - $ip2") or $err = "Can not create range $ip1 - $ip2\n";
    if ( $err ) {
		exit_error("$err", "$gip_job_status_id", 4 );
    }

    my @values_host_redes = get_host_redes_no_rootnet("$client_id");

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
#           my @red_arr=("$red","$BM","$red_num","$rloc_id","$rdyn_dns_updates");
            push (@vigilada_redes,\@red_arr) if $red_num ne $red_num_old;
        }

    } while (++$ipob);

    print "Found addresses from " . scalar @vigilada_redes . " networks\n" if $verbose;
    print LOG "Found addresses from " . scalar @vigilada_redes . " networks\n" if $verbose;

} elsif ( $location_scan ) {
    $location_scan =~ s/^\s+//g;
    $location_scan =~ s/\s+$//g;
    $location_scan =~ s/,\s+/,/g;
    my $db_locations = get_loc_hash("$client_id");
    my @location_array_names_scan = split /,/, $location_scan;
    my $location_scan_ids = "";
    foreach ( @location_array_names_scan ) {
        if ( defined($db_locations->{$_} )) {
            $location_scan_ids .= "," .  $db_locations->{$_};
        } else {
            print "\nWARNING: Site not found: $_: ignored\n" if $verbose;
            print LOG "\nWARNING: Site not found: $_: ignored\n";
        } 
        $location_scan_ids =~ s/^,//;
    }
    @vigilada_redes=get_vigilada_redes("$client_id", "", "v4", "", "$location_scan_ids");


} elsif ( $ipv4 eq "yes" && $ipv6 eq "no" ) {
	@vigilada_redes=get_vigilada_redes("$client_id", "", "v4", $tag_ref);
} elsif ( $ipv4 eq "no" && $ipv6 eq "yes" ) {
	@vigilada_redes=get_vigilada_redes("$client_id", "", "v6", $tag_ref);
} else {
	@vigilada_redes=get_vigilada_redes("$client_id", "", "", $tag_ref);
}


my %location_ids_args=();
my @location_array_names=();
my $db_locations="";
$location_args="" if ! $location_args;
my $locations_conf=$params{process_only_locations} || "";
my $process_locations=$location_args || "";
if ( $process_locations ) {
	$process_locations=$process_locations . ","  . $locations_conf if $process_locations;
} else {
	$process_locations=$locations_conf if $locations_conf;
}


$process_locations =~ s/^\s+//g if $process_locations;
$process_locations =~ s/\s+$//g if $process_locations;
$process_locations =~ s/,\s+/,/g if $process_locations;
if ( $process_locations ) {
	my $db_locations = get_loc_hash("$client_id");
	my @location_array_names = split /,/, $process_locations;
	foreach ( @location_array_names ) {
		if ( ! defined($db_locations->{$_} )) {
			$exit_message = "Location \"$_\" doesn't exists - location must be equal to the location in the GestioIP database - $lang_vars{exiting_message}";
			exit_error("$exit_message", "$gip_job_status_id", 4 );
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
	$exit_message = "$lang_vars{no_sync_redes}";
	exit_error("$exit_message", "$gip_job_status_id", 4, "OK" );
}

my $network_count=scalar(@vigilada_redes);
print "Found $network_count networks to process\n" if $verbose;
print LOG "Found $network_count networks to process\n";


if ( $vigilada_redes[0]->[1] ) {
	my $audit_type="44";
	my $audit_class="1";
	my $update_type_audit="3";
	my $event="---";
	insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
}


my %use_arp_cache_devices;
if ( $use_arp_cache_devices_file ) {
#
	print "Reading $use_arp_cache_devices_file...\n" if $verbose;
	print LOG "Reading $use_arp_cache_devices_file...\n";
#
	open(ARP_DEVICES,"<$use_arp_cache_devices_file") or exit_error("Can not open $use_arp_cache_devices_file: $!", "$gip_job_status_id", 4);
	while (<ARP_DEVICES>) {
		next if $_ =~ /^#/;
		$_=~s/\n//;
		if ( $_ =~ /.+\/\d+/ ) {
			# network - add all addresses of this network to %use_arp_cache_devices
			$_=~ /^(.+)\/(\d+)/;
			my $ured=$1;
			my $uBM=$2;
			my $ip_version="v4";
			$ip_version="v6" if $ured !~ /^\d{1,3}\./;
			if ( ${$redes_hash}{$ured} ) {
				my $uredob="$ured/$uBM";
				my $ipob = new Net::IP ($uredob) or print LOG "error: $lang_vars{comprueba_red_BM_message} (2): $ured/$uBM\n";
				my $redint=($ipob->intip());
				$redint = Math::BigInt->new("$redint");
				my $first_ip_int = $redint;
				if ( $ip_version eq "v4" && $uBM < 31 ) {
					$first_ip_int = $redint + 1;
				}
				$first_ip_int = Math::BigInt->new("$first_ip_int");
				my $last_ip_int = ($ipob->last_int());
				$last_ip_int = Math::BigInt->new("$last_ip_int");
				if ( $ip_version eq "v4" && $uBM < 31 ) {
					$last_ip_int = $last_ip_int - 1;
				}
				for ( my $i=$first_ip_int; $i <= $last_ip_int; $i++) {
					my $uip=int_to_ip("$i","$ip_version");
					$use_arp_cache_devices{$uip}++;
				}
			}
		} else {
			# host
			$use_arp_cache_devices{$_}++;
		}
	}
	close ARP_DEVICES;
}


my @client_entries=get_client_entries("$client_id");
my $default_resolver = $client_entries[0]->[20];
#my @dns_servers =("$client_entries[0]->[21]");
#push @dns_servers, $client_entries[0]->[22] if $client_entries[0]->[22];
#push @dns_servers, $client_entries[0]->[23] if $client_entries[0]->[23];

my %predef_host_columns=get_predef_host_column_all_hash("$client_id");

my $l=0;
my %res_sub;
my %res;
my ($first_ip_int,$last_ip_int);
my @zone_records;
my $zone_name;

my $ip_version;
my @values_host_redes = get_host_redes_no_rootnet("$client_id");

foreach (@vigilada_redes) {

    my $red="$vigilada_redes[$l]->[0]";
    my $BM="$vigilada_redes[$l]->[1]";
    my $red_num="$vigilada_redes[$l]->[2]";


    # get DNS servers
	my @dns_servers;
    my $dns_server_group_id = get_custom_column_entry("$client_id","$red_num","DNSSG") || "";
    my $dns_server_group_name;
    my @dns_server_group_values;
    if ( $dns_server_group_id ) {
        # check for DNS server group
        @dns_server_group_values = get_dns_server_group_from_id("$client_id","$dns_server_group_id");
    }
    if ( @dns_server_group_values ) {
        $dns_server_group_name = $dns_server_group_values[0]->[0];
        push @dns_servers, $dns_server_group_values[0]->[2] if $dns_server_group_values[0]->[2];
        push @dns_servers, $dns_server_group_values[0]->[3] if $dns_server_group_values[0]->[3];
        push @dns_servers, $dns_server_group_values[0]->[4] if $dns_server_group_values[0]->[4];
    } else {
        push @dns_servers, $client_entries[0]->[21] if $client_entries[0]->[21];
        push @dns_servers, $client_entries[0]->[22] if $client_entries[0]->[22];
        push @dns_servers, $client_entries[0]->[23] if $client_entries[0]->[23];
    }


    # get snmp parameter
    my ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port, $snmp_group_name) = get_snmp_parameter("$client_id", "$red_num", "network", "$snmp_group_id_arg");

	$dyn_ranges_only = $dyn_ranges_only || $params{dyn_rangos_only};
	if ( $dyn_ranges_only eq "yes" ) {
		print "\n($lang_vars{sync_only_rangos_message})\n\n" if $verbose;
		print LOG "\n($lang_vars{sync_only_rangos_message})\n\n" if $verbose;
	} else {
#		print "\n";
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

	my ($descr, $loc_id, $ip_version);
	if ( ${$redes_hash}{$red} ) {
		$descr = ${$redes_hash}{$red}->[2];
		$loc_id = ${$redes_hash}{$red}->[10];
		$ip_version = ${$redes_hash}{$red}->[7];
	} else {
		my @values_redes = get_red("$client_id","$red_num");

		if ( ! $values_redes[0] ) {
			print "$lang_vars{algo_malo_message}\n";
			print LOG "$lang_vars{algo_malo_message}\n";
		}

		$descr = "$values_redes[0]->[2]" || "";
		$loc_id = "$values_redes[0]->[3]" || "";
		$ip_version = "$values_redes[0]->[7]" || "";
	}

	my $redob = "$red/$BM";
	my $host_loc = get_loc_from_redid("$client_id","$red_num");
	$host_loc = "---" if $host_loc eq "NULL";
	my $host_cat = "---";


	if ( ! $ipv4 &&  $ip_version eq "v4" ) {
		$l++;
		next;
	} elsif ( ! $ipv6 &&  $ip_version eq "v6" ) {
		$l++;
		next;
	}

	if ( $BM > 30 && $ip_version eq "v4" && ! $process31) {
                print "$red/$BM: Bitmask > 30 - $lang_vars{ignorado_message}\n" if $verbose;
                print LOG "$red/$BM: Bitmask > 30 - $lang_vars{ignorado_message}\n";
                $l++;
                next;
    }

	my $smallest_bm4="16";
	my $smallest_bm6="64";

	if ( $ip_version eq "v4" && $BM < $smallest_bm4 ) {
		print "$lang_vars{smalles_bm_manage_message}: $smallest_bm4 < $BM $lang_vars{ignorado_message}\n\n" if $verbose;
		print LOG "$lang_vars{smalles_bm_manage_message}: $smallest_bm4 < $BM $lang_vars{ignorado_message}\n\n";
		$l++;
		next;
	} elsif ( $ip_version eq "v6" && $BM < $smallest_bm6 ) {
		print "$lang_vars{smalles_bm_manage_message}: $smallest_bm6 $lang_vars{ignorado_message}\n\n" if $verbose;
		print LOG "$lang_vars{smalles_bm_manage_message}: $smallest_bm6 $lang_vars{ignorado_message}\n\n";
		$l++;
		next;
	}


	print "\n$red/$BM\n" if $verbose;
	print LOG "\n$red/$BM\n";
    print "using DNS server group $dns_server_group_name\n" if $dns_server_group_name && $verbose;
    print LOG "using DNS server group $dns_server_group_name\n" if $dns_server_group_name && $verbose;
    print "using SNMP group $snmp_group_name\n" if $snmp_group_name && $verbose;
    print LOG "using SNMP group $snmp_group_name\n" if $snmp_group_name && $verbose;
	print "\n" if $verbose;


	my $ipob = new Net::IP ($redob) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $red/$BM\n";
	my $redint=($ipob->intip());
	$redint = Math::BigInt->new("$redint");
	my $first_ip_int = $redint;
	if ( $ip_version eq "v4" && $BM < 31 ) {
		$first_ip_int = $redint + 1;
	}
	$first_ip_int = Math::BigInt->new("$first_ip_int");
	my $last_ip_int = ($ipob->last_int());
	$last_ip_int = Math::BigInt->new("$last_ip_int");
	if ( $ip_version eq "v4" && $BM < 31 ) {
		$last_ip_int = $last_ip_int - 1;
	}


    #check if DNS servers are alive

	my $res_dns;
	my $dns_error = "";
	my $nameserver_available="1";

	if ( $ip_version eq "v4" ) {
		if ( $default_resolver eq "yes" ) {
			$res_dns = Net::DNS::Resolver->new(
			retry       => 2,
			udp_timeout => 5,
			recurse     => 1,
			debug       => 0,
			);
		} else {
			$res_dns = Net::DNS::Resolver->new(
			retry       => 2,
			udp_timeout => 5,
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
				print LOG "$lang_vars{no_dns_server_message} ($test_ip) (1): " . $res_dns->errorstring . "\n\n";
				print "$lang_vars{no_dns_server_message} ($test_ip) (1): " . $res_dns->errorstring . "\n\n" if $verbose;
				$nameserver_available="0";
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

		if ( $all_used_nameservers eq "127.0.0.1" && $default_resolver eq "yes" ) {
			print LOG "$lang_vars{no_answer_from_dns_message} - $lang_vars{nameserver_localhost_message}\n\n$lang_vars{exiting_message}\n\n";
			print "$lang_vars{no_answer_from_dns_message} - $lang_vars{nameserver_localhost_message}\n\n$lang_vars{exiting_message}\n\n" if $verbose;
			$l++;
			next;
		}
	}


	my $mydatetime = time();


	if ( $ip_version eq "v6" ) {
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
		@zone_records=fetch_zone("$zone_name","$default_resolver",\@dns_servers);
	}



	my @ip;
	my @found_ip;
	if ( $ip_version eq "v6" ) {
		@ip=get_host_from_red_num("$client_id","$red_num");
		my $p=0;
		foreach my $found_ips (@ip) { 
			if ( $found_ips->[0] ) {
				$found_ips->[0]=int_to_ip("$found_ips->[0]","$ip_version");
				$found_ip[$p]=$found_ips->[0];
			}
			$p++;
		}
	}

	if ( ! $zone_records[0] && $ip_version eq "v6" ) {
		print LOG "$lang_vars{no_zone_data_message} $zone_name\n";
		print "$lang_vars{no_zone_data_message} $zone_name\n" if $verbose;
	}
	   

	my @records;
	if ( $ip_version eq "v4" ) {
		my $l=0;
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
		my $anz_records=$#records || "";
		my %seen;
		if ( $anz_records ) {
			for ( my $q = 0; $q <= $#records; ) {
				splice @records, --$q, 1
				if $seen{$records[$q++]}++;
			}
		}
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


	my $j=0;
	my $hostname;
	my ( $ip_int, $ip_bin, $pm, $res, $pid, $ip );
	my ( %res_sub, %res, %result);

	my $MAX_PROCESSES = $max_sinc_procs || $params{max_sinc_procs};
	$MAX_PROCESSES = "128" if ! $MAX_PROCESSES;
    if ( $MAX_PROCESSES !~ /^4|8|16|32|64|128|254|256$/ ) {
        $exit_message = "-max_sinc_procs must be one of this numbers: 4|8|16|32|64|128|256";
        if ( $gip_job_status_id ) {
            exit_error("$exit_message", "$gip_job_status_id", 4 );
        } else {
            print_help("$exit_message");
        }
    }


	$pm = new Parallel::ForkManager($MAX_PROCESSES);

	$pm->run_on_finish(
		sub { my ($pid, $exit_code, $ident) = @_;
			$res_sub{$pid}=$exit_code;
		}
	);
	$pm->run_on_start(
		sub { my ($pid,$ident)=@_;
			$res{$pid}="$ident";
		}
	);

	my $utype="snmp";
	my $ip_hash = get_host_hash_id_key("$client_id","$red_num");

	my $red_loc = get_loc_from_redid("$client_id","$red_num");
	my $red_loc_id = get_loc_id("$client_id","$red_loc");

	my $i;
	$i = $first_ip_int-1 if $ip_version eq "v4";

	my $cc_id_net_ifDescr=get_custom_column_id_from_name("$client_id","ifDescr") || "";
	my $cc_id_net_ifAlias=get_custom_column_id_from_name("$client_id","ifAlias") || "";

	foreach ( @records ) {

#		next if ! $_;

        if ( ! $_ ) {
            $i++;
            next;
        }

		my $node="";


        if ( $ip_range ) {
            if ( exists $ip_range_ips{$_} ) {
                if ( $ip_version eq "v4" ) {
                    $i=$_;
                    $node = int_to_ip("$i","$ip_version");
                } else {
                    $node=$_;
                    $i = ip_to_int("$node","$ip_version");
                }
            } else {
                $i++;
                next;
            }
        } else {
            if ( $ip_version eq "v4" ) {
                $i++;
                $node = int_to_ip("$i","$ip_version");
            } else {
                $node=$_;
                $i = ip_to_int("$node","$ip_version");
            }
        }


		$count_entradas_dns++;

		my $exit=0;

#        if ( $ip_version eq "v4" ) {
#                $i++;
#                $node=int_to_ip("$i","$ip_version");
#        } else {
#                $node=$_;
#                $i=ip_to_int("$node","$ip_version");
#        }

		if ( $use_arp_cache_devices_file && ! $use_arp_cache_devices{$node} ) {
			next;
		}

		my $node_id=get_host_id_from_ip_int("$client_id","$i","$red_num") || "";
		
			##fork
			$pid = $pm->start("$node") and next;
				#child

                my $snmp_group_name_host = get_custom_host_column_entry_from_name("$client_id", "$node_id", "SNMPGroup") || "";
                if ( $snmp_group_name_host ) {
                    ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port) = get_snmp_parameter("$client_id", "$node_id", "host");
                    $snmp_group_name = $snmp_group_name_host;
                }

				print "$node: " if $verbose;
				print LOG "$node: ";
                print "(SNMP group $snmp_group_name) " if $snmp_group_name && $verbose;
                print LOG "(SNMP group $snmp_group_name) " if $snmp_group_name && $verbose;

				my $utype_db;
				my $device_name_db = "";
				$utype_db=$ip_hash->{$node_id}[7] if $node_id;
				$device_name_db=$ip_hash->{$node_id}[1] if $node_id;
				$device_name_db = "" if ! $device_name_db;
				my $alive_found=0;
				$alive_found=$ip_hash->{"$node_id"}[8] if $node_id;
				my $range_id="";
				$range_id=$ip_hash->{"$node_id"}[10] if $node_id;
				$utype_db = "---" if ! $utype_db;
				if ( $utype_db eq "man" ) {
					print "update type: $utype_db - $lang_vars{ignorado_message}\n" if $verbose;
					print LOG "update type: $utype_db - $lang_vars{ignorado_message}\n";
					$exit = 1;
					$pm->finish($exit); # Terminates the child process
				}

				my @added_arp_ips;
				my %arp_cache_network_exists=();
				my $device_type="";
				my $device_vendor="";
				my $device_serial="";
				my $device_contact="";
				my $device_name="";
				my $device_location="";
				my $device_descr="";
				my $device_forwarder="";
				my $device_os="";
				my $device_cat="-1";

				my $mydatetime = time();
				my $new_host = "0";
				my $snmp_info_connect = "1";
				my $snmp_connect = "1";


				my $bridge=create_snmp_info_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","$auth_is_key","$priv_proto","$priv_pass","$priv_is_key","$sec_level",$mibdirs_ref,"","$snmp_port");


				my %if_values=();
				my %all_if_values=();
				if ( ! defined($bridge) ) {
	#				print "SNMP::INFO: $lang_vars{can_not_connect_message}<br>\n";
	#				$exit = 1;
	#				$pm->finish($exit); # Terminates the child process
				} else {

					$snmp_info_connect ="0";
					$device_type=$bridge->model() || "";
					$device_type = "" if $device_type =~ /enterprises\.\d/;
					$device_vendor=$bridge->vendor() || "";
					$device_serial=$bridge->serial() || "";
					$device_contact=$bridge->contact() || "";
					$device_name=$bridge->name() || "";
					$device_location=$bridge->location() || "";
					$device_descr=$bridge->description() || "";
					$device_forwarder=$bridge->ipforwarding() || "";
					$device_os="";


					# ifAlias, ifDescription

					my ($ifDescr,$ifAlias,$interfaces);
					$ifDescr=$ifAlias=$interfaces="";

					$interfaces = $bridge->interfaces() || ();
					my $i_descr = $bridge->i_description() || ();
					my $i_alias = $bridge->i_alias() || ();

					my $i_IP=$bridge->ip_index() || {};
					my $i_IPv6=$bridge->ipv6_index() || {};
					my %ni_IP = reverse %$i_IP;
					my $ni_IP=\%ni_IP;
					$i_IP=$ni_IP;

					foreach my $iid (keys %$interfaces){
						next if ! $i_IP->{$iid};

						my $ifIP=$i_IP->{$iid};
						$ifDescr=$i_descr->{$iid} || "";
						$ifAlias=$i_alias->{$iid} || "";

						next if ! $ifDescr && ! $ifAlias;

						push @{$all_if_values{$ifIP}},"$ifDescr","$ifAlias";

						if ( $i_IP->{$iid} eq $node ) {
							$if_values{ifDescr}=$ifDescr || "";
							$if_values{ifAlias}=$ifAlias || "";
							push @{$all_if_values{$ifIP}},"$red_num";
							last;
						}
					}
				}


						
				my $session=create_snmp_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","$auth_is_key","$priv_proto","$priv_pass","$priv_is_key","$sec_level","$snmp_port");

				if ( defined $session ) {
					no strict 'subs';	
					my $vars = new SNMP::VarList([sysDescr,0],
								[sysName,0],
								[sysContact,0],
								[sysLocation,0]);
					use strict 'subs';

					my @values = $session->get($vars);

					if ( ! ($session->{ErrorStr}) ) {

						$snmp_connect = "0";

						$device_descr = $values[0];
						$device_name = $values[1];
						$device_contact = $values[2];
						$device_location = $values[3];
						
		
						
						if ( $device_descr =~ /ubuntu/i ) {
							$device_os = "ubuntu";
						} elsif ( $device_descr =~ /gentoo/i ) {
							$device_os = "gentoo";
						} elsif ( $device_descr =~ /funtoo/i ) {
							$device_os = "funtoo";
						} elsif ( $device_descr =~ /-ARCH/ ) {
							$device_os = "arch";
						} elsif ( $device_descr =~ /debian/i ) {
							$device_os = "debian";
						} elsif ( $device_descr =~ /suse/i ) {
							$device_os = "suse";
						} elsif ( $device_descr =~ /fedora/i ) {
							$device_os = "fedora";
						} elsif ( $device_descr =~ /redhat/i ) {
							$device_os = "redhat";
						} elsif ( $device_descr =~ /centos/i ) {
							$device_os = "centos";
						} elsif ( $device_descr =~ /turbolinux/i ) {
							$device_os = "turbolinux";
						} elsif ( $device_descr =~ /slackware/i ) {
							$device_os = "slackware";
						} elsif ( $device_descr =~ /linux/i ) {
							$device_os = "linux";
						} elsif ( $device_descr =~ /freebsd/i ) {
							$device_os = "freebsd";
						} elsif ( $device_descr =~ /netbsd/i ) {
							$device_os = "netbsd";
						} elsif ( $device_descr =~ /netware/i ) {
							$device_os = "netware";
						} elsif ( $device_descr =~ /openbsd/i ) {
							$device_os = "openbsd";
						} elsif ( $device_descr =~ /solaris/i || $device_descr =~ /sunos/i ) {
							$device_os = "solaris";
						} elsif ( $device_descr =~ /unix/i ) {
							$device_os = "unix";
						} elsif ( $device_descr =~ /windows/i ) {
							$device_os = "windows_server";
						}


						my @vendors=("actiontec","accton","adder","aerohive","aficio","arquimedes","ricoh","alvaco","anitech","apple","aruba","adtran","allied","apc","altiga","alps","arista","asante","astaro","avaya","avocent","axis","barracuda","billion","belair","bluecoat","borderware","brother","broadcom","brocade","buffalo","calix","citrix","cyclades","canon","carestream","checkpoint","cisco","cyberoam","d-link","dell","dialogic","dothill","draytek","eaton","eci telecom","edgewater","eeye","emc","emerson","enterasys","epson","ericsson","extreme","extricom","f5","force10","fluke","fortinet","foundry","fujitsu","general electric","h3c","heidelberg","hitachi","hp|hewlett.?packard","huawei","ibm","iboss","imperva","juniper","kasda","kemp","kodak","konica","kyocera","lacie","lancom","lantronix","lanier","lanner","alcatel|lucent","lenovo","lexmark","lg","liebert","linksys","lifesize","macafee","megaware","meru","multitech","microsemi","microsoft","minolta","mikrotik","mitsubishi","mobileiron","motorola","moxa","netapp","nec","netgear","netsweeper","nitro","nokia","nortel","novell","oce","okilan","olivetti","olympus","optibase","ovislink","oracle","packetfront","panasonic","passport","palo.?alto","patton","peplink","philips","pica8","polycom","procurve","proxim","qnap","radvision","radware","rapid7","realtek","redback","reflex","riverbed","riverstone","rsa","ruckus","samsung","savin","seiko","shinko","siemens","silverpeak","sipix","smc","sonicwall","sourcefire","stillsecure","storagetek","star","stonesoft","sony","symantec","sun","supermicro","tally-genicom","tandberg","tenda","thomson","tippingpoint","toplayer","tp-link","ubiquiti","toshiba","vegastream","vidyo","vmware","vyatta","watchguard","websense","westbase","western digital","xante","xerox","xiro","zyxel","zebra","3com");
						foreach ( @vendors ) {
							my $vendor=$_;
							if ( $device_descr =~ /(${vendor}\s)/i ) {
								if ( $device_descr =~ /(ibm.+aix)/i ) {
									$device_vendor = "ibm";
									$device_os = "aix";
								} elsif ( $device_descr =~ /(ibm.+os2)/i ) {
									$device_vendor = "ibm";
									$device_os = "os2";
								} elsif ( $device_descr =~ /(aficio|ricoh)/i ) {
									if ( $device_descr =~ /printer/i ) {
										my $new_cat=get_cat_id("$client_id","printer");
										$device_cat = "$new_cat" if $new_cat;
									}
								} elsif ( $device_descr =~ /(hp\s|hewlett.?packard)/i ) {
									$device_vendor = "hp";
									if ( $device_descr =~ /jet/i ) {
										my $new_cat=get_cat_id("$client_id","printer");
										$device_cat = "$new_cat" if $new_cat;
									}
								} elsif ( $device_descr =~ /(alcatel|lucent)/i ) {
									$device_vendor = "alcatel-lucent";
								} elsif ( $device_descr =~ /(palo.?alto)/i ) {
									$device_vendor = "paloalto";
								} elsif ( $device_descr =~ /(microsoft|windows)/i ) {
									$device_os = "windows";
								} elsif ( $device_descr =~ /cyclades/i ) {
									$device_vendor = "avocent";
								} elsif ( $device_descr =~ /orinoco/i ) {
									$device_vendor = "alcatel-lucent";
								} elsif ( $device_descr =~ /phaser/i ) {
									$device_vendor = "xerox";
								} elsif ( $device_descr =~ /minolta/i ) {
									$device_vendor = "konica";
								} elsif ( $device_descr =~ /check.?point/i ) {
									$device_vendor = "checkpoint";
								} elsif ( $device_descr =~ /top.?layer/i ) {
									$device_vendor = "toplayer";
								} elsif ( $device_descr =~ /silver.?peak/i ) {
									$device_vendor = "Silver Peak";
								} elsif ( $device_descr =~ /okilan/i ) {
									$device_vendor = "Oki Data";
								} elsif ( $device_descr =~ /(dlink|d-link)/i ) {
									$device_vendor = "dlink";
								} else {
									$device_vendor = $vendor;
								}
							} 
						}
					}


					# ARP cache
                    if ( ! $ignore_arp_cache ) {
                        my %arp_cache=();
                        # set up the data structure for the getnext command
                        $vars = new SNMP::VarList(['ipNetToMediaNetAddress'],
                                      ['ipNetToMediaPhysAddress']);

                        # get first row

                        if ( ! ($session->{ErrorStr}) ) {
                            my ($ip,$mac) = $session->getnext($vars);

                            while (!$session->{ErrorStr} and
                                $$vars[0]->tag eq "ipNetToMediaNetAddress"){
                                my $ip_version_ip="";
                                $ip_version_ip="v4" if $ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
                                $ip_version_ip="v6" if $ip =~ /:/;
                                if  ( $ip_version_ip ) {
                                    my $ip_int_ip=ip_to_int("$ip","$ip_version_ip");
                                    push @{$arp_cache{$ip}},"$mac","$ip_version_ip","$ip_int_ip";
                                }
                                ($ip,$mac) = $session->getnext($vars);
                            }

                            foreach my $key ( sort keys (%arp_cache) ) {

                                my $ip_version_ip=$arp_cache{$key}[1] || "";
                                my $ip_int_ip=$arp_cache{$key}[2] || "";
                                next if ! $ip_version_ip;
                                print "DEBUG: ARP CACHE: $key - $arp_cache{$key}[0]\n" if $debug;
                                print LOG "DEBUG: ARP CACHE: $key - $arp_cache{$key}[0]\n" if $debug;
                                if ( $ip_int_ip >= $first_ip_int && $ip_int_ip <= $last_ip_int ) {
                                    $arp_cache_network_exists{$key}=$arp_cache{$key};
                                    push @{$arp_cache_network_exists{$key}},"$red_num";
                                    print LOG "DEBUG: ADD to arp_cache_network_exist (1): $key - $red_num\n" if $debug;
                                    next;
                                }

                                my $k = 0;
                                foreach ( @values_host_redes ) {
                                    if ( ! $values_host_redes[$k]->[0] || $values_host_redes[$k]->[5] == 1  ) {
                                        $k++;
                                        next;
                                    }

                                    my $ip_version_checkred = $values_host_redes[$k]->[4];

                                    if ( $ip_version_ip ne $ip_version_checkred ) {
                                        $k++;
                                        next;
                                    }

                                    my $host_red = $values_host_redes[$k]->[0];
                                    my $host_red_bm = $values_host_redes[$k]->[1];
                                    my $red_num_red = $values_host_redes[$k]->[2];

                                    if ( $red_num_red eq $red_num ) {
                                        $k++;
                                        next;
                                    }

                                    if ( $ip_version_ip eq "v4" ) {
                                        $host_red =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
                                        my $third_host_red_oct=$3;
                                        $key =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
                                        my $third_host_oct=$3;
                                        if (  $host_red_bm >= 24 && $third_host_red_oct != $third_host_oct ) {
                                            $k++;
                                            next;
                                        }
                                    }

                                    my $redob_redes = "$host_red/$host_red_bm";
                                    my $ipob_redes = new Net::IP ($redob_redes) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $redob_redes\n";
                                    my $ipm = "$key/32";
                                    my $ipm_ip = new Net::IP ($ipm) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $ipm\n";
                                    if ( $ipm_ip->overlaps($ipob_redes) == $IP_NO_OVERLAP ) {
                                        # no overlap
                                        $k++;
                                        next;
                                    }

                                    $arp_cache_network_exists{$key}=$arp_cache{$key};
                                    print "DEBUG: ADD to arp_cache_network_exist (2): $key - $red_num\n" if $debug;
                                    print LOG "DEBUG: ADD to arp_cache_network_exist (2): $key - $red_num\n" if $debug;
                                    push @{$arp_cache_network_exists{$key}},"$red_num_red";

                                    $k++;
                                    last;
                                }
                            }
                        }
                    }
				} else {
#					print "SNMP $lang_vars{can_not_connect_message} (1)\n" if $verbose;
#					print LOG "SNMP $lang_vars{can_not_connect_message}\n";
				}

				if ( ( $snmp_info_connect == "1" && $snmp_connect == "1" ) ) {
					print "$lang_vars{can_not_connect_message} (2)\n" if $verbose;
					print LOG "$lang_vars{can_not_connect_message} (2) - " . $session->{ErrorStr} . "\n";
					$exit = "1";
					$pm->finish($exit); # Terminates the child process
				}

				if ( $node_id && $alive_found != 1) {
					print "DEBUG $node: Updating ping info ($alive_found): alive\n" if $debug; 
					print LOG "DEBUG $node: Updating ping info: alive\n" if $debug; 
					#update alive status to 1 (alive)
					update_host_ping_info("$client_id","$i","1","1","$node","3","$vars_file")
				}	

				$device_descr = "" if $device_descr =~ /(unknown|configure)/i;
				$device_contact = "" if $device_contact =~ /(unknown|configure)/i;
				$device_location = "" if $device_location =~ /(unknown|configure)/i;
				$device_name = "unknown" if $device_name =~ /(localhost|DEFAULT SYSTEM NAME)/i;
				$device_vendor = "" if $device_vendor =~ /(unknown)/i;
				$device_contact =~ s/^"//;
				$device_contact =~ s/"$//;
				$device_name =~ s/^"//;
				$device_name =~ s/"$//;
				$device_location =~ s/^"//;
				$device_location =~ s/"$//;

				my $device_name_dns = "";
				if ( ! $node_id && ! $device_name && $nameserver_available == 1 ) {

					my $res_dns;

					if ( $default_resolver eq "yes" ) {
						$res_dns = Net::DNS::Resolver->new(
						retry       => 2,
						udp_timeout => 5,
						recurse     => 1,
						debug       => 0,
						);
					} else {
						$res_dns = Net::DNS::Resolver->new(
						retry       => 2,
						udp_timeout => 5,
						nameservers => [@dns_servers],
						recurse     => 1,
						debug       => 0,
						);
					}

					my $ptr_query;
					my $dns_error="";
					if ( $node =~ /\w+/ ) {
						$ptr_query = $res_dns->query("$node");

						if ($ptr_query) {
							foreach my $rr ($ptr_query->answer) {
								next unless $rr->type eq "PTR";
								$device_name_dns = $rr->ptrdname;
							}
						} else {
							$dns_error = $res_dns->errorstring;
						}
					}


					$node =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
					my $generic_auto = "$2-$3-$4|$4-$3-$2";
					if ( $device_name_dns =~ /$generic_auto/ && $ignore_generic_auto eq "yes" ) {
						$device_name_dns = "unknown";
					}
					$device_name=$device_name_dns if $device_name_db eq "unknown";
				}

				if ( ! $device_name_dns ) {
					$device_name = "unknown" if $device_name =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
				} else {
					$device_name = "" if $device_name =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
				}

				my $hostname_update="0";

				if ( ! $node_id && $device_name ) {
					$device_name =~ s/\s/_/g;
#					insert_ip_mod("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version");
					my ($added_ip,$added_hostname,$new_host_id) = check_and_insert_host("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","1","$ip_version","$node","$default_resolver",\@dns_servers,"$ignore_generic_auto");
					$new_host = "1";
                    $node_id=$new_host_id;

					$pm->finish(0) if ! $node_id;

					print LOG "$lang_vars{host_anadido_message}: $device_name";
					print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
				} elsif ( ! $node_id && $device_name_dns ) {
#					insert_ip_mod("$client_id","$i","$device_name_dns","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version");
					my ($added_ip,$added_hostname,$new_host_id) = check_and_insert_host("$client_id","$i","$device_name_dns","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version","$node","$default_resolver",\@dns_servers,"$ignore_generic_auto");
					$new_host = "1";
                    $node_id=$new_host_id;

					$pm->finish(0) if ! $node_id;

					print "$lang_vars{host_anadido_message}: $device_name_dns" if $verbose;
					print LOG "$lang_vars{host_anadido_message}: $device_name_dns";
				} elsif ( ! $node_id && $device_type ) {
					$device_type =~ /^(.+)\s*/;
					my $device_name = $1;
#					insert_ip_mod("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version");
					my ($added_ip,$added_hostname,$new_host_id) = check_and_insert_host("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version","$node","$default_resolver",\@dns_servers,"$ignore_generic_auto");
					$new_host = "1";
                    $node_id=$new_host_id;

					$pm->finish(0) if ! $node_id;

					print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
					print LOG "$lang_vars{host_anadido_message}: $device_name";
				} elsif ( ! $node_id && $device_vendor ) {
					$device_vendor =~ /^(.+)\s*/;
					my $device_name = $1;
#					insert_ip_mod("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version");
					my ($added_ip,$added_hostname,$new_host_id) = check_and_insert_host("$client_id","$i","$device_name","","$red_loc_id","n","$device_cat","","-1","$mydatetime","$red_num","-1","$ip_version","$node","$default_resolver",\@dns_servers,"$ignore_generic_auto");
					$new_host = "1";
                    $node_id=$new_host_id;

					$pm->finish(0) if ! $node_id;

					print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
					print LOG  "$lang_vars{host_anadido_message}: $device_name";
				} elsif ( ! $node_id ) {
					$exit = 1;
					print LOG " $lang_vars{no_device_name_message} - $lang_vars{ignorado_message}\n";
					print " $lang_vars{no_device_name_message} - $lang_vars{ignorado_message}\n" if $verbose;
					$pm->finish($exit); # Terminates the child process
				} elsif ( $node_id  &&  $device_name_db eq "unknown" && $device_name_db ne $device_name ) {
						update_host_hostname("$client_id","$node_id","$device_name");
						$hostname_update="1";
				} elsif ( $node_id && $range_id != "-1" && ! $device_name_db ) {
					if ( $device_name ) {
						update_host_hostname("$client_id","$node_id","$device_name");
						print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
						print LOG "$lang_vars{host_anadido_message}: $device_name";
						$new_host = "1";
					} elsif ( $device_name_dns ) {
						update_host_hostname("$client_id","$node_id","$device_name_dns");
						print "$lang_vars{host_anadido_message}: $device_name_dns" if $verbose;
						print LOG "$lang_vars{host_anadido_message}: $device_name_dns";
						$new_host = "1";
					} elsif ( $device_type ) {
						$device_type =~ /^(.+)\s*/;
						my $device_name = $1;
						update_host_hostname("$client_id","$node_id","$device_name");
						print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
						print LOG "$lang_vars{host_anadido_message}: $device_name";
						$new_host = "1";
					} elsif ( $device_vendor ) {
						$device_vendor =~ /^(.+)\s*/;
						my $device_name = $1;
						update_host_hostname("$client_id","$node_id","$device_name");
						print "$lang_vars{host_anadido_message}: $device_name" if $verbose;
						print LOG  "$lang_vars{host_anadido_message}: $device_name";
						$new_host = "1";
					} else {
						update_host_hostname("$client_id","$node_id","unknown");
						print "$lang_vars{host_anadido_message}: unknown" if $verbose;
						print LOG "$lang_vars{host_anadido_message}: unknown";
						$new_host = "1";
					}
				}

				my $entry;
				my $audit_entry = "";
				my $audit_entry_cc = "";
				my $audit_entry_cc_new = "";
				my $update = "0";

				while ( my ($key, $value) = each(%predef_host_columns) ) {
					my $pc_id;
					my $cc_id = get_custom_host_column_id_from_name_client("$client_id","$key") || "-1"; 
					next if $cc_id eq "-1";

					if ( $key eq "vendor" ) {
						$entry = $device_vendor;
					} elsif ( $key eq "model" ) {
						$entry = $device_type;
					} elsif ( $key eq "contact" ) {
						$entry = $device_contact;
					} elsif ( $key eq "serial" ) {
						$entry = $device_serial;
					} elsif ( $key eq "device_descr" ) {
						$entry = $device_descr;
					} elsif ( $key eq "device_name" ) {
						$entry = $device_name;
						$entry = "" if $device_name eq "unknown";
					} elsif ( $key eq "device_loc" ) {
						$entry = $device_location;
					} elsif ( $key eq "OS" ) {
						$entry = $device_os;
					} elsif ( $key eq "ifDescr" ) {
						$entry = $if_values{"ifDescr"} || "";
					} elsif ( $key eq "ifAlias" ) {
						$entry = $if_values{"ifAlias"} || "";
					} else {
						$entry = "";
					}


					if ( $entry ) {
						$pc_id=$predef_host_columns{$key}[0];

						my @cc_entry_host=();
						my $cc_entry_host=get_custom_host_column_entry_complete("$client_id","$node_id","$cc_id") || "";

						if ( @{$cc_entry_host}[0] ) {
							my $entry_db=@{$cc_entry_host}[0]->[0];
							$entry_db=~s/^\*//;
							$entry_db=~s/\*$//;
							if ( $entry_db ne $entry ) {
								update_custom_host_column_value_host("$client_id","$cc_id","$pc_id","$node_id","$entry");
								if ( $audit_entry_cc ) {
									$audit_entry_cc = $audit_entry_cc . "," . $entry;
								} else {
									$audit_entry_cc = $entry;
								}
								if ( $audit_entry_cc_new ) {
									$audit_entry_cc_new = $audit_entry_cc . "," . @{$cc_entry_host}[0]->[0];
								} else {
									$audit_entry_cc_new = @{$cc_entry_host}[0]->[0];
								}
								$update="2";
							} else {

								if ( $audit_entry_cc ) {
									$audit_entry_cc = $audit_entry_cc . "," . $entry;
								} else {
									$audit_entry_cc = $entry;
								}
								if ( $audit_entry_cc_new ) {
									$audit_entry_cc_new = $audit_entry_cc_new . "," . @{$cc_entry_host}[0]->[0];
								} else {
									$audit_entry_cc_new = @{$cc_entry_host}[0]->[0];
								}
								
							}
						} else {
							insert_custom_host_column_value_host("$client_id","$cc_id","$pc_id","$node_id","$entry");
							if ( $audit_entry_cc ) {
								$audit_entry_cc = $audit_entry_cc . ",---";
							} else {
								$audit_entry_cc = "---";
							}
							if ( $audit_entry_cc_new ) {
								$audit_entry_cc_new = $audit_entry_cc_new . "," . $entry;
							} else {
								$audit_entry_cc_new = $entry;
							}
							$update="1" if $update != "2";
						}
					}
				}


				if ( $hostname_update == "1" && $new_host == "0" ) { 
					print "$lang_vars{host_updated_message}: $device_name" if $verbose;
					print LOG "$lang_vars{host_updated_message}: $device_name";
					print LOG ", " if $update != "0";
				}
				if ( $update == "1" && $new_host == "0" ) {
					print ", " if $hostname_update == "1" && $verbose;
					print LOG ", " if $hostname_update == "1";
					print "$lang_vars{cc_updated_message}" if $verbose;
					print LOG "$lang_vars{cc_updated_message}";
				} elsif ( $update == "0" && $new_host != "1" && $hostname_update == "0" ) {
					print "$lang_vars{no_changes_message}" if $verbose;
					print LOG "$lang_vars{no_changes_message}";
				} elsif ( $update == "2" && $new_host != "1" ) {
					if ( $hostname_update == 1 ) {
						print ", " if $hostname_update == "1" && $verbose;
						print LOG ", " if $hostname_update == "1";
					}
					print "$lang_vars{cc_updated_message}" if $verbose;
					print LOG "$lang_vars{cc_updated_message}";
				}

				print LOG "\n";
				print "\n" if $verbose;
	#			print " - DEVICE TYPE: $device_type - VENDOR: $device_vendor - SERIAL: $device_serial - CONTACT: $device_contact - NAME: $device_name - LOC: $device_location - DESCR: $device_descr - FORWARDER: $device_forwarder <br>";



                # Insert IPs found in arp cache
                if ( ! $ignore_arp_cache ) {
                    my $cc_id_mac = get_custom_host_column_id_from_name_client("$client_id","MAC") || "";
                    my $pc_id_mac=$predef_host_columns{"MAC"}[0] || "";
                    while ( my ($key, @value) = each(%arp_cache_network_exists) ) {
                        my $mac=$arp_cache_network_exists{$key}[0];
                        my $ip_version_insert=$arp_cache_network_exists{$key}[1];
                        my $ip_int_ip=$arp_cache_network_exists{$key}[2];
                        my $red_num_ip=$arp_cache_network_exists{$key}[3];

                        print "DEBUG: while arp_cache_network_exists: $key - $ip_version_insert - $ip_int_ip - $red_num_ip\n" if $debug;
                        print LOG "DEBUG: while arp_cache_network_exists: $key - $ip_version_insert - $ip_int_ip - $red_num_ip\n" if $debug;
                        next if ! $ip_version_insert || ! $ip_int_ip || ! $red_num_ip;

                        my $hostname_ip="";
                        $hostname_ip = "unknown" if ! $hostname_ip;

                        my ($added_arp_ip,$new_hostname,$new_host_id)=check_and_insert_host("$client_id","$ip_int_ip","$hostname_ip","","-1","n","$device_cat","","-1","$mydatetime","$red_num_ip","1","$ip_version","$key","$default_resolver",\@dns_servers,"$ignore_generic_auto");
                        if ( $added_arp_ip ) {
                            print "Found in Arp-cache of $node: $added_arp_ip ($new_hostname) - $lang_vars{host_anadido_message}\n" if $verbose;
                            print LOG "Found in Arp-cache of $node: $added_arp_ip ($new_hostname) - $lang_vars{host_anadido_message}\n";
                            my $audit_type="15";
                            my $audit_class="1";
                            my $update_type_audit="7";
                            my $event="$added_arp_ip: $new_hostname,---,---,n,---,---,$utype,$audit_entry,$mac";
                            $event=$event . " (community: public)" if $community eq "public";
                            insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
                        }

                        # Update MAC column
                        if ( $cc_id_mac && $pc_id_mac ) {
                            my $host_id=get_host_id_from_ip_int("$client_id","$ip_int_ip") || "-1";
                            my $cc_entry_host=get_custom_host_column_entry_complete("$client_id","$host_id","$cc_id_mac") || "";

                            if ( @{$cc_entry_host}[0] ) {
                                my $entry_db=@{$cc_entry_host}[0]->[0];
                                update_custom_host_column_value_host("$client_id","$cc_id_mac","$pc_id_mac","$host_id","$mac");
                            } else {
                                insert_custom_host_column_value_host("$client_id","$cc_id_mac","$pc_id_mac","$host_id","$mac");
                            }
                        }
                    }
                }

				#update NETWORK ifDescr and ifAlias columns
				while ( my ($key,@value)=each(%all_if_values) ) {
					my $ip_ip=$key;
					my $ip_ip_version="v4";
					$ip_ip_version="v6" if $ip_ip !~ /^\d{1,3}\./;
					my $ip_ip_int=ip_to_int("$ip_ip","$ip_ip_version");
					my $ifDescr=$value[0]->[0] || "";
					my $ifAlias=$value[0]->[1] || "";
					my $ip_red_num=$value[0]->[2] || "";

					if ( ! $ip_red_num ) {
						$ip_red_num=get_red_num_from_host_ip_int("$client_id","$ip_ip_int") || "";
					}

					next if ! $ip_red_num;

					my $cc_value_net_ifDescr=get_custom_column_entry("$client_id","$ip_red_num","ifDescr") || "";
					my $cc_value_net_ifAlias=get_custom_column_entry("$client_id","$ip_red_num","ifAlias") || "";
					print "DEBUG: while %all_if_values loop: $ip_ip - $ifDescr ($cc_value_net_ifDescr)- $ifAlias ($cc_value_net_ifAlias) - $ip_red_num\n" if $debug;
					print LOG "DEBUG: while %all_if_values loop: $ip_ip - $ifDescr ($cc_value_net_ifDescr)- $ifAlias ($cc_value_net_ifAlias) - $ip_red_num\n" if $debug;


					if ( ! $cc_value_net_ifDescr && $ifDescr && $cc_id_net_ifDescr ) {
						print "DEBUG: INSERT NET CC ifDescr: $ip_ip - $ifDescr - $ip_red_num\n" if $debug;
						print LOG "DEBUG: INSERT NET CC ifDescr: $ip_ip - $ifDescr - $ip_red_num\n" if $debug;
						insert_custom_column_value_red("$client_id","$cc_id_net_ifDescr","$ip_red_num","$ifDescr");
					} elsif ( $ifDescr && $ifDescr ne $cc_value_net_ifDescr && $cc_id_net_ifDescr ) {
						print "DEBUG: UPDATE NET CC ifDescr: $ip_ip - $ifDescr - $ip_red_num\n" if $debug;
						print LOG "DEBUG: UPDATE NET CC ifDescr: $ip_ip - $ifDescr - $ip_red_num\n" if $debug;
						update_custom_column_value_red("$client_id","$cc_id_net_ifDescr","$ip_red_num","$ifDescr");
					}
					if ( ! $cc_value_net_ifAlias && $ifAlias && $cc_id_net_ifAlias ) {
						print "DEBUG: INSERT NET CC ifAlias: $ip_ip - $ifAlias - $ip_red_num\n" if $debug;
						print LOG "DEBUG: INSERT NET CC ifAlias: $ip_ip - $ifAlias - $ip_red_num\n" if $debug;
						insert_custom_column_value_red("$client_id","$cc_id_net_ifAlias","$ip_red_num","$ifAlias");
					} elsif ( $ifAlias && $ifAlias ne $cc_value_net_ifAlias && $cc_id_net_ifAlias ) {
						print "DEBUG: UPDATE NET CC ifAlias: $ip_ip - $ifAlias - $ip_red_num\n" if $debug;
						print LOG "DEBUG: UPDATE NET CC ifAlias: $ip_ip - $ifAlias - $ip_red_num\n" if $debug;
						update_custom_column_value_red("$client_id","$cc_id_net_ifAlias","$ip_red_num","$ifAlias");
					}
				}



				if ( $new_host == "1" ) {
					my $audit_type="15";
					my $audit_class="1";
					my $update_type_audit="3";
					$red_loc = "---" if $red_loc eq "NULL";
					my $event="$node: $device_name,---,$red_loc,n,---,---,$utype,$audit_entry";
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
				} elsif ( $update == "1" || $update == "2" ) {
					my $audit_type="1";
					my $audit_class="1";
					my $update_type_audit="3";
					my $hostname_audit=$ip_hash->{$node_id}[1] || "---";
					my $host_descr=$ip_hash->{$node_id}[2] || "---";
					my $loc=$ip_hash->{$node_id}[3] || "---";
					my $cat=$ip_hash->{$node_id}[4] || "---";
					my $int_admin=$ip_hash->{$node_id}[5] || "---";
					my $comentario=$ip_hash->{$node_id}[6] || "---";
					my $utype_audit=$ip_hash->{$node_id}[7] || "---";
					$host_descr = "---" if $host_descr eq "NULL";
					$cat = "---" if $cat eq "NULL";
					$loc = "---" if $loc eq "NULL";
					$comentario = "---" if $comentario eq "NULL";
					$utype_audit = "---" if ! $utype_audit;
					$utype_audit = "---" if $utype_audit eq "NULL";
					$hostname_audit = "---" if $hostname_audit eq "NULL";
					my $event="$node: $hostname_audit,$host_descr,$loc,$int_admin,$cat,$comentario,$utype_audit,$audit_entry_cc -> $hostname_audit,$host_descr,$loc,$int_admin,$cat,$comentario,$utype_audit";
					$event=$event . "," . $audit_entry_cc_new if $audit_entry_cc_new;
					insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file") if $enable_audit == "1";
				}

				$exit=0;


			$pm->finish($exit); # Terminates the child process

	}

	$pm->wait_all_children;

	my $audit_type="44";
	my $audit_class="2";
	my $update_type_audit="3";
	my $event="${red}/${BM}";
	$event=$event . " (community: public)" if $community eq "public";
	my $user=getlogin() || "";
	insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user") if $enable_audit == "1";

	$l++;

    update_net_usage_cc_column("$client_id", "$ip_version", "$red_num", "$BM","no_rootnet");
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

if ( $gip_job_id && ! $combined_job ) {
    update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
}

print "Job successfully finished\n";
exit 0;


#######################
# Subroutiens
#######################

sub get_vigilada_redes {
	my ( $client_id, $red, $ip_version, $tag, $location_scan_ids ) = @_;

	my $ip_ref;

	$ip_version="" if ! $ip_version;
	my $ip_version_expr="";
	if ( $ip_version eq "v4" ) {
		$ip_version_expr="AND ip_version='v4'";
	} elsif ( $ip_version eq "v6" ) {
		$ip_version_expr="AND ip_version='v6'";
	}
	my @vigilada_redes;
	my $dbh = mysql_connection();
	my $sth;
    if ( $tag ) {
		my %tags = get_tag_hash("$client_id", "name");
        my $tag_expr = "";
		if ( $tag ) {
			$tag_expr = " AND red_num IN ( SELECT net_id from tag_entries_network WHERE (";
			foreach my $item ( @${tag} ) {
				if ( ! defined $tags{$item}->[0] ) {
					$exit_message = "$item: Tag NOT FOUND - ignored";
					exit_error("$exit_message", "$gip_job_status_id", 4 );
				}
				$tag_expr .= " tag_id=\"$tags{$item}->[0]\" OR";
			}
			$tag_expr =~ s/OR$//;
			$tag_expr .= " ))";
		}
        $sth = $dbh->prepare("SELECT red, BM, red_num, loc FROM net WHERE client_id=\"$client_id\" $ip_version_expr $tag_expr ORDER BY ip_version,red");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";

    } elsif ( $location_scan_ids ) {
        my $loc_expr = " AND loc IN ( $location_scan_ids )";
        $sth = $dbh->prepare("SELECT red, BM, red_num, loc, dyn_dns_updates FROM net WHERE client_id=\"$client_id\" $ip_version_expr $loc_expr ORDER BY ip_version,red");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";

    } else {
        $sth = $dbh->prepare("SELECT red, BM, red_num, loc FROM net WHERE vigilada=\"y\" AND client_id=\"$client_id\" $ip_version_expr ORDER BY ip_version,red");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";
    }

	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @vigilada_redes, [ @$ip_ref ];
	}

	$sth->finish();
	$dbh->disconnect;
	return @vigilada_redes;
}


sub check_for_reserved_range {
	my ( $client_id,$red_num ) = @_;
	my $ip_ref;
	my @ranges;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT red_num FROM ranges WHERE red_num = \"$red_num\" AND client_id=\"$client_id\"");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @ranges, [ @$ip_ref ];
        }
	$sth->finish();
        $dbh->disconnect;
        return @ranges;
}

sub print_help {
	my ( $message ) = @_;

    print "$message\n" if $message;

	print "\nusage: ip_update_gestioip_snmp.pl [OPTIONS...]\n\n";
	print "--config_file_name=config_file_name      name of the configuration file (without path)\n";
	print "-C, --CSV_networks=csv_list              coma separated list of networks to process\n";
	print "-d, --disable_audit                      disable auditing\n";
	print "-h, --help                               this help\n";
	print "-i, --ignore_arp_cache                   ignore arp cache information\n";
	print "-l, --log=logfile                        logfile\n";
	print "-L, --Location=locations                 Process only networks with this location (coma separted list of locations)\n";
	print "-m, --mail                               send the result by mail (mail_destinatarios)\n";
	print "-N, --Network_file=networks.list         file with the list of networks to process (without path)\n";
	print "-o, --only_added_mail                    send only a summary for new added hosts by mail\n";
	print "-p, --process31                          process networks with bitmask of /31\n";
    print "-r, --range=ip-range                     range of IPs to scan. Format: --range=IP1-IP2\n";
    print "                                         (e.g. --range=1.1.1.3-1.1.1.10)\n";

    print "-s, --snmp_port=port-nr					SNMP port to connect to (default: 161)\n";
    print "-t, --tag                                use networks with this tags to process\n";
	print "                                         (e.g. -t tag1,tag2,tag3)\n";
	print "-u, --use_arp_cache_devices_file=file    file with a list of devices for which the ARP\n";
	print "                                         cache should be queried to discover new devices\n";
	print "-v, --verbose                            verbose\n";
	print "-V, --Version                            print version and exit\n\n";

    print "Options to overwrite values from the configuration file:\n";
	print "-A client\n";
    print "-B ignore_generic_auto   ([yes|no])\n";
    print "-D snmp_version          ([1|2|3])\n";
	print "-E community             SNMP v1/2c community string\n";
    print "-F snmp_user_name        SNMP v3 user name\n";
    print "-G sec_level\n";
    print "-H auth_proto\n";
    print "-I auth_pass\n";
    print "-J priv_proto\n";
    print "-K priv_pass\n";
    print "-M logdir\n";
	print "-T actualize_ipv4        ([yes|no]), Default: yes\n";
    print "-O actualize_ipv6        ([yes|no]), Default: no\n";
    print "-S max_sinc_procs        ([4|8|16|32|64|128|256])\n";

	print "\n\nconfiguration file: $conf\n\n";
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
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
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
        my $sth = $dbh->prepare("INSERT IGNORE audit_auto (event,user,event_class,event_type,update_type_audit,date,remote_host,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qremote_host,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
}


sub get_red {
        my ( $client_id, $red_num ) = @_;
        my $ip_ref;
        my @values_redes;
        my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $sth = $dbh->prepare("SELECT red, BM, descr, loc, vigilada, comentario, categoria, ip_version FROM net WHERE red_num=$qred_num  AND client_id=\"$client_id\"") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_redes;
}

sub get_loc_from_redid {
        my ( $client_id, $red_num ) = @_;
        my @values_locations;
        my ( $ip_ref, $red_loc );
        my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $sth = $dbh->prepare("SELECT l.loc FROM locations l, net n WHERE n.red_num = $qred_num AND n.loc = l.id AND n.client_id=\"$client_id\"") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $red_loc = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $red_loc;
}

sub get_host {
        my ( $client_id, $first_ip_int, $last_ip_int ) = @_;
        my @values_ip;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qfirst_ip_int = $dbh->quote( $first_ip_int );
        my $qlast_ip_int = $dbh->quote( $last_ip_int );
        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id FROM host h, locations l, categorias c, update_type ut WHERE ip BETWEEN $qfirst_ip_int AND $qlast_ip_int AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND h.client_id=\"$client_id\" ORDER BY h.ip") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_ip;
}

sub get_host_range {
        my ( $client_id,$first_ip_int, $last_ip_int ) = @_;
        my @values_ip;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qfirst_ip_int = $dbh->quote( $first_ip_int );
        my $qlast_ip_int = $dbh->quote( $last_ip_int );
        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id FROM host h, locations l, categorias c, update_type ut WHERE ip BETWEEN $qfirst_ip_int AND $qlast_ip_int AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND range_id != '-1' AND h.client_id=\"$client_id\" ORDER BY h.ip") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_ip;
}


sub get_cat_id {
        my ( $cat ) = @_;
        my $cat_id;
        my $dbh = mysql_connection();
        my $qcat = $dbh->quote( $cat );
        my $sth = $dbh->prepare("SELECT id FROM categorias WHERE cat=$qcat
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $cat_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $cat_id;
}

sub get_utype_id {
        my ( $utype ) = @_;
        my $utype_id;
        my $dbh = mysql_connection();
        my $qutype = $dbh->quote( $utype );
        my $sth = $dbh->prepare("SELECT id FROM update_type WHERE type=$qutype
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $utype_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $utype_id;
}

sub insert_ip_mod {
        my ( $client_id,$ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version  ) = @_;
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
	my $qip_version = $dbh->quote( $ip_version );
        if ( defined($alive) ) {
                my $qalive = $dbh->quote( $alive );
                my $qlast_response = $dbh->quote( time() );
                $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,ip_version,client_id) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qip_version,$qclient_id)"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        } else {
                $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,client_id) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qclient_id)"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        }
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}


sub check_and_insert_host {
	my ( $client_id, $ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $ip,$default_resolver,$dns_servers,$ignore_generic_auto,$device_name ) = @_;

	my @values_host;
	$hostname="" if ! $hostname;

	my $return_ip;

    my $dbh = mysql_connection();
	my $sth;
	my $ip_ref;

	$loc="-1" if ! $loc;
	$cat="-1" if ! $cat;
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
    my $qalive = $dbh->quote( $alive );
	my $qclient_id = $dbh->quote( $client_id );
	my $qip_version = $dbh->quote( $ip_version );
	my $qlast_response = $dbh->quote( time() );


	# Check if host already exists in the DB
    $sth = $dbh->prepare("SELECT id,hostname,range_id,alive FROM host h WHERE ip=$qip_int AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_host, [ @$ip_ref ];
    }

	my $id=$values_host[0]->[0];
	my $hostname_found=$values_host[0]->[1] || "unknown";
	$hostname_found = $hostname if $hostname && $hostname ne "unknown";
	my $range_id=$values_host[0]->[2] || -1;
	my $alive_found=$values_host[0]->[3] || 0;

	if ( ! $hostname || $hostname eq "unknown" ) {
		# get hostname from rDNS

		use Net::DNS;

		my $res_dns;

		if ( $default_resolver eq "yes" ) {
			$res_dns = Net::DNS::Resolver->new(
			retry       => 2,
			udp_timeout => 5,
			recurse     => 1,
			debug       => 0,
			);
		} else {
			$res_dns = Net::DNS::Resolver->new(
			retry       => 2,
			udp_timeout => 5,
			nameservers => [@$dns_servers],
			recurse     => 1,
			debug       => 0,
			);
		}

		my $ptr_query;
		my $dns_error="";
		if ( $ip =~ /\w+/ ) {
			$ptr_query = $res_dns->search("$ip");

			if ($ptr_query) {
				foreach my $rr ($ptr_query->answer) {
					next unless $rr->type eq "PTR";
					$hostname_found = $rr->ptrdname;
				}
			} else {
				$dns_error = $res_dns->errorstring;
			}
		}

		$ip =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
		my $generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
		if ( $hostname_found =~ /$generic_auto/ && $ignore_generic_auto eq "yes" ) {
			$hostname_found = "unknown";
		}

		$hostname_found = "unknown" if ! $hostname_found;
	}


    my $qhostname = $dbh->quote( $hostname_found );

    my $new_id;

	if ( ! $id ) {
		$return_ip=$ip;
		# Insert host
		$sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,ip_version,client_id) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qip_version,$qclient_id)"
				) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $new_id=$sth->{mysql_insertid};

	} elsif ( $id && $range_id != -1 && $hostname_found eq "unknown") {
		# IP from reserved range
		$return_ip=$ip if ! $values_host[0]->[1];
		$sth = $dbh->prepare("UPDATE host set hostname=$qhostname, last_update=$qmydatetime, alive=$qalive, last_response=$qlast_response WHERE id=$id"
				) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	} elsif ( $alive_found == 0 ) {
		# entry exists - as found in ARP cache, device is considered as alive
		$sth = $dbh->prepare("UPDATE host SET alive=1, last_response=$qlast_response WHERE id=$id AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	} else { 
        #entry exists
	}

    $sth->finish();
    $dbh->disconnect;

	return ($return_ip,$hostname_found,$new_id) if $return_ip;
}




sub update_ip_mod {
        my ( $client_id,$ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive ) = @_;
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
        if ( defined($alive) ) {
                my $qalive = $dbh->quote( $alive );
                my $qlast_response = $dbh->quote( time() );
                $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname, host_descr=$qhost_descr, loc=$qloc, int_admin=$qint_admin, categoria=$qcat, comentario=$qcomentario, update_type=$qupdate_type, last_update=$qmydatetime, red_num=$qred_num, alive=$qalive, last_response=$qlast_response WHERE ip=$qip_int AND client_id=$qclient_id"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        } else {
                $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname, host_descr=$qhost_descr, loc=$qloc, int_admin=$qint_admin, categoria=$qcat, comentario=$qcomentario, update_type=$qupdate_type, last_update=$qmydatetime, red_num=$qred_num WHERE ip=$qip_int AND client_id=$qclient_id"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        }
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
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
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT client FROM clients WHERE client=\"$client_name\"
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_client_id_one {
	my ($client_name) = @_; 
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT id FROM clients
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

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

sub get_client_entries {
        my ( $client_id ) = @_;
        my @values;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
	my $sth;
        $sth = $dbh->prepare("SELECT c.client,ce.phone,ce.fax,ce.address,ce.comment,ce.contact_name_1,ce.contact_phone_1,ce.contact_cell_1,ce.contact_email_1,ce.contact_comment_1,ce.contact_name_2,ce.contact_phone_2,ce.contact_cell_2,ce.contact_email_2,ce.contact_comment_2,ce.contact_name_3,ce.contact_phone_3,ce.contact_cell_3,ce.contact_email_3,ce.contact_comment_3,ce.default_resolver,ce.dns_server_1,ce.dns_server_2,ce.dns_server_3 FROM clients c, client_entries ce WHERE c.id = ce.client_id AND c.id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values;
}


sub get_version {
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT version FROM global_config");
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}


sub get_host_hash_id_key {
        my ( $client_id, $red_num ) = @_;
        my %values_ip;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth;
        $sth = $dbh->prepare("SELECT h.id,h.ip, INET_NTOA(h.ip),h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id, h.ip_version FROM host h, locations l, categorias c, update_type ut WHERE red_num=$qred_num AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND h.client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

        my $i=0;
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $hostname = $ip_ref->{'hostname'} || "";
                my $range_id = $ip_ref->{'range_id'} || "";
#               next if ! $hostname;
                my $id = $ip_ref->{'id'};
                my $ip_int = $ip_ref->{'ip'};
                my $ip_version = $ip_ref->{'ip_version'};
		my $ip;
		if ( $ip_version eq "v4" ) {
			$ip = $ip_ref->{'INET_NTOA(h.ip)'};
		} else {
			$ip=int_to_ip("$ip_int","$ip_version");
			
		}
                my $host_descr = $ip_ref->{'host_descr'} || "";
                my $loc = $ip_ref->{'loc'} || "";
                my $cat = $ip_ref->{'cat'} || "";
                my $int_admin = $ip_ref->{'int_admin'} || "";
                my $comentario = $ip_ref->{'comentario'} || "";
                my $update_type = $ip_ref->{'type'} || "NULL";
                my $alive = $ip_ref->{'alive'};
                my $last_response = $ip_ref->{'last_response'} || "";
                push @{$values_ip{$id}},"$ip","$hostname","$host_descr","$loc","$cat","$int_admin","$comentario","$update_type","$alive","$last_response","$range_id";
        }

        $dbh->disconnect;
        return \%values_ip;
}

sub get_loc_id {
        my ( $client_id, $loc ) = @_;
        my $loc_id;
        my $dbh = mysql_connection();
        my $qloc = $dbh->quote( $loc );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT id FROM locations WHERE loc=$qloc AND ( client_id = $qclient_id OR client_id = '9999' )
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $loc_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $loc_id;
}

#sub get_host_id_from_ip {
#        my ( $client_id,$ip ) = @_;
#        my $val;
#        my $dbh = mysql_connection();
#        my $qip = $dbh->quote( $ip );
#        my $qclient_id = $dbh->quote( $client_id );
#        my $sth = $dbh->prepare("SELECT id FROM host WHERE ip=INET_ATON($qip) AND client_id=$qclient_id");
#        $sth->execute() or die "Can not execute statement: $DBI::errstr";
#        $val = $sth->fetchrow_array;
#        $sth->finish();
#        $dbh->disconnect;
#        return $val;
#}

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

sub get_last_host_id {
        my ( $client_id ) = @_;
        my $id;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT id FROM host ORDER BY (id+0) desc
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $id;
}

sub update_host_hostname {
        my ( $client_id, $host_id, $hostname ) = @_;
        my $dbh = mysql_connection();
        my $qhost_id = $dbh->quote( $host_id );
        my $qhostname = $dbh->quote( $hostname );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname WHERE id=$qhost_id AND client_id=$qclient_id
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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

sub get_custom_host_column_entry_complete {
        my ( $client_id, $host_id, $ce_id ) = @_;
        my @values;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qhost_id = $dbh->quote( $host_id );
        my $qce_id = $dbh->quote( $ce_id );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("select distinct cce.entry,cce.cc_id from custom_host_column_entries cce WHERE cce.host_id = $qhost_id AND cce.cc_id = $qce_id AND cce.client_id = $qclient_id
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values, [ @$ip_ref ];
        }
        $sth->finish();
        $dbh->disconnect;
        return \@values;
}

sub get_custom_host_column_entry_from_name {
    my ( $client_id, $host_id, $cc_name ) = @_;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qcc_name = $dbh->quote( $cc_name );
    my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT cce.entry from custom_host_column_entries cce WHERE cce.host_id = $qhost_id AND cce.cc_id = ( SELECT id FROM custom_host_columns WHERE name = $qcc_name AND (client_id = $qclient_id OR client_id='9999'))
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        my $entry = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $entry;
}


sub update_custom_host_column_value_host {
        my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;
        my $dbh = mysql_connection();
        my $qcc_id = $dbh->quote( $cc_id );
        my $qpc_id = $dbh->quote( $pc_id );
        my $qhost_id = $dbh->quote( $host_id );
        my $qentry = $dbh->quote( $entry );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET cc_id=$qcc_id,entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}

sub insert_custom_host_column_value_host {
        my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;
        my $dbh = mysql_connection();
        my $qcc_id = $dbh->quote( $cc_id );
        my $qpc_id = $dbh->quote( $pc_id );
        my $qhost_id = $dbh->quote( $host_id );
        my $qentry = $dbh->quote( $entry );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("INSERT INTO custom_host_column_entries (cc_id,pc_id,host_id,entry,client_id) VALUES ($qcc_id,$pc_id,$qhost_id,$qentry,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}

sub get_predef_host_column_all_hash {
        my ( $client_id ) = @_;
        my $dbh = mysql_connection();
        my $ip_ref;
        my %values;
        my $sth = $dbh->prepare("SELECT id,name FROM predef_host_columns WHERE id != '-1'
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $id = $ip_ref->{id};
                my $name = $ip_ref->{name};
                push @{$values{$name}},"$id";
        }
        $sth->finish();
        $dbh->disconnect;
        return %values;
}

sub get_global_config {
        my ( $client_id ) = @_;
        my @values_config;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT version, default_client_id, confirmation, mib_dir, vendor_mib_dirs FROM global_config") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_config, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_config;
}


sub create_snmp_session {
	my ($client_id,$node,$community,$community_type,$snmp_version,$auth_pass,$auth_proto,$auth_is_key,$priv_proto,$priv_pass,$priv_is_key,$sec_level,$snmp_port) = @_;

	my $session;
	my $error;

    my $timeout = 400000;
    my $retries = 1;

	$snmp_port=161 if ! $snmp_port;
    my $ipversion = ip_get_version ($node);
    $node="udp6:" . $node if $ipversion eq "6";

	if ( $snmp_version == "1" || $snmp_version == "2" ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						Timeout => $timeout,
						Retries => $retries,
						Verbose => 1
						);
	} elsif ( $snmp_version == "3" && $community && ! $auth_proto && ! $priv_proto ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && ! $auth_is_key && ! $priv_proto ) {
		$session = new SNMP::Session(DestHost => $node,
						Debug=>1,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthPass => $auth_pass,
						AuthProto => $auth_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $auth_is_key && ! $priv_proto ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && ! $auth_is_key && ! $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthPass => $auth_pass,
						AuthProto => $auth_proto,
						PrivPass => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && $auth_is_key && ! $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						PrivPass => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && ! $auth_is_key && $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthPass => $auth_pass,
						AuthProto => $auth_proto,
						PrivMasterKey => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && $auth_is_key && $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						PrivMasterKey => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} else {
		$exit_message = "Can not determine SecLevel";
		exit_error("$exit_message", "$gip_job_status_id", 4 );
	}

	return $session;
}


sub create_snmp_info_session {
	my ($client_id,$node,$community,$community_type,$snmp_version,$auth_pass,$auth_proto,$auth_is_key,$priv_proto,$priv_pass,$priv_is_key,$sec_level,$mibdirs_ref,$vars_file,$snmp_port) = @_;

	my $session;
	my $error;

    my $timeout = 400000;
    my $retries = 1;

	$snmp_port=161 if ! $snmp_port;

        my $ipversion = ip_get_version ($node);
        $node="udp6:" . $node if $ipversion eq "6";


	if ( $snmp_version == "1" || $snmp_version == "2" ) {
		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => 0,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
#			Timeout => $timeout,
			Retries => $retries,
		);

	} elsif ( $snmp_version == "3" && $community && ! $auth_proto && ! $priv_proto ) {

		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => 0,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			SecLevel => $sec_level,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
			);

	} elsif ( $snmp_version == "3" && $auth_proto && ! $auth_is_key && ! $priv_proto ) {

		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => 0,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			SecLevel => $sec_level,
			AuthPass => $auth_pass,
			AuthProto => $auth_proto,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
			);
	} elsif ( $snmp_version == "3" && $auth_proto && $auth_is_key && ! $priv_proto ) {

		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => 0,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			SecLevel => $sec_level,
			AuthLocalizedKey => $auth_pass,
			AuthProto => $auth_proto,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
			);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && ! $auth_is_key && ! $priv_is_key ) {

		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => 0,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			SecLevel => $sec_level,
			AuthPass => $auth_pass,
			AuthProto => $auth_proto,
			PrivPass => $priv_pass,
			PrivProto => $priv_proto,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
			);

	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && $auth_is_key && ! $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						PrivPass => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && ! $auth_is_key && $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthPass => $auth_pass,
						AuthProto => $auth_proto,
						PrivMasterKey => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $priv_proto && $auth_is_key && $priv_is_key ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						PrivMasterKey => $priv_pass,
						PrivProto => $priv_proto,
						UseSprintValue => 1,
						RemotePort => $snmp_port,
						);
	} else {
		print "Can not determine SecLevel\n";
	}

	return $session;
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


        my @fetch_zone = $res->axfr("$zone_name");

        my $i=0;
        my $rr;
        foreach $rr (@fetch_zone) {
                $zone_records[$i]=$rr->string;
                $i++;
        }
        return @zone_records;
}

sub get_host_from_red_num {
        my ( $client_id, $red_num ) = @_;
        my @values_ip;
        my $ip_ref;
	my $dbh = mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT h.ip, h.hostname, h.host_descr, l.loc, c.cat, h.int_admin, h.comentario, ut.type, h.alive, h.last_response, h.range_id, h.id FROM host h, locations l, categorias c, update_type ut WHERE h.red_num=$qred_num AND h.loc = l.id AND h.categoria = c.id AND h.update_type = ut.id AND h.client_id = $qclient_id ORDER BY h.ip"
                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values_ip, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_ip;
}


sub get_loc_hash {
	my ( $client_id ) = @_;
	my %values;
	my $ip_ref;
	my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT id,loc FROM locations WHERE ( client_id = $qclient_id OR client_id = '9999' )") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $id = $ip_ref->{'id'};
		my $loc = $ip_ref->{'loc'};
		$values{$loc}="$id";
	}

	$dbh->disconnect;

	return \%values;
}


sub get_redes_hash_key_red {
	my ( $client_id, $ip_version, $return_int ) = @_;
	my $ip_ref;
	$ip_version="" if ! $ip_version;
	$return_int="" if ! $return_int;
	my %values_redes;

#	my %tags = get_tag_hash("$client_id", "name");

	my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );

	my $ip_version_expr="";
	$ip_version_expr="AND n.ip_version='$ip_version'" if $ip_version;
	my $client_id_expr="";
	$client_id_expr="AND n.client_id=$qclient_id" if $client_id;

	my $sth = $dbh->prepare("SELECT n.red_num, n.red, n.BM, n.descr, l.loc, l.id, n.vigilada, n.comentario, c.cat, n.ip_version, INET_ATON(n.red), n.rootnet FROM net n, categorias_net c, locations l WHERE c.id = n.categoria AND l.id = n.loc AND n.rootnet = 0 $ip_version_expr $client_id_expr") 
		or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
					$red_int = ip_to_int($red,"$ip_version");
				}
			}
			my $rootnet=$ip_ref->{'rootnet'};

			push @{$values_redes{$red}},"$red_num","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$loc_id";
		}

        $dbh->disconnect;
        return \%values_redes;
}


sub get_host_redes_no_rootnet {
	my ( $client_id ) = @_;
	my @host_redes;
	my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT red, BM, red_num, loc, ip_version, rootnet FROM net WHERE rootnet = '0' AND client_id = $qclient_id")
		or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @host_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @host_redes;
}


sub insert_custom_column_value_red {
	my ( $client_id, $cc_id, $net_id, $entry ) = @_;

	my $ip_ref;
	my @values;
        my $dbh = mysql_connection();
	my $qcc_id = $dbh->quote( $cc_id );
	my $qnet_id = $dbh->quote( $net_id );
	my $qentry = $dbh->quote( $entry );
	my $qclient_id = $dbh->quote( $client_id );


        my $sth = $dbh->prepare("SELECT cc_id FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id AND entry=$qentry") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @values, [ @$ip_ref ];
        }


	if ( ! $values[0] ) {
		$sth = $dbh->prepare("INSERT INTO custom_net_column_entries (cc_id,net_id,entry,client_id) VALUES ($qcc_id,$qnet_id,$qentry,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	}


        $sth->finish();
        $dbh->disconnect;
}

sub update_custom_column_value_red {
	my ( $client_id, $cc_id, $net_id, $entry ) = @_;
	my $dbh = mysql_connection();
	my $qcc_id = $dbh->quote( $cc_id );
	my $qnet_id = $dbh->quote( $net_id );
	my $qentry = $dbh->quote( $entry );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("UPDATE custom_net_column_entries SET entry=$qentry WHERE cc_id=$qcc_id AND net_id=$qnet_id");
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


sub get_custom_column_entry {
	my ( $client_id, $red_num, $cc_name ) = @_;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qcc_name = $dbh->quote( $cc_name );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT cce.entry from custom_net_column_entries cce WHERE cce.net_id = $qred_num AND cce.cc_id = ( SELECT id FROM custom_net_columns WHERE name = $qcc_name AND (client_id = $qclient_id OR client_id='9999'))
		") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	my $entry = $sth->fetchrow_array;
	$sth->finish();
	$dbh->disconnect;
	return $entry;
}


sub get_red_num_from_host_ip_int {
	my ( $client_id, $ip_int ) = @_;
	my $id;
	my $val;
	my $dbh = mysql_connection();
	my $qip_int = $dbh->quote( $ip_int );
	my $qclient_id = $dbh->quote( $client_id );

	my $sth = $dbh->prepare("SELECT id FROM host WHERE ip=$qip_int AND client_id=$qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$id = $sth->fetchrow_array;

	my $qid = $dbh->quote( $id );

	$sth = $dbh->prepare("SELECT red_num FROM host WHERE id=$qid AND client_id=$qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$val = $sth->fetchrow_array;

	$sth->finish();
	$dbh->disconnect;

	return $val;
}


sub update_host_ping_info {
	my ( $client_id,$ip_int,$ping_result_new,$enable_ping_history,$ip_ad,$update_type_audit,$vars_file) = @_;

	$enable_ping_history="1" if ! $enable_ping_history;
	$update_type_audit="3" if ! $update_type_audit;
	my $ping_result_old;

    my $dbh = mysql_connection();
	my $qip_int = $dbh->quote( $ip_int );

	my $qmydatetime = $dbh->quote( time() );
	my $alive = $dbh->quote( $ping_result_new );
    my $qclient_id = $dbh->quote( $client_id );

	my $sth;

	$sth = $dbh->prepare("SELECT alive FROM host WHERE ip=$qip_int AND client_id = $qclient_id
		") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute();
	$ping_result_old = $sth->fetchrow_array || "";
	$ping_result_old = 0 if ! $ping_result_old || $ping_result_old eq "NULL";

	$sth = $dbh->prepare("UPDATE host SET alive=$alive, last_response=$qmydatetime WHERE ip=$qip_int AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
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
}


### Network usage column

sub update_net_usage_cc_column {
    my ($client_id, $ip_version, $red_num, $BM) = @_;

    my ($ip_total, $ip_ocu, $free) = get_red_usage("$client_id", "$ip_version", "$red_num", "$BM");
    my $cc_id_usage = get_custom_column_id_from_name("$client_id", "usage") || "";
    my $cc_usage_entry = "$ip_total,$ip_ocu,$free" || "";
    update_or_insert_custom_column_value_red("$client_id", "$cc_id_usage", "$red_num", "$cc_usage_entry") if $cc_id_usage && $cc_usage_entry;
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


sub update_or_insert_custom_column_value_red {
    my ( $client_id, $cc_id, $net_id, $entry ) = @_;

    my $dbh = mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qnet_id = $dbh->quote( $net_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id");
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

sub get_snmp_group_id_from_name {
    my ( $client_id, $name ) = @_;

    my $value;
    my $dbh = mysql_connection();
    my $qname = $dbh->quote( $name );

    my $sth = $dbh->prepare("SELECT id FROM snmp_group WHERE name=$qname
                    ")  or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute()  or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $value = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $value;
}

sub get_snmp_groups {
    my ( $client_id, $id ) = @_;
    my (@values,$ip_ref);
    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qid = $dbh->quote( $id ) if $id;

    my $filter = "";
    $filter = " AND id=$qid" if $id;

    my $sth = $dbh->prepare("SELECT id, name, snmp_version, port, community, user_name, sec_level, auth_algorithm, auth_password, priv_algorithm, priv_password, comment, client_id FROM snmp_group WHERE client_id=$qclient_id $filter ORDER BY name") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $dbh->disconnect;
    $sth->finish(  );
    return @values;
}


# SNMP parameters
sub get_snmp_parameter {
    my ( $client_id, $id, $object, $snmp_group_id_arg ) = @_;

    my ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port);
    $snmp_version=$community=$snmp_user_name=$sec_level=$auth_proto=$auth_pass=$priv_proto=$priv_pass=$community_type=$auth_is_key=$priv_is_key=$snmp_port="";

	my $snmp_group_name = "";
	if ( $object eq "network" ) {
		$snmp_group_name = get_custom_column_entry("$client_id", "$id", "SNMPGroup") || "";
	} elsif ( $object eq "host" ) {
		$snmp_group_name = get_custom_host_column_entry_from_name("$client_id", "$id", "SNMPGroup") || "";
	}

	if ( $snmp_group_id_arg ) {
            my @snmp_group_values = get_snmp_groups("$client_id","$snmp_group_id_arg");

            $snmp_version = $snmp_group_values[0]->[2];
            $snmp_port = $snmp_group_values[0]->[3] || 161;
            $community = $snmp_group_values[0]->[4];
            $snmp_user_name = $snmp_group_values[0]->[5];
            $sec_level = $snmp_group_values[0]->[6];
            $auth_proto = $snmp_group_values[0]->[7];
            $auth_pass = $snmp_group_values[0]->[8];
            $priv_proto = $snmp_group_values[0]->[9];
            $priv_pass = $snmp_group_values[0]->[10];

            $community = $snmp_user_name if $snmp_version eq 3;
	} elsif ( $snmp_group_name ) {
		my $snmp_group_id = get_snmp_group_id_from_name("$client_id","$snmp_group_name");
		if ( ! $snmp_group_id ) {
			print "SNMP Group not found: $snmp_group_name\n";
		} else {
            my @snmp_group_values = get_snmp_groups("$client_id","$snmp_group_id");

            $snmp_version = $snmp_group_values[0]->[2];
            $snmp_port = $snmp_group_values[0]->[3] || 161;
            $community = $snmp_group_values[0]->[4];
            $snmp_user_name = $snmp_group_values[0]->[5];
            $sec_level = $snmp_group_values[0]->[6];
            $auth_proto = $snmp_group_values[0]->[7];
            $auth_pass = $snmp_group_values[0]->[8];
            $priv_proto = $snmp_group_values[0]->[9];
            $priv_pass = $snmp_group_values[0]->[10];

            $community = $snmp_user_name if $snmp_version eq 3;
        }

#		print "Using SNMP Group: $snmp_group_name\n" if $verbose;
	} else {
		$snmp_version = $snmp_version_arg || $params{'snmp_version'};
		$community = $community_arg || $params{'snmp_community_string'};
        $snmp_port = $snmp_port_arg || 161;

		if ( $snmp_version eq "3" ) {
			$community = $snmp_user_name_arg || $params{'snmp_user_name'};
			$sec_level = $sec_level_arg || $params{'sec_level'};
			$auth_proto = $auth_proto_arg || $params{'auth_proto'};
			$auth_pass = $auth_pass_arg || $params{'auth_pass'};
			$priv_proto = $priv_proto_arg || $params{'priv_proto'};
			$priv_pass = $priv_pass_arg || $params{'priv_pass'};
			if ( ! $sec_level ) {
				$exit_message = "Please configure parameter \"sec_level\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			}
			if ( $sec_level eq "noAuthNoPriv" ) {
				$auth_proto= "";
				$auth_pass= "";
				$priv_proto= "";
				$priv_pass= "";
				$auth_is_key="";
				$priv_is_key="";
			} elsif ( $sec_level eq "authNoPriv" ) {
				$priv_proto= "";
				$priv_pass= "";
				$auth_is_key="";
				$priv_is_key="";
			} elsif ( $sec_level eq "authPriv" ) {
				$auth_is_key="";
				$priv_is_key="";
			} else {
				$exit_message = "\"sec_level\" must be either noAuthNoPriv, authNoPriv or authPriv";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
				exit 1;
			}
			
			if ( $sec_level eq "authNoPriv" && ! $auth_proto ) {
				$exit_message = "Please configure parameter \"auth_proto\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			} elsif ( $sec_level eq "authNoPriv" && ! $auth_pass ) {
				$exit_message = "Please configure parameter \"auth_pass\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			} elsif ( $sec_level eq "authPriv" && ! $auth_proto ) {
				print "Please configure parameter \"auth_proto\"\n";
				exit 1;
			} elsif ( $sec_level eq "authPriv" && ! $auth_pass ) {
				$exit_message = "Please configure parameter \"auth_pass\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			} elsif ( $sec_level eq "authPriv" && ! $priv_proto ) {
				$exit_message = "Please configure parameter \"priv_proto\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			} elsif ( $sec_level eq "authPriv" && ! $priv_pass ) {
				$exit_message = "Please configure parameter \"priv_pass\"";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			}
			my $auth_pass_length=length($auth_pass);
			if ( $sec_level ne "noAuthNoPriv" && $auth_pass_length < 8 ) {
				$exit_message = "auth_pass must contain at least 8 characters";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			}
			my $priv_pass_length=length($auth_pass);
			if ( $sec_level ne "noAuthNoPriv" && $priv_pass_length < 8 ) {
				$exit_message = "priv_pass must contain at least 8 characters";
				exit_error("$exit_message", "$gip_job_status_id", 4 );
			}
		}
	}

	if ( ! $snmp_version ) {
			$exit_message = "Parameter \"snmp_version\" missing";
			exit_error("$exit_message", "$gip_job_status_id", 4 );
	} elsif ( $snmp_version !~ /^1|2|3$/ ) {
			$exit_message = "Wrong \"snmp version\"";
			exit_error("$exit_message", "$gip_job_status_id", 4 );
	}
	if ( ! $community ) {
			$exit_message = "Please configure parameter \"snmp_community_string\"\n" if $snmp_version ne "3";
			$exit_message = "Please configure parameter \"snmp_user_name\"" if $snmp_version eq "3";
			exit_error("$exit_message", "$gip_job_status_id", 4 );
	}
	$community_type="Community";
	if ( $snmp_version == "3" ) {
			$community_type = "SecName";
	}


    return ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port, $snmp_group_name)
}

sub get_dns_server_group_from_id {
    my ( $client_id, $id ) = @_;
    my @values;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qid = $dbh->quote( $id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT name, description, dns_server1, dns_server2, dns_server3, client_id FROM dns_server_group WHERE id=$qid ORDER BY name") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $sth->finish();
    $dbh->disconnect;

    return @values;
}


sub get_db_parameter {
    my ($document_root) = @_;
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    unshift @document_root, "$document_root" if $document_root;
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or print "Can not open $priv_file: $!\n";
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

sub exit_error {
    my ( $message, $gip_job_status_id, $status, $exit_signal ) = @_;

    $exit_signal = "1" if ! $exit_signal;
    $exit_signal = "0" if $exit_signal eq "OK";

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;

    if ( $gip_job_status_id && ! $combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

#        my $time = scalar(localtime(time + 0));
        my $time=time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close LOG  if fileno LOG;

    Gipfuncs::send_mail (
        debug       =>  "$debug",
        mail_from   =>  $mail_from,
        mail_to     =>  \@mail_to,
        subject     => "Result $job_name",
        smtp_server => "$smtp_server",
        smtp_message    => "",
        log         =>  "$log",
        gip_job_status_id   =>  "$gip_job_status_id",
        changes_only   =>  "$changes_only",
    ) if $mail;

    exit $exit_signal;
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


__DATA__
