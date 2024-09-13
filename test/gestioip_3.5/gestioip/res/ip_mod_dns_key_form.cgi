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
	my $required_perms="manage_sites_and_cats_perm";
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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_tsig_key_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_tsig_key_message}","$vars_file");

my $id=$daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;
my $tsig_key=$daten{'tsig_key'} || "";
my $name=$daten{'name'} || "";
my $description=$daten{'description'} || "";

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

print "<p>\n";
print "<form name=\"mod_dns_key_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_dns_key.cgi\"><br>\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{tsig_key_message}</td><td $align1><input name=\"tsig_key\" value=\"$tsig_key\" type=\"text\" class='form-control form-control-sm m-2' style='width: 60em' size=\"60\" maxlength=\"150\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" value=\"$name\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" value=\"$description\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
print "</table>\n";
print "<p>\n";
print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"submit\" value=\"$$lang_vars{update_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";

print "<script type=\"text/javascript\">\n";
print "document.mod_dns_key_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
