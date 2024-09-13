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
use DBI;
use lib './modules';
use GestioIP;
use GipTemplate;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $first_client_id = $gip->get_first_client_id();

$gip->{print_sitebar} = 1;


# Parameter check
my $client_id = $daten{'client_id'} || $gip->get_default_client_id("$first_client_id");

my $lang = $daten{'lang'} || "";
my $entries_per_page=$daten{'entries_per_page'} || "500";
$entries_per_page=500 if $entries_per_page !~ /^\d{1,4}$/;

my ($lang_vars,$vars_file);
($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("$entries_per_page","$lang");

# check Permissions
my @global_config = $gip->get_global_config("1");
my $user_management_enabled=$global_config[0]->[13] || "";
my $locs_ro_perm = "";
my $locs_rw_perm = "";

if ( $user_management_enabled eq "yes" ) {

#    $client_id = $gip->get_allowed_client_perm("$client_id","$vars_file") || $client_id;

	my $required_perms="read_net_perm";
    my $dummy_val;
    ($locs_ro_perm, $locs_rw_perm, $dummy_val, $client_id) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
        return_client_id=>"1",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
) || "";


print <<EOF;
Content-type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
EOF

$gip->print_error("$client_id","$error_message") if $error_message;


my ($show_rootnet, $show_endnet, $hide_not_rooted, $local_filter_enabled);
$show_rootnet=$show_endnet=$hide_not_rooted=$local_filter_enabled="";
if ( defined($daten{show_rootnet}) ) {
	$show_rootnet= $daten{show_rootnet} ? 1 : 0;
#	$gip->set_show_rootnet_val("1");
} elsif (( defined($daten{filter_button}) || defined($daten{pages_links_red_button})) && ! defined($daten{show_rootnet}) ) {
	$show_rootnet="0";
#	$gip->set_show_rootnet_val("0");
} else {
	$show_rootnet=$gip->get_show_rootnet_val();
}

if ( defined($daten{show_endnet}) ) {
	$show_endnet=$daten{show_endnet} ? 1 : 0;
#	$gip->set_show_endnet_val("1");
} elsif (( defined($daten{filter_button}) || defined($daten{pages_links_red_button})) && ! defined($daten{show_endnet}) ) {
	$show_endnet="0";
#	$gip->set_show_endnet_val("0");
} else {
	$show_endnet=$gip->get_show_endnet_val();
}

if ( defined($daten{hide_not_rooted}) ) {
	$hide_not_rooted=$daten{hide_not_rooted} ? 1 : 0;
#	$gip->set_hide_not_rooted_val("1");
} elsif (( defined($daten{filter_button}) || defined($daten{pages_links_red_button})) && ! defined($daten{hide_not_rooted}) ) {
	$hide_not_rooted="0";
#	$gip->set_hide_not_rooted_val("0");
} else {
#	$hide_not_rooted=$gip->get_hide_not_rooted_val();
}

my $local_filter=$global_config[0]->[16] || 0;
$local_filter=0 if $local_filter eq "no";
if ( $local_filter ) {
	if ( defined($daten{local_filter_enabled}) ) {
		$local_filter_enabled=$daten{local_filter_enabled} ? 1 : 0;
#		$gip->set_local_filter_enabled_val("1");
	} elsif (( defined($daten{filter_button}) || defined($daten{pages_links_red_button})) && ! defined($daten{local_filter_enabled}) ) {
		$local_filter_enabled=0;
#		$gip->set_local_filter_enabled_val("0");
	} else {
		$local_filter_enabled=$gip->get_local_filter_enabled_val() || 0;
	}
}
$local_filter_enabled=0 if ! $local_filter_enabled;
$gip->{local_filter} = $local_filter || 0;

my $ipv4_only_mode=$global_config[0]->[5] || "yes";
my $ip_version_ele="";
if ( $ipv4_only_mode eq "no" ) {
	$ip_version_ele = $daten{'ip_version_ele'} || "";
	if ( $ip_version_ele ) {
#		$ip_version_ele = $gip->set_ip_version_ele("$ip_version_ele");
	} else {
		$ip_version_ele = $gip->get_ip_version_ele();
	}
} else {
	$ip_version_ele = "v4";
}

my $parent_network_id = $daten{parent_network_id} || "";

if ( $parent_network_id ) {
    my @values_red = $gip->get_red("$client_id","$parent_network_id");
    my $rootnet_ip = $values_red[0]->[0];
    my $rootnet_BM = $values_red[0]->[1];
    my $net_values=$gip->get_first_network_address("$client_id","$rootnet_ip","$rootnet_BM","$ip_version_ele");
    my $rootnet_first_ip_int=$net_values->{first_ip_int};
    my $rootnet_last_ip_int=$net_values->{last_ip_int};


    $gip->{rootnet_first_ip} = $rootnet_ip;
    $gip->{rootnet_BM} = $rootnet_first_ip_int;
    $gip->{rootnet_first_ip_int} = $rootnet_first_ip_int;
    $gip->{rootnet_last_ip_int} = $rootnet_last_ip_int;
}

#$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_dispo_message}","$vars_file");


my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();

my $tipo_ele = $daten{'tipo_ele'} || "NULL";
my $loc_ele = $daten{'loc_ele'} || "NULL";
my $start_entry=$daten{'start_entry'} || '0';
my $order_by=$daten{'order_by'} || 'red_auf';
my $first_call = $daten{'first_call'} || "no";
$first_call="no" if $first_call ne "yes";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if $start_entry !~ /^\d{1,5}$/;

my $show_fav=$daten{'show_fav'} || "";

my $tipo_ele_id=$gip->get_cat_net_id("$client_id","$tipo_ele") || "-1";
my $loc_ele_id=$gip->get_loc_id("$client_id","$loc_ele") || "-1";

my @ip;
if ( $show_fav ) {
	@ip=$gip->get_redes_fav("$client_id","$start_entry","$entries_per_page","$order_by","$ip_version_ele");
} elsif ( $parent_network_id ) {
	@ip=$gip->get_redes("$client_id","$tipo_ele_id","$loc_ele_id","$start_entry","$entries_per_page","$order_by","$ip_version_ele","$show_rootnet","$show_endnet","$hide_not_rooted","$show_fav","$local_filter_enabled","$local_filter","$parent_network_id");
} else {
	@ip=$gip->get_redes("$client_id","$tipo_ele_id","$loc_ele_id","$start_entry","$entries_per_page","$order_by","$ip_version_ele","$show_rootnet","$show_endnet","$hide_not_rooted","$show_fav","$local_filter_enabled","$local_filter");
}

my $anz_values_redes = scalar(@ip);
my $ip=$gip->prepare_redes_array("$client_id",\@ip,"$order_by","$start_entry","$entries_per_page","$ip_version_ele");

my $pages_links=$gip->get_pages_links_red("$client_id","$vars_file","$start_entry","$anz_values_redes","$entries_per_page","$tipo_ele","$loc_ele","$order_by","","","$show_rootnet","$show_endnet","$hide_not_rooted","","$parent_network_id");

$pages_links = "" if $pages_links eq "NO_LINKS";
print <<EOF;
    <script type="text/javascript">
        create_pages_links_net('$pages_links');
    </script>
EOF

if ( $ip[0] ) {
	$gip->PrintRedTab("$client_id",$ip,"$vars_file","simple","$start_entry","$tipo_ele","$loc_ele","$order_by","","$entries_per_page","$ip_version_ele","$show_rootnet","$show_endnet","","","$hide_not_rooted");
} else {
	if ( $ip_version_ele eq "v4" ) {
        my $rootnet_chain = "";
        if ( $gip->{rootnet_first_ip_int} ) {
            $rootnet_chain = $gip->get_rootnet_chain("$client_id", "$ip_version_ele");
        }

print <<EOF;
    <script type="text/javascript">
        create_rootnet_chain('$rootnet_chain');
    </script>
EOF

		print "<p class=\"NotifyText\">$$lang_vars{no_networks_message}</p><br>\n";
	} else {
		print "<p class=\"NotifyText\">$$lang_vars{no_ipv6_networks_message}</p><br>\n";
	}

	if ( $first_call eq "yes" ) {
		print "<p><br><b>$$lang_vars{first_call1_message}</b><br><p><br>\n";
		print "$$lang_vars{import_sheet_message}<br>\n";
		print "<form name=\"import_red_spread\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_import_spreadsheet_form.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{import_networks_from_spreadsheet_message}\" name=\"B1\"></form><br><p><br>\n";
		print "$$lang_vars{start_initialization_message}<br>\n";
		print "<form name=\"initialize\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_initialize_form.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{discover_message}\" name=\"B1\"></form><br><p><br>\n";
		print "$$lang_vars{start_network_snmp_discovery_message}<br>\n";
		print "<form name=\"import_snmp\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_import_snmp_form.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{import_networks_from_snmp_message}\" name=\"B1\"></form><br><p><br>\n";
		print "$$lang_vars{add_net_manually_message}<br>\n";
		print "<form name=\"insertred\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insertred_form.cgi\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{nuevo_message}\" name=\"B1\"></form><br>\n";
	}
}

#$gip->print_end("$client_id","$vars_file","go_to_top","$daten");
