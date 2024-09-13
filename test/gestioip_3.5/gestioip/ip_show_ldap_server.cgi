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


use DBI;
use strict;
use lib './modules';
use GestioIP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();
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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ldap_servers_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my @column_names = ("$$lang_vars{name_message}","$$lang_vars{server_message}","$$lang_vars{enabled_message}","$$lang_vars{tipo_message}","$$lang_vars{protocol_message}","$$lang_vars{port_message}","$$lang_vars{bind_identity_message}","$$lang_vars{base_dn_message}","$$lang_vars{username_attribute_message}","$$lang_vars{ldap_filter_message}","$$lang_vars{comentario_message}");

my %column_positions = (
    $$lang_vars{name_message} => 0,
    $$lang_vars{server_message} => 1,
    $$lang_vars{tipo_message} => 2,
    $$lang_vars{protocol_message} => 3,
    $$lang_vars{port_message} => 4,
    $$lang_vars{bind_identity_message} => 5,
    $$lang_vars{base_dn_message} => 7,
    $$lang_vars{username_attribute_message} => 8,
    $$lang_vars{ldap_filter_message} => 9,
    $$lang_vars{comentario_message} => 10,
    $$lang_vars{enabled_message} => 11,
);

my $mod_form = "ip_mod_ldap_server_form.cgi";
my $delete_form = "ip_delete_ldap_server.cgi";

$gip->PrintGenericTab("$client_id", "$vars_file", "" ,\@column_names, \%column_positions, $mod_form, $delete_form);

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
