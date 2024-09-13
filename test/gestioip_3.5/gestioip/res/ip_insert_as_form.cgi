#!/usr/bin/perl -w -T

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
        my $required_perms="create_as_perm";
        $gip->check_perms (
                client_id=>"$client_id",
                vars_file=>"$vars_file",
                daten=>\%daten,
                required_perms=>"$required_perms",
        );
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_as_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @values_clientes=$gip->get_as_clients("$client_id");
my $anz_as_clients=$gip->count_as_clients("$client_id");



my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{as_number_message},
    id => "as_number",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "description",
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
);


if ( $anz_as_clients > "1" ) {
    @item_order = (); 
    push @item_order, "";
    foreach my $opt(@values_clientes) {
        my $name = $opt->[0] || "";
        my $value = $opt->[1] || "";
        if ( $name == "-1" ) {
            next;
        }
        push @item_order, $name;
        $items{$name} = $value;
    }

    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{as_client_message},
        item_order => \@item_order,
        id => "as_client_id",
        width => "10em",
    );

} else {
    $form_elements .= GipTemplate::create_form_element_comment(
        label => $$lang_vars{as_client_message},
        comment => "$$lang_vars{no_as_clients_message}",
        class => "font-italic text-secondary",
    );
}


$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{create_message},
    name => "B2",
);

$form_elements .= GipTemplate::create_focus_js(
    form => "insert_as_form",
    field => "as_number",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_as_form",
    link => "./ip_insert_as.cgi",
    method => "POST",
);

print $form;



#print "<p>\n";
#print "<form name=\"insertvlan_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_as.cgi\"><br>\n";
#print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
#
#print "<tr><td $align>$$lang_vars{as_number_message}</td><td $align1><input name=\"as_number\" type=\"text\"  size=\"10\" maxlength=\"10\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" type=\"text\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" type=\"text\" size=\"30\" maxlength=\"500\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{as_client_message}</td><td $align1>";
#my $j=0;
#my $as_client_id_form="";
#if ( $anz_as_clients > "1" ) {
#
#	print "<select name=\"as_client_id\" size=\"1\">";
#	print "<option></option>\n";
#	my $opt;
#	foreach $opt(@values_clientes) {
#		if ( $values_clientes[$j]->[0] == "-1" ) {
#			$j++;
#			next;
#		}
#
#		print "<option value=\"$values_clientes[$j]->[0]\">$values_clientes[$j]->[1]</option>";
#		$j++;
#	}
#	print "</select></td></tr>\n";
#} else {
#	print "&nbsp;<font color=\"gray\"><i>$$lang_vars{no_as_clients_message}</i></font>\n";
#	$as_client_id_form="<input type=\"hidden\" value=\"-1\" name=\"as_client_id\">";
#}
#
#
#print "</table>\n";
#
#print "<p>\n";
#
#print "<script type=\"text/javascript\">\n";
#	print "document.insertvlan_form.vlan_num.focus();\n";
#print "</script>\n";
#
#print "<span style=\"float: $ori\"><br><p>$as_client_id_form<input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"submit\" value=\"$$lang_vars{add_message}\" name=\"B2\" class=\"input_link_w_net\"></form></span><br><p>\n";

$gip->print_end("$client_id", "", "", "");
