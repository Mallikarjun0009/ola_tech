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

my ($purpose, $status, $src_vlan, $source, $src, $application_protocol, $protocol, $port, $bidirectional, $dst_vlan, $destination, $dst, $encrypted_base_proto, $remark); 
$purpose=$status=$src_vlan=$source=$src=$application_protocol=$protocol=$port=$bidirectional=$dst_vlan=$destination=$dst=$encrypted_base_proto=$remark="";

my $mass_update_type = $daten{'mass_update_type'} || "";
my $mass_update_acls = $daten{'mass_update_acls'} || "";
my $acl_nr = $daten{'acl_nr'} || 0;

if ( $mass_update_type =~ /purpose/i ) {
    $purpose = $daten{'purpose'} || "NO__VALUE";
}
if ( $mass_update_type =~ /status/i ) {
    $status = $daten{'status'} || "NO__VALUE";
}
if ( $mass_update_type =~ /Src VLAN/i ) {
    $src_vlan = $daten{'src_vlan'} || "NO__VALUE";
print STDERR "TEST SRC_VLAN FOUND; $src_vlan\n";
}
if ( $mass_update_type =~ /source/i ) {
    $source = $daten{'source'} || "NO__VALUE";
}
if ( $mass_update_type =~ /src ip/i ) {
    $src = $daten{'src'} || "NO__VALUE";
}
if ( $mass_update_type =~ /application protocol/i ) {
    $application_protocol = $daten{'application_protocol'} || "NO__VALUE";
}
if ( $mass_update_type =~ /protocol/i ) {
    $protocol = $daten{'protocol'} || "NO__VALUE";
}
if ( $mass_update_type =~ /port/i ) {
    $port = $daten{'port'} || "NO__VALUE";
}
if ( $mass_update_type =~ /bidirec/i ) {
    $bidirectional = $daten{'bidirectional'} || "NO__VALUE";
}
if ( $mass_update_type =~ /dst vlan/i ) {
    $dst_vlan = $daten{'dst_vlan'} || "NO__VALUE";
}
if ( $mass_update_type =~ /destination/i ) {
    $destination = $daten{'destination'} || "NO__VALUE";
}
if ( $mass_update_type =~ /dst ip/i ) {
    $dst = $daten{'dst'} || "NO__VALUE";
}
if ( $mass_update_type =~ /base proto/i ) {
    $encrypted_base_proto = $daten{'encrypted_base_proto'} || "NO__VALUE";
}
if ( $mass_update_type =~ /remark/i ) {
    $remark = $daten{'remark'} || "NO__VALUE";
}

$acl_nr = $gip->remove_whitespace_se("$acl_nr");
$src = $gip->remove_whitespace_se("$src");
$dst = $gip->remove_whitespace_se("$dst");

$mass_update_acls = $gip->remove_whitespace("$mass_update_acls");
my @mass_update_acls = split(",", $mass_update_acls);

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mod_acl_connection_message}","$vars_file");

$gip->print_error("$client_id","No Mass Update ACLs found") if ! $mass_update_acls;

my @protocols = $gip->get_protocols("$client_id");

$gip->mod_connection_mass_update("$client_id", "$mass_update_acls", "$purpose", "$status", "$src_vlan", "$source", "$src", "$application_protocol", "$protocol", "$port", "$bidirectional", "$dst_vlan", "$destination", "$dst", "$encrypted_base_proto", "$remark");


foreach my $id ( @mass_update_acls ) {
my $audit_type="145";
my $audit_class="27";
my $update_type_audit="1";
my $event="$acl_nr, $purpose, $status, $src_vlan, $source, $src, $application_protocol, $protocol, $port, $bidirectional, $dst_vlan, $destination, $dst, $encrypted_base_proto, $remark";
#my $event="$acl_nr_old, $purpose_old, $status_old, $src_vlan_old, $source_old, $src_old, $application_protocol_old, $protocol_old, $src_port_old, $bidirectional_old, $dst_vlan_old, $destination_old, $dst_old, $encrypted_base_proto_old, $remark_old > $acl_nr, $purpose, $status, $src_vlan, $source, $src, $application_protocol, $protocol, $src_port, $bidirectional, $dst_vlan, $destination, $dst, $encrypted_base_proto, $remark";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

}

my @acls=$gip->get_acl_connections("$client_id");
if ( $acls[0] ) {
        $gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","", "$daten");

