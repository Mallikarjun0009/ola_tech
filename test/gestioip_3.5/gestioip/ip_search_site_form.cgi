#!/usr/bin/perl -T -w

# Copyright (C) 2019 Marc Uebel

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
use lib './modules';
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri=$gip->get_base_uri();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();


my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my @values_locations=$gip->get_loc("$client_id");
my $anz_clients_all=$gip->count_clients("$client_id");

my $ipv4_only_mode=$global_config[0]->[5] || "yes";

$gip->print_init("$$lang_vars{buscar_site_message}","$$lang_vars{advanced_site_search_message}","$$lang_vars{advanced_site_search_message}","$vars_file","$client_id");

my @cc_values=$gip->get_custom_site_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","site");


my $align="align=\"right\"";
my $align1="";
my $ori="left";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

print "<br><form method=\"POST\" name=\"search_site\" action=\"$server_proto://$base_uri/ip_search_site.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\"><tr><td $align>";

#if ( $anz_clients_all > 1 ) {
#        print "$$lang_vars{client_independent_message}</td><td><input type=\"checkbox\" name=\"client_independent\" value=\"yes\">";
#        print "</td></tr>";
#}

print "<tr><td colspan=\"4\"><br></td></tr>\n";
print "<tr><td $align>";
print "$$lang_vars{loc_message}:</td><td $align1><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"loc\" size=\"1\">";
print "<option></option>";
my $j=0;
foreach (@values_locations) {
        $values_locations[$j]->[0] = "" if ( $values_locations[$j]->[0] eq "NULL" );
        print "<option>$values_locations[$j]->[0]</option>" if ( $values_locations[$j]->[0] );
        $j++;
}
print "<option value=\"NULL\">$$lang_vars{without_loc_message}</option>";

print "</select></td></tr>";

#print "<tr><td colspan=\"2\"><br></td></tr>";


for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
    my $cc_name  = $cc_values[$k]->[0];
    my $cc_id  = $cc_values[$k]->[1];
    if ( $cc_name ) {
        if ( exists $custom_colums_select{$cc_id} ) {
            # CC column is a select
            my $select_values = $custom_colums_select{$cc_id}->[2];

            print "<tr><td $align>$cc_name</td><td><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"cc_id_${cc_id}\" size=\"1\">\n";
            print "<option></option>";
            foreach (@$select_values) {
                my $opt = $_;
                $opt = $gip->remove_whitespace_se("$opt");
                print "<option value=\"$opt\">$opt</option>";
            }
            print "</select></td></tr>\n";
            next;
		} else {
			print "<tr><td $align>$cc_name</td><td><input type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' name=\"cc_id_${cc_id}\" size=\"15\"></td></tr>";
		}
	}
}

print "<tr><td colspan=\"2\"><br></td></tr>";
print "</td></tr></table>";

#TEST
#print "<br><p><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{buscar_message}\" name=\"B2\" class=\"input_link_w\" style=\"float: $ori\"></form>\n";
print "<br><p><input name=\"search_index\" type=\"hidden\" value=\"true\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{buscar_message}\" name=\"B2\" class=\"btn\" style=\"float: $ori\"></form>\n";

print "<script type=\"text/javascript\">\n";
print "document.searchip.loc.focus();\n";
print "</script>\n";

$gip->print_end("$client_id", "", "", "");
