#!/usr/bin/perl -T -w

# Copyright (C) 2019 Marc Uebel

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
use CGI;
use CGI qw/:standard/;
use CGI::Carp qw ( fatalsToBrowser );
use File::Basename;


my $gip = GestioIP -> new();

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang="";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my %daten=();

my $query = new CGI;
my $filename = $query->param("spreadsheet");

my $client_id = $query->param("client_id") || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
	$client_id = 1;
	gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_message}","$vars_file");
	gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="create_line_perm,read_line_perm,update_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{importar_host_sheet_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $module = "Spreadsheet::ParseExcel";
my $module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{no_spreadsheet_support}") if $module_check != "1";

my $import_dir = getcwd;
$import_dir =~ s/res.*/import/;

$CGI::POST_MAX = 1024 * 5000;
my $safe_filename_characters = "a-zA-Z0-9_.-";
my $upload_dir = getcwd;
$upload_dir =~ s/res.*/import/;

$gip->print_error("$client_id","$$lang_vars{no_excel_name_message}") if ! $filename;

my ( $name, $path, $extension ) = fileparse ( $filename, '\..*' );
$filename = $name . $extension;
$filename =~ tr/ /_/;
$filename =~ s/[^$safe_filename_characters]//g;

if ( $filename =~ /^([$safe_filename_characters]+)$/ ) {
        $filename = $1;
} else {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

$gip->print_error("$client_id","$$lang_vars{no_xls_extension_message}") if $filename !~ /\.xls$/;

my $upload_filehandle = $query->upload("spreadsheet");
if ( $upload_dir =~ /^(\/.*)$/ ) {
        $upload_dir =~ /^(\/.*)$/;
        $upload_dir = $1;
}

open ( UPLOADFILE, ">$upload_dir/$filename" ) or die "Can not open $upload_dir/$filename: $!";
binmode UPLOADFILE;

while ( <$upload_filehandle> ) {
        print UPLOADFILE;
}

close UPLOADFILE;

my @cc_values=$gip->get_custom_line_columns("$client_id");

print "<p>\n";
print "<span style=\"float: $ori\"><b>$$lang_vars{step_two_message}</b> <a href=\"$server_proto://$base_uri/help.html#import_spreadsheet\" target=\"_blank\" class=\"help_link_link\"><span class=\"help_link\">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span></a></span>\n";
print "<p><br><p><br>\n";
print "<span style=\"float: $ori\">\n";
print "$$lang_vars{sheet_step_two_message}<br>\n";
print "</span>";
print "<br><table border=\"0\" cellpadding=\"7\">\n";
print "<form  name=\"import_line_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_import_line_spreadsheet.cgi\">\n";
print "<tr><td $align>$$lang_vars{all_sheets_message}</td><td $align1> <input type=\"radio\" name=\"sheet_import_type\" value=\"all_sheet\" onclick=\"hoja.disabled=true;some_sheet_values.disabled=true\" checked></td></tr>\n";
print "<tr><td $align>$$lang_vars{sheet_name_message}</td><td $align1> <input type=\"radio\" name=\"sheet_import_type\" value=\"one_sheet\" onclick=\"hoja.disabled=false;some_sheet_values.disabled=true;some_sheet_values.value = ''\"</td><td> <input name=\"hoja\" type=\"text\" class='form-control form-control-sm' style='width: 12em' size=\"12\" maxlength=\"50\" disabled></td></tr>\n";
print "<tr><td $align>$$lang_vars{sheets_message}</td><td $align1> <input type=\"radio\" name=\"sheet_import_type\" value=\"some_sheet\" onclick=\"hoja.disabled=true;some_sheet_values.disabled=false;hoja.value = ''\"</td><td> <input name=\"some_sheet_values\" type=\"text\" class='form-control form-control-sm' style='width: 12em' size=\"12\" maxlength=\"30\" disabled> <img src=\"../imagenes/quick_help.png\" title=\"$$lang_vars{sheets_explic_message}\">\n";
print "</td></tr></table><p>\n";

print "<p><br><span style=\"float: $ori\">$$lang_vars{correpondig_colums_message}<br></span>\n";
print "<br><table border=\"0\" cellpadding=\"5\">\n";
print "<tr><td $align><b>$$lang_vars{columna_message}</b></td><td $align1><b>$$lang_vars{entradas_message}</b></td></tr>\n";
print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"line_provider\" size=\"1\">";
my @nums=("","A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z");
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{ll_client_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"type\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{tipo_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"service\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{service_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"description\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{description_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"phone_number\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{phone_number_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"ad_number\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{administrative_number_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"loc\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{loc_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"room\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{room_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"device\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{connected_device_message}</td></tr>\n";


print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"comment\" size=\"1\">";
foreach (@nums) {
	print "<option>$_</option>\n";
}
print "</select>\n";
print "</td><td>$$lang_vars{comentario_message}</td></tr>\n";

#print "<tr><td colspan=\"2\" $align1><br><i>$$lang_vars{columnas_opcionales_message}</i>\n";

print "</td></tr>\n";

#if ( scalar(@cc_values) > 0 ) {
#        print "<tr><td colspan=\"2\"><br><i>$$lang_vars{custom_column_message}</i></td></tr>\n";
#}

print "<tr><td colspan=\"2\"><br></td></tr>\n";
for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
	my $cc_name=$cc_values[$k]->[0];
	next if $cc_name eq "linkedIP";
	print "<tr><td $align><select class='custom-select custom-select-sm' style='width: 4em' name=\"$cc_name\" size=\"1\">";
	foreach (@nums) {
		print "<option>$_</option>\n";
	}
	print "</select>\n";
	print "</td><td $align1>\n";
	print "$cc_name</td></tr>";
}

print "<tr><td colspan=\"2\" $align1><br><input name=\"spreadsheet\" type=\"hidden\" value=\"$filename\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" value=\"$$lang_vars{importar_message}\" name=\"B1\" class=\"btn\"></td></tr>\n";
print "</form>\n";
print "</table>\n";

$gip->print_end("$client_id", "", "", "");
