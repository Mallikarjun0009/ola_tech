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
my $base_uri=$gip->get_base_uri();
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


my $id = $daten{'id'} || "";
my $acl_nr = $daten{'acl_nr'} || 0;
my $purpose = $daten{'purpose'} || "";
my $status = $daten{'status'} || "";
my $src_vlan = $daten{'src_vlan'} || "";
my $source = $daten{'source'} || "";
my $src = $daten{'src'} || "";
my $application_protocol = $daten{'application_protocol'} || "";
my $protocol = $daten{'protocol'} || "";
my $src_port = $daten{'src_port'} || "";
my $bidirectional = $daten{'bidirectional'} || "";
my $dst_vlan = $daten{'dst_vlan'} || "";
my $destination = $daten{'destination'} || "";
my $dst = $daten{'dst'} || "";
my $encrypted_base_proto = $daten{'encrypted_base_proto'} || "";
my $remark = $daten{'remark'} || "";

$acl_nr = $gip->remove_whitespace_se("$acl_nr");
$src = $gip->remove_whitespace_se("$src");
$dst = $gip->remove_whitespace_se("$dst");

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mod_acl_connection_message}","$vars_file");

my @values = $gip->get_acl_connections("$client_id", "$id");
my @protocols = $gip->get_protocols("$client_id");

my $acl_nr_old = $values[0]->[1] || 0;
my $purpose_old = $values[0]->[2] || "";
my $status_old = $values[0]->[3];
my $src_vlan_old = $values[0]->[4];
my $source_old = $values[0]->[5] || "";
my $src_old = $values[0]->[6] || "";
my $application_protocol_old = $values[0]->[7] || "";
my $protocol_old = $values[0]->[8] || "";
my $src_port_old = $values[0]->[9] || "";
my $bidirectional_old = $values[0]->[10] || "";
my $dst_vlan_old = $values[0]->[11] || "";
my $destination_old = $values[0]->[12] || "";
my $dst_old = $values[0]->[13] || "";
my $encrypted_base_proto_old = $values[0]->[14] || "";
my $remark_old = $values[0]->[15] || "";


$gip->mod_connection("$client_id","$id","$acl_nr", "$purpose", "$status", "$src_vlan", "$source", "$src", "$application_protocol", "$protocol", "$src_port", "$bidirectional", "$dst_vlan", "$destination", "$dst", "$encrypted_base_proto", "$remark");


my $audit_type="145";
my $audit_class="27";
my $update_type_audit="1";
my $event="$acl_nr_old, $purpose_old, $status_old, $src_vlan_old, $source_old, $src_old, $application_protocol_old, $protocol_old, $src_port_old, $bidirectional_old, $dst_vlan_old, $destination_old, $dst_old, $encrypted_base_proto_old, $remark_old > $acl_nr, $purpose, $status, $src_vlan, $source, $src, $application_protocol, $protocol, $src_port, $bidirectional, $dst_vlan, $destination, $dst, $encrypted_base_proto, $remark";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @acls=$gip->get_acl_connections("$client_id");
if ( $acls[0] ) {
        $gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","", "$daten");

