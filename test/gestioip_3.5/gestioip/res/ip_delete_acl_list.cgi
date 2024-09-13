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
use lib '../modules';
use GestioIP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


my @global_config = $gip->get_global_config("$client_id");

my $anz_entries = $daten{'anz_entries'} || "";
my $k;
my $id_string = "";
if ( $anz_entries ) {
    for ($k=0;$k<=$anz_entries;$k++) {
        my $mu_id = "mass_update_acl_submit_${k}";
        my $id = $daten{$mu_id} || "";
        $id_string .= ", $id" if $id;
    }
    $id_string =~ s/^, //;
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{acl_list_message}","$vars_file");

$gip->delete_acls("$client_id","$id_string");

my @acls;
@acls=$gip->get_acls("$client_id");


print <<EOF;
<script language="JavaScript" type="text/javascript" charset="utf-8">
<!--
function show_searchform(){
document.getElementById('search_text').innerHTML='<input type=\"text\" size=\"15\" name=\"match\" > <input type="submit" value="" class="button" style=\"cursor:pointer;\"><br><p>';
document.search_ll.match.focus();
}
-->
</script>

<form name="search_dns_zone" method="POST" action="$server_proto://$base_uri/ip_search_acl.cgi" style="display:inline"><input type="hidden" name="client_id" value="$client_id">
EOF

print "<span style=\"float: right;\"><span id=\"search_text\"><img src=\"$server_proto://$base_uri/imagenes/lupe.png\" alt=\"search\" style=\"float: right; cursor:pointer;\" onclick=\"show_searchform('');\"></span></span><br>";
print "</form>\n";


if ( $acls[0] ) {
	$gip->PrintACLTab("$client_id",\@acls,"$vars_file");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}



$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

