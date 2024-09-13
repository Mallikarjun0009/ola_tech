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
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_snmp_group_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $id = $daten{'id'} || "";
my $name = $daten{'name'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{smtp_server_deleted_message}","$vars_file");

my $cc_id_snmp_group = $gip->get_custom_column_id_from_name("$client_id", "SNMPGroup") || "";
my $snmp_group_exists_id = $gip->check_snmp_group_in_use("$client_id","$name","$cc_id_snmp_group","network") || "";
$gip->print_error("$client_id","$$lang_vars{'snmp_group_in_use_message'}") if $snmp_group_exists_id;

$gip->delete_smtp_server("$client_id","$id");

my $audit_type="179";
my $audit_class="34";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


$gip->PrintSMTPServerTab("$client_id","$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

