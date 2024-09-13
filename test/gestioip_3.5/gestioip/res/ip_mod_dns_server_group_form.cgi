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
	my $required_perms="manage_dns_server_group_perm";
		$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $id = $daten{'id'};

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_dns_server_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_dns_server_group_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 1") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 2") if $id !~ /^\d{1,5}$/;

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my @obj = $gip->get_dns_server_group_from_id("$client_id", "$id");
my $name = $obj[0][0];
my $description = $obj[0][1] || "";
my $dns_server1 = $obj[0][2] || "";
my $dns_server2 = $obj[0][3] || "";
my $dns_server3 = $obj[0][4] || "";




my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    value => $name,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_1_message},
    id => "dns_server1",
    value => $dns_server1,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_2_message},
    id => "dns_server2",
    value => $dns_server2,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{server_3_message},
    value => $dns_server3,
    id => "dns_server3",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    value => $description,
    id => "description",
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


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_dns_server_group_form",
    link => "./ip_mod_dns_server_group.cgi",
    method => "POST",
);

print $form;



#print "<p>\n";
#print "<form name=\"mod_dns_server_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_dns_server_group.cgi\"><br>\n";
#print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
#
#print "<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" value=\"$name\" type=\"text\" size=\"15\" maxlength=\"20\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" value=\"$description\" type=\"text\" size=\"15\" maxlength=\"500\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{server_1_message}</td><td $align1><input name=\"dns_server1\" value=\"$dns_server1\" type=\"text\" size=\"15\" maxlength=\"500\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{server_2_message}</td><td $align1><input name=\"dns_server2\" value=\"$dns_server2\" type=\"text\" size=\"15\" maxlength=\"500\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{server_3_message}</td><td $align1><input name=\"dns_server3\" value=\"$dns_server3\" type=\"text\" size=\"15\" maxlength=\"500\"></td></tr>\n";
#
#
#print "</table>\n";
#
#print "<p>\n";

print "<script type=\"text/javascript\">\n";
print "document.mod_dns_server_group_form.name.focus();\n";
print "</script>\n";

#print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{cambiar_message}\" name=\"B2\" class=\"input_link_w_net\"></form></span><br><p>\n";

$gip->print_end("$client_id", "", "", "");
