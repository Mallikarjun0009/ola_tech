#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
# strip # sign from the color
$daten =~ s/color=%23/color=/;
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_gestioip_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $name = $daten{'name'} || "";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{add_ldap_server_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_ldap_server_message}","$vars_file");


my $ldap_server = $daten{'ldap_server'} || "";
my $enabled = $daten{'enabled'} || "0";
my $type = $daten{'type'} || "";
my $protocol = $daten{'protocol'} || "";
my $port = $daten{'port'} || "";
my $bind_dn = $daten{'bind_dn'} || "";
my $password = $daten{'password'} || "";
my $base_dn = $daten{'base_dn'} || "";
my $user_attribute = $daten{'user_attribute'} || "";
my $filter = $daten{'filter'} || "";
my $comment = $daten{'comment'} || "";

$bind_dn = $gip->remove_whitespace_se("$bind_dn");
$base_dn = $gip->remove_whitespace_se("$base_dn");
$user_attribute = $gip->remove_whitespace_se("$user_attribute");
$filter = $gip->remove_whitespace_se("$filter");


$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;

my @objects = $gip->get_ldap_server("$client_id");
foreach my $obj( @objects ) {
    if ( $name eq $obj->[1] ) {
        $gip->print_error("$client_id","<b>$name</b>: $$lang_vars{name_exists_message}");
    } elsif ( $enabled && $obj->[12] eq 1 ) {
        $gip->print_error("$client_id","$$lang_vars{only_one_active_server_message}<p><br>$$lang_vars{disable_server_error_message}:<p><b>$obj->[1]</b>");
    }
}


$gip->print_error("$client_id","$$lang_vars{insert_ldap_server_message}") if ! $ldap_server;
$gip->print_error("$client_id","$$lang_vars{select_type_message}") if ! $type;
$gip->print_error("$client_id","$$lang_vars{select_protocol_message}") if ! $protocol;
$gip->print_error("$client_id","$$lang_vars{select_port_message}") if ! $port;
$gip->print_error("$client_id","$$lang_vars{insert_bind_dn_message}") if ! $bind_dn;
$gip->print_error("$client_id","$$lang_vars{insert_base_dn_message}") if ! $base_dn;
$gip->print_error("$client_id","$$lang_vars{insert_user_attrib_message}") if ! $user_attribute;
$gip->print_error("$client_id","$$lang_vars{select_port_message}") if ! $port;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $enabled !~ /^\d$/;

my $error = "";
if ( $enabled ) {
    $error = $gip->update_ldap_apache_configuration(
        client_id => "$client_id",
        ldap_server => "$ldap_server",
        protocol => "$protocol",
        ldap_port => "$port",
        bind_dn => "$bind_dn",
        password => "$password",
        base_dn => "$base_dn",
        user_attribute => "$user_attribute",
        filter => "$filter",
    ) || "";

    if ( $error =~ /context/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_ldap_server_not_created_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } else {
        $gip->print_error("$client_id","Update Apache LDAP configuration failed (2): $error") if $error;
	}

}

my $exit_status_apache = $gip->{exit_status_apache} || 0;

my $last_id;
if ( $exit_status_apache == 0 ) {
# Insert Object
    $last_id = $gip->insert_ldap_server(
        client_id => "$client_id",
        name => "$name",
        ldap_server => "$ldap_server",
        type => "$type",
        protocol => "$protocol",
        ldap_port => "$port",
        bind_dn => "$bind_dn",
        password => "$password",
        base_dn => "$base_dn",
        user_attribute => "$user_attribute",
        filter => "$filter",
        enabled => "$enabled",
        comment => "$comment",
    ) || "";

} else {
    my $div_notify_message = "$$lang_vars{apache_not_reloaded_message}";
    my $div_notify = GipTemplate::create_div_notify_text(
        noti => $div_notify_message,
    );
    print "$div_notify\n";
}


print <<EOF;
<script>
update_nav_text("$$lang_vars{ldap_server_added_message}")
</script>
EOF

my $audit_type="180";
my $audit_class="35";
my $update_type_audit="1";
my $event="$name,$comment";
$event =~ s/,$//;

$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");



my %changed_id;
$changed_id{$last_id}=$last_id;

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

$gip->PrintGenericTab("$client_id", "$vars_file", \%changed_id ,\@column_names, \%column_positions, $mod_form, $delete_form);

$gip->print_end("$client_id","$vars_file","", "$daten");
