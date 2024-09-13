#!/usr/bin/perl -T -w

# Copyright (C) 2014 Marc Uebel

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
use POSIX qw(strftime);
use lib './modules';
use GestioIP;
use Net::IP;
use Net::IP qw(:PROC);


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");


my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();
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


my $ip = $daten{'ip'} || "";

my $knownhosts="all";
my $start_entry_hosts="0";
my $entries_per_page_hosts="512";
my $pages_links="NO_LINKS";
my $host_order_by = "IP";
my $red_num = "";
my $red_loc = "";
my $redbroad_int = "1";
my $first_ip_int = "";
my $last_ip_int = "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{resultado_busqueda_message}","$vars_file");

my $valid_ip;
my $ip_version;
if ( $ip =~ /:/ ) {
    $valid_ip = $gip->check_valid_ipv6("$ip") || "0";
    $ip_version = "v6";
} else {
    $valid_ip = $gip->check_valid_ipv4("$ip") || "0";
    $ip_version = "v4";
}

$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $valid_ip;

my $ip_int = $gip->ip_to_int("$client_id","$ip","$ip_version");
$ip_int=Math::BigInt->new("$ip_int") if $ip_version eq "v6";


#my ($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%daten);
my $values = $gip->get_host_hash_between( "$client_id", "$ip_int", "$ip_int", "$ip_version" );
my $anz_values_hosts += keys %$values;


if ( $anz_values_hosts < "1" ) {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
	$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
}

print "<p><br>\n";
$gip->PrintIpTab("$client_id",$values,"$ip_int","$ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by","","","","","","","");

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

