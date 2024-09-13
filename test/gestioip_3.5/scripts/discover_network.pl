#!/usr/bin/perl -w

# Version 3.5.7 20210527


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

$dir =~ /^(.*)\/bin/;
$base_dir=$1;
my $tmp_dir = $base_dir . "/tmp";


my ( $verbose, $mail, $help, $import_host_routes, $report_not_found_networks, $get_vrf_routes, $ascend, $descend, $add_if_descr, $interfaces_descr_indent, $delete_not_found_networks  );
my $config_name="";
my $nodes_file="";
my $nodes_list="";
my $tag="";
my $set_sync_flag=0;
my $force_site="";
my $write_new_to_file="";
my $only_added_mail=0;
my $debug ="";
my $gip_job_id ="";
my $logdir = "";
my $changes_only = "";
my $delete_down_hosts = "";

my ( $client, $ignore_generic_auto, $snmp_version, $snmp_community_string, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $actualize_ipv4, $actualize_ipv6, $generic_dyn_host_name, $ignorar, $dyn_ranges_only, $max_sinc_procs, $bin_dir, $user, $execute_vlan_discovery, $execute_host_discovery_dns, $execute_host_discovery_snmp, $snmp_group, $run_once, $assign_tags, $smtp_server, $mail_from, $mail_to, $ignore_arp_cache );


$execute_vlan_discovery=$execute_host_discovery_dns=$execute_host_discovery_snmp=$report_not_found_networks=$delete_not_found_networks="";

GetOptions(
        "A=s"=>\$client,
        "B=s"=>\$ignore_generic_auto,
        "D=s"=>\$snmp_version,
        "E=s"=>\$snmp_community_string,
        "F=s"=>\$snmp_user_name,
        "G=s"=>\$sec_level,
        "H=s"=>\$auth_proto,
        "I=s"=>\$auth_pass,
        "J=s"=>\$priv_proto,
        "K=s"=>\$priv_pass,
        "M=s"=>\$logdir,
#		"Network_file=s"=>\$network_file,
        "T=s"=>\$actualize_ipv4,
        "O=s"=>\$actualize_ipv6,
        "P=s"=>\$generic_dyn_host_name,
        "Q=s"=>\$ignorar,
        "R!"=>\$dyn_ranges_only,
        "S=s"=>\$max_sinc_procs,
        "Set_sync_flag!"=>\$set_sync_flag,

#        "U=s"=>\$bin_dir,

        "assign_tags=s"=>\$assign_tags,
        "changes_only!"=>\$changes_only,
        "config_file_name=s"=>\$config_name,
        "delete_down_hosts!"=>\$delete_down_hosts,
        "delete_not_found_networks!"=>\$delete_not_found_networks,
        "report_not_found_networks!"=>\$report_not_found_networks,
        "force_site=s"=>\$force_site,
        "get_vrf_routes!"=>\$get_vrf_routes,
        "import_host_routes!"=>\$import_host_routes,
        "ignore_arp_cache!"=>\$ignore_arp_cache,
        "j!"=>\$add_if_descr,
        "k=s"=>\$interfaces_descr_indent,
        "mail!"=>\$mail,
		"smtp_server=s"=>\$smtp_server,
        "mail_from=s"=>\$mail_from,
        "mail_to=s"=>\$mail_to,
        "nodes_file=s"=>\$nodes_file,
        "CSV_nodes=s"=>\$nodes_list,
        "tag=s"=>\$tag,
        "execute_vlan_discovery!"=>\$execute_vlan_discovery,
        "execute_host_discovery_dns!"=>\$execute_host_discovery_dns,
        "execute_host_discovery_snmp!"=>\$execute_host_discovery_snmp,
        "user=s"=>\$user,
        "snmp_group=s"=>\$snmp_group,
        "run_once!"=>\$run_once,
        "verbose!"=>\$verbose,
		"W=s"=>\$gip_job_id,
        "x!"=>\$debug,
        "help!"=>\$help
) or print_help();

if ( $help ) { print_help(); }

my $start_time = time();

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

my $gip_job_status_id = "";
my $job_name = "";
if ( $gip_job_id ) {

	my $job_status = Gipfuncs::check_disabled("$gip_job_id");
    if ( $job_status != 1 ) {
        exit;
    }

	my $check_start_date = Gipfuncs::check_start_date("$gip_job_id", "5") || "";
	if ( $check_start_date eq "TOO_EARLY" ) {
		exit;
	}

	$job_name = Gipfuncs::get_job_name("$gip_job_id");
	my $audit_type="176";
	my $audit_class="33";
	my $update_type_audit="2";

	my $event="$job_name ($gip_job_id)";
	insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");
}

$verbose = 1 if $debug;


my ( $client_arg, $ignore_generic_auto_arg, $snmp_version_arg, $snmp_community_string_arg, $snmp_user_name_arg, $sec_level_arg, $auth_proto_arg, $auth_pass_arg, $priv_proto_arg, $priv_pass_arg, $logdir_arg, $actualize_ipv4_arg, $actualize_ipv6_arg, $generic_dyn_host_name_arg, $ignorar_arg, $dyn_ranges_only_arg, $max_sinc_procs_arg, $config_name_arg, $verbose_arg, $debug_arg, $force_site_arg, $add_if_descr_arg, $interfaces_descr_indent_arg, $nodes_file_arg, $nodes_list_arg, $tag_arg, $user_arg, $get_vrf_routes_arg, $import_host_routes_arg, $snmp_group_arg, $run_once_arg, $assign_tags_arg, $set_sync_flag_arg, $changes_only_arg, $delete_down_hosts_arg, $report_not_found_networks_arg, $delete_not_found_networks_arg, $ignore_arp_cache_arg);

$client_arg=$ignore_generic_auto_arg=$snmp_version_arg=$snmp_community_string_arg=$snmp_user_name_arg=$sec_level_arg=$auth_proto_arg=$auth_pass_arg=$priv_proto_arg=$priv_pass_arg=$logdir_arg=$actualize_ipv4_arg=$actualize_ipv6_arg=$generic_dyn_host_name_arg=$ignorar_arg=$dyn_ranges_only_arg=$max_sinc_procs_arg=$config_name_arg=$verbose_arg=$debug_arg=$force_site_arg=$add_if_descr_arg=$interfaces_descr_indent_arg=$nodes_file_arg=$nodes_list_arg=$tag_arg=$user_arg=$get_vrf_routes_arg=$import_host_routes_arg=$snmp_group_arg=$run_once_arg=$assign_tags_arg=$set_sync_flag_arg=$changes_only_arg=$delete_down_hosts_arg=$report_not_found_networks_arg=$delete_not_found_networks_arg=$ignore_arp_cache_arg="";

if ( $client ) {
	$client_arg = "--A=\"$client\"";
}
if ( $ignore_generic_auto ) {
	$ignore_generic_auto_arg = "--B=\"$ignore_generic_auto\"";
}
if ( $snmp_version ) {
	$snmp_version_arg = "--D=\"$snmp_version\"";
}
if ( $snmp_community_string ) {
	$snmp_community_string_arg = "--E=\"$snmp_community_string\"";
}
if ( $snmp_user_name ) {
	$snmp_user_name_arg = "--F=\"$snmp_user_name\"";
}
if ( $sec_level ) {
	$sec_level_arg = "--G=\"$sec_level\"";
}
if ( $auth_proto ) {
	$auth_proto_arg = "--H=\"$auth_proto\"";
}
if ( $auth_pass ) {
	$auth_pass_arg = "--I=\"$auth_pass\"";
}
if ( $priv_proto ) {
	$priv_proto_arg = "--J=\"$priv_proto\"";
}
if ( $priv_pass ) {
	$priv_pass_arg = "--K=\"$priv_pass\"";
}
if ( $actualize_ipv4 ) {
	$actualize_ipv4_arg = "--T=\"$actualize_ipv4\"";
}
if ( $actualize_ipv6 ) {
	$actualize_ipv6_arg = "--O=\"$actualize_ipv6\"";
}
if ( $generic_dyn_host_name ) {
	$generic_dyn_host_name_arg = "--P=\"$generic_dyn_host_name\""; 
}
if ( $ignorar ) {
	$ignorar_arg = "--Q=\"$ignorar\"";
}
if ( $dyn_ranges_only ) {
	$dyn_ranges_only_arg = "--R=\"$dyn_ranges_only\"";
}
if ( $max_sinc_procs ) {
	$max_sinc_procs_arg = "--S=\"$max_sinc_procs\"";
}
if ( $config_name ) {
	$config_name_arg = "--config_file_name=\"$config_name\"";
}
if ( $force_site ) {
	$force_site_arg = "--f=\"$force_site\"";
}
if ( $add_if_descr ) {
	$add_if_descr_arg = "-j";
}
if ( $interfaces_descr_indent ) {
	$interfaces_descr_indent_arg = "--k=\"$interfaces_descr_indent\"";
}
if ( $nodes_file ) {
	$nodes_file_arg = "--nodes_file=\"$nodes_file\"";
}
if ( $nodes_list ) {
	$nodes_list_arg = "--CSV_nodes=\"$nodes_list\"";
}
if ( $tag ) {
	$tag_arg = "--tag=$tag";
}
if ( $assign_tags ) {
	$assign_tags_arg = "--assign_tags=\"$assign_tags\"";
}
if ( $get_vrf_routes ) {
	$get_vrf_routes_arg = "--get_vrf_routes";
}
if ( $import_host_routes ) {
	$import_host_routes_arg = "--import_host_routes";
}
if ( $ignore_arp_cache ) {
	$ignore_arp_cache_arg = "--ignore_arp_cache";
}
if ( $user ) {
	$user_arg = "--user=\"$user\"";
}
if ( $snmp_group ) {
	$snmp_group_arg = "--snmp_group=\"$snmp_group\"";
}
if ( $verbose ) {
	$verbose_arg = "-v";
}
if ( $set_sync_flag ) {
	$set_sync_flag_arg = "--Set_sync_flag";
}
if ( $logdir ) {
	$logdir_arg = "--M=\"$logdir\"";
}
if ( $delete_not_found_networks ) {
	$delete_not_found_networks_arg = "--delete_not_found_networks";
}
if ( $report_not_found_networks ) {
	$report_not_found_networks_arg = "--report_not_found_networks";
}

if ( $debug ) {
	$debug_arg = "--x";
}
if ( $run_once ) {
	$run_once_arg = "--run_once";
}
if ( $changes_only ) {
	$changes_only_arg = "--changes_only";
}
if ( $delete_down_hosts ) {
	$delete_down_hosts_arg = "--delete_down_hosts";
}

my $combined_job_arg = " --combined_job";

my %result_hash;
my $result_warning = 0;

my $log = "";
my $datetime;
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "discover_network");
my $log_date = $datetime;
$log_date =~ s/-//g;
$log_date =~ s/\s//g;
$log_date =~ s/://g;
my $log_dir = $log;
$log_dir =~ s/\/\d+.+log$//;


print "Logfile: $log\n" if $verbose;

my $log_mail_tmp = $tmp_dir . "/discover_network_" . $gip_job_id . ".tmp";
open(LOG,">$log") or exit_error("Can not open $log: $!", "$gip_job_status_id", 4);
open(LOG_MAIL,">$log_mail_tmp") or exit_error("Can not open $log_mail_tmp: $!", "", 4);

my $logfile_name_log = "";
my $logfile_name = $log;
$logfile_name =~ s/^(.*\/)//;
$logfile_name_log .= $logfile_name;

my $delete_job_error;
if ( $gip_job_id ) {
    if ( $run_once ) {
        $delete_job_error = delete_cron_entry("$gip_job_id");
        if ( $delete_job_error ) {
            print LOG "ERROR: Job not deleted from crontab: $delete_job_error";
            print LOG_MAIL "ERROR: Job not deleted from crontab: $delete_job_error";
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




#### Execute sub commmands

$logfile_name = $log_date . "_" . $client . "_get_networks_snmp.log";
$logfile_name_log .= ", " . $logfile_name;

my $log_arg = "--log=\"$logfile_name\"";

my $write_new_to_file_arg = "";
$write_new_to_file_arg = "--write_new_to_file=" . $log_date . "_discover_networks" if $execute_host_discovery_dns || $execute_host_discovery_snmp;
my $network_file = $log_date . "_discover_networks";
my $network_file_arg = "";
$network_file_arg = "--Network_file=" . $network_file if $execute_host_discovery_dns || $execute_host_discovery_snmp;

my $command = $dir . "/get_networks_snmp.pl $verbose_arg $debug_arg $config_name_arg $client_arg $snmp_version_arg $snmp_community_string_arg $snmp_user_name_arg $sec_level_arg $auth_proto_arg $auth_pass_arg $priv_proto_arg $priv_pass_arg $force_site_arg $add_if_descr_arg $interfaces_descr_indent_arg $nodes_file_arg $nodes_list_arg $tag_arg $actualize_ipv4_arg $actualize_ipv6_arg $get_vrf_routes_arg $import_host_routes_arg $user_arg $log_arg $combined_job_arg $snmp_group_arg $write_new_to_file_arg $run_once_arg $assign_tags_arg $set_sync_flag_arg $changes_only_arg $delete_not_found_networks_arg $report_not_found_networks_arg";

$command =~ s/\s{2,}/ /g;

print "EXECUTING $command\n" if $verbose;
print LOG "EXECUTING $command\n";
print LOG_MAIL "EXECUTING $command\n\n";

my @result = `$command`;
my $return_value=$?;

read_and_print_log("$log_dir/$logfile_name");

my $result_message = "";
if ( $return_value != 0 ) {
	$result_warning = 1;
	if ( @result ) {
		$result_message = $result[$#result];
	} else {
		$result_message = "ERROR: NO OUTPUT FROM SCRIPT";
	}
	$result_hash{"get_networks_snmp"} = $result_message;

	print LOG "Network discovery: $result_message\n";
	print LOG_MAIL "Network discovery: $result_message\n";


} else {
	$result_hash{"get_networks_snmp"} = "OK";
	print LOG "Network discovery - OK\n\n";
	print LOG_MAIL "Network discovery - OK\n\n";

    if ( $execute_vlan_discovery ) {
        $logfile_name = $log_date . "_" . $client . "_ip_import_vlans.log";
        $logfile_name_log .= ", " . $logfile_name;
        $log_arg = "--log=\"$logfile_name\"";

        $command = $dir . "/ip_import_vlans.pl $verbose_arg $debug_arg $nodes_file_arg $nodes_list_arg $tag_arg $client_arg $user_arg $log_arg $combined_job_arg $snmp_group_arg $run_once_arg $changes_only_arg";

        $command =~ s/\s{2,}/ /g;
        print "\nEXECUTING $command\n\n" if $verbose;
        print LOG "EXECUTING $command\n";
        print LOG_MAIL "EXECUTING $command\n\n";

        @result = `$command`;
        $return_value=$?;

        read_and_print_log("$log_dir/$logfile_name");

		my $result_message = "";
        if ( $return_value != 0 ) {
            $result_warning = 1;
			if ( @result ) {
				$result_message = $result[$#result];
			} else {
				$result_message = "ERROR: NO OUTPUT FROM SCRIPT";
			}
            $result_hash{"ip_import_vlans"} = $result_message;
            print LOG "VLAN discovery - $result_message\n";
            print LOG_MAIL "VLAN discovery - $result_message\n";
        } else {
            print LOG "VLAN discovery - OK\n\n";
            print LOG_MAIL "VLAN discovery - OK\n\n";
        }
    }

    if ( $execute_host_discovery_dns ) {
        $logfile_name = $log_date . "_" . $client . "_ip_update_gestioip_dns.log";
        $logfile_name_log .= ", " . $logfile_name;
        $log_arg = "--log=\"$logfile_name\"";

        $command = $dir . "/ip_update_gestioip_dns.pl $verbose_arg $debug_arg $config_name_arg $network_file_arg $client_arg $ignore_generic_auto_arg $actualize_ipv4_arg $actualize_ipv6_arg $generic_dyn_host_name_arg $ignorar_arg $dyn_ranges_only_arg $max_sinc_procs_arg $user_arg $log_arg $combined_job_arg $run_once_arg $changes_only_arg $delete_down_hosts_arg";

        $command =~ s/\s{2,}/ /g;
        print "\nEXECUTING $command\n\n" if $verbose;
        print LOG "EXECUTING $command\n";
        print LOG_MAIL "EXECUTING $command\n\n";

        @result = `$command`;
        $return_value=$?;

        read_and_print_log("$log_dir/$logfile_name");

		my $result_message = "";
        if ( $return_value != 0 ) {
            $result_warning = 1;
			if ( @result ) {
				$result_message = $result[$#result];
			} else {
				$result_message = "ERROR: NO OUTPUT FROM SCRIPT";
			}
            $result_hash{"ip_update_gestioip_dns"} = $result_message;
            print LOG "Host discovery DNS - $result_message\n";
            print LOG_MAIL "Host discovery DNS - $result_message\n";
        } else {
            print LOG "Host discovery DNS - OK\n\n";
            print LOG_MAIL "Host discovery DNS - OK\n\n";
        }
    }

    if ( $execute_host_discovery_snmp ) {
        $logfile_name = $log_date . "_" . $client . "_ip_update_gestioip_snmp.log";
        $logfile_name_log .= ", " .  $logfile_name;
        $log_arg = "--log=\"$logfile_name\"";

        $command = $dir . "/ip_update_gestioip_snmp.pl $verbose_arg $debug_arg $config_name_arg $network_file_arg $client_arg $snmp_version_arg $snmp_community_string_arg $snmp_user_name_arg $sec_level_arg $auth_proto_arg $auth_pass_arg $priv_proto_arg $priv_pass_arg $actualize_ipv4_arg $actualize_ipv6_arg $dyn_ranges_only_arg $max_sinc_procs_arg $user_arg $log_arg $combined_job_arg $snmp_group_arg $run_once_arg $changes_only_arg $ignore_arp_cache_arg";

        $command =~ s/\s{2,}/ /g;
        print "\nEXECUTING $command\n\n" if $verbose;
        print LOG "EXECUTING $command\n";
        print LOG_MAIL "EXECUTING $command\n\n";

        @result = `$command`;
        $return_value=$?;

        read_and_print_log("$log_dir/$logfile_name");

		my $result_message = "";
        if ( $return_value != 0 ) {
            $result_warning = 1;
			if ( @result ) {
				$result_message = $result[$#result];
			} else {
				$result_message = "ERROR: NO OUTPUT FROM SCRIPT";
			}
            $result_hash{"ip_update_gestioip_dns"} = $result_message;
            print LOG "Host discovery SNMP - $result_message\n";
            print LOG_MAIL "Host discovery SNMP - $result_message\n";
        } else {
            print LOG "Host discovery SNMP - OK\n\n";
            print LOG_MAIL "Host discovery SNMP - OK\n\n";
        }

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
print LOG_MAIL "\nExecution time: $duration_string\n";



close LOG;
close LOG_MAIL;

Gipfuncs::send_mail (
    debug       =>  "$debug",
    mail_from   =>  $mail_from,
    mail_to     =>  \@mail_to,
    subject     => "Result Job $job_name",
    smtp_server => "$smtp_server",
    smtp_message    => "",
    log         =>  "$log_mail_tmp",
    gip_job_status_id   =>  "$gip_job_status_id",
    changes_only   =>  "$changes_only",
) if $mail;

#unlink("$log_mail_tmp");

my $result_status_message = "Job successfully finished";
if ( $gip_job_id ) {
	# 1: scheduled, 2: running, 3: competed, 4: failed, 5: warning

	my $result_status;
    my $end_time=time();

	if ( $result_warning == 1 ) {
		$result_status = 5;
		$result_status_message = "Job finished with warning";
	} else {
		$result_status = 3;
	}

    update_job_status("$gip_job_status_id", "$result_status", "$end_time", "$result_status_message", "$logfile_name_log");
}


if ( -r "$base_dir/var/data/$network_file" ) {
    unlink "$base_dir/var/data/$network_file";
}


print "$result_status_message\n";
exit 0;


###### Subroutines

sub print_help {

    print "\nusage: discover_network.pl [OPTIONS...]\n\n";

    print "-c, --config_file_name=config_file_name  Name of the configuration file (without path)\n";
    print "-f, --force_site=Site    Force Site for the new discovered networks\n";
    print "-h, --help               help\n";
    print "-j                       Add the interface description/alias as description for new discovered networks (local routes only)\n";
    print "-k, --k=[Descr|Alias]    Specify if ifDescr or ifAlias should be used as description of new discovered networks (local routes only) (default: Alias)\n";
    print "-l, --log=logfile        Logfile\n";
    print "-n, --nodes_file=snmp_targets            File with a list of devices which should be queried to find new networks. Default: snmp_targets\n";
    print "-v, --verbose            Verbose\n";
    print "-w, --write_new_to_file=FILE             Write new found networks to FILE (without path)\n";
    print "-x, --x                  Debug\n\n";

    print "Options to overwrite values from the configuration file:\n";
	print "-A client\n";
	print "-B ignore_generic_auto ([yes|no])\n";
	print "-D snmp_version\n";
	print "-E snmp_community_string\n";
	print "-F snmp_user_name\n";
	print "-G sec_level\n";
	print "-H auth_proto\n";
	print "-I auth_pass\n";
	print "-J priv_proto\n";
	print "-K priv_pass\n";
	print "-M logdir\n";
	print "-T actualize_ipv4 ([yes|no]), Default: yes\n";
	print "-O actualize_ipv6 ([yes|no]), Default: no\n";
	print "-P generic_dyn_host_name\n";
	print "-Q ignorar\n";
	print "-S max_sinc_procs ([4|8|16|32|64|128|254])\n";
	print "-U Directory where the scripts are located (default: /usr/share/gestioip/bin\n";
    exit 1;
}

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
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
    $sth->execute() or exit_error("Can not execute statement: $DBI::errstr", "$gip_job_status_id", 4);

    $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or exit_error("Can not execute statement: $DBI::errstr", "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Can not execute statement: $DBI::errstr", "$gip_job_status_id", 4);
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
#    print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug;
    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
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


sub exit_error {
    my ( $message, $gip_job_status_id, $status ) = @_;

    if ( $delete_job_error ) {
        $gip_job_status_id = 5 if $gip_job_status_id == 3;
    }

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;

    if ( $gip_job_status_id ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

        my $time = time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close LOG if fileno LOG;

    exit 1;
}

sub get_db_parameter {
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or exit_error("Can not open $priv_file: $!","$gip_job_status_id","4");
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
#    if ( ! $sid_gestioip ) {
#        $sid_gestioip = $params{sid_gestioip};
#        $bbdd_host_gestioip = $params{bbdd_host_gestioip};
#        $bbdd_port_gestioip = $params{bbdd_port_gestioip};
#        $user_gestioip = $params{user_gestioip};
#        $pass_gestioip = $params{pass_gestioip};
#    }

    return ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip);
}


sub count_clients {
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT count(*) FROM clients
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub read_and_print_log {
    my ( $log_sub ) = @_;

    open(LOG_SUB,"<$log_sub") or print LOG "Can not open sub log $log_sub: $! - ";

    while (<LOG_SUB>) {
        print LOG_MAIL "$_";
    }    

    close LOG_SUB;
}

sub insert_audit_auto {
    my ($event_class,$event_type,$event,$update_type_audit,$client_id) = @_;

    my $remote_host = "N/A";

    $user=$ENV{'USER'} if ! $user;
    #my $user=getlogin();
    my $mydatetime=time();
    my $dbh = mysql_connection() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $qevent_class = $dbh->quote( $event_class );
    my $qevent_type = $dbh->quote( $event_type );
    my $qevent = $dbh->quote( $event );
    my $qupdate_type_audit = $dbh->quote( $update_type_audit );
    my $quser = $dbh->quote( $user );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qremote_host = $dbh->quote( $remote_host );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,remote_host,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qremote_host,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
}

sub get_client_id_from_name {
        my ( $client_name ) = @_;
        my $val;
        my $dbh = mysql_connection()  or die "Mysql ERROR: ". $DBI::errstr;
        my $qclient_name = $dbh->quote( $client_name );
        my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qclient_name");
        $sth->execute()  or die "Mysql ERROR: ". $DBI::errstr;
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

