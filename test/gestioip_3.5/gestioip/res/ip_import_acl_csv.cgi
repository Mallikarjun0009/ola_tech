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
use Cwd;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
	$client_id = 1;
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{import_from_sheet_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_net_perm,create_net_perm,update_net_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


my @config = $gip->get_config("$client_id");
my $confirmation = $config[0]->[7] || "no";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{import_acl_acl_con_message}","$vars_file");

print <<EOF;

<script type="text/javascript">
<!--

function show_radio(TYPE){
    if ( TYPE == "connections" ) {
        document.getElementById('HideRadios').innerHTML = '<p></p>$$lang_vars{existing_entries_message}:<br> $$lang_vars{report_only_message}<input type="radio" class="m-2" name="report" id="report" value="report_only" checked>&nbsp;&nbsp;&nbsp;&nbsp;$$lang_vars{update_and_report_message}<input type="radio" class="m-2" name="report" id="report" value="update"><p></p>';
    } else {
        document.getElementById('HideRadios').innerHTML = '';
    }
}


function check_import_type(TYPE) {

       if ( TYPE == 'acl' ) {
            document.send_csv.action = "$server_proto://$base_uri/res/ip_import_acl_csv1.cgi";
       } else if ( TYPE == 'connections' ) {
            document.send_csv.action = "$server_proto://$base_uri/res/ip_import_connections_csv1.cgi";
       }
}
-->
</script>
EOF

my $align="align=\"left\"";

my $import_dir = getcwd;
$import_dir =~ s/res.*/import/;

print <<EOF;
<p><br><p>
<form id="send_csv" name="send_csv" action="$server_proto://$base_uri/res/ip_import_acl_csv1.cgi" method="post" enctype="multipart/form-data">
<table border="0"><tr><td $align>
$$lang_vars{acl_list_message}<input type="radio" class='m-2' name="import_type" value="acl" onchange="show_radio('acl'); check_import_type('acl');" checked>&nbsp;&nbsp;&nbsp;&nbsp;$$lang_vars{connection_message}<input type="radio" class='m-2' name="import_type" value="connections" onchange="show_radio('connections'); check_import_type('connections');"> 
<font color=\"white\">x</font>
</td></tr>
<tr><td $align>
</td></tr>
<tr><td $align>
<span id="HideRadios">
</span>
</td></tr>
<tr><td $align>
<p><input type="hidden" name="client_id" value="$client_id"><input type="file" name="csv_file" style="margin: 1em;"></p>
</td></tr>
<tr><td $align>
<input type="submit" name="Submit" value="$$lang_vars{upload_message}" class="btn">
</td></tr></table>
</form>
</span>
EOF

$gip->print_end("$client_id", "", "", "");
