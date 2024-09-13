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
my $type=$daten{'type'} || "";
my $group_id=$daten{'group_id'} || "";
my $phone=$daten{'phone'} || "";
my $email=$daten{'email'} || "";
my $comment=$daten{'comment'} || "";
my $login_pass=$daten{'login_pass'} || "";
my $retype_login_pass=$daten{'retype_login_pass'} || "";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        id=>"$group_id",
        email=>"$email",
        phone=>"$phone",
        comment=>"$comment",
) || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{new_user_message}","$vars_file");

my $new_apache_config = $gip->check_new_apache_config() || 0;

$gip->print_error("$client_id","$error_message") if $error_message;
$gip->print_error("$client_id","$$lang_vars{insert_user_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{name_message}: $$lang_vars{only_letters_and_numbers_message}") if $name !~ /^[A-Za-z0-9-_.@]+$/;;
$gip->print_error("$client_id","$$lang_vars{select_user_group_message}") if ! $group_id;
if ( $new_apache_config ) {
    $gip->print_error("$client_id","$$lang_vars{introduce_user_password_message}") if ! $login_pass && $type ne "LDAP";
    $gip->print_error("$client_id","$$lang_vars{password_not_match_message}") if $login_pass ne $retype_login_pass && $type ne "LDAP";
}

$name=$gip->remove_whitespace_se("$name");
$group_id=$gip->remove_whitespace_se("$group_id");
$phone=$gip->remove_whitespace_se("$phone");
$email=$gip->remove_whitespace_se("$email");
$comment=$gip->remove_whitespace_se("$comment");


# Check if the user exists

my %values_users=$gip->get_user_hash("$client_id");

while ( my ($key, @value) = each(%values_users) ) {
        $gip->print_error("$client_id","$$lang_vars{user_name_exists_message} (1)") if $value[0]->[0] eq $name;
}

if ( $new_apache_config && $type eq "LDAP" ) {
    my $error = $gip->insert_ldap_user_apache_configuration("$client_id","$name");
    if ( $error =~ /context/ ) {
        $gip->print_error("$client_id","$error<p>$$lang_vars{selinux_user_not_created_message}<p>$$lang_vars{selinux_prevents_command_execution_message}");
    } elsif ( $error ) {
        $gip->print_error("$client_id","Update Apache LDAP configuration failed (2): $error");
    }
}

my $exit_status_apache = $gip->{exit_status_apache} || 0;


##### user in datenbank einstellen
my $id = "";
if ( $exit_status_apache == 0 ) {
    my $return_message = $gip->insert_user("$client_id","$vars_file","$name","$group_id","$phone","$email","$comment","$type","$login_pass");
    if ( $return_message eq "USER_EXISTS" ) {
            $gip->print_error("$client_id","$$lang_vars{user_name_exists_message} (2)");
    } elsif ( $return_message =~ /^CREATE_USER/ ) {
            $gip->print_error("$client_id","$$lang_vars{user_not_created_message}:<br> $return_message");
    } elsif ( $return_message =~ /USER_GROUP/ ) {
            $gip->print_error("$client_id","$$lang_vars{user_not_added_to_group_message}:<br> $return_message");
    } elsif ( $return_message =~ /^\d+$/ ) {
        $id = $return_message;
    }
} else {
    my $div_notify_message = "$$lang_vars{apache_not_reloaded_message}";
    my $div_notify = GipTemplate::create_div_notify_text(
        noti => $div_notify_message,
    );
    print "$div_notify\n";
}


my $audit_type="116";
my $audit_class="21";
my $update_type_audit="1";
my $event="$name,$group_id,$phone,$email,$comment";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

print <<EOF;
<script>
update_nav_text("$$lang_vars{user_added_message}")
</script>
EOF


$gip->PrintUserTab("$client_id","$vars_file","$id");


$gip->print_end("$client_id","$vars_file","", "$daten");

