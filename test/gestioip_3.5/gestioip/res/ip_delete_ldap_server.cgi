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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ldap_server_deleted_message}","$vars_file");

# Check if server has active groups assigned
my @ldap_groups_assigned = $gip->check_ldap_group_assigned("$client_id","$id");
if ( @ldap_groups_assigned ) {
	my $ldap_group_string;
	foreach ( @ldap_groups_assigned ) {
		my $ldap_group_name = $_->[1];
		$ldap_group_string .= "<br>$ldap_group_name";
	}
	$gip->print_error("$client_id","$$lang_vars{ldap_server_has_active_groups_assigend}:<p> $ldap_group_string <p>$$lang_vars{disable_ldap_groups_first_message}");
}

my %values = $gip->get_ldap_server_hash("$client_id", "id", "$id");
my $enabled = $values{$id}[11] || 0;

if ( $enabled ) {
    my $error = $gip->reset_ldap_apache_configuration("$client_id") || 0;
	if ( $error =~ /context/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_ldap_server_not_deleted_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } elsif ( $error ) {
        $gip->print_error("$client_id","Update Apache LDAP configuration failed (1): $error") if $error;
	}
}

$gip->delete_ldap_server("$client_id","$id");

my $audit_type="182";
my $audit_class="35";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @column_names = ("$$lang_vars{name_message}","$$lang_vars{server_message}","$$lang_vars{enabled_message}","$$lang_vars{tipo_message}","$$lang_vars{protocol_message}","$$lang_vars{port_message}","$$lang_vars{bind_identity_message}","$$lang_vars{base_dn_message}","$$lang_vars{username_attribute_message}","$$lang_vars{ldap_filter_message}","$$lang_vars{comentario_message}");


my %column_positions = (
    $$lang_vars{name_message} => 0,
    $$lang_vars{server_message} => 1,
    $$lang_vars{tipo_message} => 2,
    $$lang_vars{protocol_message} => 3,
    $$lang_vars{port_message} => 4,
    $$lang_vars{bind_identity_message} => 5,
    $$lang_vars{base_dn_message} => 7,
    $$lang_vars{username_attribute_message} => 8,
    $$lang_vars{ldap_filter_message} => 9,
    $$lang_vars{comentario_message} => 10,
    $$lang_vars{enabled_message} => 11,
);


my $mod_form = "ip_mod_ldap_server_form.cgi";
my $delete_form = "ip_delete_ldap_server.cgi";

$gip->PrintGenericTab("$client_id", "$vars_file", "", \@column_names, \%column_positions, $mod_form, $delete_form);
#$gip->PrintGenericTab("$client_id", "$vars_file", \%changed_id ,\@column_names, \%column_positions, $mod_form, $delete_form);


$gip->print_end("$client_id","$vars_file","", "$daten");

