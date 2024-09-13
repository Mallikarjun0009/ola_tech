#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm,create_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


my $acl_nr = $daten{'acl_nr'} || "";
my $id = $daten{'id'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{acl_connection_deleted_message}","$vars_file");

my @acl_connections=$gip->get_acl_connections("$client_id","$id");
my %protocols = $gip->get_protocol_hash("$client_id");

my @acl_connections_prepared;
my @acls_prepared;

my $purpose = $acl_connections[0]->[2] || "";
my $status = $acl_connections[0]->[3];
my $src_vlan = $acl_connections[0]->[4];
my $source = $acl_connections[0]->[5] || "";
my $src = $acl_connections[0]->[6] || "";
my $application_protocol = $acl_connections[0]->[7] || "";
my $proto_id = $acl_connections[0]->[8] || "";
my $protocol = "IP";
$protocol = $protocols{$proto_id} || "" if $proto_id;
my $src_port = $acl_connections[0]->[9] || "";
my $bidirectional = $acl_connections[0]->[10] || "";
my $dst_vlan = $acl_connections[0]->[11] || "";
my $destination = $acl_connections[0]->[12] || "";
my $dst = $acl_connections[0]->[13] || "";
my $encrypted_base_proto = $acl_connections[0]->[14] || "";
my $remark = $acl_connections[0]->[15] || "";


$gip->delete_acl_connection("$client_id","$id");


my $audit_type="146";
my $audit_class="27";
my $update_type_audit="1";
my $event="$acl_nr, $purpose, $status, $src_vlan, $source, $src, $application_protocol, $protocol, $src_port, $bidirectional, $dst_vlan, $destination, $dst, $encrypted_base_proto, $remark";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @acls=$gip->get_acl_connections("$client_id");
if ( $acls[0] ) {
        $gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","", "$daten");

