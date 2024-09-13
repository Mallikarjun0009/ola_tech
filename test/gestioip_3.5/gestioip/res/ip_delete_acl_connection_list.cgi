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
use lib '../modules';
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
#my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


my $anz_entries = $daten{'anz_entries'} || "";
my $id_string = "";
if ( $anz_entries ) {
	my $k;
	for ($k=0;$k<=$anz_entries;$k++) {
		my $mu_id = "mass_update_acl_submit_${k}";
		my $id = $daten{$mu_id} || "";
		$id_string .= ", $id" if $id;
	}
	$id_string =~ s/^, //;
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_acl_connection_message}","$vars_file");

if ( $anz_entries && ! $id_string ) {
    $gip->print_error("$client_id","No ACL IDs found")
} else {
    $gip->delete_acl_connection("$client_id","$id_string");
}

my @acls;
@acls=$gip->get_acl_connections("$client_id");


my $onclick_confirmation_delete="";
my $confirmation = $gip->get_config_confirmation("$client_id") || "yes";

if ( $confirmation eq "yes" ) {
    $onclick_confirmation_delete = "onclick=\"saveScrollCoordinates();return confirmation(\'all ACL connections\',\'delete\');\"";
}

if ( $acls[0] ) {
	$gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file");
    print "<span style=\"float: right\"><form name=\"delete_acls\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_delete_acl_connection_list.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{delete_acl_connections_message}\" name=\"B2\" $onclick_confirmation_delete></form><br>\n";
} else {
	print "<p class=\"NotifyText\">$$lang_vars{all_acl_connections_deleted_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
