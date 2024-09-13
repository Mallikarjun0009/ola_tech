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

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm,create_host_perm,update_host_perm,execute_update_snmp_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $ip_version=$daten{'ip_version'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{discover_network_via_snmp_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}


my $ipv4_only_mode=$global_config[0]->[5] || "yes";

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $ip_version !~ /^(v4|v6)$/;

my $module = "SNMP::Info";
my $module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{snmp_info_not_found_message}") if $module_check != "1";

$module = "Net::DNS";
$module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{net_dns_not_found_message}") if $module_check != "1";



my $red_num = $daten{'red_num'} || $gip->$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");

my @values_redes=$gip->get_red("$client_id","$red_num");
my $red = "$values_redes[0]->[0]" || "";
my $BM = "$values_redes[0]->[1]" || "";
$gip->print_error("$client_id","$$lang_vars{no_valid_sheet_message}") if ! $red;

my $snmp_group_name_db = $gip->get_custom_column_entry("$client_id","$red_num","SNMPGroup") || "";
my @snmp_groups=$gip->get_snmp_groups("$client_id");
#$gip->prepare_snmp_version_form("$client_id","$vars_file","$snmp_group_name_db",\@snmp_groups);


my $confirmation = $gip->get_config_confirmation("$client_id") || "yes";
my $onclick = "";
if ( $confirmation eq "yes" ) {
        $onclick =  "onclick=\"return confirmation();\"";
}

print "<p><h5>$$lang_vars{redes_message} ${red}/${BM}</h5>\n";
print "<p>\n";
print "<form name=\"snmp_form\"  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_discover_net_snmp.cgi\">\n";

if ( $snmp_groups[0] ) {

print "$$lang_vars{use_snmp_group_message} <input type=\"radio\" value=\"1\" name=\"UseSNMPGroup\" id=\"useSNMPGroup\" value=\"\" onchange=\"changeText2('useSNMPGroup')\" checked> &nbsp;&nbsp;&nbsp;";
print "$$lang_vars{introduce_snmp_manual_message} <input type=\"radio\" value=\"1\" name=\"noUseSNMPGroup\" id=\"noUseSNMPGroup\" value=\"\" onchange=\"changeText2('noUseSNMPGroup')\">";
} else {
print "$$lang_vars{use_snmp_group_message} <input type=\"radio\" value=\"1\" name=\"UseSNMPGroup\" id=\"useSNMPGroup\" value=\"\" onchange=\"changeText2('useSNMPGroup')\"> &nbsp;&nbsp;&nbsp;";
print "$$lang_vars{introduce_snmp_manual_message} <input type=\"radio\" value=\"1\" name=\"noUseSNMPGroup\" id=\"noUseSNMPGroup\" value=\"\" onchange=\"changeText2('noUseSNMPGroup')\" checked>";
}


$gip->prepare_snmp_version_form("$client_id","$vars_file","$snmp_group_name_db",\@snmp_groups, $red, $BM, $red_num, $ip_version);

$gip->print_end("$client_id","$vars_file","", "$daten");
