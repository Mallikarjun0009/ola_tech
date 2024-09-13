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


use DBI;
use strict;
use lib './modules';
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();

# Parameter check
my $lang = $daten{'lang'} || "";
$lang="" if $lang !~ /^\w{1,3}$/;
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_vlan_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $mode = $daten{'mode'} || "show";
my $vlan_id = $daten{'vlan_id'} || "";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        mode=>"$mode",
        vlan_id=>"$vlan_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{vlans_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

if ( $mode eq "asso_vlans" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{asso_vlans_message}","$vars_file");
} else {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{vlans_message}","$vars_file");
}

$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $mode !~ /^show|unir|asso_vlans$/; 

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my @vlans;
if ( $mode eq "asso_vlans" ) {
	@vlans=$gip->get_asso_vlans("$client_id","$vlan_id");
} else {
	@vlans=$gip->get_vlans("$client_id");
}

print "<p>";
if ( $vlans[0] ) {
	$gip->PrintVLANTab("$client_id",\@vlans,"show_ip.cgi","detalles","$vars_file","$mode");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

print "<span style=\"float: $ori\"><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"$$lang_vars{atras_message}\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM></span>\n" if $mode eq "asso_vlans";

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

