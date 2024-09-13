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
use lib './modules';
use DBI;
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

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
	my $required_perms="read_net_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my @values_locations=$gip->get_loc("$client_id");
my @values_cat_red=$gip->get_cat_net("$client_id");
my $anz_clients_all=$gip->count_clients("$client_id");

my @cc_values=$gip->get_custom_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","network");
my $loc_hash=$gip->get_loc_hash("$client_id");


my $ipv4_only_mode=$global_config[0]->[5] || "yes";

my $align="align=\"right\"";
my $align1="";
my $ori="left";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

$gip->print_init("$$lang_vars{buscar_red_message}","$$lang_vars{advanced_network_search_message}","$$lang_vars{advanced_network_search_message}","$vars_file","$client_id");



my $ip_version = "v4";

my ($form, $form_elements, @item_order, $opt_name, $opt_value);
my %items;
my $onclick;

if ( $anz_clients_all > 1 ) {

  $form_elements .= '
  <div class="form-group row">
    <div class="col-sm-1 control-label">' . $$lang_vars{client_independent_message} . '</div>
    <div class="col-sm-5">';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="yes" id="client_independent" name="client_independent">
          <span class="custom-control-label pr-2"></span>
        </label>
     </div>';

    $form_elements .= '</div></div>';

}


my ($disabled_ipv4, $disabled_ipv6, $checked_ipv4, $checked_ipv6);
$disabled_ipv4=$disabled_ipv6=$checked_ipv4=$checked_ipv4="";
if ( $ipv4_only_mode eq "no" ) {

  $form_elements .= '
  <div class="form-group row">
    <div class="col-sm-1 control-label">' . $$lang_vars{ip_version_message} . '</div>
    <div class="col-sm-5">';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="ipv4" id="ip_version" name="ipv4" selected>
          <span class="custom-control-label pr-2">IPv4</span>
        </label>
     </div>';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="ipv6" id="ip_version" name="ipv6">
          <span class="custom-control-label pr-2">IPv6</span>
        </label>
     </div>';

    $form_elements .= '</div></div>';
}


# IP
my $maxlength = 15;
my $hint_text;

$form_elements .= GipTemplate::create_form_element_text(
    label => "$$lang_vars{redes_message}",
    id => "red",
    size => 30,
    maxlength => $maxlength,
);


# DESCRIPTION

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "descr",
    maxlength => 100,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comentario",
    maxlength => 100,
);

# SITE
@item_order = ();
push @item_order, "";
foreach my $opt( @values_locations) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        next;
    }

	if ( $locs_rw_perm || $locs_ro_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ || $locs_ro_perm eq "9999" || $locs_ro_perm =~ /^$loc_id_opt$/ || $locs_ro_perm =~ /^${loc_id_opt}_/ || $locs_ro_perm =~ /_${loc_id_opt}$/ || $locs_ro_perm =~ /_${loc_id_opt}_/ ) {
            push @item_order, $name;
        }
    } else {
        push @item_order, $name;
    }
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{loc_message},
    item_order => \@item_order,
    id => "loc",
    width => "10em",
    without_search => $$lang_vars{without_loc_message},
#    selected_value => 'EMPTY_OPTION',
);

# CATEGORY
@item_order = ();
foreach my $opt( @values_cat_red) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        unshift @item_order, "EMPTY_OPTION";
        next;
    }
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{cat_message},
    item_order => \@item_order,
    id => "cat_red",
    width => "10em",
    without_search => $$lang_vars{without_cat_message},
);


my $cc_form_elements = $gip->print_custom_net_colums_form("$client_id","$vars_file","","$ip_version","","ip_searchred_form");

$form_elements .= $cc_form_elements;

$form_elements .= GipTemplate::create_form_element_hidden(

    value => $client_id,
    name => "client_id",
);



$form_elements .= "<table><tr><td $align>";
$form_elements .= "$$lang_vars{sincronizado_message}: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td><input type=\"radio\" name=\"vigilada\" value=\"\" checked  class='m-1'> $$lang_vars{todos_message}</td><td><input type=\"radio\" name=\"vigilada\" value=\"y\"  class='m-1'> $$lang_vars{solo_sinc_message} </td><td  class='m-2'><input type=\"radio\" name=\"vigilada\" value=\"n\"  class='m-2'>$$lang_vars{solo_no_sinc_message}\n";
$form_elements .= "</td></tr></table>\n";



$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{buscar_message},
    name => "B2",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "searchred",
    link => "./ip_searchred.cgi",
    method => "POST",
);


print $form;


print "<script type=\"text/javascript\">\n";
print "document.searchred.red.focus();\n";
print "</script>\n";

$gip->print_end("$client_id", "", "", "");

