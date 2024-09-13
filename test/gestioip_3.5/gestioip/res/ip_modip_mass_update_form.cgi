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
if ( $daten{'entries_per_page_hosts'} && $daten{'entries_per_page_hosts'} =~ /^\d{1,3}$/ ) {
        $entries_per_page_hosts=$daten{'entries_per_page_hosts'};
} else {
        $entries_per_page_hosts = "254";
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

my $loc_hash=$gip->get_loc_hash("$client_id");

my $mass_update_type=$daten{'mass_update_type'};

if ( $user_management_enabled eq "yes" && $mass_update_type eq "CM" || $mass_update_type =~ /^CM_/ || $mass_update_type =~ /_CM_/ || $mass_update_type =~ /_CM$/ ) {
	my $user=$ENV{'REMOTE_USER'};
	my %values_user_group_perms=$gip->get_user_group_perms_hash("$vars_file","","$user");
	if ( ! $values_user_group_perms{administrate_cm_perm} ) {
		$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{host_mass_update_message}","$vars_file");
		print "<p><br><b>$$lang_vars{following_permissions_missing}</b><br><p>\n";
		print "<ul>\n";
		print "<li><b><i>administrate_cm_perm</i></b></li>\n";
		print "</ul>\n";
		print "<br><p><br><b>$$lang_vars{contact_gip_admin_message}</b><p><br>\n";
		print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";
		$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	}
}
# permission check end

my $host_order_by = $daten{'host_order_by'} || "IP_auf";
my $ip_version = $daten{'ip_version'} || "";

my $search_index=$daten{'search_index'} || "";
my $search_hostname=$daten{'search_hostname'} || "";
my $match=$daten{'match'} || "";

my $red_num=$daten{'red_num'} || "";
$red_num = "" if $search_index eq "true";
my $loc=$daten{'loc'} || "";
$loc = "" if $loc eq "---";

my $text_field_number_given_form = "";
if ( defined($daten{'text_field_number_given'}) ) {
	$text_field_number_given_form="<input name=\"text_field_number_given\" type=\"hidden\" value=\"text_field_number_given\">";
}


#Detect call from ip_show_cm_hosts.cgi and ip_list_device_by_job.cgi
my $CM_show_hosts=$daten{'CM_show_hosts'} || "";
my $CM_show_hosts_by_jobs=$daten{'CM_show_hosts_by_jobs'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{host_mass_update_message}","$vars_file");

my $mass_update_type_orig=$mass_update_type;
$gip->print_error("$client_id","$$lang_vars{select_mass_update_type}") if ! $mass_update_type;
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

my $anz_hosts=$daten{'anz_hosts'} || 0;


my $k;
my $j=0;
my $mass_update_host_ids="";
for ($k=0;$k<=$anz_hosts;$k++) {
	if ( $daten{"mass_update_host_submit_${k}"} ) {
        if ( ! $ip_version ) {
            if ( $daten{"mass_update_host_submit_${k}"} =~ /^\d{1,3}\./ ) {
                $ip_version = "v4";
            } else {
                $ip_version = "v6";
            }
        }
		$mass_update_host_ids.=$daten{"mass_update_host_submit_${k}"} . "_";
		$j++;
	}
}
$mass_update_host_ids =~ s/_$//;

my $anz_hosts_update=$j;

$gip->print_error("$client_id","$$lang_vars{select_host_message}") if ! $mass_update_host_ids;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} $mass_update_host_ids (1)") if ($mass_update_host_ids !~ /[0-9_]/ );
my @mass_update_host_ids_arr=split("_",$mass_update_host_ids);
#my $mass_update_host_ids_arr_ref=\@mass_update_host_ids_arr;


my $utype = $daten{'update_type'};
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'anz_values_hosts'} && $daten{'anz_values_hosts'} !~ /^\d{2,4}||no_value$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'knownhosts'} && $daten{'knownhosts'} !~ /^all|hosts|libre$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $daten{'start_entry_hosts'} && $daten{'start_entry_hosts'} !~ /^\d{1,20}$/;
my $anz_values_hosts = $daten{'anz_values_hosts'} || "no_value";

my $start_entry_hosts=$daten{'start_entry_hosts'} || '0';
my $knownhosts=$daten{'knownhosts'} || 'all';
my $host_id=$daten{'host_id'} || "";

#print "<p>\n";

my @values_redes = $gip->get_red("$client_id","$red_num");

my $red="";
my $BM="";
if ( $values_redes[0]->[0] ) {
	$red = $values_redes[0]->[0] || "";
	$BM = $values_redes[0]->[1] || "";
}

my @values_locations=$gip->get_loc("$client_id");
my @values_categorias=$gip->get_cat("$client_id");
my @values_utype=$gip->get_utype();

my $disabled_color='#F0EDEA';


print <<EOF;


<script type="text/javascript">
<!--
function mod_cm_fields(ANZ_OTHER_JOBS){
//ANZ_OTHER_JOBS++
  if(ip_mod_form.enable_cm.checked == true){
    ip_mod_form.connection_proto.disabled=false;
    ip_mod_form.connection_proto.style.backgroundColor="white";
    ip_mod_form.connection_proto_port.disabled=false;
    ip_mod_form.connection_proto_port.style.backgroundColor="white";
    ip_mod_form.device_type_group_id.disabled=false;
    ip_mod_form.device_type_group_id.style.backgroundColor="white";
    ip_mod_form.save_config_changes.disabled=false;
    ip_mod_form.save_config_changes.style.backgroundColor="white";
    ip_mod_form.cm_server_id.disabled=false;
    ip_mod_form.cm_server_id.style.backgroundColor="white";
    ip_mod_form.exclude_device_user_group.disabled=false;
    ip_mod_form.exclude_connection_proto.disabled=false;
    ip_mod_form.exclude_cm_server_id.disabled=false;
    ip_mod_form.exclude_save_config_changes.disabled=false;
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

    for(j=0;j<60;j++){
        OTHER_JOB_ID='device_other_job_' + j
        OTHER_JOB_GROUP_ID='other_job_group_' + j
        OTHER_JOB_DESCR='other_job_descr_' + j
        document.getElementById(OTHER_JOB_ID).disabled=false;
        document.getElementById(OTHER_JOB_ID).style.backgroundColor="white";
        document.getElementById(OTHER_JOB_GROUP_ID).disabled=false;
        document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="white";
        document.getElementById(OTHER_JOB_DESCR).disabled=false;
        document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="white";
    }
    ip_mod_form.delete_old_jobs.disabled=false;
//    ip_mod_form.delete_old_jobs.style.backgroundColor="white";


   }else{

    ip_mod_form.connection_proto.disabled=true;
    ip_mod_form.connection_proto.style.backgroundColor='$disabled_color';
    ip_mod_form.connection_proto_port.disabled=true;
    ip_mod_form.connection_proto_port.style.backgroundColor='$disabled_color';
    ip_mod_form.device_type_group_id.disabled=true;
    ip_mod_form.device_type_group_id.style.backgroundColor="$disabled_color";
    ip_mod_form.save_config_changes.disabled=true;
    ip_mod_form.save_config_changes.style.backgroundColor="$disabled_color";
    ip_mod_form.cm_server_id.disabled=true;
    ip_mod_form.exclude_device_user_group.disabled=true;
    ip_mod_form.exclude_connection_proto.disabled=true;
    ip_mod_form.exclude_cm_server_id.disabled=true;
    ip_mod_form.exclude_save_config_changes.disabled=true;
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

    for(j=0;j<60;j++){
        OTHER_JOB_ID='device_other_job_' + j
        OTHER_JOB_GROUP_ID='other_job_group_' + j
        OTHER_JOB_DESCR='other_job_descr_' + j
        document.getElementById(OTHER_JOB_ID).disabled=true;
        document.getElementById(OTHER_JOB_ID).style.backgroundColor="$disabled_color";
        document.getElementById(OTHER_JOB_GROUP_ID).disabled=true;
        document.getElementById(OTHER_JOB_GROUP_ID).style.backgroundColor="$disabled_color";
        document.getElementById(OTHER_JOB_DESCR).disabled=true;
        document.getElementById(OTHER_JOB_DESCR).style.backgroundColor="$disabled_color";
    }
    ip_mod_form.delete_old_jobs.disabled=true;
    ip_mod_form.delete_old_jobs.checked=false;
   }
}
//-->
</script>

<script type="text/javascript">
<!--
function change_delete_old_jobs_checkbox(){
  if(ip_mod_form.delete_cm_checkbox.checked == true){
    ip_mod_form.delete_old_jobs.checked=true;
    ip_mod_form.delete_old_jobs.disabled=true;
  }else{
//    ip_mod_form.delete_old_jobs.disabled=false;
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
function disable_djg(){
    if ( ip_mod_form.exclude_device_user_group.checked ) {
        ip_mod_form.ele_auth[0].disabled=true;
        ip_mod_form.ele_auth[1].disabled=true;
        ip_mod_form.ele_auth.disabled=true;
        ip_mod_form.user_name.disabled=true;
        ip_mod_form.login_pass.disabled=true;
        ip_mod_form.retype_login_pass.disabled=true;
        ip_mod_form.enable_pass.disabled=true;
        ip_mod_form.retype_enable_pass.disabled=true;
        ip_mod_form.device_user_group_id.disabled=true;
        ip_mod_form.device_user_group_id.selectedIndex='0';
        ip_mod_form.device_user_group_id.style.backgroundColor='#F0EDEA';
        ip_mod_form.user_name.value='';
        ip_mod_form.login_pass.value='';
        ip_mod_form.retype_login_pass.value='';
        ip_mod_form.enable_pass.value='';
        ip_mod_form.retype_enable_pass.value='';
    } else {
        ip_mod_form.ele_auth[0].disabled=false;
        ip_mod_form.ele_auth[1].disabled=false;
        ip_mod_form.user_name.disabled=false;
        ip_mod_form.login_pass.disabled=false;
        ip_mod_form.retype_login_pass.disabled=false;
        ip_mod_form.enable_pass.disabled=false;
        ip_mod_form.retype_enable_pass.disabled=false;
        ip_mod_form.device_user_group_id.disabled=false;
        ip_mod_form.device_user_group_id.style.backgroundColor='white';
    }
}
//-->
</script>

<script type="text/javascript">
<!--
function disable_cp(){
    if ( ip_mod_form.exclude_connection_proto.checked ) {
        ip_mod_form.connection_proto.disabled=true;
        ip_mod_form.connection_proto.selectedIndex='0';
        ip_mod_form.connection_proto.style.backgroundColor='#F0EDEA';
        ip_mod_form.connection_proto_port.disabled=true;
        ip_mod_form.connection_proto_port.value="";
        ip_mod_form.connection_proto_port.style.backgroundColor='#F0EDEA';
    } else {
        ip_mod_form.connection_proto.disabled=false;
        ip_mod_form.connection_proto.style.backgroundColor='white';
        ip_mod_form.connection_proto_port.disabled=false;
        ip_mod_form.connection_proto_port.style.backgroundColor='white';
    }
}
//-->
</script>

<script type="text/javascript">
<!--
function disable_server(){
    if ( ip_mod_form.exclude_cm_server_id.checked ) {
        ip_mod_form.cm_server_id.disabled=true;
        ip_mod_form.cm_server_id.selectedIndex='0';
        ip_mod_form.cm_server_id.style.backgroundColor='#F0EDEA';
    } else {
        ip_mod_form.cm_server_id.disabled=false;
        ip_mod_form.cm_server_id.style.backgroundColor='white';
    }
}
//-->
</script>

<script type="text/javascript">
<!--
function disable_scc(){
    if ( ip_mod_form.exclude_save_config_changes.checked ) {
        ip_mod_form.save_config_changes.disabled=true;
        ip_mod_form.save_config_changes.checked=false;
        ip_mod_form.save_config_changes.style.backgroundColor='#F0EDEA';
    } else {
        ip_mod_form.save_config_changes.disabled=false;
        ip_mod_form.save_config_changes.style.backgroundColor='white';
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


my %cc_value = ();
my @custom_columns = $gip->get_custom_host_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","host");

%cc_value=$gip->get_custom_host_columns_from_net_id_hash("$client_id","$host_id") if $host_id;

#        while ( my ($key, @value) = each(%custom_host_column_values) ) {
#                if ( $value[0]->[0] eq $cc_name ) {
#                        $cc_id=$key;
#                        $pc_id=$value[0]->[2];
#		}
#	}


#print "<form name=\"ip_mod_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modip_mass_update.cgi\">\n";
#print "<table border=\"0\" cellpadding=\"1\">\n";


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);
my $form_elements_cm = "";

my $standard_column_mod=0;
foreach my $mut(@mass_update_types) {
	if ( $mut eq $$lang_vars{hostname_message} ) {
#		print "<tr><td>$$lang_vars{hostname_message}</td><td></td><td><i><font size=\"2\"><input type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" name=\"hostname\" value=\"\" maxlength=\"75\"></font></i></td></tr>\n";
        $form_elements .= GipTemplate::create_form_element_text(
			label => "$$lang_vars{hostname_message}",
			id => "hostname",
			maxlength => 75,
		);

		$standard_column_mod=1;
	}

	if ( $mut eq $$lang_vars{description_message} ) {
#		print "<tr><td>$$lang_vars{description_message}</td><td></td><td><i><font size=\"2\"><input type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" name=\"host_descr\" value=\"\" maxlength=\"100\"></font></i></td></tr>\n";

		$form_elements .= GipTemplate::create_form_element_text(
			label => $$lang_vars{description_message},
			id => "host_descr",
			maxlength => 100,
		);

		$standard_column_mod=1;
	}

	if ( $mut eq $$lang_vars{loc_message} ) {

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
			id => "loc",
			width => "10em",
			required => "required",
		);


#		print "<tr><td>$$lang_vars{loc_message}</td><td></td><td><font size=\"2\"><select class='custom-select custom-select-sm' style='width: 6em' name=\"loc\" size=\"1\" value=\"\">";
#		print "<option></option>";
#		my $j=0;
#		foreach (@values_locations) {
#			print "<option>$values_locations[$j]->[0]</option>" if ( $values_locations[$j]->[0] ne "NULL" );
#			$j++;
#		}
#		print "</select></td></tr>\n";

		$standard_column_mod=1;
	}

	if ( $mut eq $$lang_vars{tipo_message} ) {

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
			id => "cat",
			width => "10em",
		);

#		print "<tr><td>$$lang_vars{tipo_message}</td><td></td><td><select class='custom-select custom-select-sm' style='width: 6em' name=\"cat\" size=\"1\">";
#		print "<option></option>";
#		my $j=0;
#		foreach (@values_categorias) {
#			print "<option>$values_categorias[$j]->[0]</option>" if ($values_categorias[$j]->[0] ne "NULL" );
#			$j++;
#		}
#		print "</select></td></tr>\n";

		$standard_column_mod=1;
	}

	if ( $mut eq "AI" ) {

		$form_elements .= GipTemplate::create_form_element_checkbox(
			label => "AI",
			id => "int_admin",
			value => "y",
			width => "10em",

		);

#		print "<tr><td>AI</td><td><input type=\"checkbox\" name=\"int_admin\" value=\"y\"></td></tr>\n";

		$standard_column_mod=1;
	}


	if ( $mut eq $$lang_vars{comentario_message} ) {
		$form_elements .= GipTemplate::create_form_element_textarea(
			label => $$lang_vars{comentario_message},
			rows => '5',
			cols => '30',
			id => "comentario",
			width => "10em",
			maxlength => 500,
		);

#		print "<tr><td>$$lang_vars{comentario_message}</td><td></td><td><textarea name=\"comentario\" cols=\"30\" rows=\"5\" wrap=\"physical\" maxlength=\"500\"></textarea></td></tr>";
		$standard_column_mod=1;
	}

	if ( $mut eq "UT" ) {


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
			id => "update_type",
			width => "6em",
		);


#		print "<tr><td>UT</td><td><select class='custom-select custom-select-sm' style='width: 6em' name=\"update_type\" size=\"1\">";
#		print "<option></option>";
#		my $j=0;
#		foreach (@values_utype) {
#			print "<option>$values_utype[$j]->[0]</option>" if ( $values_utype[$j]->[0] ne "NULL" );
#			$j++;
#		}
#		print "</select>\n";
#		print "</td></tr>";
#		$standard_column_mod=1;
	}

	if ( $mut eq $$lang_vars{update_mode_message} ) {

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
			id => "dyn_dns_updates",
			width => "14em",
			size => 1,
		);


#        my @dyn_dns_values = ( 1, 2, 3, 4 );
#		my %dyn_dns_value_name_hash = (
#			'1' => $$lang_vars{'no_update_message'},
#			'2' => $$lang_vars{'a_and_ptr_message'},
#			'3' => $$lang_vars{'a_update_only_message'},
#			'4' => $$lang_vars{'ptr_update_only_message'},
#		);
#
#		print "<tr><td>&nbsp;</td><td></td></tr>\n";
#		print "<tr><td>$$lang_vars{'update_mode_message'}</td><td></td><td><select class='custom-select custom-select-sm' style='width: 6em' name=\"dyn_dns_updates\" size=\"1\">";
#
#		foreach my $val ( @dyn_dns_values ) {
#			print "<option value=\"$val\">$dyn_dns_value_name_hash{$val}</option>\n";
#		}
#		print "</select></td></tr>\n";

		$standard_column_mod=1;
	}
}


#print "<tr><td><input name=\"entries_per_page_hosts\" type=\"hidden\" value=\"$entries_per_page_hosts\"><input name=\"start_entry_hosts\" type=\"hidden\" value=\"$start_entry_hosts\"><input name=\"knownhosts\" type=\"hidden\" value=\"$knownhosts\"><input name=\"anz_values_hosts\" type=\"hidden\" value=\"$anz_values_hosts\"></td></tr>\n";


my @vendors = $gip->get_vendor_array();
my @tag_column=$gip->get_custom_host_column_ids_from_name("$client_id","Tag");
my @tags = $gip->get_custom_host_column_ids_from_name("client_id", "Tag");
my $tag_cc_id=$tag_column[0][0] || "";
my $form_elements_tag = ""; 

my $n;
foreach my $mass_element(@mass_update_types) {
	$n=0;
	foreach my $cc_ele(@custom_columns) {
		my $cc_name = $custom_columns[$n]->[0];
		my $pc_id = $custom_columns[$n]->[3];
		my $cc_id = $custom_columns[$n]->[1];
        
        if ( $cc_name eq $mass_element && $cc_name eq "Line" ) {
            # ignore Lines
            $n++;
            next;
        }

		if ( $cc_name eq $mass_element ) {
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
						id => "${cc_name}_value",
						width => "10em",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_name,
						name => "cc_name",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_id,
						name => "${cc_name}_id",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						name => "${cc_name}_pcid",
						value => $pc_id,
					);

					$n++;
					next;


#					my $select_values = $custom_colums_select{$cc_id}->[2];
#					my $selected = "";
#
#					print "<tr><td>$cc_name</td><td></td><td><select class='custom-select custom-select-sm' style='width: 6em' name=\"${cc_name}_value\" size=\"1\">\n";
#					print "<option></option>";
#					foreach (@$select_values) {
#						my $opt = $_;
#						$opt = $gip->remove_whitespace_se("$opt");
#						print "<option value=\"$opt\">$opt</option>";
#					}
#					print "</select></td></tr>\n";
#					print "<input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";

					$n++;
					next;
				} elsif ( $cc_name eq "vendor" ) {
					my $knownvendor="0";
					my $checked_known="";
					my $checked_unknown="";
					my $disabled_known="";
					my $disabled_unknown="";
					my $cc_entry_unknown="";
					if ( $knownvendor == 1 ) {
						$checked_known="checked";
						$disabled_unknown="disabled";
					} else {
						$checked_unknown="checked";
						$disabled_known="disabled";
					}

					@item_order = ();
					my %option_style;


#					print "<tr><td>$cc_name</td><td> <input type=\"radio\" name=\"vendor_radio\" value=\"known\" onclick=\"${cc_name}_value_known.disabled=false;${cc_name}_value_unknown.value='';${cc_name}_value_unknown.disabled=true;\" $checked_known></td><td>\n";
#					print "<input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\">";
#					print "<font size=\"2\"><select class='custom-select custom-select-sm' style='width: 6em' name=\"${cc_name}_value\" id=\"${cc_name}_value_known\" size=\"1\" $disabled_known>";
#					print "<option></option>\n";
					my $j=0;
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
						} else {
							$vendor_img=$vendor;
						}
#						print "<option style=\"background: url('../imagenes/vendors/${vendor_img}.png') no-repeat top left;\" value=\"$vendor\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $vendor</option>";

						push @item_order, "$vendor";
						$option_style{"$vendor"} = "style=\"background: url(../imagenes/vendors/${vendor_img}.png) no-repeat top left;\"";

						$j++;
					}


					my $before_text_span_id = "vendor_radio_span_select";
					my $before_text = "<input type=\"radio\" name=\"vendor_radio\" value=\"known\" onclick=\"${cc_name}_value_known.disabled=false;${cc_name}_value_unknown.value='';${cc_name}_value_unknown.disabled=true;\" checked>";

					@item_order = ();
					push @item_order, "";
					foreach my $name(@vendors) {
						push @item_order, $name;
					}

					$form_elements .= GipTemplate::create_form_element_select(
						name => $cc_name,
						item_order => \@item_order,
						id => "${cc_name}_value_known",
						width => "10em",
						option_style => \%option_style,
						before_text => $before_text,
						before_text_span_id => $before_text_span_id,
					);




					$before_text_span_id = "vendor_radio_span_text";
					$before_text = "<input type=\"radio\" name=\"vendor_radio\" value=\"unknown\" onclick=\"${cc_name}_value_known.disabled=true;${cc_name}_value_unknown.disabled=false;document.ip_mod_form.${cc_name}_value_known.options[0].selected = true;\">";

					$form_elements .= GipTemplate::create_form_element_text(
						id => "${cc_name}_value_unknown",
						maxlength => 500,
						before_text => $before_text,
						before_text_span_id => $before_text_span_id,
						disabled => "disabled",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_name,
						name => "cc_name",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_id,
						name => "${cc_name}_id",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						name => "${cc_name}_pcid",
						value => $pc_id,
					);

# TEST name=\"${cc_name}_value\" id=\"${cc_name}_value_unknown\" 


#					print "</select><input name=\"custom_name\" type=\"hidden\" value=\"$cc_name\"></td></tr>\n";
#					print "<tr><td></td><td><input type=\"radio\" name=\"vendor_radio\" value=\"unknown\" onclick=\"${cc_name}_value_known.disabled=true;${cc_name}_value_unknown.disabled=false;document.ip_mod_form.${cc_name}_value_known.options[0].selected = true;\" $checked_unknown></td><td><input type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"20\" name=\"${cc_name}_value\" id=\"${cc_name}_value_unknown\" value=\"$cc_entry_unknown\" maxlength=\"500\" $disabled_unknown></td></tr>\n";

				} elsif ( $cc_name eq "URL" ) {


					$form_elements .= GipTemplate::create_form_element_textarea(
						label => "$cc_name (service::URL)",
						rows => '5',
						cols => '30',
						id => "${cc_name}_value",
						width => "10em",
						maxlength => 500,
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_name,
						name => "cc_name",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						value => $cc_id,
						name => "${cc_name}_id",
					);

					$form_elements .= GipTemplate::create_form_element_hidden(
						name => "${cc_name}_pcid",
						value => $pc_id,
					);





#					my @values_url=$gip->get_url_values("$client_id","$mass_update_host_ids","$red_num","$cc_id","$pc_id");
#					my $refurl=$values_url[0] || "";
#					my $same_urls=0;
#					my $url_value="";
#					foreach ( @values_url ) {
#						if ( $_ ne $refurl ) {
#							$same_urls=1;
#							last;
#						}
#					}
#					$url_value=$refurl if $same_urls == 0;
#					
#					print "<tr><td>$cc_name<br>(service::URL)</td><td colspan='2'><input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\"><textarea name='${cc_name}_value' cols='50' rows='5' wrap='physical' maxlength='500'>$url_value</textarea></td></tr>\n";


				} elsif ( $cc_name eq "Tag" ) {

                    $form_elements_tag = $gip->print_tag_form("$client_id","$vars_file","$host_id","host") if @tags;

#					my @values = $gip->get_tag("$client_id","$vars_file");
#					my $values = \@values;
#
#					print "<tr><td>$$lang_vars{'tags_message'}</td><td></td><td><select multiple name=\"tag\" size=\"5\">\n";
#					print "<option></option>";
#
#					my $m=0;
#					foreach my $ele(@values) {
#						my $id = $values[$m]->[0];
#						my $name = $values[$m]->[1];
#						print "<option value=\"$id\">$name</option>";
#						$m++;
#					}
#					print "</select></td></tr>\n";
#					print "<input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";
#
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
                            id => "${cc_name}_value",
							width => "10em",
						);
					}

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        value => $cc_name,
                        name => "cc_name",
                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        value => $cc_id,
                        name => "${cc_name}_id",
                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        name => "${cc_name}_pcid",
                        value => $pc_id,
                    );





#					my @snmp_groups = $gip->get_snmp_groups("$client_id");
#					$j=0;
#					if ( ! $snmp_groups[0] ) {
#						print "<tr><td>$cc_name</td><td><i>$$lang_vars{no_snmp_groups_message}</i>";
#					} else {
#						print "<tr><td>$cc_name</td><td></td>";
#						print "<td><select class='custom-select custom-select-sm' style='width: 6em' name=\"${cc_name}_value\" size=\"1\">";
#						print "<option></option>";
#						foreach ( @snmp_groups ) {
#							my $snmp_group_name = $snmp_groups[$j]->[1];
#							print "<option>$snmp_group_name</option>\n";
#							$j++;
#						}
#						print "</select>\n";
##						print "<input name=\"custom_${n}_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"custom_${n}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"custom_${n}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";
#						print "<input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";

#					}
#					print "</td></tr>\n";

				} elsif ( $cc_name eq "CM" ) {

			my ($host_hash_ref,$host_sort_helper_array_ref)=$gip->get_host_hash("$client_id","","","CM_MASS","","",\@mass_update_host_ids_arr,"","$ip_version");
			my $anz_ip_hash = scalar keys %$host_hash_ref;

			my @global_config = $gip->get_global_config("$client_id");

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
			my $device_count_enabled_new_hosts=$gip->get_cm_host_count_hosts("$client_id",$host_hash_ref);
			my $device_count_enabled=$gip->get_cm_host_count("$client_id");	
			
			my $device_count_disabled_new_hosts=$anz_hosts_update - $device_count_enabled_new_hosts;
			my $device_count_enabled_total=$device_count_enabled + $device_count_disabled_new_hosts;
			my $device_count_exceed_hosts=$device_count_enabled_total - $device_count;

			if ( $cm_enabled ne "yes" ) {
				$cm_note="<font color=\"red\"><b>" . $$lang_vars{cm_management_disabled_message} . "<br>" . $$lang_vars{enable_cm_managemente_help_message} . "</b></font>";
				$enable_cm_checkbox_disabled="disabled";
			} elsif ( $device_count < $device_count_enabled_total ) {
			# license host count exceeded
				$cm_note="<b><font color=\"red\">" . $$lang_vars{host_count_exceeded_message} . "</font><br>" . $$lang_vars{number_of_supported_cm_hosts_message} . ": " . $device_count . "<br>" . $$lang_vars{number_of_cm_hosts_message} . ": " . $device_count_enabled. "<br>" . $$lang_vars{number_of_new_cm_hosts_message} . ": " . $device_count_disabled_new_hosts . "<br>" . $$lang_vars{number_of_host_which_exceed_the_license} . ": " . $device_count_exceed_hosts ."<p>";
				$enable_cm_checkbox_disabled="disabled";

			} elsif ( $return_code != 0 && $return_code != 2 ) {
				# valid or exire warn
				$cm_note="<font color=\"red\"><b>" . $$lang_vars{cm_management_disabled_message} . "<br>" . $cm_licence_key_message . "<br" .  $$lang_vars{cm_management_disabled_message} . "</b></font>";
				$enable_cm_checkbox_disabled="disabled";
			}



			my %values_device_type_groups=$gip->get_device_type_values("$client_id","$cm_xml_dir");
			my %values_device_user_groups=$gip->get_device_user_groups_hash("$client_id");
			my %values_cm_server=$gip->get_cm_server_hash("$client_id");

			my ($cm_id,$device_type_group_id,$device_user_group_id,$user_name,$login_pass,$enable_pass,$description,$connection_proto,$connection_proto_port,$cm_server_id,$save_config_changes);
			$device_type_group_id=$device_user_group_id=$user_name=$login_pass=$enable_pass=$description=$connection_proto=$connection_proto_port=$cm_server_id=$save_config_changes="";

			my $device_type_group_id_preselected=1;


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
for(j=0;j<60;j++){
            OTHER_JOB_ID='device_other_job_' + j
            OTHER_JOB_GROUP_ID='other_job_group_' + j
            document.getElementById(OTHER_JOB_ID).options.length=values_job_names.length
            document.getElementById(OTHER_JOB_GROUP_ID).options[0].selected=true
}

//document.ip_mod_form.cm_job_group.options[0].selected=true

for(i=0;i<values_job_names.length;i++){
        for(j=0;j<60;j++){
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
			my $save_config_changes_checked="";
			$save_config_changes_checked="checked" if $save_config_changes;


			$form_elements_cm .= "<tr><td><br><b>$$lang_vars{device_jobs_message}</b></td><td>";
			$form_elements_cm .= "<tr><td colspan=\"2\">$cm_note</td><td>" if $cm_note;

			$form_elements_cm .= "<tr><td>$$lang_vars{enable_cm_host_message}</td><td><input name=\"enable_cm\" type=\"checkbox\" value=\"enable_cm\" $enable_cm_checked onchange=\"mod_cm_fields(\'60\');\" $enable_cm_checkbox_disabled checked></td></tr>";
			 $form_elements_cm .= "<tr><td> <span id=\"delete_cm_checkbox_span\" style=\"display:none;\">$$lang_vars{delete_cm_configuration_message}</span></td><td> <input name=\"delete_cm_all\" id=\"delete_cm_checkbox\" type=\"checkbox\" value=\"delete_cm_all\" onchange=\"change_delete_old_jobs_checkbox();\" style=\"display:none;\"></td></tr>\n";



			$form_elements_cm .= "<tr><td>$$lang_vars{device_type_group_message}</td><td>";
			if ( scalar keys %values_device_type_groups >= 1 ) {
				$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"device_type_group_id\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" onchange=\"changerows(this,\'60\');\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_device_type_groups{$a}[0] cmp $values_device_type_groups{$b}[0] } keys %values_device_type_groups ) {

					my $device_type_group_name=$values_device_type_groups{$key}[0];
					$form_elements_cm .= "<option value=\"$key\">$device_type_group_name</option>\n";
				}
				$form_elements_cm .= "</select></td></tr>\n";
			} else {
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_type_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_device_type_group_message}</i></font>\n";
			}



			my $device_user_group_disabled="";
			my $individual_user_disabled="";
			my $device_user_select_background="white";
			my $display_device_user_group="inline";
			my $display_individual_user="none";
			$individual_user_disabled="disabled";
			$form_elements_cm .= "<tr><td colspan=\"2\">$$lang_vars{use_device_user_group_message} <input name=\"ele_auth\" id=\"ele_auth\" type=\"radio\" value=\"group\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled checked> $$lang_vars{use_device_individual_user_message}\n";
			$form_elements_cm .= "<input name=\"ele_auth\" type=\"radio\" value=\"individual\" onclick=\"mod_user_info(this.value);\" $enable_cm_disabled>";
			$form_elements_cm .= " <input type=\"checkbox\" name=\"exclude_device_user_group\" value=\"1\" onclick=\"disable_djg();\"> <i>$$lang_vars{exclude_from_update_message}</i></td></tr>\n";


			$form_elements_cm .= "<tr><td>\n";
			$form_elements_cm .= "<span id=\"cm_device_user_group\" style=\"display:$display_device_user_group;\">$$lang_vars{device_user_group_message}</span></td><td><span id=\"cm_device_user_group1\" style=\"display:$display_device_user_group;\">";
			if ( scalar keys %values_device_user_groups >= "1" ) {

				$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"device_user_group_id\" id=\"device_user_group_id\" size=\"1\" style=\"background-color: $device_user_select_background;\" $device_user_group_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_device_user_groups{$a}[0] cmp $values_device_user_groups{$b}[0] } keys %values_device_user_groups ) {
					my $device_user_group_name=$values_device_user_groups{$key}[0];
					$form_elements_cm .= "<option value=\"$key\">$device_user_group_name</option>";
				}
				$form_elements_cm .= "</select>\n";
			} else {
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"device_user_group_id\" id=\"device_user_group_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_device_user_group_message}</i></font>\n";
			}


			$form_elements_cm .= "</span></td></tr>\n";


			$form_elements_cm .= "<tr><td colspan=\"2\">\n";
			$form_elements_cm .= "<span id=\"cm_individual_user\" style=\"display:$display_individual_user;\">\n";
			$form_elements_cm .= "<table border=\"0\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\">\n";


			$form_elements_cm .= "<tr><td>$$lang_vars{device_user_name_message}</td><td><input name=\"user_name\" id=\"user_name\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\" value=\"$user_name\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{login_pass_message}</td><td><input name=\"login_pass\" id=\"login_pass\" type=\"password\" size=\"12\" maxlength=\"500\" value=\"$login_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{retype_login_pass_message}</td><td><input name=\"retype_login_pass\" id=\"retype_login_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$login_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{enable_pass_message}</td><td><input name=\"enable_pass\" id=\"enable_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$enable_pass\" $individual_user_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "$$lang_vars{retype_enable_pass_message}</td><td><input name=\"retype_enable_pass\" id=\"retype_enable_pass\" type=\"password\" size=\"12\" maxlength=\"30\" value=\"$enable_pass\" $individual_user_disabled>\n";


			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "</table>\n";
			$form_elements_cm .= "</span>\n";


			$form_elements_cm .= "</td></tr>\n";

			my @cm_connetion_type_values=("telnet","SSH");
			$form_elements_cm .= "\n<tr><td>$$lang_vars{connection_proto_message}</td><td><select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"connection_proto\" size=\"1\" onchange=\"mod_connection_proto_port(this.value);\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>\n";
			$form_elements_cm .= "<option></option>\n";
			foreach (@cm_connetion_type_values) {
				$form_elements_cm .= "<option>$_</option>\n";
			}
			$form_elements_cm .= "</select>\n";
			$form_elements_cm .= "$$lang_vars{port_message} <input name=\"connection_proto_port\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"3\" maxlength=\"5\" value=\"$connection_proto_port\" $enable_cm_disabled>\n";
			$form_elements_cm .= "<input type=\"checkbox\" name=\"exclude_connection_proto\" value=\"1\" onclick=\"disable_cp();\"> <i>$$lang_vars{exclude_from_update_message}</i>\n";


			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{backup_server_message}</td><td>";
			if ( scalar keys %values_cm_server >= "1" ) {
				$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"cm_server_id\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $key ( sort { $values_cm_server{$a}[0] cmp $values_cm_server{$b}[0] } keys %values_cm_server ) {

					my $cm_server_name=$values_cm_server{$key}[0];
					$form_elements_cm .= "<option value=\"$key\">$cm_server_name</option>\n";
				}
				$form_elements_cm .= "</select>\n";
				$form_elements_cm .= "<input type=\"checkbox\" name=\"exclude_cm_server_id\" value=\"1\" onclick=\"disable_server();\"> <i>$$lang_vars{exclude_from_update_message}</i>\n";
			} else {
				$form_elements_cm .= "&nbsp;<font color=\"gray\"><input name=\"cm_server_id\" type=\"hidden\" value=\"\"><i>$$lang_vars{no_cm_server_message}</i></font>\n";
			}

			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{save_config_changes_message}</td><td><input type=\"checkbox\" name=\"save_config_changes\" value=\"1\" $save_config_changes_checked $enable_cm_disabled>\n";
			$form_elements_cm .= "<input type=\"checkbox\" name=\"exclude_save_config_changes\" value=\"1\" onclick=\"disable_scc();\"> <i>$$lang_vars{exclude_from_update_message}</i></td></tr>\n";


### JOBS
			$form_elements_cm .= "<tr><td>\n";
			$form_elements_cm .= "<br><b><i>$$lang_vars{other_jobs_message}</i></b>";
			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "<tr><td>$$lang_vars{delete_old_jobs_message}</td><td><input type=\"checkbox\" name=\"delete_old_jobs\" id=\"delete_old_jobs\" value=\"delete_old_jobs\"></td></tr>\n";
			$form_elements_cm .= "<tr><td>\n";



			$form_elements_cm .= "</td></tr><tr><td>\n";

			my %job_groups=$gip->get_job_groups("$client_id");
			my $k=0;
			$form_elements_cm .= "$$lang_vars{job_message}</td><td>";
			$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"device_other_job_0\" id=\"device_other_job_0\" size=\"1\" style=\"background-color:$enable_cm_bg_color; width: 230px;\" $enable_cm_disabled>";
			$form_elements_cm .= "<option></option>\n";
			$form_elements_cm .= "</select>\n";
			$form_elements_cm .= "<input name=\"device_other_jobs_anz\" type=\"hidden\" value=\"1\">\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{description_message}</td><td><input name=\"other_job_descr_0\" id=\"other_job_descr_0\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"30\" maxlength=\"500\" value=\"\" $enable_cm_disabled>\n";

			$form_elements_cm .= "</td></tr><tr><td>\n";


			$form_elements_cm .= "$$lang_vars{job_group_message}</td><td>";
			$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"other_job_group_0\" id=\"other_job_group_0\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
			$form_elements_cm .= "<option></option>\n";
			for my $job_group_all_id ( sort keys %job_groups ) {
				my $job_group_name=$job_groups{$job_group_all_id}[0];
				$form_elements_cm .= "<option value=\"$job_group_all_id\">$job_group_name</option>\n";
			}
			$form_elements_cm .= "</select>\n";
			$form_elements_cm .= "<input name=\"device_other_job_id_0\" type=\"hidden\" value=\"0\">";
			$form_elements_cm .= "</td></tr><tr><td>\n";
				$form_elements_cm .= "<span id=\"delete_button_${k}\" onClick=\"delete_job('$k')\" class=\"delete_small_button\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";


			$form_elements_cm .= "</td></tr><tr><td>\n";

			$form_elements_cm .= "<span id=\"plus_button_${k}\" onClick=\"show_host_ip_field('$k')\" class=\"add_small_button\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";


			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "<tr><td><br></td></tr>\n";

			$k++;
			for ( ; $k<=60; $k++ ) {

				$form_elements_cm .= "<tr><td colspan=\"2\">\n";
				$form_elements_cm .= "<span id=\"other_job_group_form_${k}\" style='display:none;'>\n";
				$form_elements_cm .= "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\" style=\"border-collapse:collapse\" width=\"100%\">\n";
				$form_elements_cm .= "<tr><td width=\"50%\">$$lang_vars{job_message}\n";
				$form_elements_cm .= "</td><td>\n";

				$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"device_other_job_${k}\" id=\"device_other_job_${k}\"size=\"1\" style=\"background-color:$enable_cm_bg_color; width: 230px;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				$form_elements_cm .= "</select>\n";

				$form_elements_cm .= "</td></tr><tr><td>\n";

				$form_elements_cm .= "$$lang_vars{description_message}</td><td><input name=\"other_job_descr_${k}\" id=\"other_job_descr_${k}\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"30\" maxlength=\"500\" value=\"\" $enable_cm_disabled>\n";

				$form_elements_cm .= "</td></tr><tr><td>\n";


				$form_elements_cm .= "$$lang_vars{job_group_message}\n";
				$form_elements_cm .= "</td><td>\n";
				$form_elements_cm .= "<select class='custom-select custom-select-sm m-2' style='width: 6em' name=\"other_job_group_${k}\" id=\"other_job_group_${k}\" size=\"1\" style=\"background-color:$enable_cm_bg_color;\" $enable_cm_disabled>";
				$form_elements_cm .= "<option></option>\n";
				for my $job_group_all_id ( sort keys %job_groups ) {
					my $job_group_name=$job_groups{$job_group_all_id}[0];
					$form_elements_cm .= "<option value=\"$job_group_all_id\">$job_group_name</option>\n";
				}
				$form_elements_cm .= "</select>\n";


				$form_elements_cm .= "</td></tr><tr><td>\n";


				$form_elements_cm .= "<span id=\"delete_button_${k}\" onClick=\"delete_job('$k')\" class=\"delete_small_button\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
				$form_elements_cm .= "</td></tr><tr><td>\n";

				$form_elements_cm .= "<span id=\"plus_button_${k}\" onClick=\"show_host_ip_field('$k')\" class=\"add_small_button\" style=\"cursor:pointer\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>\n";
				$form_elements_cm .= "</td></tr>\n";
				$form_elements_cm .= "<tr><td><br></td><td></td></tr>\n";
				$form_elements_cm .= "</table>\n";
				$form_elements_cm .= "</span></td></tr>\n";
			}



			$form_elements_cm .= "</table>\n";

			$form_elements_cm .= "</td></tr>\n";
			$form_elements_cm .= "<p>\n";

			$form_elements_cm .= "<input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\">\n";


# CM END

				} else {

					$form_elements .= GipTemplate::create_form_element_text(
						label => $cc_name,
						id => "${cc_name}_value",
						maxlength => 500,
					);

#                    $form_elements .= GipTemplate::create_form_element_hidden(
#                        value => $cc_name,
#                        name => "cc_name",
#                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        value => $cc_id,
                        name => "${cc_name}_id",
                    );

                    $form_elements .= GipTemplate::create_form_element_hidden(
                        name => "${cc_name}_pcid",
                        value => $pc_id,
                    );



#					print "<tr><td>$cc_name</td><td></td><td><input name=\"cc_name\" type=\"hidden\" value=\"$cc_name\"><input name=\"${cc_name}_id\" type=\"hidden\" value=\"$cc_id\"><input name=\"${cc_name}_pcid\" type=\"hidden\" value=\"$pc_id\"><input type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"20\" name=\"${cc_name}_value\" value=\"\" maxlength=\"500\"></td></tr>\n";
				}
			}
		}
	$n++;
	}
}



# Pass search data

#my $hidden_form_fields="";
#
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_hostname\" value=\"$daten{'hostname'}\">" if $daten{'hostname'};
## call from ip_modip_mass_update after advanced search 
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_hostname\" value=\"$daten{'advanced_search_hostname'}\">" if $daten{'advanced_search_hostname'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_host_descr\" value=\"$daten{'host_descr'}\">" if $daten{'host_descr'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_host_descr\" value=\"$daten{'advanced_search_host_descr'}\">" if $daten{'advanced_search_host_descr'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_comentario\" value=\"$daten{'comentario'}\">" if $daten{'comentario'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_comentario\" value=\"$daten{'advanced_search_comentario'}\">" if $daten{'advanced_search_comentario'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_ip\" value=\"$daten{'ip'}\">" if $daten{'ip'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_ip\" value=\"$daten{'advanced_search_ip'}\">" if $daten{'advanced_search_ip'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_loc\" value=\"$daten{'loc'}\">" if $daten{'loc'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_loc\" value=\"$daten{'advanced_search_loc'}\">" if $daten{'advanced_search_loc'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_cat\" value=\"$daten{'cat'}\">" if $daten{'cat'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_cat\" value=\"$daten{'advanced_search_cat'}\">" if $daten{'advanced_search_cat'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_int_admin\" value=\"$daten{'int_admin'}\">" if $daten{'int_admin'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_int_admin\" value=\"$daten{'advanced_search_int_admin'}\">" if $daten{'advanced_search_int_admin'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_hostname_exact\" value=\"$daten{'hostname_exact'}\">" if $daten{'hostname_exact'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_hostname_exact\" value=\"$daten{'advanced_search_hostname_exact'}\">" if $daten{'advanced_search_hostname_exact'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_client_independent\" value=\"$daten{'client_independent'}\">" if $daten{'client_independent'};
#$hidden_form_fields .= "<input type=\"hidden\" name=\"advanced_search_client_independent\" value=\"$daten{'advanced_search_client_independent'}\">" if $daten{'advanced_search_client_independent'};


if ( $daten{'hostname'} ) {
# call from ip_searchip (advanced)
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'hostname'},
		name => "advanced_search_hostname",
	);
} elsif ( $daten{'advanced_search_hostname'} ) {
# call from ip_modip_mass_update after advanced search 
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_hostname'},
		name => "advanced_search_hostname",
	);
}

if ( $daten{'host_descr'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'host_descr'},
		name => "advanced_search_host_descr",
	);
} elsif ( $daten{'advanced_search_host_descr'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_host_descr'},
		name => "advanced_search_host_descr",
	);
}

if ( $daten{'comentario'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'comentario'},
		name => "advanced_search_comentario",
	);
} elsif ( $daten{'advanced_search_comentario'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_comentario'},
		name => "advanced_search_comentario",
	);
}

if ( $daten{'ip'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'ip'},
		name => "advanced_search_ip",
	);
} elsif ( $daten{'advanced_search_ip'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_ip'},
		name => "advanced_search_ip",
	);
}

if ( $daten{'loc'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'loc'},
		name => "advanced_search_loc",
	);
} elsif ( $daten{'advanced_search_loc'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_loc'},
		name => "advanced_search_loc",
	);
}

if ( $daten{'cat'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'cat'},
		name => "advanced_search_cat",
	);
} elsif ( $daten{'advanced_search_cat'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_cat'},
		name => "advanced_search_cat",
	);
}

if ( $daten{'int_admin'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'.ip'},
		name => "advanced_search_int_admin",
	);
} elsif ( $daten{'advanced_search_int_admin'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_int_admin'},
		name => "advanced_search_int_admin",
	);
}

if ( $daten{'hostname_exact'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'hostname_exact'},
		name => "advanced_search_hostname_exact",
	);
} elsif ( $daten{'advanced_search_hostname_exact'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_hostname_exact'},
		name => "advanced_search_hostname_exact",
	);
}

if ( $daten{'client_independent'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'client_independent'},
		name => "advanced_search_client_independent",
	);
} elsif ( $daten{'advanced_search_client_independent'} ) {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $daten{'advanced_search_client_independent'},
		name => "advanced_search_client_independent",
	);
}

for ( my $k = 0; $k < scalar(@custom_columns); $k++ ) {
#	$hidden_form_fields .= "<input type=\"hidden\" name=\"cc_id_$custom_columns[$k]->[1]\" value=\"$daten{\"cc_id_$custom_columns[$k]->[1]\"}\">" if $daten{"cc_id_$custom_columns[$k]->[1]"};
	if ( $daten{"cc_id_$custom_columns[$k]->[1]"} ) {
		$form_elements .= GipTemplate::create_form_element_hidden(
			value => $daten{"cc_id_$custom_columns[$k]->[1]"},
			name => "cc_id_$custom_columns[$k]->[1]",
		);
	}
}

my $CM_show_hosts_hidden="";
my $CM_show_hosts_by_jobs_hidden="";
if ( $CM_show_hosts ) {
#	$CM_show_hosts_hidden="<input name=\"CM_show_hosts\" type=\"hidden\" value=\"$CM_show_hosts\">";
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $CM_show_hosts,
		name => "CM_show_hosts",
	);
} elsif ( $CM_show_hosts_by_jobs ) {
#	$CM_show_hosts_by_jobs_hidden="<input name=\"CM_show_hosts_by_jobs\" type=\"hidden\" value=\"$CM_show_hosts_by_jobs\">";
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => $CM_show_hosts_by_jobs,
		name => "CM_show_hosts_by_jobs",
	);
}

if ( defined($daten{'text_field_number_given'}) ) {
#    $text_field_number_given_form="<input name=\"text_field_number_given\" type=\"hidden\" value=\"text_field_number_given\">";
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => "text_field_number_given",
		name => "text_field_number_given",
	);
}

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $entries_per_page_hosts,
	name => "entries_per_page_hosts",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $start_entry_hosts,
	name => "start_entry_hosts",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $knownhosts,
	name => "knownhosts",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $anz_values_hosts,
	name => "anz_values_hosts",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $anz_values_hosts,
	name => "anz_values_hosts",
);

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
	value => $anz_hosts,
	name => "anz_hosts",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $mass_update_type,
	name => "mass_update_type",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $mass_update_host_ids,
	name => "mass_update_host_ids",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $red,
	name => "red",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $BM,
	name => "BM",
);

$form_elements .= GipTemplate::create_form_element_hidden(
	value => $red_num,
	name => "red_num",
);




#print "<tr><td><br><p><input type=\"hidden\" name=\"host_id\" value=\"$host_id\"><input name=\"host_order_by\" type=\"hidden\" value=\"$host_order_by\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"hidden\" name=\"ip_version\" value=\"$ip_version\"><input type=\"hidden\" name=\"search_index\" value=\"$search_index\"><input type=\"hidden\" name=\"search_hostname\" value=\"$search_hostname\"><input type=\"hidden\" name=\"anz_hosts\" value=\"$anz_hosts\"><input type=\"hidden\" name=\"mass_update_type\" value=\"$mass_update_type\"><input type=\"hidden\" name=\"mass_update_host_ids\" value=\"$mass_update_host_ids\"><input type=\"hidden\" name=\"red\" value=\"$red\"><input type=\"hidden\" name=\"BM\" value=\"$BM\"><input type=\"hidden\" name=\"red_num\" value=\"$red_num\">$text_field_number_given_form $hidden_form_fields $CM_show_hosts_hidden $CM_show_hosts_by_jobs_hidden<input type=\"submit\" value=\"$$lang_vars{cambiar_message}\" name=\"B1\" class=\"input_link_w_net\"></td><td></td></tr>\n";

#print "</form>\n";
#print "</table>\n";


#$gip->print_tag_form("$client_id","$vars_file","$host_id","host") if @tags;


$form_elements .= $form_elements_tag;
$form_elements .= $form_elements_cm;


$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B1",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "ip_mod_form",
    link => "./ip_modip_mass_update.cgi",
    method => "POST",
);

print $form;




#print "<script type=\"text/javascript\">\n";
#print "document.ip_mod_form.hostname.focus();\n";
#print "</script>\n";

$gip->print_end("$client_id","$vars_file","", "$daten");

