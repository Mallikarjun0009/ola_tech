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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_ldap_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_ldap_group_message}","$vars_file");

my $id = $daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $id !~ /^\d+/;

my %ldap_server = $gip->get_ldap_server_hash("$client_id");
my %user_groups = $gip->get_user_group_hash("$client_id");

my @values=$gip->get_table_array("$client_id","ldap_group","$id");
my $name = $values[0][1];
my $dn = $values[0][2];
my $user_group_id = $values[0][3] || "";
my $ldap_server_id = $values[0][4] || "";
my $comment = $values[0][5] || "";
my $group_attrib_is_dn = $values[0][6] || "";
my $enabled = $values[0][7] || "";

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    width => "350",
    required => "required",
	value => $name,
);

my $checked = "";
$checked = 1 if $enabled;

$form_elements .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{enabled_message},
    id => "enabled",
    value => "1",
    checked => "$checked",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{dn_message},
    id => "dn",
    width => "350",
#    hint_text => $$lang_vars{dns_or_ip_explic_message},
    required => "required",
	value => $dn,
);

@item_order = ();
push @item_order, "";
while ( my ($key, @value) = each(%ldap_server) ) {
        my $name=$value[0]->[0];
        my $id=$key;
        push @item_order, $name;
        $items{$name} = $id;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{ldap_server_message},
    item_order => \@item_order,
    items => \%items,
    id => "ldap_server",
    width => "10em",
    required => "required",
    selected_value => "$ldap_server_id",

);


#@item_order = ();
#my @values_protocol = ("DN", "$$lang_vars{username_message}");
#foreach my $opt(@values_protocol) {
#    my $name = $opt || "";
#    push @item_order, $name;
#}
#
#
#my %group_attrib_is_dn = (
#	1 =>"DN",
#	2 => "$$lang_vars{username_message}",
#);
#
#$onclick = "onchange='changePort(this.value);'";
#$form_elements .= GipTemplate::create_form_element_select(
#    name => $$lang_vars{group_attrib_is_dn_message},
#    item_order => \@item_order,
#    id => "group_attrib_is_dn",
#    width => "10em",
#    onclick => $onclick,
#    required => "required",
#    selected_value => "$group_attrib_is_dn{$group_attrib_is_dn}",
#);


@item_order = ();
undef %items;

push @item_order, "";
while ( my ($key, @value) = each(%user_groups) ) {
        my $name=$value[0]->[0];
        my $id=$key;
        push @item_order, $name;
        $items{$name} = $id;
}

if ( $user_management_enabled eq "yes" ) {
    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{user_group_message},
        item_order => \@item_order,
        items => \%items,
        id => "user_group",
        width => "10em",
        required => "required",
        selected_value => "$user_group_id",
    );
} else {
    $form_elements .= GipTemplate::create_form_element_hidden(
        value => 1,
        name => "user_group",
    );
}

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


#$form_elements .= GipTemplate::create_form_element_button(
#    value => $$lang_vars{check_ldap_group_message},
#    name => "B2",
#);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);


## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_ldap_group_form",
    link => "./ip_mod_ldap_group.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.forms.mod_ldap_group_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
