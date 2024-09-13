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

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");


# Parameter check
my $lang = $daten{'lang'} || "";
$lang="" if $lang !~ /^\w{1,3}$/;
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{about_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{about_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}


my $version=$gip->get_version();
my $anz_clients_all=$gip->count_clients("$client_id") || "0";
my $anz_red_all=$gip->count_red_entries_all("$client_id","NULL","NULL","all") || "0";
my $anz_host_all=$gip->count_all_host_entries("$client_id","all") || "0";
my $anz_vlans=$gip->count_all_vlan_entries("$client_id","all") || "0";
my $patch_version=$gip->get_patch_version();
my $sub_version=$gip->get_sub_version();

print "<p>";
print "<span class=\"AboutTextGestio\">$$lang_vars{gestioip_message}</span> <span class=\"AboutTextGestioVersion\">$$lang_vars{v_message}$version</span> ($$lang_vars{patch_version_message} $patch_version ($sub_version))<br>\n";
print "<span class=\"AboutTextGestioIPAM\">&nbsp;&nbsp;$$lang_vars{ip_address_management_message}</span><p>\n";
print "<p><br>$$lang_vars{copyright_message}";
print "<p><br><p><br><p>";


my @global_config = $gip->get_global_config("$client_id");

#my $cm_enabled_db=$global_config[0]->[8] || "no";
my $cm_enabled = $gip->check_cm_enabled() || "no";

my $cm_licence_key_check;

my $cm_conf_file = "/usr/share/gestioip/etc/cmm.conf";
my $cm_licence_key = "";

if ( -r $cm_conf_file ) {
	open(CM_CONF, "<$cm_conf_file");
	while (<CM_CONF>) {
		if ( $_ =~ /^cm_license_key/ ) {
			$_ =~ /^cm_license_key=(.*)$/;
			$cm_licence_key = $1 || "";
		}
	}
}

if ( $cm_licence_key ) {
	$cm_licence_key_check = $cm_licence_key;
} else {
	my $cm_licence_key_db=$global_config[0]->[10] || "";
	$cm_licence_key_check = $cm_licence_key_db;
}

my ($return_code,$cm_licence_key_message,$device_count)=$gip->check_cm_licence("$client_id","$vars_file","$cm_licence_key_check");
my $cm_licence_key_note="";
my $cm_dir_exists=0;
my $cm_dir = "./res/cm";
if ( -e $cm_dir ) {
        $cm_dir_exists=1;
}

if ( $cm_dir_exists == 0 ) {
	print "$$lang_vars{no_cm_module_message}<br>\n";
} elsif ( $return_code == 1 ) {
	# licence invalid
	$cm_licence_key_note="<font color=\"red\"><i>" . $cm_licence_key_message . "</i></font>";
} elsif ( $return_code == 2 ) {
	# licence expire warn
	$cm_licence_key_note="<font color=\"orange\"><i>" . $cm_licence_key_message . "</i></font>";
} elsif ( $return_code == 0 ) {
	# licence valid
	$cm_licence_key_note="<font color=\"green\"><i>" . $cm_licence_key_message . "</i></font>";
} elsif ( $return_code == 3 ) {
	# licence expired
	$cm_licence_key_note="<font color=\"red\"><i>" . $cm_licence_key_message . "</i></font>";
} elsif ( $return_code == 4 ) {
	# licence expired
	$cm_licence_key_note="<b>$cm_licence_key_message</b>\n";
}

$cm_licence_key_note=$$lang_vars{disabled_message} if $cm_enabled ne "yes";
my $devices_message="";
$devices_message="$device_count $$lang_vars{devices_message}," if $device_count;
print "<b>$$lang_vars{cm_licence_status_message}: $devices_message $cm_licence_key_note</b>\n" if $cm_dir_exists == 1;
print "<p><br><p><br><p>";


print "$$lang_vars{redes_total_messages}</td></tr>\n";
print "<table border=\"0\">";
if ( $anz_clients_all > 1 ) {
	print "<tr><td><span class=\"table_text_about\"><b>$anz_clients_all</b> $$lang_vars{clients_message}</span></td></tr>\n";
	print "<tr><td></b>$$lang_vars{con_message}</td></tr><tr>\n";
	if ( $anz_red_all == 1 ) {
		print "<tr><td><span class=\"table_text_about\"><b>$anz_red_all</b> $$lang_vars{network_message}</span></td></tr>\n";
	} else {
		print "<tr><td><span class=\"table_text_about\"><b>$anz_red_all</b> $$lang_vars{about_redes_dispo_message}</span></td></tr>\n";
	}
	print "<tr><td></b>$$lang_vars{y_message}</td></tr><tr>\n";
	print "<tr><td><span class=\"table_text_about\"><b>$anz_vlans</b> $$lang_vars{vlans_message}</span></td></tr>\n";
	print "<tr><td></b>$$lang_vars{y_message}</td></tr>\n";
	print "<tr><td><span class=\"table_text_about\"><b>$anz_host_all</b> $$lang_vars{entradas_host_message}</span></td></tr>";
	print "</table>\n";
} else {
	print "<br><p>";
	if ( $anz_red_all == 1 ) {
		print "<tr><td nowrap><span class=\"table_text_about\"><b>$anz_red_all</b> $$lang_vars{network_message}, <b>$anz_vlans</b> $$lang_vars{vlans_message} $$lang_vars{y_message} <b>$anz_host_all</b> $$lang_vars{entradas_host_message}</span></td></tr>\n";
	} else {
		print "<tr><td nowrap><span class=\"table_text_about\"><b>$anz_red_all</b> $$lang_vars{about_redes_dispo_message}, <b>$anz_vlans</b> $$lang_vars{vlans_message} $$lang_vars{y_message} <b>$anz_host_all</b> $$lang_vars{entradas_host_message}</span></td></tr>\n";
	}
	print "</table>\n";
	print "<p><br><p><br><p><br><p>";
}
print "<br><p><br>";
print "<p><br><p><br><p><br><p><br>";
print "$$lang_vars{visita_gestioip_message}\n";
print "<br><p><br>";

$gip->print_end("$client_id","$vars_file","", "$daten");
