#!/usr/bin/perl -T -w

# Copyright (C) 2014 Marc Uebel

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


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();

my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page_hosts);
($lang_vars,$vars_file)=$gip->get_lang("","$lang");
if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,4}$/ ) {
        $entries_per_page_hosts=$daten{'entries_per_page_hosts'};
} else {
        $entries_per_page_hosts = "254";
}

my $tag_request = "";
if ( $daten =~ /tag=/ ) {
    $tag_request = 1;
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="create_host_perm,update_host_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;

my $user=$ENV{'REMOTE_USER'};
my %values_user_group_perms=$gip->get_user_group_perms_hash("$vars_file","","$user");

if (  $user_management_enabled eq "yes" && ! $values_user_group_perms{administrate_cm_perm} && ( $daten{'enable_cm'} || $daten{'device_type_group_id'} || $daten{'device_user_group_id'} || $daten{'device_user_group_id'} || $daten{'user_name'} || $daten{'login_pass'} || $daten{'retype_login_pass'} || $daten{'enable_pass'} || $daten{'retype_enable_pass'} || $daten{'description'} || $daten{'connection_proto'} || $daten{'connection_proto_port'} || $daten{'cm_server_id'} || $daten{'save_config_changes'} )) {

	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
	print "<p><br><b>$$lang_vars{following_permissions_missing}</b><br><p>\n";
	print "<ul>\n";
	print "<li><b><i>administrate_cm_perm</i></b></li>\n";
	print "</ul>\n";
	print "<br><p><br><b>$$lang_vars{contact_gip_admin_message}</b><p><br>\n";
	print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";
	$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
}
for (my $q=0;$q<=30;$q++) {
	if ( ! $values_user_group_perms{administrate_cm_perm} && ( $daten{"device_other_job_${q}"} || $daten{"other_job_group_${q}"} || $daten{"other_job_descr_${q}"} )) {
		$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
		print "<p><br><b>$$lang_vars{following_permissions_missing}</b><br><p>\n";
		print "<ul>\n";
		print "<li><b><i>administrate_cm_perm</i></b></li>\n";
		print "</ul>\n";
		print "<br><p><br><b>$$lang_vars{contact_gip_admin_message}</b><p><br>\n";
		print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";
		$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	}
}



my $ip_version = $daten{'ip_version'} || "";

my ($hostname, $ip);
my $host_order_by = $daten{'host_order_by'} || "IP_auf";


my $length_hostname=0;
$length_hostname = length($daten{'hostname'}) || "0" if ! $daten{'hostname'};
my $length_descr=0;
$length_descr = length($daten{'host_descr'}) || "0" if ! $daten{'host_descr'};
my $length_comentario=0;
$length_comentario = length($daten{'comentario'}) || "0" if ! $daten{'comentario'};

my ($ipob, $ip_int, $range_comentario);

#my $search_index=$daten{'search_index'} || "false";
my $search_index=$daten{'search_index'} || "";
my $search_hostname=$daten{'search_hostname'} || "";
$host_order_by = "SEARCH" if $search_index eq "true";

#Detect call from ip_show_cm_hosts.cgi and ip_list_device_by_job.cgi
my $CM_show_hosts=$daten{'CM_show_hosts'} || "";
my $CM_show_hosts_by_jobs=$daten{'CM_show_hosts_by_jobs'} || "";

#Set global variables
$gip->{CM_show_hosts} = 1 if $CM_show_hosts;
$gip->{CM_show_hosts_by_jobs} = $CM_show_hosts_by_jobs if $CM_show_hosts_by_jobs;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{host_mass_update_message}","$vars_file");

my $url_method=$daten{'url_method'} || "";
if ( $url_method ) {
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $url_method !~ /^(POST|GET)$/;
}

my $anz_nets=$daten{'anz_nets'} || "0";


$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if ! $daten{'mass_update_host_ids'};
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if ($daten{'mass_update_host_ids'} !~ /[0-9_]/ );
my $mass_update_host_ids=$daten{"mass_update_host_ids"} || "";


$gip->print_error("$client_id",$$lang_vars{max_signos_hostname_message}) if $length_hostname > 100 ;
$gip->print_error("$client_id",$$lang_vars{max_signos_descr_message}) if $length_descr > 100 ;
$gip->print_error("$client_id",$$lang_vars{max_signos_comentario_message}) if $length_comentario > 500 ;



my $red=$daten{'red'};
my $BM=$daten{'BM'};
my $red_num=$daten{'red_num'} || "";
my $host_descr=$daten{'host_descr'} || "NULL";
my $knownhosts = $daten{'knownhosts'} || "all";

$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'anz_values_hosts'} && $daten{'anz_values_hosts'} !~ /^\d{2,4}||no_value$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'knownhosts'} && $daten{'knownhosts'} !~ /^all|hosts|libre$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'start_entry_hosts'} && $daten{'start_entry_hosts'} !~ /^\d{1,20}$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (4) $ip_version") if $ip_version !~ /^(v4|v6)$/;


my $redob = "$red/$BM";

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


my ( $first_ip_int, $last_ip_int, $last_ip_int_red, $start_entry, $redint, $redbroad_int, $start_ip_int);
$first_ip_int=$last_ip_int=$last_ip_int_red=$start_entry=$redint=$redbroad_int=$start_ip_int="";


if ( $search_index ne "true" && ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
#	$ipob = new Net::IP ($redob) || $gip->print_error("$client_id","Can't create ip object: $redob: $!\n");
#	$redint=($ipob->intip());
#	$redbroad_int=($ipob->last_int());
#	$redint = Math::BigInt->new("$redint");
#	$first_ip_int = $redint + 1;
#	$start_ip_int=$first_ip_int;
#	$last_ip_int = ($ipob->last_int());
#	$last_ip_int = Math::BigInt->new("$last_ip_int");
#	$last_ip_int = $last_ip_int - 1;
#	$last_ip_int_red=$last_ip_int;

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

my $red_loc = $gip->get_loc_from_redid("$client_id","$red_num") || "";
my $red_loc_id = $gip->get_loc_id("$client_id","$red_loc") || "-1";


my $mass_update_type=$daten{'mass_update_type'};
my $mass_update_type_orig=$mass_update_type;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $mass_update_type;
my %cc_columns_all=$gip->get_custom_host_columns_hash_client_all("$client_id");
my @mass_update_types=();
my $i=0;
foreach my $key( reverse sort keys %cc_columns_all ) {
	if ( $mass_update_type =~ /$key/ ) {
		my $mass_update_type_new="";
		$mass_update_type =~ s/(^|_)($key)(_|$)/$1$3/;
		$mass_update_type_new=$2;
		$mass_update_types[$i++]=$mass_update_type_new if $mass_update_type_new;
	}
}

$mass_update_type=~s/^_+?//;
$mass_update_type=~s/_+$//;
my @mass_update_types_standard=();
if ( $mass_update_type =~ /_/ ) {
    @mass_update_types_standard=split("_",$mass_update_type);
	push @mass_update_types,@mass_update_types_standard;
} else {
    push @mass_update_types,"$mass_update_type";
}

$mass_update_type=$mass_update_type_orig;


my $descr="";
my $loc="";
#my $loc_id="-1";
my $loc_id="";
my $cat="";
#my $cat_id="-1";
my $cat_id="";
my $comentario="";
my $int_admin="";
my $utype="";
my $utype_id="";
my $dyn_dns_updates="";
my @mass_update_types_cc=();


$i=0;
my $standard_column_mod=0;
foreach (@mass_update_types) {
	if ( $_ eq $$lang_vars{description_message} ) {
		$gip->print_error("$client_id","$$lang_vars{introduce_description_message}") if ( ! $daten{'host_descr'} );
		$gip->print_error("$client_id","$$lang_vars{palabra_reservada_comment_NULL_message}") if $daten{'host_descr'} eq "NULL";
		$descr=$daten{'host_descr'} || "__NOVAL__";
		$standard_column_mod=1;
	} elsif ( $_ =~ /$$lang_vars{loc_message}/ ) {
		$gip->print_error("$client_id","$$lang_vars{introduce_loc_message}") if ( ! $daten{'loc'} );
		$loc=$daten{'loc'} || "";
		$loc_id=$gip->get_loc_id("$client_id","$loc") || "-1";
        # Check SITE permission
        if ( $user_management_enabled eq "yes" ) {
            $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc", "$loc_id");
        }
		$standard_column_mod=1;
	} elsif ( $_ =~ /$$lang_vars{tipo_message}/ ) {
		$cat=$daten{'cat'} || "";
		$cat_id=$gip->get_cat_id("$client_id","$cat") || "-1";
		$standard_column_mod=1;
	} elsif ( $_ =~ /$$lang_vars{comentario_message}/ ) {
		$gip->print_error("$client_id","$$lang_vars{palabra_reservada_comment_NULL_message}") if $daten{'comentario'} eq "NULL";
		$comentario=$daten{'comentario'} || "__NOVAL__";
		$standard_column_mod=1;
	} elsif ( $_ =~ /^AI$/ ) {
		$int_admin=$daten{'int_admin'} || "n";
		$standard_column_mod=1;
	} elsif ( $_ =~ /^UT$/ ) {
		$utype=$daten{'update_type'} || "";
		$utype_id=$gip->get_utype_id("$client_id","$utype") || "-1";
		$standard_column_mod=1;
	} elsif ( $_ =~ /$$lang_vars{update_mode_message}/ ) {
		$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (5)") if ( $daten{'dyn_dns_updates'} !~ /^(1|2|3|4)$/ );
		$dyn_dns_updates=$daten{'dyn_dns_updates'} || "";
		$standard_column_mod=1;
	} else {
		$mass_update_types_cc[$i]=$_;	
		$i++;
	}
}

#if ( ! $standard_column_mod ) {
#	$gip->print_error("$client_id","$$lang_vars{description_requiered_message}");
#}

$gip->mass_update_hosts("$client_id","$mass_update_host_ids","$red_num","$ip_version","$descr","$loc_id","$cat_id","$comentario","$utype_id","$int_admin","$red_loc_id","$search_index","$dyn_dns_updates");

my %cc_value=$gip->get_custom_host_columns_id_from_net_id_hash("$client_id");
my @custom_columns = $gip->get_custom_host_columns("$client_id");
my $cc_anz=@custom_columns;

my $audit_entry_cc;

my @mass_update_host_ids=split("_",$mass_update_host_ids);
my %changed_host_id;
foreach my $cid ( @mass_update_host_ids ) {
    $changed_host_id{$cid}=$cid;
}

my $ip_check_hash_ref; 
my %ip_check_hash_new=();

my @hosts_to_create=();
if ( $mass_update_types_cc[0] && $red_num) {

	#create hosts if not exits
	#only necessary for from net list view because search and cm hosts return only existing hosts
	$ip_check_hash_ref = $gip->get_host_hash_id_key("$client_id","$red_num");
	my %hosts_to_create=();

	while ( my ($key, @value) = each(%$ip_check_hash_ref) ) {
		$ip_check_hash_new{$value[0]->[0]}=$key;
	}

	foreach my $id ( @mass_update_host_ids ) {
		if (! exists($ip_check_hash_new{$id})) {
			push (@hosts_to_create,$id);
		}
	}

	if (scalar(@hosts_to_create) > 0 ) {
		my $hosts_to_create=join("_",@hosts_to_create);

		$gip->mass_update_hosts("$client_id","$hosts_to_create","$red_num","$ip_version","","-1","-1","","-1","n","-1","$search_index");
	}

} else {
	$ip_check_hash_ref = $gip->get_host_hash_id_key("$client_id","");
}

my $cm_change="";
foreach (@mass_update_types_cc) {
	if ( $_ eq "CM" ) {
		$cm_change=1;
		last;
	}
}
if ( $cm_change ) {
	# needed to create backup_config dir
	# old ip_check_hash_ref does not contain the new hosts
	$ip_check_hash_ref = $gip->get_host_hash_id_key("$client_id","$red_num");
	while ( my ($key, @value) = each(%$ip_check_hash_ref) ) {
		$ip_check_hash_new{$value[0]->[0]}=$key;
	}
}

my @tag_column=$gip->get_custom_host_column_ids_from_name("$client_id","Tag");
my $tag_cc_id=$tag_column[0][0] || "";

my ($mass_update_type_cc_name, $mass_update_type_cc_name_value, $mass_update_type_cc_name_id, $mass_update_type_cc_name_pcid);
foreach (@mass_update_types_cc) {
	$mass_update_type_cc_name=$_;
	$mass_update_type_cc_name_value=$mass_update_type_cc_name . "_value";
	$mass_update_type_cc_name_id=$mass_update_type_cc_name . "_id";
	$mass_update_type_cc_name_pcid=$mass_update_type_cc_name . "_pcid";
    my $cc_id=$daten{"$mass_update_type_cc_name_id"};
    my $cc_pcid=$daten{"$mass_update_type_cc_name_pcid"};
	my $description=$daten{"dcm_description"};
    if ( $mass_update_type_cc_name_value eq "vendor_value" && $daten{"vendor_radio"} eq "known" ) {
		$mass_update_type_cc_name_value = "vendor_value_known";
    } elsif ( $mass_update_type_cc_name_value eq "vendor_value" ) {
		$mass_update_type_cc_name_value = "vendor_value_unknown";
    }

	if ( defined($daten{"$mass_update_type_cc_name_value"}) && $mass_update_type_cc_name ne "CM" && $mass_update_type_cc_name ne "Tag" ) {
		$audit_entry_cc.="," if $audit_entry_cc;
		if ( length($daten{"$mass_update_type_cc_name_value"}) > 0 ) {	
			if ( $mass_update_type_cc_name eq "URL" ) {
				if ( $daten{$mass_update_type_cc_name_value} !~ /^(.{1,30}::.{1,750})(,.{1,30}.{1,750};?)?$/ ) {
					print "<font color=\"red\">$$lang_vars{wrong_url_format_message} - $daten{$mass_update_type_cc_name_value} - $$lang_vars{ignorado_message}</font><br>\n";
					next;
				}
				$gip->mass_update_custom_column_value_host("$client_id","$cc_id","$cc_pcid","$mass_update_host_ids","$daten{$mass_update_type_cc_name_value}","$red_num");
				$audit_entry_cc.="$mass_update_type_cc_name:$daten{$mass_update_type_cc_name_value}";
					
			} else {
				$gip->mass_update_custom_column_value_host("$client_id","$cc_id","$cc_pcid","$mass_update_host_ids","$daten{$mass_update_type_cc_name_value}","$red_num");
				$audit_entry_cc.="$mass_update_type_cc_name:$daten{$mass_update_type_cc_name_value}";
			}
		} else {
			$gip->mass_update_custom_column_value_host("$client_id","$cc_id","$cc_pcid","$mass_update_host_ids","__NOVAL__","$red_num");
			$audit_entry_cc.="$mass_update_type_cc_name:---";
		}
	} elsif ( $mass_update_type_cc_name eq "Tag" ) {
        # TAGS
        my $tag = $daten{'tag'};
        if ( $tag ) {
            $gip->delete_tag_from_host_object_mass_update("$client_id", "$mass_update_host_ids");
			my @new_tags = split("_", $tag);
			foreach (@new_tags) {
				my $id = $_;
				$gip->insert_tag_for_host_object_mass_update ("$client_id", "$id", "$mass_update_host_ids");
			}

        } elsif ( $tag_request && ! $tag ) {
            $gip->delete_tag_from_host_object_mass_update("$client_id", "$mass_update_host_ids");
		}


	} elsif ( $mass_update_type_cc_name eq "CM" ) {
		my ($cc_value,$cm_server_id,$device_type_group_id,$device_user_group_id,$connection_proto,$connection_proto_port,$dcm_description,$save_config_changes,$ele_auth,$user_name,$login_pass,$retype_login_pass,$enable_pass,$retype_enable_pass,$exclude_device_user_group,$exclude_connection_proto,$exclude_cm_server_id,$exclude_save_config_changes);

		my %jobs=();
		my %jobs_new=();
		my %job_groups=$gip->get_job_groups("$client_id");

		for (my $p=0; $p<30; $p++) {
			my $job_name=$daten{"device_other_job_${p}"} || "";
			my $job_id=$daten{"device_other_job_id_${p}"} || "";
			my $job_group_id=$daten{"other_job_group_${p}"} || "";
			my $job_descr=$daten{"other_job_descr_${p}"} || "";
			if ( $job_id ) {
				push @{$jobs{$job_id}},"$job_name","$job_group_id","$job_descr" if $job_name;
			} else {
				push @{$jobs_new{$p}},"$job_name","$job_group_id","$job_descr" if $job_name;
			}
		}

		my $delete_old_jobs=$daten{'delete_old_jobs'} || "";

		if ( $daten{enable_cm} ) {
			$cc_value="enabled";

			$cm_server_id=$daten{"cm_server_id"} || "";
			$device_type_group_id=$daten{"device_type_group_id"} || "";
			$device_user_group_id=$daten{"device_user_group_id"} || "";
			$ele_auth=$daten{"ele_auth"} || "";
			$user_name=$daten{"user_name"} || "";
			$login_pass=$daten{"login_pass"} || "";
			$retype_login_pass=$daten{"retype_login_pass"} || "";
			$enable_pass=$daten{"enable_pass"} || "";
			$retype_enable_pass=$daten{"retype_enable_pass"} || "";
			$connection_proto=$daten{"connection_proto"} || "";
			$connection_proto_port=$daten{"connection_proto_port"} || "";
			$dcm_description=$daten{"dcm_description"} || "";
			$save_config_changes=$daten{"save_config_changes"} || 0;
			$exclude_device_user_group=$daten{"exclude_device_user_group"} || "";
			$exclude_connection_proto=$daten{"exclude_connection_proto"} || "";
			$exclude_cm_server_id=$daten{"exclude_cm_server_id"} || "";
			$exclude_save_config_changes=$daten{"exclude_save_config_changes"} || "";

			$gip->print_error("$client_id","$$lang_vars{choose_device_type_group_message}") if ! $device_type_group_id;
			$gip->print_error("$client_id","$$lang_vars{choose_cm_server_message}") if ! $cm_server_id && ! $exclude_cm_server_id;
			$gip->print_error("$client_id","$$lang_vars{choose_device_user_group_message}") if ! $device_user_group_id && $ele_auth eq "group" && ! $exclude_device_user_group;
			$gip->print_error("$client_id","$$lang_vars{choose_cm_connection_proto_message}") if ! $connection_proto && ! $exclude_connection_proto;
			$gip->print_error("$client_id","$$lang_vars{insert_cm_connection_proto_port_message}") if ! $connection_proto_port && ! $exclude_connection_proto;
			$gip->print_error("$client_id","$$lang_vars{wrong_connection_proto_port_message}") if $connection_proto_port !~ /^\d{1,5}$/ && ! $exclude_connection_proto;
			$gip->print_error("$client_id","$$lang_vars{login_pass_no_match_message}") if $login_pass ne $retype_login_pass;
			$gip->print_error("$client_id","$$lang_vars{priv_pass_no_match_message}") if $enable_pass ne $retype_enable_pass;
		} else {
			$cc_value="disabled";
		}


		$gip->mass_update_custom_column_value_host("$client_id","$cc_id","$cc_pcid","$mass_update_host_ids","$cc_value","$red_num");

		my %values_device_cm=$gip->get_device_cm_hash_mass_update_key_host_ip("$client_id");
		my $mass_update_host_id_id="";

		if ( $cc_value eq "enabled" ) {

			my %values_device_user_groups=$gip->get_device_user_groups_hash("$client_id");
			my $mass_update_host_id_has_value="";
			my $mass_update_host_id_no_value="";
			my $mass_update_host_id_different_device_type_group="";

			my @global_config = $gip->get_global_config("$client_id");
			my $client_name=$gip->get_client_from_id("$client_id");
			my $cm_backup_dir=$global_config[0]->[9] . "/" . $client_name;
			if ( ! $cm_backup_dir ) {
				$gip->print_error("$client_id","$$lang_vars{no_cm_config_dir_message}");
			}

			foreach my $id_host( @mass_update_host_ids ) {
				my $host_id=$ip_check_hash_new{$id_host} || "";
				next if ! $host_id;
				$mass_update_host_id_id.="_" . $host_id;
				if ( defined($values_device_cm{$id_host}) ) {
					$mass_update_host_id_has_value.="_" . $host_id;
					my $device_type_group_id_old=$values_device_cm{$id_host}[1] || "";
					$mass_update_host_id_different_device_type_group.="_" . $host_id if $device_type_group_id_old ne $device_type_group_id;
				} else {
					$mass_update_host_id_no_value.="_" . $host_id;
				}


				# create configuration backup directory for this host if not exists
				unless ( -d "$cm_backup_dir/$host_id" ) {
					mkdir "$cm_backup_dir/$host_id" or $gip->print_error("$client_id","$$lang_vars{can_not_create_backup_dir_message}: $cm_backup_dir/$host_id: $!");
				}
				unless ( -w "$cm_backup_dir/$host_id" ) {
					$gip->print_error("$client_id","$$lang_vars{backup_dir_not_writable_message}: $cm_backup_dir/$host_id: $!");
				}

			}
			$mass_update_host_id_has_value =~ s/^_+//;
			$mass_update_host_id_has_value =~ s/_+/_/g;
			$mass_update_host_id_no_value =~ s/^_+//;
			$mass_update_host_id_no_value =~ s/_+/_/g;
			$mass_update_host_id_different_device_type_group =~ s/^_+//;
			$mass_update_host_id_different_device_type_group =~ s/_+/_/g;
			$mass_update_host_id_id =~ s/^_+//;
			$mass_update_host_id_id =~ s/_+/_/g;

			## host ids
			if ($mass_update_host_id_has_value) {
				#$values_device_cm{$id_host}[0];
				$gip->mod_device_cm_mass_update("$client_id","$mass_update_host_id_has_value","$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$dcm_description","$connection_proto","$cm_server_id","$save_config_changes","$connection_proto_port");
			}
			## IPs
			if ($mass_update_host_id_no_value) {
				$gip->insert_device_cm_mass_update("$client_id","$mass_update_host_id_no_value","$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$dcm_description","$connection_proto","$cm_server_id","$save_config_changes","$connection_proto_port");
			}

			# delete all jobs if delete old jobs is selected
			if ( $delete_old_jobs eq "delete_old_jobs") {
				$gip->delete_other_device_job_device_all("$client_id","$mass_update_host_id_id");
			} elsif ( $mass_update_host_id_different_device_type_group ) {
				# delete jobs of devices where device type group has changed
				$gip->delete_other_device_job_device_all("$client_id","$mass_update_host_id_different_device_type_group");
			}

			# insert new jobs
			for my $index( sort { $jobs_new{$a} <=> $jobs_new{$b} } keys %jobs_new ) {
				my $job_name=$jobs_new{$index}[0] || "";
				my $job_group_id=$jobs_new{$index}[1] || "";
				my $job_descr=$jobs_new{$index}[2] || "";
				my $job_group_name=$job_groups{$job_group_id}[0];

				$gip->insert_other_device_jobs("$client_id","","$job_name","$job_group_id","$job_descr","1","$mass_update_host_ids");

				$audit_entry_cc.=",$$lang_vars{job_added_message}: $job_name:$job_group_name:$job_descr";
			}


		} else {
			#### DELETE CM_VALUE
			foreach my $id_host( @mass_update_host_ids ) {
				my $host_id=$values_device_cm{$id_host}[0] || "";
				$mass_update_host_id_id.="_" . $host_id;
			}
			$mass_update_host_id_id =~ s/^_+//;

			$audit_entry_cc.=",CM $$lang_vars{cm_management_disabled_message}";

			my $delete_cm_all=$daten{'delete_cm_all'} || "";
			if ( $delete_cm_all eq "delete_cm_all" ) {
				#delete device_cm_config
				$gip->delete_device_cm_host_id_all("$client_id","$mass_update_host_ids");

				# delete all jobs 
				$gip->delete_other_device_job_device_all("$client_id","$mass_update_host_id_id");

				#delete custom_host_column_entry
				my $pc_id_cm=$gip->get_predef_host_column_id("$client_id","CM");
				$gip->delete_single_custom_host_column_entry_all("$client_id","$mass_update_host_ids","$pc_id_cm");

				$audit_entry_cc.=",CM $$lang_vars{cm_configuration_deleted_message}";

			} else {
				$gip->mass_update_custom_column_value_host("$client_id","$cc_id","$cc_pcid","$mass_update_host_ids","$cc_value","$red_num");
			}

			# delete all jobs 
			if ( $delete_old_jobs eq "delete_old_jobs") {
				$gip->delete_other_device_job_device_all("$client_id","$mass_update_host_ids");
			}
		}
	}
}


$audit_entry_cc = "---" if ! $audit_entry_cc;

my $mass_update_host_ids_audit=$mass_update_host_ids;
$mass_update_host_ids_audit =~ s/_/,/g;

my $audit_type="1";
my $audit_class="1";
my $update_type_audit="1";
$host_descr = "---" if $host_descr eq "NULL" || ! $descr;
my $cat_audit = $cat;
$cat_audit = "---" if $cat_id eq "-1" || ! $cat;
my $loc_audit=$loc;
$loc_audit = "---" if $loc_id eq "-1" || ! $loc;
my $comentario_audit = $comentario;
$comentario_audit = "---" if $comentario eq "NULL" || ! $comentario;
$utype = "---" if ! $utype || $utype_id eq "-1";
my $int_admin_audit=$int_admin;
$int_admin_audit="n" if ! $int_admin;
my $event="mass update: $mass_update_host_ids_audit: $host_descr,$loc_audit,$int_admin_audit,$cat_audit,$comentario,$utype,$audit_entry_cc";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

#update net usage
$gip->update_net_usage_cc_column("$client_id", "$ip_version", "$red_num","$BM","no_rootnet") if $red_num;


$knownhosts="all" if $knownhosts eq "libre";
my $go_to_address="";
$go_to_address=$ip;

my ($host_hash_ref,$host_sort_helper_array_ref);
if ( $CM_show_hosts ) {
        ($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","","","$host_order_by","","","","CM");
} elsif ( $CM_show_hosts_by_jobs ) {
	# $CM_show_hosts_by_jobs contains the job_group_id
	($host_hash_ref)=$gip->get_devices_from_job_number("$client_id","$CM_show_hosts_by_jobs");
} elsif ( $search_index ne "true" ) {
	($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","$first_ip_int","$last_ip_int","$host_order_by","$knownhosts","$red_num");
} elsif ( $search_index eq "true" && $search_hostname ) {
	($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%daten);
} else {
    my @mass_update_host_ids_check;
    if ( $ip_version eq "v6" ) {
        foreach my $id ( @mass_update_host_ids ) {
            my $ip_int=$gip->ip_to_int("$client_id","$id","v6");
            push @mass_update_host_ids_check, "$ip_int";
        }
    } else {
        @mass_update_host_ids_check = @mass_update_host_ids;
    }

	($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","$first_ip_int","$last_ip_int","SEARCH","$knownhosts","",\@mass_update_host_ids_check, "", "$ip_version");
}

my $anz_host_total=0;
if ( $search_index ne "true" ) {
	$anz_host_total=$gip->get_host_hash_count("$client_id","$red_num") || "0";
} else {
#	$anz_host_total=scalar(%{$host_hash_ref});
	$anz_host_total=keys %$host_hash_ref
}

my %anz_hosts_bm=();
my ($anz_values_hosts_pages, $anz_values_hosts);
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

        $gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","","","$vars_file","$anz_host_total","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","","","$ip_version","","",\%changed_host_id);


} elsif ( $search_index ne "true" ) {

	if ( $anz_host_total >= $entries_per_page_hosts ) {
		my $last_ip_int_new = $first_ip_int + $start_entry_hosts + $entries_per_page_hosts - 1;
		$last_ip_int = $last_ip_int_new if $last_ip_int_new < $last_ip_int;
	} else {
		$last_ip_int = ($ipob->last_int());
		$last_ip_int = $last_ip_int - 1 if $BM < 31;
	}

	%anz_hosts_bm = $gip->get_anz_hosts_bm_hash("$client_id","$ip_version");
	$anz_hosts_bm{$BM} =~ s/,//g;
	$anz_values_hosts_pages = $anz_hosts_bm{$BM};
	$anz_values_hosts_pages = Math::BigInt->new("$anz_values_hosts_pages");
	$anz_values_hosts=$daten{'anz_values_hosts'} || $anz_hosts_bm{$BM};
	$anz_values_hosts = Math::BigInt->new("$anz_values_hosts");


	if ( $knownhosts eq "hosts" ) {
		if ( $entries_per_page_hosts > $anz_values_hosts_pages ) {
			$anz_values_hosts=$anz_hosts_bm{$BM};
			$anz_values_hosts_pages=$anz_host_total;
		} else {
			$anz_values_hosts=$entries_per_page_hosts;
			$anz_values_hosts_pages=$anz_host_total;
		}
	} elsif ( $knownhosts =~ /libre/ ) {
		$anz_values_hosts_pages=$anz_hosts_bm{$BM}-$anz_host_total;
	} elsif ( $host_order_by =~ /IP/ ) {
		$anz_values_hosts=$entries_per_page_hosts;
		$anz_values_hosts_pages=$anz_hosts_bm{$BM};
	} else {
		$anz_values_hosts=$anz_host_total;
		$anz_values_hosts_pages=$anz_host_total;
	}

	$anz_values_hosts_pages =~ s/,//g;

	if ( $go_to_address ) {
		my $go_to_address_int=$ip_int;
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
			$add_dif++ if $ip_version eq "v6";
			$add_dif = Math::BigInt->new("$add_dif");
			$entries_per_page_hosts = Math::BigInt->new("$entries_per_page_hosts");
			$start_entry_hosts=$add_dif/$entries_per_page_hosts;
			$start_entry_hosts=int($start_entry_hosts + 0.5);
			$start_entry_hosts*= $entries_per_page_hosts;
		} elsif ( $knownhosts =~ /hosts/ && $ENV{HTTP_REFERER} =~ /ip_modip/ ) {
			$start_entry_hosts=$daten{start_entry_hosts};
		}

	} else {

		if ( $start_entry_hosts >= $anz_values_hosts_pages ) {
			$start_entry_hosts=$anz_values_hosts_pages/$entries_per_page_hosts;
			$start_entry_hosts=floor("$start_entry_hosts");
			$start_entry_hosts*= $entries_per_page_hosts;
		}
	}

	($host_hash_ref,$first_ip_int,$last_ip_int)=$gip->prepare_host_hash("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","$redbroad_int","$ip_version");

	my $pages_links=$gip->get_pages_links_host("$client_id","$start_entry_hosts","$anz_values_hosts_pages","$entries_per_page_hosts","$red_num","$knownhosts","$host_order_by","$start_ip_int",$host_hash_ref,"$redbroad_int","$ip_version","$vars_file");

	$gip->PrintIpTabHead("$client_id","$knownhosts","res/ip_modip_form.cgi","$red_num","$vars_file","$start_entry_hosts","$anz_values_hosts","$entries_per_page_hosts","$pages_links","","$ip_version");

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts_pages","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","$host_sort_helper_array_ref","","$ip_version","","",\%changed_host_id);

} else {
	$anz_values_hosts += keys %$host_hash_ref;
	$knownhosts="all";
	$start_entry_hosts="0";
	$entries_per_page_hosts="512";
	my $pages_links="NO_LINKS";
	$host_order_by = "SEARCH";
	$red_num = "";
	$red_loc = "";
	$redbroad_int = "1";
	$first_ip_int = "";
	$last_ip_int = "";
	my $client_independent="no";

	my %advanced_search_hash=();

	my @column_values=("advanced_search_hostname","advanced_search_host_descr","advanced_search_comentario","advanced_search_ip","advanced_search_loc","advanced_search_cat","advanced_search_int_admin","advanced_search_host_descr","advanced_search_hostname_exact","advanced_search_client_independent");

	foreach my $column ( @column_values ) {
		if ( $daten{"$column"} ) {
			$advanced_search_hash{"$column"}=$daten{"$column"};
		}
	}

	my @cc_values=$gip->get_custom_host_columns("$client_id");
	for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
		# mass update
		if (  defined $daten{"cc_id_$cc_values[$k]->[1]"} ) {
			my $key="cc_id_$cc_values[$k]->[1]";
			$advanced_search_hash{"$key"}=$daten{"$key"} if exists($daten{"$key"});
		}
	}

	my $advanced_search_hash=\%advanced_search_hash;

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by",$host_sort_helper_array_ref,"$client_independent","$ip_version","$search_index","$search_hostname", \%changed_host_id,$advanced_search_hash);

}


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

