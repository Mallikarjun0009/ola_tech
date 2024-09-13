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
	my $required_perms="read_vlan_perm,create_vlan_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @values_clientes=$gip->get_vlan_providers("$client_id");
my $anz_vlan_providers=$gip->count_vlan_providers("$client_id");


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);

$form_elements .= GipTemplate::create_form_element_text(
	label => $$lang_vars{vlan_number_message},
	id => "vlan_num",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
	label => $$lang_vars{vlan_name_message},
	id => "vlan_name",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
	label => $$lang_vars{description_message},
	id => "comment",
);

if ( $anz_vlan_providers >= "1" ) {
	my $j = 0;
	foreach my $opt(@values_clientes) {
		$opt_name = $values_clientes[$j]->[0] || "";
		$opt_value = $values_clientes[$j]->[1];
		push @item_order, $opt_name;
		$items{$opt_name} = $opt_value;
		$j++;
	}

	$form_elements .= GipTemplate::create_form_element_select(
		name => $$lang_vars{vlan_providers_message},
		item_order => \@item_order,
		items => \%items,
		id => "vlan_provider_id",
		width => "10em",
	);

} else {
	$form_elements .= GipTemplate::create_form_element_comment(
		label => $$lang_vars{vlan_provider_message},
		id => $$lang_vars{vlan_provider_message},
		comment => $$lang_vars{no_vlan_providers_message},
	);

}


$form_elements .= '
<div class="form-group row">
<label class="control-label col-sm-1" for="' . $$lang_vars{bg_message} . '">' . $$lang_vars{bg_message} . '</label>
<div class="col-sm-10">
<select name="bg_color" class="custom-select" size="3" style="width:150px">
<OPTION class="gold" value="amar">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</OPTION>
<OPTION class="DarkOrange" value="orano"></OPTION>
<OPTION class="brown" value="maro"></OPTION>
<OPTION class="red" value="rojo"></OPTION>
<OPTION class="pink" value="pink"></OPTION>
<OPTION class="LightCyan" value="azulcc"></OPTION>
<OPTION class="LightBlue" value="azulc"></OPTION>
<OPTION class="dodgerblue" value="azulo"></OPTION>
<OPTION class="LimeGreen" value="verc"></OPTION>
<OPTION class="SeaGreen" value="vero"></OPTION>
<OPTION class="white" value="blan"></OPTION>
<OPTION class="black" value="negr"></OPTION>
</SELECT>
</div>
</div>';

$form_elements .= '
<div class="form-group row">
<label class="control-label col-sm-1" for="' . $$lang_vars{font_message} . '">' . $$lang_vars{font_message} . '</label>
<div class="col-sm-10">
<select name="font_color" class="custom-select" size="3" style="width:150px">
<OPTION class="gold" value="amar">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</OPTION>
<OPTION class="DarkOrange" value="orano"></OPTION>
<OPTION class="brown" value="maro"></OPTION>
<OPTION class="red" value="rojo"></OPTION>
<OPTION class="LightCyan" value="azulcc"></OPTION>
<OPTION class="LightBlue" value="azulc"></OPTION>
<OPTION class="dodgerblue" value="azulo"></OPTION>
<OPTION class="LimeGreen" value="verc"></OPTION>
<OPTION class="SeaGreen" value="vero"></OPTION>
<OPTION class="white" value="blan"></OPTION>
<OPTION class="black" value="negr"></OPTION>
</SELECT>
</div>
</div>';


$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


$form_elements .= GipTemplate::create_form_element_button(
	value => $$lang_vars{add_message},
	name => "B2",
);


$form = GipTemplate::create_form(
	form_elements => $form_elements,
	form_id => "insertvlan_form",
	link => "$server_proto://$base_uri/res/ip_insertvlan.cgi",
	method => "POST",
);

print $form;

print "<script type=\"text/javascript\">\n";
	print "document.insertvlan_form.vlan_num.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
