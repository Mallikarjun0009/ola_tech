#!/usr/bin/perl -T -w

# Copyright (C) 2011 Marc Uebel

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
use lib '../modules';
use GestioIP;
use Net::IP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");


my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
        my $required_perms="update_as_perm";
        $gip->check_perms (
                client_id=>"$client_id",
                vars_file=>"$vars_file",
                daten=>\%daten,
                required_perms=>"$required_perms",
        );
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_as_client_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}


#my %values_as_clients=$gip->get_as_clients("$client_id");

#$switches{$_}[1]

#while ( my ($key, @value) = each(%values_as_clients) ) {
#        print "TEST: $key => $value[0]\n";
#    }

#print "<b style=\"float: $ori\">$$lang_vars{add_as_client_message}</b>\n";
print "<br><p>\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"5\"><tr><td $align>";
print "$$lang_vars{as_client_name_message}</td>\n";
print "<td><form method=\"POST\" name=\"admin2\" action=\"$server_proto://$base_uri/res/ip_insert_asclient.cgi\">\n";
print "<input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"as_client_name\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{tipo_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"type\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"comment\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"description\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{phone_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"phone\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{fax_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"fax\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{address_message}</td><td colspan=\"4\" $align1><textarea name=\"address\" cols=\"40\" rows=\"4\" maxlength=\"500\"></textarea></td></tr>\n";
print "<tr><td $align>$$lang_vars{contact_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"contact\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{mail_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"contact_email\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{phone_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"contact_phone\" size=\"10\" maxlength=\"30\"></td><td $align>&nbsp;&nbsp;$$lang_vars{cell_message}</td><td $align1><input type=\"text\" class='form-control form-control-sm' style='width: 12em' name=\"contact_cell\" size=\"10\" maxlength=\"30\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{contact_message}</td><td $align1><input type=\"text\" name=\"contact\" size=\"10\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align1><p><br><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{crear_message}\" name=\"B2\" class=\"btn\"><input type=\"hidden\" name=\"admin_type\" value=\"as_client_add\"></form></td><td></td></tr></table>\n";


print "<script type=\"text/javascript\">\n";
print "document.admin2.as_client_name.focus();\n";
print "</script>\n";

$gip->print_end("$client_id", "", "", "");
