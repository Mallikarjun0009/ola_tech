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

# This script fetches all devices from PRTG and creats URL entries for the devices

# 20160426 3.2.6.12

# Usage: ./fetch_prtg_hosts.pl --help

# execute it from cron. Example crontab (usage with [DocumentRoot]/gestioip/priv/prtg.conf):
# 30 10 * * * /usr/share/gestioip/bin/fetch_prtg_hosts.pl -s https://prtg.paessler.com -x -o > /dev/null 2>&1

# (usage without [DocumentRoot]/gestioip/priv/prtg.conf):
# 30 10 * * * /usr/share/gestioip/bin/fetch_prtg_hosts.pl -s https://prtg.paessler.com  -u demo -p demodemo -x -o > /dev/null 2>&1


use strict;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use DBI;
use Time::Local;
use Time::HiRes qw(sleep);
use Date::Calc qw(Add_Delta_Days);
use Date::Manip qw(UnixDate);
use Net::IP;
use Net::IP qw(:PROC);
use Net::Ping::External qw(ping);
use Mail::Mailer;
use Socket;
use FindBin qw($Bin);
use Net::DNS;
use POSIX;
use LWP::UserAgent;
use XML::Parser;
use XML::Simple;
use Data::Dumper;
use Math::BigInt;


my $conf="/usr/share/gestioip/etc/ip_update_gestioip.conf";
my $cm_conf_dir="/usr/share/gestioip/etc/cm_predef/";


my ( $verbose, $debug, $help, $server, $user, $pass, $ignore_certificate_errors, $overwrite_comment, $add_comment, $delete_old_url, $eliminate_hosts, $cm, $filter );
$delete_old_url = $eliminate_hosts = "";

GetOptions(
        "add_comment!"=>\$add_comment,
        "cm!"=>\$cm,
        "help!"=>\$help,
        "delete_old_url!"=>\$delete_old_url,
        "filter=s"=>\$filter,
        "eliminate_hosts!"=>\$eliminate_hosts,
        "ignore_certificate_errors!"=>\$ignore_certificate_errors,
        "overwrite_comment!"=>\$overwrite_comment,
        "pass=s"=>\$pass,
        "server=s"=>\$server,
        "user=s"=>\$user,
        "verbose!"=>\$verbose,
        "x!"=>\$debug,
) or print_help();

print_help() if $help;

# You can specify the PRTG server parameters here if you do not like to
# specify them as arguments.
### EDIT ####

$server="" if ! $server;
$user="" if ! $user;
$pass="" if ! $pass;

### EDIT END ####


if ( ! $server ) {
	print "\nPlease specify the PRTG server (https://servername)\n\n";
	print_help();
}
if ( $server !~ /^(http:|https:)/ ) {
	print "\nServer argument must start with http:// or https:// (e.g. https://prtg.my.org)\n\n";
	print_help();
}
$server =~ s/\/$//;
if ( ! $user ) {
	print "\nPlease specify a username for the PRTG server\n\n";
	print_help();
}
if ( ! $pass ) {
	print "\nPlease specify a password for the PRTG user\n\n";
	print_help();
}
if ( $cm && ! -e $cm_conf_dir ) {
	print "\n$cm_conf_dir does not exists\n\n";
	print_help();
}

$debug=0 if ! $debug;
$verbose=1 if $debug;

print "Debugging enabled\n" if $debug;


my %params;
open(VARS,"<$conf") or die "Can no open $conf: $!\n";
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

my $client_name_conf = $params{client};
my $client_id=get_client_id_from_name("$client_name_conf") || "";

if ( ! $client_id ) {
        print "$client_name_conf: Client not found: $client_name_conf - Check parameter 'client' in $conf\n";
        exit 1;
}

# open logfile
my ($s, $mm, $h, $d, $m, $y) = (localtime) [0,1,2,3,4,5];
$m++;
$y+=1900;
if ( $d =~ /^\d$/ ) { $d = "0$d"; }
if ( $s =~ /^\d$/ ) { $s = "0$s"; }
if ( $m =~ /^\d$/ ) { $m = "0$m"; }
if ( $mm =~ /^\d$/ ) { $mm = "0$mm"; }

my $log_date="$y$m$d$h$mm$s";
my $mydatetime = "$y-$m-$d $h:$mm:$s";

my $logfile_name = $log_date . "_" . $client_name_conf . "_fetch_prtg_host.log";
my $log="/usr/share/gestioip/var/log/" . $logfile_name;

open(LOG,">$log") or die "Can not open logfile: $log: $!\n";

print "Logfile: $log\n" if $verbose;

# fetch cm config
my %cm_params;
my %cm_param_hash;
my %cm_host_hash;
my @filters;
my ($device_type_group_id, $device_user_group, $device_user_group_id, $cm_server, $cm_server_id, $cm_connection_protocol, $cm_connection_port, $save_unsaved_configuration, $job_name, $job_description, $job_group_id, $cm_hosts);
if ( $cm ) {
    if ( ! $filter ) {
        print "\nPlease specify a CM filter (or a comma separated list of filters)\n";
        print_help();
    }

    print "CM configuration enabled\n" if $verbose;
    print LOG "CM configuration enabled\n" if $verbose;

    @filters = split(",",$filter);
    for my $ele ( @filters ) {
        print "FILTER: $ele\n" if $debug;
        print LOG "FILTER: $ele\n" if $debug;
        my $cm_conf = $cm_conf_dir . $ele . ".conf";
        open(VARS,"<$cm_conf") or die "Can no open $cm_conf: $!\n";
        while (<VARS>) {
                chomp;
                s/#.*//;
                s/^\s+//;
                s/\s+$//;
                next unless length;
                my ($var, $value) = split(/\s*=\s*/, $_, 2);
                $cm_params{$var} = $value;
        }
        close VARS;

        $device_type_group_id = $cm_params{device_type_group_id} || "";
        $device_user_group = $cm_params{device_user_group} || "";
        $device_user_group_id = get_device_user_group_id_from_name("$device_user_group") || "";
        $cm_server = $cm_params{backup_server} || "";
        $cm_server_id = get_cm_server_id_from_name("$cm_server") || "";
        if ( ! $device_type_group_id ) {
            print "\nCan not find id for device_type_group_id \"$device_user_group\"\n";
            print_help();
        }
        if ( ! $device_user_group_id ) {
            print "\nCan not find id for device_user_group \"$device_user_group\"\n";
            print "\nCheck parameter in $cm_conf\n";
            print_help();
        }
        if ( ! $cm_server_id ) {
            print "\nCan not find id for backup_server \"$cm_server\"\n";
            print "\nCheck parameter in $cm_conf\n";
            print_help();
        }
        $cm_connection_protocol= $cm_params{'connection_protocol'} || "";
        if ( $cm_connection_protocol !~ /^(SSH|telnet)$/ ) {
            print "\nWrong connection protocol \"$cm_connection_protocol\". Supported values: SSH|telnet\n";
            print "\nCheck parameter in $cm_conf\n";
            print_help();
        }
        $cm_connection_port= $cm_params{'connection_port'} || "";
        if ( $cm_connection_port !~ /^\d+$/ ) {
            print "\nConnection port must be an integer. Found \"$cm_connection_port\"\n";
            print "\nCheck parameter in $cm_conf\n";
            print_help();
        }    
        $save_unsaved_configuration= $cm_params{'save_unsaved_configuration'} || 0;
        $job_name = $cm_params{'job'} || "";
        $job_description = $cm_params{'description'} || "";
        $job_group_id = $cm_params{'job_group_id'} || "";
        if ( ! $job_name ) {
            print "\nNo CM Job name found\n";
            print "\nCheck parameter in $cm_conf\n";
            print_help();
        }    

        $cm_param_hash{$ele}{device_user_group}=$device_user_group;
        $cm_param_hash{$ele}{device_user_group_id}=$device_user_group_id;
        $cm_param_hash{$ele}{device_type_group_id}=$device_type_group_id;
        $cm_param_hash{$ele}{cm_server}=$cm_server;
        $cm_param_hash{$ele}{cm_server_id}=$cm_server_id;
        $cm_param_hash{$ele}{cm_connection_protocol}=$cm_connection_protocol;
        $cm_param_hash{$ele}{cm_connection_port}=$cm_connection_port;
        $cm_param_hash{$ele}{job_name}=$job_name;
        $cm_param_hash{$ele}{job_description}=$job_description;
        $cm_param_hash{$ele}{job_group_id}=$job_group_id;
        $cm_param_hash{$ele}{save_unsaved_configuration}=$save_unsaved_configuration;

        print "UG: $device_user_group - UGID: $device_user_group_id - DGID: $device_type_group_id - CM_server: $cm_server - SID: $cm_server_id - Proto: $cm_connection_protocol - Port: $cm_connection_port - Jname: $job_name - Jdesc: $job_description - JGID: $job_group_id - Filter: $ele\n" if $debug;
        print LOG "UG: $device_user_group - UGID: $device_user_group_id - DGID: $device_type_group_id - CM_server: $cm_server - SID: $cm_server_id - Proto: $cm_connection_protocol - Port: $cm_connection_port - Jname: $job_name - Jdesc: $job_description - JGID: $job_group_id - Filter: $ele\n" if $debug;

        # Fetch CM hosts from PRTG server
        $cm_hosts = make_call (
            filter=>"$ele",
        ) || "";
        if ( ! $cm_hosts ) {
            print "\nWARNING: Filter: $ele: No host to configure CM from PRTG server received\n";
            print LOG "\nWARNING: Filter: $ele: No host to configure CM from PRTG server received\n";
            print "\nWARNING: Skipping CM configuration for $cm_conf\n";
            print LOG "\nWARNING: Skipping CM configuration for $cm_conf\n";
        } else {
               $cm_host_hash{$ele} = $cm_hosts;
        }    
    }
}



# Fetch data from PRTG
my $hosts=make_call() || "";
if ( ! $hosts ) {
    print "\nNo hosts from PRTG received\n";
	exit 1;
}


my $pc_id_url=get_predef_host_column_id("$client_id","URL");
my $cc_id_url=get_custom_host_column_id("$client_id","URL");
my $pc_id_cm=get_predef_host_column_id("$client_id","CM");
my $cc_id_cm=get_custom_host_column_id("$client_id","CM");

if ( ! $pc_id_url || ! $cc_id_url ) {
	print "\nURL column not enabled. Please enable the URL column first (manage > custom columns > insert predefined host column)\n\n";
	exit 1;
}

my $cc_url_hash;

for my $host ( keys %$hosts ) {
	my $objid = $hosts->{$host}[0];
	my $device = $hosts->{$host}[1] || "";
	my $prtg_url='PRTG::' . $server . '/device.htm?id=' . $objid . '&tabid=1' . '&username=' . $user . '&password=' . $pass;
	print "=========================\n" if $verbose;
	print "$host - $objid - $device\n" if $verbose;
	print LOG "=========================\n";
	print LOG "$host - $objid - $device\n";
    
    # Check if host is a CM host
    my $cm_host = 0;
    my $apply_filter;
    for my $ele ( @filters ) {
       if (exists($cm_host_hash{$ele}->{$objid})) {
            $cm_host = 1;
            $apply_filter = $ele;
            print "CM Host: $host ($device)- $ele - $objid\n" if $debug;
            print LOG "CM Host: $host ($device) - $ele - $objid\n" if $debug;
        }
    }

	# delete protocol (https://.....)
	$host =~ s/^.+\/\///;

	my ($ip,$ip_int);

	my $values_ip=get_host_hash_id_key("$client_id","$host") || "";

	if ( keys %$values_ip ) {
		# host found in db -> update url column
		for my $id ( keys %$values_ip ) {
			my $range_id = $values_ip->{$id}[3];
			my $hostname_db = $values_ip->{$id}[4];
			my $comment_db = $values_ip->{$id}[5] || "";
			$comment_db = "" if $comment_db eq "NULL";

			my $cc_url_hash=get_custom_host_column_values_host_id_hash("$client_id","URL","$id");

			if ( ! $hostname_db && $range_id != -1) {
				# check if host is from reserverd range
				# insert cc
				update_ip_mod_hostname("$client_id","$host","$device","$id");
				insert_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$prtg_url");

				print "Host added (reserved range): $ip - $host\n" if $verbose; 
				print LOG "Host added (reserved range): $ip - $host\n";

				my $audit_type=15; # host added
				my $audit_class=1; # host
				my $update_type_audit=14; # auto prtg
				my $event="$ip,$host,---,---,---";
				insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit");

				next;
			}

			print "DEBUG: Host found in DB: $host - $range_id - $hostname_db\n" if $debug;
			print LOG "DEBUG: Host found in DB: $host - $range_id - $hostname_db\n" if $debug;

			if ( $add_comment || $overwrite_comment ) {
				# update comment with device info
				my $device_quoted=quotemeta $device;
				my $new_comment;

				if ( $overwrite_comment ) {
					$new_comment=$device;
					print "DEBUG: overwriting comment: $host: $new_comment\n" if $debug;

					update_ip_mod_hostname("$client_id","$hostname_db","$new_comment","$id");

				} elsif ( $comment_db !~ /$device_quoted/ ) {
					$new_comment=$comment_db . ", " . $device;
					$new_comment =~ s/^,\s//;
					print "DEBUG: updateing comment: $host: $new_comment\n" if $debug;

					update_ip_mod_hostname("$client_id","$hostname_db","$new_comment","$id");
				}
			}

			if ( $cc_url_hash->{$id} ) {
				# URL entry for this IP found - update cc entry
				my $cc_value = $cc_url_hash->{$id}[0];
				my $qprtg_url=quotemeta $prtg_url;
				if ( $cc_value =~ /$qprtg_url/ ) {
					print "DEBUG: $host: URL found - ignored\n" if $debug;
					print LOG "DEBUG: $host: URL found - ignored\n" if $debug;
				} else {
                    $cc_value.="," . $prtg_url;
                    update_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$cc_value") if $cc_value;
                    print "DEBUG: update URL CC\n" if $debug;
                    print LOG "DEBUG: update URL CC\n" if $debug;
                }
			} else {
				# No URL entry for this IP found insert cc entry
				my $cc_value=$prtg_url;
				insert_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$cc_value");
				print "DEBUG: insert URL CC\n" if $debug;
				print LOG "DEBUG: insert URL CC\n" if $debug;
			}

            # CM configuration
            if ( $cm_host ) {
                #Check if host already has a CM config
                my $cc_cm_hash=get_custom_host_column_values_host_id_hash("$client_id","CM","$id");
                if ( ! $cc_cm_hash->{$id} ) {
                    # enable CM for this host if no cc CM entry is found
                    print "$id - $hostname_db: no CM configuation found - adding CM configuration\n" if $verbose;
                    print LOG "$id - $hostname_db: no CM configuation found - adding CM configuration\n" if $verbose;

                    $device_user_group = $cm_param_hash{$apply_filter}{device_user_group};
                    $device_user_group_id = $cm_param_hash{$apply_filter}{device_user_group_id};
                    $device_type_group_id = $cm_param_hash{$apply_filter}{device_type_group_id};
                    $cm_server = $cm_param_hash{$apply_filter}{cm_server};
                    $cm_server_id = $cm_param_hash{$apply_filter}{cm_server_id};
                    $cm_connection_protocol = $cm_param_hash{$apply_filter}{cm_connection_protocol};
                    $cm_connection_port = $cm_param_hash{$apply_filter}{cm_connection_port};
                    $job_name = $cm_param_hash{$apply_filter}{job_name};
                    $job_description = $cm_param_hash{$apply_filter}{job_description};
                    $job_group_id = $cm_param_hash{$apply_filter}{job_group_id};
                    $save_unsaved_configuration = $cm_param_hash{$apply_filter}{save_unsaved_configuration};

                    insert_custom_host_column_value("$client_id","$cc_id_cm","$pc_id_cm","$id","enabled");
                    insert_device_cm("$client_id","$id","$device_type_group_id","$device_user_group_id","","","","","$cm_connection_protocol","$cm_server_id","$save_unsaved_configuration","$cm_connection_port");
                    insert_other_device_jobs("$client_id","$id","$job_name","$job_group_id","$job_description","1");
                }
            }
		}
	} else {
		# host not found in db
		print "DEBUG: Host not found in DB (1): $host\n" if $debug;
		print LOG "DEBUG: Host not found in DB (1): $host if $debug\n";
		my $ip;

		my $valid;
		my $ip_version;
		my $ip_version_check;
		# Check if $host is an IP
		if ( $host =~ /^\d{1,3}\.\d{1,3}/ ) {
			$ip_version_check = "v4";
			$valid=check_valid_ip("$host","$ip_version_check") || 0;
		} else {
			$ip_version_check = "v6";
			$valid=check_valid_ip("$host","$ip_version_check") || 0;
		} 

		my @client_entries=get_client_entries("$client_id");
		my $default_resolver = $client_entries[0]->[20] || "yes";
		my @dns_servers =("$client_entries[0]->[21]","$client_entries[0]->[22]","$client_entries[0]->[23]");

		if ( $valid == 1 ) {
			# $host is an IP
			$ip_version=$ip_version_check;

			print "DEBUG: Host is IP: $host - $ip_version - $valid\n" if $debug;
			print LOG "DEBUG: Host is IP: $host - $ip_version - $valid\n" if $debug;

			$host = ip_compress_address ($host, 6) if $ip_version eq "v6";
			$ip=$host;
			$ip_int=ip_to_int("$ip","$ip_version");
			$ip_int = Math::BigInt->new("$ip_int");
		} else {
			# assume that $host is an FQDN -> get IP by DNS query
			print "DEBUG: Host is FQDN: $host\n" if $debug;
			print LOG "DEBUG: Host is FQDN: $host\n" if $debug;


			# ASSUME THAT HOST HAS A IPV4 ADDRESS
			$ip_version = "v4";


			use Net::DNS;

			my ($res_dns,$a_query);

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

			if ( $ip_version eq "v4" ) {
				$a_query = $res_dns->query("$host");
			} elsif ( $ip_version eq "v6" ) {
				$a_query = $res_dns->query("$host","AAAA");
			} else {
				print "DEBUG: Can not determe IP version (1): $ip_version\n" if $debug;
				print LOG "DEBUG: Can not determe IP version (1): $ip_version\n" if $debug;
				next;
			}


			if ( $res_dns->errorstring =~ /(query timed out|no nameservers)/ ) {
				print "DNS ERROR: $host: " . $res_dns->errorstring . "\n" if $verbose;
				print LOG "DNS ERROR: $host: " . $res_dns->errorstring . "\n" if $verbose;
			}

			if ( ! $a_query ) {
				print "DEBUG: No DNS entry for $host found - ignored\n" if $debug;
				print LOG "DEBUG: No DNS entry for $host found - ignored\n" if $debug;
				next;
			} else {
				foreach my $rr ($a_query->answer) {
					next unless $rr->type eq "A";
					$ip = $rr->address;
					print "DEBUG: IPv4 IP found: $host - $ip\n" if $debug;
					print LOG "DEBUG: IPv4 IP found: $host - $ip\n" if $debug;
				}
				foreach my $rr ($a_query->answer) {
					next unless $rr->type eq "AAAA";
					$ip = $rr->address;
					print "DEBUG: IPv6 IP found: $host - $ip\n" if $debug;
					print LOG "DEBUG: IPv6 IP found: $host - $ip\n" if $debug;
				}
			}

			if ( ! $ip ) {
				print "No DNS entry for $host found - ignored\n" if $verbose;
				print LOG "No DNS entry for $host found - ignored\n" if $verbose;
				next;
			}

			$ip_int=ip_to_int("$ip","$ip_version");
			$ip_int = Math::BigInt->new("$ip_int");
		}


		# check if $ip has already an entry in the database
		$values_ip=get_host_hash_id_key("$client_id","$ip") || "";


		my $host_was_added = 0;
		if ( keys %$values_ip ) {
			# host found in db -> update url column
			print "DEBUG: Host found in DB (1): $ip\n" if $debug;
			print LOG "DEBUG: Host found in DB (1): $ip\n" if $debug;
			for my $id ( keys %$values_ip ) {

				my $hostname_db = $values_ip->{$id}[4];
				my $comment_db = $values_ip->{$id}[5];
				$comment_db = "" if $comment_db eq "NULL";

				my $cc_url_hash=get_custom_host_column_values_host_id_hash("$client_id","URL","$id");


				if ( $add_comment || $overwrite_comment ) {
					# update comment with device info
					my $device_quoted=quotemeta $device;
					my $new_comment;

					if ( $overwrite_comment ) {
						$new_comment=$device;
						print "DEBUG: overwriting comment: $host: $new_comment\n" if $debug;

						update_ip_mod_hostname("$client_id","$hostname_db","$new_comment","$id");

					} elsif ( $comment_db !~ /$device_quoted/ ) {
						$new_comment=$comment_db . ", " . $device;
						$new_comment =~ s/^,\s//;
						print "DEBUG: updateing comment: $host: $new_comment\n" if $debug;

						update_ip_mod_hostname("$client_id","$hostname_db","$new_comment","$id");
					}
				}


				if ( $cc_url_hash->{$id} ) {
					# update cc entry
					my $cc_value = $cc_url_hash->{$id}[0];
					my $qprtg_url=quotemeta $prtg_url;
					if ( $cc_value =~ /$qprtg_url/ ) {
						print "DEBUG: $host: URL found - ignored\n" if $debug;
						print LOG "DEBUG: $host: URL found - ignored\n" if $debug;
						next;
					}
					$cc_value.="," . $prtg_url;
					update_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$cc_value") if $cc_value;
					print "DEBUG: update URL CC (1)\n" if $debug;
					print LOG "DEBUG: update URL CC (1)\n" if $debug;
				} else {
					# insert cc entry
					my $cc_value=$prtg_url;
					insert_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$cc_value");
					print "DEBUG: insert URL CC (1)\n" if $debug;
					print LOG "DEBUG: insert URL CC (1)\n" if $debug;
				}
			}
			$host_was_added=1;
			next;
		} 

		next if $host_was_added == 1;

		print "DEBUG: Host not found in DB: $ip\n" if $debug;
		print LOG "DEBUG: Host not found in DB: $ip\n" if $debug;

		my @values_host_redes = get_host_redes_no_rootnet("$client_id");
		my $network_found=0;
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
			my $red_loc_id = $values_host_redes[$k]->[3] || -1;

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
			my $ipob_redes = new Net::IP ($redob_redes) or print "ERROR: Can not create IP object - check network/BM: $redob_redes\n";
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

			$network_found=1;
			my $mydatetime=time();
			# INSERT HOST, returns "" if host was found in DB
			my $id=insert_ip_mod("$client_id","$ip_int","$host","","$red_loc_id","n","-1","$device","-1","$mydatetime","$red_num_red","1","$ip_version") || "";

			# host found in DB
			last if ! $id;

			# INSERT URL COLUMN
			insert_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$id","$prtg_url");

            # CM configuration
            if ( $cm_host ) {
                # enable CM for this host

                $device_user_group = $cm_param_hash{$apply_filter}{device_user_group};
                $device_user_group_id = $cm_param_hash{$apply_filter}{device_user_group_id};
                $device_type_group_id = $cm_param_hash{$apply_filter}{device_type_group_id};
                $cm_server = $cm_param_hash{$apply_filter}{cm_server};
                $cm_server_id = $cm_param_hash{$apply_filter}{cm_server_id};
                $cm_connection_protocol = $cm_param_hash{$apply_filter}{cm_connection_protocol};
                $cm_connection_port = $cm_param_hash{$apply_filter}{cm_connection_port};
                $job_name = $cm_param_hash{$apply_filter}{job_name};
                $job_description = $cm_param_hash{$apply_filter}{job_description};
                $job_group_id = $cm_param_hash{$apply_filter}{job_group_id};
                $save_unsaved_configuration = $cm_param_hash{$apply_filter}{save_unsaved_configuration};

                print "$id - $ip: adding CM configuration for new host\n" if $verbose;
                print LOG "$id - $ip: adding CM configuration for new host\n" if $verbose;

                insert_custom_host_column_value("$client_id","$cc_id_cm","$pc_id_cm","$id","enabled");
                insert_device_cm("$client_id","$id","$device_type_group_id","$device_user_group_id","","","","","$cm_connection_protocol","$cm_server_id","$save_unsaved_configuration","$cm_connection_port");
                insert_other_device_jobs("$client_id","$id","$job_name","$job_group_id","$job_description","1");
            }

			print "Host added: $ip - $host\n" if $verbose; 
			print LOG "Host added: $ip - $host\n"; 

			my $audit_type=15; # host added
			my $audit_class=1; # host
			my $update_type_audit=14; # auto prtg
			my $event="$ip,$host,---,---,---";
			insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit");
			$k++;
			last;
		}
		print "No network found for $ip\n" if $network_found == 0 && $verbose;
		print LOG "No network found for $ip\n" if $network_found == 0 && $verbose;
	}
}


if ( $delete_old_url ) {
	print "\nChecking for invalid PRTG URLs...\n" if $verbose;
	print LOG "\nChecking for invalid PRTG URLs...\n" if $verbose;

	my $url_vals = get_url_values_host_id_hash("$client_id");
	my %url_vals =%$url_vals;
	my %new_url_vals;


	while ( my ($host_id, $value) = each %url_vals ) {
	    print "HOST WITH PRTG URL: $host_id - $value\n" if $debug;
	    print LOG "HOST WITH PRTG URL: $host_id - $value\n" if $debug;
	    next if $value !~ /PRTG/;

	    my @urls = split(",",$value);

            my $url_found = 0;

	    foreach my $url ( @urls ) {
            if ( $url !~ /^PRTG/ ) {
                push @{$new_url_vals{"${host_id}"}},"$url";
                next;
            }

            $url =~ /id=(\d+)&/;
            my $id = $1 || "";
            if ( ! $id ) {
                next;
            }

            my $resp = make_call (
                id_url=>"$id",
            );

            if ( $resp =~ /Sorry, the selected object cannot be used here or it does not exist/i ) {
                print "URL obsolate (host $host_id): $url - Deleted\n" if $verbose;
                print LOG "URL obsolate (host $host_id): $url - Deleted\n" if $verbose;
            } else {
                push @{$new_url_vals{"${host_id}"}},"$url";
                        $url_found = 1;
            }
	    }

        if ( $url_found == 0 && $eliminate_hosts ) {
            print "NO valid PRTG URLs found for $host_id - host deleted\n" if $verbose;
            delete_custom_host_column_entry("$client_id","$host_id");
            delete_ip_host_id("$client_id","$host_id");
            # delete other URLS for this host from hash
            delete $new_url_vals{$host_id};
        }
	}


	while ( my ($host_id, $value) = each %new_url_vals ) {
        # remove duplicated entries
	    @$value = uniq(@$value);
	    my $new_url = join( ',', @$value );
	    if ( $new_url ne $url_vals{$host_id} ) {
            print "PRTG URL updated (host $host_id): $new_url (old value: $url_vals{$host_id})\n" if $debug;
            print LOG "PRTG URL updated (host $host_id): $new_url (old value: $url_vals{$host_id})\n" if $debug;
            update_custom_host_column_value("$client_id","$cc_id_url","$pc_id_url","$host_id","$new_url");
	    }
	}
}



close LOG;


#############
# subroutines
#############

sub make_call {
    my %args = @_;

    my $id_url = $args{id_url} || "";
    my $filter = $args{filter} || "";

	my $url;
	if ( $user && $pass ) {
		if ( $id_url ) {
		    $url = $server . '/device.htm?id=' . $id_url . '&tabid=1&username=' . $user . '&password=' . $pass;
		} elsif ( $filter ) {
		    $url = $server . '/api/table.xml?content=devices&output=xml&columns=objid,device,host&count=9999&filter_tags=' . $filter . '&username=' . $user . '&password=' . $pass;
		} else {
		    $url = $server . '/api/table.xml?content=devices&output=xml&columns=objid,device,host&count=9999&username=' . $user . '&password=' . $pass;
		}
	} else {
		return if $id_url;
		$url = $server . '/api/table.xml?content=devices&output=xml&columns=objid,device,host&count=9999';
	}

	print "Using URL: $url\n" if $verbose && ! $id_url;
	print LOG "Using URL: $url\n";
        my $xml;
        my $error="";
	my %hosts;


	my $ua;
	if ( $ignore_certificate_errors ) {
		$ua = LWP::UserAgent->new(
			ssl_opts => { verify_hostname => 0, SSL_verify_mode => 0x00 }, # not worried about SSL certs
			cookie_jar => {}, # keep cookies in RAM but not persistent between sessions
		);
	} else {
		$ua = LWP::UserAgent->new(
			cookie_jar => {}, # keep cookies in RAM but not persistent between sessions
		);
	}


    my $resp = $ua->get($url);

    if ($resp->is_success) {
        if ( $id_url ) {
            return $resp->content;
        } else {
            $xml = XMLin($resp->content, ForceArray=>1);
            print LOG Dumper \$xml if $debug;

            my $item=$xml->{"item"};
            foreach my $item1 ( @{$item} ) {
                my $device=$item1->{'device'}->[0];
                $device =~ s/\\'/'/g;
                my $objid=$item1->{'objid'}->[0];
                my $host=$item1->{'host'}->[0];
                if ( $filter ) {
                    push @{$hosts{$objid}},"$host","$device";
                } else {    
                    push @{$hosts{$host}},"$objid","$device";
                }    
            }
        }
	} else {
		$error=$url . " (" . $resp->status_line . ")<br>\n";
		print "ERROR: Opening $url\nCan not fetch PRTG data:" . " (" . $resp->status_line . ")\n";
		print LOG "ERROR: Opening $url\nCan not fetch PRTG data:" . " (" . $resp->status_line . ")\n";
		return;
	}

	return \%hosts;
}



sub get_host_hash_id_key {
        my ( $client_id, $host ) = @_;

        my %values_ip;
	my $ip_version;

	if ( $host =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
		$ip_version = "v4";
	} else {
		$ip_version = "v6";
	} 

	my $valid=check_valid_ip("$host","$ip_version") || 0;

	if ( $valid == 1 && $ip_version eq "v6" ) {
		$host = ip_compress_address ($host, 6);
	}


        my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $qhost = $dbh->quote( $host );
        my $sth;
	if ( $ip_version eq "v4" && $valid == 1 ) {
		$sth = $dbh->prepare("SELECT id, ip, INET_NTOA(ip), hostname, ip_version, range_id, comentario FROM host WHERE INET_NTOA(ip)=$qhost AND client_id = $qclient_id")
			or die "Can not execute statement:<p>$DBI::errstr";
	} elsif ( $ip_version eq "v6" && $valid == 1 ) {
		$sth = $dbh->prepare("SELECT id, ip, hostname, ip_version, range_id, comentario FROM host WHERE ip=$qhost AND client_id = $qclient_id")
			or die "Can not execute statement:<p>$DBI::errstr";
	} else {
		# assuming that $host is a hostname
		$sth = $dbh->prepare("SELECT id, ip, INET_NTOA(ip), hostname, ip_version, range_id, comentario FROM host WHERE hostname=$qhost AND client_id = $qclient_id")
			or die "Can not execute statement:<p>$DBI::errstr";
	}
        $sth->execute() or die "Can not execute statement: $DBI::errstr";

        my $i=0;
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $id = $ip_ref->{'id'};
                my $ip_version = $ip_ref->{'ip_version'};
                my $range_id = $ip_ref->{'range_id'};
                my $hostname = $ip_ref->{'hostname'};
                my $comment = $ip_ref->{'comentario'} || "";
                my $ip;
               if ( $ip_version eq "v4" ) {
                        $ip = $ip_ref->{'INET_NTOA(ip)'};
                } else {
			$ip = $ip_ref->{'ip'};
                }

                push @{$values_ip{$id}},"$host","$ip","$ip_version","$range_id","$hostname","$comment";
        }

        $dbh->disconnect;

        return \%values_ip;
}

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$params{sid_gestioip}:$params{bbdd_host_gestioip}:$params{bbdd_port_gestioip}",$params{user_gestioip},$params{pass_gestioip}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}

sub insert_audit_auto {
        my ($client_id,$event_class,$event_type,$event,$update_type_audit) = @_;
        my $user=$ENV{'USER'};
        my $mydatetime=time();
        my $dbh = mysql_connection();
        my $qevent_class = $dbh->quote( $event_class );
        my $qevent_type = $dbh->quote( $event_type );
        my $qevent = $dbh->quote( $event );
        my $quser = $dbh->quote( $user );
        my $qupdate_type_audit = $dbh->quote( $update_type_audit );
        my $qmydatetime = $dbh->quote( $mydatetime );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("INSERT IGNORE audit_auto (event,user,event_class,event_type,update_type_audit,date,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qclient_id)") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
}

sub check_valid_ip {
        my ($ip, $ip_version) = @_;
	my $valid="";

	if ( $ip_version eq "v4" ) {
		$valid = ip_is_ipv4("$ip");
	} else {
		$valid = ip_is_ipv6("$ip");
	}

	# 1 = OK
        return $valid;
}


sub get_predef_host_column_id {
        my ( $client_id, $name ) = @_;
        my $dbh = mysql_connection();
        my $qname = $dbh->quote( $name );
        my $sth = $dbh->prepare("SELECT id FROM predef_host_columns WHERE name=$qname
                        ") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        my $id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $id;
}

sub get_custom_host_column_id {
        my ( $client_id, $column_name ) = @_;
        my $cc_id;
        my $dbh = mysql_connection();
        my $qcolumn_name = $dbh->quote( $column_name );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcolumn_name
                        ") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $cc_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $cc_id;
}


sub get_custom_host_column_values_host_id_hash {
        my ( $client_id, $cc_name, $host_id ) = @_;

	my $ip_ref;
	my %cc_values;
        my $dbh = mysql_connection();
        my $qcc_name = $dbh->quote( $cc_name );
        my $qclient_id = $dbh->quote( $client_id );
        my $qhost_id = $dbh->quote( $host_id );

	my $sth = $dbh->prepare("SELECT cc_id,pc_id,entry,host_id from custom_host_column_entries WHERE pc_id=(SELECT id from predef_host_columns WHERE name=$qcc_name) AND host_id=$qhost_id AND client_id = $qclient_id")
		 or die "Can not execute statement: $dbh->errstr";

        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $cc_id = $ip_ref->{cc_id};
                my $pc_id = $ip_ref->{pc_id};
                my $host_id = $ip_ref->{host_id};
                my $entry = $ip_ref->{entry};
                push @{$cc_values{"${host_id}"}},"$entry","$cc_id","$pc_id";
        }
        $dbh->disconnect;
        return \%cc_values;
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


sub get_client_entries {
        my ( $client_id ) = @_;
        my @values;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth;
        $sth = $dbh->prepare("SELECT c.client,ce.phone,ce.fax,ce.address,ce.comment,ce.contact_name_1,ce.contact_phone_1,ce.contact_cell_1,ce.contact_email_1,ce.contact_comment_1,ce.contact_name_2,ce.contact_phone_2,ce.contact_cell_2,ce.contact_email_2,ce.contact_comment_2,ce.contact_name_3,ce.contact_phone_3,ce.contact_cell_3,ce.contact_email_3,ce.contact_comment_3,ce.default_resolver,ce.dns_server_1,ce.dns_server_2,ce.dns_server_3 FROM clients c, client_entries ce WHERE c.id = ce.client_id AND c.id = $qclient_id") or die "Can not execute statement: $sth->errstr";
        $sth->execute() or die "Can not execute statement:$sth->errstr";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @values;
}

sub get_client_id_from_name {
        my ( $client_name ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qclient_name = $dbh->quote( $client_name );
        my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qclient_name");
        $sth->execute() or  die "Can not execute statement:$sth->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_device_user_group_id_from_name {
        my ( $name ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qname = $dbh->quote( $name );
        my $sth = $dbh->prepare("SELECT id FROM device_user_groups WHERE name=$qname");
        $sth->execute() or  die "Can not execute statement:$sth->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_cm_server_id_from_name {
        my ( $name ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qname = $dbh->quote( $name );
        my $sth = $dbh->prepare("SELECT id FROM cm_server WHERE name=$qname");
        $sth->execute() or  die "Can not execute statement:$sth->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub update_ip_mod_hostname {
	my ( $client_id, $hostname, $comment, $id ) = @_;

        my $dbh = mysql_connection();
        my $sth;
        my $qhostname = $dbh->quote( $hostname );
        my $qcomment = $dbh->quote( $comment );
        my $qid = $dbh->quote( $id );

	$sth = $dbh->prepare("UPDATE host set hostname=$qhostname,comentario=$qcomment WHERE id=$qid")
		 or die "Can not execute statement: $dbh->errstr";

        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
        $dbh->disconnect;
}


sub insert_ip_mod {
        my ( $client_id,$ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version  ) = @_;

        my $dbh = mysql_connection();
        my $sth;
	my $ip_ref;
	my @values_host;
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

        # Check if host already exists in the DB
	if ( $ip_version eq "v6" ) {
		my $ip=int_to_ip("$ip_int","v6");
		my $qip = $dbh->quote( $ip );
		$sth = $dbh->prepare("SELECT id,hostname,range_id FROM host h WHERE ip=$qip AND client_id = $qclient_id") or die "Can not execute statement: $dbh->errstr";
	} else {
		$sth = $dbh->prepare("SELECT id,hostname,range_id FROM host h WHERE ip=$qip_int AND client_id = $qclient_id") or die "Can not execute statement: $dbh->errstr";
	} 
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
                push @values_host, [ @$ip_ref ];
        }
        my $id=$values_host[0]->[0] || "";
	if ( $id ) {
		print "Host exists ($ip_int): $id - not added\n" if $debug;
		print LOG "Host exists ($ip_int): $id - not added\n" if $debug;
		return;
	}

        if ( defined($alive) ) {
                my $qalive = $dbh->quote( $alive );
                my $qlast_response = $dbh->quote( time() );
                $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,client_id,ip_version) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qclient_id,$qip_version)"
                                ) or die "Can not execute statement: $dbh->errstr";
        } else {
                $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,client_id,ip_version) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qclient_id,$qip_version)"
                                ) or die "Can not execute statement: $dbh->errstr";
        }
        $sth->execute() or die "Can not execute statement: $dbh->errstr";

	my $new_id=$sth->{mysql_insertid};
        $sth->finish();
        $dbh->disconnect;

	return $new_id;
}

sub get_host_redes_no_rootnet {
        my ( $client_id ) = @_;
        my @host_redes;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT red, BM, red_num, loc, ip_version, rootnet FROM net WHERE rootnet = '0' AND client_id = $qclient_id")
                or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @host_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
        return @host_redes;
}

sub update_custom_host_column_value {
        my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;
        my $dbh = mysql_connection();
        my $qcc_id = $dbh->quote( $cc_id );
        my $qpc_id = $dbh->quote( $pc_id );
        my $qhost_id = $dbh->quote( $host_id );
        my $qentry = $dbh->quote( $entry );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET cc_id=$qcc_id,entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id")
		or die "Can not execute statement: $dbh->errstr";;
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
        $dbh->disconnect;
}

sub insert_custom_host_column_value {
        my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;

        my $dbh = mysql_connection();
        my $qcc_id = $dbh->quote( $cc_id );
        my $qpc_id = $dbh->quote( $pc_id );
        my $qhost_id = $dbh->quote( $host_id );
        my $qentry = $dbh->quote( $entry );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("INSERT INTO custom_host_column_entries (cc_id,pc_id,host_id,entry,client_id) VALUES ($qcc_id,$qpc_id,$qhost_id,$qentry,$qclient_id)"
            ) or die "Can not execute statement: $dbh->errstr";

        $sth->execute() or die "Can not execute statement: $dbh->errstr";

        $sth->finish();
        $dbh->disconnect;
}


sub print_help {
        print "\nusage: fetch_prtg_config.pl [OPTIONS...]\n\n";
        print "-a, --add_comment    	add device name to comment\n";
        print "-c, --cm             	configure CM for devices\n";
        print "-d, --delete_old_url 	Delete PRTG URLs which are not working anymore\n";
        print "-e, --eliminate_hosts 	Delete hosts which do not have any longer a valid PRTG URL\n\t\t\t(only for host which disposed before about a PRTG URL)\n";
        print "-f, --filter             Comma separated list of CM filter\n";
        print "-h, --help               print this help\n";
        print "-i, --ignore_certificate_errors	ignore HTTPS certificate errors\n";
        print "-o, --overwrite comment  overwrite comment with device name\n";
        print "-p, --pass=password  	PRTG user's password - omit if priv/prtg.conf is used\n";
        print "-s, --server=PRTG_server	PRTG server with protocol (e.g. https://prtg.my.org)\n";
        print "-u, --user=PRTG_user	PRTG username - omit if priv/prtg.conf is used\n";
        print "-v, --verbose            verbose\n";
        print "-x, --debug              debug\n\n";
        print "\n\nconfiguration file: $conf\n\n";
        exit;
}

sub get_url_values_host_id_hash {
        my ( $client_id ) = @_;

	my $ip_ref;
	my %cc_values;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );

#    	my $sth = $dbh->prepare("SELECT entry,host_id from custom_host_column_entries WHERE pc_id=(SELECT id from predef_host_columns WHERE name='URL') AND client_id = $qclient_id")
    	my $sth = $dbh->prepare("SELECT entry,host_id from custom_host_column_entries WHERE pc_id=(SELECT id from predef_host_columns WHERE name='URL') AND entry LIKE '%PRTG%' AND client_id = $qclient_id")
		 or die "Can not execute statement: $dbh->errstr";

        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $host_id = $ip_ref->{host_id};
                my $entry = $ip_ref->{entry};
                $cc_values{"${host_id}"} = "$entry";
        }
        $dbh->disconnect;
        return \%cc_values;
}

sub delete_custom_host_column_entry {
        my ( $client_id, $host_id ) = @_;
        my $dbh = mysql_connection();
        my $qhost_id = $dbh->quote( $host_id );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth;
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND client_id = $qclient_id") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement:$sth->errstr";
        $sth->finish();
        $dbh->disconnect;
}

sub delete_ip_host_id {
        my ( $client_id,$id ) = @_;
        my $dbh = mysql_connection();
        my $qid = $dbh->quote( $id );

        my $sth = $dbh->prepare("DELETE FROM host WHERE id=$qid"
                                ) or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
        $dbh->disconnect;
}

sub uniq {
    my %seen;
    grep !$seen{$_}++, @_;
}

sub insert_device_cm {
    my ( $client_id,$host_id,$device_type_group_id,$device_user_group_id,$user_name,$login_pass,$enable_pass,$description,$connection_proto,$cm_server_id,$save_config_changes,$connection_proto_port) = @_;

        my $dbh = mysql_connection();
        my $qhost_id = $dbh->quote( $host_id );

        $save_config_changes=0 if ! $save_config_changes;
        $device_user_group_id="" if ! $device_user_group_id;
        $user_name="" if ! $user_name;
        $login_pass="" if ! $login_pass;
        $enable_pass="" if ! $enable_pass;
        $description="" if ! $description;

        my $qdevice_type_group_id = $dbh->quote( $device_type_group_id );
        my $qdevice_user_group_id = $dbh->quote( $device_user_group_id );
        my $quser_name = $dbh->quote( $user_name );
        my $qlogin_pass = $dbh->quote( $login_pass );
        my $qenable_pass = $dbh->quote( $enable_pass );
        my $qdescription = $dbh->quote( $description );
        my $qconnection_proto = $dbh->quote( $connection_proto );
        my $qconnection_proto_port = $dbh->quote( $connection_proto_port );
        my $qsave_config_changes = $dbh->quote( $save_config_changes );
        my $qcm_server_id = $dbh->quote( $cm_server_id );
        my $qclient_id = $dbh->quote( $client_id );

        my $sth;
        if ( $device_user_group_id ) {
            $sth = $dbh->prepare("INSERT INTO device_cm_config (host_id,device_type_group_id,device_user_group_id,user_name,login_pass,enable_pass,description,connection_proto,connection_proto_args,cm_server_id,save_config_changes,client_id) VALUES ( $qhost_id,$qdevice_type_group_id,$qdevice_user_group_id,$quser_name,$qlogin_pass,$qenable_pass,$qdescription,$qconnection_proto,$qconnection_proto_port,$qcm_server_id,$qsave_config_changes,$qclient_id)"
                ) or die "Can not execute statement: $dbh->errstr";
        } else {
            $sth = $dbh->prepare("INSERT INTO device_cm_config (host_id,device_type_group_id,user_name,login_pass,enable_pass,description,connection_proto,connection_proto_args,cm_server_id,save_config_changes,client_id) VALUES ( $qhost_id,$qdevice_type_group_id,$quser_name,$qlogin_pass,$qenable_pass,$qdescription,$qconnection_proto,$qconnection_proto_port,$qcm_server_id,$qsave_config_changes,$qclient_id)"
                ) or die "Can not execute statement: $dbh->errstr";

    }
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
        $dbh->disconnect;
}


sub insert_other_device_jobs {
    my ( $client_id,$host_id,$job_name,$job_group_id,$job_descr,$job_enabled) = @_;

        $job_group_id="" if ! $job_group_id;
        $job_descr="" if ! $job_descr;
        $job_enabled="" if ! $job_enabled;

        my $dbh = mysql_connection();
        my $qhost_id = $dbh->quote( $host_id );
        my $qjob_name = $dbh->quote( $job_name );
        my $qjob_group_id;
        if ( $job_group_id ) {
            $qjob_group_id = $dbh->quote( $job_group_id );
        } else {
            $qjob_group_id="NULL";
        }
        my $qjob_descr = $dbh->quote( $job_descr );
        my $qjob_enabled = $dbh->quote( $job_enabled );
        my $qclient_id = $dbh->quote( $client_id );

        my $sth = $dbh->prepare("INSERT INTO device_jobs (host_id,job_name,job_group_id,job_descr,enabled,client_id) VALUES ($qhost_id,$qjob_name,$qjob_group_id,$qjob_descr,$qjob_enabled,$qclient_id)"
                                )  or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $sth->finish();
        $dbh->disconnect;
}

