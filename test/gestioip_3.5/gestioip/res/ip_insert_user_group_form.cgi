#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel



use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();
my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_user_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{new_user_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{new_user_group_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $clients_perm=9999;
my $locs_ro_perm=9999;
my $locs_rw_perm=9999;

print <<'EOF';

<script type="text/javascript">
<!--
function mod_vals_clients(VALUE, newOptions){
   var num_values
   if( document.getElementById("client_perm_all").checked == true ){
    document.getElementById("client_perm_all").disabled=false;
    document.getElementById("client_perm").disabled=true;
    document.getElementById("client_perm").style.color="#F0EDEA";
    document.getElementById("client_perm").style.backgroundColor="#F0EDEA";
    num_values=document.getElementById("client_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("client_perm").options[i].selected=false;
         document.getElementById("client_perm").options[i].style.color="#F0EDEA";
    }

    // get selected clients
    var selected=[];
    $('#client_perm option:selected').each(function(){
   	if ( $(this).val() && $(this).text() ) {
         selected[$(this).text()]=$(this).val();
   	}
    });
 
    var $el = $("#locs_ro_perm");
    $el.empty(); // remove old options
    $.each(newOptions, function(key,value) {
    var client_name = key.match(/ \((.*)\)$/);
   	console.log( "MATCH I ro: " + client_name[1] );
       $el.append($("<option></option>")
         .attr("value", value).text(key));
    });
 
    var $el = $("#locs_rw_perm");
    $el.empty(); // remove old options
    $.each(newOptions, function(key,value) {
    var client_name = key.match(/ \((.*)\)$/);
   	console.log( "MATCH I rw: " + client_name[1] );
       $el.append($("<option></option>")
         .attr("value", value).text(key));
    });

   } else {
    document.getElementById("client_perm_all").checked=false;
    document.getElementById("client_perm").disabled=false;
    document.getElementById("client_perm").style.backgroundColor="white";
    document.getElementById("client_perm").style.color="black";
    num_values=document.getElementById("client_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("client_perm").options[i].style.color="black";
    }

    var $el = $("#locs_ro_perm");
    $el.empty(); // remove old options

    $el = $("#locs_rw_perm");
    $el.empty(); // remove old options
   }
}
//-->
</script>

<script>

function getSelectValues(select) {
  var result = [];
  var options = select && select.options;
  var opt;

  for (var i=0, iLen=options.length; i<iLen; i++) {
    opt = options[i];

    if (opt.selected) {
      result.push(opt.value || opt.text);
    }
  }
  return result;
}

function mod_vals_clients_select(newOptions){
   document.getElementById("locs_ro_perm_all").disabled=false;

   // get selected clients
   var selected=[];
   $('#client_perm option:selected').each(function(){
  	if ( $(this).val() && $(this).text() ) {
        selected[$(this).text()]=$(this).val();
  	}
   });

   var $el = $("#locs_ro_perm");
   $el.empty(); // remove old options
   $.each(newOptions, function(key,value) {
   var client_name = key.match(/ \((.*)\)$/);
   if ( selected[client_name[1]] ) {
  	console.log( "MATCH ro: " + client_name[1] );
      $el.append($("<option></option>")
        .attr("value", value).text(key));
	}
   });

   var $el = $("#locs_rw_perm");
   $el.empty(); // remove old options
   $.each(newOptions, function(key,value) {
   var client_name = key.match(/ \((.*)\)$/);
   if ( selected[client_name[1]] ) {
  	console.log( "MATCH rw: " + client_name[1] );
      $el.append($("<option></option>")
        .attr("value", value).text(key));
	}
   });
}
//-->
</script>

<script type="text/javascript">
<!--
function mod_vals_locs_ro(VALUE){
   var num_values
   if( document.getElementById("locs_ro_perm_all").checked == true ){
    document.getElementById("locs_ro_perm_all").disabled=false;
    document.getElementById("locs_ro_perm").disabled=true;
    document.getElementById("locs_ro_perm").style.color="#F0EDEA";
    document.getElementById("locs_ro_perm").style.backgroundColor="#F0EDEA";
    num_values=document.getElementById("locs_ro_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("locs_ro_perm").options[i].selected=false;
         document.getElementById("locs_ro_perm").options[i].style.color="#F0EDEA";
    }
   } else {
    document.getElementById("locs_ro_perm").checked=false;
    document.getElementById("locs_ro_perm").disabled=false;
    document.getElementById("locs_ro_perm").style.backgroundColor="white";
    document.getElementById("locs_ro_perm").style.color="black";
    num_values=document.getElementById("locs_ro_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("locs_ro_perm").options[i].style.color="black";
    }
   }
}

function mod_vals_locs_rw(VALUE){
   if( document.getElementById("locs_rw_perm_all").checked == true ){
    document.getElementById("locs_rw_perm_all").disabled=false;
    document.getElementById("locs_rw_perm").disabled=true;
    document.getElementById("locs_rw_perm").style.color="#F0EDEA";
    document.getElementById("locs_rw_perm").style.backgroundColor="#F0EDEA";
    num_values=document.getElementById("locs_rw_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("locs_rw_perm").options[i].selected=false;
         document.getElementById("locs_rw_perm").options[i].style.color="#F0EDEA";
    }
   } else {
    document.getElementById("locs_rw_perm").checked=false;
    document.getElementById("locs_rw_perm").disabled=false;
    document.getElementById("locs_rw_perm").style.backgroundColor="white";
    document.getElementById("locs_rw_perm").style.color="black";
    num_values=document.getElementById("locs_rw_perm").options.length
    for(i=0;i<num_values;i++){
         document.getElementById("locs_rw_perm").options[i].style.color="black";
    }
   }
}
//-->
</script>

EOF

my @clients = $gip->get_clients();
my %client_hash = $gip->get_client_hash_all("$client_id");
my @values_categorias=$gip->get_cat_net("$client_id");


print "<p>\n";
print "<form name=\"insert_user_group_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_user_group.cgi\"><br>\n";

print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" type=\"text\" class='form-control form-control-sm m-2' size=\"15\" maxlength=\"50\"></td></tr>\n";

print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" type=\"text\" class='form-control form-control-sm m-2' size=\"15\" maxlength=\"200\"></td></tr>\n";
print "</table>\n";

print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><b>$$lang_vars{global_permissions_message}</b></td><td></td></tr>\n";
print "<tr><td><br></td><td></td></tr>\n";

print "<tr><td>$$lang_vars{manage_gestioip_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_gestioip_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_user_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_user_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_sites_and_cats_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_sites_and_cats_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_custom_columns_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_custom_columns_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_scheduled_jobs_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_scheduled_jobs_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_audit_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_audit_perm\"></td></tr>\n";

my @values_locations=$gip->get_loc_all_clients("$client_id");

my $new_options = "{";
my $j=0;
foreach (@values_locations) {
    my $loc_id=$values_locations[$j]->[0];
    my $loc=$values_locations[$j]->[1];
    my $loc_client_id=$values_locations[$j]->[2];
    if ( $loc eq "NULL" || $loc_id == -1 ) {
        $j++;
        next;
    }
    $new_options .= "'$loc ($client_hash{$loc_client_id}->[0])': '$loc_id',";
    $j++;
}
$new_options =~ s/,$//;
$new_options .= '}';

if ( scalar(@clients) > 0 ) {
	print "<tr><td><br></td><td></td></tr>\n";
    my $size=1;
    $size=2 if scalar(@clients) == 2;
    $size=3 if scalar(@clients) >= 3;

    my ($all_clients_checked,$all_clients_disabled,$some_clients_disabled);
    $all_clients_checked="";
    $some_clients_disabled="";
    my $bg_color="";
    my $color="black";

    $clients_perm=~s/_/\|/g;
    if ( $clients_perm =~ /^9999$/ ) {
        $all_clients_checked="checked";
        $some_clients_disabled="disabled";
        $bg_color="#F0EDEA";
        $color="#F0EDEA";
    }
    print "<tr><td>$$lang_vars{clients_message}</td>";
    print "<td><input type=\"checkbox\" value=\"9999\" name=\"clients_perm\" id=\"client_perm_all\" onchange=\"mod_vals_clients(this.value, $new_options);\" $all_clients_checked> $$lang_vars{all_clients_message}<br>\n";

    print "<select name=\"clients_perm\" id=\"client_perm\" class='custom-select custom-select-sm m-2' size=\"$size\" style=\"width: 12em; background-color:$bg_color; color:$color;\"  multiple $some_clients_disabled  onchange=\"mod_vals_clients_select($new_options);\">";
    my $j=0;
    foreach (@clients) {
		print "<option value=\"$clients[$j]->[0]\">$clients[$j]->[1]</option>";
        $j++;
    }
    print "</select>\n";
    print "</td></tr>";

}


my ($all_locs_checked_ro,$all_locs_disabled_ro,$some_locs_disabled_ro);

$all_locs_checked_ro="";
$some_locs_disabled_ro="";
my $bg_color_ro="";
my $color_ro="black";

$locs_ro_perm=~s/_/\|/g;
if ( $locs_ro_perm =~ /^9999$/ ) {
    $all_locs_checked_ro="checked";
    $some_locs_disabled_ro="disabled";
    $bg_color_ro="#F0EDEA";
    $color_ro="#F0EDEA";
}
print "<tr><td></td>";
print "<td><input type=\"checkbox\" value=\"9999\" name=\"locs_ro_perm_all\" id=\"locs_ro_perm_all\" onchange=\"mod_vals_locs_ro(this.value);\" $all_locs_checked_ro> $$lang_vars{all_locs_message}\n";

print "<tr><td>$$lang_vars{locs_ro_message}</td><td><select name=\"locs_ro_perm\" id='locs_ro_perm'  size=\"3\" class='custom-select custom-select-sm m-2' size=\"5\" style=\"width: 12em; background-color:$bg_color_ro; color:$color_ro;\"  multiple $some_locs_disabled_ro>";
$j=0;
print "<option></option>";

foreach (@values_locations) {

    my $loc_id=$values_locations[$j]->[0];
    my $loc=$values_locations[$j]->[1];
    my $loc_client_id=$values_locations[$j]->[2];

    my $selected = "";
    if ( $locs_ro_perm =~ /^$loc_id$/ || $locs_ro_perm =~ /^$loc_id\|/ || $locs_ro_perm =~ /\|$loc_id$/ || $locs_ro_perm =~ /\|$loc_id\|/ ) {
        $selected = "selected";
    }

    if ( $clients_perm !~ /^9999$/ ) {
        if ( $clients_perm !~ /\b${loc_client_id}\b/ ) {
            $j++;
            next;
        }
    }
    if ( $loc eq "NULL" || $loc_id == -1 ) {
        $j++;
        next;
    }

    print "<option value='$loc_id' $selected>$loc ($client_hash{$loc_client_id}->[0])</option>";

    $j++;
}
print "</select>\n";
print "</td></tr>";

my ($all_locs_checked_rw,$all_locs_disabled_rw,$some_locs_disabled_rw);

$all_locs_checked_rw="";
$some_locs_disabled_rw="";
my $bg_color_rw="";
my $color_rw="black";

$locs_rw_perm=~s/_/\|/g;
if ( $locs_rw_perm =~ /^9999$/ ) {
    $all_locs_checked_rw="checked";
    $some_locs_disabled_rw="disabled";
    $bg_color_rw="#F0EDEA";
    $color_rw="#F0EDEA";
}
print "<tr><td></td>";
print "<td><input type=\"checkbox\" value=\"9999\" name=\"locs_rw_perm_all\" id=\"locs_rw_perm_all\" onchange=\"mod_vals_locs_rw(this.value);\" $all_locs_checked_rw> $$lang_vars{all_locs_message}\n";

print "<tr><td>$$lang_vars{locs_rw_message}</td><td><select name=\"locs_rw_perm\" id='locs_rw_perm'  size=\"3\" class='custom-select custom-select-sm m-2' size=\"5\" style=\"width: 12em; background-color:$bg_color_rw; color:$color_rw;\"  multiple $some_locs_disabled_rw>";
$j=0;
print "<option></option>";

foreach (@values_locations) {

    my $loc_id=$values_locations[$j]->[0];
    my $loc=$values_locations[$j]->[1];
    my $loc_client_id=$values_locations[$j]->[2];
    my $selected = "";

    if ( $locs_rw_perm =~ /^$loc_id$/ || $locs_rw_perm =~ /^$loc_id\|/ || $locs_rw_perm =~ /\|$loc_id$/ || $locs_rw_perm =~ /\|$loc_id\|/ ) {
        $selected = "selected";
    }

    if ( $clients_perm !~ /^9999$/ ) {
        if ( $clients_perm !~ /\b${loc_client_id}\b/ ) {
            $j++;
            next;
        }
    }
    if ( $loc eq "NULL" || $loc_id == -1 ) {
        $j++;
        next;
    }

    print "<option value='$loc_id' $selected>$loc ($client_hash{$loc_client_id}->[0])</option>";

    $j++;
}
print "</select>\n";
print "</td></tr>";

print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><b>$$lang_vars{client_permissions_message}</b></td><td></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";

print "<tr><td>$$lang_vars{manage_tags_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_tags_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_snmp_group_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_snmp_group_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_dns_server_group_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_dns_server_group_perm\"></td></tr>\n";
#print "<tr><td>$$lang_vars{manage_smtp_server_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_smtp_server_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_manage_dyn_dns_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_dyn_dns_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{manage_macs_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"manage_macs_perm\"></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";

print "<tr><td><i><b>$$lang_vars{networks_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{create_net_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"create_net_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_net_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_net_perm\" checked></td></tr>\n";
print "<tr><td>$$lang_vars{update_net_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"update_net_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{delete_net_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"delete_net_perm\"></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><i><b>$$lang_vars{hosts1_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{create_host_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"create_host_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_host_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_host_perm\" checked></td></tr>\n";
print "<tr><td>$$lang_vars{update_host_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"update_host_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{delete_host_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"delete_host_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{execute_update_dns_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"execute_update_dns_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{execute_update_snmp_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"execute_update_snmp_perm\"></td></tr>\n";
#print "<tr><td>$$lang_vars{execute_update_ping_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"execute_update_ping_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{password_management_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"password_management_perm\"></td></tr>\n";


print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><i><b>$$lang_vars{vlans_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{create_vlan_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"create_vlan_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_vlan_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_vlan_perm\" checked></td></tr>\n";
print "<tr><td>$$lang_vars{update_vlan_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"update_vlan_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{delete_vlan_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"delete_vlan_perm\"></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><i><b>$$lang_vars{cm_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{read_device_config_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_device_config_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{write_device_config_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"write_device_config_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{administrate_cm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"administrate_cm_perm\"></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><i><b>$$lang_vars{autonomous_systems_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{create_as_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"create_as_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_as_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_as_perm\" checked></td></tr>\n";
print "<tr><td>$$lang_vars{update_as_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"update_as_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{delete_as_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"delete_as_perm\"></td></tr>\n";

print "<tr><td><br></td><td></td></tr>\n";
print "<tr><td><i><b>$$lang_vars{leased_lines_message}</b></i></td><td></td></tr>\n";
print "<tr><td>$$lang_vars{create_line_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"create_line_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{read_line_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"read_line_perm\" checked></td></tr>\n";
print "<tr><td>$$lang_vars{update_line_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"update_line_perm\"></td></tr>\n";
print "<tr><td>$$lang_vars{delete_line_perm_message}</td><td> <input type=\"checkbox\" value=\"1\" name=\"delete_line_perm\"></td></tr>\n";


print "</table>\n";

print "<p><br>\n";

print "<script type=\"text/javascript\">\n";
print "document.insert_user_group_form.name.focus();\n";
print "</script>\n";

print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"submit\" class='btn' value=\"$$lang_vars{add_message}\" name=\"B2\" class=\"input_link_w_net\"></form></span><br><p>\n";

$gip->print_end("$client_id", "", "", "");
