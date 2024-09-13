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
	my $required_perms="manage_gestioip_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $id = $daten{'id'} || "";
my $name = $daten{'name'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ldap_group_deleted_message}","$vars_file");

my @values=$gip->get_table_array("$client_id","ldap_group","$id");
my $dn = $values[0][2];

my $error;
if ( $error =~ /context/ ) {
	$gip->print_error("$client_id","$error<p>$$lang_vars{selinux_ldap_group_not_deleted_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
} else {
	$error = $gip->delete_ldap_group_apache_configuration("$client_id","$dn");
}

$gip->print_error("$client_id","Error update ldap group Apache configuration (2): $error") if $error;

my $exit_status_apache = $gip->{exit_status_apache} || 0;

if ( $exit_status_apache == 0 ) {
	$gip->delete_object("$client_id","ldap_group","$id");

	my $audit_type="182";
	my $audit_class="35";
	my $update_type_audit="1";
	my $event="$name";

	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	my $div_notify_message = "$$lang_vars{borrar_ldap_group_done_message}: $name";
	my $div_notify = GipTemplate::create_div_notify_text(
		noti => $div_notify_message,
	);
	print "$div_notify\n";
} else {
    my $div_notify_message = "$$lang_vars{apache_not_reloaded_message}";
    my $div_notify = GipTemplate::create_div_notify_text(
        noti => $div_notify_message,
    );
    print "$div_notify\n";
}



my @column_names;
if ( $user_management_enabled eq "yes" ) {
#    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{user_group_message}","$$lang_vars{group_attrib_is_dn_message}","$$lang_vars{comentario_message}");
    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{user_group_message}","$$lang_vars{comentario_message}");
} else {
#    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{group_attrib_is_dn_message}","$$lang_vars{comentario_message}");
    @column_names = ("$$lang_vars{id_message}","$$lang_vars{name_message}","$$lang_vars{enabled_message}","$$lang_vars{dn_message}","$$lang_vars{ldap_server_message}","$$lang_vars{comentario_message}");
}


my %column_names_db = (
    $$lang_vars{id_message} => "id",
    $$lang_vars{name_message} => "name",
    $$lang_vars{dn_message} => "dn",
    $$lang_vars{ldap_server_message} => "ldap_server_id",
    $$lang_vars{user_group_message} => "user_group_id",
#    $$lang_vars{group_attrib_is_dn_message} => "group_attrib_is_dn",
    $$lang_vars{comentario_message} => "comment",
    $$lang_vars{enabled_message} => "enabled",
);

my %user_group_hash = $gip->get_user_group_hash("$client_id");
my %ldap_server_hash = $gip->get_ldap_server_hash("$client_id");
my %group_attrib_is_dn_tab;
#push @{$group_attrib_is_dn_tab{1}}, "DN";
#push @{$group_attrib_is_dn_tab{2}}, "$$lang_vars{group_attrib_is_dn_message}";

my %id_columns = (
    user_group_id => \%user_group_hash,
    ldap_server_id => \%ldap_server_hash,
#    group_attrib_is_dn => \%group_attrib_is_dn_tab,
);

my %symbol_columns = (
    $$lang_vars{enabled_message} => "x",
);

my $mod_form = "ip_mod_ldap_group_form.cgi";
my $delete_form = "ip_delete_ldap_group.cgi";
my $confirm_message = "$$lang_vars{delete_ldap_group_confirm_message}";


$gip->PrintGenericTab1("$client_id", "$vars_file", "" ,\@column_names, \%column_names_db, "$mod_form", "$delete_form", "$confirm_message", \%id_columns, sub { $gip->get_table_hash("$client_id","ldap_group", "id") }, \%symbol_columns);


$gip->print_end("$client_id","$vars_file","", "$daten");

