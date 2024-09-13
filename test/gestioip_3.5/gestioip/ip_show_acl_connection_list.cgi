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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{connection_message}","$vars_file");


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
@acls=$gip->get_acl_connections("$client_id");


my $csv_file_name="acl_con_all.csv";
my $csv_file="./export/$csv_file_name";

unlink $csv_file if -e $csv_file;

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!");

print EXPORT "\"$$lang_vars{id_message}\",\"$$lang_vars{ACL_nr_message}\",\"$$lang_vars{purpose_message}\",\"$$lang_vars{status_message}\",\"$$lang_vars{src_vlan_message}\",\"$$lang_vars{source_message}\",\"$$lang_vars{src_ip_message}\",\"$$lang_vars{application_protocol_message}\",\"$$lang_vars{protocol_message}\",\"$$lang_vars{port_message}\",\"$$lang_vars{bidirectional_head_message}\",\"$$lang_vars{dst_vlan_message}\",\"$$lang_vars{destination_message}\",\"$$lang_vars{dst_ip_message}\",\"$$lang_vars{base_proto_encrypt_message}\",\"$$lang_vars{remark_message}\",\"ACL\"\n";

my $i = 0;
foreach ( @acls ) {
    my $no_acl = "";
    $no_acl = "x" if $acls[$i]->[17] == 1;
	print EXPORT '"' . $acls[$i]->[0] . '","' . $acls[$i]->[1] . '","' . $acls[$i]->[2] . '","' . $acls[$i]->[3] . '","' . $acls[$i]->[4] . '","' . $acls[$i]->[5] . '","' . $acls[$i]->[6] . '","' . $acls[$i]->[7] . '","' . $acls[$i]->[8] . '","' . $acls[$i]->[9] . '","' . $acls[$i]->[10] . '","' . $acls[$i]->[11] . '","' . $acls[$i]->[12] . '","' . $acls[$i]->[13] . '","' . $acls[$i]->[14] . '","' . $acls[$i]->[15] . '","' . $no_acl . '"' . "\n";

		$i++;
}
close EXPORT;

my $onclick_confirmation_delete="";
my $confirmation = $gip->get_config_confirmation("$client_id") || "yes";

if ( $confirmation eq "yes" ) {
	$onclick_confirmation_delete = "onclick=\"saveScrollCoordinates();return confirmation(\'all ACL connections\',\'delete\');\"";
}

if ( $acls[0] ) {
	$gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file");
    print "<span style=\"float: right\"><form name=\"delete_acls\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_delete_acl_connection_list.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{delete_acl_connections_message}\" name=\"B2\" $onclick_confirmation_delete></form><br>\n";
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

