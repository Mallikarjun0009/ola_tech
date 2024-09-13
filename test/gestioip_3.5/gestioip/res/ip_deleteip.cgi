#!/usr/bin/perl -T -w

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


use strict;
use lib '../modules';
use GestioIP;
use Net::IP;
use Net::IP qw(:PROC);
use Math::BigInt;
use POSIX;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page_hosts);
($lang_vars,$vars_file)=$gip->get_lang("","$lang");
if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,4}$/ ) {
        $entries_per_page_hosts=$daten{'entries_per_page_hosts'};
} else {
        $entries_per_page_hosts = "254";
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
        $client_id = 1;
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{borrar_host_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{client_id_invalid_message}");
}


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="delete_host_perm";
		($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;



if ( $daten{'red_num'} && $daten{'red_num'} !~ /^\d{1,6}$/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{hosts_deleted_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)");
}
my $red_num=$daten{'red_num'};

my $ip_version=$daten{'ip_version'};
my $anz_hosts=$daten{'anz_hosts'} || "0";

my $global_dyn_dns_updates_enabled=$global_config[0]->[19] || "";
#check if the networks has a zone associated
my $dyn_dns_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSZone") || "DUMMY_NO_ZONE_NAME";
my $dyn_dns_ptr_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSPTRZone") || "DUMMY_NO_PTR_ZONE_NAME";
#my $dyn_dns_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSZone") || "";
#my $dyn_dns_ptr_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSPTRZone") || "";
my $make_dyn_update="";
$make_dyn_update = "yes" if $global_dyn_dns_updates_enabled eq "yes" && ( $dyn_dns_zone_name || $dyn_dns_ptr_zone_name );


my ($ip_int, $ip_ad);
#my $mass_update_host_ips;
my @mass_update_host_ips=();
my @mass_update_host_ips_int=();
my %mass_update_host_ips_int=();

my $search_index=$daten{'search_index'} || "false";
my $search_hostname=$daten{'search_hostname'} || "";
my $match=$daten{'match'} || "";

if ( ! $daten{'mass_submit'} ) {

	if ( $daten{'ip_int'} !~ /^\d{8,40}$/ ) {
		$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{borrar_host_message}","$vars_file");
		$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)");
	}
	$ip_int=$daten{'ip_int'};
	$ip_ad=$gip->int_to_ip("$client_id","$ip_int","$ip_version");
	$mass_update_host_ips_int[0]=$ip_int;
	$mass_update_host_ips[0]=$ip_ad;
    $mass_update_host_ips_int{$ip_int} = $ip_ad;
} else {
	my $k;
	my $j=0;
#	my $mass_update_host_ips_int="";
	for ($k=0;$k<=$anz_hosts;$k++) {
		if ( $daten{"mass_update_host_submit_${k}"} ) {
			$mass_update_host_ips[$j]=$daten{"mass_update_host_submit_${k}"};
			$j++;
		}
	}
	$j=0;
	foreach (@mass_update_host_ips) {
		my $ip_version_host = ip_get_version ($_);
		$ip_version_host="v" . $ip_version_host;
my $ip_int = $gip->ip_to_int("$client_id","$_","$ip_version_host");
		$mass_update_host_ips_int[$j++] = $ip_int;
		$mass_update_host_ips_int{$ip_int} = $_;
	}
#	$mass_update_host_ips_int =~ s/_$//;
}

my @values_redes = $gip->get_red("$client_id","$red_num");

my $red = $values_redes[0]->[0] || "";
my $BM = $values_redes[0]->[1] || "";
my $descr = $values_redes[0]->[2] || "";
my $knownhosts = $daten{'knownhosts'} || "all";
my $host_order_by = $daten{'host_order_by'} || "IP_auf";
$host_order_by = "SEARCH" if $search_index eq "true";

my $checki_message;
if ( ! $daten{'mass_submit'} ) {
	$checki_message=$$lang_vars{borrar_host_done_message};
} else {
	$checki_message=$$lang_vars{hosts_deleted_message};
}


#Detect call from ip_show_cm_hosts.cgi and ip_list_device_by_job.cgi
my $CM_show_hosts=$daten{'CM_show_hosts'} || "";
my $CM_show_hosts_by_jobs=$daten{'CM_show_hosts_by_jobs'};

#Set global variables
$gip->{CM_show_hosts} = 1 if $CM_show_hosts;
$gip->{CM_show_hosts_by_jobs} = $CM_show_hosts_by_jobs if $CM_show_hosts_by_jobs;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$checki_message","$vars_file");

my $utype = $daten{'update_type'};

my $start_entry_hosts;
if ( defined($daten{'start_entry_hosts'}) ) {
        $daten{'start_entry_hosts'} = 0 if $daten{'start_entry_hosts'} !~ /^\d{1,35}$/;
}

if ( defined($daten{'text_field_number_given'}) ) {
        $start_entry_hosts=$daten{'start_entry_hosts'} * $entries_per_page_hosts - $entries_per_page_hosts;
        $start_entry_hosts = 0 if $start_entry_hosts < 0;
} else {
        $start_entry_hosts=$daten{'start_entry_hosts'} || '0';
}
$start_entry_hosts = Math::BigInt->new("$start_entry_hosts");

#Set global variables
my $password_management_enabled = $global_config[0]->[18] || "no";
$gip->{password_management_enabled} = 1 if $password_management_enabled eq "yes";


$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if $daten{'anz_values_hosts'} && $daten{'anz_values_hosts'} !~ /^\d{2,4}||no_value$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (4)") if $daten{'knownhosts'} && $daten{'knownhosts'} !~ /^all|hosts|libre$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (5)") if $daten{'start_entry_hosts'} && $daten{'start_entry_hosts'} !~ /^\d{1,20}$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (6)") if $ip_version !~ /^(v4|v6)$/;


my ( $first_ip_int, $last_ip_int, $last_ip_int_red, $start_entry, $redob, $ipob,$redint,$redbroad_int,$start_ip_int);
$first_ip_int=$last_ip_int=$last_ip_int_red=$start_entry=$redob=$ipob=$redint=$redbroad_int=$start_ip_int="";

if ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs  ) {
	$redob = "$red/$BM";
	$ipob = new Net::IP ($redob) || $gip->print_error("$client_id","Can't create ip object: $!\n");
	$redint=($ipob->intip());
	$redint = Math::BigInt->new("$redint");
	$last_ip_int = ($ipob->last_int());
	$last_ip_int = Math::BigInt->new("$last_ip_int");
	$redbroad_int=($ipob->last_int());
    if ( $BM < 31 ) {
        $first_ip_int = $redint + 1;
        $last_ip_int = $last_ip_int - 1;
    } else {
        $first_ip_int = $redint;
        $last_ip_int = $redbroad_int;
    }
	$start_ip_int=$first_ip_int;
	$last_ip_int_red=$last_ip_int;
}



my %cc_value = ();
my @custom_columns = $gip->get_custom_host_columns("$client_id");
my @linked_cc_id=$gip->get_custom_host_column_ids_from_name("$client_id","linkedIP");
my $linked_cc_id=$linked_cc_id[0]->[0] || "0";

my ($ip_hash,$host_sort_helper_array_ref_ip);
my $from_advanced_search = "";
if ( $CM_show_hosts ) {
	($ip_hash,$host_sort_helper_array_ref_ip)=$gip->get_host_hash("$client_id","","","IP","","","","CM");
} elsif ( $CM_show_hosts_by_jobs ) {
	# $CM_show_hosts_by_jobs contains the job_group_id
	($ip_hash)=$gip->get_devices_from_job_number("$client_id","$CM_show_hosts_by_jobs");
} elsif ( $search_index ne "true" ) {
	($ip_hash,$host_sort_helper_array_ref_ip)=$gip->get_host_hash("$client_id","$first_ip_int","$last_ip_int","IP","$knownhosts","$red_num");
} elsif ( $search_index eq "true" && ! $match ) {
    # call from advanced search -> no host list, only notify message
    $from_advanced_search = 1;
} else {
	($ip_hash,$host_sort_helper_array_ref_ip)=$gip->search_db_hash("$client_id","$vars_file",\%daten);
}

my @zone_values;
my @dyn_dns_server;
my ($zone_values, $type, $dns_user_id, $ttl, $dyn_dns_user_name, $dyn_dns_server, $dns_user_password, $realm, $hostname_dyn_dns_update, $dyn_dns_updates, $server_type, $tsig_key, $tsig_key_name);
if ( $make_dyn_update eq "yes" ) {
    @zone_values = $gip->get_dns_zones("$client_id","","$dyn_dns_zone_name");
	$type=$zone_values[0]->[3] || "";
	$dns_user_id=$zone_values[0]->[4] || "";
	$ttl=$zone_values[0]->[5] || "";
	$dyn_dns_user_name=$zone_values[0]->[6] || "";
	$dyn_dns_server=$zone_values[0]->[7] || "";
    $server_type=$zone_values[0]->[8] || "";
	if ( $dyn_dns_server =~ /,/ ) {
		@dyn_dns_server = split(",", $dyn_dns_server);
	} else {
		$dyn_dns_server[0] = $dyn_dns_server;
	}

    $dns_user_password=$realm=$tsig_key=$tsig_key_name="";
    if ( $server_type eq "GSS-TSIG" ) {
        my @dns_user_values = $gip->get_dns_user("$client_id","$dns_user_id");
        $dns_user_password=$dns_user_values[0]->[2] || "---";
        $realm=$dns_user_values[0]->[3] || "---";
    } elsif ( $server_type eq "TSIG" ) {
        # with TSIG dns_user_id is tsig_key_id
        my @key_values = $gip->get_dns_keys("$client_id","$dns_user_id");
        $tsig_key = $key_values[0]->[1];
        $tsig_key_name = $key_values[0]->[2];
    }
}

foreach $ip_int( @mass_update_host_ips_int ) {

#	next if ! defined($ip_hash->{$ip_int}[11]);
	my $host_id = "";	
	my $loc_check = "";
	if ( ! defined($ip_hash->{$ip_int}[11]) ) {
		next if ! $from_advanced_search;
	}
	if ( $from_advanced_search ) {
		my @host=$gip->get_host("$client_id","$ip_int","$ip_int");
		$host_id = $host[0]->[11];
		$loc_check = $host[0]->[3];
		$ip_ad = $mass_update_host_ips_int{$ip_int}; 
		next if ! $host_id;
	} else {
		$ip_ad=$ip_hash->{$ip_int}[0];
		$host_id = $ip_hash->{$ip_int}[12];
		$loc_check = $ip_hash->{$ip_int}[3];
	}

    my $loc_id_check=$gip->get_loc_id("$client_id","$loc_check") || "-1";
	my $ip_version_host = ip_get_version ($ip_ad);

	# Check SITE permission
	if ( $user_management_enabled eq "yes" ) {
		$gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc_check", "$loc_id_check");
	}

	my $range_comentario=$gip->get_rango_comentario_host("$client_id","$ip_int");
	$ip_version_host="v" . $ip_version_host;
	if ( $range_comentario ) {
		$gip->clear_ip("$client_id","$ip_int","$ip_int","$ip_version_host");
	} else {
		$gip->delete_ip("$client_id","$ip_int","$ip_int","$ip_version_host");
	}

	%cc_value=$gip->get_custom_host_columns_from_net_id_hash("$client_id","$host_id") if $host_id;

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
					$gip->delete_linked_ip("$client_id","$ip_version_host","$linked_ip_delete","$ip_ad");
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

	my %values_other_jobs = $gip->get_cm_jobs("$client_id","$host_id","job_id");
	$gip->delete_custom_host_column_entry("$client_id","$host_id");
	$gip->delete_device_cm_host_id("$client_id","$host_id") if $cm_config_host == 1;
	for my $job_id ( keys %{ $values_other_jobs{$host_id} } ) {
		$gip->delete_other_device_job("$client_id","$job_id");
	}

	my @switches;
	my @switches_new;

	if ( $ip_hash->{$ip_int}[12] ) {
		my $switch_id_hash = $ip_hash->{$ip_int}[12];
		@switches = $gip->get_vlan_switches_match("$client_id","$switch_id_hash");
		my $i = 0;
		if (scalar(@switches) == 0) {
			foreach ( @switches ) {
				my $vlan_id = $_[0];
				my $switches = $_[1];
				$switches =~ s/,$switch_id_hash,/,/;
				$switches =~ s/^$switch_id_hash,//;
				$switches =~ s/,$switch_id_hash$//;
				$switches =~ s/^$switch_id_hash$//;
				$switches_new[$i]->[0]=$vlan_id;
				$switches_new[$i]->[1]=$switches;
				$i++;
			}

			foreach ( @switches_new ) {
				my $vlan_id_new = $_[0];
				my $switches_new = $_[1];
				$gip->update_vlan_switches("$client_id","$vlan_id_new","$switches_new");
			}
		}
	}

    # dyn dns update
	my $dyn_dns_updates_host = $ip_hash->{$ip_int}[17] || 1;
    if ( $make_dyn_update eq "yes" && $dyn_dns_updates_host > 1  ) {

		my $hostname = $ip_hash->{$ip_int}[1];
		my $hostname_dyn_dns_update;
		if ( $hostname =~ /${dyn_dns_zone_name}$/ ) {
			$hostname_dyn_dns_update = $hostname;
		} else {
			$hostname_dyn_dns_update = $hostname . "." . $dyn_dns_zone_name;
		}
		my $old_hostname = $hostname_dyn_dns_update;

        if ( $dyn_dns_updates_host == 2 ) {
            #delete A and PTR
            $dyn_dns_updates = 5;
        } elsif ( $dyn_dns_updates_host == 3 ) {
            #delete A only
            $dyn_dns_updates = 6;
        } elsif ( $dyn_dns_updates_host == 4 ) {
            #delete PTR only
            $dyn_dns_updates = 7;
        }

        my $return = 0;
		foreach my $dns_server ( @dyn_dns_server ) {
			$dns_server = $gip->remove_whitespace_se("$dns_server");
			$ENV{'PATH'} = '/usr/share/gestioio/bin';
			delete @ENV{'PATH', 'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};
			if ( $dyn_dns_updates =~ /^(5|6|7)$/ ) {
                $return = $gip->dyn_update_dns("$ip_version","$dyn_dns_updates", "$dyn_dns_user_name", "$dns_user_password", "$realm", "$dyn_dns_zone_name", "$dyn_dns_ptr_zone_name", "$dyn_dns_server", "$hostname_dyn_dns_update", "$ip_ad", "$ttl", "$old_hostname","$BM", "$server_type", "$tsig_key", "$tsig_key_name");
                if ( $return != 0 ) {
                    my $error = "";
                    if ( $return == 2 ) {
                           $error = "Can not create KRB ticket";
                    } elsif ( $return == 3 ) {
                           $error = "Unsupported update type";
                    } elsif ( $return == 4 ) {
                           $error = "nsupdate error";
                    } elsif ( $return == 500 ) {
                           $error = "No DNS server given";
                    }
                    print STDERR "DYN DNS ERROR: $error\n" if $error;
                }
			}
		}
	}



	my $audit_type="14";
	my $audit_class="1";
	my $update_type_audit="1";

	$ip_hash->{$ip_int}[2] = "---" if ! $ip_hash->{$ip_int}[2] || $ip_hash->{$ip_int}[2] eq "NULL";
	$ip_hash->{$ip_int}[3] = "---" if ! $ip_hash->{$ip_int}[3] || $ip_hash->{$ip_int}[3] eq "NULL";
	$ip_hash->{$ip_int}[4] = "---" if ! $ip_hash->{$ip_int}[4] || $ip_hash->{$ip_int}[4] eq "NULL";
	$ip_hash->{$ip_int}[5] = "---" if ! $ip_hash->{$ip_int}[5] || $ip_hash->{$ip_int}[5] eq "NULL";
	$ip_hash->{$ip_int}[6] = "---" if ! $ip_hash->{$ip_int}[6] || $ip_hash->{$ip_int}[6] eq "NULL";
	$ip_hash->{$ip_int}[7] = "---" if ! $ip_hash->{$ip_int}[7] || $ip_hash->{$ip_int}[7] eq "NULL";

    my $event;
	if ( $from_advanced_search ) {
        $event="$ip_ad,$ip_hash->{$ip_int}[1],$ip_hash->{$ip_int}[2],$ip_hash->{$ip_int}[3],$ip_hash->{$ip_int}[4],$ip_hash->{$ip_int}[5],$ip_hash->{$ip_int}[6],$ip_hash->{$ip_int}[7],$audit_entry_cc ";
    } else {
        $event="$ip_ad,$audit_entry_cc ";
    }
    $gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
}

#update net usage
$gip->update_net_usage_cc_column("$client_id", "$ip_version", "$red_num", "$BM", "no_rootnet");


my $red_loc = $gip->get_loc_from_redid("$client_id","$red_num") || "";


my ($host_hash_ref,$host_sort_helper_array_ref);
if ( $CM_show_hosts ) {
	($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","","","$host_order_by","","","","CM");
} elsif ( $CM_show_hosts_by_jobs ) {
	# $CM_show_hosts_by_jobs contains the job_group_id
	($host_hash_ref)=$gip->get_devices_from_job_number("$client_id","$CM_show_hosts_by_jobs");
} elsif ( $search_index ne "true" ) {
	($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","$first_ip_int","$last_ip_int","IP_auf","$knownhosts","$red_num");
} elsif ( $search_index eq "true" && $match ) {
	($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%daten);
} else {
	# from advanced search
}


my $anz_host_total;
if ( $search_index ne "true" ) {
	$anz_host_total=$gip->get_host_hash_count("$client_id","$red_num") || "0";
} else {
	$anz_host_total=scalar keys %$ip_hash;
}

if ( $anz_host_total >= $entries_per_page_hosts ) {
        my $last_ip_int_new = $first_ip_int + $start_entry_hosts + $entries_per_page_hosts - 1;
        $last_ip_int = $last_ip_int_new if $last_ip_int_new < $last_ip_int;
} elsif ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
        $last_ip_int = ($ipob->last_int());
        $last_ip_int = $last_ip_int - 1 if $BM < 31;
}


my %anz_hosts_bm = $gip->get_anz_hosts_bm_hash("$client_id","$ip_version");
my $anz_values_hosts_pages = $anz_hosts_bm{$BM} || 0;
$anz_values_hosts_pages =~ s/,//g;

my $anz_values_hosts=$daten{'anz_values_hosts'} || $entries_per_page_hosts;
$anz_values_hosts =~ s/,//g; 
$anz_values_hosts = Math::BigInt->new("$anz_values_hosts");
$anz_values_hosts_pages = Math::BigInt->new("$anz_values_hosts_pages");


#$anz_hosts_bm{$BM} =~ s/,//g;
if ( $knownhosts eq "hosts" ) {
	if ( $entries_per_page_hosts > $anz_values_hosts_pages ) {
#		$anz_values_hosts=$anz_hosts_bm{$BM};
		$anz_values_hosts=$anz_values_hosts_pages;
		$anz_values_hosts_pages=$anz_host_total;
	} else {
		$anz_values_hosts=$entries_per_page_hosts;
		$anz_values_hosts_pages=$anz_host_total;
	}

} elsif ( $knownhosts =~ /libre/ ) { 
		
#	$anz_values_hosts_pages=$anz_hosts_bm{$BM}-$anz_host_total;
	$anz_values_hosts_pages=$anz_values_hosts_pages-$anz_host_total;

} elsif ( $host_order_by =~ /IP/ ) { 
	$anz_values_hosts=$entries_per_page_hosts;
#	$anz_values_hosts_pages=$anz_hosts_bm{$BM};
	$anz_values_hosts_pages=$anz_values_hosts_pages;
} else {
	$anz_values_hosts=$anz_host_total;
	$anz_values_hosts_pages=$anz_host_total;
}


$anz_values_hosts_pages = Math::BigInt->new("$anz_values_hosts_pages");

my $go_to_address=$daten{'go_to_address'} || "";
my $go_to_address_int="";
if ( $go_to_address ) {
	$go_to_address =~ s/\s|\t//g;
	if ( $ip_version eq "v6" ) {
		my $valid_v6 = $gip->check_valid_ipv6("$go_to_address") || "0";
		if ( $valid_v6 != "1" ) { 
			$gip->print_error("$client_id","$$lang_vars{no_valid_ipv6_address_message} <b>$go_to_address</b>");
		}
	} else {
		if ( $go_to_address !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) { $gip->print_error("$client_id","$$lang_vars{formato_ip_malo_message}") };
	}
	$go_to_address_int = $gip->ip_to_int("$client_id","$go_to_address","$ip_version");
	$go_to_address_int = Math::BigInt->new("$go_to_address_int");
	if ( $ip_version eq "v4" ) {
		if ( $go_to_address_int < $first_ip_int || $go_to_address_int > $last_ip_int_red ) {
			$gip->print_error("$client_id","<b>$go_to_address</b>: $$lang_vars{no_net_address_message}");
		}
	} else {
		if ( $go_to_address_int < $first_ip_int - 1 || $go_to_address_int > $last_ip_int_red + 1 ) {
			$gip->print_error("$client_id","<b>$go_to_address</b>: $$lang_vars{no_net_address_message}");
		}
	}
	my $add_dif;
	
	if ( $knownhosts !~ /hosts/ ) { 
		$add_dif = $go_to_address_int-$start_ip_int;
		$add_dif = Math::BigInt->new("$add_dif");
		$entries_per_page_hosts = Math::BigInt->new("$entries_per_page_hosts");
		$start_entry_hosts=$add_dif/$entries_per_page_hosts;
		$start_entry_hosts=int($start_entry_hosts + 0.5);
		$start_entry_hosts*= $entries_per_page_hosts;
	} else {
		my $entry_number;
		my $u=0;
		my @hostnames=$gip->get_red_hostnames("$client_id","$red_num");
		my $go_to_address_int=$gip->ip_to_int("$client_id","$go_to_address",'v6');
		foreach (@hostnames) {
			last if $_->[0] =~ /($go_to_address_int)/;
			$u++;
		}
		$entry_number = $u;
		my $anz_values_hosts_total=$gip->count_host_entries("$client_id","$red_num");
		$start_entry_hosts=$entry_number/$entries_per_page_hosts;
		$start_entry_hosts=int($start_entry_hosts + 0.5);
		$start_entry_hosts*= $entries_per_page_hosts;
	}
}


$start_entry_hosts = Math::BigInt->new("$start_entry_hosts");

my $pages_links;

if ( $CM_show_hosts || $CM_show_hosts_by_jobs ) {

        my $anz_host_total = keys %$host_hash_ref;

        my $pages_links=$gip->get_pages_links_cm(
                vars_file=>"$vars_file",
                ip_version=>"$ip_version",
                client_id=>"$client_id",
                anz_host_total=>$anz_host_total,
                entries_per_page_hosts=>"$entries_per_page_hosts",
                start_entry_hosts=>"$start_entry_hosts",
                host_order_by=>"$host_order_by",
        ) || "";


        $host_hash_ref=$gip->prepare_host_hash_cm(
                vars_file=>"$vars_file",
                ip_version=>"$ip_version",
                client_id=>"$client_id",
                host_hash_ref=>$host_hash_ref,
                entries_per_page_hosts=>"$entries_per_page_hosts",
                start_entry_hosts=>"$start_entry_hosts",
                host_order_by=>"$host_order_by",
        );


        #$gip->PrintIpTabHead("$client_id","$knownhosts","res/ip_modip_form.cgi","$red_num","$vars_file","$start_entry_hosts","$anz_values_hosts","$entries_per_page_hosts","$pages_links","$host_order_by","$ip_version");

        print "<table border='0'><tr><td>$pages_links</td></tr></table>" if $pages_links ne "NO_LINKS";

        $gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","","","$vars_file","$anz_host_total","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","","","$ip_version","","","");


} elsif ( $search_index ne "true" ) {

	($host_hash_ref,$first_ip_int,$last_ip_int)=$gip->prepare_host_hash("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","$redbroad_int","$ip_version");

	$pages_links=$gip->get_pages_links_host("$client_id","$start_entry_hosts","$anz_values_hosts_pages","$entries_per_page_hosts","$red_num","$knownhosts","$host_order_by","$start_ip_int",$host_hash_ref,"$redbroad_int","$ip_version","$vars_file");
	$gip->PrintIpTabHead("$client_id","$knownhosts","res/ip_modip_form.cgi","$red_num","$vars_file","$start_entry_hosts","$anz_values_hosts","$entries_per_page_hosts","$pages_links","$host_order_by","$ip_version");

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts_pages","$start_entry_hosts","$entries_per_page_hosts","$host_order_by",$host_sort_helper_array_ref,"","$ip_version","","","");
} else {
	if ( $from_advanced_search ) {
	    my $div_notify_message = "$$lang_vars{borrar_host_done_message}:<p>";
	    foreach (@mass_update_host_ips) {
	         $div_notify_message .= "<br>$_\n";
	    }
	    my $div_notify = GipTemplate::create_div_notify_text(
		noti => $div_notify_message,
	    );
	    print "$div_notify\n";
	} else {
	my $anz_host_rest=scalar keys %$host_hash_ref;
	if ( $anz_host_rest < 1 ) {
		print "<p class=\"NotifyText\">$$lang_vars{hosts_deleted_message}</p><br>\n";
#		print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
		$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	} else {
		$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts_pages","$start_entry_hosts","$entries_per_page_hosts","$host_order_by",$host_sort_helper_array_ref,"","$ip_version","","","");
	}
	}
}



$gip->print_end("$client_id","$vars_file","", "$daten");
