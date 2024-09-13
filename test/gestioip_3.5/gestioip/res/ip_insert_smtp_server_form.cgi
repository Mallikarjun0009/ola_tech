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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{add_smtp_server_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_smtp_server_message}","$vars_file");


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_name_message},
    id => "server_name",
    hint_text => $$lang_vars{server_name_explic_message},
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{user_name_message},
    id => "user_name",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{password_message},
    id => "password",
    type => "password",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{default_from_address_message},
    id => "default_from",
    type => "email",
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
	onclick => $onclick,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{port_message},
    id => "port",
    size => "5",
    value => "25",
    type => "number",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{timeout_message},
    id => "timeout",
    size => "5",
    value => "30",
    type => "number",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{add_message},
    name => "B2",
);

$onclick = "onclick='openMailTestForm();'";
$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{send_test_mail_message},
    name => "B2",
    onclick => $onclick,
);

## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_smtp_server_form",
    link => "./ip_insert_smtp_server.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.forms.insert_smtp_server_form.server_name.focus();\n";
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

function openMailTestForm() {
    console.log("open mail test form");
	var f = document.insert_smtp_server_form;
    var w = window.open('', 'form-target', 'width=400, height=300');
    f.action ="$server_proto://$base_uri/send_test_mail.cgi";
    f.target = 'form-target';
    f.submit();
};
-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
