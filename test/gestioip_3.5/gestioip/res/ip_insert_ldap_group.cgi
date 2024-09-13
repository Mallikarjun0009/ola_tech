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
my $name=$daten{'name'} || "";
my $dn=$daten{'dn'} || "";
my $ldap_server_id=$daten{'ldap_server'} || "";
my $user_group_id=$daten{'user_group'} || "";
my $group_attrib_is_dn=$daten{'group_attrib_is_dn'} || "DN";
my $comment = $daten{'comment'} || "";
my $enabled = $daten{'enabled'} || "0";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{add_ldap_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_ldap_group_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{name_no_whitespace_message}") if $name =~ /\s/;
$name=$gip->remove_whitespace_se("$name");
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if $enabled !~ /^\d$/;
$dn =~ s/\+/ /g;
$dn=$gip->remove_whitespace_se("$dn");

if ( $group_attrib_is_dn eq "DN" ) {
    $group_attrib_is_dn = 1;
} elsif ( $group_attrib_is_dn eq "$$lang_vars{username_message}" ) {
    $group_attrib_is_dn = 2;
} else {
    $gip->print_error("$client_id","$$lang_vars{formato_malo_messge}");
}

# Check if the object exists

my %ldap_group_hash = $gip->get_table_hash("$client_id","ldap_group", "name");
$gip->print_error("$client_id","<b>$name</b>: $$lang_vars{name_exists_message}") if $ldap_group_hash{$name};

my $error = "";
if ( $enabled ) {
    $error = $gip->insert_ldap_group_apache_configuration("$client_id","$dn") || "";
    if ( $error =~ /context/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_ldap_group_not_created_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } elsif ( $error ) {
        $gip->print_error("$client_id","$error");
	}
}

my $exit_status_apache = $gip->{exit_status_apache} || 0;

my $last_id;
if ( $exit_status_apache == 0 ) {
	# Insert Object
	$last_id = $gip->insert_LDAP_group(
		client_id => "$client_id",
		name => "$name",
		dn => "$dn",
		ldap_server_id => "$ldap_server_id",
		user_group_id => "$user_group_id",
		group_attrib_is_dn => "$group_attrib_is_dn",
		comment => "$comment",
		enabled => "$enabled",
	);
} else {
    my $div_notify_message = "$$lang_vars{apache_not_reloaded_message}";
    my $div_notify = GipTemplate::create_div_notify_text(
        noti => $div_notify_message,
    );
    print "$div_notify\n";
}


print <<EOF;
<script>
update_nav_text("$$lang_vars{ldap_group_added_message}")
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
my %group_attrib_is_dn;
#push @{$group_attrib_is_dn{1}}, "DN";
#push @{$group_attrib_is_dn{2}}, "$$lang_vars{group_attrib_is_dn_message}";

my %id_columns = (
    user_group_id => \%user_group_hash,
    ldap_server_id => \%ldap_server_hash,
#    group_attrib_is_dn => \%group_attrib_is_dn,
);

my %symbol_columns = (
    $$lang_vars{enabled_message} => "x",
);

my $mod_form = "ip_mod_ldap_group_form.cgi";
my $delete_form = "ip_delete_ldap_group.cgi";
my $confirm_message = "$$lang_vars{delete_ldap_group_confirm_message}";


$gip->PrintGenericTab1("$client_id", "$vars_file", \%changed_id, \@column_names, \%column_names_db, "$mod_form", "$delete_form", "$confirm_message", \%id_columns, sub { $gip->get_table_hash("$client_id","ldap_group", "id") }, \%symbol_columns);


$gip->print_end("$client_id","$vars_file","", "$daten");
