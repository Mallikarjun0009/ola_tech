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
	my $required_perms="manage_gestioip_perm";
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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_smtp_server_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_smtp_server_message}","$vars_file");

my $id = $daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $id !~ /^\d+/;


my @values=$gip->get_smtp_server_from_id("$client_id","$id");
my $name = $values[0][0];
my $username = $values[0][1];
my $password = $values[0][2] || "";
my $default_from = $values[0][3] || "";
my $security = $values[0][4] || "";
my $port = $values[0][5] || "";
my $timeout = $values[0][6] || "";
my $comment = $values[0][7] || "";



my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_name_message},
    id => "server_name",
    hint_text => $$lang_vars{server_name_explic_message},
	value => $name,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{user_name_message},
    id => "user_name",
	value => $username,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{password_message},
    id => "password",
    type => "password",
	value => $password,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{default_from_address_message},
    id => "default_from",
    type => "email",
	value => $default_from,
);


@item_order = ();
my @values_security = ("", "SSL", "STARTTLS");
foreach my $opt(@values_security) {
    my $name = $opt || "";
    push @item_order, $name;
}

$onclick = "onchange='changePort(this.value);'";
$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{security_message},
    item_order => \@item_order,
    id => "security",
    width => "10em",
	selected_value => "$security",
    onclick => $onclick,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{port_message},
    id => "port",
    size => "5",
    value => "25",
    type => "number",
	value => $port,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{timeout_message},
    id => "timeout",
    size => "5",
    value => "30",
    type => "number",
	value => $timeout,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
	value => $comment,
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $id,
    name => "id",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);


## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_smtp_server_form",
    link => "./ip_mod_smtp_server.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.forms.mod_smtp_server_form.server_name.focus();\n";
print "</script>\n";

print <<EOF;
<script type="text/javascript">
<!--
function changePort(TYPE){
    if ( TYPE == "STARTTLS" ) {
        document.getElementById('port').value = "587";
    } else if ( TYPE == "SSL" ){
        document.getElementById('port').value = "465";
    } else {
        document.getElementById('port').value = "25";
    }
}  
-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
