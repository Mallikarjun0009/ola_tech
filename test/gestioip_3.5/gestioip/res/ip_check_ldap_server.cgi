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


my $id = $daten{'id'} || "";
my $name = $daten{'name'} || "";
my $ldap_server = $daten{'ldap_server'} || "";
my $type = $daten{'type'} || "";
my $protocol = $daten{'protocol'} || "";
my $port = $daten{'port'} || "";
my $bind_dn = $daten{'bind_dn'} || "";
my $password = $daten{'password'} || "";
my $base_dn = $daten{'base_dn'} || "";
my $user_attribute = $daten{'user_attribute'} || "";
my $filter = $daten{'filter'} || "";
my $comment = $daten{'comment'} || "";
my $referer = $daten{'referer'} || "insert";
my $enabled = $daten{'enabled'} || 0;

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;

my @objects = $gip->get_ldap_server("$client_id");
foreach my $obj( @objects ) {
    if ( $id ) {
		if ( $name eq $obj->[1] && $id ne $obj->[0] ) {
			$gip->print_error("$client_id","<b>$name</b>: $$lang_vars{name_exists_message}");
		}
	} else {
		if ( $name eq $obj->[1] ) {
			$gip->print_error("$client_id","<b>$name</b>: $$lang_vars{name_exists_message}");
		}
	}
}

$gip->print_error("$client_id","$$lang_vars{insert_ldap_server_message}") if ! $ldap_server;
$gip->print_error("$client_id","$$lang_vars{select_type_message}") if ! $type;
$gip->print_error("$client_id","$$lang_vars{select_protocol_message}") if ! $protocol;
$gip->print_error("$client_id","$$lang_vars{select_port_message}") if ! $port;
$gip->print_error("$client_id","$$lang_vars{insert_bind_dn_message}") if ! $bind_dn;
$gip->print_error("$client_id","$$lang_vars{insert_base_dn_message}") if ! $base_dn;
$gip->print_error("$client_id","$$lang_vars{insert_user_attrib_message}") if ! $user_attribute;
$gip->print_error("$client_id","$$lang_vars{select_port_message}") if ! $port;

$gip->print_error("$client_id","$$lang_vars{bind_dn_no_whitespace_message}") if $bind_dn =~/\s/;

my $search = $user_attribute . "=*";
my @attrs = ("$user_attribute");
#$attrs[0] = $user_attribute;

my $ldap = $gip->create_ldap_connection(
	client_id => "$client_id",
    ldap_server => "$ldap_server",
    protocol => "$protocol",
    ldap_port => "$port",
    bind_dn => "$bind_dn",
    password => "$password",
    base_dn => "$base_dn",
#    user_attribute => "$user_attribute",
    filter => "$filter",
    search => "$search",
    attrs => \@attrs,
) || "";

my $connect_error = "";
if ( exists $ldap->{ldap_error} ) {
    $connect_error = $ldap->{ldap_error};
}

my $readonly = "";
my $disabled = "";
if ( ! $connect_error ) {
	print "<br><p><h5 class='text-success'>$$lang_vars{ldap_check_successful_message}</h5><br>";
    $readonly = 1;
    $disabled = 1;
} else {
	if ( $connect_error =~ /Connect error/ ) {
		print "<br><h6 class='text-danger'>$$lang_vars{ldap_connect_error_message}</h6><p class='font-weight-bold'>$$lang_vars{error_message_message}: $connect_error</p><br>";
	} elsif ( $connect_error =~ /Bind error/ ) {
		print "<br><h6 class='text-danger'>$$lang_vars{ldap_bind_error_message}</h6><p class='font-weight-bold'>$$lang_vars{error_message_message}: $connect_error</p><br>";
	} elsif ( $connect_error =~ /Search error/ ) {
		print "<br><p class='text-danger'>$$lang_vars{ldap_search_error_message}</p>$$lang_vars{error_message_message}: $connect_error<br>";
	} else {
		print "<br><h5 class='text-danger'>$$lang_vars{ldap_error_message}</h5><p class='font-weight-bold'>$$lang_vars{error_message_message}: $connect_error</p><br>";
	}
}

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    width => "350",
    required => "required",
    value => "$name",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_message},
    id => "ldap_server",
    width => "350",
    hint_text => $$lang_vars{dns_or_ip_explic_message},
    required => "required",
    value => "$ldap_server",
    readonly => "$readonly",
);

my $checked = "";
$checked = 1 if $enabled;
$onclick = 'onclick="return false;"';
$form_elements .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{enabled_message},
    id => "enabled",
    value => "1",
    checked => "$checked",
    onclick => "$onclick",
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
    selected_value => "$type",
    disabled => "$disabled",
);

if ( $disabled ) {
    $form_elements .= GipTemplate::create_form_element_hidden(
        value => $type,
        name => "type",
    );
}


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
    selected_value => "$protocol",
    disabled => "$disabled",
);

if ( $disabled ) {
    $form_elements .= GipTemplate::create_form_element_hidden(
        value => $protocol,
        name => "protocol",
    );
}

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{port_message},
    id => "port",
    size => "5",
    value => "389",
    type => "number",
    required => "required",
    value => "$port",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{bind_identity_message},
    id => "bind_dn",
    width => "350",
    required => "required",
    value => "$bind_dn",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{bind_password_message},
    id => "password",
    type => "password",
    width => "350",
    required => "required",
    value => "$password",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{base_dn_message},
    id => "base_dn",
    size => "25",
    width => "350",
    required => "required",
    value => "$base_dn",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{username_attribute_message},
    id => "user_attribute",
    required => "required",
    value => "$user_attribute",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{ldap_filter_message},
    width => "350",
    id => "filter",
    value => "$filter",
    readonly => "$readonly",
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
    value => "$comment",
    readonly => "$readonly",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$referer",
    name => "referer",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$id",
    name => "id",
);

my $link;
if ( $connect_error ) {
	$form_elements .= GipTemplate::create_form_element_button(
		value => $$lang_vars{check_ldap_settings_message},
		name => "B2",
	);

	$link="./ip_check_ldap_server.cgi";
} else {
	my $btn_text = "";

    if ( $referer eq "insert" ) {
		$btn_text = $$lang_vars{add_message};
        $link="./ip_insert_ldap_server.cgi";
    } else {
		$btn_text = $$lang_vars{update_message};
        $link="./ip_mod_ldap_server.cgi";
    }

	$form_elements .= GipTemplate::create_form_element_button(
		value => "$btn_text",
		name => "B2",
	);
}


## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_ldap_server_form",
    link => "$link",
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
	} else {
        document.getElementById('user_attribute').value = "";
    }   
}  
-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
