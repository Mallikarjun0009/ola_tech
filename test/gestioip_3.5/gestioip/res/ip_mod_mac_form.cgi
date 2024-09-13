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


## check Permissions
#my @global_config = $gip->get_global_config("$client_id");
#my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm,update_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{modify_mac_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}

my $id=$daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;

my @values = $gip->get_macs("$client_id","$id");
my $mac = $values[0]->[1];
my $duid = $values[0]->[2] || "";
my $account = $values[0]->[3] || "";
my $host = $values[0]->[4] || "";
my $comment = $values[0]->[5] || "";

print "<p>\n";
print "<form name=\"mod_mac_form\" method=\"POST\" action=\"./ip_mod_mac.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{mac_message}</td><td $align1><input name=\"mac\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$mac\"  size=\"15\" maxlength=\"50\"> <i>($$lang_vars{ejemplo_message}: e0:13:fa:c4:c3:40)</i></td></tr>\n";
print "<tr><td $align>$$lang_vars{duid_message}</td><td $align1><input name=\"duid\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  value=\"$duid\" size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{account_message}</td><td $align1><input name=\"account\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$account\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{host_message}</td><td $align1><input name=\"host\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$host\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$comment\"  size=\"30\" maxlength=\"100\"></td></tr>\n";

print "</table>\n";

print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"hidden\" name=\"id\" value=\"$id\"><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";

print "<p><br><p><br><p>\n";

$gip->print_end("$client_id", "", "", "");

