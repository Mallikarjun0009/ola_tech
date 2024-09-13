#!/usr/bin/perl -w -T

# Copyright (C) 2013 Marc Uebel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.



use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();

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


my $id = $daten{'id'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_client_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $id !~ /^\d{1,4}$/;

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my %values_clients=$gip->get_client_hash_all("$id");

my $client = $values_clients{$id}[0];
my $phone = $values_clients{$id}[1] || "";
my $fax = $values_clients{$id}[2] || "";
my $address = $values_clients{$id}[3] || "";
my $comment = $values_clients{$id}[4] || "";
my $contact_name_1 = $values_clients{$id}[5] || "";
my $contact_phone_1 = $values_clients{$id}[6] || "";
my $contact_cell_1 = $values_clients{$id}[7] || "";
my $contact_email_1 = $values_clients{$id}[8] || "";
my $contact_comment_1 = $values_clients{$id}[9] || "";
my $contact_name_2 = $values_clients{$id}[10] || "";
my $contact_phone_2 = $values_clients{$id}[11] || "";
my $contact_cell_2 = $values_clients{$id}[12] || "";
my $contact_email_2 = $values_clients{$id}[13] || "";
my $contact_comment_2 = $values_clients{$id}[14] || "";
my $contact_name_3 = $values_clients{$id}[15] || "";
my $contact_phone_3 = $values_clients{$id}[16] || "";
my $contact_cell_3 = $values_clients{$id}[17] || "";
my $contact_email_3 = $values_clients{$id}[18] || "";
my $contact_comment_3 = $values_clients{$id}[19] || "";
my $default_resolver = $values_clients{$id}[20] || "";
my $dns_server_1 = $values_clients{$id}[21] || "";
my $dns_server_2 = $values_clients{$id}[22] || "";
my $dns_server_3 = $values_clients{$id}[23] || "";


print "<p>\n";
print "<form name=\"mod_client_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_client.cgi\"><br>\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{client_message}</td><td $align1><input name=\"client_name\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'  size=\"15\" maxlength=\"30\" value=\"$client\"></td></tr>";

print "<tr><td $align><img src=\"$server_proto://$base_uri/imagenes/telefon.png\" title=\"$$lang_vars{phone_message}\"></td><td colspan=\"9\" $align1><input name=\"phone\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"15\" maxlength=\"30\" value=\"$phone\"></td></tr>";
print "<tr><td $align><img src=\"$server_proto://$base_uri/imagenes/fax.png\" title=\"$$lang_vars{fax_message}\"></td><td colspan=\"9\" $align1><input name=\"fax\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"15\" maxlength=\"30\" value=\"$fax\"></td></tr>";
print "<tr><td $align>$$lang_vars{address_message}</td><td colspan=\"9\" $align1><textarea name=\"address\" cols=\"40\" rows=\"4\" maxlength=\"500\">$address</textarea></td></tr>";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td colspan=\"9\" $align1><input name=\"comment\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"35\" maxlength=\"200\" value=\"$comment\"></td></tr>";
print "<tr><td colspan=\"10\"></td></tr>\n";
print "<tr nowrap><td $align>$$lang_vars{contact_message}</td><td $align1><input name=\"contact_name_1\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'  size=\"18\" maxlength=\"200\" value=\"$contact_name_1\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/telefon.png\" title=\"$$lang_vars{phone_message}\"></td><td><input name=\"contact_phone_1\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"12\" maxlength=\"25\" value=\"$contact_phone_1\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/handy.png\" title=\"$$lang_vars{cell_message}\"></td><td><input name=\"contact_cell_1\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"10\" maxlength=\"25\" value=\"$contact_cell_1\"> </td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/email.png\" title=\"$$lang_vars{mail_message}\"></td><td><input name=\"contact_email_1\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"15\" maxlength=\"50\" value=\"$contact_email_1\"> </td><td>&nbsp; $$lang_vars{comentario_message}</td><td><input name=\"contact_comment_1\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"22\" maxlength=\"50\" value=\"$contact_comment_1\"></td></tr>";
print "<tr nowrap><td $align>$$lang_vars{contact_message}</td><td $align1><input name=\"contact_name_2\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'  size=\"18\" maxlength=\"200\" value=\"$contact_name_2\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/telefon.png\" title=\"$$lang_vars{phone_message}\"></td><td><input name=\"contact_phone_2\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"12\" maxlength=\"25\" value=\"$contact_phone_2\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/handy.png\" title=\"$$lang_vars{cell_message}\"></td><td><input name=\"contact_cell_2\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"10\" maxlength=\"25\" value=\"$contact_cell_2\"> </td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/email.png\" title=\"$$lang_vars{mail_message}\"></td><td><input name=\"contact_email_2\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"15\" maxlength=\"50\" value=\"$contact_email_2\"> </td><td>&nbsp; $$lang_vars{comentario_message}</td><td><input name=\"contact_comment_2\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"22\" maxlength=\"50\" value=\"$contact_comment_2\"></td></tr>";
print "<tr nowrap><td $align>$$lang_vars{contact_message}</td><td $align1><input name=\"contact_name_3\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'  size=\"18\" maxlength=\"200\" value=\"$contact_name_3\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/telefon.png\" title=\"$$lang_vars{phone_message}\"></td><td><input name=\"contact_phone_3\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"12\" maxlength=\"25\" value=\"$contact_phone_3\"></td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/handy.png\" title=\"$$lang_vars{cell_message}\"></td><td><input name=\"contact_cell_3\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"10\" maxlength=\"25\" value=\"$contact_cell_3\"> </td><td>&nbsp; <img src=\"$server_proto://$base_uri/imagenes/email.png\" title=\"$$lang_vars{mail_message}\"></td><td><input name=\"contact_email_3\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"15\" maxlength=\"50\" value=\"$contact_email_3\"> </td><td>&nbsp; $$lang_vars{comentario_message}</td><td><input name=\"contact_comment_3\" type=\"text\" style='width: 12em;' class='form-control form-control-sm'   size=\"22\" maxlength=\"50\" value=\"$contact_comment_3\"></td></tr>";
print "<tr><td><br><input name=\"client_action\" type=\"hidden\" value=\"mod_client\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"id\" type=\"hidden\" value=\"$id\"><input type=\"submit\" class='btn' value=\"$$lang_vars{submit_message}\" name=\"B1\" class=\"input_link_w\"></td><td></td></tr>";


print "</table>\n";
print "</form>\n";

print "<p>\n";

print "<script type=\"text/javascript\">\n";
	print "document.mod_client_form.client_name.focus();\n";
print "</script>\n";

$gip->print_end("$client_id", "", "", "");
