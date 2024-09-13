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
use Net::IP;
use Net::IP qw(:PROC);
use lib '../modules';
use GestioIP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page_hosts);
($lang_vars,$vars_file)=$gip->get_lang("","$lang");
#if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,3}$/ ) {
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
my $host_order_by = $daten{'host_order_by'} || "IP_auf";
my $ip_version = $daten{'ip_version'} || "";

my $search_index=$daten{'search_index'} || "";
my $search_hostname=$daten{'search_hostname'} || "";
my $match=$daten{'match'} || "";
my $hostname_line=$daten{'hostname_line'} || "";

my $red_num=$daten{'red_num'} || "";
my $ip_int=$daten{'ip'};

if ( $ip_int && $ip_int !~ /^\d{1,50}$/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)");
}

## Call from create lines
if ( $daten{'from_line'} && ! $red_num ) {

    my $check_ip = $daten{'line_ip'};
    my $valid_ip = "";
    if ( $check_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $valid_ip = $gip->check_valid_ipv4("$check_ip") || 0;
        $ip_version = "v4";
    } else {
        $valid_ip = $gip->check_valid_ipv6("$check_ip") || 0;
        $ip_version = "v6";
    }
    if ( $valid_ip != 1 ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{ip_invalid_message}: $check_ip - $ip_version");
    }

    $ip_int = $gip->ip_to_int("$client_id","$check_ip","$ip_version") if ! $ip_int;

    my $error = "";
	($red_num, $error) = $gip->get_host_network(
        ip         => "$check_ip",
        ip_int     => "$ip_int",
        ip_version => "$ip_version",
        client_id => "$client_id",
        vars_file => "$vars_file",
    );

    if ( ! $red_num ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message}","$vars_file");
        $gip->print_error("$client_id","$error");
    }

}

my $loc_hash=$gip->get_loc_hash("$client_id");
my @line_columns=$gip->get_line_columns("$client_id");

my $phone_number=$daten{'line_phone_number'} || "";
my $from_line=$daten{'from_line'} || "";
my $comment=$daten{'line_comment'} || "";
my $loc_id=$daten{'line_loc_id'} || "-1";
my $ll_client_id=$daten{'ll_client_id'} || '-1';
my $description=$daten{'line_description'} || "";
my $type=$daten{'line_type'} || "";
my $service=$daten{'line_service'} || "";
my $device=$daten{'line_device'} || "";
my $room=$daten{'line_room'} || "";
my $ad_number=$daten{'line_ad_number'} || "";
my $ll_id=$daten{'ll_id'} || "";
my $hidden_line_form = " 
<input type=\"hidden\" name=\"line_phone_number\" value=\"$phone_number\">
<input type=\"hidden\" name=\"line_comment\" value=\"$comment\">
<input type=\"hidden\" name=\"line_loc_id\" value=\"$loc_id\">
<input type=\"hidden\" name=\"ll_client_id\" value=\"$ll_client_id\">
<input type=\"hidden\" name=\"line_description\" value=\"$description\">
<input type=\"hidden\" name=\"line_type\" value=\"$type\">
<input type=\"hidden\" name=\"line_service\" value=\"$service\">
<input type=\"hidden\" name=\"line_device\" value=\"$device\">
<input type=\"hidden\" name=\"line_room\" value=\"$room\">
<input type=\"hidden\" name=\"line_ad_number\" value=\"$ad_number\">
<input type=\"hidden\" name=\"ll_id\" value=\"$ll_id\">
";

my $form_elements_line = "";
$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $phone_number,
    name => "line_phone_number",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $comment,
    name => "line_comment",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $loc_id,
    name => "line_loc_id",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $ll_client_id,
    name => "ll_client_id",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $description,
    name => "line_description",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $type,
    name => "line_type",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $service,
    name => "line_service",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $device,
    name => "line_device",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $room,
    name => "line_room",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $ad_number,
    name => "line_ad_number",
);

$form_elements_line .= GipTemplate::create_form_element_hidden(
    value => $ll_id,
    name => "ll_id",
);



my $k=0;
foreach ( @line_columns ) {

	my $column_id=$line_columns[$k]->[0];
	my $column_name=$line_columns[$k]->[1];

	my $entry=$daten{"$column_name"} || "";
	$entry=$gip->remove_whitespace_se("$entry");
	$hidden_line_form .= "<input type=\"hidden\" name=\"$column_name\" value=\"$entry\">";
	$k++;
}
## END Call from create lines


my @host=$gip->get_host("$client_id","$ip_int","$ip_int");

my $required_perms;
if (@host) {
	$required_perms="update_host_perm";
} else {
	$required_perms="create_host_perm";
}

my $loc=$daten{'loc'} || "";
$loc = "" if $loc eq "---";
my $loc_id_check = $loc_hash->{$loc} || "";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
    ($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
		loc_id_rw=>"$loc_id_check",
	);
}

my $global_dyn_dns_updates_enabled=$global_config[0]->[19] || "";


my $ip_ad=$gip->int_to_ip("$client_id","$ip_int","$ip_version");

my $cm_val=$daten{'cm_val'} || "";

#Detect call from ip_show_cm_hosts.cgi and ip_list_device_by_job.cgi
my $CM_show_hosts=$daten{'CM_show_hosts'} || "";
my $CM_show_hosts_by_jobs=$daten{'CM_show_hosts_by_jobs'} || "";
my $CM_diff_form=$daten{'CM_diff_form'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{cambiar_host_message} $ip_ad","$vars_file");


# Activate custom host column CM if no activated
my $cm_enabled = $gip->check_cm_enabled() || "no";
my $cm_id=$gip->get_custom_host_column_ids_from_name("$client_id","CM") || "";
if ( ! $cm_id && $cm_enabled eq "yes" ) {
	my $last_custom_host_column_id=$gip->get_last_custom_host_column_id();
	$last_custom_host_column_id++;
	my $cm_id_predef=$gip->get_predef_host_column_id("$client_id","CM");
	my $insert_ok=$gip->insert_custom_host_column("9999","$last_custom_host_column_id","CM","$cm_id_predef","$vars_file");
#my ( $self,$client_id, $id, $custom_column,$column_type_id, $vars_file, $select_type, $select_items, $mandatory ) = @_;


	my $audit_type="42";
	my $audit_class="5";
	my $update_type_audit="1";
	my $event="CM";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
}  


my $utype = $daten{'update_type'};
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $daten{'anz_values_hosts'} && $daten{'anz_values_hosts'} !~ /^\d{1,4}|no_value$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if $daten{'knownhosts'} && $daten{'knownhosts'} !~ /^all|hosts|libre$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (4)") if $daten{'start_entry_hosts'} && $daten{'start_entry_hosts'} !~ /^\d{1,20}$/;
#$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $daten{'host_id'};
my $anz_values_hosts = $daten{'anz_values_hosts'} || "no_value";

my $start_entry_hosts=$daten{'start_entry_hosts'} || '0';
my $knownhosts=$daten{'knownhosts'} || 'all';
my $host_id=$daten{'host_id'} || "";

if ( ! $daten{'ip'} && ! $daten{'from_line'} ) {
    $gip->print_error("$client_id","$$lang_vars{una_ip_message}<br>");
}
my $linked_ip=$daten{'linked_ip'} || "";

if ( $ip_version eq "v4" ) {
	$gip->CheckInIP("$client_id","$ip_ad","$$lang_vars{formato_ip_malo_message} - $$lang_vars{comprueba_ip_message}: <b><i>$ip_ad</i></b><br>");
} else {
	my $valid_v6=$gip->check_valid_ipv6("$ip_ad") || "0";
	$gip->print_error("$client_id","$$lang_vars{formato_ip_malo_message}") if $valid_v6 ne "1";
}

my @values_redes=();
my $red="";
my $BM="";
my $red_loc_id="";
my $red_dyn_dns_updates="";
if ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
	@values_redes = $gip->get_red("$client_id","$red_num");
	$red = $values_redes[0]->[0] || "";
	$BM = $values_redes[0]->[1] || "";
	$red_loc_id = $values_redes[0]->[3] || "";
	$red_dyn_dns_updates = $values_redes[0]->[10] || 1;
}

my @values_locations=$gip->get_loc("$client_id");
my @values_categorias=$gip->get_cat("$client_id");
my @values_utype=$gip->get_utype();

my $hostname = $host[0]->[1] || "";
#if (( ! $hostname || $hostname eq "unknown" ) && $search_hostname ) {
if ( ! $hostname  && $search_hostname ) {
	$hostname = $search_hostname;
}
$hostname = "" if $hostname eq "NULL";
$hostname = $hostname_line if $hostname_line && ! $hostname;

my $host_descr = $host[0]->[2] || "NULL";
my $loc_val = $host[0]->[3] || "$loc";
if ( ! $loc_val || $loc_val eq "NULL" ) {
	$loc_val=$gip->get_loc_from_id("$client_id","$red_loc_id");
}
my $cat_val = $host[0]->[4] || "NULL";
my $int_ad_val = $host[0]->[5] || "n";
my $update_type = $host[0]->[7] || "";
my $comentario = $host[0]->[6] || "";
my $dyn_dns_updates = $host[0]->[13] || $red_dyn_dns_updates;

$host_descr = "" if (  $host_descr eq "NULL" );
$comentario = "" if (  $comentario eq "NULL" ); 
$loc_val = "" if (  $loc_val eq "NULL" ); 
$cat_val = "" if (  $cat_val eq "NULL" );
$update_type = "" if (  $update_type eq "NULL" ); 


my $disabled_color='#F0EDEA';

print <<EOF;
<script language="JavaScript" type="text/javascript" charset="utf-8">
<!--
function checkhost(IP,HOSTNAME,CLIENT_ID,IP_VERSION,RED_NUM)
{
var opciones="toolbar=no,right=100,top=100,width=500,height=300", i=0;
var URL="$server_proto://$base_uri/ip_checkhost.cgi?ip=" + IP + "&hostname=" + HOSTNAME + "&client_id=" + CLIENT_ID  + "&ip_version=" + IP_VERSION + "&red_num=" + RED_NUM;
host_info=window.open(URL,"",opciones);
}
-->
</script>

<script type="text/javascript">
<!--
function mod_cm_fields(ANZ_OTHER_JOBS){
//ANZ_OTHER_JOBS++
  if(ip_mod_form.enable_cm.checked == true){
    ip_mod_form.connection_proto.disabled=false;
    ip_mod_form.connection_proto_port.disabled=false;
    ip_mod_form.connection_proto.style.backgroundColor="white";
    ip_mod_form.connection_proto_port.style.backgroundColor="white";
    ip_mod_form.device_type_group_id.disabled=false;
    ip_mod_form.device_type_group_id.style.backgroundColor="white";
    ip_mod_form.save_config_changes.disabled=false;
    ip_mod_form.save_config_changes.style.backgroundColor="white";
    ip_mod_form.cm_server_id.disabled=false;
    ip_mod_form.cm_server_id.style.backgroundColor="white";
    document.getElementById('delete_cm_checkbox').checked=false;
    document.getElementById('delete_cm_checkbox').style.display='none';
    document.getElementById('delete_cm_checkbox_span').style.display='none';

    for (var i = 0, length = ip_mod_form.ele_auth.length; i < length; i++) {
      if (ip_mod_form.ele_auth[i].checked) {
        ele_auth_value=ip_mod_form.ele_auth[i].value;
        break;
      }
    }
    for (var i = 0, length = ip_mod_form.ele_auth.length; i < length; i++) {
      ip_mod_form.ele_auth[i].disabled=false;
    }
    if ( ele_auth_value == "group" ) {
      ip_mod_form.user_name.disabled=true;
      ip_mod_form.login_pass.disabled=true;
      ip_mod_form.retype_login_pass.disabled=true;
      ip_mod_form.enable_pass.disabled=true;
      ip_mod_form.retype_enable_pass.disabled=true;
      ip_mod_form.device_user_group_id.disabled=false;
      ip_mod_form.device_user_group_id.style.backgroundColor='white';
    } else {
      ip_mod_form.user_name.disabled=false;
      ip_mod_form.login_pass.disabled=false;
      ip_mod_form.retype_login_pass.disabled=false;
      ip_mod_form.enable_pass.disabled=false;
      ip_mod_form.retype_enable_pass.disabled=false;
      ip_mod_form.device_user_group_id.disabled=true;
      ip_mod_form.device_user_group_id.style.backgroundColor='$disabled_color';
    }

        for(j=0;j<30;j++){
            OTHER_JOB_ENABLED='job_enabled_' + j
            OTHER_JOB_ID='device_other_job_' + j
            OTHER_JOB_GROUP_ID='other_job_group_' + j
            OTHER_JOB_DESCR='other_job_descr_' + j

            document.getElementById(OTHER_JOB_ENABLED).disabled=false;

            if ( document.getElementById(OTHER_JOB_ENABLED).checked == true ) {
              document.getElementById(OTHER_JOB_ID).disabled=false;
              document.getElementById(OTHER_JOB_ID).style.backgroundColor="white";
              document.getElementById(OTHER_JOB_GROUP_ID).disabled=false;
              document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="white";
              document.getElementById(OTHER_JOB_DESCR).disabled=false;
              document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="white";
            }
        }


   }else{

    ip_mod_form.connection_proto.disabled=true;
    ip_mod_form.connection_proto_port.disabled=true;
    ip_mod_form.connection_proto.style.backgroundColor='$disabled_color';
    ip_mod_form.connection_proto_port.style.backgroundColor='$disabled_color';
    ip_mod_form.device_type_group_id.disabled=true;
    ip_mod_form.device_type_group_id.style.backgroundColor="$disabled_color";
    ip_mod_form.save_config_changes.disabled=true;
    ip_mod_form.save_config_changes.style.backgroundColor="$disabled_color";
    ip_mod_form.cm_server_id.disabled=true;
    ip_mod_form.cm_server_id.style.backgroundColor="$disabled_color";
    document.getElementById('delete_cm_checkbox').checked=false;
    document.getElementById('delete_cm_checkbox').style.display='inline';
    document.getElementById('delete_cm_checkbox_span').style.display='inline';

    for (var i = 0, length = ip_mod_form.ele_auth.length; i < length; i++) {
      ip_mod_form.ele_auth[i].disabled=true;
    }

    ip_mod_form.device_user_group_id.disabled=true;
    ip_mod_form.device_user_group_id.style.backgroundColor="$disabled_color";
    ip_mod_form.user_name.disabled=true;
    ip_mod_form.login_pass.disabled=true;
    ip_mod_form.retype_login_pass.disabled=true;
    ip_mod_form.enable_pass.disabled=true;
    ip_mod_form.retype_enable_pass.disabled=true;

        for(j=0;j<30;j++){
            OTHER_JOB_ENABLED='job_enabled_' + j
            OTHER_JOB_ID='device_other_job_' + j
            OTHER_JOB_GROUP_ID='other_job_group_' + j
            OTHER_JOB_DESCR='other_job_descr_' + j
            document.getElementById(OTHER_JOB_ENABLED).disabled=true;
            document.getElementById(OTHER_JOB_ID).disabled=true;
            document.getElementById(OTHER_JOB_ID).style.backgroundColor="$disabled_color";
            document.getElementById(OTHER_JOB_GROUP_ID).disabled=true;
            document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="$disabled_color";
            document.getElementById(OTHER_JOB_DESCR).disabled=true;
            document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="$disabled_color";
        }
   }
}
//-->
</script>


<script type="text/javascript">
<!--
function mod_user_info(VALUE){
   if(VALUE == 'group' ){
    ip_mod_form.user_name.disabled=true;
    ip_mod_form.login_pass.disabled=true;
    ip_mod_form.retype_login_pass.disabled=true;
    ip_mod_form.enable_pass.disabled=true;
    ip_mod_form.retype_enable_pass.disabled=true;
    ip_mod_form.device_user_group_id.disabled=false;
    ip_mod_form.device_user_group_id.style.backgroundColor='white';
    ip_mod_form.user_name.value='';
    ip_mod_form.login_pass.value='';
    ip_mod_form.retype_login_pass.value='';
    ip_mod_form.enable_pass.value='';
    ip_mod_form.retype_enable_pass.value='';

    document.getElementById('cm_individual_user').style.display='none';
    document.getElementById('cm_device_user_group').style.display='inline';
    document.getElementById('cm_device_user_group1').style.display='inline';

   } else {

    ip_mod_form.user_name.disabled=false;
    ip_mod_form.login_pass.disabled=false;
    ip_mod_form.retype_login_pass.disabled=false;
    ip_mod_form.enable_pass.disabled=false;
    ip_mod_form.retype_enable_pass.disabled=false;
    ip_mod_form.device_user_group_id.selectedIndex='0';
    ip_mod_form.device_user_group_id.disabled=true;
    ip_mod_form.device_user_group_id.style.backgroundColor='#F0EDEA';

    document.getElementById('cm_individual_user').style.display='inline';
    document.getElementById('cm_device_user_group').style.display='none';
    document.getElementById('cm_device_user_group1').style.display='none';

   }

}
//-->
</script>

<script type="text/javascript">
<!--
function disable_job(K){
  OTHER_JOB_ENABLED='job_enabled_' + K;
  OTHER_JOB_ID='device_other_job_' + K;
  OTHER_JOB_GROUP_ID='other_job_group_' + K;
  OTHER_JOB_DESCR='other_job_descr_' + K;
  JOB_ENABLED=document.getElementById(OTHER_JOB_ENABLED).checked;
  if ( JOB_ENABLED == true ) {
    document.getElementById(OTHER_JOB_ID).disabled=false;
    document.getElementById(OTHER_JOB_ID).style.backgroundColor="white";
    document.getElementById(OTHER_JOB_GROUP_ID).disabled=false;
    document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="white";
    document.getElementById(OTHER_JOB_DESCR).disabled=false;
    document.getElementById(OTHER_JOB_DESCR).readOnly=false;
    document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="white";
    for (i=0; i<document.getElementById(OTHER_JOB_ID).options.length; i++) {
      document.getElementById(OTHER_JOB_ID).options[i].disabled=false;
    }
    for (i=0; i<document.getElementById(OTHER_JOB_GROUP_ID).options.length; i++) {
        document.getElementById(OTHER_JOB_GROUP_ID).options[i].disabled=false ;
    }
  } else {
    document.getElementById(OTHER_JOB_ID).style.backgroundColor="$disabled_color";
    document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="$disabled_color";
    document.getElementById(OTHER_JOB_DESCR).readOnly=true;
    document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="$disabled_color";
    for (i=0; i<document.getElementById(OTHER_JOB_ID).options.length; i++) {
      if ( i != document.getElementById(OTHER_JOB_ID).selectedIndex ) {
        document.getElementById(OTHER_JOB_ID).options[i].disabled=true;
      }
    }
    for (i=0; i<document.getElementById(OTHER_JOB_GROUP_ID).options.length; i++) {
      if ( i != document.getElementById(OTHER_JOB_GROUP_ID).selectedIndex ) {
        document.getElementById(OTHER_JOB_GROUP_ID).options[i].disabled=true;
      }
    }
  }
}
//-->
</script>

<script type="text/javascript">
<!--
function mod_connection_proto_port(VALUE){
   if(VALUE == 'telnet' ){
    ip_mod_form.connection_proto_port.value='23';
   } else if (VALUE == 'SSH' ){
    ip_mod_form.connection_proto_port.value='22';
   }
}
//-->
</script>

EOF




my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);
my $j = 0;

my $onclick = 'onClick="checkhost(\'' . $ip_ad . '\',\'\',\'' . $client_id . '\',\'' . $ip_version . '\',\'' . $red_num . '\')"';
$form_elements .= GipTemplate::create_form_element_link_form(
    label => "IP",
    value => $ip_ad,
    id => "IP",
    onclick => $onclick,
#    class_args => "btn-sm",
	
);

$form_elements .= GipTemplate::create_form_element_text(
    label => "$$lang_vars{hostname_message}",
    value => $hostname,
    id => "hostname",
    required => "required",
    maxlength => 75,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    value => $host_descr,
    id => "host_descr",
    maxlength => 100,
);

# SITE
@item_order = ();
foreach my $opt(@values_locations) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        push @item_order, "";
        next;
    }
	if ( $locs_rw_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ ) {
            push @item_order, $name;
        }
    } else {
        push @item_order, $name;
    }
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{loc_message},
    item_order => \@item_order,
    selected_value => $loc_val,
    id => "loc",
    width => "10em",
    required => "required",
);

# CATEGORY
@item_order = ();
foreach my $opt(@values_categorias) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        push @item_order, "";
        next;
    }
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{cat_message},
    item_order => \@item_order,
    selected_value => $cat_val,
    id => "cat",
    width => "10em",
);

my $int_admin_checked = "";
if ( $int_ad_val eq "y" ) {
    $int_admin_checked="checked";

}

$form_elements .= GipTemplate::create_form_element_checkbox(
    label => "AI",
    id => "int_admin",
    value => "y",
    checked => $int_admin_checked,
    width => "10em",

);

$form_elements .= GipTemplate::create_form_element_textarea(
    label => $$lang_vars{comentario_message},
    value => $comentario,
    rows => '5',
    cols => '30',
    id => "comentario",
    width => "10em",
    maxlength => 500,
);


# UT
@item_order = ();
foreach my $opt(@values_utype) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        push @item_order, "";
        next;
    }
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => "UT",
    item_order => \@item_order,
    selected_value => $update_type,
    id => "update_type",
    width => "6em",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $ip_ad,
    name => "ip",
);












#print "<form name=\"ip_mod_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modip.cgi\">\n";
#print "<table border=\"0\" cellpadding=\"1\">\n";
#print "<tr><td><b>IP</b></td><td><b>  $$lang_vars{hostname_message}</b></td><td><b>  $$lang_vars{description_message}</b></td><td><b>  $$lang_vars{loc_message}</b></td><td><b> $$lang_vars{cat_message}</b></td><td><b>AI</b></td><td><b>$$lang_vars{comentario_message}</b></td><td><b>UT</b></td></tr>\n";
#print "<tr valign=\"top\"><td class=\"hostcheck\" onClick=\"checkhost(\'$ip_ad\',\'\',\'$client_id\',\'$ip_version\',\'$red_num\')\" style=\"cursor:pointer;\" title=\"ping\"><font size=\"2\">$ip_ad<input type=\"hidden\" name=\"ip\" value=\"$ip_ad\"></font></td>\n";
#print "<td><i><font size=\"2\"><input type=\"text\" size=\"15\" name=\"hostname\" value=\"$hostname\" maxlength=\"75\"></font></i></td>\n";
#print "<td><i><font size=\"2\"><input type=\"text\" size=\"15\" name=\"host_descr\" value=\"$host_descr\" maxlength=\"100\"></font></i></td>\n";
#print "<td><font size=\"2\"><select name=\"loc\" size=\"1\" value=\"$loc_val\">";
#print "<option>$loc_val</option>";
#$j=0;
#foreach (@values_locations) {
#	$values_locations[$j]->[0] = "" if ($values_locations[$j]->[0] eq "NULL" && $loc_val ne "NULL" );
#	print "<option>$values_locations[$j]->[0]</option>" if ( $values_locations[$j]->[0] ne "$loc_val" );
#	$j++;
#}
#print "</select>\n";
#print "</font></td><td><font size=\"2\"><select name=\"cat\" size=\"1\">";
#print "<option>$cat_val</option>";
#$j=0;
#foreach (@values_categorias) {
#	$values_categorias[$j]->[0] = "" if ($values_categorias[$j]->[0] eq "NULL" && $cat_val ne "NULL" );
#        print "<option>$values_categorias[$j]->[0]</option>" if ($values_categorias[$j]->[0] ne "$cat_val" );
#        $j++;
#}
#print "</select>\n";
#
#if ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
#	print "</font></td><input name=\"red\" type=\"hidden\" value=\"$red\"><input name=\"BM\" type=\"hidden\" value=\"$BM\">\n";
#}
#
#if ( $int_ad_val eq "y" ) {
#	$int_admin_checked="checked";
#} else {
#	$int_admin_checked="";
#}
#
#print "<td><input type=\"checkbox\" name=\"int_admin\" value=\"y\" $int_admin_checked></td>\n";
#
#
#print "<td><textarea name=\"comentario\" cols=\"30\" rows=\"5\" wrap=\"physical\" maxlength=\"500\">$comentario</textarea></td>";
#print "<td><select name=\"update_type\" size=\"1\">";
#print "<option>$update_type</option>";
#$j=0;
#foreach (@values_utype) {
#	$values_utype[$j]->[0] = "" if ( $values_utype[$j]->[0] =~ /NULL/ && $update_type ne "NULL" );
#        print "<option>$values_utype[$j]->[0]</option>" if ( $values_utype[$j]->[0] ne "$update_type" );
#        $j++;
#}
#print "</select>\n";
#print "</td>";
#
#print "<td><input name=\"entries_per_page_hosts\" type=\"hidden\" value=\"$entries_per_page_hosts\"><input name=\"start_entry_hosts\" type=\"hidden\" value=\"$start_entry_hosts\"><input name=\"knownhosts\" type=\"hidden\" value=\"$knownhosts\"><input name=\"anz_values_hosts\" type=\"hidden\" value=\"$anz_values_hosts\"></td></tr>\n";
#
#
#
my %cc_value = ();
my @custom_columns = $gip->get_custom_host_columns("$client_id");
%cc_value=$gip->get_custom_host_columns_from_net_id_hash("$client_id","$host_id") if $host_id;
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","host");
#
#print "<table border=\"0\" cellpadding=\"0\" style=\"border-collapse:collapse\">\n";
#print "<tr><td colspan='3'><p></td></tr>\n";
#if ( $custom_columns[0] ) {
#        print "<tr><td colspan='3'> <b>$$lang_vars{custom_host_columns_message}</b></td></tr>\n";
#}
#print "<tr><td colspan='3'><p></td></tr>\n";
#
my @vendors = $gip->get_vendor_array();

$j=0;
my %cc_mandatory_check_hash;
foreach ( @custom_columns ) {
	my $column_name=$custom_columns[$j]->[0];
	my $mandatory=$custom_columns[$j]->[4];
	$cc_mandatory_check_hash{$column_name}++ if $mandatory;
	$j++;
}

my $required;
my $form_elements_cm = "";


my $n=0;

foreach my $cc_ele(@custom_columns) {

	my $cc_name = $custom_columns[$n]->[0] || "";
	my $pc_id = $custom_columns[$n]->[3];
	my $cc_id = $custom_columns[$n]->[1];
	my $cc_entry = $cc_value{$cc_id}[1] || "";
	if ( $cc_name eq "Line" || $cc_name eq "Tag" || $cc_name eq "VLAN" || $cc_name eq "Sec_Zone" ) {
        # Ignore 
        $n++;
        next;
	}
	if ( $daten{'OS'} && $cc_name eq "OS" ) {
		$cc_entry = $daten{'OS'};	
	}
	if ( $daten{'OS_version'} && $cc_name eq "OS_version" ) {
		$cc_entry = $daten{'OS_version'};	
	}
	if ( $daten{'MAC'} && $cc_name eq "MAC" ) {
		$cc_entry = $daten{'MAC'};	
	}

	$required = "";
	$required = "required" if exists $cc_mandatory_check_hash{$cc_name};

	if ( $cc_name ) {
        if ( exists $custom_colums_select{$cc_id} ) {
            # CC column is a select


                my $select_values = $custom_colums_select{$cc_id}->[2];
                my $selected = "";

                $j = 0;
                @item_order = ();
                push @item_order, "";
                foreach my $opt(@$select_values) {
                    $opt = $gip->remove_whitespace_se("$opt");
                    push @item_order, $opt;
                    $j++;
                }

                $form_elements .= GipTemplate::create_form_element_select(
                    name => $cc_name,
                    item_order => \@item_order,
                    selected_value => $cc_entry,
                    id => "custom_${n}_value",
                    width => "10em",
                    required => $required,
                );

                $form_elements .= GipTemplate::create_form_element_hidden(
                    value => $cc_name,
                    name => "custom_${n}_name",
                );

                $form_elements .= GipTemplate::create_form_element_hidden(
                    value => $cc_id,
                    name => "custom_${n}_id",
                );

				$form_elements .= GipTemplate::create_form_element_hidden(
					name => "custom_${n}_pcid",
					value => $pc_id,
				);

                $n++;
                next;






#            my $select_values = $custom_colums_select{$cc_id}->[2];
#			my $selected = "";
#
#			print "<tr><td><b>$cc_name</b></td><td></td><td><input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\"><select name=\"custom_${n}_value\" size=\"1\">\n";
#			print "<option></option>";
#			foreach (@$select_values) {
#				my $opt = $_;
#				$opt = $gip->remove_whitespace_se("$opt");
#				$selected = "";
#				$selected = "selected" if $opt eq $cc_entry;
#				print "<option value=\"$opt\" $selected>$opt</option>";
#			}
#			print "</select></td></tr>\n";
#            $n++;
#            next;
		}
		if ( $cc_name eq "vendor" ) {
			my $knownvendor="0";
			foreach (@vendors) {
				if ( $cc_entry =~ /$_/i ) {
					$knownvendor=1; 
					last;
				}
			}
			my $checked_known="";
			my $checked_unknown="";
			my $disabled_known="";
			my $disabled_unknown="";
			my $cc_entry_unknown="";
			if ( $knownvendor == 1 ) {
				$checked_known="checked";
				$disabled_unknown="disabled";
			} elsif ( ! $cc_entry  ) {
				$checked_known="checked";
				$disabled_unknown="disabled";
			} else {
				$checked_unknown="checked";
				$disabled_known="disabled";
				$cc_entry_unknown=$cc_entry;
			}

			@item_order = ();
			push @item_order, "";

			my %option_style;

			my $j=0;
			my $vendor_found=0;
			foreach (@vendors) {
				my $vendor=$vendors[$j];
				my $vendor_img;
				if ( $vendor =~ /(lucent|alcatel)/i ) {
					$vendor_img="lucent-alcatel";
				} elsif ( $vendor =~ /(borderware)/i ) {
					$vendor_img="watchguard";
				} elsif ( $vendor =~ /(dlink|d-link)/i ) {
					$vendor_img="dlink";
				} elsif ( $vendor =~ /(cyclades)/i ) {
					$vendor_img="avocent";
				} elsif ( $vendor =~ /(eci telecom)/i ) {
					$vendor_img="eci";
				} elsif ( $vendor =~ /(^hp)/i ) {
					$vendor="hp";
					$vendor_img="hp";
				} elsif ( $vendor =~ /(minolta)/i ) {
					$vendor_img="konica";
				} elsif ( $vendor =~ /(okilan)/i ) {
					$vendor_img="oki";
				} elsif ( $vendor =~ /(phaser)/i ) {
					$vendor_img="xerox";
				} elsif ( $vendor =~ /(tally|genicom)/i ) {
					$vendor_img="tallygenicom";
				} elsif ( $vendor =~ /(seiko|infotec)/i ) {
					$vendor_img="seiko_infotec";
				} elsif ( $vendor =~ /(^palo)/i ) {
					$vendor="paloalto";
					$vendor_img="palo_alto";
				} elsif ( $vendor =~ /(silverpeak)/i ) {
					$vendor_img="silver_peak";
				} elsif ( $vendor =~ /(general.electric)/i ) {
					$vendor_img="ge";
				} elsif ( $vendor =~ /(western.digital)/i ) {
					$vendor_img="wd";
				} else {
					$vendor_img=$vendor;
				}

				if ( $cc_entry && $vendors[$j] eq "kyocera" && $cc_entry =~ /$vendors[$j]/i ) {
#					print "<option value=\"$vendor\" style=\"background: url(../imagenes/vendors/$vendor_img.png) no-repeat top left;\" selected>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $vendor</option>";
					$vendor_found=1;
				} elsif ( $cc_entry && $cc_entry =~ /$vendors[$j]/i && $vendor_found == 0 ) {
#					print "<option value=\"$vendor\" style=\"background: url(../imagenes/vendors/$vendor_img.png) no-repeat top left;\" selected>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $vendor</option>";
				} else {
#					print "<option value=\"$vendor\" style=\"background: url(../imagenes/vendors/$vendor_img.png) no-repeat top left;\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $vendor</option>";
				}

				push @item_order, "$vendor";
				$option_style{"$vendor"} = "style=\"background: url(../imagenes/vendors/$vendor_img.png) no-repeat top left;\"";
				$j++;
			}

			my $before_text_span_id = "vendor_radio_span_select";
			my $before_text = "<input type=\"radio\" name=\"vendor_radio\" value=\"known\" onclick=\"custom_${n}_value_known.disabled=false;custom_${n}_value_unknown.value='';custom_${n}_value_unknown.disabled=true;\" $checked_known>";

			foreach my $name(@vendors) {
				push @item_order, $name;
			}

			$form_elements .= GipTemplate::create_form_element_select(
				name => $cc_name,
				item_order => \@item_order,
				selected_value => $cc_entry,
				id => "custom_${n}_value_known",
				width => "10em",
				option_style => \%option_style,
				before_text => $before_text,
				before_text_span_id => $before_text_span_id,
				disabled => $disabled_known,
			);




			$before_text_span_id = "vendor_radio_span_text";
			$before_text = "<input type=\"radio\" name=\"vendor_radio\" value=\"unknown\" onclick=\"custom_${n}_value_known.disabled=true;custom_${n}_value_unknown.disabled=false;document.ip_mod_form.custom_${n}_value_known.options[0].selected = true;\" $checked_unknown>";

            my $entry_unknown = "";
            $entry_unknown = $cc_entry if $knownvendor == 0;

			$form_elements .= GipTemplate::create_form_element_text(
				value => $entry_unknown,
				id => "custom_${n}_value_unknown",
				maxlength => 500,
				before_text => $before_text,
				before_text_span_id => $before_text_span_id,
				disabled => $disabled_unknown,
			);


			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_name",
				value => $cc_name,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_id",
				value => $cc_id,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_pcid",
				value => $pc_id,
			);





#			print "<tr><td></td><td><input type=\"radio\" name=\"vendor_radio\" value=\"unknown\" onclick=\"custom_${n}_value_known.disabled=true;custom_${n}_value_unknown.disabled=false;document.ip_mod_form.custom_${n}_value_known.options[0].selected = true;\" $checked_unknown></td><td><input type=\"text\" size=\"20\" name=\"custom_${n}_value_unknown\" id=\"custom_${n}_value_unknown\" value=\"$cc_entry_unknown\" maxlength=\"500\" $disabled_unknown></td></tr>\n";






		} elsif ( $cc_name eq "SNMPGroup" ) {


                my @snmp_groups=$gip->get_snmp_groups("$client_id");

                $j=0;
                if ( ! $snmp_groups[0] ) {

                    $form_elements .= GipTemplate::create_form_element_comment(
                        label => "SNMPGroup",
                        comment => "<font color=\"gray\"><i>$$lang_vars{no_snmp_groups_message}</i></font>",
                        id => "custom_${n}_value",
                    );

                } else {

                    $j = 0;
                    @item_order = ();
                    push @item_order, "";
                    foreach my $opt(@snmp_groups) {
                        $opt_name = $snmp_groups[$j]->[1];
                        push @item_order, $opt_name;
                        $j++;
                    }

                    $form_elements .= GipTemplate::create_form_element_select(
                        name => $cc_name,
                        item_order => \@item_order,
                        selected_value => $cc_entry,
                        id => "custom_${n}_value",
                        width => "10em",
                    );


                    $form_elements .= GipTemplate::create_form_element_hidden(
                        name => "custom_${n}_name",
                        value => $cc_name,
                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        name => "custom_${n}_id",
                        value => $cc_id,
                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        name => "custom_${n}_pcid",
                        value => $pc_id,
                    );
                }

#			my @snmp_groups = $gip->get_snmp_groups("$client_id");
#			$j=0;
#			if ( ! $snmp_groups[0] ) {
#				print "<tr><td><b>$cc_name</b></td><td><i>$$lang_vars{no_snmp_groups_message}</i>";
#			} else {
#				print "<tr><td><b>$cc_name</b></td><td></td>";
#				print "<td><select name=\"custom_${n}_value\" size=\"1\">";
#				print "<option></option>";
#				foreach ( @snmp_groups ) {
#					my $snmp_group_name = $snmp_groups[$j]->[1];
#					if ( $cc_entry eq "$snmp_group_name" ) {
#
#						print "<option selected>$snmp_group_name</option>\n";
#					} else {
#						print "<option>$snmp_group_name</option>\n";
#					}
#					$j++;
#				}
#				print "</select>\n";
#				print "<input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";

#			}
#			print "</td></tr>\n";
		} elsif ( $cc_name eq "URL" ) {



			$form_elements .= GipTemplate::create_form_element_textarea(
				label => "$cc_name (service::URL)",
				value => $cc_entry,
				rows => '5',
				cols => '30',
				id => "custom_${n}_value",
				width => "10em",
				maxlength => 500,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_name",
				value => $cc_name,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_id",
				value => $cc_id,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_pcid",
				value => $pc_id,
			);


#			print "<tr><td><b>$cc_name</b><br>(service::URL)</td><td colspan='2'><input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\"><textarea name='custom_${n}_value' cols='50' rows='5' wrap='physical' maxlength='500'>$cc_entry</textarea></td></tr>\n";

		} elsif ( $cc_name eq "linkedIP" ) {
			$linked_ip=$cc_entry if ! $linked_ip;
			my $no_create_linked_entry_checked="";
			$no_create_linked_entry_checked="checked" if $linked_ip =~ /^X::/;
			$linked_ip =~ s/^X:://;


			my $hint_text = "<input type=\"checkbox\" name=\"no_create_linked_entry\" value=\"y\" $no_create_linked_entry_checked> $$lang_vars{no_create_linked_entry}";
			my $hint_text_span_id = "no_create_linked_entry_span_id";


			$form_elements .= GipTemplate::create_form_element_text(
				label => $cc_name,
				value => $linked_ip,
				id => "custom_${n}_value",
				maxlength => 3000,
				hint_text => $hint_text,
				hint_text_span_id => $hint_text_span_id,
			);


            $form_elements .= GipTemplate::create_form_element_hidden(
                name => "custom_${n}_name",
                value => $cc_name,
            );

            $form_elements .= GipTemplate::create_form_element_hidden(
                name => "custom_${n}_id",
                value => $cc_id,
            );

            $form_elements .= GipTemplate::create_form_element_hidden(
                name => "custom_${n}_pcid",
                value => $pc_id,
            );



#			print "<tr><td><b>$cc_name</b></td><td></td><td><input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\"><input type=\"text\" size=\"20\" name=\"custom_${n}_value\" value=\"$linked_ip\" maxlength=\"3000\"> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $$lang_vars{no_create_linked_entry} <input type=\"checkbox\" name=\"no_create_linked_entry\" value=\"y\" $no_create_linked_entry_checked> </td></tr>\n";

		} elsif ( $cc_name eq "CM" ) {

			my %values_device_config;
			%values_device_config=$gip->get_device_cm_hash("$client_id","$host_id") if $host_id;


			my $cm_enabled = "no";
			my $cm_conf_file = "/usr/share/gestioip/etc/cmm.conf";
			my $cm_licence_key = "";
			my $cm_backup_dir = "";
			my $cm_log_dir = "";
			my $cm_xml_dir = "";

			if ( -r $cm_conf_file ) {
				open(CM_CONF, "<$cm_conf_file");
				while (<CM_CONF>) {
					if ( $_ =~ /^cm_license_key/ ) {
						$_ =~ /^cm_license_key=(.*)$/;
						$cm_licence_key = $1 || "";
					} elsif ( $_ =~ /^backup_file_directory/ ) {
						$_ =~ /^backup_file_directory=(.*)$/;
						$cm_backup_dir = $1;
					} elsif ( $_ =~ /^log_directory/ ) {
						$_ =~ /^log_directory=(.*)$/;
						$cm_log_dir = $1;
					} elsif ( $_ =~ /^job_definition_directory/ ) {
						$_ =~ /^job_definition_directory=(.*)$/;
						$cm_xml_dir = $1;
					} else {
						next;
					}
				}
				close CM_CONF;

				$cm_enabled = "yes" if $cm_licence_key;
			} else {
				# compatibiltiy with version <3.5
				$cm_enabled = $global_config[0]->[8] || "no";
				$cm_licence_key=$global_config[0]->[10] || "";
				$cm_xml_dir=$global_config[0]->[12] || "";
			}

			my $enable_cm_checkbox_disabled="";
			my $cm_note="";
			my ($return_code,$cm_licence_key_message,$device_count)=$gip->check_cm_licence("$client_id","$vars_file","$cm_licence_key");
			my $device_count_enabled=$gip->get_cm_host_count("$client_id") || 0;
            $device_count = 0 if ! $device_count;

			if ( $cm_enabled ne "yes" ) {
				$cm_note="<font color=\"red\"><b>" . $$lang_vars{cm_management_disabled_message} . "<br>" . $$lang_vars{enable_cm_managemente_help_message} . "</b></font>";
				$enable_cm_checkbox_disabled="disabled";
			} elsif ( $device_count < $device_count_enabled && !keys %values_device_config ) {
			# license host count exceeded, only for new hosts
				$cm_note="<b><font color=\"red\">" . $$lang_vars{host_count_exceeded_message} . "</font><br>" . $$lang_vars{number_of_supported_cm_hosts_message} . ": " . $device_count . "<br>" . $$lang_vars{number_of_new_cm_hosts_message} . ": " . $device_count_enabled . "<p>";
				$enable_cm_checkbox_disabled="disabled";
			} elsif ( $return_code != 0 && $return_code != 2 ) {
				# valid or expire warn
				$cm_note="<font color=\"red\"><b>" . $$lang_vars{cm_management_disabled_message} . "<br>" . $cm_licence_key_message . "<br" .  $$lang_vars{cm_management_disabled_message} . "</b></font>";
				$enable_cm_checkbox_disabled="disabled";
			}

			$cm_val="disabled" if ! $cm_val;


			my %values_device_type_groups=$gip->get_device_type_values("$client_id","$cm_xml_dir");
			my %values_device_user_groups=$gip->get_device_user_groups_hash("$client_id");
			my %values_cm_server=$gip->get_cm_server_hash("$client_id");
			my %values_other_jobs;
			my $anz_values_other_jobs=0;
			%values_other_jobs = $gip->get_cm_jobs("$client_id","$host_id","job_id") if $host_id;
			$anz_values_other_jobs=keys(%{$values_other_jobs{$host_id}}) if $host_id;

			my ($cm_id,$device_type_group_id,$device_user_group_id,$user_name,$login_pass,$enable_pass,$description,$connection_proto,$connection_proto_port,$cm_server_id,$save_config_changes);
			$device_type_group_id=$device_user_group_id=$user_name=$login_pass=$enable_pass=$description=$connection_proto=$connection_proto_port=$cm_server_id=$save_config_changes="";

			if ( $host_id ) {
				for my $key ( sort keys %values_device_config ) {
					$cm_id=$key;
					$device_type_group_id=$values_device_config{$key}[1] || "";
					$device_user_group_id=$values_device_config{$key}[2] || "";
					if ( ! $device_user_group_id ) {
						$user_name=$values_device_config{$key}[3] || "";
						$login_pass=$values_device_config{$key}[4] || "";
						$enable_pass=$values_device_config{$key}[5] || "";
					}
					$description=$values_device_config{$key}[6] || "";
					$connection_proto=$values_device_config{$key}[7] || "";
					$connection_proto_port=$values_device_config{$key}[13] || "";
					$cm_server_id=$values_device_config{$key}[8] || "";
					$save_config_changes=$values_device_config{$key}[9] || "";
				}
			}

			my $device_type_group_id_preselected=$device_type_group_id || 1;
			my $jobs=$values_device_type_groups{$device_type_group_id_preselected}[2] || "";
			my %jobs=();
			if ( $jobs ) {
				%jobs=%$jobs;
			}


print <<EOF;

<script type="text/javascript">
<!--
function changerows(ID,ANZ_OTHER_JOBS) {
value=ID.options[ID.selectedIndex].value
EOF

my $m=0;
for my $id ( keys %values_device_type_groups ) {
        if ( $m == 0 ) {
                print "  if ( value == \"$id\" ) {\n";
        } else {
                print "  } else if ( value == \"$id\" ) {\n";
        }

        print "    var values_job_names=new Array(\"\"";
	my $jobs_j=$values_device_type_groups{$id}[2] || "";
	my %jobs_j=();
	if ( $jobs_j ) {
		%jobs_j=%$jobs_j;
	}
	

	for my $job_name ( keys %{$jobs_j{$id}} ) {
                print ",\"$job_name\"";
        }
        print ")\n";



        print "    var values_job_descr=new Array(\"\"";
	for my $job_name ( keys %{$jobs_j{$id}} ) {
		my $job_description=$jobs_j{$id}{$job_name}[0] || "";
		$job_description=~s/"/\\"/g;
                print ",\"$job_description\"";
        }
        print ")\n";

        $m++;
}
print "  }\n";

print <<EOF;
var OTHER_JOB_ID
var OTHER_JOB_GROUP_ID
var OTHER_JOB_DESCR
for(j=0;j<30;j++){
            OTHER_JOB_ID='device_other_job_' + j
            OTHER_JOB_GROUP_ID='other_job_group_' + j
            OTHER_JOB_DESCR='other_job_descr_' + j 
            document.getElementById(OTHER_JOB_ID).options.length=values_job_names.length
            document.getElementById(OTHER_JOB_ID).options[0].selected=true
            document.getElementById(OTHER_JOB_GROUP_ID).options[0].selected=true
            document.getElementById(OTHER_JOB_DESCR).value='';
}

for(i=0;i<values_job_names.length;i++){
        for(j=0;j<30;j++){
            OTHER_JOB_ID='device_other_job_' + j
            document.getElementById(OTHER_JOB_ID).options[i].text=values_job_descr[i]
            document.getElementById(OTHER_JOB_ID).options[i].value=values_job_names[i]
            document.getElementById(OTHER_JOB_ID).options[0].selected=true
        }
}

}
-->
</script>

<script type="text/javascript">
<!--

function show_host_ip_field(ID) {
var BUTTON_ID='plus_button_' + ID
document.getElementById(BUTTON_ID).value='';
document.getElementById(BUTTON_ID).style.display='none';
ID++
var OTHER_JOB_ID='other_job_group_form_' + ID
document.getElementById(OTHER_JOB_ID).style.display='inline';
}

-->
</script>


<script type="text/javascript">
<!--

function delete_job(ID) {
var OTHER_JOB_ID='device_other_job_' + ID
var OTHER_JOB_GROUP_ID='other_job_group_' + ID
var OTHER_JOB_DESCR='other_job_descr_' + ID
document.getElementById(OTHER_JOB_ID).options[0].selected=true
document.getElementById(OTHER_JOB_GROUP_ID).options[0].selected=true
document.getElementById(OTHER_JOB_DESCR).value='';
}

-->
</script>

EOF

			$form_elements_cm .= "<tr><td colspan=\"3\">\n";
			$form_elements_cm .= "<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\">\n";

			my $enable_cm_checked="";
			my $enable_cm_disabled="";
			my $enable_cm_bg_color="white";
			$enable_cm_checked="checked" if $cc_entry eq "enabled";
			$enable_cm_disabled="disabled" if $cc_entry ne "enabled" || $enable_cm_checkbox_disabled eq "disabled";
			$enable_cm_bg_color=$disabled_color if $cc_entry ne "enabled" || $enable_cm_checkbox_disabled eq "disabled";
			my $save_config_changes_checked="";
			$save_config_changes_checked="checked" if $save_config_changes;


			$form_elements_cm .= "<tr><td><br><b>$$lang_vars{CM_message}</b></td><td>";
			$form_elements_cm .= "<tr><td colspan=\"2\">$cm_note</td><td>" if $cm_note;

			$form_elements_cm .= "<tr><td>$$lang_vars{enable_cm_host_message}</td><td><input name=\"enable_cm\" type=\"checkbox\" value=\"enable_cm\" $enable_cm_checked onchange=\"mod_cm_fields(\'$anz_values_other_jobs\');\" $enable_cm_checkbox_disabled></td></tr>\n";
			$form_elements_cm .= "<tr><td><span id=\"delete_cm_checkbox_span\" style=\"display:none;\">$$lang_vars{delete_cm_configuration_message}</span></td><td> <input name=\"delete_cm_all\" id=\"delete_cm_checkbox\" type=\"checkbox\" value=\"delete_cm_all\" style=\"display:none;\">\n";
			$form_elements_cm .= "</td></tr>";


			$form_elements_cm .= "<tr><td>$$lang_vars{device_type_group_message}</td><td>";
			if ( scalar keys %values_device_type_groups >= 1 ) {
				$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' style='width: 12em;' name=\"device_type_group_id\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" onchange=\"changerows(this,\'$anz_values_other_jobs\');\" $enable_cm_disabled>";
#				print "<option></option>\n";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_device_type_groups{$a}[0] cmp $values_device_type_groups{$b}[0] } keys %values_device_type_groups ) {

					my $device_type_group_name=$values_device_type_groups{$key}[0];
					if ( $device_type_group_id eq $key ) {
#						print "<option value=\"$key\" selected>$device_type_group_name</option>\n";
						$form_elements_cm .= "<option value=\"$key\" selected>$device_type_group_name</option>\n";
					} else {
#						print "<option value=\"$key\">$device_type_group_name</option>\n";
						$form_elements_cm .= "<option value=\"$key\">$device_type_group_name</option>\n";
					}
				}
#				print "</select></td></tr>\n";
				$form_elements_cm .= "</select></td></tr>\n";
			} else {
#				print "&nbsp;<font color=\"gray\"><input name=\"device_type_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_device_type_group_message}</i></font>\n";
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_type_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_device_type_group_message}</i></font>\n";
			}


#			print "<tr><td><br></td></tr>\n";
			$form_elements_cm .= "<tr><td><br></td></tr>\n";





			my $device_user_group_disabled="";
			my $individual_user_disabled="";
			my $device_user_select_background="white";
			my $display_device_user_group="inline";
			my $display_individual_user="none";
			if ( $user_name || $login_pass || $enable_pass ) {
				$device_user_group_disabled="disabled";
				$device_user_select_background="#F0EDEA";
				$display_device_user_group="none";
				$display_individual_user="inline";

				$form_elements_cm .= "<tr><td colspan=\"2\">$$lang_vars{use_device_user_group_message} <input name=\"ele_auth\" type=\"radio\" value=\"group\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled> $$lang_vars{use_device_individual_user_message}\n";
				$form_elements_cm .="<input name=\"ele_auth\" type=\"radio\" value=\"individual\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled checked></td></tr>\n";
			} else {
				$individual_user_disabled="disabled";
				$device_user_group_disabled="disabled" if $cc_entry ne "enabled" || $enable_cm_checkbox_disabled eq "disabled";
				$device_user_select_background="#F0EDEA" if $cc_entry ne "enabled" || $enable_cm_checkbox_disabled eq "disabled";
				$form_elements_cm .= "<tr><td colspan=\"2\">$$lang_vars{use_device_user_group_message} <input name=\"ele_auth\" type=\"radio\" value=\"group\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled checked> $$lang_vars{use_device_individual_user_message}\n";
				$form_elements_cm .="<input name=\"ele_auth\" type=\"radio\" value=\"individual\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled></td></tr>\n";
			}


			$form_elements_cm .= "<tr><td>\n";

			$form_elements_cm .= "<span id=\"cm_device_user_group\" style=\"display:$display_device_user_group;\">$$lang_vars{device_user_group_message}</span></td><td><span id=\"cm_device_user_group1\" style=\"display:$display_device_user_group;\">";
			if ( scalar keys %values_device_user_groups >= "1" ) {

				$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' style='width: 12em;' name=\"device_user_group_id\" size=\"1\" style=\"background-color: $device_user_select_background;\" $device_user_group_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_device_user_groups{$a}[0] cmp $values_device_user_groups{$b}[0] } keys %values_device_user_groups ) {
					my $device_user_group_name=$values_device_user_groups{$key}[0];
					if ( $device_user_group_id eq $key ) {
						$form_elements_cm .= "<option value=\"$key\" selected>$device_user_group_name</option>";
					} else {
						$form_elements_cm .= "<option value=\"$key\">$device_user_group_name</option>";
					}
				}
				$form_elements_cm .= "</select>\n";
			} else {
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_user_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_device_user_group_message}</i></font>\n";
			}


			$form_elements_cm .= "</span></td></tr>\n";



			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "<tr><td colspan=\"2\">\n";
			$form_elements_cm .= "<span id=\"cm_individual_user\" style=\"display:$display_individual_user;\">\n";
			$form_elements_cm .= "<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\">\n";


			$form_elements_cm .= "<tr><td>$$lang_vars{device_user_name_message}</td><td><input name=\"user_name\" type=\"text\" class='form-control form-control-sm' size=\"15\" maxlength=\"50\" value=\"$user_name\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{login_pass_message}</td><td><input name=\"login_pass\" type=\"password\" size=\"12\" maxlength=\"500\" value=\"$login_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{retype_login_pass_message}</td><td><input name=\"retype_login_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$login_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{enable_pass_message}</td><td><input name=\"enable_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$enable_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{retype_enable_pass_message}</td><td><input name=\"retype_enable_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$enable_pass\" $individual_user_disabled>\n";


			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "</table>\n";
			$form_elements_cm .= "</span>\n";



			$form_elements_cm .= "<tr><td><br></td></tr>\n";



			$form_elements_cm .= "<tr><td>\n";


			if ( ! $connection_proto_port && $connection_proto eq "telnet") {
				$connection_proto_port=23;
			} elsif ( ! $connection_proto_port && $connection_proto eq "SSH") {
				$connection_proto_port=22;
			}

			my @cm_connetion_type_values=("telnet","SSH");
			$form_elements_cm .= "\n$$lang_vars{connection_proto_message}</td><td><font size=\"2\"><select class='custom-select custom-select-sm' style='width: 6em;' style='width: 12em;' name=\"connection_proto\" size=\"1\" onchange=\"mod_connection_proto_port(this.value);\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
			$form_elements_cm .= "<option></option>";
			foreach (@cm_connetion_type_values) {
				if ( $_ eq $connection_proto ) {
					$form_elements_cm .= "<option selected>$_</option>\n";
				} else {
					$form_elements_cm .= "<option>$_</option>\n";
				}
			}
			$form_elements_cm .= "</select>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";
			$form_elements_cm .= "$$lang_vars{port_message}</td><td> <input name=\"connection_proto_port\" type=\"text\" class='form-control form-control-sm' style='width: 3em;'  size=\"3\" maxlength=\"5\" value=\"$connection_proto_port\" $enable_cm_disabled>\n";


			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{backup_server_message}</td><td>";
			if ( scalar keys %values_cm_server >= "1" ) {
				$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"cm_server_id\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_cm_server{$a}[0] cmp $values_cm_server{$b}[0] } keys %values_cm_server ) {

					my $cm_server_name=$values_cm_server{$key}[0];
					if ( $cm_server_id eq $key ) {
						$form_elements_cm .= "<option value=\"$key\" selected>$cm_server_name</option>\n";
					} else {
						$form_elements_cm .= "<option value=\"$key\">$cm_server_name</option>\n";
					}
				}
				$form_elements_cm .= "</select>\n";
			} else {
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"cm_server_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_cm_server_message}</i></font>\n";
			}

			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{save_config_changes_message}</td><td><input type=\"checkbox\" name=\"save_config_changes\" value=\"1\" $save_config_changes_checked $enable_cm_disabled>\n";


### JOBS
			$form_elements_cm .= "</td></tr><tr><td>\n";
			$form_elements_cm .= "<br><b><i>$$lang_vars{other_jobs_message}</i></b>";
			$form_elements_cm .= "</td></tr><tr><td>\n";

			my %job_groups=$gip->get_job_groups("$client_id");
			my $k=0;
			if ( $anz_values_other_jobs > 0 && $host_id ) {
				sub sort_sub {
					$a <=> $b;
				}
				for my $job_id ( sort sort_sub keys %{ $values_other_jobs{$host_id} } ) {
					my $job_name=$values_other_jobs{$host_id}{$job_id}[0];
					my $job_group_id=$values_other_jobs{$host_id}{$job_id}[1];
					my $job_descr=$values_other_jobs{$host_id}{$job_id}[2];
					my $job_enabled=$values_other_jobs{$host_id}{$job_id}[6] || 0;
					my $job_enabled_disabled="";
					my $job_enabled_readonly="";
					my $job_enabled_checked="";
					my $job_enabled_bg_color="white";
					$job_enabled_bg_color=$disabled_color if $job_enabled == 0 || $enable_cm_disabled eq "disabled";
					$job_enabled_readonly="readonly" if $job_enabled == 0;
					$job_enabled_disabled="disabled" if $job_enabled == 0;
					$job_enabled_checked="checked" if $job_enabled == 1;

					$form_elements_cm .= "<tr><td><br></td><td></td></tr>\n";
					$form_elements_cm .= "<tr><td>$$lang_vars{enable_message}</td><td>";
					$form_elements_cm .= "<input type=\"checkbox\" name=\"job_enabled_${k}\" id=\"job_enabled_${k}\" style=\"background-color:$job_enabled_bg_color\" onclick=\"disable_job($k);\" $enable_cm_disabled $job_enabled_checked>";
					$form_elements_cm .= "</td></tr>\n";
					$form_elements_cm .= "<tr><td>\n";
					$form_elements_cm .= "$$lang_vars{job_message}</td><td>";
					if ( scalar keys %jobs >= 1 ) {
						$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"device_other_job_${k}\" id=\"device_other_job_${k}\" size=\"1\" style=\"background-color:$job_enabled_bg_color; width: 230px;\" $enable_cm_disabled>";
						$form_elements_cm .= "<option $job_enabled_disabled></option>\n";
						for my $job_name1 ( keys %{ $jobs{$device_type_group_id} } ) {
								my $job_description=$jobs{$device_type_group_id}{$job_name1}[0] || "";
								if ( $job_name eq $job_name1 ) {
										$form_elements_cm .= "<option value=\"$job_name1\" selected>$job_description</option>\n";
								} else {
										$form_elements_cm .= "<option value=\"$job_name1\" $job_enabled_disabled>$job_description</option>\n";
								}
						}
						$form_elements_cm .= "</select>\n";


						$form_elements_cm .= "</td></tr><tr><td>\n";


						$form_elements_cm .= "$$lang_vars{description_message}</td><td><input name=\"other_job_descr_${k}\" id=\"other_job_descr_${k}\" type=\"text\" class='form-control form-control-sm' size=\"30\" maxlength=\"500\" value=\"$job_descr\" style=\"background-color:$job_enabled_bg_color;\" $enable_cm_disabled  $job_enabled_readonly>\n";


						$form_elements_cm .= "</td></tr><tr><td>\n";


						$form_elements_cm .= "$$lang_vars{job_group_message}</td><td>";
						$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"other_job_group_${k}\" id=\"other_job_group_${k}\" size=\"1\" style=\"background-color:$job_enabled_bg_color;\" $enable_cm_disabled>";
						$form_elements_cm .= "<option $job_enabled_disabled></option>\n";

						for my $job_group_all_id ( sort keys %job_groups ) {
							my $job_group_name=$job_groups{$job_group_all_id}[0];
								if ( $job_group_id eq $job_group_all_id ) {
										$form_elements_cm .= "<option value=\"$job_group_all_id\" selected>$job_group_name</option>\n";
								} else {
										$form_elements_cm .= "<option value=\"$job_group_all_id\" $job_enabled_disabled>$job_group_name</option>\n";
								}
						}
						$form_elements_cm .= "</select>\n";


						$form_elements_cm .= "</td></tr>\n<tr><td>\n";


						$form_elements_cm .= "<span id=\"delete_button_${k}\" onClick=\"delete_job('$k')\" class=\"delete_small_button\" title=\"$$lang_vars{delete_job_message}\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
						$form_elements_cm .= "<input name=\"device_other_job_id_${k}\" type=\"hidden\" value=\"$job_id\">";


					} else {
						$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_type_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_cm_jobs_message}</i></font>\n";
					}

					$k++;
				}
				$form_elements_cm .= "<input name=\"device_other_jobs_anz\" type=\"hidden\" value=\"$k\">\n";
			} else {
				$form_elements_cm .= "</td></tr><tr><td>\n";
				$form_elements_cm .= "$$lang_vars{enable_message}</td><td>";
				$form_elements_cm .= "<input type=\"checkbox\" name=\"job_enabled_0\" id=\"job_enabled_0\" style=\"background-color:$enable_cm_bg_color;\" onclick=\"disable_job($k);\" $enable_cm_disabled checked>";
				$form_elements_cm .= "</td></tr><tr><td>\n";

				$form_elements_cm .= "$$lang_vars{job_message}</td><td>";
				if ( scalar keys %jobs >= 1 ) {
					$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"device_other_job_0\" id=\"device_other_job_0\" size=\"1\" style=\"background-color:$enable_cm_bg_color; width: 230px;\" $enable_cm_disabled>";
					$form_elements_cm .= "<option></option>\n";
					for my $job_name ( keys %{ $jobs{$device_type_group_id} } ) {
						my $job_description=$jobs{$device_type_group_id}{$job_name}[0] || "";
						$form_elements_cm .= "<option value=\"$job_name\">$job_description</option>\n";
					}
					$form_elements_cm .= "</select>\n";
					$form_elements_cm .= "<input name=\"device_other_jobs_anz\" type=\"hidden\" value=\"1\">\n";

					$form_elements_cm .= "</td></tr><tr><td>\n";


					$form_elements_cm .= "$$lang_vars{description_message}</td><td><input name=\"other_job_descr_0\" id=\"other_job_descr_0\" type=\"text\" class='form-control form-control-sm' size=\"30\" maxlength=\"500\" value=\"\" $enable_cm_disabled>\n";

					$form_elements_cm .= "</td></tr><tr><td>\n";


					$form_elements_cm .= "$$lang_vars{job_group_message}</td><td>";
					$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"other_job_group_0\" id=\"other_job_group_0\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
					$form_elements_cm .= "<option></option>\n";

					for my $job_group_all_id ( sort keys %job_groups ) {
						my $job_group_name=$job_groups{$job_group_all_id}[0];
						$form_elements_cm .= "<option value=\"$job_group_all_id\">$job_group_name</option>\n";
					}

					$form_elements_cm .= "</select>\n";
					$form_elements_cm .= "<input name=\"device_other_job_id_0\" type=\"hidden\" value=\"0\">";
					$form_elements_cm .= "</td></tr><tr><td>\n";
					$form_elements_cm .= "<span id=\"delete_button_${k}\" onClick=\"delete_job('$k')\" class=\"delete_small_button\" title=\"$$lang_vars{delete_job_message}\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
					$k++;

				} else {
					$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_type_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_cm_jobs_message}</i></font>\n";
				}
			}

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "<span id=\"plus_button_${k}\" onClick=\"show_host_ip_field('$k')\" class=\"add_small_button\" title=\"$$lang_vars{add_job_message}\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";


			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "<tr><td><br></td></tr>\n";

			for ( ; $k<=30; $k++ ) {

				$form_elements_cm .= "<tr><td colspan=\"2\">\n";
				$form_elements_cm .= "<span id=\"other_job_group_form_${k}\" style='display:none;'>\n";
				$form_elements_cm .= "<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\" width=\"100%\">\n";
				$form_elements_cm .= "<tr><td>$$lang_vars{enable_message}</td><td>";
				$form_elements_cm .= "<input type=\"checkbox\" name=\"job_enabled_${k}\" id=\"job_enabled_${k}\" style=\"background-color:$enable_cm_bg_color\" onclick=\"disable_job($k);\" $enable_cm_disabled checked>";
				$form_elements_cm .= "</td></tr>\n";
				$form_elements_cm .= "<tr><td width=\"50%\">$$lang_vars{job_message}\n";
				$form_elements_cm .= "</td><td>\n";

				$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"device_other_job_${k}\" id=\"device_other_job_${k}\" size=\"1\" style=\"background-color:$enable_cm_bg_color; width: 230px;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $job_name ( keys %{ $jobs{$device_type_group_id} } ) {
					my $job_description=$jobs{$device_type_group_id}{$job_name}[0] || "";
					$form_elements_cm .= "<option value=\"$job_name\">$job_description</option>\n";
				}
				$form_elements_cm .= "</select>\n";

				$form_elements_cm .= "</td></tr><tr><td>\n";

				$form_elements_cm .= "$$lang_vars{description_message}</td><td><input name=\"other_job_descr_${k}\" id=\"other_job_descr_${k}\" type=\"text\" class='form-control form-control-sm' size=\"30\" maxlength=\"500\" value=\"\" $enable_cm_disabled>\n";

				$form_elements_cm .= "</td></tr><tr><td>\n";


				$form_elements_cm .= "$$lang_vars{job_group_message}\n";
				$form_elements_cm .= "</td><td>\n";
				$form_elements_cm .= "<select class='custom-select custom-select-sm' style='width: 12em;' name=\"other_job_group_${k}\" id=\"other_job_group_${k}\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";

				for my $job_group_all_id ( sort keys %job_groups ) {
					my $job_group_name=$job_groups{$job_group_all_id}[0];
					$form_elements_cm .= "<option value=\"$job_group_all_id\">$job_group_name</option>\n";
				}
				$form_elements_cm .= "</select>\n";


				$form_elements_cm .= "</td></tr><tr><td>\n";


				$form_elements_cm .= "<span id=\"delete_button_${k}\" onClick=\"delete_job('$k')\" class=\"delete_small_button\" title=\"$$lang_vars{delete_job_message}\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
				$form_elements_cm .= "</td></tr><tr><td>\n";

				$form_elements_cm .= "<span id=\"plus_button_${k}\" onClick=\"show_host_ip_field('$k')\" class=\"add_small_button\" title=\"$$lang_vars{add_job_message}\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
				$form_elements_cm .= "</td></tr>\n";
#				print "<tr><td><br></td><td></td></tr>\n";
				$form_elements_cm .= "</table>\n";
				$form_elements_cm .= "</span></td></tr>\n";
			}



			$form_elements_cm .= "</table>\n";

			$form_elements_cm .= "<input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\"></td></tr>\n";
#			print "</td></tr>\n";
#			print "<p>\n";


		} else {

		   $required = "";
			$required = "required" if exists $cc_mandatory_check_hash{$cc_name};
			$form_elements .= GipTemplate::create_form_element_text(
				label => $cc_name,
				value => $cc_entry,
				id => "custom_${n}_value",
				maxlength => 500,
				required => $required,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_name",
				value => $cc_name,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_id",
				value => $cc_id,
			);

			$form_elements .= GipTemplate::create_form_element_hidden(
				name => "custom_${n}_pcid",
				value => $pc_id,
			);


#			print "<tr><td><b>$cc_name</b></td><td></td><td><input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\"><input type=\"text\" size=\"20\" name=\"custom_${n}_value\" value=\"$cc_entry\" maxlength=\"500\"></td></tr>\n";
		}
	$n++;
	}
}

my @tags = $gip->get_custom_host_column_ids_from_name("$client_id", "Tag");

my $form_elements_tag = "";
$form_elements_tag = $gip->print_tag_form("$client_id","$vars_file","$host_id","host") if @tags;

$form_elements .= $form_elements_tag;

if ( $global_dyn_dns_updates_enabled eq "yes" ) {

    @item_order = ();
    undef %items;

    push @item_order, $$lang_vars{'no_update_message'};
    $items{$$lang_vars{'no_update_message'}} = 1;
    push @item_order, $$lang_vars{'a_and_ptr_message'};
    $items{$$lang_vars{'a_and_ptr_message'}} = 2;
    push @item_order, $$lang_vars{'a_update_only_message'};
    $items{$$lang_vars{'a_update_only_message'}} = 3;
    push @item_order, $$lang_vars{'ptr_update_only_message'};
    $items{$$lang_vars{'ptr_update_only_message'}} = 4;


    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{update_mode_message},
        items => \%items,
        item_order => \@item_order,
        selected_value => $dyn_dns_updates,
        id => "dyn_dns_updates",
        width => "14em",
        size => 1,
    );

}

$form_elements .= $form_elements_cm;
$form_elements .= $form_elements_line;

if ( $CM_show_hosts ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $CM_show_hosts,
		name => "CM_show_hosts",
	);
} elsif ( $CM_show_hosts_by_jobs ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $CM_show_hosts_by_jobs,
		name => "CM_show_hosts_by_jobs",
	);
} elsif ( $CM_diff_form ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => 1,
		name => "CM_diff_form",
	);
}

if ( defined($daten{'text_field_number_given'}) ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => "text_field_number_given",
		name => "text_field_number_given",
	);
}

if ( ! $CM_show_hosts && ! $CM_show_hosts_by_jobs ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $red,
		name => "red",
	);

	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $BM,
		name => "BM",
	);
}



$form_elements .= GipTemplate::create_form_element_hidden(
    value => $host_id,
    name => "host_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $host_order_by,
    name => "host_order_by",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $ip_version,
    name => "ip_version",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $from_line,
    name => "from_line",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $search_index,
    name => "search_index",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $search_hostname,
    name => "search_hostname",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $match,
    name => "match",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $red_num,
    name => "red_num",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B1",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "ip_mod_form",
    link => "./ip_modip.cgi",
    method => "POST",
);

print $form;






print "<script type=\"text/javascript\">\n";
print "document.ip_mod_form.hostname.focus();\n";
print "</script>\n";

$gip->print_end("$client_id","$vars_file","", "$daten");

