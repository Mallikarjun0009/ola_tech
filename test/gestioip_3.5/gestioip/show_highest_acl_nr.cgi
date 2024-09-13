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
use Net::IP;
use Net::IP qw(:PROC);
use POSIX qw(ceil);
use Math::BigInt;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $base_uri = $gip->get_base_uri();
my ($lang_vars,$vars_file)=$gip->get_lang();
my $server_proto=$gip->get_server_proto();

my $client_id = $daten{'client_id'} || 1;


#if ( $ENV{'QUERY_STRING'} ) {
#	my $QUERY_STRING = $ENV{'QUERY_STRING'};
#	$QUERY_STRING =~ /ip=(.*)&BM=(.*)&ip_version=(.*)$/;
#	$red=$1; 
#	$BM=$2;
#	$ip_version=$3 if $3;
#	if ( $ip_version eq "v6" ) {
#		$selected_index = $BM - 8 if $ip_version eq "v6";
#}

my @ids = $gip->get_acl_connection_numbers("$client_id");


print <<EOF;
Content-type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<HTML>
<head><title>Gesti&oacute;IP subnet calculator</title>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta http-equiv="Author" content="Marc Uebel">
<meta http-equiv="Pragma" content="no-cache">
<link rel="stylesheet" type="text/css" href="./stylesheet.css">
<link rel="stylesheet" href="./css/bootstrap/bootstrap.min.css">
<script src="http://localhost/gestioip/js/bootstrap/bootstrap.min.js"></script>
<link rel="shortcut icon" href="/favicon.ico">
</head>

<body>
EOF
#<div id="TopBoxCalc">
#<table border="0" width="00%"><tr height="50px" valign="middle"><td>
#  <span class="TopTextGestio">Gesti&oacute;IP</span></td>
#  <td><span class="TopText">$$lang_vars{show_highest_acl_number_message}</span></td><tr>
#</td></table>
#</div>
#<p>


my $old_id;
my $last_id = 0;
my %last_ids = (
    100000 => "",
    150000 => "",
    200000 => "",
    300000 => "",
    400000 => "",
    500000 => "",
    600000 => "",
    700000 => "",
    800000 => "",
    900000 => "",
);

foreach my $val ( @ids ) {
    my $id = $val->[0];
    if ( $id < 150000 ) {
        $last_ids{100000} = $id;
    } elsif ( $id < 200000 ) {
        $last_ids{150000} = $id;
    } elsif ( $id < 300000 ) {
        $last_ids{200000} = $id;
    } elsif ( $id < 400000 ) {
        $last_ids{300000} = $id;
    } elsif ( $id < 500000 ) {
        $last_ids{400000} = $id;
    } elsif ( $id < 600000 ) {
        $last_ids{500000} = $id;
    } elsif ( $id < 700000 ) {
        $last_ids{600000} = $id;
    } elsif ( $id < 800000 ) {
        $last_ids{700000} = $id;
    } elsif ( $id < 900000 ) {
        $last_ids{800000} = $id;
    } elsif ( $id < 1000000 ) {
        $last_ids{900000} = $id;
    }
}

print "<p></p>\n";
print "<h5 class='pb-2 pl-2'>Highest ACL Connection Numbers</h5>\n";
print "<p></p>\n";
print "<table class='table table-striped' width='20%'>\n";
print "<tr><td>Block <b>100xxx</b>: " . $last_ids{100000} . "</td></tr>\n";
print "<tr><td>Block <b>150xxx</b>: " . $last_ids{150000} . "</td></tr>\n";
print "<tr><td>Block <b>200xxx</b>: " . $last_ids{200000} . "</td></tr>\n";
print "<tr><td>Block <b>300xxx</b>: " . $last_ids{300000} . "</td></tr>\n";
print "<tr><td>Block <b>400xxx</b>: " . $last_ids{400000} . "</td></tr>\n";
print "<tr><td>Block <b>500xxx</b>: " . $last_ids{500000} . "</td></tr>\n";
print "<tr><td>Block <b>600xxx</b>: " . $last_ids{600000} . "</td></tr>\n";
print "<tr><td>Block <b>700xxx</b>: " . $last_ids{700000} . "</td></tr>\n";
print "<tr><td>Block <b>800xxx</b>: " . $last_ids{800000} . "</td></tr>\n";
print "<tr><td>Block <b>900xxx</b>: " . $last_ids{900000} . "</td></tr>\n";


print "</div>\n";
print "</div>\n";
print "</body>\n";
print "</html>\n";
exit 0;

