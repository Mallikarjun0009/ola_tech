#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel


use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_user_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $name=$daten{'name'} || "";
my $description=$daten{'description'} || "";

my $manage_gestioip_perm=$daten{'manage_gestioip_perm'} || 0;
my $manage_user_perm=$daten{'manage_user_perm'} || 0;
my $manage_sites_and_cats_perm=$daten{'manage_sites_and_cats_perm'} || 0;
my $manage_custom_columns_perm=$daten{'manage_custom_columns_perm'} || 0;
my $read_audit_perm=$daten{'read_audit_perm'} || 0;
my $clients_perm=$daten{'clients_perm'} || 0;
my $loc_perm=$daten{'loc_perm'} || 0;
my $cat_perm=$daten{'cat_perm'} || 0;
my $create_net_perm=$daten{'create_net_perm'} || 0;
my $read_net_perm=$daten{'read_net_perm'} || 0;
my $update_net_perm=$daten{'update_net_perm'} || 0;
my $delete_net_perm=$daten{'delete_net_perm'} || 0;
my $create_host_perm=$daten{'create_host_perm'} || 0;
my $read_host_perm=$daten{'read_host_perm'} || 0;
my $update_host_perm=$daten{'update_host_perm'} || 0;
my $delete_host_perm=$daten{'delete_host_perm'} || 0;
my $create_vlan_perm=$daten{'create_vlan_perm'} || 0;
my $read_vlan_perm=$daten{'read_vlan_perm'} || 0;
my $update_vlan_perm=$daten{'update_vlan_perm'} || 0;
my $delete_vlan_perm=$daten{'delete_vlan_perm'} || 0;
my $read_device_config_perm=$daten{read_device_config_perm} || 0;
my $write_device_config_perm=$daten{write_device_config_perm} || 0;
my $administrate_cm_perm=$daten{administrate_cm_perm} || 0;
my $create_as_perm=$daten{create_as_perm} || 0;
my $read_as_perm=$daten{read_as_perm} || 0;
my $update_as_perm=$daten{update_as_perm} || 0;
my $delete_as_perm=$daten{delete_as_perm} || 0;
my $create_line_perm=$daten{create_line_perm} || 0;
my $read_line_perm=$daten{read_line_perm} || 0;
my $update_line_perm=$daten{update_line_perm} || 0;
my $delete_line_perm=$daten{delete_line_perm} || 0;
my $execute_update_dns_perm=$daten{execute_update_dns_perm} || 0;
my $execute_update_snmp_perm=$daten{execute_update_snmp_perm} || 0;
#my $execute_update_ping_perm=$daten{execute_update_ping_perm} || 0;
my $execute_update_ping_perm=1;
my $password_management_perm=$daten{password_management_perm} || 0;
my $manage_tags_perm=$daten{tags_perm} || 0;
my $manage_snmp_group_perm=$daten{manage_snmp_group_perm} || 0;
my $manage_dns_server_group_perm=$daten{manage_dns_server_group_perm} || 0;
my $manage_dyn_dns_perm=$daten{manage_dyn_dns_perm} || 0;
my $manage_macs_perm=$daten{manage_macs_perm} || 0;
my $locs_ro_perm=$daten{locs_ro_perm} || "9999";
my $locs_rw_perm=$daten{locs_rw_perm} || "9999";
my $manage_scheduled_jobs_perm=$daten{manage_scheduled_jobs_perm} || 0;
my $manage_smtp_server_perm=$daten{manage_smtp_server_perm} || 0;


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        description=>"$description",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{user_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_user_group_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_user_group_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{select_client_message}") if ! $clients_perm;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if $clients_perm !~ /^(\d|_)+$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2.2) $locs_ro_perm") if $locs_ro_perm !~ /^(\d|_)+$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2.3)") if $locs_rw_perm !~ /^(\d|_)+$/;

if ( ($manage_gestioip_perm |$manage_user_perm| $manage_sites_and_cats_perm| $manage_custom_columns_perm| $read_audit_perm| $create_net_perm | $read_net_perm| $update_net_perm | $delete_net_perm | $create_host_perm | $read_host_perm| $update_host_perm| $delete_host_perm| $create_vlan_perm | $read_vlan_perm| $update_vlan_perm| $delete_vlan_perm | $read_device_config_perm | $write_device_config_perm | $administrate_cm_perm |$create_as_perm|$read_as_perm|$update_as_perm|$delete_as_perm|$create_line_perm|$read_line_perm|$update_line_perm|$delete_line_perm |$execute_update_dns_perm|$execute_update_snmp_perm|$execute_update_ping_perm|$password_management_perm|$manage_tags_perm|$manage_snmp_group_perm|$manage_dns_server_group_perm|$manage_dyn_dns_perm|$manage_macs_perm|$manage_scheduled_jobs_perm) !~ /^(0|1)$/ ) {
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2.1)");
}

$name=$gip->remove_whitespace_se("$name");
$description=$gip->remove_whitespace_se("$description");

# Check if this user servername for this client exists

my %values_user_groups=$gip->get_user_group_hash("$client_id");

while ( my ($key, @value) = each(%values_user_groups) ) {
        $gip->print_error("$client_id","$$lang_vars{user_group_name_exists_message}") if $value[0]->[0] eq $name;
}


##### user group in datenbank einstellen

my $group_id=$gip->insert_user_group("$client_id","$name","$description");

$gip->insert_user_group_perms(
    client_id=>"$client_id",
    group_id=>"$group_id",
	manage_gestioip_perm=>"$manage_gestioip_perm", 
	manage_user_perm=>"$manage_user_perm", 
	manage_sites_and_cats_perm=>"$manage_sites_and_cats_perm", 
	manage_custom_columns_perm=>"$manage_custom_columns_perm", 
	read_audit_perm=>"$read_audit_perm", 
	clients_perm=>"$clients_perm", 
	loc_perm=>"$loc_perm", 
	cat_perm=>"$cat_perm", 
	create_net_perm=>"$create_net_perm", 
	read_net_perm=>"$read_net_perm", 
	update_net_perm=>"$update_net_perm", 
	delete_net_perm=>"$delete_net_perm", 
	create_host_perm=>"$create_host_perm", 
	read_host_perm=>"$read_host_perm", 
	update_host_perm=>"$update_host_perm", 
	delete_host_perm=>"$delete_host_perm", 
	create_vlan_perm=>"$create_vlan_perm", 
	read_vlan_perm=>"$read_vlan_perm", 
	update_vlan_perm=>"$update_vlan_perm", 
	delete_vlan_perm=>"$delete_vlan_perm", 
	read_device_config_perm=>"$read_device_config_perm",
	write_device_config_perm=>"$write_device_config_perm",
	administrate_cm_perm=>"$administrate_cm_perm",
	create_as_perm=>"$create_as_perm", 
	read_as_perm=>"$read_as_perm", 
	update_as_perm=>"$update_as_perm", 
	delete_as_perm=>"$delete_as_perm", 
	create_line_perm=>"$create_line_perm",
	read_line_perm=>"$read_line_perm",
	update_line_perm=>"$update_line_perm",
	delete_line_perm=>"$delete_line_perm",
	execute_update_dns_perm=>"$execute_update_dns_perm",
	execute_update_snmp_perm=>"$execute_update_snmp_perm",
	execute_update_ping_perm=>"$execute_update_ping_perm",
	password_management_perm=>"$password_management_perm",
	manage_tags_perm=>"$manage_tags_perm",
	manage_snmp_group_perm=>"$manage_snmp_group_perm",
	manage_dns_server_group_perm=>"$manage_dns_server_group_perm",
	manage_dyn_dns_perm=>"$manage_dyn_dns_perm",
	manage_macs_perm=>"$manage_macs_perm",
    locs_ro_perm=>"$locs_ro_perm",
    locs_rw_perm=>"$locs_ro_perm",
	manage_scheduled_jobs_perm=>"$manage_scheduled_jobs_perm",
	manage_smtp_server_perm=>"$manage_smtp_server_perm",

);

my $audit_type="119";
my $audit_class="21";
my $update_type_audit="1";
my $event="$name,$description";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintUserGroupTab("$client_id","$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

