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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{acl_list_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @acls;
@acls=$gip->get_acls("$client_id");

print <<EOF;
<form name="search_acl_connection" method="POST" action="$server_proto://$base_uri/ip_search_acl.cgi" style="display:inline"><input type="hidden" name="client_id" value="$client_id"><input type="submit" value="" class="button" style=\"float: right; cursor:pointer;\"><input type=\"text\" size=\"15\" name=\"match\" style=\"float: right;\"> 
EOF
print "</form>\n";

#my $onclick_confirmation_delete="";
#my $confirmation = $gip->get_config_confirmation("$client_id") || "yes";
#
#if ( $confirmation eq "yes" ) {
#    $onclick_confirmation_delete = "onclick=\"saveScrollCoordinates();return confirmation(\'all ACLs\',\'delete\');\"";
#}



if ( $acls[0] ) {
	$gip->PrintACLTab("$client_id",\@acls,"$vars_file");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
