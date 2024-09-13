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
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_line_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my @values_clientes=$gip->get_ll_clients("$client_id");
my $anz_ll_clients=$gip->count_ll_clients("$client_id");
my @values_ll=$gip->get_ll("$client_id");
my $anz_clients_all=$gip->count_clients("$client_id");
my @values_locations=$gip->get_loc_all("$client_id");


$gip->print_init("$$lang_vars{buscar_line_message}","$$lang_vars{advanced_line_search_message}","$$lang_vars{advanced_line_search_message}","$vars_file","$client_id");

my @cc_values=$gip->get_custom_line_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","line");


my $align="align=\"right\"";
my $align1="";
my $ori="left";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

print "<br><form method=\"POST\" name=\"search_ll\" action=\"$server_proto://$base_uri/ip_search_ll.cgi\">\n";

#if ( $anz_clients_all > 1 ) {
#        print "$$lang_vars{client_independent_message}</td><td><input type=\"checkbox\" name=\"client_independent\" value=\"yes\">";
#        print "</td></tr>";
#}

if ( ! @values_ll ) {
    print "<br><p><b>$$lang_vars{no_ll_message}</b><p>";
    $gip->print_end("$client_id", "", "", "");
}

print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\"><tr><td $align>";
print "<tr><td $align>";
print "$$lang_vars{id_message}:</td><td $align1><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"line\" size=\"1\">";
print "<option></option>";
#SELECT a.id, a.phone_number, a.description, a.comment, a.client_id, c.client_name, c.id, c.type, a.loc, l.loc, a.type, a.service, a.device, a.room, a.ad_number
my $j=0;
foreach ( sort { $a->[0] <=> $b->[0] } @values_ll) {
        $_->[0] = "" if ( $_->[0] eq "NULL" );
        print "<option>$_->[0]</option>" if ( $_->[0] );
        $j++;
}
print "</select></td></tr>";

print "<tr><td $align>$$lang_vars{ll_client_message}</td><td $align1>";
$j=0;
my $ll_client_id_form="";
if ( $anz_ll_clients > "1" ) {

    print "<select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"ll_client_id\" size=\"1\">";
    print "<option></option>\n";
    my $opt;
    foreach $opt(@values_clientes) {
        if ( $values_clientes[$j]->[0] == "-1" ) {
            $j++;
            next;
        }

        print "<option value=\"$values_clientes[$j]->[0]\">$values_clientes[$j]->[1]</option>";
        $j++;
    }
    print "</select></td></tr>\n";
} else {
    print "&nbsp;<font color=\"gray\"><i>$$lang_vars{no_ll_clients_message}</i></font>\n";
    $ll_client_id_form="<input type=\"hidden\" value=\"-1\" name=\"ll_client_id\">";
}


#print "<tr><td $align>$$lang_vars{tipo_message}</td><td $align1><input name=\"type\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{tipo_message}</td><td $align1><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"type\" size=\"1\">";
print "<option></option>";
my $values_types = $custom_colums_select{"9998"}->[2];
foreach (@$values_types) {
    my $type_opt = $_;
	print "<option value=\"$type_opt\">$type_opt</option>";
}
print "</select></td><td>";

#print "<tr><td $align>$$lang_vars{service_message}</td><td $align1><input name=\"service\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{service_message}</td><td $align1><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"service\" size=\"1\">";
print "<option></option>";
my $values_service = $custom_colums_select{"9999"}->[2];
foreach (@$values_service) {
    my $opt = $_;
	print "<option value=\"$opt\">$opt</option>";
}
print "</select></td><td>";
print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"100\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{phone_number_message}</td><td $align1><input name=\"phone_number\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{administrative_number_message}</td><td $align1><input name=\"ad_number\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"50\"></td></tr>\n";

$j=0;
print "<tr><td $align>$$lang_vars{loc_message}</td><td $align1><select class='custom-select custom-select-sm m-2' style='width: 12em' name=\"loc_id\" size=\"1\">";
print "<option></option>";
foreach (@values_locations) {
        my $loc_id = $values_locations[$j]->[0] || "";
        if ( $locs_rw_perm || $locs_ro_perm ) {
            if ( $locs_rw_perm ne "9999" && $locs_rw_perm !~ /^$loc_id$/ && $locs_rw_perm !~ /^${loc_id}_/ && $locs_rw_perm !~ /_${loc_id}$/ && $locs_rw_perm !~ /_${loc_id}_/ && $locs_ro_perm ne "9999" && $locs_ro_perm !~ /^$loc_id$/ && $locs_ro_perm !~ /^${loc_id}_/ && $locs_ro_perm !~ /_${loc_id}$/ && $locs_ro_perm !~ /_${loc_id}_/ ) {
                $j++;
                next;
            }
        }
        if ( $loc_id eq "-1") {
            $j++;
            next;
        }
        print "<option value=\"$loc_id\">$values_locations[$j]->[1]</option>";
        $j++;
}

print "</td></tr>\n";
print "<tr><td $align>$$lang_vars{room_message}</td><td $align1><input name=\"room\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"15\" maxlength=\"100\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{connected_device_message}</td><td $align1><input name=\"device\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em'  size=\"15\" maxlength=\"100\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' size=\"30\" maxlength=\"500\"></td></tr>\n";



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

print "<br><p><input name=\"search_index\" type=\"hidden\" value=\"true\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{buscar_message}\" name=\"B2\" class=\"btn\" style=\"float: $ori\"></form>\n";


$gip->print_end("$client_id", "", "", "");
