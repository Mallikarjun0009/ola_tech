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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ldap_groups_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my @column_names;

if ( $user_management_enabled eq "yes" ) {
#    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{user_group_message}","$$lang_vars{group_attrib_is_dn_message}","$$lang_vars{comentario_message}");
    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{user_group_message}","$$lang_vars{comentario_message}");
} else {
#    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{group_attrib_is_dn_message}","$$lang_vars{comentario_message}");
    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{comentario_message}");
}

#for my $key ( keys %ENV ) {
#    print "TEST: $key - $ENV{$key}<br>\n";
#}


my %column_names_db = (
    $$lang_vars{id_message} => "id",
    $$lang_vars{name_message} => "name",
    $$lang_vars{dn_message} => "dn",
    $$lang_vars{ldap_server_message} => "ldap_server_id",
    $$lang_vars{user_group_message} => "user_group_id",
#    $$lang_vars{group_attrib_is_dn_message} => "group_attrib_is_dn",
    $$lang_vars{comentario_message} => "comment",
    $$lang_vars{enabled_message} => "enabled",
);

my %user_group_hash = $gip->get_user_group_hash("$client_id");
my %ldap_server_hash = $gip->get_ldap_server_hash("$client_id");
#my %group_attrib_is_dn;
#push @{$group_attrib_is_dn{1}}, "DN";
#push @{$group_attrib_is_dn{2}}, "$$lang_vars{group_attrib_is_dn_message}";

my %id_columns = (
    user_group_id => \%user_group_hash,
    ldap_server_id => \%ldap_server_hash,
#    group_attrib_is_dn => \%group_attrib_is_dn,
);

my %symbol_columns = (
    $$lang_vars{enabled_message} => "x",
);

my $mod_form = "ip_mod_ldap_group_form.cgi";
my $delete_form = "ip_delete_ldap_group.cgi";
my $confirm_message = "$$lang_vars{delete_ldap_group_confirm_message}";


$gip->PrintGenericTab1("$client_id", "$vars_file", "" ,\@column_names, \%column_names_db, "$mod_form", "$delete_form", "$confirm_message", \%id_columns, sub { $gip->get_table_hash("$client_id","ldap_group", "id") }, \%symbol_columns);


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
