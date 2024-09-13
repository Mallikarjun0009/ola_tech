#!/usr/bin/perl -T -w

# Copyright (C) 2018 Marc Uebel

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
use Text::CSV;

my $gip = GestioIP -> new();

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
my $lang = "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my %daten=();

my $query = new CGI;
my $client_id = $query->param("client_id") || $gip->get_first_client_id();

$gip->debug("CLIENT ID: $query->param(client_id)");
if ( $client_id !~ /^\d{1,4}$/ ) {
	$client_id = 1;
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

my $report = $query->param("report") || "";

## check Permissions
my @global_config = $gip->get_global_config("$client_id");
#my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_net_perm,create_net_perm,update_net_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{import_acl_acl_con_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my $ipv4_only_mode=$global_config[0]->[5] || "yes";

my $import_dir = getcwd;
$import_dir =~ s/res.*/import/;


$CGI::POST_MAX = 1024 * 5000;
my $safe_filename_characters = "a-zA-Z0-9_.-";
my $upload_dir = getcwd;
$upload_dir =~ s/res.*/import/;


my $filename = $query->param("csv_file");

$gip->print_error("$client_id","$$lang_vars{no_excel_name_message}") if ( !$filename );

my ( $name, $path, $extension ) = fileparse ( $filename, '\..*' );
$filename = $name . $extension;
$filename =~ tr/ /_/;
$filename =~ s/[^$safe_filename_characters]//g;

if ( $filename =~ /^([$safe_filename_characters]+)$/ ) {
	$filename = $1;
} else {
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

#$gip->print_error("$client_id","$$lang_vars{no_xls_extension_message}") if $filename !~ /\.xls$/;

my $upload_filehandle = $query->upload("csv_file");
if ( $upload_dir =~ /^(\/.*)$/ ) {
        $upload_dir =~ /^(\/.*)$/;
        $upload_dir = $1;
}


my ( $acl_nr, $purpose, $status, $src_vlan, $source, $application_protocol, $bidirectional, $dst_vlan, $destination, $encrypted_base_proto, $remark );
my ( $action, $protocol, $proto_id, $src, $src_wmask, $src_port, $src_operator, $dst, $dst_wmask, $dst_port, $dst_operator, $icmp_type);
my ( $src_mask, $dst_mask );

my %protocols = $gip->get_protocol_name_hash("$client_id");

my $csv = Text::CSV->new({ sep_char => ',' });

print "<p><b>$$lang_vars{'importing_connections_message'}</b><p></p>\n";
my $i = 0;
while ( <$upload_filehandle> ) {
    my $line = $_;
    $gip->debug("PROCESSING: $line");

    if ( $_ =~ /^(permit|deny|!!!!!!)/ && ( $i == 1 || $i == 2 )) {
        $gip->print_error("$client_id","$$lang_vars{acl_no_con_message}");
    }
    $i++;

	next if $line =~ /^(ACL-nr|ID)/i;
	next if $line =~ /^#/;
	next if $line =~ /^$/;


    $action=$protocol=$src=$src_wmask=$src_port=$src_operator=$dst=$dst_wmask=$dst_port=$dst_operator=$icmp_type=$src_mask=$dst_mask="";

	if ($csv->parse($line)) {

		my @connections = $csv->fields();

		$acl_nr = $connections[0] || 0;
        next if $line =~ /^\d+$/;
		$purpose = $connections[1] || "";
		$status = $connections[2] || "";
		$src_vlan = $connections[3] || "";
		$source = $connections[4] || "";
		$src = $connections[5] || "";
        $src =~ s/,/\./g;
        my $src_check = $src;
        if ( $src =~ /\//g ) {
            $src =~ /^(.+)\//;
            $src_check = $1;
        }
        my $ip_check = $gip->check_valid_ipv4("$src_check") || 0;
        if ( $ip_check != 1 ) {
            $gip->debug("DEBUG: CAN NOT PARSE LINE: $line - WRONG Src IP: $src\n");
            print "CAN NOT PARSE LINE - IGNORED: $line - WRONG Src IP: $src<br>\n";
            next;
        }
        $src=$gip->remove_whitespace_se("$src");
		$application_protocol = $connections[6] || "";
        $protocol = $connections[7] || "";
        if ( $protocol =~ /^\d+$/ ) {
            $proto_id = $protocol;
        } else {
            $protocol = uc $protocol;
            $proto_id = $protocols{$protocol} || "";
        }
        if ( $protocol && $proto_id !~ /^\d+$/ ) {
            $gip->debug("DEBUG: CAN NOT PARSE LINE: $line - UNKNOWN PROTOCOL: \"$proto_id\"\n");
            print "CAN NOT PARSE LINE - IGNORED: $line - UNKNOWN PROTOCOL: \"$proto_id\"<br>\n";
            next;
        }
		$src_port = $connections[8] || "";
		$bidirectional = $connections[9] || "";
        $bidirectional = "X" if $bidirectional;
		$dst_vlan = $connections[10] || "";
		$destination = $connections[11] || "";
		$dst = $connections[12] || "";
        $dst =~ s/,/\./g;
        my $dst_check = $dst;
        if ( $dst =~ /\//g ) {
            $dst =~ /^(.+)\//;
            $dst_check = $1;
        }
        $ip_check = $gip->check_valid_ipv4("$dst_check") || 0;
        if ( $ip_check != 1 ) {
            $gip->debug("DEBUG: CAN NOT PARSE LINE: $line - WRONG Dst IP: $dst\n");
            print "CAN NOT PARSE LINE - IGNORED: $line - WRONG Dst IP: $dst<br>\n";
            next;
        }
        $dst=$gip->remove_whitespace_se("$dst");
		$encrypted_base_proto = $connections[13] || "";
		$remark = $connections[14] || "";
        $remark =~ s/^(.{1,1024})/$1/ if $remark;

        my ($report_result, $check_value) = $gip->insert_connection("$client_id","$acl_nr", "$purpose", "$status", "$src_vlan", "$source", "$src", "$application_protocol", "$proto_id", "$src_port", "$bidirectional", "$dst_vlan", "$destination", "$dst", "$encrypted_base_proto", "$remark","$report");

        $gip->debug("RETURN: $report_result - $check_value");
        $check_value = $acl_nr if ! $check_value;
        if ( $report_result eq "INSERT" ) {
            $gip->debug("IMPORTING: $line\n");
            print "IMPORTING: $line<br>\n";
        } elsif ( $report_result eq "NEW_CONNECTION" ) {
            $gip->debug("NEW - IGNORED: $line\n");
            print "NEW (NO UPDATE): $line<br>\n";
        } elsif ( $report_result eq "SAME_FOUND" ) {
            $gip->debug("EXISTS - IGNORED: $line\n");
            print "EXISTS: $line<br>\n";
        } elsif ( $report_result eq "UPDATE" ) {
            $gip->debug("UPDATED: $line<br>\n");
            print "UPDATED ($check_value): $line<br>\n";
        } elsif ( $report_result eq "REPORT_CHANGE" ) {
            $gip->debug("CHANGED: $line<br>\n");
            print "CHANGED (NO UPDATE): $line<br>\n";
        } else {
            $gip->debug("NO RETURN: $line<br>\n");
            print "NO RETURN: $line - IGNORED<br>\n";
        }
	} else {
		# can not parse line....
        $gip->debug("DEBUG: CAN NOT PARSE LINE: $line\n");
        print "CAN NOT PARSE LINE - IGNORED: $line<br>\n";
	}
}

print "<p></p><b>$$lang_vars{'done_message'}</b><p><br>\n";
print "<form name=\"show_acl_connection1\" method=\"POST\" action=\"$server_proto://$base_uri/ip_show_acl_connection_list.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{show_acl_connection_message}\" name=\"B2\"></form><br>\n";

my $audit_type="143";
my $audit_class="27";
my $update_type_audit="1";
my $event="";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->print_end("$client_id", "", "", "");
