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


my $gip = GestioIP -> new();

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
my $lang = "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my %daten=();

my $query = new CGI;
my $client_id = $query->param("client_id") || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
	$client_id = 1;
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}


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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{import_acl_con_message}","$vars_file");

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

my $upload_filehandle = $query->upload("csv_file");
if ( $upload_dir =~ /^(\/.*)$/ ) {
        $upload_dir =~ /^(\/.*)$/;
        $upload_dir = $1;
}

#permit tcp 123.23.55.0 0.0.0.255 eq 960 host 15.44.136.
#permit icmp 123.23.55.0 0.0.0.255 host 22.44.136.41
#permit icmp 123.23.55.0 0.0.0.255 eq 123 host 22.44.136.41
#permit tcp 123.23.55.0 0.0.0.255 host 22.44.152.61 eq 135
#permit udp any any range 16000 16511
#permit tcp 123.23.55.0 0.0.0.255 range 1111 2222 host 22.44.152.61 range 4444 5555
#permit tcp host 7.88.234.13 eq 25 host 52.2.5.40                
#permit udp 192.11.22.0/26 192.11.22.73/32 eq 464

my ( $action, $protocol, $src, $src_wmask, $src_port, $src_operator, $dst, $dst_wmask, $dst_port, $dst_operator, $icmp_type);

print "<p><b>$$lang_vars{'importing_acls_message'}</b><br><p>\n";
while ( <$upload_filehandle> ) {
    $action=$protocol=$src=$src_wmask=$src_port=$src_operator=$dst=$dst_wmask=$dst_port=$dst_operator=$icmp_type="";
    

    if ( $_ =~ /^!/ ) {
        # ignore comments
        next;
    }
    if ( $_ =~ /ACL-nr/ ) {
        # check if this is a ACL Connection file...
        $gip->print_error("$client_id","$$lang_vars{con_no_acl_message}");
    }
    if ( $_ !~ /^\s?(permit|deny)/ ) {
        # ignore all lines which do not start with "permit" or "deny"
        next;
    }

#    $_ =~ /^(\w+\s)(\w+\s)(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?/;
    $_ =~ s/[ \r\t]+/ /g;
    $_ =~ /^\s?(\w+\s)(\w+\s)(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?(.+?\s)?/;

#	print "TEST: $1 - $2 - $3 - $4 - $5 - $6 - $7 - $8 - $9 - $10 - $11 - $12<br>\n";

	my ( $f1, $f2, $f3, $f4, $f5, $f6, $f7, $f8, $f9, $f10, $f11, $f12);
	$f1 = $1 || "";
	$f2 = $2 || "";
	$f3 = $3 || "";
	$f4 = $4 || "";
	$f5 = $5 || "";
	$f6 = $6 || "";
	$f7 = $7 || "";
	$f8 = $8 || "";
	$f9 = $9 || "";
	$f10 = $10 || "";
	$f11 = $11 || "";
	$f12 = $12 || "";
	my $found = "";

    my @acl_parts_new;
	my @acl_parts = ("$f1", "$f2", "$f3", "$f4", "$f5", "$f6", "$f7", "$f8", "$f9", "$f10", "$f11", "$f12");
    foreach (@acl_parts) {
        $_ = $gip->remove_whitespace_se("$_");
        push @acl_parts_new, $_;
    }
    @acl_parts = @acl_parts_new;

	$action = shift @acl_parts || "";
	$protocol = shift @acl_parts || "";

    # SRC ADDR
	$found = shift @acl_parts || "";
	if ( $found eq "host" ) {
		$src_wmask = "0.0.0.0";
		$src = shift @acl_parts || "";
	} elsif ( $found eq "any" ) {
		$src = $found;
    } elsif ( $found =~ /\// ) {
		$found =~ /^(.+)\/(\d+)$/;
		$src = $1;
		my $bm = $2;
		$src_wmask = $gip->get_wmask_from_bm("$bm");
	} else {
		$src = $found;
		$src_wmask = shift @acl_parts || "";
	}

    $src=$gip->remove_whitespace_se("$src");
    next if $src !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ && $src ne "any";
    next if $src_wmask && $src_wmask !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;

    # SRC PORT
	$found = shift @acl_parts || "";
	if ( $found eq "range" ) {
		my $sport = shift @acl_parts || "";
		my $eport = shift @acl_parts || "";
		$src_port = $found . " " . $sport . " " . $eport;
     	$found = shift @acl_parts || "";
	} elsif ( $found =~ /^(eq|le|ge)$/ ) {
		$src_operator = $found;
		$src_port = shift @acl_parts || "";
     	$found = shift @acl_parts || "";
	}

    # DST ADDR
	if ( $found eq "host" ) {
		$dst_wmask = "0.0.0.0";
		$dst = shift @acl_parts || "";
	} elsif ( $found eq "any" ) {
		$dst = $found;
    } elsif ( $found =~ /\// ) {
		$found =~ /^(.+)\/(\d+)$/;
		$dst = $1;
		my $bm = $2;
		$dst_wmask = $gip->get_wmask_from_bm("$bm");
	} else {
		$dst = $found;
		$dst_wmask = shift @acl_parts || "";
	}

    $dst=$gip->remove_whitespace_se("$dst");
    next if $dst !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ && $dst ne "any";
    next if $dst_wmask && $dst_wmask !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
    
    # DST PORT
	$found = shift @acl_parts || "";
	if ( $found eq "range" ) {
		my $sport = shift @acl_parts || "";
		my $eport = shift @acl_parts || "";
		$dst_port =  $found . " " .$sport . " " . $eport;
	} elsif ( $found =~ /^(eq|le|ge)$/ ) {
		$dst_operator = $found;
		$dst_port = shift @acl_parts || "";
	} elsif ( $protocol eq "icmp" ) {
        $icmp_type = $found;
    }

    my $check_value = $gip->insert_acl("$client_id","$action", "$protocol", "$src", "$src_wmask", "$src_port", "$src_operator", "$dst", "$dst_wmask", "$dst_port", "$dst_operator", "$icmp_type");

    if ( ! $check_value ) {
        print "ADDED: $action $protocol $src $src_wmask $src_operator $src_port $dst $dst_wmask $dst_operator $dst_port $icmp_type<br>\n";
    } else {
        print "IGNORED (already exists): $action $protocol $src $src_wmask $src_operator $src_port $dst $dst_wmask $dst_operator $dst_port $icmp_type<br>\n";
    }
}

print "<p><b>$$lang_vars{'done_message'}</b><p><br>\n";
print "<form name=\"show_acl_connection1\" method=\"POST\" action=\"$server_proto://$base_uri/ip_show_acl_list.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{show_acls_message}\" name=\"B2\"></form><br>\n";

my $audit_type="141";
my $audit_class="26";
my $update_type_audit="1";
my $event="";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


$gip->print_end("$client_id", "", "", "");
