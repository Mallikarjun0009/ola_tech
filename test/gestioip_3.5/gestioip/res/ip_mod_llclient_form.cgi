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



$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_client_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}

my $ll_client_id=$daten{'ll_client_id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $ll_client_id;

my @ll_client_values=$gip->get_one_ll_client("$client_id","$ll_client_id");
my $name=$ll_client_values[0]->[1] || "";
my $type=$ll_client_values[0]->[2] || "";
my $description=$ll_client_values[0]->[3] || "";
my $comment=$ll_client_values[0]->[4] || "";
my $phone=$ll_client_values[0]->[5] || "";
my $fax=$ll_client_values[0]->[6] || "";
my $address=$ll_client_values[0]->[7] || "";
my $contact=$ll_client_values[0]->[8] || "";
my $contact_email=$ll_client_values[0]->[9] || "";
my $contact_phone=$ll_client_values[0]->[10] || "";
my $contact_cell=$ll_client_values[0]->[11] || "";

print "<p>\n";
print "<form name=\"mod_ll_client_form\" method=\"POST\" action=\"./ip_mod_llclient.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"1\"><tr><td $align>";
print "$$lang_vars{ll_client_name_message}</td><td><input type=\"text\" name=\"name\" class='form-control form-control-sm m-2' style='width: 12em'   value=\"$name\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input type=\"text\" name=\"comment\" class='form-control form-control-sm m-2' style='width: 12em'   value=\"$comment\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input type=\"text\" name=\"description\" class='form-control form-control-sm m-2' style='width: 12em'   value=\"$description\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{phone_message}</td><td $align1><input type=\"text\" name=\"phone\" class='form-control form-control-sm m-2' style='width: 12em'   size=\"10\" value=\"$phone\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{fax_message}</td><td $align1><input type=\"text\" name=\"fax\" class='form-control form-control-sm m-2' style='width: 12em'   value=\"$fax\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{address_message}</td><td colspan=\"4\" $align1><textarea name=\"address\" class='form-control form-control-sm m-2' style='width: 12em'   cols=\"40\" rows=\"4\" maxlength=\"500\">$address</textarea></td></tr>\n";
print "<tr><td $align>$$lang_vars{contact_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm m-2' style='width: 8em'  name=\"contact\" value=\"$contact\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{mail_message}</td><td $align1><input type=\"text\" name=\"contact_email\"  class='form-control form-control-sm m-2' style='width: 8em' value=\"$contact_email\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{phone_message}</td><td $align1><input type=\"text\"   class='form-control form-control-sm m-2' style='width: 8em' name=\"contact_phone\" value=\"$contact_phone\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{cell_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm m-2' style='width: 8em' name=\"contact_cell\" value=\"$contact_cell\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align1><p><input type=\"hidden\" name=\"ll_client_id\" value=\"$ll_client_id\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"input_link_w\"><input type=\"hidden\" name=\"admin_type\" value=\"ll_client_add\"></form></td><td></td></tr></table>\n";

print "</form>\n";

print "<p><br><p><br><p>\n";

print "<script type=\"text/javascript\">\n";
print "document.mod_ll_client_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");

