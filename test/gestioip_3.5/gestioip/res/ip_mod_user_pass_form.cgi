#!/usr/bin/perl -w -T

# Copyright (C) 2020 Marc Uebel

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

my $id = $daten{'id'};

# Parameter check

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
) || "";

my $user=$ENV{'REMOTE_USER'};
my %values_users=$gip->get_user_hash("$client_id");
my $name=$values_users{$id}[0];

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" && $user ne $name ) {
	my $required_perms="manage_user_perm";
		$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_user_password_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_user_password_message}","$vars_file");

print <<EOF;
<script type='text/javascript' src='$server_proto://$base_uri/js/PrintRedTab.js'></script>
EOF


$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 1") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 2") if $id !~ /^\d{1,5}$/;


print "<br><h4>$$lang_vars{change_password_for_message}: $name</h4><br>\n";

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{new_login_pass_message},
    id => "login_pass",
    type => "password",
	required => 1,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{retype_new_login_pass_message},
    id => "retype_login_pass",
    type => "password",
	required => 1,
);


$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $id,
    name => "id",
);

$onclick = "";
$onclick = "onclick=\"return confirmation(\'$$lang_vars{update_user_password_message}\', \'\', \'\', \'$$lang_vars{cause_logout_message}\');\"" if $user eq $name;
$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
    onclick => "$onclick",
);

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_user_pass_form",
    link => "./ip_mod_user_pass.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
	print "document.mod_user_pass_form.login_pass.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
