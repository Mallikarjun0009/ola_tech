#!/usr/bin/perl -w -T

use strict;
use Socket;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_line_perm,update_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_dns_user_message}","$vars_file");

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
print "<form name=\"insert_dns_user_form\" method=\"POST\" action=\"./ip_insert_dns_user.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{password_message}</td><td $align1><input name=\"password\" type=\"password\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{realm_message}</td><td $align1><input name=\"realm\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";

print "<td><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><br><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"btn\"></td>\n";


print "</table>\n";
print "</form>\n";

print "<p><br><p><br><p>\n";
print "<script type=\"text/javascript\">\n";
print "document.insert_dns_user_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");

