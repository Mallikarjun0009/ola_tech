#!/usr/bin/perl -w -T

# Copyright (C) 2019 Marc Uebel

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
	my $required_perms="manage_dns_server_group_perm";
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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{add_ldap_server_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_ldap_server_message}","$vars_file");


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    width => "350",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_message},
    id => "ldap_server",
    width => "350",
    hint_text => $$lang_vars{dns_or_ip_explic_message},
    required => "required",
);

$onclick = "onchange='changeAction();'";
$form_elements .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{enabled_message},
    id => "enabled",
    value => "1",
	onclick => $onclick,
    checked => "1",
);

@item_order = ();
my @values_type = ("", "MS Active Directory", "LDAP");
foreach my $opt(@values_type) {
    my $name = $opt || "";
    push @item_order, $name;
}

$onclick = "onchange='changeUserAttribute(this.value);'";
$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{tipo_message},
    item_order => \@item_order,
    id => "type",
    width => "10em",
	onclick => $onclick,
    required => "required",
);


@item_order = ();
my @values_protocol = ("LDAP", "LDAPS");
foreach my $opt(@values_protocol) {
    my $name = $opt || "";
    push @item_order, $name;
}

$onclick = "onchange='changePort(this.value);'";
$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{protocol_message},
    item_order => \@item_order,
    id => "protocol",
    width => "10em",
	onclick => $onclick,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{port_message},
    id => "port",
    size => "5",
    value => "389",
    type => "number",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{bind_identity_message},
    id => "bind_dn",
    width => "350",
    maxlength => "250",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{bind_password_message},
    id => "password",
    type => "password",
    width => "350",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{base_dn_message},
    id => "base_dn",
    size => "25",
    width => "350",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{username_attribute_message},
    id => "user_attribute",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{ldap_filter_message},
    width => "350",
    id => "filter",
);

#$form_elements .= GipTemplate::create_form_element_text(
#    label => $$lang_vars{timeout_message},
#    id => "timeout",
#    size => "5",
#    value => "30",
#    type => "number",
#);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "insert",
    name => "referer",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{check_ldap_settings_message},
    name => "B2",
);

#$form_elements .= GipTemplate::create_form_element_button(
#    value => $$lang_vars{add_message},
#    name => "B2",
#    disabled => "1",
#);


## FORM

my $form_action = "./ip_check_ldap_server.cgi";
$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_ldap_server_form",
    link => "$form_action",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.forms.insert_ldap_server_form.name.focus();\n";
print "</script>\n";

print <<EOF;
<script type="text/javascript">
<!--
function changePort(TYPE){
    if ( TYPE == "LDAP" ) {
        document.getElementById('port').value = "389";
    } else if ( TYPE == "LDAPS" ){
        document.getElementById('port').value = "636";
	}
}  

function changeUserAttribute(TYPE){
    if ( TYPE == "MS Active Directory" ) {
        document.getElementById('user_attribute').value = "sAMAccountName";
        document.getElementById('filter').value = "objectClass=*";
	} else {
        document.getElementById('user_attribute').value = "uid";
        document.getElementById('filter').value = "";
    }   
}  

function changeAction()
{
    if (document.getElementById('enabled').checked) {
        document.insert_ldap_server_form.action = "./ip_check_ldap_server.cgi";
        document.getElementById("B2").innerText= "$$lang_vars{check_ldap_settings_message}";
    } else {
        document.insert_ldap_server_form.action = "./ip_insert_ldap_server.cgi";
        document.getElementById("B2").innerText= "$$lang_vars{add_message}";
    }
}

-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
