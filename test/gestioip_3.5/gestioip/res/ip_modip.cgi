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
my $base_uri=$gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
#if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,4}$/ ) {
#        $entries_per_page_hosts=$daten{'entries_per_page_hosts'};
#} else {
#        $entries_per_page_hosts = "254";
#}
if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,4}$/ ) {
    $entries_per_page_hosts=$daten{'entries_per_page_hosts'};
    $gip->set_entries_host_por_site("$entries_per_page_hosts");
} else {
    $entries_per_page_hosts = $gip->get_entries_host_por_site() || 254;
#   $entries_per_page_hosts = "254";
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $loc_check=$daten{'loc'} || "";
my $loc_id_check=$gip->get_loc_id("$client_id","$loc_check") || "";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm,update_host_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
        loc_id_rw=>"$loc_id_check",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my $host_id = $daten{'host_id'} || "";
$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{cambiar_host_message}",notification=>"$$lang_vars{formato_malo_message} $host_id",vars_file=>"$vars_file",client_id=>"$client_id") if $host_id && $host_id !~ /^\d+$/;

# Check CM permissions

my $user=$ENV{'REMOTE_USER'};
my %values_user_group_perms=$gip->get_user_group_perms_hash("$vars_file","","$user");
my $pc_id_cm=$gip->get_predef_host_column_id("$client_id","CM");
my $enable_cm_actual=$gip->get_custom_host_column_entry("$client_id","$host_id","CM","$pc_id_cm") || "";
if ( $host_id && ! $values_user_group_perms{administrate_cm_perm} && $enable_cm_actual && $user_management_enabled eq "yes" ) {
	my %values_device_config=$gip->get_device_cm_hash("$client_id","$host_id","","host_id");

	my $device_type_group_id_actual=$values_device_config{$host_id}[1] || "";
	my $device_user_group_id_actual=$values_device_config{$host_id}[2] || "";
	my $user_name_actual=$values_device_config{$host_id}[3] || "";
	my $login_pass_actual=$values_device_config{$host_id}[4] || "";
	my $enable_pass_actual=$values_device_config{$host_id}[5] || "";
	my $description_actual=$values_device_config{$host_id}[6] || "";
	my $connection_proto_actual=$values_device_config{$host_id}[7] || "";
	my $connection_proto_port_actual=$values_device_config{$host_id}[13] || "";
	my $cm_server_id_actual=$values_device_config{$host_id}[8] || "";
	my $save_config_changes_actual=$values_device_config{$host_id}[9] || "";

	my $enable_cm_new=$daten{'enable_cm'} || "";
	my $device_type_group_id_new=$daten{'device_type_group_id'} || "";
	my $device_user_group_id_new=$daten{'device_user_group_id'} || "";
	my $user_name_new=$daten{'user_name'} || "";
	my $login_pass_new=$daten{'login_pass'} || "";
	my $retype_login_pass_new=$daten{'retype_login_pass'} || "";
	my $enable_pass_new=$daten{'enable_pass'} || "";
	my $retype_enable_pass_new=$daten{'retype_enable_pass'} || "";
	my $description_new=$daten{'description'} || "";
	my $connection_proto_new=$daten{'connection_proto'} || "";
	my $connection_proto_port_new=$daten{'connection_proto_port'} || "";
	my $cm_server_id_new=$daten{'cm_server_id'} || "";
	my $save_config_changes_new=$daten{'save_config_changes'} || "";

	if ( $enable_cm_actual ne $enable_cm_new || $device_type_group_id_actual ne $device_type_group_id_new || $device_user_group_id_actual ne $device_user_group_id_new || $user_name_actual ne $user_name_new || $login_pass_actual ne $login_pass_new || $login_pass_actual ne $retype_login_pass_new || $enable_pass_actual ne $enable_pass_new || $enable_pass_actual ne $retype_enable_pass_new || $connection_proto_actual ne $connection_proto_new || $connection_proto_port_actual ne $connection_proto_port_new || $cm_server_id_actual ne $cm_server_id_new || $save_config_changes_actual || $save_config_changes_new ) {
		$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
		print "<p><br><b>$$lang_vars{following_permissions_missing}</b><br><p>\n";
		print "<ul>\n";
		print "<li><b><i>administrate_cm_perm</i></b></li>\n";
                print "</ul>\n";
		print "<br><p><br><b>$$lang_vars{contact_gip_admin_message}</b><p><br>\n";
		print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";
		$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	}

	sub sort_sub {
		$a <=> $b;
	}
	my $p=0;

	my %values_other_jobs = $gip->get_cm_jobs("$client_id","$host_id","job_id");
	for my $job_id ( sort sort_sub keys %{ $values_other_jobs{$host_id} } ) {
		my $job_name_actual=$values_other_jobs{$host_id}{$job_id}[0];
		my $job_group_id_actual=$values_other_jobs{$host_id}{$job_id}[1];
		my $job_descr_actual=$values_other_jobs{$host_id}{$job_id}[2];
		my $job_enabled_actual=$values_other_jobs{$host_id}{$job_id}[6] || 0;


		my $job_name_new=$daten{"device_other_job_${p}"} || "";
		my $job_group_id_new=$daten{"other_job_group_${p}"} || "";
		my $job_descr_new=$daten{"other_job_descr_${p}"} || "";
		my $job_enabled_new=$daten{"job_enabled_${p}"} || "";

		if ( $job_name_actual ne $job_name_new || $job_group_id_actual ne $job_group_id_new || $job_descr_actual ne $job_descr_new || $job_enabled_actual ne $job_enabled_new ) {
			$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
			print "<p><br><b>$$lang_vars{following_permissions_missing}</b><br><p>\n";
			print "<ul>\n";
			print "<li><b><i>administrate_cm_perm</i></b></li>\n";
			print "</ul>\n";
			print "<br><p><br><b>$$lang_vars{contact_gip_admin_message}</b><p><br>\n";
			print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";
			$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
		}

		$p++;
	}

	for (my $q=$p;$q<=30;$q++) {
		if ( $daten{"device_other_job_${q}"} || $daten{"other_job_group_${q}"} || $daten{"other_job_descr_${q}"} ) {
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
} elsif ( ! $host_id && ! $values_user_group_perms{administrate_cm_perm} && $enable_cm_actual && $user_management_enabled eq "yes" ) {
	my $enable_cm_new=$daten{'enable_cm'} || "";
	my $device_type_group_id_new=$daten{'device_type_group_id'} || "";
	my $device_user_group_id_new=$daten{'device_user_group_id'} || "";
	my $user_name_new=$daten{'user_name'} || "";
	my $login_pass_new=$daten{'login_pass'} || "";
	my $retype_login_pass_new=$daten{'retype_login_pass'} || "";
	my $enable_pass_new=$daten{'enable_pass'} || "";
	my $retype_enable_pass_new=$daten{'retype_enable_pass'} || "";
	my $description_new=$daten{'description'} || "";
	my $connection_proto_new=$daten{'connection_proto'} || "";
	my $connection_proto_port_new=$daten{'connection_proto_port'} || "";
	my $cm_server_id_new=$daten{'cm_server_id'} || "";
	my $save_config_changes_new=$daten{'save_config_changes'} || "";
	if ( $enable_cm_new || $device_type_group_id_new || $device_user_group_id_new || $user_name_new || $login_pass_new || $retype_login_pass_new || $enable_pass_new || $retype_enable_pass_new || $description_new || $connection_proto_new || $connection_proto_port_new || $cm_server_id_new || $save_config_changes_new ) {
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
		if ( $daten{"device_other_job_${q}"} || $daten{"other_job_group_${q}"} || $daten{"other_job_descr_${q}"} ) {
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
}

# Check CM permissions end




my $ip_version = $daten{'ip_version'};

my ($hostname, $ip);
if ( $ip_version eq "v4" ) {
	$ip=$daten{'ip'} if ( $daten{'ip'} =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/ );
} else {
	$ip=$daten{'ip'};
}
my $host_order_by = $daten{'host_order_by'} || "IP_auf";

my $no_create_linked_entry = $daten{'no_create_linked_entry'} || "";


my $length_hostname = length($daten{'hostname'});
my $length_descr = length($daten{'host_descr'});
my $length_comentario = length($daten{'comentario'});
my ($ipob, $ip_int, $range_comentario);

my $search_index=$daten{'search_index'} || "false";
my $search_hostname=$daten{'search_hostname'} || "";
my $match=$daten{'match'} || "";
$host_order_by = "SEARCH" if $search_index eq "true";

#Detect call from ip_show_cm_hosts.cgi and ip_list_device_by_job.cgi
my $CM_show_hosts=$daten{'CM_show_hosts'} || "";
my $CM_show_hosts_by_jobs=$daten{'CM_show_hosts_by_jobs'} || "";
my $CM_diff_form=$daten{'CM_diff_form'} || "";

my $from_line=$daten{'from_line'} || "";

#Set global variables
$gip->{CM_show_hosts} = 1 if $CM_show_hosts;
$gip->{CM_show_hosts_by_jobs} = $CM_show_hosts_by_jobs if $CM_show_hosts_by_jobs;


if ( ! $daten{'hostname'} || ! $daten{'loc'} || ! $ip || $daten{'hostname'} =~ /\s+/ || $length_hostname > 75 || $length_hostname < 2 || $length_descr > 100 || $length_comentario > 500) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message} $ip","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $ip;
	$ipob = new Net::IP ($ip) or $gip->print_error("$client_id","$$lang_vars{formato_ip_malo_message}: <b>+$ip+</b>");
	$ip_int = ($ipob->intip());
	$range_comentario=$gip->get_rango_comentario_host("$client_id","$ip_int");
	$gip->print_error("$client_id","$$lang_vars{introduce_hostname_message}") if ! $daten{'hostname'};
	$gip->print_error("$client_id","$$lang_vars{min_signos_hostname_message}") if $length_hostname < 2;
	$gip->print_error("$client_id","$$lang_vars{introduce_loc_message}") if ! $daten{'loc'};
	$gip->print_error("$client_id","$$lang_vars{whitespace_message}") if $daten{'hostname'} =~ /\s+/;
	$gip->print_error("$client_id","$$lang_vars{max_signos_hostname_message}") if $length_hostname > 75;
	$gip->print_error("$client_id","$$lang_vars{max_signos_descr_message}") if $length_descr > 100;
	$gip->print_error("$client_id","$$lang_vars{max_signos_comentario_message}") if $length_hostname > 500;
} else { 
	$hostname=$daten{'hostname'} || "$ip";
	$hostname=~s/^\s//;
	$hostname=~s/\s$//;
    if ( $from_line ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{lls_message}","$vars_file");
    } else {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$hostname: $$lang_vars{cambiar_host_done_message}","$vars_file");
    }
	$ipob = new Net::IP ($ip) or $gip->print_error("$client_id","$$lang_vars{formato_ip_malo_message}: <b>+$ip+</b>");
	$ip_int = ($ipob->intip());
	$range_comentario=$gip->get_rango_comentario_host("$client_id","$ip_int");
}

my $url_method=$daten{'url_method'} || "";
if ( $url_method ) {
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (7)") if $url_method !~ /^(POST|GET)$/;
}

my $loc=$daten{'loc'} || "NULL";
my $red=$daten{'red'};
my $BM=$daten{'BM'} || "";
my $red_num=$daten{'red_num'} || "";
my $host_descr=$daten{'host_descr'} || "NULL";
my $cat=$daten{'cat'} || "NULL";
my $host_exist=$daten{'host_exist'};
my $comentario=$daten{'comentario'} || "NULL";
my $knownhosts = $daten{'knownhosts'} || "all";
my $int_admin = $daten{'int_admin'} || "n";
my $utype = $daten{'update_type'};

my $global_dyn_dns_updates_enabled=$global_config[0]->[19] || "";
#check if the networks has a zone associated
my $dyn_dns_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSZone") || "";
my $dyn_dns_ptr_zone_name = $gip->get_custom_column_entry("$client_id","$red_num","DNSPTRZone") || "";
my $make_dyn_update="";
$make_dyn_update = "yes" if $global_dyn_dns_updates_enabled eq "yes" && ( $dyn_dns_zone_name || $dyn_dns_ptr_zone_name );
my $dyn_dns_updates="";
$dyn_dns_updates=$daten{'dyn_dns_updates'} || 1 if $global_dyn_dns_updates_enabled eq "yes";


$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (4)") if $daten{'anz_values_hosts'} && $daten{'anz_values_hosts'} !~ /^\d{2,4}||no_value$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (5)") if $daten{'knownhosts'} && $daten{'knownhosts'} !~ /^all|hosts|libre$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (6)") if $daten{'start_entry_hosts'} && $daten{'start_entry_hosts'} !~ /^\d{1,20}$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $ip_version !~ /^(v4|v6)$/;
$gip->print_error("$client_id","$$lang_vars{no_dns_zone_message}") if ! $dyn_dns_zone_name && $dyn_dns_updates =~ /^[23]$/ && $make_dyn_update eq "yes";
$gip->print_error("$client_id","$$lang_vars{no_ptr_zone_message}") if ! $dyn_dns_ptr_zone_name && $dyn_dns_updates =~ /^[24]$/ && $make_dyn_update eq "yes";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if ( $global_dyn_dns_updates_enabled eq "yes" && $daten{'dyn_dns_updates'} !~ /^(1|2|3|4)$/ );

my $loc_id=$gip->get_loc_id("$client_id","$loc") || "-1";
my $cat_id=$gip->get_cat_id("$client_id","$cat") || "-1";
my $utype_id=$gip->get_utype_id("$client_id","$utype") || "-1";


# Check SITE permission
if ( $user_management_enabled eq "yes" ) {
    $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc", "$loc_id");
}

my @custom_columns = $gip->get_custom_host_columns("$client_id");

my %cc_mandatory_check_hash;

# prepare mandatory check
my $j=0;
foreach ( @custom_columns ) {
    my $column_name=$custom_columns[$j]->[0];
    my $mandatory=$custom_columns[$j]->[4];
    $cc_mandatory_check_hash{$column_name}++ if $mandatory;
    $j++;
}



my $start_entry_hosts;
if ( defined($daten{'start_entry_hosts'}) ) {
        $daten{'start_entry_hosts'} = 0 if $daten{'start_entry_hosts'} !~ /^\d{1,35}$/;
}

if ( defined($daten{'text_field_number_given'}) ) {
        $start_entry_hosts=$daten{'start_entry_hosts'} * $entries_per_page_hosts - $entries_per_page_hosts;
        $start_entry_hosts = 0 if $start_entry_hosts < 0;
} else {
        $start_entry_hosts=$daten{'start_entry_hosts'} || 0;
}
$start_entry_hosts = Math::BigInt->new("$start_entry_hosts") if $start_entry_hosts ne 0;

#Set global variables
my $password_management_enabled = $global_config[0]->[18] || "no";
$gip->{password_management_enabled} = 1 if $password_management_enabled eq "yes";


my ( $first_ip_int, $last_ip_int, $last_ip_int_red, $start_entry, $redob, $redint,$redbroad_int,$start_ip_int);
$first_ip_int=$last_ip_int=$last_ip_int_red=$start_entry=$redob=$redint=$redbroad_int=$start_ip_int="";

if ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
	$redob = "$red/$BM";
#    $gip->debug("processing: $red/$BM");
	$ipob = new Net::IP ($redob) || $gip->print_error("$client_id","Can't create ip object: $!\n");
	$redint=($ipob->intip());
	$redint = Math::BigInt->new("$redint");
	$redbroad_int=($ipob->last_int());
	$first_ip_int = $redint + 1;
	$start_ip_int=$first_ip_int;
	$last_ip_int = ($ipob->last_int());
	$last_ip_int = Math::BigInt->new("$last_ip_int");
	$last_ip_int = $last_ip_int - 1;
	$last_ip_int_red=$last_ip_int;
}


my $mydatetime = time();

my $red_loc = $gip->get_loc_from_redid("$client_id","$red_num") || "";
my @ch=$gip->get_host("$client_id","$ip_int","$ip_int");
my $create_entry = 1;
$create_entry = 0 if @ch;

$hostname = $gip->remove_whitespace_se("$hostname");

my ($audit_class, $audit_type, $update_type_audit);
$update_type_audit="1";

if ( $create_entry == 0 ) {
	my $alive = $ch[0]->[8] || -1;
	$gip->update_ip_mod("$client_id","$ip_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$alive","$ip_version","$dyn_dns_updates");
    $audit_type = 1;
} else {
	$gip->insert_ip_mod("$client_id","$ip_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","-1","$ip_version","$dyn_dns_updates");
    $audit_type = 15;
}

$host_id = $gip->get_last_host_id("$client_id") if ! $host_id;

my %cc_value=$gip->get_custom_host_columns_id_from_net_id_hash("$client_id","$red_num");
my $cc_anz=@custom_columns;

my $audit_entry_cc;
my $audit_entry_cc_new;
my @linked_ips_not_exists=();
my @linked_ips_not_valid=();

my $cm_enabled=0;
my ($cm_enabled_cc_value,$cm_pc_id,$cm_cc_id);
my ($linked_ip_cc_id, $linked_ip_pc_id);

for (my $o=0; $o<$cc_anz; $o++) {
    my $cc_name=$daten{"custom_${o}_name"};
    my $cc_value=$daten{"custom_${o}_value"} || "";
	if ( defined($daten{"custom_${o}_value_known"}) && $daten{"vendor_radio"} eq "known" ) {
		$cc_value=$daten{"custom_${o}_value_known"} || "";
	} elsif ( defined($daten{"custom_${o}_value_unknown"}) ) {
		$cc_value=$daten{"custom_${o}_value_unknown"} || "";
	}

    my $cc_id=$daten{"custom_${o}_id"};
    my $pc_id=$daten{"custom_${o}_pcid"};

	next if ! $cc_id;
	my $prede_column_name=$gip->get_predef_host_column_name("$client_id","$pc_id");

	# mandatory check
    if ( exists $cc_mandatory_check_hash{$cc_name} && ! $cc_value) {
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $cc_name");
    }


	# Configuration Management is processed below
	if ( $cc_name eq "CM" ) {
## TEST: $cm_enabled -> check if licence is valid......
		$cm_enabled=1;
		$cm_pc_id=$daten{"custom_${o}_pcid"};
		$cm_cc_id=$daten{"custom_${o}_id"};
        $cm_enabled_cc_value=$gip->get_custom_host_column_entry("$client_id","$host_id","$cc_name","$pc_id") || "";
		next;
	}

	# Tags are processed below
	if ( $cc_name eq "Tag" ) {
		next;
	}

    if ( $cc_value ) {
        my $cc_entry_host=$gip->get_custom_host_column_entry("$client_id","$host_id","$cc_name","$pc_id") || "";
        if ( $cc_entry_host ) {
	    	if ( $prede_column_name eq "URL" ) {
				if ( $cc_value !~ /^(.{1,30}::.{1,750})(,.{1,30}.{1,750};?)?$/ ) {
					print "<font color=\"red\">$$lang_vars{wrong_url_format_message} - $cc_value</font><br>\n";
					next;
				}
			} elsif ( $prede_column_name eq "linked IP" || $prede_column_name eq "linkedIP" ) {
				$linked_ip_cc_id=$cc_id;
				$linked_ip_pc_id=$pc_id;
				my @linked_ips=();
				my @linked_ips_old=();
				@linked_ips_old=split(",",$cc_entry_host);
				$cc_value =~ s/\s*//g;
				@linked_ips=split(",",$cc_value);

				# elements which are only in linked_ips_old
				my %seen;
				my @linked_ips_old_only;
				@seen{@linked_ips} = ();
				foreach my $item (@linked_ips_old) {
					push(@linked_ips_old_only, $item) unless exists $seen{$item};
				}

				# delete linked IP from elements of @linked_ips_old_only
				foreach my $linked_ip_old_only(@linked_ips_old_only){
					$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_old_only","$ip");
				}

				# update linked IP
				my $cc_value_new="";

				# Do not create entries for the linked IPs if no_create_linked_entry was checked
#				@linked_ips=() if $no_create_linked_entry;

				foreach my $linked_ip( @linked_ips ) {
					my $ip_version_linked_ip;
					if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$ip_version_linked_ip="v4";
					} else {
						$ip_version_linked_ip="v6";
					}

					my $ip_version_ip;
					if ( $ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$ip_version_ip="v4";
					} else {
						$ip_version_ip="v6";
					}

					my $ip_comp=$ip;
					$ip_comp = ip_compress_address ($ip_comp, 6) if $ip_version_ip eq "v6";

					next if $linked_ip eq $ip_comp;

					my $valid_ip=0;
					if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$valid_ip = 1;
					} else {
						$valid_ip = $gip->check_valid_ipv6("$linked_ip") || "0";
					}
					if ( $valid_ip != 1 ) {
						push(@linked_ips_not_valid,"$linked_ip");
						next;
					}

					my $ip_int_linked=$gip->ip_to_int("$client_id","$linked_ip","$ip_version_linked_ip");
					my @host=$gip->get_host("$client_id","$ip_int_linked","$ip_int_linked");
					if ( ! $host[0] ) {
						push(@linked_ips_not_exists,"$linked_ip");
						next;
					}

					my $linked_ip_comp;
					if ( $ip_version_linked_ip eq "v6" ) {
						$linked_ip_comp = ip_compress_address ($linked_ip, 6);
					} else {
						$linked_ip_comp=$linked_ip;
					}
					$cc_value_new.="," . $linked_ip_comp;
					
					my $linked_host_id=$host[0]->[11];
					my $linked_cc_entry=$gip->get_custom_host_column_entry("$client_id","$linked_host_id","$cc_name","$pc_id") || "";

					if ( $linked_cc_entry && ! $no_create_linked_entry ) {
						if ( $linked_cc_entry !~ /\b${ip_comp}\b/ ) {
							$linked_cc_entry.="," . $ip_comp;
							$gip->update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$linked_host_id","$linked_cc_entry");
						}
					} elsif ( ! $no_create_linked_entry ) {
						$gip->insert_custom_host_column_value_host("$client_id","$cc_id","$pc_id","$linked_host_id","$ip_comp");
					}
				}
				$cc_value_new =~ s/^,//;
				$cc_value=$cc_value_new;
			}

			$gip->update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$host_id","$cc_value") if $cc_value;

			if ( $audit_entry_cc ) {
				$audit_entry_cc = $audit_entry_cc . "," . $cc_entry_host;
			} else {
				$audit_entry_cc = $cc_entry_host;
			}
			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . "," .$cc_value;
			} else {
				$audit_entry_cc_new = $cc_value;
			}
        } else {
			if ( $prede_column_name eq "URL" ) {
				if ( $cc_value !~ /^.{1,30}::.{1,300}$/ ) {
					print "<font color=\"red\">$$lang_vars{wrong_url_format_message} - $cc_value</font><br>\n";
					next;
				}
			} elsif ( $prede_column_name eq "linked IP" || $prede_column_name eq "linkedIP" ) {
				$linked_ip_cc_id=$cc_id;
				$linked_ip_pc_id=$pc_id;

				my @linked_ips=();
				$cc_value =~ s/\s*//g;
				@linked_ips=split(",",$cc_value);

				# update linked IP
				my $cc_value_new="";
				foreach my $linked_ip( @linked_ips ) {

					my $ip_version_linked_ip;
					if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$ip_version_linked_ip="v4";
					} else {
						$ip_version_linked_ip="v6";
					}

					my $ip_version_ip;
					if ( $ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$ip_version_ip="v4";
					} else {
						$ip_version_ip="v6";
					}

					my $ip_comp=$ip;
					$ip_comp = ip_compress_address ($ip_comp, 6) if $ip_version_ip eq "v6";

					next if $linked_ip eq $ip_comp;

					my $valid_ip=0;
					if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
						$valid_ip = 1;
					} else {
						$valid_ip = $gip->check_valid_ipv6("$linked_ip") || "0";
					}
					if ( $valid_ip != 1 ) {
						push(@linked_ips_not_valid,"$linked_ip");
						next;
					}

					my $ip_int_linked=$gip->ip_to_int("$client_id","$linked_ip","$ip_version_linked_ip");
					my @host=$gip->get_host("$client_id","$ip_int_linked","$ip_int_linked");
					if ( ! $host[0] && ! $no_create_linked_entry ) {
						push(@linked_ips_not_exists,"$linked_ip");
						next;
					}

					my $linked_ip_comp;
					if ( $ip_version_linked_ip eq "v6" ) {
						$linked_ip_comp = ip_compress_address ($linked_ip, 6);
					} else {
						$linked_ip_comp=$linked_ip;
					}
					$cc_value_new.="," . $linked_ip_comp;

					my $linked_host_id=$host[0]->[11];
					my $linked_cc_entry=$gip->get_custom_host_column_entry("$client_id","$linked_host_id","$cc_name","$pc_id") || "";

					if ( $linked_cc_entry && ! $no_create_linked_entry ) {
						if ( $linked_cc_entry !~ /\b${ip_comp}\b/ ) {
							$linked_cc_entry.="," . $ip_comp;
							$gip->update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$linked_host_id","$linked_cc_entry");
						}
					} elsif ( ! $no_create_linked_entry ) {
						$gip->insert_custom_host_column_value_host("$client_id","$cc_id","$pc_id","$linked_host_id","$ip_comp");
					}
				}
				$cc_value_new =~ s/^,//;
				$cc_value=$cc_value_new || "";
			}

			$gip->insert_custom_host_column_value_host("$client_id","$cc_id","$pc_id","$host_id","$cc_value") if $cc_value;

			if ( $audit_entry_cc ) {
				$audit_entry_cc = $audit_entry_cc . ",---";
			} else {
				$audit_entry_cc = ",---";
			}
			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . "," . $cc_value ;
			} else {
				$audit_entry_cc_new = $cc_value;
			}
        }
    } else {
        my $cc_entry_host=$gip->get_custom_host_column_entry("$client_id","$host_id","$cc_name","$pc_id") || "";
        if ( $cc_entry_host ) {
			if ( $prede_column_name eq "linked IP" || $prede_column_name eq "linkedIP" ) {
				$linked_ip_cc_id=$cc_id;
				$linked_ip_pc_id=$pc_id;
				my @linked_ips_old_only=();
				@linked_ips_old_only=split(",",$cc_entry_host);

				# delete linked IP from elements of @linked_ips_old_only
				foreach my $linked_ip_old_only(@linked_ips_old_only){
					$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_old_only","$ip");
				}
			}

			$gip->delete_single_custom_host_column_entry("$client_id","$host_id","$cc_entry_host","$pc_id","$cc_id");
			if ( $audit_entry_cc ) {
				$audit_entry_cc = $audit_entry_cc . "," . $cc_entry_host;
			} else {
				$audit_entry_cc = $cc_entry_host;
			}
			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . ",---" ;
			} else {
				$audit_entry_cc_new = "---";
			}
		} else {
			if ( $audit_entry_cc ) {
				$audit_entry_cc = $audit_entry_cc . ",---";
			} else {
				$audit_entry_cc = "---";
			}
			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . ",---" ;
			} else {
				$audit_entry_cc_new = "---";
			}
		}
	}
}

# TAGS

my $tag = $daten{'tag'};
my @object_tags = $gip->get_object_tags("$client_id", "$host_id", "host");
if ( $tag || @object_tags ) {
#    my @object_tags = $gip->get_object_tags("$client_id", "$host_id", "host");
    my @object_tag_ids;
    my $n=0;
    foreach (@object_tags) {
        my $id = $object_tags[$n]->[0];
        push @object_tag_ids, $id;
        $n++;
    }
    @object_tag_ids = sort { $a <=> $b } @object_tag_ids;

    my $object_tag_id_string = join("_", @object_tag_ids);

    if ( $tag ne $object_tag_id_string ) {
        foreach (@object_tag_ids) {
            my $id = $_;
            $gip->delete_tag_from_object("$client_id", "$id", "$host_id", "host");
        }
        my @new_tags = split("_", $tag);
        foreach (@new_tags) {
            my $id = $_;
            $gip->insert_tag_for_object ("$client_id", "$id", "$host_id", "host");
        }
    }
}


# dyn dns update
my $old_hostname = $ch[0]->[1] || "";
if ( $make_dyn_update eq "yes" && $hostname ne $old_hostname ) {
    my @zone_values = $gip->get_dns_zones("$client_id","","$dyn_dns_zone_name");
    my $zone_id=$zone_values[0]->[0] || "";
    my $description=$zone_values[0]->[2] || "";
    my $type=$zone_values[0]->[3] || "";
    my $dns_user_id=$zone_values[0]->[4] || "";
    my $ttl=$zone_values[0]->[5] || "";
    my $dyn_dns_user_name=$zone_values[0]->[6] || "";
    my $dyn_dns_server=$zone_values[0]->[7] || "";
    my $server_type=$zone_values[0]->[8] || "";
    my @dyn_dns_server;
    if ( $dyn_dns_server =~ /,/ ) {
        @dyn_dns_server = split(",", $dyn_dns_server);
    } else {
        $dyn_dns_server[0] = $dyn_dns_server;
    }

    my ($dns_user_password, $realm, $tsig_key, $tsig_key_name);
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

    my $hostname_dyn_dns_update;
    if ( $hostname =~ /${dyn_dns_zone_name}$/ ) {
        $hostname_dyn_dns_update = $hostname;
    } else {
        $hostname_dyn_dns_update = $hostname . "." . $dyn_dns_zone_name;
    }

    if ( $create_entry == 0 ) {
        # update entries > delete and create
		# translate dyn_dns_updates for make_update.sh
        $dyn_dns_updates = 8 if $dyn_dns_updates == 2;
        $dyn_dns_updates = 9 if $dyn_dns_updates == 3;
        $dyn_dns_updates = 10 if $dyn_dns_updates == 4;
        if ( $old_hostname !~ /${dyn_dns_zone_name}$/ ) {
            $old_hostname = $old_hostname . "." . $dyn_dns_zone_name;
        }
    }

    my $return = 0;
    foreach my $dns_server ( @dyn_dns_server ) {
        $dns_server = $gip->remove_whitespace_se("$dns_server");
        $ENV{'PATH'} = '/usr/share/gestioip/bin';
        delete @ENV{'PATH', 'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};
        if ( $dyn_dns_updates =~ /^(2|3|8|9|10)$/ ) {
            $dyn_dns_zone_name = "DUMMY_NO_ZONE_NAME" if ! $dyn_dns_zone_name;
            $dyn_dns_ptr_zone_name = "DUMMY_NO_PTR_ZONE_NAME" if ! $dyn_dns_ptr_zone_name;
            $return = $gip->dyn_update_dns("$ip_version","$dyn_dns_updates", "$dyn_dns_user_name", "$dns_user_password", "$realm", "$dyn_dns_zone_name", "$dyn_dns_ptr_zone_name", "$dyn_dns_server", "$hostname_dyn_dns_update", "$ip", "$ttl", "$old_hostname","$BM", "$server_type", "$tsig_key", "$tsig_key_name");
			if ( $return != 0 ) {
				my $error = "";
				if ( $return == 2 ) {
					   $error = "Can not create KRB ticket";
				} elsif ( $return == 3 ) {
					   $error = "Unsupported update type";
				} elsif ( $return == 4 ) {
					   $error = "nsupdate error";
				}
				print STDERR "DYN DNS ERROR: $error\n" if $error;
			}

        }
    }
}

#update no_create_linked_entry
if ( $linked_ip_pc_id ) {
#	my $linked_ip_entry_host=$gip->get_custom_host_column_entry("$client_id","$host_id","linked IP","$linked_ip_pc_id") || "";
	my $linked_ip_entry_host=$gip->get_custom_host_column_entry("$client_id","$host_id","linkedIP","$linked_ip_pc_id") || "";
	if ( $linked_ip_entry_host ) {
		if ( $linked_ip_entry_host =~ /^X::/ && ! $no_create_linked_entry ) {
			$linked_ip_entry_host=~s/^X:://;
			$gip->update_custom_host_column_value_host_modip("$client_id","$linked_ip_cc_id","$linked_ip_pc_id","$host_id","$linked_ip_entry_host");
		} elsif ( $linked_ip_entry_host !~ /^X::/ && $no_create_linked_entry ) {
			$linked_ip_entry_host="X::" . $linked_ip_entry_host;
			$gip->update_custom_host_column_value_host_modip("$client_id","$linked_ip_cc_id","$linked_ip_pc_id","$host_id","$linked_ip_entry_host");
		}
	}
}



# CM CONFIGURATIN MANAGEMENT

my %jobs=();
my %jobs_new=();
my $enable_cm = $daten{'enable_cm'} || "";
my $delete_cm_all=$daten{'delete_cm_all'} || "";
for (my $p=0; $p<60; $p++) {
	my ($job_name,$job_id,$job_group_id,$job_descr,$job_enabled);
	$job_name=$daten{"device_other_job_${p}"} || "";
	$job_id=$daten{"device_other_job_id_${p}"} || "";
	$job_group_id=$daten{"other_job_group_${p}"} || "";
	$job_descr=$daten{"other_job_descr_${p}"} || "";
	$job_enabled=0;
	if ( $daten{"job_enabled_${p}"} ) {
		$job_enabled=1 if $daten{"job_enabled_${p}"} eq "on";
	}
	if ( ! $enable_cm && $delete_cm_all eq "delete_cm_all" && $job_id ) {
		push @{$jobs{$job_id}},"$job_name","$job_group_id","$job_descr","$job_enabled";
	} else {
		if ( $job_id ) {
			push @{$jobs{$job_id}},"$job_name","$job_group_id","$job_descr","$job_enabled" if $job_name;
		} else {
			push @{$jobs_new{$p}},"$job_name","$job_group_id","$job_descr","$job_enabled" if $job_name;
		}
	}
}


if ( ! $enable_cm ) {
	my $delete_cm_all=$daten{'delete_cm_all'} || "";
	if ( $delete_cm_all eq "delete_cm_all" ) {
		#delete device_cm_config
		$gip->delete_device_cm_host_id("$client_id","$host_id");

		#delete custom_host_column_entry
		my $pc_id_cm=$gip->get_predef_host_column_id("$client_id","CM");
		$gip->delete_single_custom_host_column_entry("$client_id","$host_id","","$pc_id_cm");

		#delete jobs
		for my $job_id( keys %jobs ) {
			$gip->delete_other_device_job("$client_id","$job_id");
		}
	} else {
		if ( $cm_enabled_cc_value ) {
			$gip->update_custom_host_column_value_host_modip("$client_id","$cm_cc_id","$cm_pc_id","$host_id","disabled");
		}
	}
}

if ( $cm_enabled == 1 && $enable_cm ) {

	my %values_other_jobs = $gip->get_cm_jobs("$client_id","$host_id","job_id");
	my %job_groups=$gip->get_job_groups("$client_id");
	my $client_name=$gip->get_client_from_id("$client_id");
	my $cm_backup_dir=$global_config[0]->[9];
	if ( ! $cm_backup_dir ) {
		$gip->print_error("$client_id","$$lang_vars{no_cm_config_dir_message}");
	}
	$cm_backup_dir.="/" . $client_name;


	# create configuration backup directory for this client if not exists
	unless ( -d "$cm_backup_dir" ) {
		mkdir "$cm_backup_dir" or $gip->print_error("$client_id","$$lang_vars{can_not_create_backup_dir_message} (1): $cm_backup_dir: $!");
	}

	# create configuration backup directory for this host if not exists
	unless ( -d "$cm_backup_dir/$host_id" ) {
		mkdir "$cm_backup_dir/$host_id" or $gip->print_error("$client_id","$$lang_vars{can_not_create_backup_dir_message} (2): $cm_backup_dir/$host_id: $!");
	}
	unless ( -w "$cm_backup_dir/$host_id" ) {
		$gip->print_error("$client_id","$$lang_vars{backup_dir_not_writable_message}: $cm_backup_dir/$host_id: $!");
	}

	my ( $device_user_group_id, $user_name, $login_pass, $retype_login_pass, $enable_pass,$retype_enable_pass);
	$device_user_group_id=$user_name=$login_pass=$retype_login_pass=$enable_pass,$retype_enable_pass="";

	my $ele_auth=$daten{"ele_auth"};
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (a)") if ( $ele_auth ne "group" && $ele_auth ne "individual" );

	my $cm_server_id=$daten{'cm_server_id'} || "";
	my $device_type_group_id=$daten{'device_type_group_id'} || "";
	my $cm_job=$daten{'cm_job'} || "";
	my $cm_job_group_id=$daten{'cm_job_group'} || "";
	my $save_config_changes=$daten{'save_config_changes'} || "";

	if ( $ele_auth eq "group" ) {
		$device_user_group_id=$daten{'device_user_group_id'} || "";
		$user_name="";
		$login_pass="";
		$retype_login_pass="";
		$enable_pass="";
		$retype_enable_pass="";
	} else {
		$device_user_group_id="";
		$user_name=$daten{'user_name'} || "";
		$login_pass=$daten{'login_pass'} || "";
		$retype_login_pass=$daten{'retype_login_pass'} || "";
		$enable_pass=$daten{'enable_pass'} || "";
		$retype_enable_pass=$daten{'retype_enable_pass'} || "";
	}

	my $description=$daten{'description'} || "";
	my $connection_proto=$daten{'connection_proto'} || "";
	my $connection_proto_port=$daten{'connection_proto_port'} || "";

	$gip->print_error("$client_id","$$lang_vars{choose_cm_server_message}") if ! $cm_server_id;
	$gip->print_error("$client_id","$$lang_vars{choose_device_type_group_message}") if ! $device_type_group_id;
	$gip->print_error("$client_id","$$lang_vars{choose_device_user_group_message}") if ! $device_user_group_id && $ele_auth eq "group";
#	$gip->print_error("$client_id","$$lang_vars{introduce_username_message}") if ! $user_name && $ele_auth eq "individual";
	$gip->print_error("$client_id","$$lang_vars{choose_cm_connection_proto_message}") if ! $connection_proto;
	$gip->print_error("$client_id","$$lang_vars{insert_cm_connection_proto_port_message}") if ! $connection_proto_port;
	$gip->print_error("$client_id","$$lang_vars{wrong_connection_proto_port_message}") if $connection_proto_port !~ /^\d{1,5}$/;
	$gip->print_error("$client_id","$$lang_vars{login_pass_no_match_message}") if $login_pass ne $retype_login_pass;
	$gip->print_error("$client_id","$$lang_vars{priv_pass_no_match_message}") if $enable_pass ne $retype_enable_pass;

	my %values_device_user_groups=$gip->get_device_user_groups_hash("$client_id");
	my %values_device_cm=$gip->get_device_cm_hash("$client_id","$host_id");

	if ( $enable_cm && ! $cm_enabled_cc_value ) {
		$gip->insert_custom_host_column_value_host("$client_id","$cm_cc_id","$cm_pc_id","$host_id","enabled");
	} elsif ( $enable_cm && $cm_enabled_cc_value ne "enabled" ) {
		$gip->update_custom_host_column_value_host_modip("$client_id","$cm_cc_id","$cm_pc_id","$host_id","enabled");
	} elsif ( ! $enable_cm && $cm_enabled_cc_value eq "enabled" ) {
		$gip->update_custom_host_column_value_host_modip("$client_id","$cm_cc_id","$cm_pc_id","$host_id","disabled");
	}

	my $cm_id;
	#%values_device_cm has only one element
	for my $key ( sort keys %values_device_cm ) {
		$cm_id=$key;
	}

	if (!keys %values_device_cm) {
		$gip->insert_device_cm("$client_id","$host_id","$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$description","$connection_proto","$cm_server_id","$save_config_changes","$connection_proto_port");
 	} else {
		$gip->mod_device_cm("$client_id","$cm_id","$host_id","$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$description","$connection_proto","$cm_server_id","$save_config_changes","$connection_proto_port");
	}

	for my $job_id( keys %jobs ) {
		my $job_name=$jobs{$job_id}[0] || "";
		my $job_group_id=$jobs{$job_id}[1] || "";
		my $job_descr=$jobs{$job_id}[2] || "";
		my $job_enabled=$jobs{$job_id}[3] || 0;

		my $job_name_old=$values_other_jobs{$host_id}{$job_id}[0] || "";
		my $job_group_old_id=$values_other_jobs{$host_id}{$job_id}[1] || "";
		my $job_descr_old=$values_other_jobs{$host_id}{$job_id}[2] || "";
		my $job_enabled_old=$values_other_jobs{$host_id}{$job_id}[6] || "";

		my $job_group_name=$job_groups{$job_group_id}[0] || "";

		if ( $job_name ne $job_name_old || $job_group_id ne $job_group_old_id || $job_descr ne $job_descr_old || $job_enabled ne $job_enabled_old ) {
			$gip->update_other_device_jobs("$client_id","$host_id","$job_name","$job_group_id","$job_id","$job_descr","$job_enabled");

			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . ",$$lang_vars{job_updated_message}: " . "$job_name_old:$job_group_old_id:$job_descr_old -> $job_name:$job_group_name:$job_descr";
			} else {
				$audit_entry_cc_new = "$$lang_vars{job_updated_message}: $job_name_old:$job_group_old_id:$job_descr_old -> $job_name:$job_group_name:$job_descr";
			}
		}
	}

	for my $index( sort { $jobs_new{$a} <=> $jobs_new{$b} } keys %jobs_new ) {
		my $job_name=$jobs_new{$index}[0] || "";
		my $job_group_id=$jobs_new{$index}[1] || "";
		my $job_descr=$jobs_new{$index}[2] || "";
		my $job_enabled=$jobs_new{$index}[3] || "";
		my $job_group_name=$job_groups{$job_group_id}[0] || "";

		$gip->insert_other_device_jobs("$client_id","$host_id","$job_name","$job_group_id","$job_descr","$job_enabled");

		if ( $audit_entry_cc_new ) {
			$audit_entry_cc_new = $audit_entry_cc_new . ",$$lang_vars{job_added_message}: " . "$job_name:$job_group_name:$job_descr";
		} else {
			$audit_entry_cc_new = "$$lang_vars{job_added_message}: $job_name:$job_group_name:$job_descr";
		}
	}

	for my $job_id ( keys %{ $values_other_jobs{$host_id} } ) {
		unless ( exists ($jobs{$job_id}) ) {

			my $job_name=$values_other_jobs{$host_id}{$job_id}[0] || "";
			my $job_group_id=$values_other_jobs{$host_id}{$job_id}[1] || "";
			my $job_descr=$values_other_jobs{$host_id}{$job_id}[2] || "";
			my $job_group_name=$job_groups{$job_group_id}[0];

			$gip->delete_other_device_job("$client_id","$job_id");

			if ( $audit_entry_cc_new ) {
				$audit_entry_cc_new = $audit_entry_cc_new . ",$$lang_vars{job_deleted_message}: " . "$job_name:$job_group_name:$job_descr";
			} else {
				$audit_entry_cc_new = "$$lang_vars{job_deleted_message}: $job_name:$job_group_name:$job_descr";
			}
		}
	}
}


$audit_entry_cc = "---" if ! $audit_entry_cc;
$audit_entry_cc_new = "---" if ! $audit_entry_cc_new;

if ( @ch ) {
	$audit_class="1";
	$utype = "---" if ! $utype;
	$ch[0]->[1] = "---" if ! $ch[0]->[1];
	$ch[0]->[1] = "---" if $ch[0]->[1] eq "NULL";
	$ch[0]->[2] = "---" if ! $ch[0]->[2];
	$ch[0]->[2] = "---" if $ch[0]->[2] eq "NULL";
	$ch[0]->[3] = "---" if ! $ch[0]->[3];
	$ch[0]->[3] = "---" if $ch[0]->[3] eq "NULL";
	$ch[0]->[4] = "---" if ! $ch[0]->[4];
	$ch[0]->[4] = "---" if $ch[0]->[4] eq "NULL";
	$ch[0]->[5] = "n" if ! $ch[0]->[5];
	$ch[0]->[5] = "n" if $ch[0]->[5] eq "NULL";
	$ch[0]->[6] = "---" if ! $ch[0]->[6];
	$ch[0]->[6] = "---" if $ch[0]->[6] eq "NULL";
	$ch[0]->[7] = "---" if ! $ch[0]->[7];
	$ch[0]->[7] = "---" if $ch[0]->[7] eq "-1" || $ch[0]->[7] eq "NULL";
	my $ip=$gip->int_to_ip("$client_id","$ip_int","$ip_version");
	$host_descr = "---" if ! $host_descr;
	$host_descr = "---" if $host_descr eq "NULL";
	$cat = "---" if ! $cat;
	$cat = "---" if $cat eq "NULL";
	$loc = "---" if ! $loc;
	$loc = "---" if $loc eq "NULL";
	$comentario = "---" if ! $comentario;
	$comentario = "---" if $comentario eq "NULL";
	$utype = "---" if ! $utype;
	my $hostname_audit = $hostname;
	$hostname_audit = "---" if $hostname_audit eq "NULL";
	if ( $range_comentario ) {
		if ( $comentario ne "---" ) {
			$comentario = "[" . $range_comentario . "] " . $comentario;
		} else {
			$comentario = "[" . $range_comentario . "] ";
		}
		if ( $ch[0]->[6] ne "---" ) {
			$ch[0]->[6] = "[" . $range_comentario . "] " . $ch[0]->[6];
		} else {
			$ch[0]->[6] = "[" . $range_comentario . "] ";
		}
	}
	my $event="$ip: $ch[0]->[1],$ch[0]->[2],$ch[0]->[3],$ch[0]->[4],$ch[0]->[5],$ch[0]->[6],$ch[0]->[7],$audit_entry_cc" . " -> " . "$hostname_audit,$host_descr,$loc,$cat,$int_admin,$comentario,$utype,$audit_entry_cc_new";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
} else {
	$audit_class="1";
	$host_descr = "---" if $host_descr eq "NULL";
	$cat = "---" if $cat eq "NULL";
	$loc = "---" if $loc eq "NULL";
	$comentario = "---" if $comentario eq "NULL";
	$utype = "---" if ! $utype;
	my $hostname_audit = $hostname;
	$hostname_audit = "---" if $hostname_audit eq "NULL";
	my $event="$ip: $hostname_audit,$host_descr,$loc,$int_admin,$cat,$comentario,$utype,$audit_entry_cc_new";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
}

#update net usage
$gip->update_net_usage_cc_column("$client_id", "$ip_version", "$red_num","$BM","no_rootnet");


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
} else {
	if ( $match ) {
			my %search_daten = (
			client_id => $client_id,
			search_index => "true",
			match => $match,
		);
		($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%search_daten);
	} else {
		($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%daten);
	}
}

my $anz_host_total=$gip->get_host_hash_count("$client_id","$red_num") || "0";


if ( $anz_host_total >= $entries_per_page_hosts ) {
        my $last_ip_int_new = $first_ip_int + $start_entry_hosts + $entries_per_page_hosts - 1;
        $last_ip_int = $last_ip_int_new if $last_ip_int_new < $last_ip_int;
} elsif ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
        $last_ip_int = ($ipob->last_int());
        $last_ip_int = $last_ip_int - 1;
}

#NET32
if ( $BM && ( $BM == 31 || $BM == 32 )) {
	$first_ip_int--;
	$last_ip_int++;
	$last_ip_int_red++;
}


my %anz_hosts_bm4=();
my %anz_hosts_bm6=();
%anz_hosts_bm4 = $gip->get_anz_hosts_bm_hash("$client_id","v4");
%anz_hosts_bm6 = $gip->get_anz_hosts_bm_hash("$client_id","v6");
my %anz_hosts_bm=();
if ( $ip_version eq "v4" ) {
	%anz_hosts_bm=%anz_hosts_bm4;
} else {
	%anz_hosts_bm=%anz_hosts_bm6;
}

my ($anz_values_hosts_pages, $anz_values_hosts);
my %values_lines_cc;

my %changed_host_id;

if ( $from_line ) {
    %values_lines_cc=$gip->get_line_column_values_hash("$client_id"); # $values{"${column_id}_${ll_id}"}="$entry";
	## Call from create lines

	my @line_columns=$gip->get_line_columns("$client_id");

	my $phone_number=$daten{'line_phone_number'} || "";
	my $comment=$daten{'line_comment'} || "";
	my $loc_id=$daten{'line_loc_id'} || "-1";
	my $ll_client_id=$daten{'ll_client_id'} || '-1';
	my $description=$daten{'line_description'} || "";
	my $type=$daten{'line_type'} || "";
	my $service=$daten{'line_service'} || "";
	my $device=$daten{'line_device'} || "";
	my $room=$daten{'line_room'} || "";
	my $ad_number=$daten{'line_ad_number'} || "";

    if ( $from_line eq "insert" ) {
        my $last_line_id = $gip->insert_ll("$client_id","$phone_number","$loc_id","$comment","$description","$ll_client_id","$type","$service","$ip","$room","$ad_number");

        my $j=0;
        my @cc_entries;
        foreach ( @line_columns ) {

            my $column_id=$line_columns[$j]->[0];
            my $column_name=$line_columns[$j]->[1];

            my $entry=$daten{"$column_name"} || "";
            $entry=$gip->remove_whitespace_se("$entry");

            $gip->insert_line_column_entry("$client_id","$column_id","$last_line_id","$entry" );

            push @cc_entries,"$entry";

            $j++;
        }

		my @host_cc_id = $gip->get_custom_host_column_ids_from_name( "$client_id","Line" );

		if ( $host_cc_id[0] ) {

			my %predef_host_columns=$gip->get_predef_host_column_all_hash("$client_id");
			my $pc_id = $predef_host_columns{'Line'}[0] || "";
			my $host_cc_id = $host_cc_id[0]->[0] || "";

			my $host_line_entry = $gip->get_custom_host_column_entry("$client_id","$host_id","Line","$pc_id") || "";

			if  ( $host_line_entry ) {
				$gip->update_custom_host_column_value_host("$client_id","$host_cc_id","$pc_id","$host_id","$last_line_id");
			} else {
				$gip->insert_custom_host_column_value_host("$client_id","$host_cc_id","-1","$host_id","$last_line_id") if $host_cc_id;
			}
		}



        $audit_type="54";
        $audit_class="13";
    } else {
        ## from_line = mod

        my $ll_id=$daten{'ll_id'} || "";

        $gip->update_ll("$client_id","$ll_id","$comment","$description","$ll_client_id","$loc_id","$type","$service","$ip","$room","$phone_number","$ad_number");

		my $j=0;
		foreach ( @line_columns ) {

			my $column_id=$line_columns[$j]->[0];
			my $column_name=$line_columns[$j]->[1];

			my $entry=$daten{"$column_name"} || "";

			$entry=$gip->remove_whitespace_se("$entry");

			my $entry_db=$values_lines_cc{"${column_id}_${ll_id}"} || "";

			if ( $entry_db ) {
				$gip->update_line_column_entry("$client_id","$column_id","$ll_id","$entry" );
			} else {
				$gip->insert_line_column_entry("$client_id","$column_id","$ll_id","$entry" );
			}

			$j++;
		}
        $audit_type="54";
        $audit_class="13";
    }

	my $event="$phone_number";
	$event=$event . "," .  $comment if $comment;
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	$gip->PrintLLTab("$client_id","$vars_file","","","host_created");


} elsif ( $CM_show_hosts || $CM_show_hosts_by_jobs ) {

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


	print "<table border='0'><tr><td>$pages_links</td></tr></table>" if $pages_links ne "NO_LINKS";

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","","","$vars_file","$anz_host_total","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","","","$ip_version","","","");

} elsif ( $CM_diff_form ) {
	print "<br><b>$hostname: $$lang_vars{host_successfuly_updated_message}</b><p>\n";

print <<EOF;
<form id="redir_hidden_form" method="post" action="$server_proto://$base_uri/res/cm/ip_cm_diff_form.cgi">
<input type="hidden" name="host_id" value="$host_id" />
<input type="hidden" name="hostname" value="$hostname" />
<input type="hidden" name="client_id" value="$client_id" />
</form>

<script type="text/javascript">
document.getElementById('redir_hidden_form').submit();
</script>
EOF
	$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	
} elsif ( $search_index ne "true" ) {
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

	if ( $go_to_address && $BM != 31 && $BM != 32 ) {
		my $go_to_address_int=$ip_int;
		if ( $ip_version eq "v4" ) {
			if ( $go_to_address_int < $first_ip_int || $go_to_address_int > $last_ip_int_red ) {
				$gip->print_error("$client_id","<b>$go_to_address</b>: $$lang_vars{no_net_address_message} (1)");
			}
		} else {
			if ( $go_to_address_int < $first_ip_int - 1 || $go_to_address_int > $last_ip_int_red + 1 ) {
				$gip->print_error("$client_id","<b>$go_to_address</b>: $$lang_vars{no_net_address_message} (2)");
			}
		}
		my $add_dif;
		
		if ( $knownhosts !~ /hosts/ ) {
            if ( $start_entry_hosts != 0 ) {
                $add_dif = $go_to_address_int-$start_ip_int;
                $add_dif++ if $ip_version eq "v6";
                $add_dif = Math::BigInt->new("$add_dif");
                $entries_per_page_hosts = Math::BigInt->new("$entries_per_page_hosts");
                $start_entry_hosts=$add_dif/$entries_per_page_hosts;
                $start_entry_hosts=int($start_entry_hosts + 0.5);
                $start_entry_hosts*= $entries_per_page_hosts;
            }
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

	if ( $linked_ips_not_exists[0] && ! $no_create_linked_entry ) {
		my $base_uri=$gip->get_base_uri();
		my $server_proto=$gip->get_server_proto();
		my $values_redes=$gip->get_redes_hash("$client_id","","return_int","client_only");
		print "<span style=\"color:red;\">$$lang_vars{aviso_message}<br>\n";
		foreach ( @linked_ips_not_exists ) {
			my $ip_version_check;
			my %anz_hosts_bm_check=();
			if ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
				$ip_version_check="v4";
				%anz_hosts_bm_check=%anz_hosts_bm4;
			} else {
				$ip_version_check="v6";
				%anz_hosts_bm_check=%anz_hosts_bm6;
			}
			my $linked_ip_not_exitst_int=$gip->ip_to_int("$client_id","$_","$ip_version_check");
			$linked_ip_not_exitst_int = Math::BigInt->new("$linked_ip_not_exitst_int");
			my $linked_net_found=0;
			my $red_num_linked_red;
			for my $key (sort keys %$values_redes){
				#ignore other IP version
				next if ${$values_redes}{$key}->[7] ne $ip_version_check;
				#ignore rootnets
				next if ${$values_redes}{$key}->[9] == 1;
				my $red_int=${$values_redes}{$key}->[8];
				$red_int = Math::BigInt->new("$red_int");
				my $BM_red=${$values_redes}{$key}->[1];
				$red_num_linked_red=$key;

				my $anz_values_hosts_red = $anz_hosts_bm_check{$BM_red};
				$anz_values_hosts_red =~ s/,//g;	
				my $red_broad_int=$red_int+$anz_values_hosts_red+1;
				$red_broad_int = Math::BigInt->new("$red_broad_int");
				if ( $linked_ip_not_exitst_int >= $red_int && $linked_ip_not_exitst_int <= $red_broad_int ) {
					# Network found
					$linked_net_found=1;
					last;
				} else {
					next;
				}
			}
			if ( $linked_net_found == 1 ) {
				print "$$lang_vars{ip_without_host_message}: $_ -<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modip_form.cgi\" style=\"display:inline\"><input name=\"ip\" type=\"hidden\" value=\"$linked_ip_not_exitst_int\"><input name=\"loc\" type=\"hidden\" value=\"$loc\"><input name=\"host_exist\" type=\"hidden\" value=\"no\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num_linked_red\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version_check\"><input name=\"linked_ip\" type=\"hidden\" value=\"$ip\"><input name=\"red\" type=\"hidden\" value=\"$red\"><input name=\"BM\" type=\"hidden\" value=\"$BM\"><input type=\"submit\" name=\"B2\" class=\"btn\" value=\"$$lang_vars{add_host_message}\" style=\"cursor:pointer;\" title=\"$$lang_vars{add_host_message}\"></form><br>";

			} else {
				print "$$lang_vars{no_network_found_for_ip}: $_ - $$lang_vars{ignorado_message}<br>\n";
			}
		}
		print "</span><p>\n";
	}

	if ( $linked_ips_not_valid[0] && $no_create_linked_entry ) {
		print "<span style=\"color:red;\">$$lang_vars{aviso_message}<br>\n";
		foreach ( @linked_ips_not_valid ) {
			print "$$lang_vars{ip_invalid_message}: $_ - $$lang_vars{ignorado_message}<br>\n";
		}
		print "</span>\n";
	}

	($host_hash_ref,$first_ip_int,$last_ip_int)=$gip->prepare_host_hash("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","$redbroad_int","$ip_version");

	my $pages_links=$gip->get_pages_links_host("$client_id","$start_entry_hosts","$anz_values_hosts_pages","$entries_per_page_hosts","$red_num","$knownhosts","$host_order_by","$start_ip_int",$host_hash_ref,"$redbroad_int","$ip_version","$vars_file");

	$gip->PrintIpTabHead("$client_id","$knownhosts","res/ip_modip_form.cgi","$red_num","$vars_file","$start_entry_hosts","$anz_values_hosts","$entries_per_page_hosts","$pages_links","","$ip_version");

    $changed_host_id{$host_id}=$host_id;

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

	if ( $linked_ips_not_exists[0] && ! $no_create_linked_entry) {
		my $base_uri=$gip->get_base_uri();
		my $server_proto=$gip->get_server_proto();
		my $values_redes=$gip->get_redes_hash("$client_id","","return_int");
		print "<span style=\"color:red;\">$$lang_vars{aviso_message}<br>\n";
		foreach ( @linked_ips_not_exists ) {
			my $ip_version_check;
			my %anz_hosts_bm_check=();
			if ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
				$ip_version_check="v4";
				%anz_hosts_bm_check=%anz_hosts_bm4;
			} else {
				$ip_version_check="v6";
				%anz_hosts_bm_check=%anz_hosts_bm6;
			}
			my $linked_ip_not_exitst_int=$gip->ip_to_int("$client_id","$_","$ip_version_check");
			$linked_ip_not_exitst_int = Math::BigInt->new("$linked_ip_not_exitst_int");
			my $linked_net_found=0;
			my $red_num_linked_red;
			for my $key (sort keys %$values_redes){
				#ignore other IP version
                                next if ${$values_redes}{$key}->[7] ne $ip_version_check;
				#ignore rootnets
				next if ${$values_redes}{$key}->[9] == 1;
				my $red_int=${$values_redes}{$key}->[8];
				$red_int = Math::BigInt->new("$red_int");

				next if $linked_ip_not_exitst_int < $red_int;

				my $BM_red=${$values_redes}{$key}->[1];
				$red_num_linked_red=$key;

				my $anz_values_hosts_red = $anz_hosts_bm_check{$BM_red};
				$anz_values_hosts_red =~ s/,//g;	
				my $red_broad_int=$red_int+$anz_values_hosts_red+1;
				$red_broad_int = Math::BigInt->new("$red_broad_int");
				if ( $linked_ip_not_exitst_int >= $red_int && $linked_ip_not_exitst_int <= $red_broad_int ) {
					# Network found
					$linked_net_found=1;
					last;
				} else {
					next;
				}
			}
			if ( $linked_net_found == 1 ) {
				print "$$lang_vars{ip_without_host_message}: $_ -<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modip_form.cgi\" style=\"display:inline\"><input name=\"ip\" type=\"hidden\" value=\"$linked_ip_not_exitst_int\"><input name=\"loc\" type=\"hidden\" value=\"$loc\"><input name=\"host_exist\" type=\"hidden\" value=\"no\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num_linked_red\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version_check\"><input name=\"linked_ip\" type=\"hidden\" value=\"$ip\"><input type=\"submit\" name=\"B2\" class=\"input_link_w\" value=\"$$lang_vars{add_host_message}\" style=\"cursor:pointer;\" title=\"$$lang_vars{add_host_message}\"></form><br>";

			} else {
				print "$$lang_vars{no_network_found_for_ip}: $_ - $$lang_vars{ignorado_message}<br>\n";
			}
		}
		print "</span>\n";
	}

	if ( $linked_ips_not_valid[0] && ! $no_create_linked_entry ) {
		print "<span style=\"color:red;\">$$lang_vars{aviso_message}<br>\n";
		foreach ( @linked_ips_not_valid ) {
			print "$$lang_vars{ip_invalid_message}: $_ - $$lang_vars{ignorado_message}<br>\n";
		}
		print "</span>\n";
	}

    $changed_host_id{$host_id}=$host_id;

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by",$host_sort_helper_array_ref,"$client_independent","$ip_version","$search_index","$search_hostname", \%changed_host_id);
}

#print <<EOF;
#<script type="text/javascript">
#//	window.onbeforeunload = confirmExit;
#//
#//	function confirmExit()
#//	{
#//	 console.log("redirecting");
#//	 window.location.href='$server_proto://$base_uri/ip_show.cgi?ip_version=$ip_version&client_id=$client_id&red_num=$red_num';
#//	 console.log("redirecting done");
#//	 return true;
#//	}
#
#
#//	window.onbeforeunload = function () {
#//	 console.log("redirecting");
#//	 window.location.href='$server_proto://$base_uri/ip_show.cgi?ip_version=$ip_version&client_id=$client_id&red_num=$red_num';
#//	 console.log("redirecting done");
#//	 return true;
#//	};
#
#
#	$(window).on('beforeunload', function(){
#	 console.log("redirecting");
#	 window.location.href='$server_proto://$base_uri/ip_show.cgi?ip_version=$ip_version&client_id=$client_id&red_num=$red_num';
#	 console.log("hash=" + location.hash);
#	 return false;
#	});

#</script>
#EOF

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
