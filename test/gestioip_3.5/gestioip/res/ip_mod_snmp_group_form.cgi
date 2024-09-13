#!/usr/bin/perl -w -T

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
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
my $id = $daten{'id'} || "";


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_snmp_group_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
		id=>"$id",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_snmp_group_message}","$vars_file");


my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @snmp_groups=$gip->get_snmp_groups("$client_id");
my @snmp_group=$gip->get_snmp_groups("$client_id","$id");
my $name = $snmp_group[0][1];
my $snmp_version = $snmp_group[0][2];
my $port = $snmp_group[0][3] || "";
my $community = $snmp_group[0][4] || "";
my $user_name = $snmp_group[0][5] || "";
my $sec_level = $snmp_group[0][6] || "";
my $auth_proto = $snmp_group[0][7] || "";
my $auth_pass = $snmp_group[0][8] || "";
my $priv_proto = $snmp_group[0][9] || "";
my $priv_pass = $snmp_group[0][10] || "";
my $comment = $snmp_group[0][11] || "";

$gip->prepare_snmp_version_form("$client_id","$vars_file", "", \@snmp_groups, "", "", "", "", "", "", "1");


print "<p>\n";
print "<form name=\"snmp_form\" autocomplete=\"off\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_snmp_group.cgi\"><br>\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";


print <<EOF;
<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" type=\"text\" class='form-control form-control-sm' value=\"$name\"  size=\"15\" maxlength=\"50\"></td></tr>
<tr><td $align1><br></td></tr>
<tr><td $align>$$lang_vars{snmp_version_message}</td>
<td colspan="3" $align1><select name="snmp_version" class="custom-select custom-select-sm" style='width: 5em;' id="snmp_version" onchange="changeText1(this.value);">
EOF

my $selected;
my @option_values = ("1","2","3");
foreach my $opt ( @option_values ) {
    $selected = "";
    $selected = "selected" if $opt eq $snmp_version;
    my $opt_show = $opt;
    $opt_show .= "c" if $opt == 2;
    print "<option value=\"$opt\" $selected>v${opt_show}</option>\n";
}

print <<EOF;
</select>
</td></tr>
<tr><td $align>
EOF

if ( $snmp_version =~ /^[12]$/ ) {

print <<EOF;
<span id="Hide1" $align1>$$lang_vars{snmp_community_message}</span>
</td><td colspan="3" $align1><input type="password" class='form-control form-control-sm'  size="10" name="community" value="$community" maxlength="55"> <span id="Hide12" $align1>$$lang_vars{snmp_default_public_message}</span></td></tr>
<tr><td $align>
<span id="Hide2" $align1></span>
</td><td colspan=\"3\" $align1>
<span id="Hide3" $align1></span>
</select>
</td></tr>
<tr><td $align></td><td $align1><span id="Hide4"></span></td><td $align1><span id="Hide5"></span></td><td></td></tr>
<tr><td $align></td><td $align1>
<span id="Hide6"></span>
</select>
</td><td $align1><span id="Hide7"></span></td><td></tr>
<tr><td $align></td><td $align1><span id="Hide8"></span></td><td $align1><span id="Hide9"></span></td><td></td></tr>
<tr><td $align></td><td $align1>
<span id="Hide10"></span>
</td><td $align1><span id="Hide11"></span></td><td></tr>
<tr><td $align>$$lang_vars{port_message}</td><td><input type=\"text\" class='form-control form-control-sm' size=\"5\" name=\"port\" value=\"161\" maxlength=\"5\" value=\"161\"></td></tr>
<tr><td colespan="4" $align1></td></tr>
<tr><td $align1><br></td></tr>
EOF


} else {


print <<EOF;
<span id="Hide1" $align1>$$lang_vars{snmp_username_message}</span>
</td><td colspan="3" $align1><input type="text" class='form-control form-control-sm' size="10" name="community" value="$user_name" maxlength="55"> <span id="Hide12" $align1></span></td></tr>
<tr><td $align>
<span id="Hide2" $align1>$$lang_vars{security_level_message}</span>
</td><td colspan=\"3\" $align1>
<span id="Hide3" $align1>
<select name="sec_level" id="sec_level" class="custom-select custom-select-sm">
EOF

@option_values = ("noAuthNoPriv","authNoPriv","authPriv");
foreach my $opt ( @option_values ) {
    $selected = "";
    $selected = "selected" if $opt eq $sec_level;
    print "<option value=\"$opt\" $selected>${opt}</option>\n";
}

print <<EOF;
</span>
</select>
</td></tr>
<tr><td $align></td><td $align1><span id="Hide4">$$lang_vars{auth_proto_message}</span></td><td $align1><span id="Hide5">$$lang_vars{auth_pass_message}</span></td><td></td></tr>
<tr><td $align></td><td $align1>
<span id="Hide6">
<select name="auth_proto" id="auth_proto" class="custom-select custom-select-sm">
EOF

@option_values = ("","MD5","SHA");
foreach my $opt ( @option_values ) {
    $selected = "";
    $selected = "selected" if $opt eq $auth_proto;
    print "<option value=\"$opt\" $selected>${opt}</option>\n";
}

print <<EOF;
</span>
</select>
</td><td $align1><span id="Hide7"><input type="password" class='form-control form-control-sm' size="15" name="auth_pass" id="auth_pass" value="$auth_pass" maxlength="100"></span></td><td></tr>
<tr><td $align></td><td $align1><span id="Hide8">$$lang_vars{priv_proto_message}</span></td><td $align1><span id="Hide9">$$lang_vars{priv_pass_message}</span></td><td></td></tr>
<tr><td $align></td><td $align1>
<span id="Hide10">
<select name="priv_proto" id="priv_proto" class="custom-select custom-select-sm">
EOF

@option_values = ("","DES","3DES","AES");
foreach my $opt ( @option_values ) {
    $selected = "";
    $selected = "selected" if $opt eq $priv_proto;
    print "<option value=\"$opt\" $selected>${opt}</option>\n";
}

print <<EOF;
</select>
</span>
</td><td $align1><span id="Hide11"><input type="password" class='form-control form-control-sm' size="15" name="priv_pass" id="priv_pass" value="$priv_pass" maxlength="100"></span></td><td></tr>
<tr><td $align>$$lang_vars{port_message}</td><td><input type=\"text\" class='form-control form-control-sm' size=\"5\" name=\"port\" value=\"$port\" maxlength=\"5\" value=\"161\"></td></tr>
<tr><td colespan="4" $align1></td></tr>
<tr><td $align1><br></td></tr>
EOF


}


print <<EOF;
<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" type=\"text\" class='form-control form-control-sm' value=\"$comment\" size=\"15\" maxlength=\"500\"></td></tr>
</form>
</table>
EOF

print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"submit\" value=\"$$lang_vars{cambiar_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";

print "<script type=\"text/javascript\">\n";
print "document.forms.snmp_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
