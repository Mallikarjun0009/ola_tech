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


## check Permissions
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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_snmp_group_message}","$vars_file");


my $comment=$daten{'comment'} || "";
my $name=$daten{'name'} || "";
my $port=$daten{'port'} || "";
#my $community=$daten{'community_string'} || "";
my $community=$daten{'community'} || "";
my $snmp_version=$daten{'snmp_version'} || "";
my $sec_level=$daten{'sec_level'} || "";
my $auth_algorithm=$daten{'auth_proto'} || "";
my $auth_password=$daten{'auth_pass'} || "";
my $priv_algorithm=$daten{'priv_proto'} || "";
my $priv_password=$daten{'priv_pass'} || "";

my $user_name = $community;

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{introduce_community_string_message}") if ! $community;

#my @snmp_group=$gip->get_snmp_groups("$client_id","$id");
#my $name = $snmp_group[0][1];
#my $snmp_version = $snmp_group[0][2];
#my $port = $snmp_group[0][3] || "";
#my $community = $snmp_group[0][4] || "";
#my $user_name = $snmp_group[0][5] || "";
#my $sec_level = $snmp_group[0][6] || "";
#my $auth_proto = $snmp_group[0][7] || "";
#my $auth_pass = $snmp_group[0][8] || "";
#my $priv_proto = $snmp_group[0][9] || "";
#my $priv_pass = $snmp_group[0][10] || "";
#my $comment = $snmp_group[0][11] || "";

##### snmp group in datenbank einstellen

my $return = $gip->insert_snmp_group(
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

if ( $return ) {
	$gip->print_error("$client_id","$$lang_vars{snmp_group_exists_message}")
}


my $audit_type="163";
my $audit_class="30";
my $update_type_audit="1";
my $event="$name,$snmp_version";
$event=$event . "," .  $comment if $comment;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @values = $gip->get_snmp_groups("$client_id");
$gip->PrintSNMPGroupTab("$client_id",\@values,"$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

