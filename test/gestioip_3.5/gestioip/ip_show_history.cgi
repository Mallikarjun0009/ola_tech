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
use DBI;
use POSIX qw(strftime);
use POSIX;
use lib './modules';
use GestioIP;
use Net::IP qw(:PROC);

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $server_proto=$gip->get_server_proto();
my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_audit_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check

my $ip_version = $daten{'ip_version'} || '';
my $ip=$daten{'ip'} || '';
my $entries_per_page=$daten{'entries_per_page'} || '100';
my $start_entry=$daten{'start_entry'} || '0';
my $update_type_audit=$daten{'update_type_audit'} || "all";
my $ping_status_only=$daten{'ping_status_only'} || '';

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	ip_version=>"$ip_version",
	entries_per_page=>"$entries_per_page",
	start_entry=>"$start_entry",
	update_type_audit=>"$update_type_audit",
	ping_status_only=>"$ping_status_only",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{historia_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


### disabled 0; enabled 1;
my $enable_ping_history=1;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{historia_message} $ip","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if $ip_version !~ /^(v4|v6)$/;


my $datetime = time();
my $time_range_search = "a.date BETWEEN 1253243098 AND " . $datetime;

my @search;
$ip = ip_expand_address ($ip,6) if $ip_version eq "v6";
my $ip_search_expr;

my $network_history = 0;
if ( $ip =~ /\// ) {
    $network_history = 1;
}

if ( $ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\/(\d{1,3})$/ && $ip_version eq "v4" ) {
	$ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\/(\d{1,3})$/;
	my $o1 = $1;
	my $o2 = $2;
	my $o3 = $3;
	my $o4 = $4;
	my $bm = $5;

	$ip_search_expr = $o1 . '\.' . $o2 . '\.' .  $o3 . '\.' . $o4 . '/' . $bm;
} else {
	$ip_search_expr=$ip;
}

my $mysql_version = $gip->get_mysql_version();
my $ip_search = "";
if ( $mysql_version =~ /^8/ ) {
    $ip_search = 'REGEXP "\\\\b' . $ip_search_expr . '\\\\b"';
} else {
    $ip_search_expr =~ s/\./\\\\./g;
    $ip_search = "REGEXP \"^(mass update.+)*$ip_search_expr\[\[:>:\]\]\"";
}

$gip->debug("SEARCH: $ip_search");


my $ping_status_checked="";
$search[0]="search_string:X-X:$ip_search";
if ( $ping_status_only eq "yes" ) {
	$search[1]="event_type:X-X:ping status changed";
	$ping_status_checked="checked";
}
my @values_audit;

@values_audit=$gip->search_db_audit("$client_id","$time_range_search",\@search,$start_entry,$entries_per_page,$update_type_audit);
my $anz_values_audit = pop(@values_audit);

my $pages_links;
my $l = "0";
my $m = "0";
my $n = "1";
my $start_title;
my $cgi = "$ENV{SERVER_NAME}" . "$ENV{SCRIPT_NAME}";
if ( $anz_values_audit > $entries_per_page ) {
	while ( $l <= $anz_values_audit ) {
		$m = $l + $entries_per_page;
		$start_title = $l +1;
		if ( $n >= 100 ) {
 			$pages_links = $pages_links . "&nbsp;<span class=\"audit_page_link\" title=\"RESULT LIMITED TO $l ENTRIES\">$n</span>&nbsp;\n";
 			last;
 		}

		if ( $pages_links  && $l != $start_entry ) {
			$pages_links = $pages_links . "<form name=\"printredtabheadform\" method=\"POST\" action=\"$server_proto://$cgi\" style=\"display:inline\"><input type=\"submit\" value=\"$n\" name=\"B2\" class=\"audit_page_link\" title=\"$start_title-$m\"><input name=\"ip\" type=\"hidden\" value=\"$ip\"><input name=\"entries_per_page\" type=\"hidden\" value=\"$entries_per_page\"><input name=\"start_entry\" type=\"hidden\" value=\"$l\"><input name=\"update_type_audit\" type=\"hidden\" value=\"$update_type_audit\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"></form>";
		} elsif ( $pages_links  && $l == $start_entry ) {
			$pages_links = $pages_links . "&nbsp;<span class=\"audit_page_link_actual\" title=\"$start_title-$m\">$n</span>&nbsp;";
		} elsif ( ! $pages_links  && $l == $start_entry ) {
			$pages_links = "&nbsp;<span class=\"audit_page_link_actual\" title=\"$start_title-$m\">$n</span>&nbsp;";
		} elsif ( ! $pages_links  && $l != $start_entry ) {
			$pages_links = "<form name=\"printredtabheadform\" method=\"POST\" action=\"$server_proto://$cgi\" style=\"display:inline\"><input type=\"submit\" value=\"$n\" name=\"B2\" class=\"audit_page_link\" title=\"$start_title-$m\"><input name=\"ip\" type=\"hidden\" value=\"$ip\"><input name=\"entries_per_page\" type=\"hidden\" value=\"$entries_per_page\"><input name=\"start_entry\" type=\"hidden\" value=\"$l\"><input name=\"update_type_audit\" type=\"hidden\" value=\"$update_type_audit\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"></form>";
		}
		$l = $l + $entries_per_page;
		$n++;
	}
}
$pages_links = "&nbsp;" if ! $pages_links;


my @values_entries_per_page = ("10","50","100","250");
my @update_types_audit = $gip->get_audit_update_types("$client_id");

if ( $values_audit[0] ) {
	print "<p>\n";
	print "<form class name=\"printredtabheadform\" method=\"POST\" action=\"$server_proto://$cgi\"><input name=\"ip\" type=\"hidden\" value=\"$ip\">\n";
	print "<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"border-collapse:collapse\"><tr>\n";
	print "<td height=\"20px\">$$lang_vars{entradas_por_pagina_message} </td><td>";
	print "&nbsp;<select class=\"form-control form-control-sm display-inline\" name=\"entries_per_page\" size=\"1\">";
	my $i = "0";
	foreach (@values_entries_per_page) {
		if ( $_ eq $entries_per_page ) {
			print "<option selected>$values_entries_per_page[$i]</option>";
		} else {
			print "<option>$values_entries_per_page[$i]</option>";
		}
		$i++;
	}
	print "</select>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>\n";
#	print "<td>\n";
#	print "$$lang_vars{update_types_message}</td><td>\n";
#	print "&nbsp;<select name=\"update_type_audit\" size=\"1\">\n";
#	print "<option></option>\n";
#	$i = "0";
#	foreach (@update_types_audit) {
#		if ( $update_types_audit[$i]->[0] eq $update_type_audit ) {
#			print "<option selected>$update_types_audit[$i]->[0]</option>";
#			$i++;
#			next;
#		}
#		print "<option>$update_types_audit[$i]->[0]</option>";
#		$i++;
#	}
#	print "</select>&nbsp;</td>\n";

	if ( $enable_ping_history == 1 && ! $network_history ) {
		print "<td><span class=\"ml-3\">$$lang_vars{ping_events_only_message}</span><span class=\"pl-1\"><input type=\"checkbox\" name=\"ping_status_only\" value=\"yes\" $ping_status_checked></span></td>\n";
	}
	print "<td><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\">\n";
	print "<span class=\"pl-3\"><input type=\"submit\" value=\"\" title=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"filter_button\"></span></td></form>\n";
	print "</tr></table>\n";
	print "<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"border-collapse:collapse\"><tr><td>$pages_links</td></tr>\n";
	print "</table>\n";
	print "<br>\n" if $pages_links ne "&nbsp;";


	print "<table cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"border-collapse:collapse\" width=\"100%\"><tr><td><b>$$lang_vars{date_message}&nbsp;</b></td><td>&nbsp;<b>$$lang_vars{user_message}</b>&nbsp;</td><td>&nbsp;<b>$$lang_vars{event_type_message}</b>&nbsp;</td><td>&nbsp;<b>$$lang_vars{class_message}</b>&nbsp;</td><td>&nbsp;<b>$$lang_vars{event_message}</b>&nbsp;&nbsp;</td><td>&nbsp;<b>$$lang_vars{value_message}</b></td></tr>\n";

	my $color="white";
	my $k="0";
	foreach (@values_audit) {
		if ( $color eq "white" ) {
			$color = "#f2f2f2";
		} else {
			$color = "white";
		}
		my $event_value=$values_audit[$k]->[0];
		my $user=$values_audit[$k]->[1];
		my $date=scalar localtime ($values_audit[$k]->[2]);
		my $event_class=$values_audit[$k]->[3];
		my $event=$values_audit[$k]->[4];
		my $event_type=$values_audit[$k]->[5];
		print "<tr bgcolor=\"$color\"><td nowrap>$date&nbsp;</td><td nowrap>&nbsp;$user&nbsp;</td><td nowrap>&nbsp;$event_type&nbsp;</td><td nowrap>&nbsp;$event_class&nbsp;</td><td nowrap>&nbsp;$event&nbsp;&nbsp;</td><td>$event_value</td></tr>\n";
		$k++;
	}
	print "</table>\n";
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_entradas_historia}</p>\n";
}

print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"$$lang_vars{atras_message}\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>\n";

$gip->print_end("$client_id", "", "", "");
