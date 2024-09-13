#!/usr/bin/perl -w

# Copyright (C) 2011 Marc Uebel

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

# Version 3.5.6 20210330

use strict;
use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
	$dir = $Bin;
    $gipfunc_path = $dir . '/include';
}

use lib "$gipfunc_path";
use lib '/var/www/gestioip/modules';
use Gipfuncs;
use GestioIP;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use Socket;
use SNMP::Info;
use Fcntl qw(:flock);
use Net::IP;
use Net::IP qw(:PROC);


my $gip = GestioIP -> new();

my $VERSION="3.5.0";
my $CHECK_VERSION="3";

$dir =~ /^(.*)\/bin/;
$base_dir=$1;

my ( $test, $mail, $help, $version_arg, $client_id, $lang, $gip_config_file, $ini_devices, $user, $client, $nodes_file, $tag, $gip_job_id, $combined_job, $verbose, $debug, $document_root, $log, $snmp_group_arg, $run_once, $smtp_server, $mail_from, $mail_to, $changes_only);
$test=$mail=$help=$version_arg=$client_id=$lang=$gip_config_file=$ini_devices=$user=$client=$snmp_group_arg=$nodes_file=$tag=$gip_job_id=$combined_job=$verbose=$debug=$document_root=$log=$run_once=$smtp_server=$mail_from=$mail_to=$changes_only="";

GetOptions(
    "log=s"=>\$log,
	"snmp_group=s"=>\$snmp_group_arg,
#	"community=s"=>\$community,
	"id_client=s"=>\$client_id,
    "changes_only!"=>\$changes_only,
    "combined_job!"=>\$combined_job,
#	"snmp_version=s"=>\$snmp_version,
	"lang=s"=>\$lang,
	"user=s"=>\$user,
	"devices=s"=>\$ini_devices,
    "CSV_nodes=s"=>\$ini_devices,
	"document_root=s"=>\$document_root,
    "nodes_file=s"=>\$nodes_file,
	"Version!"=>\$version_arg,
	"gestioip_config=s"=>\$gip_config_file,
    "tag=s"=>\$tag,
	"mail!"=>\$mail,

	"smtp_server=s"=>\$smtp_server,
	"mail_from=s"=>\$mail_from,
	"mail_to=s"=>\$mail_to,

	"verbose!"=>\$verbose,
	"run_once!"=>\$run_once,
	"help!"=>\$help,
	"x!"=>\$debug,

#	"n=s"=>\$auth_proto,
#	"o=s"=>\$auth_pass,
#	"t=s"=>\$priv_proto,
#	"q=s"=>\$priv_pass,
#	"r=s"=>\$sec_level,
    "A=s"=>\$client,
    "W=s"=>\$gip_job_id,
) or print_help();

my $enable_audit = "1";

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
$client_id=get_client_id_from_name("$client") || "";
if ( ! $client_id ) {
    print "$client: client not found\n";
    exit 1;
}

my $vars_file = "";

my $job_name = "";
if ( $gip_job_id ) {

	my $job_status = Gipfuncs::check_disabled("$gip_job_id");
    if ( $job_status != 1 ) {
        exit;
    }

    if ( ! $run_once ) {
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
        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user");
	}
}

if ( $help ) { print_help(); }
if ( $version_arg ) { print_version(); }

$verbose = 1 if $debug;

my $exit_message = "";

my $start_time=time();

my $logdir = "";
my $datetime;
my $gip_job_status_id = "2";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "ip_import_vlans");

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;

my $gip_job_id_message = "";
$gip_job_id_message = ", Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime ip_import_vlans.pl LOG $gip_job_id_message\n\n";
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


$lang = "en" if ! $lang;

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

if ( ! $snmp_group_arg ) {
	$exit_message = "Parameter \"snmp_group\" missing - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}

my $lockfile = $base_dir . "/var/run/" . $client . "_ip_update_gestioip_snmp.lock";

no strict 'refs';
open($lockfile, '<', $0) or exit_error("Unable to create lock file: $!", "$gip_job_status_id", 4);
use strict;

unless (flock($lockfile, LOCK_EX|LOCK_NB)) {
    $exit_message = "$0 is already running - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}

#my $pidfile = $base_dir . "/var/run/" . $client . "_ip_import_vlans.pid";
#$pidfile =~ /^(.*_ip_import_vlans.pid)$/;
#$pidfile = $1;
#open(PID,">$pidfile") or exit_error("Unable to create pid file $pidfile: $!", "$gip_job_status_id", 4);
#print PID $$;
#close PID;

$SIG{'TERM'} = $SIG{'INT'} = \&do_term;


#if ( ! -r $gip_config_file ) {
##	unlink("$pidfile");
#    $exit_message = "config_file $gip_config_file not readable - exiting";
#	exit_error("$exit_message", "$gip_job_status_id", 4 );
#}
if ( ! $user ) {
    print STDERR "Warning: Parameter \"user\" missing\n";
}

$client_id=get_client_id_from_name("$client") || "";


my $new_vlan_count = "0";
my $all_vlan_count = "0";

my $gip_version=get_version();

#if ( $gip_version !~ /^$CHECK_VERSION/ ) {
#    print LOG "\nScript and GestioIP version are not compatible\n\nGestioIP version: $gip_version - script version: $VERSION\n\n";
#	mod_ini_stat("$new_vlan_count");
#    exit 1;
#}

my @global_config = get_global_config("$client_id");
my $mib_dir=$global_config[0]->[3] || "";
my $vendor_mib_dirs=$global_config[0]->[4] || "";

my @vendor_mib_dirs = split(",",$vendor_mib_dirs);
my @mibdirs_array;
foreach ( @vendor_mib_dirs ) {
    my $mib_vendor_dir = $mib_dir . "/" . $_;
    if ( ! -e $mib_vendor_dir ) {
#        mod_ini_stat("$new_vlan_count");
#		unlink("$pidfile");
        $exit_message = "MIB directory does not exit: $mib_vendor_dir - exiting";
		exit_error("$exit_message", "$gip_job_status_id", 4 );
        if ( ! -r $mib_vendor_dir ) {
#			unlink("$pidfile");
            $exit_message = "MIB directory not readable: $mib_vendor_dir - exiting";
			exit_error("$exit_message", "$gip_job_status_id", 4 );
        }
    }
    push (@mibdirs_array,$mib_vendor_dir);

}

my $mibdirs_ref = \@mibdirs_array;

my @snmp_group_values = get_snmp_parameter("$client_id","$snmp_group_arg");
my $snmp_version = $snmp_group_values[0]->[2];
my $snmp_port = $snmp_group_values[0]->[3] || 161;
my $community = $snmp_group_values[0]->[4];
my $snmp_user_name = $snmp_group_values[0]->[5] || "";
my $sec_level = $snmp_group_values[0]->[6] || "";
my $auth_proto = $snmp_group_values[0]->[7] || "";
my $auth_pass = $snmp_group_values[0]->[8] || "";
my $priv_proto = $snmp_group_values[0]->[9] || "";
my $priv_pass = $snmp_group_values[0]->[10] || "";
$community = $snmp_user_name if $snmp_version eq 3;

if ( ! $community ) {
#	unlink("$pidfile");
    $exit_message = "No SNMP Community string found - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}
if ( ! $snmp_version ) {
#	unlink("$pidfile");
    $exit_message = "No SNMP version found - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}
my $community_type="Community";
if ( $snmp_version == "3" ) {
	$community_type = "SecName";
}

my @nodes;
my $no_node_additional_message = "";
if ( $ini_devices ) {
	$ini_devices =~ s/^\s*//;
	$ini_devices =~ s/[\s\n\t]*$//;

	@nodes = split(",",$ini_devices);

} elsif ( $nodes_file ) {
	$nodes_file="snmp_targets" if ! $nodes_file;
	$nodes_file="$base_dir/etc/${nodes_file}";

    open(IN,"<$nodes_file") or exit_error("Can't open $nodes_file: $!", "$gip_job_status_id", 4);

    my $i=0;

    while (<IN>) {
        my $node = $_;
        next if $node =~ /^#/;
        next if $node !~ /.+/;
        chomp ($node);
        $nodes[$i]=$node;
        $i++;
    }
	close IN;
} elsif ( $tag ) {
	#TAGs
    $tag =~ s/\s//g;
    my @tag = split(",", $tag);
    my $tag_ref = \@tag;

    @nodes = get_tag_hosts("$client_id", $tag_ref);

    $no_node_additional_message = "(no nodes with TAG(s) $tag found)" if ! @nodes;
}

if ( ! $nodes[0] ) {
#	unlink("$pidfile");
    $exit_message = "\nNo nodes to query found $no_node_additional_message";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
}

my $new_net_count="0";
my $node;

my $asso_vlan_reverse_hash=get_asso_vlan_reverse_hash_ref("$client_id");

my $new_vlan="0";
my $ip_version="";

foreach ( @nodes ) {

	$node=$_;

	my $valid_v6=check_valid_ipv6("$node") || "0";
	if ( $valid_v6 == "1" ) {
		$ip_version="v6";
	} elsif ( $node =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$/ ) {
		$ip_version="v4";
	} else {
		print LOG "$node: IP invalid\n";
		next;
	}

	$new_vlan_count="0";

	$node=$_;

	my $node_int=ip_to_int("$node","$ip_version") || "";
	my $node_id=get_host_id_from_ip_int("$client_id","$node") || "";

#	my $bridge=$gip->create_snmp_info_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","","$priv_proto","$priv_pass","","$sec_level",$mibdirs_ref,"$gip_vars_file");
    my $bridge=create_snmp_info_session("$client_id","$node","$community","$community_type","$snmp_version","$auth_pass","$auth_proto","","$priv_proto","$priv_pass","","$sec_level",$mibdirs_ref,"","$snmp_port");

	if ( ! $bridge ) {
		print LOG "\n+++ Importing VLANs from $node +++\n";
		print LOG "\n$node: Can't connect or device doesn't support required OIDs\n";
#		mod_ini_stat("$new_vlan_count");
		next;
	}

	my @vlans_with_assos=get_vlans_with_asso_vlans("$client_id");

	my $device_type_info=$bridge->model() || "";
	my $device_vendor=$bridge->vendor() || "";
	if ( $device_type_info && $device_vendor ) {
		print LOG "\n+++ Importing VLANs from $node ($device_vendor - $device_type_info) +++\n\n";
	} else {
		print LOG "\n+++ Importing VLANs from $node +++\n\n";
	}

	my $cisco_index = $bridge->cisco_comm_indexing();

	if ( $cisco_index == 0 ) {
#		print "NONE CISCO\n";
		my $vlan_name=$bridge->qb_v_name();
		my $interfaces = $bridge->interfaces();
		my $vlans = $bridge->i_vlan_membership();
		my $vlan_numbers=$bridge->v_index();
		
		foreach my $v_num(keys %$vlan_numbers) {
			my $updated="0";
			my $found="0";
			my $vlan_descr = $vlan_name->{"$v_num"};
			my $vlan_num=$v_num;
			my $vlan_name=$vlan_descr;
			next if ! $vlan_num || ! $vlan_name;
			my $comment = "";
			foreach ( @vlans_with_assos ) {
				my $found_vlan_id=$_->[0];
				my $found_vlan_num=$_->[1];
				my $found_vlan_name=$_->[2];
				next if ! $found_vlan_num || ! $found_vlan_name;
				if ( $vlan_num eq $found_vlan_num && $vlan_name eq $found_vlan_name ) {
					$found='1';
					my $switches=get_vlan_switches("$client_id","$found_vlan_id") || "";
					if ( ! $switches && $node_id ) {
						update_vlan_switches("$client_id","$found_vlan_id","$node_id");
						$updated="1";
					} else {
						my @switches_array=split(",",$switches);
						foreach ( @switches_array ) {
							#UPDATE VLAN switch info
							if ( $node_id && $switches !~ /^$node_id$/ && $switches !~ /^$node_id,/ && $switches !~ /,$node_id$/ &&  $switches !~ /,$node_id,/ ) {
								update_vlan_switches("$client_id","$found_vlan_id","$switches,$node_id");
								$updated="1";
							}
							if ( $asso_vlan_reverse_hash->{"$found_vlan_id"}[0] ) {
								my $asso_vlan_id=$asso_vlan_reverse_hash->{"$found_vlan_id"}[1] || "";
								my $asso_vlan_switches = get_vlan_switches("$client_id","$asso_vlan_id");
								if ( $node_id && $asso_vlan_switches !~ /^$node_id$/ && $asso_vlan_switches !~ /^$node_id,/ && $asso_vlan_switches !~ /,$node_id$/ &&  $asso_vlan_switches !~ /,$node_id,/ ) {
									$asso_vlan_switches= $asso_vlan_switches . "," . $node_id;
									update_vlan_switches_by_id("$client_id","$asso_vlan_id","$asso_vlan_switches");
									$asso_vlan_reverse_hash->{"$found_vlan_id"}[0] = $asso_vlan_switches;
								}
							}
						}
					}
				}
				last if $found == 1;
			}
			if ( $found == "1" && $updated != "1" ) {
				print LOG "$vlan_num - $vlan_name: VLAN exists - ignored\n";
				$new_vlan="1";
				next;
			} elsif ( $found == "1" && $updated == "1" ) {
				print LOG "$vlan_num - $vlan_name: VLAN exists - switch info updated\n";
				$new_vlan="1";
			}
			next if $updated == "1";

			if ( $vlan_num && $vlan_name ) {
				insert_vlan("$client_id","$vlan_num","$vlan_name","$comment","-1","black","white","$node_id");
				print LOG "$vlan_name - $vlan_num - VLAN added\n";
				$new_vlan="1";
				$new_vlan_count++;

				my $audit_type="36";
				my $audit_class="7";
				my $update_type_audit="7";
				my $event="$vlan_num, $vlan_name";
				$event=$event . "," . $comment if $comment;
				$event=$event . " (community: public)" if $community eq "public";
#				insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user");
			        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user");

			}

		}

	} else {
#		print "CISCO\n";
		my $interfaces = $bridge->interfaces();
		my $vlans      = $bridge->i_vlan_membership();
		my $vlan_name=$bridge->v_name();
		my $vlan_index=$bridge->v_index();

		foreach my $key(%$vlan_index) {
			my $found="0";
			my $updated="0";
			my $newkey = $key;
			next if ! $$vlan_name{$key};
			if ( $newkey =~ /^\d\.\d+/ ) {
				$newkey =~ s/^\d\.//;
			}
			my $vlan_num=$newkey;
			my $vlan_name=$$vlan_name{$key};
			next if ! $vlan_num || ! $vlan_name;
			my $comment = "";

			foreach ( @vlans_with_assos ) {
				my $found_vlan_id=$_->[0];
				my $found_vlan_num=$_->[1];
				my $found_vlan_name=$_->[2];
				next if ! $found_vlan_num || ! $found_vlan_name;
				if ( $vlan_num eq $found_vlan_num && $vlan_name eq $found_vlan_name ) {
					$found='1';
					my $switches=get_vlan_switches("$client_id","$found_vlan_id") || "";
					if ( ! $switches ) {
						update_vlan_switches("$client_id","$found_vlan_id","$node_id");
						$updated="1";
						$new_vlan="1";
					} else {
						my @switches_array=split(",",$switches);
						foreach ( @switches_array ) {
							#UPDATE VLAN switch info
							if ( $switches !~ /^$node_id$/ && $switches !~ /^$node_id,/ && $switches !~ /,$node_id$/ &&  $switches !~ /,$node_id,/ ) {
								update_vlan_switches("$client_id","$found_vlan_id","$switches,$node_id");
								$updated="1";
							}
							if ( $asso_vlan_reverse_hash->{"$found_vlan_id"}[0] ) {
								my $asso_vlan_id=$asso_vlan_reverse_hash->{"$found_vlan_id"}[1] || "";
								my $asso_vlan_switches = "";
								$asso_vlan_switches = get_vlan_switches("$client_id","$asso_vlan_id") if $asso_vlan_id;
								if ( $node_id && $asso_vlan_switches !~ /^$node_id$/ && $asso_vlan_switches !~ /^$node_id,/ && $asso_vlan_switches !~ /,$node_id$/ &&  $asso_vlan_switches !~ /,$node_id,/ ) {
									$asso_vlan_switches= $asso_vlan_switches . "," . $node_id;
									update_vlan_switches_by_id("$client_id","$asso_vlan_id","$asso_vlan_switches");
									$asso_vlan_reverse_hash->{"$found_vlan_id"}[0] = $asso_vlan_switches;
								}
							}
						}
					}
				}
				last if $found == 1;
			}

			if ( $found == "1" && $updated != "1" ) {
				print LOG "$vlan_num - $vlan_name: VLAN exists - ignored\n";
				$new_vlan="1";
				next;
			} elsif ( $found == "1" && $updated == "1" ) {
				print LOG "$vlan_num - $vlan_name: VLAN exists - switch info updated\n";
				$new_vlan="1";
			}
			next if $updated == "1";

			if ( $vlan_num && $vlan_name ) {
				insert_vlan("$client_id","$vlan_num","$vlan_name","$comment","-1","black","white","$node_id");
				print LOG "$vlan_name - $vlan_num - VLAN added\n";
				$new_vlan="1";
				$new_vlan_count++;

				my $audit_type="36";
				my $audit_class="7";
				my $update_type_audit="7";
				my $event="$vlan_num, $vlan_name";
				$event=$event . "," . $comment if $comment;
				$event=$event . " (community: public)" if $community eq "public";
#				insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user");
			        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file","$user");
			}
		}
	}

	#change ini_stat.html
#	mod_ini_stat("$new_vlan_count");
	print LOG "\nFound $new_vlan_count new VLANs\n";
	$all_vlan_count= $all_vlan_count + $new_vlan_count

}

my $end_time=time();
my $duration=$end_time - $start_time;
my @parts = gmtime($duration);
my $duration_string = "";
$duration_string = $parts[2] . "h, " if $parts[2] != "0";
$duration_string = $duration_string . $parts[1] . "m";
$duration_string = $duration_string . " and " . $parts[0] . "s";

print LOG "\nFound a total of $all_vlan_count new VLANs (execution time: $duration_string)\n\n";
close LOG;

Gipfuncs::send_mail (
    debug       =>  "$debug",
    mail_from   =>  $mail_from,
    mail_to     =>  \@mail_to,
    subject     => "Restult Job $job_name",
    smtp_server => "$smtp_server",
    smtp_message    => "",
    log         =>  "$log",
    gip_job_status_id   =>  "$gip_job_status_id",
    changes_only   =>  "$changes_only",
) if $mail;

if ( $gip_job_id && ! $combined_job ) {
    update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
}

print "Job successfully finished\n";
exit 0;


#unlink("$pidfile");


####################
### subroutines ####
####################

sub print_help {}

#sub get_config {
#        my ( $client_id ) = @_;
#        my @values_config;
#        my $ip_ref;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
#        my $qclient_id = $dbh->quote( $client_id );
#        my $sth = $dbh->prepare("SELECT smallest_bm,max_sinc_procs,ignorar,ignore_generic_auto,generic_dyn_host_name,dyn_ranges_only,ping_timeout FROM config WHERE client_id = $qclient_id") or die ("Can not execute statement:<p>$DBI::errstr");
#        $sth->execute() or die ("Can not execute statement:<p>$DBI::errstr");
#        while ( $ip_ref = $sth->fetchrow_arrayref ) {
#        push @values_config, [ @$ip_ref ];
#        }
#        $dbh->disconnect;
#        return @values_config;
#}

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}

sub get_version {
        my $val;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT version FROM global_config");
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_global_config {
        my ( $client_id ) = @_;
        my @values_config;
        my $ip_ref;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT version, default_client_id, confirmation, mib_dir, vendor_mib_dirs FROM global_config") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_config, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values_config;
}

sub get_asso_vlan_reverse_hash_ref {
        my ( $client_id ) = @_;
        my (@values_vlans,$ip_ref);
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my %vlans;
        my $sth = $dbh->prepare("SELECT v.id, v.vlan_num, v.vlan_name, v.comment, vp.name, v.switches, v.asso_vlan FROM vlans v, vlan_providers vp WHERE v.asso_vlan IS NOT NULL AND ( v.client_id=$qclient_id || v.client_id='9999' ) order by (vlan_num+0)");
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $vlan_id = $ip_ref->{'id'};
                my $switches = $ip_ref->{'switches'};
                my $asso_vlan_id = $ip_ref->{'asso_vlan'};
                push @{$vlans{"$vlan_id"}},"$switches","$asso_vlan_id";

        }
        $dbh->disconnect;
        $sth->finish();
        return \%vlans;
}

sub get_host_id_from_ip_int {
        my ( $client_id,$ip_int,$red_num ) = @_;
        my $val;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
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

sub get_vlans_with_asso_vlans {
        my ( $client_id ) = @_;
        my (@values_vlans,$ip_ref);
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT id,vlan_num,vlan_name FROM vlans WHERE client_id=$qclient_id || client_id='9999'");
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values_vlans, [ @$ip_ref ];
        }
        $dbh->disconnect;
        $sth->finish(  );
        return @values_vlans;
}

sub get_vlan_switches {
        my ( $client_id,$vlan_id ) = @_;
        my $switches;
        my $ip_ref;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qvlan_id = $dbh->quote( $vlan_id );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT switches FROM vlans WHERE id=$qvlan_id AND client_id=$qclient_id
                ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute();
        $switches = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $switches;
}

sub update_vlan_switches {
        my ( $client_id,$vlan_id,$switches ) = @_;
        my ($id);
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qvlan_id = $dbh->quote( $vlan_id );
        my $qswitches = $dbh->quote( $switches );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("UPDATE vlans SET switches=$qswitches WHERE id=$qvlan_id AND client_id=$qclient_id
                ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute();
        $sth->finish();
        $dbh->disconnect;
}

sub insert_vlan {
        my ( $client_id, $vlan_num, $vlan_name, $comment, $vlan_provider_id, $font_color, $bg_color, $switches ) = @_;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qvlan_num = $dbh->quote( $vlan_num );
        my $qvlan_name = $dbh->quote( $vlan_name );
        my $qcomment = $dbh->quote( $comment );
        my $qvlan_provider_id = $dbh->quote( $vlan_provider_id );
        my $qfont_color = $dbh->quote( $font_color );
        my $qbg_color = $dbh->quote( $bg_color );
        my $qswitches = $dbh->quote( $switches );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("INSERT INTO vlans (vlan_num,vlan_name,comment,provider_id,bg_color,font_color,switches,client_id) VALUES ( $qvlan_num,$qvlan_name,$qcomment,$qvlan_provider_id,$qbg_color,$qfont_color,$qswitches,$qclient_id)"
                ) or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
        $dbh->disconnect;
}

#sub insert_audit {
#        my ($client_id,$event_class,$event_type,$event,$update_type_audit,$vars_file,$user) = @_;
#        my %lang_vars = $gip->_get_vars("$vars_file");
#        my $mydatetime=time();
#        my $audit_id=get_last_audit_id("$client_id");
#        $audit_id++;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
#        my $qaudit_id = $dbh->quote( $audit_id );
#        my $qevent_class = $dbh->quote( $event_class );
#        my $qevent_type = $dbh->quote( $event_type );
#        my $qevent = $dbh->quote( $event );
#        my $quser = $dbh->quote( $user );
#        my $qupdate_type_audit = $dbh->quote( $update_type_audit );
#        my $qmydatetime = $dbh->quote( $mydatetime );
#        my $qclient_id = $dbh->quote( $client_id );
#        my $sth = $dbh->prepare("INSERT IGNORE audit (id,event,user,event_class,event_type,update_type_audit,date,client_id) VALUES ($qaudit_id,$qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qclient_id)") or die "Can not execute statement:<p>$DBI::errstr";
#        $sth->execute() or die "Can not execute statement:<p>$DBI::errstr";
#        $sth->finish();
#}

sub insert_audit_auto {
        my ($client_id,$event_class,$event_type,$event,$update_type_audit,$vars_file,$user) = @_;
        my $mydatetime=time();
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $qevent_class = $dbh->quote( $event_class );
        my $qevent_type = $dbh->quote( $event_type );
        my $qevent = $dbh->quote( $event );
        my $quser = $dbh->quote( $user );
        my $qupdate_type_audit = $dbh->quote( $update_type_audit );
        my $qmydatetime = $dbh->quote( $mydatetime );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("INSERT IGNORE audit_auto (event,user,event_class,event_type,update_type_audit,date,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
}


sub get_last_audit_id {
        my ($client_id) = @_;
        my $last_audit_id;
#        my $dbh = $gip->_mysql_connection("$gip_config_file");
		my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT id FROM audit ORDER BY (id+0) DESC LIMIT 1
                        ") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $last_audit_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        $last_audit_id || 1;
        return $last_audit_id;
}


sub do_term {
#    unlink("$pidfile");
    $exit_message = "Got TERM Signal - exiting";
	exit_error("$exit_message", "$gip_job_status_id", 4 );
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
    $sth->finish();

    return @values;
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


sub get_snmp_parameter {
    my ( $client_id, $snmp_group_arg ) = @_;

	my $snmp_group_id = get_snmp_group_id_from_name("$client_id","$snmp_group_arg");
	my @snmp_group_values = get_snmp_groups("$client_id","$snmp_group_id");

    return @snmp_group_values;
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
                $exit_message = "\n$item: Tag NOT FOUND - ignored";
                if ( $gip_job_status_id ) {
                    exit_error("$exit_message", "$gip_job_status_id", 4 )
                } else {
                    my $exit_message = "\n$item: Tag NOT FOUND - ignored";
                    print "$exit_message\n";
                    print LOG "$exit_message\n";
                    exit 1;
                }
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
    print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug && fileno LOG;
    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}


sub exit_error {
    my ( $message, $gip_job_status_id, $status ) = @_;

    if ( $delete_job_error ) {
        $gip_job_status_id = 5 if $gip_job_status_id == 3;
    }

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;

    if ( $gip_job_status_id && ! $combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

        my $time = time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close LOG if fileno LOG;

    exit 1;
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

sub check_valid_ipv6 {
    my ($ip) = @_;
    my $valid = ip_is_ipv6("$ip");

    # 1 if valid
    return $valid;
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

sub delete_cron_entry {
    my ($id) = @_;

    $ENV{PATH} = "";

    my $crontab = "/usr/bin/crontab";

    my $echo = "/bin/echo";

    my $grep = "/bin/grep";

	my $command = $crontab . ' -l | ' . $grep . ' -v \'#ID: ' . $id . '\' | ' . $crontab . ' -';

    my $output = `$command 2>&1`;
    if ( $output ) {
        return $output;
    }
}



__DATA__
