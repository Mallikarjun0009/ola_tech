#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;
use Time::Local;
use POSIX qw(strftime);


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $bin_path = '/usr/share/gestioip/bin';

## check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_scheduled_jobs_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_job_message}","$vars_file");

my $client = $gip->get_client_from_id("$client_id");
$gip->print_error("1","$$lang_vars{formato_malo_message}") if ! $client;

my $user=$ENV{'REMOTE_USER'};

my $id=$daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $id !~ /^\d+$/;

my $job_hash = $gip->get_scheduled_job_hash("$client_id","name");

my $name=$daten{'name'} || "";
my $discovery_type=$daten{'discovery_type'} || "";
my $status=$daten{'status'} || "1";
my $start_date=$daten{'start_date'} || "";
my $end_date=$daten{'end_date'} || "";
my $run_once=$daten{'run_once'} || "0";
my $execution_time=$daten{'execution_time'} || "0";
my $comment=$daten{'comment'} || "";

my $interval=$daten{'interval'} || "";
my $interval_hours=$daten{'interval_hours'} || "0";
my $interval_minutes=$daten{'interval_minutes'} || "0";
my $interval_months=$daten{'interval_months'} || "";
my $interval_day_of_week=$daten{'interval_day_of_week'} || "";
my $interval_day_of_month=$daten{'interval_day_of_month'} || "";

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{name_no_whitespace_message}") if $name =~ /\s/;
foreach my $key ( keys %$job_hash ) {
	$gip->print_error("$client_id","$$lang_vars{job_name_exists_message}") if $job_hash->{$name} && $job_hash->{$name}[0] != $id;
}


my ($cron_time, $repeat_interval);
$cron_time=$repeat_interval="";
my $script_options = "";

if ( $run_once ) {
    $gip->print_error("$client_id","$$lang_vars{execution_time_message}: $$lang_vars{formatio_malo_message}") if $execution_time !~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;
    $execution_time =~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;
    my $exe_day = $1;
    my $exe_month = $2;
    my $exe_year = $3;
    my $exe_hour = $4;
    my $exe_minute = $5;
    my $exe_sec = "00";

    my $now_epoch = time();
    my $now_time = strftime "%d/%m/%Y %H:%M", localtime($now_epoch);

    my $exe_epoch = timelocal($exe_sec,$exe_minute,$exe_hour,$exe_day,$exe_month-1,$exe_year);
    if ( $exe_epoch <= $now_epoch ) {
        $gip->print_error("$client_id","$$lang_vars{execution_time_to_small_message} - $$lang_vars{execution_time_message}: $execution_time, $$lang_vars{now_message}: $now_time") ;
    }

    $cron_time =  "$exe_minute $exe_hour $exe_day $exe_month *";

    $start_date = $execution_time;

    $script_options .= " --run_once";

} else {

    $gip->print_error("$client_id","$$lang_vars{start_date_job_message}: $$lang_vars{formatio_malo_message}") if $start_date !~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;


    if (  $interval == 1 && ($interval_minutes !~ /^(\d|,|$$lang_vars{all_message})+/ || $interval_hours !~ /^(\d|,|$$lang_vars{all_message})+/)) {
        $gip->print_error("$client_id","$$lang_vars{check_execution_interval_message} 1");
    }
    if ( $interval == 2 && ($interval_minutes !~ /^(\d|,|$$lang_vars{all_message})+/ || $interval_hours !~ /^(\d|,|$$lang_vars{all_message})+/ || ! $interval_day_of_week)) {
        $gip->print_error("$client_id","$$lang_vars{check_execution_interval_message} 2");
    }
    if ( $interval == 3 && ($interval_minutes !~ /^(\d|,|$$lang_vars{all_message})+/ || $interval_hours !~ /^(\d|,|$$lang_vars{all_message})+/ || ! $interval_day_of_month || ! $interval_months)) {
        $gip->print_error("$client_id","$$lang_vars{check_execution_interval_message} 3");
    }

    ($cron_time, $repeat_interval) = $gip->get_cron_time (
        vars_file => $vars_file,
        client_id => $client_id,
        interval => $interval,
        interval_hours => $interval_hours,
        interval_minutes => $interval_minutes,
        interval_months => $interval_months,
        interval_day_of_month => $interval_day_of_month,
        interval_day_of_week => $interval_day_of_week,
    );
}

$start_date =~ /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})/;
my $mday = $1;
my $mon = $2;
my $year = $3;
my $hour = $4;
my $min = $5;
my $sec = 0;
if ( ! $mday || ! $mon || ! $year || ! $hour || ! $min ) {
    $gip->print_error("$client_id","$$lang_vars{check_start_date_message}");
}
my $start_date_epoch;
eval {
    $start_date_epoch = timelocal($sec,$min,$hour,$mday,$mon-1,$year);
} or do {
    $gip->print_error("$client_id","$$lang_vars{start_date_format_error_message}");
};

#if ( ! $run_once ) {
#    $script_options .= " --start_date=\"$start_date\"";
#}

if ( $end_date ) {
    $gip->print_error("$client_id","$$lang_vars{end_date_job_message}: $$lang_vars{formatio_malo_message}") if $end_date !~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;

    $end_date =~ /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})/;
    my $e_mday = $1;
    my $e_mon = $2;
    my $e_year = $3;
    my $e_hour = $4;
    my $e_min = $5;
    my $e_sec = 0;
    my $end_date_epoch = "";
    if ( $e_mday || $e_mon || $e_year || $e_hour ||  $e_min ) {
        eval {
            $end_date_epoch = timelocal($e_sec,$e_min,$e_hour,$e_mday,$e_mon-1,$e_year);
        } or do {
            $gip->print_error("$client_id","$$lang_vars{end_date_format_error_message}");
        };
    }

    if ( $end_date_epoch <= $start_date_epoch ) {
        $gip->print_error("$client_id","$$lang_vars{end_date_start_date_error_message}");
    }

#    $script_options .= " --end_date=\"$end_date\"";
}


# Job specific parameters
# global_discovery 1, network_discovery 2, host dns 3, host snmp 4, vlan 5

### FORM ELEMENTS ALL

my $verbose=$daten{'verbose'} || "";
my $debug=$daten{'debug'} || "";
my $send_result_by_mail=$daten{'send_result_by_mail'} || "";
my $send_changes_only=$daten{'send_changes_only'} || "";
my $mail_from=$daten{'mail_from'} || "";
my $mail_recipients=$daten{'mail_recipients'} || "";
my $smtp_server=$daten{'smtp_server'} || "";
my $only_added_mail=$daten{'only_added_mail'} || "";

my $email_username = qr/[a-z0-9_+]([a-z0-9_+.]*[a-z0-9_+])?/;
my $email_domain = qr/[a-z0-9.-]+/;

$script_options .= " --A=\"$client\"";
if ( $verbose ) {
    $script_options .= " --verbose";
}
if ( $debug ) {
	# fecht_config needs --debug option
	$script_options .= " --x" if $discovery_type != 11;
}
if ( $send_result_by_mail ) {
    $script_options .= " --mail";
}
if ( $send_result_by_mail && ! $mail_recipients ) {
    $gip->print_error("$client_id","$$lang_vars{introduce_mail_to_message}");
} elsif ( $send_result_by_mail && ! $smtp_server ) {
    $gip->print_error("$client_id","$$lang_vars{introduce_smtp_server_message}");
} elsif ( $send_result_by_mail && ! $mail_from ) {
    $gip->print_error("$client_id","$$lang_vars{introduce_mail_from_message}");
}
if ( $send_changes_only ) {
    $script_options .= " --changes_only";
}
if ( $mail_from ) {
    if ( $mail_from !~ /^$email_username\@$email_domain$/ ) {;
        $gip->print_error("$client_id","$$lang_vars{mail_from_message}: $$lang_vars{formato_malo_message}");
    }
    $script_options .= " --mail_from=\"$mail_from\"";
}
if ( $mail_recipients ) {
    my @mail_recipients = split(",", $mail_recipients);
    foreach ( @mail_recipients ) {
        if ( $_ !~ /^$email_username\@$email_domain$/ ) {;
            $gip->print_error("$client_id","$$lang_vars{mail_recipients_message}: $$lang_vars{formato_malo_message}");
        }
    }
    $script_options .= " --mail_to=\"$mail_recipients\"";
}
if ( $smtp_server ) {
    my %smtp_server_hash = $gip->get_smtp_server_hash("$client_id","id");
    my $smtp_server_name = $smtp_server_hash{"$smtp_server"}[0];
    $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $smtp_server_name;
    $script_options .= " --smtp_server=\"$smtp_server_name\"";
}


### global_discovery, get_networks_snmp, import_vlans, ip_update_gestioip_snmp
my $snmp_group=$daten{'snmp_group'} || "";
if ( $snmp_group ) {
	my $snmp_group_check = $gip->get_snmp_group_id_from_name("$client_id","$snmp_group");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $snmp_group_check;
    $script_options .= " --snmp_group=\"$snmp_group\"";
}


###### GLOBAL DISCOVERY

#my $execute_network_discovery=$daten{'execute_network_discovery'} || "";
my $execute_vlan_discovery=$daten{'use_vlan_discovery'} || "";
my $execute_host_discovery_dns=$daten{'use_host_discovery_dns'} || "";
my $execute_host_discovery_snmp=$daten{'use_host_discovery_snmp'} || "";

my $script;
if ( $discovery_type == 1 ) {
    $script = "discover_network.pl";
    if ( $execute_vlan_discovery ) {
        $script_options .= " --execute_vlan_discovery";
    }
    if ( $execute_host_discovery_dns ) {
        $script_options .= " --execute_host_discovery_dns";
    }
    if ( $execute_host_discovery_snmp ) {
        $script_options .= " --execute_host_discovery_snmp";
    }
} elsif ( $discovery_type == 2 ) {
    $script = "get_networks_snmp.pl";
} elsif ( $discovery_type == 3 ) {
    $script = "ip_update_gestioip_dns.pl";
} elsif ( $discovery_type == 4 ) {
    $script = "ip_update_gestioip_snmp.pl";
} elsif ( $discovery_type == 5 ) {
    $script = "import_vlans_snmp.pl";
} elsif ( $discovery_type == 6 ) {
    $script = "gip_lease_sync.pl";
} elsif ( $discovery_type == 7 ) {
    $script = "backup_gip.pl";

}
$script = $bin_path . "/" . $script;


###### NETWORK DISCOVERY - get_networks_snmp.pl

my ($CSV_nodes, $node_list, $use_tags, $nodes, @nodes);

my $nodes_type=$daten{'nodes_type'} || "";

my $loc=$daten{'loc'} || "";
my $assign_tags=$daten{'assign_tags'} || "";
my $get_vrf_routes=$daten{'get_vrf_routes'} || "";
my $delete_not_found_networks=$daten{'delete_not_found_networks'} || "";
my $import_host_routes=$daten{'import_host_routes'} || "";
my $add_if_descr=$daten{'add_if_descr'} || "";
my $interface_descr_ident=$daten{'interface_descr_ident'} || "";
my $report_not_found_networks=$daten{'report_not_found_networks'} || "";
my $set_sync_flag=$daten{'set_sync_flag'} || "";
my $write_to_file=$daten{'write_to_file'} || "";
my $actualize_ipv4 = $daten{'actualize_ipv4'} || "";
my $actualize_ipv6 = $daten{'actualize_ipv6'} || "";
my $process_networks_v4 = $daten{'process_networks_v4'} || "";
my $process_networks_v6 = $daten{'process_networks_v6'} || "";

$interface_descr_ident = "" if ! $add_if_descr;

if ( $discovery_type == 1 || $discovery_type == 2 || $discovery_type == 5 ) {

    $gip->print_error("$client_id","$$lang_vars{choose_snmp_group_message}") if ! $snmp_group;

    if ( $nodes_type eq "nodes_list") {
        $nodes=$daten{'CSV_nodes'} || "";
        $gip->print_error("$client_id","$$lang_vars{introduce_nodes_list_message}") if ! $nodes;
        $nodes =~ s/\s//g;
        @nodes = split(",", $nodes);

        foreach my $ip ( @nodes ) {
            my $valid_ip;
            if ( $ip =~ /:/ ) {
                $valid_ip = $gip->check_valid_ipv6("$ip") || "0";
            } else {
                $valid_ip = $gip->check_valid_ipv4("$ip") || "0";
            }
            $gip->print_error("$client_id","$$lang_vars{ip_invalido_message}: $ip") if $valid_ip != 1;
        }

        $script_options .= " --CSV_nodes=\"$nodes\"";

    } elsif ( $nodes_type eq "nodes_file" ) {
        $nodes=$daten{'nodes_file'} || "";
        $gip->print_error("$client_id","$$lang_vars{introduce_nodes_file_message}") if ! $nodes;
        $gip->print_error("$client_id","$$lang_vars{nodes_file_message}: $$lang_vars{only_letters_and_numbers_message} $nodes") if $nodes !~ /^[A-Za-z0-9-_]+$/;

        my $file = "/usr/share/gestioip/etc/${nodes}";
        if ( ! -r $file ) {
            $gip->print_error("$client_id","$$lang_vars{file_not_readable}: $file ");
        }

        $script_options .= " --nodes_file=\"$nodes\"";

    } elsif ( $nodes_type eq "use_tags" ) {
        my %tags = $gip->get_tag_hash("$client_id","id");
        $use_tags=$daten{'use_tags'} || "";
        $gip->print_error("$client_id","$$lang_vars{select_tag_message}") if ! $use_tags;
        $use_tags =~ s/\s//g;
        my $tags;
        my @tags = split("_", $use_tags);
        foreach (@tags) {
			$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $tags{$_};
            $tags .= $tags{$_}[0] . ",";
        }
        $tags =~ s/,$//;
        $use_tags = $tags;

        $script_options .= " --tag=\"$tags\"";
    } else {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)");
    }


	$gip->print_error("$client_id","$$lang_vars{choose_nodes_job_message}") if ! $nodes && ! $use_tags;

    if ( $discovery_type == 1 || $discovery_type == 2 ) {
        $gip->print_error("$client_id","$$lang_vars{choose_ip_version_message}") if ! $actualize_ipv4 && ! $actualize_ipv6;

        $actualize_ipv4 = "yes" if $actualize_ipv4;
        $script_options .= " --T=\"$actualize_ipv4\"" if $actualize_ipv4;

        $actualize_ipv6 = "yes" if $actualize_ipv6;
        $script_options .= " --O=\"$actualize_ipv6\"" if $actualize_ipv6;

        $script_options .= " --process_networks_v4=\"$process_networks_v4\"" if $process_networks_v4;
        $script_options .= " --process_networks_v6=\"$process_networks_v6\"" if $process_networks_v6;
    }

    if ( $loc ) {
        my $loc_id_check = $gip->get_loc_id("$client_id","$loc");
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $loc_id_check;
        $script_options .= " --force_site=\"$loc\"";
    }
	if ( $assign_tags ) {
        my %tags = $gip->get_tag_hash("$client_id","id");
        $assign_tags =~ s/\s//g;
        my $tags;
        my @tags = split("_", $assign_tags);
        foreach (@tags) {
			$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $tags{$_};
            $tags .= $tags{$_}[0] . ",";
        }
        $tags =~ s/,$//;
        $assign_tags = $tags;
        $script_options .= " --assign_tags=\"$assign_tags\"";
    }
    if ( $delete_not_found_networks ) {
        $script_options .= " --delete_not_found_networks";
    }
    if ( $get_vrf_routes ) {
        $script_options .= " --get_vrf_routes";
    }
    if ( $import_host_routes ) {
        $script_options .= " --import_host_routes";
    }
    if ( $add_if_descr ) {
        $script_options .= " --j";
    }
    if ( $interface_descr_ident ) {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}: interface description identifier") if $interface_descr_ident !~ /^(Descr|Alias)$/;
        $script_options .= " --k=\"$interface_descr_ident\"";
    }
    if ( $only_added_mail ) {
        $script_options .= " --only_added_mail";
    }
    if ( $delete_not_found_networks ) {
        $script_options .= " --delete_not_found_networks";
    }
    if ( $report_not_found_networks ) {
        $script_options .= " --report_not_found_networks";
    }
    if ( $set_sync_flag ) {
        $script_options .= " --Set_sync_flag";
    }
    if ( $write_to_file ) {
        $gip->print_error("$client_id","$$lang_vars{check_file_name_message}") if $write_to_file !~ /[a-z,A-Z,0-9]/;
        $script_options .= " --write_new_to_file=\"$write_to_file\"";
    }
}


### get_networks_snmp, import_vlans, ip_update_gestioip_snmp


# COMMON OPTIONS HOST DNS AND SNMP AND VLAN

my $network_type=$daten{'network_type'} || "";

my ($CSV_networks, $networks_file, $use_range, $networks, $location_scan, @networks);

if ( $discovery_type == 3 || $discovery_type == 4 ) {
    if ( $network_type eq "network_list" ) {
        $networks=$daten{'CSV_networks'} || "";
        $gip->print_error("$client_id","$$lang_vars{introduce_network_list_message}") if ! $networks;
        $networks =~ s/\s//g;
        @networks = split(",", $networks);
        foreach my $ip ( @networks ) {
            my $valid_ip;
            $ip =~ /\/(.*)/;
            my $mask = $1;
            $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if  $mask !~ /^\d{1,3}$/;
            $ip =~ s/\/.*//;
            if ( $ip =~ /:/ ) {
                $valid_ip = $gip->check_valid_ipv6("$ip") || "0";
            } else {
                $valid_ip = $gip->check_valid_ipv4("$ip") || "0";
            }
            $gip->print_error("$client_id","$$lang_vars{ip_invalido_message}: $ip") if $valid_ip != 1;
        }

        $script_options .= " --CSV_networks=\"$networks\"";
    } elsif ( $network_type eq "networks_file" ) {
        $networks=$daten{'networks_file'} || "";
        $gip->print_error("$client_id","$$lang_vars{introduce_network_file_message}") if ! $networks;

        my $file = "/usr/share/gestioip/etc/${networks}";
        if ( ! -r $file ) {
            $gip->print_error("$client_id","$$lang_vars{file_not_readable}: $file ");
        }

        $script_options .= " --Network_file=\"$networks\"";
    } elsif ( $network_type eq "use_tags" ) {
        my %tags = $gip->get_tag_hash("$client_id","id");
        $use_tags=$daten{'use_tags'} || "";
        $gip->print_error("$client_id","$$lang_vars{select_tag_message}") if ! $use_tags;
        $use_tags =~ s/\s//g;
        my $tags;
        my @tags = split("_", $use_tags);
        foreach (@tags) {
			$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $tags{$_};
            $tags .= $tags{$_}[0] . ",";
        }
        $tags =~ s/,$//;
        $use_tags = $tags;

        $script_options .= " --tag=\"$use_tags\"";

    } elsif ( $network_type eq "use_range" ) {
        $use_range=$daten{'use_range'} || "";
        $use_range =~ s/\s//g;
        $use_range =~ /^(.+)-(.+)$/;
        my $ip1 = $1;
        my $ip2 = $2;
        my ($valid_ip1, $valid_ip2);
        if ( $ip1 =~ /:/) {
            $valid_ip1 = $gip->check_valid_ipv6("$ip1") || "0";
            $valid_ip2 = $gip->check_valid_ipv6("$ip2") || "0";
        } else {
            $valid_ip1 = $gip->check_valid_ipv4("$ip1") || "0";
            $valid_ip2 = $gip->check_valid_ipv4("$ip2") || "0";
        }
        $gip->print_error("$client_id","$$lang_vars{ip_invalido_message}: $ip1") if $valid_ip1 != 1;
        $gip->print_error("$client_id","$$lang_vars{ip_invalido_message}: $ip2") if $valid_ip2 != 1;

        $script_options .= " --range=\"$use_range\"";
    } elsif ( $network_type eq "location_scan" ) {
        $location_scan=$daten{'location_scan'} || "";
        my $scan_locs;
        my @scan_loc_ids = split("_", $location_scan);
        my $scan_loc_string = "";
        foreach ( @scan_loc_ids ) {
            my $scan_loc_name = $gip->get_loc_from_id("$client_id", "$_") || "";
            $scan_loc_string .= "," . $scan_loc_name if $scan_loc_name;
        }
        $scan_loc_string =~ s/^,//;

        $script_options .= " --Location_scan=\"$scan_loc_string\"";

    } else {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)");
    }

    $gip->print_error("$client_id","$$lang_vars{choose_ip_version_message}") if ! $actualize_ipv4 && ! $actualize_ipv6;

    $actualize_ipv4 = "yes" if $actualize_ipv4;
    $script_options .= " --T=\"$actualize_ipv4\"" if $actualize_ipv4;

    $actualize_ipv6 = "yes" if $actualize_ipv6;
    $script_options .= " --O=\"$actualize_ipv6\"" if $actualize_ipv6;
}


# COMMON OPTIONS HOST DNS AND SNMP

my ( $process_only_location, $max_sync_procs );

$process_only_location = $daten{'process_only_location'} || "";
if ( $process_only_location ) {
	my $loc_id_check = $gip->get_loc_id("$client_id","$process_only_location");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $loc_id_check;
    $script_options .= " --Location=\"$process_only_location\"";
}

$max_sync_procs = $daten{'max_sync_procs'} || "";
if ( $max_sync_procs ) {
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $max_sync_procs !~ /^\d+$/;
    $script_options .= " --S=\"$max_sync_procs\"";
}


###### HOST DISCOVERY DNS - ip_update_gestioip_dns.pl

my ( $delete_down_hosts, $ignore_generic_auto, $ignorar, $use_zone_transfer, $generic_dyn_name, $ignore_dns);

$ignore_dns = $daten{'ignore_dns'} || "";
if ( $ignore_dns ) {
    $script_options .= " --ignore_dns";
}

$delete_down_hosts = $daten{'delete_down_hosts'} || "";
if ( $delete_down_hosts ) {
    $script_options .= " --delete_down_hosts";
}

$ignore_generic_auto = $daten{'ignore_generic_auto'} || "";
if ( $ignore_generic_auto ) {
    $ignore_generic_auto = "yes" if $ignore_generic_auto;
    $script_options .= " --B=\"$ignore_generic_auto\"";
}

$ignorar = $daten{'ignorar'} || "";
if ( $ignorar ) {
    $gip->print_error("$client_id","$$lang_vars{ignorar_manage_message}: $$lang_vars{only_letters_and_numbers_message},-,_") if $ignorar !~ /^[A-Za-z0-9-_]+$/;
    $script_options .= " --Q=\"$ignorar\"";
}

$generic_dyn_name = $daten{'generic_dyn_host_name'} || "";
if ( $generic_dyn_name ) {
    $gip->print_error("$client_id","$$lang_vars{generic_dyn_manage_message}: $$lang_vars{only_letters_and_numbers_message},-,_") if $generic_dyn_name !~ /^[A-Za-z0-9-_]+$/;
    $script_options .= " --P=\"$generic_dyn_name\"";
}

$use_zone_transfer = $daten{'zone_transfer'} || "";
if ( $use_zone_transfer ) {
    $script_options .= " --Z";
}

#check required options
if ( $discovery_type == 3 || $discovery_type == 4 ) {
	$gip->print_error("$client_id","$$lang_vars{choose_networks_job_message}") if ! $networks && ! $use_tags && ! $use_range;
	$gip->print_error("$client_id","$$lang_vars{choose_ip_version_message}") if ! $actualize_ipv4 && ! $actualize_ipv6;
}


###### HOST DISCOVERY SNMP - ip_update_gestioip_snmp.pl
my $ignore_arp_cache;

if ( $discovery_type == 4 ) {
	$gip->print_error("$client_id","$$lang_vars{choose_snmp_group_message}") if ! $snmp_group;
}

$ignore_arp_cache = $daten{'ignore_arp_cache'} || "";
if ( $ignore_arp_cache ) {
    $script_options .= " --ignore_arp_cache";
}


###### VLAN DISCOVERY - ip_import_vlans.pl
if ( $discovery_type == 5 ) {
	$gip->print_error("$client_id","$$lang_vars{choose_snmp_group_message}") if ! $snmp_group;
}


##### REQIRED OPTIONS ALL

$script_options .= " --user=\"$user\"";
$script_options .= " --W=\"$id\"";

my $next_run = $gip->get_next_run("$cron_time") || "";
$gip->print_error("$client_id","$$lang_vars{can_not_determine_next_exe_time_message}") if ! $next_run || $next_run =~ /1970/;


#### OPTIONS LEASES

if ( $discovery_type == 6 ) {
    my $leases_type=$daten{'leases_type'} || "";
    my $leases_file=$daten{'leases_file'} || "";
    my $leases_file_old=$daten{'leases_file_old'} || "";
    my $kea_url=$daten{'kea_url'} || "";
    my $kea_api_ip_version=$daten{'kea_api_ip_version'} || "";
    my $kea_basic_auth=$daten{'kea_basic_auth'} || "";

    my %tags = $gip->get_tag_hash("$client_id","id");
    my $leases_tag=$daten{'leases_tag'} || "";
	if ( $leases_tag ) {
		$leases_tag =~ s/\s//g;
        my $tags;
        my @tags = split("_", $leases_tag);
        foreach (@tags) {
            $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $tags{$_};
            $tags .= $tags{$_}[0] . ",";
        }
        $tags =~ s/,$//;
        $leases_tag = $tags;
    }

    $gip->print_error("$client_id","$$lang_vars{leases_file_no_whitespace_message}") if $leases_file =~ /\s/;

    if ( $leases_type eq $$lang_vars{kea_api_message}) {
        $script_options .= " --type=\"kea_api\"";
		if ( $kea_api_ip_version eq "ipv4" ) {
            $script_options .= " --ipv4";
        } elsif ( $kea_api_ip_version eq "ipv6" ) {
            $script_options .= " --ipv6";
        } else {
            $script_options .= " --ipv4";
        }
        $script_options .= " --kea_url=\"$kea_url\"";
        $script_options .= " --kea_basic_auth" if $kea_basic_auth;
    } elsif ( $leases_type eq $$lang_vars{kea_leases_file_message}) {
        $script_options .= " --type=\"kea_lease_file\"";
        $script_options .= " --leases_file=\"$leases_file\"";
    } elsif ( $leases_type eq $$lang_vars{dhcpd_leases_file_message}) {
        $script_options .= " --type=\"dhcpd_lease_file\"";
        $script_options .= " --leases_file=\"$leases_file\"";
    } elsif ( $leases_type eq $$lang_vars{ms_csv_leases_file_message}) {
        $script_options .= " --type=\"ms_lease_file\"";
        $script_options .= " --leases_file=\"$leases_file\"";
    } elsif ( $leases_type eq $$lang_vars{generic_csv_leases_file_message}) {
        $script_options .= " --type=\"generic_lease_file\"";
        $script_options .= " --leases_file=\"$leases_file\"";
    }
    $script_options .= " --leases_file_old=\"$leases_file_old\"" if $leases_file_old;
	$script_options .= " --tag=\"$leases_tag\"" if $leases_tag;
}


### OPTIONS CLOUD AWS

if ( $discovery_type == 8 ) {
    my $aws_dns=$daten{'aws_dns'} || "";
    my $aws_region=$daten{'aws_region'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_region_message}") if ! $aws_region;
    my $aws_access_key_id=$daten{'aws_access_key_id'} || "";
    $gip->print_error("$client_id","$$lang_vars{aws_access_key_id_message}") if ! $aws_access_key_id;
    my $aws_secret_access_key=$daten{'aws_secret_access_key'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_aws_secret_access_key_message}") if ! $aws_secret_access_key;

    $script_options .= " --type=\"aws\"";
    $script_options .= " --aws_dns" if $aws_dns;
    $script_options .= " --aws_region=\"$aws_region\"" if $aws_region;
    $script_options .= " --aws_access_key_id=\"$aws_access_key_id\"" if $aws_access_key_id;
    $script_options .= " --aws_secret_access_key=\"$aws_secret_access_key\"" if $aws_secret_access_key;
}


### OPTIONS CLOUD AZURE

if ( $discovery_type == 9 ) {
    my $azure_dns=$daten{'azure_dns'} || "";
    my $azure_resource_group=$daten{'azure_resource_group'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_azure_resource_group_message}") if $azure_dns && ! $azure_resource_group;
    my $azure_tenant_id=$daten{'azure_tenant_id'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_azure_tenant_id_message}") if ! $azure_tenant_id;
    my $azure_app_id=$daten{'azure_app_id'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_azure_app_id_message}") if ! $azure_app_id;

    my $azure_cert_file_radio=$daten{'azure_cert_file_radio'} || "";
    my $azure_cert_file = "";
    my $azure_secret_key_value = "";
    if ( $azure_cert_file_radio eq "cert" ) {
        $azure_cert_file=$daten{'azure_cert_file'} || "";
        $gip->print_error("$client_id","$$lang_vars{missing_azure_cert_file_message}") if ! $azure_cert_file;
    } elsif ( $azure_cert_file_radio eq "secret" ) {
        $azure_secret_key_value=$daten{'azure_secret_key_value'} || "";
        $gip->print_error("$client_id","$$lang_vars{missing_azure_secret_key_value_message}") if ! $azure_secret_key_value;
    } else {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
    }
    
    $script_options .= " --type=\"azure\"";
    $script_options .= " --azure_dns" if $azure_dns;
    $script_options .= " --azure_resource_group=\"$azure_resource_group\"" if $azure_resource_group;
    $script_options .= " --azure_tenant_id=\"$azure_tenant_id\"" if $azure_tenant_id;
    $script_options .= " --azure_app_id=\"$azure_app_id\"" if $azure_app_id;
    $script_options .= " --azure_cert_file=\"$azure_cert_file\"" if $azure_cert_file;
    $script_options .= " --azure_secret_key_value=\"$azure_secret_key_value\"" if $azure_secret_key_value;
}


### OPTIONS CLOUD GOOGLE GCP

if ( $discovery_type == 10 ) {
    my $gcp_dns=$daten{'gcp_dns'} || "";
    my $gcp_project=$daten{'gcp_project'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_gcp_projet_message}") if ! $gcp_project;
    my $gcp_zone=$daten{'gcp_zone'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_gcp_zone_message}") if ! $gcp_zone;
    my $gcp_key_file=$daten{'gcp_key_file'} || "";
    $gip->print_error("$client_id","$$lang_vars{missing_gcp_key_file_message}") if ! $gcp_key_file;

    $script_options .= " --type=\"gcp\"";
    $script_options .= " --gcp_dns" if $gcp_dns;
    $script_options .= " --gcp_project=\"$gcp_project\"" if $gcp_project;
    $script_options .= " --gcp_zone=\"$gcp_zone\"" if $gcp_zone;
    $script_options .= " --gcp_key_file=\"$gcp_key_file\"" if $gcp_key_file;
}


#### OPTIONS CMM JOBS

if ( $discovery_type == 11 ) {
    my $cmm_job_group_id=$daten{'cmm_job_group_id'} || "";
    $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1) $cmm_job_group_id") if $cmm_job_group_id !~ /^\d{1,6}$/;
    $script_options .= " --group_id=\"$cmm_job_group_id\"";
#    $script_options .= " --audit_user=\"$user\"";
    $script_options .= " --debug=\"2\"" if $debug;
}


# Update crontab entry

$gip->mod_scheduled_job(
    client_id=>"$client_id",
    id=>"$id",
    name=>"$name",
    type=>"$discovery_type",
    status=>"$status",
    start_date=>"$start_date",
    end_date=>"$end_date",
    run_once=>"$run_once",
    comment=>"$comment",
    arguments=>"$script_options",
    cron_time=>"$cron_time",
    next_run=>"$next_run",
    repeat_interval=>"$repeat_interval",
);
 

my $cron_entry;
if ( $debug ) {
    $cron_entry = $cron_time . " " . $script . " " . $script_options . " >/tmp/"  . $name . "_out.txt 2>&1 #ID: " . $id;
} else {
    $cron_entry = $cron_time . " " . $script . " " . $script_options . " >/dev/null 2>&1 #ID: " . $id;
}
my $cron_entry_old = $gip->get_cron_entry("$id");

my $error;
if ( $cron_entry ne $cron_entry_old ) {
    $error = $gip->mod_cron_entry("$cron_entry", "$id");
}

if ( $error ) {
    if ( $error =~ /because of pam configuration/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_prevent_job_mod_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } else {
		$gip->print_error("$client_id","$$lang_vars{error_update_cron_entry_message}: $id<p>$error");
    }
}


my $audit_type="174";
my $audit_class="33";
my $update_type_audit="1";
my $event="$name";
$event=$event . "," .  $comment if $comment;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print <<EOF;
<script>
update_nav_text("$$lang_vars{job_updated_message}");
</script>
EOF

$gip->PrintJobTab("$client_id", "$vars_file", "$id");

$gip->print_end("$client_id","$vars_file","", "$daten");

