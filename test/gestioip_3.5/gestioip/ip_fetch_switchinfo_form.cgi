#!/usr/bin/perl -T -w

# Copyright (C) 2013 Marc Uebel

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
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
my $lang = $daten{'lang'} || "";
$lang="" if $lang !~ /^\w{1,3}$/;
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $ip_version=$daten{'ip_version'} || "";
my $ip = $daten{'ip'}  || "";
my $red_num = $daten{'red_num'} || "";

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	ip_version=>"$ip_version",
	ip=>"$ip",
	red_num=>"$red_num",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{live_data_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{live_data_message}","$vars_file");

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
$gip->print_error("$client_id","$$lang_vars{snmp_info_not_found_message} (3)") if $module_check != "1";

$module = "Net::DNS";
$module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{net_dns_not_found_message} (4)") if $module_check != "1";




my $ip_int = $gip->ip_to_int("$client_id","$ip","$ip_version");
my $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_int") || "";

my $snmp_group_name_host = $gip->get_custom_host_column_entry_from_name("$client_id", "$host_id", "SNMPGroup") || "";
my $snmp_group_name_net = $gip->get_custom_column_entry("$client_id","$red_num","SNMPGroup") || "";
my @snmp_groups=$gip->get_snmp_groups("$client_id");

my $confirmation = $gip->get_config_confirmation("$client_id") || "yes";
my $onclick = "";
if ( $confirmation eq "yes" ) {
        $onclick =  "onclick=\"return confirmation();\"";
}


print "<p><h3>$$lang_vars{hosts_message} ${ip}</h3>\n";
print "<p>\n";
print "<form name=\"snmp_version\"  method=\"POST\" action=\"$server_proto://$base_uri/ip_fetch_switchinfo.cgi\">\n";


if ( $snmp_groups[0] ) {

print "$$lang_vars{use_snmp_group_message} <input type=\"radio\" value=\"1\" name=\"UseSNMPGroup\" id=\"useSNMPGroup\" value=\"\" onchange=\"changeText2('useSNMPGroup')\" checked> &nbsp;&nbsp;&nbsp;";
print "$$lang_vars{introduce_snmp_manual_message} <input type=\"radio\" value=\"1\" name=\"noUseSNMPGroup\" id=\"noUseSNMPGroup\" value=\"\" onchange=\"changeText2('noUseSNMPGroup')\">";
} else {
print "$$lang_vars{use_snmp_group_message} <input type=\"radio\" value=\"1\" name=\"UseSNMPGroup\" id=\"useSNMPGroup\" value=\"\" onchange=\"changeText2('useSNMPGroup')\"> &nbsp;&nbsp;&nbsp;";
print "$$lang_vars{introduce_snmp_manual_message} <input type=\"radio\" value=\"1\" name=\"noUseSNMPGroup\" id=\"noUseSNMPGroup\" value=\"\" onchange=\"changeText2('noUseSNMPGroup')\" checked>";
}


$gip->prepare_snmp_version_form("$client_id", "$vars_file", "$snmp_group_name_net", \@snmp_groups, "", "", $red_num, $ip_version, $ip, $snmp_group_name_host);


$gip->print_end("$client_id","$vars_file","", "$daten");
