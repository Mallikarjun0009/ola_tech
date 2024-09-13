#!/usr/bin/perl -w -T

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
my $id = $daten{'id'} || "";
my $name = $daten{'name'} || "";

my %values_users=$gip->get_user_hash("$client_id");

my $group_name=$values_users{$id}[5] || "";
my $phone=$values_users{$id}[2] || "";
my $email=$values_users{$id}[3] || "";
my $comment=$values_users{$id}[4] || "";
my $type=$values_users{$id}[6] || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
        name=>"$name",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{delete_user_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_user_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $id;

my $new_apache_config = $gip->check_new_apache_config() || 0;

my $error;
if ( $new_apache_config ) {
    $error = $gip->delete_ldap_user_apache_configuration("$client_id","$name") || 0;
    if ( $error =~ /context/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_prevent_job_creation_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } elsif ( $error ) {
        $gip->print_error("$client_id","Update Apache LDAP configuration failed (2): $error") if $error;
    }
}

my $exit_status_apache = $gip->{exit_status_apache} || 0;

if ( $exit_status_apache == 0 ) {
	$error = $gip->delete_user("$client_id","$vars_file","$id","$type","$name") || "";
	$gip->print_error("$client_id","$$lang_vars{user_not_deleted_message}:<br>$error") if $error;
} else {
    my $div_notify_message = "$$lang_vars{apache_not_reloaded_message}";
    my $div_notify = GipTemplate::create_div_notify_text(
        noti => $div_notify_message,
    );
    print "$div_notify\n";
}



my $audit_type="118";
my $audit_class="21";
my $update_type_audit="1";
my $event="$name,$type,$group_name,$phone,$email,$comment";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

my $div_notify = GipTemplate::create_div_notify_text(
    noti => "$name: $$lang_vars{user_deleted_message}",
);
print "$div_notify\n";

$gip->PrintUserTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

