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
	my $required_perms="update_vlan_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $provider_id = "";
$provider_id=$daten{'provider_id'} if $daten{'provider_id'};
if ( $provider_id !~ /^\d{1,4}$/ ) {
        $gip->print_init("gestioip","$$lang_vars{edit_vlan_provider_message}","$$lang_vars{edit_vlan_provider_message}","$vars_file","$client_id");
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} $provider_id");
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_vlan_provider_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}


my @values_vlan_provider=$gip->get_vlan_provider("$client_id","$provider_id");


my $provider_name = $values_vlan_provider[0]->[0] || "";
my $provider_comment = $values_vlan_provider[0]->[1] || "";



my @values_vlan_providers=$gip->get_vlan_providers("$client_id");

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{vlan_provider_name_message},
    id => "name",
    value => $provider_name,
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    value => $provider_comment,
    id => "comment",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $provider_id,
    name => "provider_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{cambiar_message},
    name => "B2",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_vlanprovider_form",
    link => "$server_proto://$base_uri/res/ip_mod_vlanprovider.cgi",
    method => "POST",
);

print $form;

print "<script type=\"text/javascript\">\n";
print "document.mod_vlanprovider_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
