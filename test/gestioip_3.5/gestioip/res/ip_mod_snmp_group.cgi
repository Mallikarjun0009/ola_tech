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
my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_snmp_group_message}","$vars_file");


my $id=$daten{'id'} || "";
my $comment=$daten{'comment'} || "";
my $name=$daten{'name'} || "";
my $port=$daten{'port'} || "";
my $community=$daten{'community'} || "";
my $snmp_version=$daten{'snmp_version'} || "";
my $sec_level=$daten{'sec_level'} || "";
my $auth_algorithm=$daten{'auth_proto'} || "";
my $auth_password=$daten{'auth_pass'} || "";
my $priv_algorithm=$daten{'priv_proto'} || "";
my $priv_password=$daten{'priv_pass'} || "";

my $user_name = $community;

$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;
$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{introduce_community_string_message}") if ! $community;

my @snmp_groups=$gip->get_snmp_groups("$client_id");
my @snmp_group=$gip->get_snmp_groups("$client_id","$id");
my $name_db = $snmp_group[0][1];
my $snmp_version_db = $snmp_group[0][2];
my $comment_db = $snmp_group[0][11] || "";

foreach ( @snmp_groups ) {
    my $id_test = $_->[0];
    my $name_test = $_->[1];
    if ( $name eq $name_test && $id_test != $id ) {
        $gip->print_error("$client_id","$$lang_vars{snmp_group_exists_message}");
    }
}


##### snmp group in datenbank einstellen

$gip->mod_snmp_group(
    id=>"$id",
    client_id=>"$client_id",
    name=>"$name",
    comment=>"$comment",
    port=>"$port",
    snmp_version=>"$snmp_version",
    community=>"$community",
    user_name=>"$user_name",
    sec_level=>"$sec_level",
    auth_algorithm=>"$auth_algorithm",
    auth_password=>"$auth_password",
    priv_algorithm=>"$priv_algorithm",
    priv_password=>"$priv_password",
);

my $audit_type="165";
my $audit_class="30";
my $update_type_audit="1";
my $event1="$name_db,$snmp_version_db";
$event1=$event1 . "," .  $comment_db if $comment;
my $event2="$name_db,$snmp_version_db";
$event2=$event2 . "," .  $comment_db if $comment;
my $event = $event1 . "->" . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @values=$gip->get_snmp_groups("$client_id");
$gip->PrintSNMPGroupTab("$client_id",\@values,"$vars_file");


$gip->print_end("$client_id","$vars_file","", "$daten");

