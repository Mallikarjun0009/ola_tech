#!/usr/bin/perl -w

# Script for importing networks from the routing tables via SNMP
# into the database of GestioIP.

# you have to configure some parameters directly in this script.
# See documentation for more information

# Copyright (C) 2017 Marc Uebel

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

# VERSION 3.5.7.1 20210818
# not compatible with versions <= 3.5.3

use strict;
use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
    $dir = $Bin;
    $gipfunc_path = $dir . '/include';
}

use lib "$gipfunc_path";
use Gipfuncs;
use SNMP;
use SNMP::Info;
use Net::IP;
use Net::IP qw(:PROC);
use DBI;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");

$dir =~ /^(.*)\/bin/;
$base_dir=$1;


#########################################
### change from here... #################
#########################################

# Configure here the smallest allowed bitmask/prefix length.
# Networks with smaller BM/Prefix length will not be imported

## Process only IPv4 networks starting with...
# coma separated list
# An empty list means that all found networks will be processed
# Default: ""
# e.g. a value of "192.168,172.16." causes that all networks 192.168.x.y and 172.16.y.z will 
# be imported; all other networks will be ignored

# Process only IPv6 networks starting with...
# coma separated list
# Strings to match IPv6 networks must be introduced in uncompressed format
# An empty list means that all found networks will be processed
# Default: ""
# e.g. a value of "2001:" causes that only networks starting with "2001:" will be imported
# be imported; all other networks will be ignored


#########################################
#### ...to here #########################
#########################################


my $VERSION="3.5.3.1";


my ( $help, $import_host_routes, $report_not_found_networks, $get_vrf_routes, $ascend, $descend, $add_if_descr, $interfaces_descr_indent, $delete_not_found_networks  );
my $config_name="";
my $nodes_file="";
my $set_sync_flag=0;
my $force_site="";
my $write_new_to_file="";
my $new_networks_file="";
my $only_added_mail=0;
my $gip_job_id = "";
my $snmp_group_arg = "";
my $run_once = "";
my $smallest_bm4=16;
my $smallest_bm6=64;
my $process_networks_v4="";
my $process_networks_v6="";

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

my ( $snmp_version_arg, $community_arg, $snmp_user_name_arg, $sec_level_arg, $auth_proto_arg, $auth_pass_arg, $priv_proto_arg, $priv_pass_arg, $logdir, $actualize_ipv4, $actualize_ipv6, $tag, $add_comment, $route_types_import, $snmp_port_arg, $nodes_list, $user, $combined_job, $assign_tags, $start_date, $end_date);
$snmp_version_arg=$community_arg=$snmp_user_name_arg=$sec_level_arg=$auth_proto_arg=$auth_pass_arg=$priv_proto_arg=$priv_pass_arg=$logdir=$actualize_ipv4=$actualize_ipv6=$tag=$add_comment=$nodes_list=$user=$combined_job=$assign_tags=$start_date=$end_date=$delete_not_found_networks="";

GetOptions(
        "ascend!"=>\$ascend,
        "assign_tags=s"=>\$assign_tags,
        "config_file_name=s"=>\$config_name,
        "changes_only!"=>\$changes_only,
        "combined_job!"=>\$combined_job,
        "CSV_nodes=s"=>\$nodes_list,
        "descend!"=>\$descend,
        "delete_not_found_networks!"=>\$delete_not_found_networks,
        "document_root=s"=>\$document_root,
        "force_site=s"=>\$force_site,
        "get_vrf_routes!"=>\$get_vrf_routes,
        "help!"=>\$help,
        "import_host_routes!"=>\$import_host_routes,
        "j!"=>\$add_if_descr,
        "k=s"=>\$interfaces_descr_indent,
        "log=s"=>\$log,
        "mail!"=>\$mail,
        "nodes_file=s"=>\$nodes_file,
        "only_added_mail!"=>\$only_added_mail,
        "process_networks_v4=s"=>\$process_networks_v4,
        "process_networks_v6=s"=>\$process_networks_v6,
        "report_not_found_networks!"=>\$report_not_found_networks,
        "run_once!"=>\$run_once,
        "Set_sync_flag!"=>\$set_sync_flag,
        "smallest_bm4=s"=>\$smallest_bm4,
        "smallest_bm6=s"=>\$smallest_bm6,
		"snmp_port=s"=>\$snmp_port_arg,
        "snmp_group=s"=>\$snmp_group_arg,

        "smtp_server=s"=>\$smtp_server,
        "mail_from=s"=>\$mail_from,
        "mail_to=s"=>\$mail_to,

        "tag=s"=>\$tag,
        "user=s"=>\$user,
        "verbose!"=>\$verbose,
        "write_new_to_file=s"=>\$new_networks_file,
        "x!"=>\$debug,
        "y=s"=>\$route_types_import,

		"A=s"=>\$client,
        "B=s"=>\$ignore_generic_auto,
        "D=s"=>\$snmp_version_arg,
        "E=s"=>\$community_arg,
        "F=s"=>\$snmp_user_name_arg,
        "G=s"=>\$sec_level_arg,
        "H=s"=>\$auth_proto_arg,
        "I=s"=>\$auth_pass_arg,
        "J=s"=>\$priv_proto_arg,
        "K=s"=>\$priv_pass_arg,
        "M=s"=>\$logdir,
        "O=s"=>\$actualize_ipv6,
		"T=s"=>\$actualize_ipv4,
        "U!"=>\$add_comment,
        "W=s"=>\$gip_job_id,
) or print_help();

$smallest_bm4=16 if ! $smallest_bm4;
$smallest_bm6=64 if ! $smallest_bm6;

print_help() if $help;

my $start_time=time();

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

my $job_name = "";
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
        $job_name = Gipfuncs::get_job_name("$gip_job_id");
        my $audit_type="176";
        my $audit_class="33";
        my $update_type_audit="2";

        my $event="$job_name ($gip_job_id)";
        insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");
    }
}



my $exit_message = "";

$mail=1 if $only_added_mail;
$verbose = 1 if $debug;
$debug = 1 if $debug;

my $datetime;
my $gip_job_status_id = "2";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "get_networks_snmp"); 

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or exit_error("Can not open $log: $!", "$gip_job_status_id", 4);
*STDERR = *LOG;

my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime get_networks_snmp.pl $VERSION $gip_job_id_message\n\n";

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
$set_sync_flag=1 if $set_sync_flag;

my $ipv4 = $actualize_ipv4 || "yes";
if ( $ipv4 && $ipv4 !~ /^yes|no/i ) {
    $exit_message = "actualize_ipv4 (-T) must be \"yes\" or \"no\"";
	if ( $gip_job_status_id ) {
		exit_error("$exit_message", "$gip_job_status_id", 4 );
	} else {
		print_help("$exit_message");
	}
}

my $ipv6 = $actualize_ipv6 || "no";
if ( $ipv6 && $ipv6 !~ /^yes|no/i ) {
    $exit_message = "actualize_ipv4 (-O) must be \"yes\" or \"no\"";
	if ( $gip_job_status_id ) {
		exit_error("$exit_message", "$gip_job_status_id", 4);
	} else {
		print_help("$exit_message");
	}
}
$ipv6="no" if $ipv6 !~ /^yes$/i;

if ( $add_comment ) {
    $add_comment = 1;
} else {
    $add_comment = 0;
}


my ($local_routes, $static_routes, $other_routes, $ospf_routes, $rip_routes, $isis_routes, $eigrp_routes, $netmgmt_routes, $icmp_routes, $egp_routes, $ggp_routes, $hello_routes, $esIs_routes, $ciscoIgrp_routes, $bbnSpfIgp_routes, $bgp_routes, $idpr_routes); 
$local_routes=$static_routes=$other_routes=$ospf_routes=$rip_routes=$isis_routes=$eigrp_routes=$netmgmt_routes=$icmp_routes=$egp_routes=$ggp_routes=$hello_routes=$esIs_routes=$ciscoIgrp_routes=$bbnSpfIgp_routes=$bgp_routes=$idpr_routes=0; 

if ( ! $route_types_import ) {
    $local_routes=1;
    $static_routes=1;
    $other_routes=1;
} else {
    if ( $route_types_import =~ /local/ ) {
        $local_routes=1;
    }
    if ( $route_types_import =~ /static/ ) {
        $static_routes=1;
    }
    if ( $route_types_import =~ /other/ ) {
        $other_routes=1;
    }
    if ( $route_types_import =~ /ospf/ ) {
        $ospf_routes=1;
    }
    if ( $route_types_import =~ /rip/ ) {
        $rip_routes=1;
    }
    if ( $route_types_import =~ /isis/ ) {
        $isis_routes=1;
    }
    if ( $route_types_import =~ /eigrp/ ) {
        $eigrp_routes=1;
    }
    if ( $route_types_import =~ /netmgmt/ ) {
        $netmgmt_routes=1;
    }
    if ( $route_types_import =~ /icmp/ ) {
        $icmp_routes=1;
    }
    if ( $route_types_import =~ /egp/ ) {
        $egp_routes=1;
    }
    if ( $route_types_import =~ /ggp/ ) {
        $ggp_routes=1;
    }
    if ( $route_types_import =~ /hello/ ) {
        $hello_routes=1;
    }
    if ( $route_types_import =~ /esIs/ ) {
        $esIs_routes=1;
    }
    if ( $route_types_import =~ /ciscoIgrp/ ) {
        $ciscoIgrp_routes=1;
    }
    if ( $route_types_import =~ /bbnSpfIgp/ ) {
        $bbnSpfIgp_routes=1;
    }
    if ( $route_types_import =~ /bgp/ ) {
        $bgp_routes=1;
    }
    if ( $route_types_import =~ /idpr/ ) {
        $idpr_routes=1;
    }
}



if ( ! $base_dir ) {
	$exit_message = "Please run this script from /usr/share/gestioip/bin";
	if ( $gip_job_status_id ) {
		exit_error("$exit_message", "$gip_job_status_id", 4);
	} else {
		print_help("$exit_message");
	}
}

if ( ! -r "${base_dir}/etc/${config_name}" ) {
        $exit_message = "\nCan't find configuration file \"$config_name\"";
		if ( $gip_job_status_id ) {
			exit_error("$exit_message", "$gip_job_status_id", 4);
		} else {
			print_help("$exit_message");
		}
}
my $conf = $base_dir . "/etc/" . $config_name;


if (( $tag && $nodes_file ) || ( $tag && $nodes_list ) || ( $nodes_file && $nodes_list )) {
    $exit_message = "Only one of the option \"nodes_file\" or \"tag\" or \"CVS_nodes\" is allowed";
	if ( $gip_job_status_id ) {
		exit_error("$exit_message", "$gip_job_status_id", 4);
	} else {
		print_help("$exit_message");
	}
}

$nodes_file="snmp_targets" if ! $nodes_file;
$nodes_file="$base_dir/etc/${nodes_file}";

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

#my $mail_destinatarios="";
#my $mail_from="";
#if ( $mail ) {
#        if ( ! $params{mail_destinatarios} ) {
#                $exit_message = "Please specify the recipients to send the mail to (\"mail_destinatarios\") in $conf";
#				if ( $gip_job_status_id ) {
#					exit_error("$exit_message", "$gip_job_status_id", 4);
#				} else {
#					print_help("$exit_message");
#				}
#        } elsif ( ! $params{mail_from} ) {
#                $exit_message = "Please specify the mail sender address (\"mail_from\") in $conf";
#				if ( $gip_job_status_id ) {
#					exit_error("$exit_message", "$gip_job_status_id", 4);
#				} else {
#					print_help("$exit_message");
#				}
#        }
#        $mail_destinatarios = \$params{mail_destinatarios};
#        $mail_from = \$params{mail_from};
#}


my $gip_version=get_version();

#if ( $VERSION !~ /$gip_version/ ) {
#        print "\nScript and GestioIP version are not compatible\n\nGestioIP version: $gip_version - script version: $VERSION\n\n";
#        exit 1;
#}

my $lang=$params{lang} || "en";
my $vars_file="$base_dir/etc/vars/vars_update_gestioip_" . $lang;

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

my $snmp_group_id_arg = "";
if ( $snmp_group_arg ) {
    $snmp_group_id_arg = get_snmp_group_id_from_name("$client_id","$snmp_group_arg");
    exit_error("SNMP group not found", "$gip_job_status_id", 4 ) if ! $snmp_group_id_arg;
}

my $cc_id_tag;
my @assign_tags;
my @assign_tag_ids;
if ( $assign_tags ) {
    $cc_id_tag=get_custom_column_id_from_name("$client_id","Tag") || "";
    if  ( ! $cc_id_tag ) {
        $exit_message = "Tag column for networks not enabled - Tag column must be enabled to assign Tags";
        if ( $gip_job_status_id ) {
            exit_error("$exit_message", "$gip_job_status_id", 4);
        } else {
            print_help("$exit_message");
        }
    }

    $assign_tags =~ s/ //g;
    @assign_tags=split(",", $assign_tags);
    my %tags = Gipfuncs::get_tag_hash("$client_id", "name", "$gip_job_status_id");
    foreach ( @assign_tags ) {
        if ( ! $tags{"$_"} ) {
            $exit_message = "Tag not found: $_";
            if ( $gip_job_status_id ) {
                exit_error("$exit_message", "$gip_job_status_id", 4);
            } else {
                print_help("$exit_message");
            }
        }
        push @assign_tag_ids, $tags{"$_"}[0];
    }

}


if ( $new_networks_file ) {
    if ( $new_networks_file =~ /^-/ ) {
        $exit_message = "New networks file must not start with \"-\"";
		if ( $gip_job_status_id ) {
			exit_error("$exit_message", "$gip_job_status_id", 4);
		} else {
			print_help("exit_message");
		}
    }
    $new_networks_file = "$base_dir/var/data/$new_networks_file";
    open (NET_FILE,">$new_networks_file") or exit_error("Can not open network file $new_networks_file: $!", "$gip_job_status_id", 4);
}


$ignore_generic_auto = $ignore_generic_auto || $params{'ignore_generic_auto'};

my $force_site_id = "-1";
if ( $force_site ) {
    my $db_locations = get_loc_hash("$client_id");
    if ( ! defined($db_locations->{$force_site} )) {
        $exit_message = "$client: Site does not exists: \"$force_site\"";
        exit_error("$exit_message", "$gip_job_status_id", 4);
    }
    $force_site_id = $db_locations->{$force_site};
}

if ( $add_if_descr && ! $interfaces_descr_indent ) {
    $interfaces_descr_indent = "Alias";
}

if ( $interfaces_descr_indent && $interfaces_descr_indent !~ /^([Aa]lias|[Dd]escr)$/ ) {
    $exit_message = "Interface description identifier (-k) must be either \"Alias\" or \"Descr\"";
    exit_error("$exit_message", "$gip_job_status_id", 4);
}
if ( $interfaces_descr_indent ) {
    $add_if_descr = 1;
}

my $red_num;

my @all_db_networks = get_all_networks("$client_id","v4") if $ipv4 =~ /^yes$/i;
my @all_db_networks6 = get_all_networks("$client_id","v6") if $ipv6 =~ /^yes$/i;
my $values_redes=get_redes_hash("$client_id","","return_int","client_only","redint","no_rootnet");
my %values_redes=%$values_redes;

my @nodes;
my $node;
my $no_node_additional_message = "";
if ( $tag ) {
	#TAGs
	$tag =~ s/\s//g;
	my @tag = split(",", $tag);
	my $tag_ref = \@tag;

	@nodes = get_tag_hosts("$client_id", $tag_ref);

    $no_node_additional_message = "(no nodes with TAG(s) $tag found)" if ! @nodes;
} elsif ( $nodes_list ) {
	@nodes=split(",",$nodes_list);

	print "Reading nodes from csv list...\n" if $verbose;
	print LOG  "Reading nodes from csv list...\n";

} else {
	open(IN,"<$nodes_file") or exit_error("Can not open nodes file: $nodes_file: $!", "$gip_job_status_id", 4);

	my $i=0;

	while (<IN>) {
		$node = $_;
		next if $node =~ /^#/;
		next if $node !~ /.+/; 
		chomp ($node);
		$nodes[$i]=$node;
		$i++;
	}
    close IN;
}

if ( ! $nodes[0] ) {
	$exit_message = "No nodes to query found $no_node_additional_message";
    exit_error("$exit_message", "$gip_job_status_id", 4);
}

my @client_entries=get_client_entries("$client_id");

my $default_resolver = $client_entries[0]->[20];
my @dns_servers =("$client_entries[0]->[21]");
push @dns_servers, $client_entries[0]->[22] if $client_entries[0]->[22];
push @dns_servers, $client_entries[0]->[23] if $client_entries[0]->[23];

my %proto_map = ('1'=>'other', '2'=>'local', '3'=>'netmgmt', '4'=>'icmp', '5'=>'egp', '6'=>'ggp', '7'=>'hello', '8'=>'rip', '9'=>'isIs', '10'=>'esIs', '11'=>'ciscoIgrp', '12'=>'bbnSpfIgp', '13'=>'ospf', '14'=>'bgp', '15'=>'idpr', '16'=>'ciscoEigrp' );



my @process_networks_v4=();
my %pn_v4;
if ( $process_networks_v4 ) {
    @process_networks_v4=split(",",$process_networks_v4);

    foreach ( @process_networks_v4 ) {
        my $pnet=$_;
        $pnet =~ s/^\s+//g;
        $pnet =~ s/\s+$//g;
        if ( $pnet !~ /^\d{1,3}$/ ) {
            print LOG "invalid \"process_networks_v4\": $pnet - IGNORED\n";
        }
        $pn_v4{$pnet}++;
    }
}
@process_networks_v4 = ( keys %pn_v4 );

my @process_networks_v6=();
my %pn_v6;
if ( $process_networks_v6 ) {
    @process_networks_v6=split(",",$process_networks_v6);

    foreach ( @process_networks_v6 ) {
        my $pnet=$_;
        $pnet =~ s/^\s+//g;
        $pnet =~ s/\s+$//g;
        if ( $pnet !~ /^[0-9a-fA-F]{1,4}$/ ) {
            print LOG "invalid \"process_networks_v6\": $pnet - IGNORED\n";
            print "invalid \"process_networks_v6\": $pnet - IGNORED\n";
        }
        $pn_v6{$pnet}++;
    }
}
@process_networks_v6 = ( keys %pn_v6 );

my %all_found_redes_hash;
my %values_redes_node_all;
my %comment_was_updated;
foreach ( @nodes ) {
	$node = $_;
	print "\n+++ Importing networks from $node +++\n\n" if $verbose;
	print LOG "\n+++ Importing networks from $node +++\n\n";

    my $values_redes_node=get_redes_hash("$client_id","","return_int","client_only","","no_rootnet","","$node");
    my %values_redes_node=%$values_redes_node;
    %values_redes_node_all = (%values_redes_node_all, %values_redes_node);

	# get snmp parameter
    my $ip_version_node="v4";
    $ip_version_node="v6" if $node !~ /^\d{1,3}\./;
    my $ip_int_node=ip_to_int("$node","$ip_version_node");
    my $node_id=get_host_id_from_ip_int("$client_id","$ip_int_node","") || "";

	my ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port) = get_snmp_parameter("$client_id", "$node_id", "host", "$snmp_group_id_arg");


    my $mibdirs_ref = check_mib_dir("$client_id","$vars_file");

    my %net_descr_hash;

    my $snmp_info_session=create_snmp_info_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","$auth_is_key","$priv_proto","$priv_pass","$priv_is_key","$sec_level",$mibdirs_ref,"$vars_file","$debug","$snmp_port");

    if ( ! $snmp_info_session ) {
        print "\n+++ $node: can not create SNMP::Info session +++\n\n";
        print LOG "\n+++ $node: can not create SNMP::Info session +++\n\n";
        next;
    }

    $snmp_info_session->bulkwalk(0);

    my ( $ifDescr, $ifName, $ifNameI, $ifAlias );
    my $interfaces = $snmp_info_session->interfaces();
    my $i_descr=$snmp_info_session->i_description();
    my $i_name=$snmp_info_session->i_name();
    my $i_alias=$snmp_info_session->i_alias();

    foreach my $iid (keys %$interfaces){
        $ifName=$interfaces->{$iid} || "";
        $ifNameI=$i_name->{$iid} || "";
        $ifDescr=$i_descr->{$iid} || "";
        $ifAlias=$i_alias->{$iid} || "";
        print LOG "IF IID: $iid - Name: $ifName - Name1: $ifNameI - Descr: $ifDescr - Alias: $ifAlias\n" if $debug;
        print "IF IID: $iid - Name: $ifName - Name1: $ifNameI - Descr: $ifDescr - Alias: $ifAlias\n" if $debug;
    }

	my $session=create_snmp_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","$auth_is_key","$priv_proto","$priv_pass","$priv_is_key","$sec_level");

    if ( ! $session ) {
        print "\n+++ $node: can not create SNMP session +++\n\n";
        print LOG "\n+++ $node: can not create SNMP session +++\n\n";
        next;
    }

	# get hostname, ...
	my ($device_descr, $device_name, $device_contact, $device_location);
	$device_descr=$device_name=$device_contact=$device_location="";

	no strict 'subs';
	my $vars = new SNMP::VarList([sysDescr,0],
				[sysName,0],
				[sysContact,0],
				[sysLocation,0]);
	use strict 'subs';

	my @values = $session->get($vars);

	if ( ! ($session->{ErrorStr}) ) {
		$device_descr = $values[0] || "";
		$device_name = $values[1] || "unknown";
		$device_contact = $values[2] || "";
		$device_location = $values[3] || "";
	}


	my ($ipRouteProto,$route_dest_cidr,$route_dest_cidr_mask,$comment,$route_ifindex);
	my @route_dests_cidr;

    my $l_helper;
	if ( $ipv4 =~ /^yes$/i ) {

        ###################
		### ipCidrRouteDest
        ###################

		my $first_query_ok = "0";

		my ($ipRouteProto,$route_dest_cidr,$route_dest_cidr_mask,$route_if_descr);

		$vars = new SNMP::VarList(['ipCidrRouteDest'],
					['ipCidrRouteMask'],
					['ipCidrRouteProto'],
					['ipCidrRouteIfIndex']);

		# get first row
		if ($session->{ErrorStr}) {
#			print LOG "Can't connect to $node\n";
#			print "Can't connect to $node (2)\n" if $verbose;
#			next;
		} else {
			$first_query_ok = "1";
		}

		# and all subsequent rows
		my $l = 0;

		while (!$session->{ErrorStr} and ( $$vars[0]->tag eq "ipCidrRouteDest" || $$vars[0]->tag eq "ipCidrRouteMask" || $$vars[0]->tag eq "ipCidrRouteProto" || $$vars[0]->tag eq "ipCidrRouteIfIndex")) {
            ($route_dest_cidr,$route_dest_cidr_mask,$ipRouteProto,$route_ifindex) = $session->getnext($vars);
            print LOG "DEBUG: VAR " . $$vars[0]->tag . "\n" if $debug;
            print LOG "ipCidrRouteDest: $route_dest_cidr,$route_dest_cidr_mask,$ipRouteProto,$route_ifindex\n" if $debug;
            print "ipCidrRouteDest: $route_dest_cidr,$route_dest_cidr_mask,$ipRouteProto,$route_ifindex\n" if $debug;
            next if ! $ipRouteProto;
            next if $route_dest_cidr =~ /0.0.0.0/ || $route_dest_cidr =~ /169.254.0.0/;
            $comment = "";
            $route_if_descr = "";
            if ( $add_if_descr && $ipRouteProto =~ /local/  ) {
                if ( $interfaces_descr_indent eq "Descr" ) {
                    $route_if_descr = $interfaces->{$route_ifindex} || "";
                } else {
                    $route_if_descr = $i_alias->{$route_ifindex} || "";
                }
            }

            print LOG "R_DESC - $route_if_descr\n" if $debug;
            print "R_DESC - $route_if_descr\n" if $debug;

            if ( $ipRouteProto =~ /local/ && $local_routes ) {
                    $comment = "Local route from $node" if $add_comment == "1";
            } elsif ( $ipRouteProto =~ /netmgmt/ && $static_routes ) {
                    $comment = "Static route from $node" if $add_comment == "1";
            } elsif ( $ipRouteProto =~ /other/ && $other_routes ) {
                    $comment = "Other route from $node" if $add_comment == "1";
            } elsif ( $ipRouteProto =~ /ospf/ && $ospf_routes ) {
                    $comment = "OSPF route from $node" if $add_comment eq "1";
            } elsif ( $ipRouteProto =~ /^rip$/ && $rip_routes ) {
                    $comment = "RIP route from $node" if $add_comment eq "1";
            } elsif ( $ipRouteProto =~ /^isIs$/ && $isis_routes ) {
                    $comment = "Dual IS-IS route from $node" if $add_comment eq "1";
            } elsif ( $ipRouteProto =~ /ciscoEigrp/ && $eigrp_routes ) {
                    $comment = "Eigrp route from $node" if $add_comment eq "1";
            }
			if (( $ipRouteProto =~ /local/ && $local_routes ) || ( $ipRouteProto =~ /netmgmt/ && $static_routes ) || ( $ipRouteProto =~ /other/ && $other_routes ) || ( $ipRouteProto =~ /ospf/ && $ospf_routes ) || ( $ipRouteProto =~ /^rip$/ && $rip_routes ) || ( $ipRouteProto =~ /isIs/ && $isis_routes ) || ( $ipRouteProto =~ /ciscoEigrp/ && $eigrp_routes )) {
                if ( $route_dest_cidr_mask =~ /\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/ ) {
                    $route_dest_cidr_mask =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
					my ($first_oct,$second_oct,$third_oct,$fourth_oct);
					$first_oct=$1;
					$second_oct=$2;
					$third_oct=$3;
					$fourth_oct=$4;
					if ( $fourth_oct > $first_oct ) {
						$route_dest_cidr_mask = $fourth_oct . "." . $third_oct . "." . $second_oct . "." . $first_oct;
					} else {
						$route_dest_cidr_mask = $first_oct . "." . $second_oct . "." . $third_oct . "." . $fourth_oct;
					}
                }
                $route_dests_cidr[$l] = "$route_dest_cidr/$route_dest_cidr_mask/$comment/$route_if_descr";
#                if ( $add_comment == "1" ) {
#                        $route_dests_cidr[$l] = "$route_dest_cidr/$route_dest_cidr_mask/$comment";
#                } else {
#                        $route_dests_cidr[$l] = "$route_dest_cidr/$route_dest_cidr_mask";
#                }
                print LOG "DEBUG: ipCidrRouteDest PRE ADD $route_dest_cidr/$route_dest_cidr_mask/$comment/$route_if_descr\n" if $debug;
                print "DEBUG: ipCidrRouteDest PRE ADD $route_dest_cidr/$route_dest_cidr_mask/$comment/$route_if_descr\n" if $debug;
            }
            $l++;
        };


        ###############
		### ipRouteDest
        ###############

		my ($route_dest,$route_mask,$route_proto,$route_ifindex);

		$vars = new SNMP::VarList(['ipRouteDest'],
					['ipRouteMask'],
					['ipRouteProto'],
                    ['ipRouteIfIndex']);

		# get first row
		($route_dest) = $session->getnext($vars);
		if ($session->{ErrorStr} && $first_query_ok ne "1" ) {
			if ( $session->{ErrorStr} =~ /nosuchname/i ) {
				print LOG "$node: $lang_vars{nosuchname_snmp_error_message}\n";
				print "$lang_vars{nosuchname_snmp_error_message}\n" if $verbose;
            } else {
				print LOG "Can't connect to $node\n";
				print "Can't connect to $node (3)" . $session->{ErrorStr} . "\n" if $verbose;
			}
			next;
		}

		# and all subsequent rows

		while (!$session->{ErrorStr} and $$vars[0]->tag eq "ipRouteDest") {
            ($route_dest,$route_mask,$route_proto,$route_ifindex) = $session->getnext($vars);
			print LOG "DEBUG: VAR " . $$vars[0]->tag . "\n" if $debug;
            print LOG "ipRouteDest: $route_dest,$route_mask,$route_proto,$route_ifindex\n" if $debug;
            print "ipRouteDest: $route_dest,$route_mask,$route_proto,$route_ifindex\n" if $debug;
            $route_if_descr = "";
            if ( $add_if_descr && $route_proto =~ /local/  ) {
                if ( $interfaces_descr_indent eq "Descr" ) {
                    $route_if_descr = $interfaces->{$route_ifindex} || "";
                } else {
                    $route_if_descr = $i_alias->{$route_ifindex} || "";
                }
            }

            $comment = "";
            next if ! $route_proto;
            next if $route_dest =~ /0.0.0.0/ || $route_dest =~ /169.254.0.0/;
            if ( $route_proto =~ /local/ && $local_routes ) {
                    $comment = "Local route from $node" if $add_comment == "1";
            } elsif ( $route_proto =~ /netmgmt/ && $static_routes ) {
                    $comment = "Static route from $node" if $add_comment == "1";
            } elsif ( $route_proto =~ /other/ && $other_routes == "1" ) {
                    $comment = "Other route from $node" if $add_comment == "1";
            } elsif ( $route_proto =~ /ospf/ && $ospf_routes ) {
                    $comment = "OSPF route from $node" if $add_comment eq "1";
            } elsif ( $route_proto =~ /^rip$/ && $rip_routes ) {
                    $comment = "RIP route from $node" if $add_comment eq "1";
            } elsif ( $route_proto =~ /^isIs$/ && $isis_routes ) {
                    $comment = "Dual IS-IS route from $node" if $add_comment eq "1";
            } elsif ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes ) {
                    $comment = "Eigrp route from $node" if $add_comment eq "1";
            }
			if (( $route_proto =~ /local/ && $local_routes ) || ( $route_proto =~ /netmgmt/ && $static_routes ) || ( $route_proto =~ /other/ && $other_routes ) || ( $route_proto =~ /ospf/ && $ospf_routes ) || ( $route_proto =~ /^rip$/ && $rip_routes ) || ( $route_proto =~ /isIs/ && $isis_routes ) || ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes )) {
#                if ( $add_comment == "1" ) {
#                        $route_dests_cidr[$l] = "$route_dest/$route_mask/$comment";
#                } else {
#                        $route_dests_cidr[$l] = "$route_dest/$route_mask";
#                }
                $route_dests_cidr[$l] = "$route_dest/$route_mask/$comment/$route_if_descr";
                print LOG "DEBUG: ipRouteDest PRE ADD $route_dest/$route_mask/$comment/$route_if_descr\n" if $debug;
                print "DEBUG: ipRouteDest PRE ADD $route_dest/$route_mask/$comment/$route_if_descr\n" if $debug;
            }
            $l++;
        }


        ######################
        ### inetCidrRouteProto
        ######################

		$vars = new SNMP::VarList(['inetCidrRouteDest'],
					['inetCidrRouteProto'],
					['inetCidrRouteIfIndex']);

		if ($session->{ErrorStr} ) {
			if ( $session->{ErrorStr} =~ /nosuchname/i ) {
				print LOG "$node: $lang_vars{nosuchname_snmp_error_message}\n";
			} else {
				print LOG "Can't connect to $node - $session->{ErrorStr} (3)\n";
#				next;
			}
		}

		# and all subsequent rows

		while (!$session->{ErrorStr} and ( $$vars[0]->tag eq "inetCidrRouteDest" || $$vars[0]->tag eq "inetCidrRouteIfIndex" || $$vars[0]->tag eq "inetCidrRouteProto") ){
            ($route_dest,$route_proto,$route_ifindex) = $session->getnext($vars);
            print LOG "VAR " . $$vars[0]->tag . "\n" if $debug;
            print LOG "inetCidrRouteProto: $route_dest,$route_proto,$route_ifindex\n" if $debug;
            print "inetCidrRouteProto: $route_dest,$route_proto,$route_ifindex\n" if $debug;

			my $iid=$$vars[0]->iid;

            print LOG "DEBUG: IID: $iid\n" if $debug;;
            print "DEBUG: IID: $iid\n" if $debug;;
            # 1.4.192.168.1.0.24.3.0.0.4.1.4.0.0.0.0 (linux)
            # 1.4.10.20.0.0.24.2.0.0.1.4.10.20.0.1 (cisco nexus)

			if ( $iid !~ /^((\d{1,3}\.){15,16}\d{1,3})$/ ) {
				next;
			}
            
			$iid =~ /^\d{1,3}\.\d{1,3}\.(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,3})\..*$/;
			my $ip=$1;
			my $ip_mask=$2;

            $route_if_descr = "";
#            if ( $add_if_descr && $route_proto =~ /local/  ) {
#                $route_if_descr = $interfaces->{$route_ifindex} || "";
#            }
			if ( $add_if_descr && $ipRouteProto =~ /local/  ) {
                if ( $interfaces_descr_indent eq "Descr" ) {
                    $route_if_descr = $interfaces->{$route_ifindex} || "";
                } else {
                    $route_if_descr = $i_alias->{$route_ifindex} || "";
                }
            }

            print LOG "DEBUG: IP/MASK DESCR: $ip/$ip_mask - $route_if_descr\n" if $debug;
            print "DEBUG: IP/MASK DESCR: $ip/$ip_mask - $route_if_descr\n" if $debug;

            next if ! $ip;
            next if ! $ip_mask;

			$route_dest = $ip;

            # convert bitmask to subnet mask
            if ( $ip_mask eq 32 ) {
                $route_mask = "255.255.255.255";
            } else {
                $route_mask = pack("N",-(1<<(32-($ip_mask % 32))));
                $route_mask = join('.', unpack("C4",$route_mask ));
            }

            next if $route_dest =~ /0.0.0.0/ || $route_dest =~ /169.254.0.0/;

			$comment = "";
			if ( $route_proto =~ /local/ && $local_routes ) {
				$comment = "Local route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /netmgmt/ && $static_routes ) {
				$comment = "Static route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /other/ && $other_routes ) {
				$comment = "Other route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ospf/ && $ospf_routes ) {
				$comment = "OSPF route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^rip$/ && $rip_routes ) {
				$comment = "RIP route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^isIs$/ && $isis_routes ) {
				$comment = "Dual IS-IS route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes ) {
				$comment = "Eigrp route from $node" if $add_comment eq "1";
			}
			if (( $route_proto =~ /local/ && $local_routes ) || ( $route_proto =~ /netmgmt/ && $local_routes ) || ( $route_proto =~ /other/ && $other_routes ) || ( $route_proto =~ /ospf/ && $ospf_routes ) || ( $route_proto =~ /^rip$/ && $rip_routes ) || ( $route_proto =~ /isIs/ && $isis_routes ) || ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes )) {
#				if ( $add_comment eq "1" ) {
#					$route_dests_cidr[$l] = "$route_dest/$route_mask/$comment"; 
#				} else {
#					$route_dests_cidr[$l] = "$route_dest/$route_mask"; 
#				}
                $route_dests_cidr[$l] = "$route_dest/$route_mask/$comment/$route_if_descr";
                print LOG "DEBUG: inetCidrRouteProto PRE ADD $route_dest/$route_mask/$comment/$route_if_descr\n" if $debug;
                print "DEBUG: inetCidrRouteProto PRE ADD $route_dest/$route_mask/$comment/$route_if_descr\n" if $debug;
			}
			$l++;
		};
        $l_helper = $l;
	}

    print LOG "DEBUG: number route_dests_cidr A: " . scalar(@route_dests_cidr) . "\n" if $debug;
    print "DEBUG: number route_dests_cidr A: " . scalar(@route_dests_cidr) . "\n" if $debug;


	##### IPv6 Routes

	my @route_dests_cidr_ipv6;

	if ( $ipv6 =~ /^yes$/i ) {
        print LOG "DEBUG: IPV6\n" if $debug;
		my $l=0;
		my @ip_arr;

        ######################
		### inetCidrRouteProto
        ######################

		my ($route_dest,$route_mask,$route_proto);

		$vars = new SNMP::VarList(['inetCidrRouteDest'],
					['inetCidrRouteProto'],
					['inetCidrRouteIfIndex']);

		# get first row

		if ($session->{ErrorStr} ) {
			if ( $session->{ErrorStr} =~ /nosuchname/i ) {
				print LOG "$node: $lang_vars{nosuchname_snmp_error_message}\n";
			} else {
				print LOG "Can't connect to $node (3)" . $session->{ErrorStr} . "\n";
#				next;
			}
		}

		# and all subsequent rows

		while (!$session->{ErrorStr} and ( $$vars[0]->tag eq "inetCidrRouteDest" || $$vars[0]->tag eq "inetCidrRouteIfIndex" || $$vars[0]->tag eq "inetCidrRouteProto") ){
            ($route_dest,$route_proto,$route_ifindex) = $session->getnext($vars);
            print LOG "DEBUG: VAR " . $$vars[0]->tag . "\n" if $debug;
            print LOG "DEBUG: inetCidrRouteDest (v6): $route_dest,$route_proto,$route_ifindex\n" if $debug;

			my $iid=$$vars[0]->iid;
            print LOG "DEBUG: IID: $iid\n" if $debug;;
            print "DEBUG: IID: $iid\n" if $debug;;

			if ( $iid !~ /^((\d{1,3}\.){20})/ ) {
				next;
			}
			$iid =~ /^\d{1,3}\.\d{1,3}\.((\d{1,3}\.){16})(\d{1,3})\.(\d{1,3})\..*$/;
			my $ip_dec=$1;
			my $ip_mask=$3;
			$ip_dec =~ s/\.$//;

            my $route_if_descr = "";
            if ( $add_if_descr && $route_proto =~ /local/  ) {
                $route_if_descr = $interfaces->{$route_ifindex} || "";
            }

            print LOG "DEBUG: IP/MASK DESCR: $ip_dec/$ip_mask - $route_if_descr\n" if $debug;

			next if $ip_mask eq "128";
			next if $ip_mask eq 0;

			$ip_dec =~ s/\./ /g;
			@ip_arr = split(" ",$ip_dec);

			my $m="0";
			my $ipv6_add="";
			foreach (@ip_arr) {
				my $hex=unpack("H*", pack("N", $ip_arr[$m]));
				$hex =~ s/^0{6}//;
				if ( $m == 1 || $m ==3 || $m == 5 || $m == 7 || $m == 9 || $m == 11 || $m == 13 ) {
					$ipv6_add .= $hex . ":";
				} else {
					$ipv6_add .= $hex;
				}
				$m++;
			}
			$route_dest=$ipv6_add;
			$route_mask=$ip_mask;
            print LOG "DEBUG: $ipv6_add/$ip_mask\n" if $debug;
			$comment = "";
			if ( $route_proto =~ /local/ && $local_routes ) {
				$comment = "Local route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /netmgmt/ && $static_routes ) {
				$comment = "Static route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /other/ && $other_routes ) {
				$comment = "Other route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ospf/ && $ospf_routes ) {
				$comment = "OSPF route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^rip$/ && $rip_routes ) {
				$comment = "RIP route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^isIs$/ && $isis_routes ) {
				$comment = "Dual IS-IS route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes ) {
				$comment = "Eigrp route from $node" if $add_comment eq "1";
			}
			if (( $route_proto =~ /local/ && $local_routes ) || ( $route_proto =~ /netmgmt/ && $local_routes ) || ( $route_proto =~ /other/ && $other_routes ) || ( $route_proto =~ /ospf/ && $ospf_routes ) || ( $route_proto =~ /^rip$/ && $rip_routes ) || ( $route_proto =~ /isIs/ && $isis_routes ) || ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes )) {
                $route_dests_cidr_ipv6[$l] = "$route_dest/$route_mask/$comment/$route_if_descr"; 
                print LOG "DEBUG: inetCidrRouteProto v6 PRE ADD $route_dest/$route_mask\n" if $debug;
                print "DEBUG: inetCidrRouteProto PRE ADD $route_dest/$route_mask\n" if $debug;
			}
			$l++;
		};


        #####################
		### ipv6RouteProtocol
        #####################

		$vars = new SNMP::VarList(['ipv6RouteProtocol']
					);

		# get first row
		($route_dest) = $session->getnext($vars);
		if ($session->{ErrorStr} && ! $route_dests_cidr_ipv6[0] ) {
			if ( $session->{ErrorStr} =~ /nosuchname/i ) {
				print LOG "$node: $lang_vars{nosuchname_snmp_error_message}\n";
			} else {
				print LOG "Can't connect to $node (3)" . $session->{ErrorStr} . "\n";
#				next;
			}
		}

		# and all subsequent rows

		while (!$session->{ErrorStr} and $$vars[0]->tag eq "ipv6RouteProtocol"){
			($route_dest) = $session->getnext($vars);

			my $iid=$$vars[0]->iid;
			$iid =~ /^((\d{1,3}\.){16})(.+).*$/;
			my $ip_dec=$1;
			$ip_dec =~ s/\.$//;
			$iid =~ /(\d{1,3})\.\d{1,3}$/;
			my $ip_mask=$1;
			my $route_proto = $$vars[0]->val;

			next if $ip_mask eq "128";

			$ip_dec =~ s/\./ /g;
			@ip_arr = split(" ",$ip_dec);

			my $m="0";
			my $ipv6_add="";
			foreach (@ip_arr) {
				my $hex=unpack("H*", pack("N", $ip_arr[$m]));
				$hex =~ s/^0{6}//;
				if ( $m == 1 || $m ==3 || $m == 5 || $m == 7 || $m == 9 || $m == 11 || $m == 13 ) {
					$ipv6_add .= $hex . ":";
				} else {
					$ipv6_add .= $hex;
				}
				$m++;
			}
			$route_dest=$ipv6_add;

			$route_mask=$ip_mask;
			$comment = "";
			if ( $route_proto =~ /local/ && $local_routes ) {
				$comment = "Local route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /netmgmt/ && $static_routes ) {
				$comment = "Static route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /other/ && $other_routes ) {
				$comment = "Other route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ospf/ && $ospf_routes ) {
				$comment = "OSPF route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^rip$/ && $rip_routes ) {
				$comment = "RIP route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /^isIs$/ && $isis_routes ) {
				$comment = "Dual IS-IS route from $node" if $add_comment eq "1";
			} elsif ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes ) {
				$comment = "Eigrp route from $node" if $add_comment eq "1";
			}
			if (( $route_proto =~ /local/ && $local_routes ) || ( $route_proto =~ /netmgmt/ && $local_routes ) || ( $route_proto =~ /other/ && $other_routes ) || ( $route_proto =~ /ospf/ && $ospf_routes ) || ( $route_proto =~ /^rip$/ && $rip_routes ) || ( $route_proto =~ /isIs/ && $isis_routes ) || ( $route_proto =~ /ciscoEigrp/ && $eigrp_routes )) {
				if ( $add_comment eq "1" ) {
					$route_dests_cidr_ipv6[$l] = "$route_dest/$route_mask/$comment"; 
				} else {
					$route_dests_cidr_ipv6[$l] = "$route_dest/$route_mask"; 
				}
                print LOG "DEBUG: ipv6RouteProtocol v6 PRE ADD $route_dest/$route_mask\n" if $debug;
                print "DEBUG: ipv6RouteProtocol PRE ADD $route_dest/$route_mask\n" if $debug;
			}
			$l++;
		};
	}
    

	#VRF ROUTES

    print LOG "DEBUG: l_helper: $l_helper\n" if $debug;
    print "DEBUG: l_helper: $l_helper\n" if $debug;

	if ( $get_vrf_routes && $ipv4 =~ /^yes$/i ) {

        my @routes;
		# MPLS-L3VPN-STD-MIB
        my $session=create_snmp_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","$auth_is_key","$priv_proto","$priv_pass","$priv_is_key","$sec_level","1");

        my $vars = new SNMP::VarList(['.1.3.6.1.2.1.10.166.11.1.4.1.1.9']);
		my @resp = $session->bulkwalk(0, 10, $vars);

        my $l = $l_helper;

		if ( $session->{ErrorNum} ) {
			print "ERROR: VRF route discovery failed: Cannot do bulkwalk: $session->{ErrorStr} ($session->{ErrorNum})\n";
			print "Try again with SNMP v2c\n\n" if $session->{ErrorStr} =~ /Cannot send V2 PDU on V1 session/;
		} else {
            my $m=0;
            for my $vbarr ( @resp ) {
                my $oid = $$vars[$m++]->tag();
                my $num = scalar @$vbarr;
                print LOG "DEBUG: $num responses for oid $oid:\n" if $debug;
                print "DEBUG: $num responses for oid $oid:\n" if $debug;

                for my $v (@$vbarr) {
                    my $oid_name = $v->name;
                    print LOG "DEBUG: oid_name: $oid_name\n" if $debug;
                    print "DEBUG: oid_name: $oid_name\n" if $debug;
                    my $route_proto_id = $v->val;
                    my $route_proto = $proto_map{$route_proto_id};
                    print LOG "DEBUG: RPa: $route_proto_id - $route_proto\n" if $debug;
                    print "DEBUG: RPa: $route_proto_id - $route_proto\n" if $debug;

                    my $vrf_name="";
                    my $net="";
                    my $mask="";
                    my $gw="";
                    if ( $oid_name =~ /166\.11\.1\.4\.1\.1\.9\.(.+)?\.1\.4\.(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,2})\..+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/ ) {
                        $oid_name =~ /166\.11\.1\.4\.1\.1\.9\.(.+)?\.1\.4\.(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\.(\d{1,2})\..+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/;
                        $vrf_name=$1;
                        $net=$2;
                        $mask=$3;
                        $gw=$4;
                    } else {
                        next;
                    }

                    my $ascii_vrf_name = join("", map { chr($_) } split(/\./,$vrf_name));
                    $ascii_vrf_name =~ s/\R//g;
                    if ( ! $vrf_name || ! $net || ! $mask ) {
                        print "Error: $oid_name: information missing: $ascii_vrf_name - $net/$mask - $gw - $route_proto_id\n" if $verbose;
                        print LOG "Error: $oid_name: information missing: $ascii_vrf_name - $net/$mask - $gw - $route_proto_id\n" if $verbose;
                    } else {
                        print "DEBUG: $ascii_vrf_name - $net/$mask - $gw - $route_proto_id\n" if $debug;
                        print LOG "DEBUG: $ascii_vrf_name - $net/$mask - $gw - $route_proto_id\n" if $debug;

                        if ( $route_proto eq "local" and $local_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "other" and $other_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "netmgmt" and $netmgmt_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "icmp" and $icmp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "egp" and $egp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "ggp" and $ggp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "hello" and $hello_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "rip" and $rip_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "isIs" and $isis_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "esIs" and $esIs_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "ciscoIgrp" and $ciscoIgrp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "bbnSpfIgp" and $bbnSpfIgp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "ospf" and $ospf_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "bgp" and $bgp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "idpr" and $idpr_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } elsif ( $route_proto eq "cicoEigrp" and $eigrp_routes == 1 ) {
                            push(@routes,"$ascii_vrf_name,$net,$mask,$gw,$route_proto");
                        } else {
                            print "$route_proto route ignored by configuration: $net/$mask\n" if $debug;
                            print LOG "$route_proto route ignored by configuration: $net/$mask\n" if $debug;
                        }
                    }    
                }
            }

			foreach ( @routes ) {
                print "DEBUG: ROUTES: $_\n" if $debug;
                print LOG "DEBUG: ROUTES: $_\n" if $debug;
				my ($ascii_vrf_name,$route_dest,$route_mask,$gw,$route_proto)=split(",",$_);
				if ( $add_comment == "1" ) {
                    $comment = "$route_proto route from $node" if $add_comment eq "1";
					$route_dests_cidr[$l] = "$route_dest/$route_mask/$comment" . "::VRF::${ascii_vrf_name}::";
				} else {
					$route_dests_cidr[$l] = "$route_dest/$route_mask" . "::VRF::${ascii_vrf_name}::";
				}
				$l++;
			}
		}
	}

    print "DEBUG: number route_dests_cidr B: " . scalar(@route_dests_cidr) . "\n" if $debug;
    print LOG "DEBUG: number route_dests_cidr B: " . scalar(@route_dests_cidr) . "\n" if $debug;


	# delete duplicated entries and networks with are not "process_networks_v4"

	my %seen = ();
	my $item;
	my @uniq;
	my $ignore_red;
	foreach $item(@route_dests_cidr) {
		next if ! $item;
		$ignore_red="0";
		if ( $process_networks_v4[0] ) {
			$ignore_red="1" ;
			foreach ( @process_networks_v4 ) {
				my $pnet=$_;
				$pnet =~ s/\./\\./;
				$pnet =~ s/\*/.\*/;
				if ( $item =~ m/^$pnet/ ) {
					$ignore_red="0";
					last;
				}
			}
		}
		if ( $ignore_red==0 ) {
			push(@uniq, $item) unless $seen{$item}++; 
		}
	}
	@route_dests_cidr = @uniq;

    #Sort array by mask
    if ( $ascend ) {
        @route_dests_cidr = sort {
            convert_mask("",(split '/', $a)[1],"x") cmp
            convert_mask("",(split '/', $b)[1],"x")
        } @route_dests_cidr;
    } else {
        @route_dests_cidr = sort {
            convert_mask("",(split '/', $b)[1],"x") cmp
            convert_mask("",(split '/', $a)[1],"x")
        } @route_dests_cidr;
    }


	my @process_networks_v6=();
	if ( $process_networks_v6 ) {
		@process_networks_v6=split(",",$process_networks_v6);
	}

	%seen = ();
	@uniq=();
	$ignore_red="0";
	foreach $item(@route_dests_cidr_ipv6) {
		next if ! $item;
		$ignore_red="0";
		if ( $process_networks_v6[0] ) {
			$ignore_red="1" ;
			foreach ( @process_networks_v6 ) {
				my $pnet=$_;
                $pnet =~ s/^\s+//g;
                $pnet =~ s/\s+$//g;
				$pnet =~ s/\./\\./;
				$pnet =~ s/\*/.\*/;
				if ( $item =~ m/^$pnet/ ) {
					$ignore_red="0";
					last;
				}
			}
		}
		if ( $ignore_red==0 ) {
			push(@uniq, $item) unless $seen{$item}++; 
		}
	}
	@route_dests_cidr_ipv6 = @uniq;

    #Sort array by prefix
    if ( $ascend ) {
        @route_dests_cidr_ipv6 = sort {
            convert_mask("",(split '/', $a)[1],"x","v6") cmp
            convert_mask("",(split '/', $b)[1],"x","v6")
        } @route_dests_cidr_ipv6;
    } else {
        @route_dests_cidr_ipv6 = sort {
            convert_mask("",(split '/', $b)[1],"x","v6") cmp
            convert_mask("",(split '/', $a)[1],"x","v6")
        } @route_dests_cidr_ipv6;
    }



	my ($network_cidr_mask, $network_no_cidr, $BM);
	my @hostroutes;
	my $hostroute;

	foreach $network_cidr_mask (@route_dests_cidr) {
		my $ascii_vrf_name = "";
		next if ! $network_cidr_mask;
		next if $network_cidr_mask =~ /0.0.0.0/ || $network_cidr_mask =~ /169.254.0.0/;
		my ($network,$mask,$comment,$route_if_descr);
		if ( $network_cidr_mask =~ /::VRF::/ ) {
            $ascii_vrf_name = "";
			if ($network_cidr_mask =~ /::VRF::(.*)::$/) {
                $network_cidr_mask =~ /::VRF::(.*)::$/;
                $ascii_vrf_name = $1 || "";
            }
			$network_cidr_mask =~ s/::VRF::.*//;
		}

        ($network,$mask,$comment,$route_if_descr) = split("/",$network_cidr_mask);
        $comment = "" if ! $comment;
        $route_if_descr = "" if ! $route_if_descr;

        # delete "=" and leading whitespace from $route_if_descr
        $route_if_descr =~ s/===//g;
        $route_if_descr =~ s/---//g;
        $route_if_descr =~ s/--//g;
        $route_if_descr =~ s/^\s+//g;
        $route_if_descr =~ s/\s+$//g;
        $route_if_descr =~ s/,//g;

        if ( $ascii_vrf_name ) {
            $comment .= " (VRF: $ascii_vrf_name)";
        }

		# Convert netmasks to bitmasks
        if ( $mask !~ /^\d{1,2}$/ ) {
            ($BM,$hostroute)=convert_mask("$network","$mask");
        } elsif ( $mask =~ /^\d{1,2}$/ && $mask >= 8 && $mask <= 32 ) {
            $BM=$mask;
        } else {
            next;
        }
		
		push @hostroutes,"$hostroute" if $hostroute;
		
		next if $BM eq "NOBM"; 
		
		# check if bitmask is to small
		if ( $BM < $smallest_bm4 ) {
			print LOG "$network/$BM: Bitmask to small - IGNORED\n";
			print "$network/$BM: Bitmask to small - IGNORED\n" if $verbose;
			next;
		} 

		# Add networks to all_found_redes_hash 
		$all_found_redes_hash{"$network/$BM"}++;

		# Check for overlapping networks
		my ($overlap,$overlap_red_num) = check_overlap("$network","$BM",\@all_db_networks,"1");

		next if $overlap eq "1";

		my ( $cc_id_vrf,$cc_value_net_vrf );
		if ( $get_vrf_routes ) {
			$cc_id_vrf=get_custom_column_id_from_name("$client_id","VRF") || "";
			print "DEBUG: $network: VRF CC_ID: $cc_id_vrf\n" if $debug;
			print LOG "DEBUG: $network: VRF CC_ID: $cc_id_vrf\n" if $debug;
		}

		if ( $overlap == 2 ) {
			# identical network found in db
			# CHECK IF COMMENT IS STILL CORRECT
			my $ip_int=ip_to_int("$network","v4");
			my $found_comment=${$values_redes}{$ip_int}->[6] || "";
			my $discover_device=${$values_redes}{$ip_int}->[12] || "";
			$found_comment="" if $found_comment eq "NULL";
            my $check_comment = $comment;
            $check_comment =~ s/\*/\\\*/g;

			if ( $found_comment && $found_comment !~ /$check_comment/ && $found_comment =~ /([Ll]ocal|[Ss]tatic|OSPF|ospf|RIP|rip|Dual IS-IS|Eigrp|[Oo]ther|netmgmt|icmp|egp|ggp|hello|isIs|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr|ciscoEigrp) route from/ ) {
				#update network comment
				if ( $found_comment =~ /([Ll]ocal|[Ss]tatic|OSPF|ospf|RIP|rip|Dual IS-IS|Eigrp|[Oo]ther|netmgmt|icmp|egp|ggp|hello|isIs|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr|ciscoEigrp) route from \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/ ) {
					$found_comment =~ s/,?\s?([Ll]ocal|[Ss]tatic|OSPF|ospf|RIP|rip|Dual IS-IS|Eigrp|[Oo]ther|netmgmt|icmp|egp|ggp|hello|isIs|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr|ciscoEigrp) route from \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}//;
				} elsif ( $found_comment =~ /([Ll]ocal|[Ss]tatic|OSPF|ospf|RIP|rip|Dual IS-IS|Eigrp|[Oo]ther|netmgmt|icmp|egp|ggp|hello|isIs|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr|ciscoEigrp) route from .+/ ) {
					$found_comment =~ s/,?\s?([Ll]ocal|[Ss]tatic|OSPF|ospf|RIP|rip|Dual IS-IS|Eigrp|[Oo]ther|netmgmt|icmp|egp|ggp|hello|isIs|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr|ciscoEigrp) route from .*//;
				}
				my $new_comment="";
				if ( $found_comment ) {
					$new_comment=$found_comment . ", " . $comment;
				} else {
					$new_comment=$comment;
				}
				update_red_comment( "$client_id","$overlap_red_num","$new_comment" );

				if ( $get_vrf_routes && $cc_id_vrf ) {
					$cc_value_net_vrf=get_custom_column_entry("$client_id","$overlap_red_num","VRF") || "";
					if ( $cc_value_net_vrf && $ascii_vrf_name) {
						update_custom_column_value_red("$client_id","$cc_id_vrf","$overlap_red_num","$ascii_vrf_name");
						print "DEBUG: $network: VRF column updated: $ascii_vrf_name\n" if $debug;
						print LOG "DEBUG: $network: VRF column updated: $ascii_vrf_name\n" if $debug;
					} elsif ( $ascii_vrf_name ) {
						insert_custom_column_value_red("$client_id","$cc_id_vrf","$overlap_red_num","$ascii_vrf_name");
						print "DEBUG: $network: VRF column added: $ascii_vrf_name\n" if $debug;
						print LOG "DEBUG: $network: VRF column added: $ascii_vrf_name\n" if $debug;
					}
				}
			}

            # CHECK IF DESCRIPTION (from ifDescr) IS STILL CORRECT
            my $found_descr=${$values_redes}{$ip_int}->[2] || "";
            $found_descr="" if $found_descr eq "NULL";
            my $check_descr = $route_if_descr;
            $check_descr =~ s/\*/\\\*/g;

            print "found_descr: $found_descr - $route_if_descr\n" if $debug;
            print LOG "found_descr: $found_descr - $route_if_descr\n" if $debug;

			if (  $found_descr && $check_descr && $found_descr =~ /$check_descr/ ) {
                # Do not update comment for this network for all nodes - add network to comment_was_updated if network already has a know description
                # require that the nodes are always queried in the same order.
                $comment_was_updated{"$network-$BM"}++;
                print LOG "check_descr matches found_descr - adding network $network to comment_was_updated\n" if $debug;
            } elsif ( $found_descr && $check_descr && $found_descr !~ /$check_descr/ && $check_descr !~ /\$/ && ! exists $comment_was_updated{"$network-$BM"}){
                #update network comment
                my $new_descr="";
                $found_descr =~ s/===//g;
                $found_descr =~ s/==//g;
                $found_descr =~ s/---//g;
                $found_descr =~ s/--//g;
                $found_descr =~ s/^\s+//g;
                $found_descr =~ s/\s+$//g;
                $found_descr =~ s/,{2,}//;
                $found_descr =~ s/,\s?$//;
                if ( $found_descr ne $check_descr ) {
                    $new_descr=$found_descr . ", " . $route_if_descr;
                    $new_descr =~ s/,{2,}//;
                    $new_descr =~ s/,\s?$//;
                    print "descr update 1: $found_descr - $route_if_descr - NEW: $new_descr\n" if $debug;
                    print LOG "descr update 1: $found_descr - $route_if_descr - NEW: $new_descr\n" if $debug;
                    update_red_description( "$client_id","$overlap_red_num","$new_descr" );
                    $comment_was_updated{"$network-$BM"}++;
                }

            } elsif ( ! $found_descr && $route_if_descr && ! exists $comment_was_updated{"$network-$BM"} ) {
                print "descr update 2: $found_descr - $route_if_descr\n" if $debug;
                print LOG "descr update 2: $found_descr - $route_if_descr\n" if $debug;
                update_red_description( "$client_id","$overlap_red_num","$route_if_descr" );
                $comment_was_updated{"$network-$BM"}++;
            }

			# UPDATE net discover_device
			update_red_discover_device( "$client_id","$overlap_red_num","$node") if ! $discover_device;
		}


        my $rootnet_val=0;

		# add the network to @all_db_networks to include it in the overlap check
		# for the next network
		my $l = @all_db_networks;
		$all_db_networks[$l]->[0] = $network;
		$all_db_networks[$l]->[1] = $BM;
		$all_db_networks[$l]->[2] = $rootnet_val;

		if ( $overlap != "2" ) {
			# insert networks into the database
			print LOG "$network/$BM: ADDED\n";
			print "$network/$BM: ADDED\n" if $verbose;

            $red_num = insert_networks("$network","$BM","$comment","$client_id","$set_sync_flag","v4","$rootnet_val","$route_if_descr","$force_site_id","$node");
            if ( $new_networks_file ) {
                print NET_FILE "$network/$BM\n";
            }

			if ( $get_vrf_routes && $cc_id_vrf && $ascii_vrf_name ) {
				insert_custom_column_value_red("$client_id","$cc_id_vrf","$red_num","$ascii_vrf_name");
			}

            if ( $assign_tags ) {
                foreach ( @assign_tag_ids ) {
                    Gipfuncs::insert_tag_for_object("$_", "$red_num", "network", "$gip_job_status_id");
                }
            }

			my $audit_type="17";
			my $audit_class="2";
			my $update_type_audit="3";
			my $descr="---";
			$comment="---" if ! $comment;
			my $vigilada = "n";
			my $site_audit = "---";
			my $cat_audit = "---";

			my $event="$network/$BM,$descr,$site_audit,$cat_audit,$comment,$vigilada";
			insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");

			my $ip_version="v4";
            my $red_int=ip_to_int("$network","$ip_version");
            # Add network to %values_redes 
            push @{$values_redes{"$red_int"}},"$network","$BM","$route_if_descr","-1","-1","$set_sync_flag","$comment","$ip_version","$red_int","0","$client_id","","$node";

            # Add network to %comment_was_updated 
            $comment_was_updated{"$network-$BM"}++;

		}
	}

	foreach $network_cidr_mask (@route_dests_cidr_ipv6) {
		
		$comment="";
		my ($network,$BM,$comment,$route_if_descr);
		if ( $add_comment eq "1" ) {
            ($network,$BM,$comment,$route_if_descr) = split("/",$network_cidr_mask);
		} else {
			($network,$BM) = split("/",$network_cidr_mask);
		}
        $comment = "" if ! $comment;
        $route_if_descr = "" if ! $route_if_descr;

        # delete "=" and leading whitespace from $route_if_descr
        $route_if_descr =~ s/===//g;
        $route_if_descr =~ s/---//g;
        $route_if_descr =~ s/--//g;
        $route_if_descr =~ s/^\s+//g;
        $route_if_descr =~ s/\s+$//g;
        $route_if_descr =~ s/,//g;
		
		# check if bitmask is to small
		if ( $BM < $smallest_bm6 ) {
			print LOG "$network/$BM: Bitmask to small - IGNORED\n";
			print "$network/$BM: Bitmask to small - IGNORED\n" if $verbose;
			next;
		} 

		# Add networks to all_found_redes_hash 
		$all_found_redes_hash{"$network/$BM"}++;

		my $rootnet_val="0";
		$rootnet_val=1 if $BM < 64;

		my $ignore_rootnet="1";
		if ( $rootnet_val == 1 ) {
			$ignore_rootnet="0";
		}

		my $red_exists=check_red_exists("$client_id","$network","$BM","$ignore_rootnet") || "";

		if ( $red_exists ) {
			print "$network/$BM $lang_vars{red_exists_message} - $lang_vars{ignorado_message}\n" if $verbose;
			print LOG "$network/$BM $lang_vars{red_exists_message} - $lang_vars{ignorado_message}\n" if $verbose;
			next;
		}

		# Check for overlapping networks
		my $overlap=0;
		my $overlap_red_num;
		($overlap,$overlap_red_num) = check_overlap("$network","$BM",\@all_db_networks6,"1");

		next if $overlap == "1";

		# add the network to @all_db_networks to include it in the overlap check
		# for the next network
		my $l = @all_db_networks;
		$all_db_networks[$l]->[0] = $network;
		$all_db_networks[$l]->[1] = $BM;
		$all_db_networks[$l]->[2] = $rootnet_val;

		if ( $overlap != "2" ) {
			# insert networks into the database
			print LOG "$network/$BM: ADDED\n";
			print "$network/$BM: ADDED\n" if $verbose;
			$red_num = insert_networks("$network","$BM","$comment","$client_id","$set_sync_flag","v6","$rootnet_val","$route_if_descr","$force_site_id","$node");
            if ( $new_networks_file ) {
                print NET_FILE "$network/$BM\n";
            }

			my $audit_type="17";
			my $audit_class="2";
			my $update_type_audit="3";
			my $descr="---";
			$comment="---" if ! $comment;
			my $vigilada = "n";
			my $site_audit = "---";
			my $cat_audit = "---";

			my $event="$network/$BM,$descr,$site_audit,$cat_audit,$comment,$vigilada";
			insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");
		}
	}

	if ( $import_host_routes ) {
		my @values_host_redes = get_host_redes_no_rootnet("$client_id");
		foreach my $ip( @hostroutes ) {
			print "DEBUG: HOSTROUTE: $ip\n" if $debug;
			print LOG "DEBUG: HOSTROUTE: $ip\n" if $debug;
			next if ! $ip;
			my $ip_version="v4";
			$ip_version="v6" if $ip !~ /^\d{1,3}\./;
			my $ip_int=ip_to_int("$ip","$ip_version");

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

				my $host_red = $values_host_redes[$k]->[0];
				my $host_red_bm = $values_host_redes[$k]->[1];
				my $red_num_red = $values_host_redes[$k]->[2];
				my $red_loc_red_id = $values_host_redes[$k]->[3] || -1;

				if ( $ip_version eq "v4" ) {
					$host_red =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
					my $third_host_red_oct=$3;
					$ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
					my $third_host_oct=$3;
					if (  $host_red_bm >= 24 && $third_host_red_oct != $third_host_oct ) {
						$k++;
						next;
					}
				}

				my $redob_redes = "$host_red/$host_red_bm";
				my $ipob_redes = new Net::IP ($redob_redes) or print LOG "error: $lang_vars{comprueba_red_BM_message}: $redob_redes\n";
				my $last_ip_int_red = ($ipob_redes->last_int());
				$last_ip_int_red = Math::BigInt->new("$last_ip_int_red");
				my $first_ip_int_red = ($ipob_redes->intip());
				$first_ip_int_red = Math::BigInt->new("$first_ip_int_red");

				if ( $ip_version eq "v4" ) {
					if ( ($host_red_bm >= 31 && ( $ip_int < $first_ip_int_red || $ip_int > $last_ip_int_red )) || ($host_red_bm < 31 && ( $ip_int <= $first_ip_int_red || $ip_int >= $last_ip_int_red )) )  {
						$k++;
						next;
					}
				} else {
					if ( $ip_int <= $first_ip_int_red || $ip_int >= $last_ip_int_red ) {
						$k++;
						next;
					}
				}

				# add host
				my $mydatetime=time();
				my ($added_ip,$new_hostname)=check_and_insert_host("$client_id","$ip_int","$device_name","","$red_loc_red_id","n","-1","","-1","$mydatetime","$red_num_red","1","$ip_version","$ip","$default_resolver",\@dns_servers,"$ignore_generic_auto");
				if ( $added_ip ) {
					print "Host added (/32 route): $added_ip - $new_hostname\n" if $added_ip; 
					my $audit_type="15";
					my $audit_class="1";
					my $update_type_audit="3";
					my $descr="---";
					$comment="---" if ! $comment;

					my $event="$added_ip: $new_hostname,---,---,n,---,---,---";
					insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");
				}
				$k++;
				last;
			}
		}	
	}


	if ( $process_networks_v4 && ! $route_dests_cidr[0] ) {
		print "No matching IPv4 networks found\n" if $verbose;
	}
	if (  $process_networks_v6 && ! $route_dests_cidr_ipv6[0] ) {
		print "No matching IPv6 networks found\n" if $verbose;
	}

	print "\n" if $verbose;
}

if ( $new_networks_file ) {
    close NET_FILE;
}

my @not_found_networks;
# report networks which are in the database but not longer found in the routing tables of the devices


my @global_config = get_global_config("$client_id");
my $cm_enabled_db=$global_config[0]->[8] || "";

# check if there are vlan switches
my $switch_exists = "";
my @vlan_switches_all=get_vlan_switches_all("$client_id");
#SELECT id,switches FROM vlans Wo

foreach my $ref ( @vlan_switches_all ) {
	if ( $ref->[1] ) { 
		$switch_exists = 1;
		last;
	}
}

if ( $delete_not_found_networks || $report_not_found_networks ) {
	foreach my $red_num_node ( sort keys %values_redes_node_all ) {

		my $red=$values_redes_node_all{$red_num_node}->[0];
		my $red_bm=$values_redes_node_all{$red_num_node}->[1];
		my $descr=$values_redes_node_all{$red_num_node}->[2] || "";
		my $loc=$values_redes_node_all{$red_num_node}->[3] || "";
		my $cat=$values_redes_node_all{$red_num_node}->[4] || "";
		my $vigilada=$values_redes_node_all{$red_num_node}->[5] || "";
		my $comentario=$values_redes_node_all{$red_num_node}->[6] || "";
		my $ip_version=$values_redes_node_all{$red_num_node}->[7] || "0";
		my $rootnet=$values_redes_node_all{$red_num_node}->[9] || "0";
		$descr="" if $descr eq "NULL";
		$comentario="" if $comentario eq "NULL";
		if ( $all_found_redes_hash{"$red/$red_bm"} ) {
			# red found in routing table
			next;
		} else  {
			# red found in routing table
            if ( $report_not_found_networks ) {
                print LOG "Red not found in routing tables: $red/$red_bm\n";
                print "Red not found in routing tables: $red/$red_bm\n" if $verbose;
                next;
            }

		}

		my $redob = "$red/$red_bm";
		my $ipob_red = new Net::IP ($redob);
		if ( ! $ipob_red ) {
			print LOG "Warning: Can not create IP object for $redob: $!\n";
			next;
		}

		delete_red("$client_id","$red_num_node");

		print LOG "Network deleted: $red/$red_bm (not longer found in the routing tables)\n";
		print "Network deleted: $red/$red_bm (not longer found in the routing tables)\n" if $verbose;

		my $audit_type="16";
		my $audit_class="2";
		my $update_type_audit="1";
		my $event="$red/$red_bm,$descr,$loc,$cat,$comentario,$vigilada";
		insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");


		my @linked_cc_id=get_custom_host_column_ids_from_name("$client_id","linkedIP");
		my $linked_cc_id=$linked_cc_id[0]->[0] || "";
		my %linked_cc_values=get_linked_custom_columns_hash("$client_id","$red_num_node","$linked_cc_id","$ip_version");

		if ( $linked_cc_id ) {
			foreach my $key ( keys %linked_cc_values ) {
				my $linked_ips_delete=$linked_cc_values{$key}[0];
				$linked_ips_delete =~ s/^X:://;
				my $ip_ad=$linked_cc_values{$key}[1];
				my $host_id=$linked_cc_values{$key}[2];
				my @linked_ips=split(",",$linked_ips_delete);
				foreach my $linked_ip_delete(@linked_ips){
					delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
				}
			}
		}

		if ( $rootnet == 0 ) {
			my $redint=($ipob_red->intip());
			$redint = Math::BigInt->new("$redint");
			my $first_ip_int = $redint + 1;
			my $last_ip_int = ($ipob_red->last_int());
			$last_ip_int = Math::BigInt->new("$last_ip_int");
			$last_ip_int = $last_ip_int - 1;


			my $first_ip_int_del=$first_ip_int;
			my $last_ip_int_del=$last_ip_int;
			if ( $ip_version eq "v4" && $red_bm >= 31 ) {
				$first_ip_int_del--;
				$last_ip_int_del++;
			}
			if ($ip_version eq "v6" ) {
				$first_ip_int_del--;
				$last_ip_int_del++;
			}

			my ($host_hash_ref,$host_sort_helper_array_ref)=get_host_hash_from_rednum("$client_id","$red_num_node");
			my @switches;
			my @switches_new;

		   if ( $switch_exists ) {
				foreach my $host_id ( keys %$host_hash_ref ) {
					@switches = get_vlan_switches_match("$client_id","$host_id");
					my $i = 0;
					foreach ( @switches ) {
						my $vlan_id = $_->[0];
						my $switches = $_->[1];
						$switches =~ s/,$host_id,/,/;
						$switches =~ s/^$host_id,//;
						$switches =~ s/,$host_id$//;
						$switches =~ s/^$host_id$//;
						$switches_new[$i]->[0]=$vlan_id;
						$switches_new[$i]->[1]=$switches;
						$i++;
					}

					foreach ( @switches_new ) {
						my $vlan_id_new = $_->[0];
						my $switches_new = $_->[1];
						update_vlan_switches("$client_id","$vlan_id_new","$switches_new");
					}
				}
			}

			# delete custom host column entries
			delete_custom_column_entry("$client_id","$red_num_node");
			if ( $cm_enabled_db ) {
				delete_device_cm_host_id("$client_id","", "$red_num_node");
				delete_other_device_job("$client_id","", "$red_num_node");
			}

			delete_custom_host_column_entry_from_rednum("$client_id","$red_num_node");
			delete_ip("$client_id","$first_ip_int_del","$last_ip_int_del","$ip_version","$red_num_node");

			my @rangos=get_rangos_red("$client_id","$red_num_node");
			my $i=0;
			foreach ( @rangos ) {
				my $range_id = $rangos[$i]->[0];
				my $start_ip_int = "";
				$start_ip_int = Math::BigInt->new("$start_ip_int");
				$start_ip_int=$rangos[$i]->[1];
				my $end_ip_int=$rangos[$i]->[2];
			#   $end_ip_int = Math::BigInt->new("$end_ip_int");
				my $range_comentario = $rangos[$i]->[3] if $rangos[$i]->[3];
				my $range_red_num = $rangos[$i]->[5];

				delete_range("$client_id","$range_id") if $range_red_num eq "$red_num_node";

				my $audit_type="18";
				my $audit_class="2";
				my $update_type_audit="9";
				my $start_ip_audit = int_to_ip("$client_id","$start_ip_int","$ip_version");
				my $end_ip_audit = int_to_ip("$client_id","$end_ip_int","$ip_version");
				my $event="$redob:" . $start_ip_audit . "-" . $end_ip_audit;
				$event = $event . " " . $range_comentario if $range_comentario;
				insert_audit_auto("$audit_class","$audit_type","$event","$update_type_audit","$client_id");

				$i++;
			}
		}
	}
}

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


#################
## subroutines ##
#################

sub insert_networks {
    my ($network,$BM,$comment,$client_id,$set_sync_flag,$ip_version,$rootnet,$description,$site_id,$node) = @_;
		 
	$comment = '' if ! $comment;
	$description = '' if ! $description;
	$site_id = "-1" if ! $site_id;
	$rootnet = "0" if ! $rootnet;
	$node = "" if ! $node;

	if ( $set_sync_flag == 1 && $rootnet != 1 ) {
		$set_sync_flag = "y";
	} else {
		$set_sync_flag = "n";
	}

	my ($overlap,$parent_red_num) = get_parent_network("$network", "$BM","$client_id","$ip_version");

	my $dbh = mysql_connection() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $sth;

	if ( $parent_red_num ) {
		$sth = $dbh->prepare("INSERT INTO net (red,bm,descr,loc,vigilada,comentario,categoria,client_id,ip_version,rootnet,parent_network_id,discover_device) VALUES ( \"$network\", \"$BM\", \"$description\",\"$site_id\",\"$set_sync_flag\",\"$comment\",\"-1\",\"$client_id\",\"$ip_version\",\"$rootnet\",\"$parent_red_num\",\"$node\")"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	} else {
		$sth = $dbh->prepare("INSERT INTO net (red,bm,descr,loc,vigilada,comentario,categoria,client_id,ip_version,rootnet,discover_device) VALUES ( \"$network\", \"$BM\", \"$description\",\"$site_id\",\"$set_sync_flag\",\"$comment\",\"-1\",\"$client_id\",\"$ip_version\",\"$rootnet\",\"$node\")"
                                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	}
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $red_num = $sth->fetchrow_array;

    if ( $rootnet == 1 ) {
        # update parent_network_id of child networks
        my $child_networks = get_child_networks("$network", "$BM", "$red_num", "$client_id","$ip_version");
        foreach my $child_red_num ( keys %{$child_networks}) {
            my $parent_id = $child_networks->{$child_red_num}[2];
            my $qparent_id = $dbh->quote( $parent_id );
            $sth = $dbh->prepare("UPDATE net SET parent_network_id=$qparent_id WHERE red_num=$child_red_num") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

            $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        }
    }

    $sth->finish();
    $dbh->disconnect;

    return $red_num;
}


sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}

sub get_all_networks {
        my ($client_id,$ip_version) = @_;
        my @overlap_redes;
        my $ip_ref;
        my $dbh = mysql_connection() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        my $sth;
        if ( $ip_version eq "v4" ) {
            $sth = $dbh->prepare("SELECT red, BM, rootnet, red_num FROM net WHERE client_id = \"$client_id\" AND ip_version = \"$ip_version\" ORDER BY INET_ATON(red)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        } else {
                $sth = $dbh->prepare("SELECT red, BM, rootnet, red_num FROM net WHERE client_id = \"$client_id\" AND ip_version = \"$ip_version\"") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        }
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
            push @overlap_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
        my $k = 0;
        foreach (@overlap_redes) {
            my $red2 = $overlap_redes[$k]->[0];
            my $BM2 = $overlap_redes[$k]->[1];
            $k++;
       }
        return @overlap_redes;
}

sub check_overlap {
    my ( $red, $BM, $overlap_redes, $ignore_rootnet ) = @_;

	my $red_num2="";
    my $k="0";
    my $overlap = "0";
	$ignore_rootnet = 0 if ! $ignore_rootnet;
    my $ip = new Net::IP ("$red/$BM") or print LOG "$red/$BM network/bitmask INVALID - IGNORED\n";
    if ( $ip ) {
        foreach (@{$overlap_redes}) {
            my $red2 = @{$overlap_redes}[$k]->[0];
            my $BM2 = @{$overlap_redes}[$k]->[1];
			my $rootnet2 = @{$overlap_redes}[$k]->[2] || 0;
			$red_num2 = @{$overlap_redes}[$k]->[3] || "";
            my $ip2 = new Net::IP ("$red2/$BM2") or print LOG "$red2/$BM2 INVALID network/bitmask - IGNORED\n";
            if ( ! $ip2 ) {
				$k++;
				next;
			}
			if ( $ignore_rootnet == 1 && $rootnet2 == 1) {
				$k++;
				next;
			}
            if ($ip->overlaps($ip2)==$IP_A_IN_B_OVERLAP) {
                    print "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n" if $verbose;
                    print LOG "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n";
                    $overlap = "1";
                    last;
            }
            if ($ip->overlaps($ip2)==$IP_B_IN_A_OVERLAP) {
                    print "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n" if $verbose;
                    print LOG "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n";
                    $overlap = "1";
                    last;
            }
            if ($ip->overlaps($ip2)==$IP_PARTIAL_OVERLAP) {
                    print "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n" if $verbose;
                    print LOG "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n";
                    $overlap = "1";
                    last;
            }
            if ($ip->overlaps($ip2)==$IP_IDENTICAL) {
                    print "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n" if $verbose;
                    print LOG "$red/$BM overlaps with $red2/$BM2 -  IGNORED\n";
                    $overlap = "2";
                    last;
            }
            $k++;
        }

    } else {
            $overlap = "1";
    }

    return ($overlap,$red_num2);
}

sub convert_mask {
    my ($network,$mask,$x,$version) = @_;

    $x = "" if ! $x;
    $version = "v4" if ! $version;

    print "DEBUG convert_mask: $network - $mask - $x\n" if $debug && $network;
    print LOG "DEBUG convert_mask: $network - $mask - $x\n" if $debug && $network;

    if ( $mask =~ /VRF/ ) {
        $mask =~ s/::.*//;
    }

	my $BM;
	my $hostroute="";
	if ( $version eq "v4" ) {
		if ( $mask =~ /\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/ ) {
			$mask =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
			my $fi_oc = $1;
			my $se_oc = $2;
			my $th_oc = $3;
			my $fo_oc = $4;
			if ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.254" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.254") { $BM = "31"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.252" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.252" ) { $BM = "30"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.248" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.248" ) { $BM = "29"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.240" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.240" ) { $BM = "28"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.224" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.224" ) { $BM = "27"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.192" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.192" ) { $BM = "26"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.128" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.128" ) { $BM = "25"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.255.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.255.0" ) { $BM = "24"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.254.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.254.0" ) { $BM = "23"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.252.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.252.0" ) { $BM = "22"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.248.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.248.0" ) { $BM = "21"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.240.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.240.0" ) { $BM = "20"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.224.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.224.0" ) { $BM = "19"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.192.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.192.0" ) { $BM = "18"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.128.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.128.0" ) { $BM = "17"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.255.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.255.0.0" ) { $BM = "16"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.254.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.254.0.0" ) { $BM = "15"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.252.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.252.0.0" ) { $BM = "14"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.248.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.248.0.0" ) { $BM = "13"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.240.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.240.0.0" ) { $BM = "12"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.224.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.224.0.0" ) { $BM = "11"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.192.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.192.0.0" ) { $BM = "10"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.128.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.128.0.0" ) { $BM = "9"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "255.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "255.0.0.0" ) { $BM = "8"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "254.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "254.0.0.0" ) { $BM = "7"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "252.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "252.0.0.0" ) { $BM = "6"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "248.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "248.0.0.0" ) { $BM = "5"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "240.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "240.0.0.0" ) { $BM = "4"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "224.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "224.0.0.0" ) { $BM = "3"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "192.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "192.0.0.0" ) { $BM = "2"; }
			elsif ( "$fi_oc.$se_oc.$th_oc.$fo_oc" eq "128.0.0.0" || "$fo_oc.$th_oc.$se_oc.$fi_oc" eq "128.0.0.0" ) { $BM = "1"; }
			elsif ( $mask eq "255.255.255.255" ) {
				if ( $import_host_routes ) {
					$hostroute=$network
				} else {
					print "$network/$mask: HOSTROUTE - IGNORED\n" if $verbose && $network;
					print LOG "$network/$mask: HOSTROUTE - IGNORED\n" if $network;
				}
				$BM="NOBM";
			} else {
				print "$network/$mask: Bad Netmask - IGNORED\n" if $verbose && $network;
				print LOG "$network/$mask: Bad Netmask - IGNORED\n" if $network;
				$BM="NOBM";
			}
		}
	} else {
		$BM = $mask;	
	}


	if ( $x ) {
		return $BM;
	} else {
		return $BM, $hostroute;
    }
}

#sub send_mail {
#        my $mailer;
#	my $added_count=0;
#        if ( $params{smtp_server} ) {
#                $mailer = Mail::Mailer->new('smtp', Server => $params{smtp_server});
#        } else {
#                $mailer = Mail::Mailer->new("");
#        }
#        $mailer->open({ From    => "$$mail_from",
#                        To      => "$$mail_destinatarios",
#                        Subject => "Result get_networks_snmp.pl"
#                     }) or print LOG "error while sending mail: $!\n";
#        open (LOG_MAIL,"<$log") or print "can not open log file: $!\n";
#        while (<LOG_MAIL>) {
#		if ( $only_added_mail && $_ !~ /ADDED/ ) {
#			next;
#		}
#		$added_count++;
#
#                print $mailer $_;
#        }
#
#	if ( $only_added_mail && $added_count == 0 ) {
#		print $mailer "\n\nNO NEW NETWORKS ADDED\n";
#	}
#
#	if ( $report_not_found_networks ) {
#		print $mailer "\n\nNetworks which are found in the database but not in the routing tables of the devices\n";
#		foreach ( @not_found_networks ) {
#			print $mailer "$_\n" if $_;
#		}
#	}
#
#        print $mailer "\n\n\n\n\n\n\n\n\n--------------------------------\n\n";
#        print $mailer "This mail is automatically generated by GestioIP's get_networks_snmp.pl\n";
#        $mailer->close;
#        close LOG_MAIL;
#}


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

#sub get_last_audit_id {
#	my $last_audit_id;
#	my $dbh = mysql_connection() or die "$DBI::errstr\n";
#	my $sth = $dbh->prepare("SELECT id FROM audit ORDER BY (id+0) DESC LIMIT 1
#		") or die "Can not execute statement: $dbh->errstr";
#        $sth->execute() or die "Can not execute statement:$sth->errstr";
#	$last_audit_id = $sth->fetchrow_array;
#	$sth->finish();
#	$dbh->disconnect;
#	$last_audit_id || 1;
#$last_audit_id;
#}

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

sub count_clients {
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT count(*) FROM clients
                        ")  or die "Mysql ERROR: ". $DBI::errstr;
        $sth->execute()  or die "Mysql ERROR: ". $DBI::errstr;
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


sub create_snmp_session {
	my ($client_id,$node,$community,$community_type,$snmp_version,$auth_pass,$auth_proto,$auth_is_key,$priv_proto,$priv_pass,$priv_is_key,$sec_level,$UseNumeric) = @_;

	my $session;
	my $error;
    $UseNumeric = 0 if ! $UseNumeric;

	if ( $snmp_version == "1" || $snmp_version == "2" ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						UseSprintValue => 1,
						UseNumeric => $UseNumeric,
                        NonIncreasing => 1,
						Verbose => 1
						);
	} elsif ( $snmp_version == "3" && $community && ! $auth_proto && ! $priv_proto ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						UseSprintValue => 1,
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
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
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
						);
	} elsif ( $snmp_version == "3" && $auth_proto && $auth_is_key && ! $priv_proto ) {
		$session = new SNMP::Session(DestHost => $node,
						$community_type => $community,
						Version => $snmp_version,
						SecLevel => $sec_level,
						AuthMasterKey => $auth_pass,
						AuthProto => $auth_proto,
						UseSprintValue => 1,
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
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
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
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
						UseNumeric => $UseNumeric,
                        NonIncreasing => 1,
						UseSprintValue => 1,
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
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
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
                        NonIncreasing => 1,
						UseNumeric => $UseNumeric,
						);
	} else {
		$exit_message = "Can not determine SecLevel";
        exit_error("$exit_message", "$gip_job_status_id", 4);
	}

	
	print "$node: CAN NOT CONNECT\n" unless
  (defined $session);

	return $session;
}



sub create_snmp_info_session {
	my ($client_id,$node,$community,$community_type,$snmp_version,$auth_pass,$auth_proto,$auth_is_key,$priv_proto,$priv_pass,$priv_is_key,$sec_level,$mibdirs_ref,$vars_file,$debug,$snmp_port) = @_;

	my $session;
	my $error;
	$debug="0" if ! $debug;

	$snmp_port=161 if ! $snmp_port;

	my $ipversion = ip_get_version ($node) || "";
	$node="udp6:" . $node if $ipversion eq "6";

	if ( $snmp_version == "1" || $snmp_version == "2" ) {
		$session = new SNMP::Info (
			AutoSpecify => 1,
			Debug       => $debug,
			DestHost    => $node,
			$community_type => $community,
			Version     => $snmp_version,
			MibDirs     => $mibdirs_ref,
			RemotePort => $snmp_port,
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
        print "$node: CAN NOT determine SecLevel\n";
	}
	
        print "$node: CAN NOT CONNECT\n" unless
      (defined $session);


	return $session;
}


sub check_red_exists {
        my ( $client_id, $net, $BM, $ignore_rootnet ) = @_;
        my $red_check="";
        $ignore_rootnet=1 if $ignore_rootnet eq "";
        my $ignore_rootnet_expr="AND rootnet='0'";
        if ( $ignore_rootnet == 0 ) {
                $ignore_rootnet_expr="AND rootnet='1'";
        }
        my $dbh = mysql_connection();
        my $qnet = $dbh->quote( $net );
        my $qBM = $dbh->quote( $BM );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT red_num FROM net WHERE red=$qnet AND BM=$qBM AND client_id = $qclient_id $ignore_rootnet_expr
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $red_check = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $red_check;
}

sub print_help {
	my ( $exit_message ) = @_;

	$exit_message = "" if ! $exit_message;
	print $exit_message . "\n";

    print "\nusage: get_networks_snmp.pl [OPTIONS...]\n\n";
    print "-a, --ascend            Sort networks according to it's bitmask/prefix size in ascend order (bigger networks will be imported first)\n";
    print "-c, --config_file_name=config_file_name	    Name of the configuration file (without path)\n";
	print "-C, --CSV_nodes         Coma separated list of nodes to query (Example: -C 10.0.0.1,10.0.1.1)\n";
    print "-d, --descend           Sort networks according to it's bitmask/prefix size in descend order (smaller networks will be imported first)\n";
	print "-d, --delete_not_found_networks	    Delete networks which are in the database but not longer found in the routing tables of the devices\n";
    print "-f, --force_site=Site   Force Site for the new discovered networks\n";
    print "-g, --get_vrf_routes	Import VRF routes (only Cisco devices supporting MPLS-VPN-MIB or MPLS-L3VPN-STD-MIB) (requires SNMP version 2c)\n";
    print "-h, --help              help\n";
    print "-i, --import_host_routes	Import /32 routes as hosts\n";
    print "-j                      Add the interface description/alias as description for new discovered networks (local routes only)\n";
    print "-k, --k=[Descr|Alias]   Specify if ifDescr or ifAlias should be used as description of new discovered networks (local routes only) (default: Alias)\n";
    print "-l, --log=logfile       Logfile\n";
    print "-m, --mail              Send the result by mail (mail_destinatarios)\n";
    print "-n, --nodes_file=snmp_targets		File with a list of devices which should be queried to find new networks (without path). Default: snmp_targets\n";
	print "-o, --only_added_mail   Send only a summary for new added networks by mail\n";
	print "-r, --report_not_found_networks	    Report networks which are in the database but not longer found in the routing tables of the devices\n";
    print "-s, --snmp_port=port-nr SNMP port to connect to (default: 161)\n";
	print "-S, --Set_sync_flag     Set sync flag for new discovered networks\n";
	print "-t, --tag               Execute the discovery against devices with this tags (Example: -t tag1,tag2,tag3)\n";
	print "-U                      Add a comments like \"Local route from 192.168.214.33\" to the new discovered networks\n\n";
    print "-v, --verbose           Verbose\n";
    print "-w, --write_new_to_file=FILE   Write new found networks to FILE (without path). File will be stored in /usr/share/gestioip/var/data/\n";
    print "-x, --x                 Debug\n";
    print "-y, --y=list            Route types to import ([local|static|other|ospf|rip|isis|eigrp|netmngt|icmp|egp|ggp|hello|esIs|ciscoIgrp|bbnSpfIgp|bgp|idpr])\n";
    print "                        Comma separated list. Default: local,static,other\n\n";

    print "Options to overwrite values from the configuration file:\n";
    print "-A client\n";
    print "-B ignore_generic_auto ([yes|no])\n";
    print "-D snmp_version ([1|2|3])\n";
    print "-E snmp_community_string\n";
    print "-F snmp_user_name\n";
    print "-G sec_level ([noAuthNoPriv|authNoPriv|authPriv])\n";
    print "-H auth_proto ([MD5|SHA])\n";
    print "-I auth_pass\n";
    print "-J priv_proto ([DES|3DES|AES])\n";
    print "-K priv_pass\n";
    print "-M logdir\n";
    print "-O actualize_ipv6 ([yes|no]), Default: no\n";
	print "-T actualize_ipv4 ([yes|no]), Default: yes\n";
    print "\nconfiguration file: $conf\n\n" if $conf;
    exit 1;
}


sub check_and_insert_host {
	my ( $client_id, $ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $ip,$default_resolver,$dns_servers,$ignore_generic_auto,$device_name ) = @_;

	my @values_host;
	$hostname="" if ! $hostname;

	my $return_ip="";

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
        $sth = $dbh->prepare("SELECT id,hostname,range_id FROM host h WHERE ip=$qip_int AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @values_host, [ @$ip_ref ];
	}

	my $id=$values_host[0]->[0];
	my $hostname_found=$values_host[0]->[1] || "unknown";
	$hostname_found = $hostname if $hostname && $hostname ne "unknown";
	my $range_id=$values_host[0]->[2] || -1;

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

	if ( ! $id ) {
		print "DEBUG: SUB: NO ID: $ip\n" if $debug;
		print LOG "DEBUG: SUB: NO ID: $ip\n" if $debug;
		$return_ip=$ip;
		# Insert host
		$sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,ip_version,client_id) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qip_version,$qclient_id)"
				) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	} elsif ( $id && $range_id != -1 && $hostname_found eq "unknown") {
		# IP from reserved range
		print "DEBUG: SUB: RESERVED RANGE: $ip\n" if $debug;
		print LOG "DEBUG: SUB: RESERVED RANGE: $ip\n" if $debug;
		$return_ip=$ip if ! $values_host[0]->[1];
		$sth = $dbh->prepare("UPDATE host set hostname=$qhostname, last_update=$qmydatetime, alive=$qalive, last_response=$qlast_response WHERE id=$id"
				) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	} else { 
		# entry exists
		print "DEBUG: SUB: ENTRY EXISTS: $ip\n" if $debug;
		print LOG "DEBUG: SUB: ENTRY EXISTS: $ip\n" if $debug;
	}

        $sth->finish();
        $dbh->disconnect;

	print "DEBUG: SUB: RETURN: $return_ip, $hostname_found\n" if $debug;
	print LOG "DEBUG: SUB: RETURN: $return_ip, $hostname_found\n" if $debug;

	return ($return_ip,$hostname_found) if $return_ip;
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


sub get_redes_hash {
	my ( $client_id,$ip_version,$return_int,$client_only, $keytype, $no_rootnet, $rootnet_only, $node ) = @_;

	my $ip_ref;
	$ip_version = "" if ! $ip_version;
	$return_int = "" if ! $return_int;
	$keytype = "" if ! $keytype;
    $node = "" if ! $node;

	my %values_redes;
    my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );
	my $qnode = $dbh->quote( $node );

	my $client_expr="";
	my $no_rootnet_expr="";
	my $rootnet_only_expr="";
	my $node_expr="";
	$client_expr="AND n.client_id=$qclient_id" if $client_only;
	$no_rootnet_expr="AND n.rootnet=0" if $no_rootnet;
	$rootnet_only_expr="AND n.rootnet=1" if $rootnet_only;
	$node_expr="AND n.discover_device=$qnode" if $node;

	my $ip_version_expr="";
	$ip_version_expr="AND n.ip_version='$ip_version'" if $ip_version;

#    my $tag_expr = "";
#    if ( $tag ) {
#        $tag_expr = " AND red_num IN ( SELECT net_id from tag_entries_network WHERE (";
#        foreach my $item ( @${tag} ) {
#            $tag_expr .= " name=$item OR";
#        }
#        $tag_expr =~ s/OR$//;
#        $tag_expr .= " ))";
#    }


	my $sth = $dbh->prepare("SELECT n.red_num, n.red, n.BM, n.descr, l.loc, n.vigilada, n.comentario, c.cat, n.ip_version, INET_ATON(n.red), n.rootnet, n.client_id, n.parent_network_id, n.discover_device FROM net n, categorias_net c, locations l WHERE c.id = n.categoria AND l.id = n.loc $ip_version_expr $client_expr $no_rootnet_expr $rootnet_only_expr $node_expr");
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $red_num = $ip_ref->{'red_num'} || "";
		my $red = $ip_ref->{'red'} || "";
		my $BM = $ip_ref->{'BM'};
		my $descr = $ip_ref->{'descr'};
		my $loc = $ip_ref->{'loc'} || "";
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
				$red_int = ip_to_int("$red","$ip_version");
			}
		}
		my $rootnet=$ip_ref->{'rootnet'};
		my $client_id=$ip_ref->{'client_id'};
		my $parent_network_id=$ip_ref->{'parent_network_id'} || "";
		my $discover_device=$ip_ref->{'discover_device'} || "";

		if ( $keytype eq "netbm" ) {
			push @{$values_redes{"$red/$BM"}},"$red","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$client_id","$parent_network_id","$discover_device";
		} elsif ( $keytype eq "redint" ) {
			push @{$values_redes{"$red_int"}},"$red","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$client_id","$parent_network_id","$discover_device";
		} else {
			push @{$values_redes{$red_num}},"$red","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$client_id","$parent_network_id","$discover_device";
		}
	}

    $dbh->disconnect;
    return \%values_redes;
}

sub update_red_comment {
	my ( $client_id, $red_num, $comment ) = @_;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qcomment = $dbh->quote( $comment );
	my $sth = $dbh->prepare("UPDATE net SET comentario=$qcomment WHERE red_num=$qred_num"
		) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}

sub update_red_discover_device {
	my ( $client_id, $red_num, $val ) = @_;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qval = $dbh->quote( $val );
	my $sth = $dbh->prepare("UPDATE net SET discover_device=$qval WHERE red_num=$qred_num"
		) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}


sub update_red_description {
    my ( $client_id, $red_num, $descr ) = @_;
    my $dbh = mysql_connection();
    my $qred_num = $dbh->quote( $red_num );
    my $qdescr = $dbh->quote( $descr );
    my $sth = $dbh->prepare("UPDATE net SET descr=$qdescr WHERE red_num=$qred_num"
        ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
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

sub get_global_config {
    my ( $client_id ) = @_;
    my @values_config;
    my $ip_ref;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT version, default_client_id, confirmation, mib_dir, vendor_mib_dirs, ipv4_only, as_enabled, leased_line_enabled, configuration_management_enabled, cm_backup_dir, cm_licence_key, cm_log_dir, cm_xml_dir, auth_enabled, freerange_ignore_non_root, arin_enabled, local_filter_enabled, site_management_enabled, password_management_enabled, dyn_dns_updates_enabled, acl_management_enabled FROM global_config");
        $sth->execute();
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_config, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_config;
}


sub check_mib_dir {
    my ( $client_id,$vars_file,$mib_dir,$vendor_mib_dirs ) = @_;

    my @global_config = get_global_config("$client_id");
    $mib_dir=$global_config[0]->[3] || "" if ! $mib_dir;
    if ( ! -e $mib_dir ) {
        exit_error("MIB direcory not found: $mib_dir", "$gip_job_status_id", 4);
    }
    $vendor_mib_dirs=$global_config[0]->[4] || "" if ! $vendor_mib_dirs;

    my @vendor_mib_dirs = split(",",$vendor_mib_dirs);
    my @mibdirs_array;
    foreach ( @vendor_mib_dirs ) {
        my $mib_vendor_dir = $mib_dir . "/" . $_;
        if ( ! -e $mib_vendor_dir ) {
            print "Mib dir does not exist: $mib_vendor_dir\n";
            print LOG "Mib dir does not exist: $mib_vendor_dir\n";
            next;
        } elsif ( ! -r $mib_vendor_dir ) {
            print "Mib dir not readable: $mib_vendor_dir\n";
            print LOG "Mib dir not readable: $mib_vendor_dir\n";
            next;
        }
        push (@mibdirs_array,$mib_vendor_dir);
        if ( ! @mibdirs_array ) {
            exit_error("MIB direcory not found: $mib_dir", "$gip_job_status_id", 4);
        }
    }

    return \@mibdirs_array;
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

sub get_tag_hosts {
    my ( $client_id, $tag ) = @_;

    my @values;
    my $ip_ref;

    my $tag_expr = "";
    if ( $tag ) {
        my %tags = get_tag_hash("$client_id", "name");
        $tag_expr = " AND id IN ( SELECT host_id from tag_entries_host WHERE (";
        foreach my $item ( @${tag} ) {
			if ( ! defined $tags{$item}->[0] ) {
				$exit_message = "\n$item: Tag NOT FOUND - ignored\n\n";
                exit_error("$exit_message", "$gip_job_status_id", 4);
			}
			$tag_expr .= " tag_id=\"$tags{$item}->[0]\" OR";
        }
        $tag_expr =~ s/OR$//;
        $tag_expr .= " ))";
    }

    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT id, inet_ntoa(ip), ip, ip_version FROM host WHERE ( client_id = $qclient_id OR client_id = '9999' ) $tag_expr") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{'id'};
        my $ip_version = $ip_ref->{'ip_version'};
		my ($ip, $ip_int);
		if ( $ip_version eq "v4" ) {
			$ip=$ip_ref->{'inet_ntoa(ip)'};
		} else {
			$ip_int = $ip_ref->{'ip'};
			# macht die sache langsam ....
			$ip = int_to_ip($ip_int,"$ip_version");
		}

		push @values, $ip;
    }

    $dbh->disconnect;

    return @values;

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
    my ( $client_id, $id, $object, $snmp_group_id_arg  ) = @_;

    my ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port);
    $snmp_version=$community=$snmp_user_name=$sec_level=$auth_proto=$auth_pass=$priv_proto=$priv_pass=$community_type=$auth_is_key=$priv_is_key=$snmp_port="";

	my $exit = 0;
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
            print "SNMP Group not found\n";
            print_help();
        }
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

        print "Using SNMP Group: $snmp_group_name\n" if $verbose;
        print LOG "Using SNMP Group: $snmp_group_name\n" if $verbose;

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
                exit_error("$exit_message", "$gip_job_status_id", 4);
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
                exit_error("$exit_message", "$gip_job_status_id", 4);
            }

            if ( $sec_level eq "authNoPriv" && ! $auth_proto ) {
                $exit_message = "Please configure parameter \"auth_proto\"";
                $exit = 1;
            } elsif ( $sec_level eq "authNoPriv" && ! $auth_pass ) {
                $exit_message = "Please configure parameter \"auth_pass\"";
                $exit = 1;
            } elsif ( $sec_level eq "authPriv" && ! $auth_proto ) {
                $exit_message = "Please configure parameter \"auth_proto\"";
                $exit = 1;
            } elsif ( $sec_level eq "authPriv" && ! $auth_pass ) {
                $exit_message = "Please configure parameter \"auth_pass\"";
                $exit = 1
            } elsif ( $sec_level eq "authPriv" && ! $priv_proto ) {
                $exit_message = "Please configure parameter \"priv_proto\"";
                $exit = 1;
            } elsif ( $sec_level eq "authPriv" && ! $priv_pass ) {
                $exit_message = "Please configure parameter \"priv_pass\"";
                $exit = 1;
            }

            my $auth_pass_length=length($auth_pass);
            if ( $sec_level ne "noAuthNoPriv" && $auth_pass_length < 8 ) {
                $exit_message = "auth_pass must contain at least 8 characters\n";
                $exit = 1;
            }
            my $priv_pass_length=length($auth_pass);
            if ( $sec_level ne "noAuthNoPriv" && $priv_pass_length < 8 ) {
                $exit_message = "priv_pass must contain at least 8 characters\n";
                $exit = 1;
            }

			if ( $exit == 1 ) {
                exit_error("$exit_message", "$gip_job_status_id", 4);
			}
        }
	}

    if ( ! $snmp_version ) {
            print "Parameter \"snmp_version\" missing\n";
            exit 1;
    } elsif ( $snmp_version !~ /^1|2|3$/ ) {
            print "Wrong \"snmp version\"\n";
            exit 1;
    }
    if ( ! $community ) {
            print "Please configure parameter \"snmp_community_string\"\n" if $snmp_version ne "3";
            print "Please configure parameter \"snmp_user_name\"\n" if $snmp_version eq "3";
            exit 1;
    }

	if ( $exit == 1 ) {
        exit_error("$exit_message", "$gip_job_status_id", 4);
	}

    $community_type="Community";
    if ( $snmp_version == "3" ) {
            $community_type = "SecName";
    }


    return ($snmp_version, $community, $snmp_user_name, $sec_level, $auth_proto, $auth_pass, $priv_proto, $priv_pass, $community_type, $auth_is_key, $priv_is_key, $snmp_port)
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

sub get_parent_network {
    my ( $red, $BM, $client_id, $ip_version ) = @_;

    my $rednum_overlap = "";
    my $overlap = 0;
    my $error = "";
    my $ip = new Net::IP ("$red/$BM") or $error = "$red/$BM INVALID network/bitmask - IGNORED";
    return if ! $ip;

    my $overlap_redes = get_redes_hash("$client_id","$ip_version","","client_only");

    my $sort_order_ref = sub {
        # bigger BM first
        my ($X, $Y);
        $X = $overlap_redes->{$a}[1];
        $Y = $overlap_redes->{$b}[1];
        $Y <=> $X;
    };

    foreach my $red_num2 ( sort  $sort_order_ref keys %{$overlap_redes}) {
        $error = "";
        my $rootnet2 = $overlap_redes->{$red_num2}[9] || 0;
        if ( $rootnet2 != 1 ) {
            next;
        }

        my $red2 = $overlap_redes->{$red_num2}[0];
        my $BM2 = $overlap_redes->{$red_num2}[1];
        my $ip2 = new Net::IP ("$red2/$BM2") or $error = "$red2/$BM2 INVALID network/bitmask - IGNORED";
        if ( ! $ip2 ) {
            next;
        }

        if ($ip->overlaps($ip2)==$IP_A_IN_B_OVERLAP) {
                $overlap = "1";
                $rednum_overlap = $red_num2;
                last;
        }
    }

    return ($overlap,$rednum_overlap);
}


sub get_child_networks {
    my ( $red, $BM, $red_num, $client_id, $ip_version ) = @_;

    my %values;
    my %values_change;
    my $error = "";
    my $ip = new Net::IP ("$red/$BM") or $error = "$red/$BM INVALID network/bitmask - IGNORED";
    return if ! $ip;

    my $overlap_redes = get_redes_hash("$client_id","$ip_version","","client_only");

    my $sort_order_ref = sub {
        my ($X, $Y);
        $X = $overlap_redes->{$a}[1];
        $Y = $overlap_redes->{$b}[1];
        $Y <=> $X;
    };

    foreach my $red_num2 ( sort $sort_order_ref keys %{$overlap_redes}) {

        $error = "";
        my $red2 = $overlap_redes->{$red_num2}[0];
        my $BM2 = $overlap_redes->{$red_num2}[1];
        my $parent_network_id2 = $overlap_redes->{$red_num2}[11] || "";
        my $parent_network_BM2;
        if ( $parent_network_id2 ) {
            $parent_network_BM2 = $overlap_redes->{$parent_network_id2}[1];
        } else {
            $parent_network_BM2 = "";
        }
        my $ip2 = new Net::IP ("$red2/$BM2") or $error = "$red2/$BM2 INVALID network/bitmask - IGNORED";
        if ( ! $ip2 ) {
            next;
        }
        if ($ip->overlaps($ip2)==$IP_B_IN_A_OVERLAP) {
                push @{$values{$red_num2}},"$red2","$BM2","$parent_network_id2","$parent_network_BM2";
        }
    }

    foreach my $red_num_child ( sort $sort_order_ref keys %values) {
        my $red_child = $values{$red_num_child}[0];
        my $BM_child = $values{$red_num_child}[1];
        my $BM_child_parent = $values{$red_num_child}[3];
        if ( $BM_child_parent ) {
            if ( $BM_child_parent < $BM ) {
                # childs parent network has a smaller BM than new network > change childs parent_network_id
                push @{$values_change{$red_num_child}},"$red_child","$BM_child","$red_num";
            }
        } else {
            #childs without_parent_network_id
            push @{$values_change{$red_num_child}},"$red_child","$BM_child","$red_num";
        }
    }

    return \%values_change;
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
#	print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug && fileno LOG;
	my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}

sub exit_error {
    my ( $message, $gip_job_status_id, $status ) = @_;

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;

    if ( $gip_job_status_id && ! $combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

        my $time=time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close LOG  if fileno LOG;
    exit 1;
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



sub delete_red {
	my ( $client_id, $red, $rootnet, $red_num, $red_ip, $BM ) = @_;

	$rootnet = 0 if ! $rootnet;
	my $dbh = mysql_connection();
	my $qred = $dbh->quote( $red );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth;
	if ( $red =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
			$red_num = get_red_id_from_red("$client_id","$red") if ! $red_num;
	} elsif ( $red =~ /^\d{1,5}$/ ) {
			$red_num = $red;
	} else { 
		print LOG "Networks was not deleted: $red/$BM - $red_num\n";
		return;
	}

	my $qred_num = $dbh->quote( $red_num );

	$sth = $dbh->prepare("DELETE FROM net WHERE red_num=$qred_num AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth = $dbh->prepare("DELETE FROM tag_entries_network WHERE net_id=$qred_num") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	delete_tag_entry_object_obj_id("$client_id", "$red_num", "network");


	# update child networks
	if ( $rootnet == 1 ) {
		my @child_networks = get_child_networks_by_parent_id("$client_id","$red_num");

		my $i = 0;
		foreach (@child_networks ) {
			my $child_red = $child_networks[$i]->[0];
			my $child_bm = $child_networks[$i]->[1];
			my $child_red_num = $child_networks[$i]->[3];
			my $child_ip_version = $child_networks[$i]->[9];
			my ($overlap,$parent_network_id) = get_parent_network("$child_red", "$child_bm","$client_id","$child_ip_version");
			$parent_network_id = "" if ! $parent_network_id;
			my $qparent_network_id = $dbh->quote( $parent_network_id );
			my $qchild_red_num = $dbh->quote( $child_red_num );
			$sth = $dbh->prepare("UPDATE net SET parent_network_id=$qparent_network_id WHERE red_num=$qchild_red_num") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
			$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
			$i++;
		}
	}

	$sth->finish();
	$dbh->disconnect;
}


sub get_custom_host_column_ids_from_name {
	my ( $client_id, $column_name ) = @_;
	my $dbh = mysql_connection();
	my @values;
	my $ip_ref;
	my $qcolumn_name = $dbh->quote( $column_name );
	my $sth;
	$sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcolumn_name") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @values, [ @$ip_ref ];
	}
	$dbh->disconnect;
	return @values;
}


sub get_linked_custom_columns_hash {
	my ( $client_id,$red_num,$cc_id,$ip_version ) = @_;
	my %cc_values;
	my $ip_ref;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qcc_id = $dbh->quote( $cc_id );
	my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT ce.cc_id,ce.pc_id,ce.host_id,ce.entry,h.ip,INET_NTOA(h.ip),h.ip_version FROM custom_host_column_entries ce, host h WHERE ce.cc_id=$qcc_id AND ce.host_id=h.id AND ce.host_id IN ( select id from host WHERE red_num=$qred_num ) AND (h.client_id = $qclient_id OR h.client_id = '9999')")
    or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_hashref ) {
    my $ip="";
    my $ip_int = $ip_ref->{'ip'};
    # ignore ip_version argument an use ip_version from query
    my $ip_version= $ip_ref->{'ip_version'};
    if ( $ip_version eq "v4" ) {
        $ip = $ip_ref->{'INET_NTOA(h.ip)'};
    } else {
        $ip = int_to_ip("$client_id","$ip_int","$ip_version");
        $ip = ip_compress_address ($ip, 6);
    }
    my $entry = $ip_ref->{entry};
    my $host_id = $ip_ref->{host_id};
    push @{$cc_values{$ip_int}},"$entry","$ip","$host_id";
    }
    $dbh->disconnect;
    return %cc_values;
}


sub delete_linked_ip {
    my ( $client_id,$ip_version,$linked_ip_old,$ip,$host_id_linked ) = @_;

    my $ip_version_ip_old;
    if ( $linked_ip_old =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $ip_version_ip_old="v4";
    } else {
        $ip_version_ip_old="v6";
    }

    #   my $cc_name="linked IP";
    my $cc_name="linkedIP";
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

sub update_custom_host_column_value_host_modip {
	my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;

	my $error;
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

	my $error;
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





sub get_vlan_switches_match {
	my ( $client_id,$switch_host_id ) = @_;

	my $error;
	my @switches;
	my $ip_ref;
	my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT id,switches FROM vlans WHERE ( switches LIKE \"%,$switch_host_id,%\" OR switches REGEXP \"^$switch_host_id,\" OR switches REGEXP \",$switch_host_id\$\" OR switches = \"$switch_host_id\" ) AND client_id=$qclient_id
		") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @switches, [ @$ip_ref ];
	}
	$sth->finish();
	$dbh->disconnect;
	return @switches;
}


sub delete_custom_column_entry {
	my ( $client_id, $red_num ) = @_;

	my $error;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id IN ( SELECT id FROM host WHERE red_num = $qred_num AND client_id = $qclient_id )") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth = $dbh->prepare("DELETE FROM custom_net_column_entries WHERE net_id = $qred_num"
                            ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}


sub delete_device_cm_host_id {
    my ( $client_id, $host_id, $red_num ) = @_;

    $host_id = "" if ! $host_id;
    $red_num = "" if ! $red_num;
    my $error;
	my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth;
    if ( $red_num ) {
        my $qred_num = $dbh->quote( $red_num );
        $sth = $dbh->prepare("DELETE FROM device_cm_config WHERE host_id IN (select id from host where red_num=$qred_num)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("DELETE FROM device_cm_config WHERE host_id=$host_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}


sub delete_other_device_job {
	my ( $client_id,$id, $red_num ) = @_;

    $red_num = "" if ! $red_num;

    my $error;
	my $dbh = mysql_connection();
    my $qid = $dbh->quote( $id );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth;
    if ( $red_num ) {
        my $qred_num = $dbh->quote( $red_num );
        $sth = $dbh->prepare("DELETE FROM device_jobs WHERE host_id IN (select id from host where red_num=$qred_num)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    } else {
        $sth = $dbh->prepare("DELETE FROM device_jobs WHERE id = $qid") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    }

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}


sub delete_ip {
    my ( $client_id, $first_ip_int, $last_ip_int,$ip_version, $red_num ) = @_;

    my $error;
	my $dbh = mysql_connection();
    my $qfirst_ip_int = $dbh->quote( $first_ip_int );
    my $qlast_ip_int = $dbh->quote( $last_ip_int );
    my $qip_version = $dbh->quote( $ip_version );
    my $qclient_id = $dbh->quote( $client_id );

    my $match;
    if ( $first_ip_int eq $last_ip_int ) {
        $match = "ip=$qfirst_ip_int";
    } elsif ( $ip_version eq "v4" ) {
        $match="CAST(ip AS UNSIGNED) BETWEEN $qfirst_ip_int AND $qlast_ip_int";
    } else {
        $match="ip BETWEEN $qfirst_ip_int AND $qlast_ip_int";
    }

    my $red_num_expr = "";
    if ( $red_num ) {
        my $qred_num = $dbh->quote( $red_num );
        $red_num_expr = "AND red_num=$qred_num";
    }

    my $sth = $dbh->prepare("DELETE FROM host WHERE ip_version=$qip_version AND $match AND client_id = $qclient_id $red_num_expr") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->finish();
    $dbh->disconnect;
}


sub delete_custom_host_column_entry_from_rednum {
	my ( $client_id, $red_num ) = @_;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id IN ( SELECT id FROM host WHERE red_num = $qred_num AND client_id = $qclient_id )"
				) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->finish();
	$dbh->disconnect;
}


sub get_rangos_red {
	my ($client_id,$red_num)=@_;

	my $error;
	my $ip_ref;
	my @rangos;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qclient_id = $dbh->quote( $client_id );
		my $sth = $dbh->prepare("SELECT id,start_ip,end_ip,comentario,range_type,red_num FROM ranges WHERE red_num = $qred_num AND client_id = $qclient_id ORDER BY start_ip") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    while ( $ip_ref = $sth->fetchrow_arrayref ) {
    push @rangos, [ @$ip_ref ];
    }
    $dbh->disconnect;
    return @rangos;
}


sub delete_range {
	my ( $client_id, $range_id, $preserve_hosts ) = @_;

	my $error;
	my $dbh = mysql_connection();
	my $qrange_id = $dbh->quote( $range_id );
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("DELETE FROM ranges WHERE id = $qrange_id AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	if ( $preserve_hosts ) {
		$sth = $dbh->prepare("UPDATE host SET range_id='-1' WHERE hostname != '' AND range_id = $qrange_id AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

		$sth = $dbh->prepare("DELETE FROM host WHERE hostname='' AND range_id = $qrange_id AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	} else {
		$sth = $dbh->prepare("DELETE FROM host WHERE range_id = $qrange_id AND client_id = $qclient_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	}

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->finish();
	$dbh->disconnect;
}


sub get_vlan_switches_all {
	my ( $client_id ) = @_;
	my @switches;
	my $ip_ref;
	my $dbh = mysql_connection();
	my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT id,switches FROM vlans WHERE client_id=$qclient_id
		") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute();
	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @switches, [ @$ip_ref ];
	}
	$sth->finish();
	$dbh->disconnect;
	return @switches;
}


sub get_red_id_from_red {
	my ( $client_id, $red, $rootnet, $BM ) = @_;

	my $error;
	my $red_id;
	my $dbh = mysql_connection();
	my $qred = $dbh->quote( $red );
	my $qclient_id = $dbh->quote( $client_id );

	my $rootnet_expr="AND rootnet = 0";
	$rootnet_expr="AND rootnet = 1" if $rootnet;

	my $BM_expr="";
	$BM_expr="AND BM=$BM" if $BM;

	my $sth = $dbh->prepare("SELECT red_num FROM net WHERE red=$qred AND client_id=$qclient_id $rootnet_expr $BM_expr") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	$red_id = $sth->fetchrow_array || "";
	$sth->finish();
	$dbh->disconnect;
	return $red_id;
}

sub delete_tag_entry_object_obj_id {
	my ( $client_id, $obj_id, $object ) = @_;

	my $dbh = mysql_connection();
	my $ip_ref;
	my $qobj_id = $dbh->quote( $obj_id );

	my ($table, $col_name);
	if ( $object eq "network" ) {
		$table = "tag_entries_network";
		$col_name = "net_id";
	} elsif ( $object eq "host" ) {
		$table = "tag_entries_host";
		$col_name = "host_id";
	}

	my $sth = $dbh->prepare("DELETE FROM $table WHERE $col_name=$qobj_id
					") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}

sub get_child_networks_by_parent_id {
    my ( $client_id, $parent_network_id ) = @_;
    my @values;
    my $ip_ref;
	my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qparent_network_id = $dbh->quote( $parent_network_id );
    my $sth = $dbh->prepare("SELECT n.red, n.BM, n.descr, n.red_num, l.loc, n.vigilada, n.comentario, c.cat, n.client_id, n.ip_version, n.rootnet, n.parent_network_id FROM net n, locations l , categorias_net c WHERE l.id = n.loc AND n.categoria = c.id AND n.client_id = $qclient_id and parent_network_id=$qparent_network_id;") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $dbh->disconnect;
    $sth->finish();

    return @values;
}

sub get_custom_host_columns_from_net_id_hash {
	my ( $client_id,$host_id ) = @_;

	my $error;
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

sub get_custom_host_column_entry {
	my ( $client_id, $host_id, $cc_name, $pc_id ) = @_;

	my $dbh = mysql_connection();
	my $qhost_id = $dbh->quote( $host_id );
	my $qcc_name = $dbh->quote( $cc_name );
	my $qpc_id = $dbh->quote( $pc_id );
	my $qclient_id = $dbh->quote( $client_id );
		my $sth = $dbh->prepare("SELECT cce.entry from custom_host_column_entries cce, custom_host_columns cc, predef_host_columns pc WHERE cc.name=$qcc_name AND cce.host_id = $qhost_id AND cce.cc_id = cc.id AND cc.column_type_id= pc.id AND pc.id = $qpc_id AND cce.client_id = $qclient_id
                    ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $entry = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $entry;
}

sub get_host_hash_from_rednum {
	my ( $client_id,$red_num ) = @_;

	my %values_ip = ();
	my $ip_ref;
	my $dbh = mysql_connection();
	my $qred_num = $dbh->quote( $red_num );
	my $qclient_id = $dbh->quote( $client_id );

	my $sth;
	$sth = $dbh->prepare("SELECT h.ip, INET_NTOA(h.ip),h.hostname, h.host_descr, h.comentario, h.range_id, h.id, h.red_num, h.ip_version FROM host h WHERE $red_num=$qred_num AND h.client_id = $qclient_id ORDER BY h.ip")
		or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
		$sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

	my $i=0;
	my $j=0;
	my $k=0;
	while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $ip_version = $ip_ref->{'ip_version'};
		my $hostname = $ip_ref->{'hostname'} || "";
		my $range_id = $ip_ref->{'range_id'} || "";
		next if ! $hostname;
		my $ip_int = $ip_ref->{'ip'} || "";
		my $ip;
		if ( $ip_version eq "v4" ) {
			$ip = $ip_ref->{'INET_NTOA(h.ip)'};
		} else {
			$ip = int_to_ip("$client_id","$ip_int","$ip_version");
		}
		my $host_descr = $ip_ref->{'host_descr'} || "";
		my $comentario = $ip_ref->{'comentario'} || "";
		my $id = $ip_ref->{'id'} || "";
		my $red_num = $ip_ref->{'red_num'} || "";
		push @{$values_ip{$id}},"$ip","$hostname","$host_descr","$comentario","$range_id","$ip_int","$red_num","$client_id","$ip_version";
	}

    $dbh->disconnect;

    return \%values_ip;
}

