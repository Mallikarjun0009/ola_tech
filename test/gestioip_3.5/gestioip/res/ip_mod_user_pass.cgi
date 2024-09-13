#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

use strict;
use DBI;
use lib '../modules';
use GestioIP;
use CGI;



my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $q = CGI->new();


my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();



my $id=$daten{'id'} || "";
my $login_pass=$daten{'login_pass'} || "";
my $retype_login_pass=$daten{'retype_login_pass'} || "";

my %values_users=$gip->get_user_hash("$client_id");
my $name=$values_users{$id}[0];
my $user=$ENV{'REMOTE_USER'};


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" && $user ne $name ) {
	my $required_perms="manage_user_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_user_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id", back_link=>1) if $error_message;

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_user_message}",notification=>"$$lang_vars{password_not_match_message}",vars_file=>"$vars_file",client_id=>"$client_id", back_link=>1) if $login_pass ne $retype_login_pass;


##### password updaten

my $error = $gip->update_user_pass("$name", "$login_pass") || "";
$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_user_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


my $audit_type="183";
my $audit_class="21";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


if ( $user eq $name ) {
    # logout if user changes it's password
    print $q->redirect("../logout");
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_user_message}","$vars_file");


my $div_notify = GipTemplate::create_div_notify_text(
	noti => "$name: $$lang_vars{password_updated_message}",
);
print "$div_notify\n";

$gip->PrintUserTab("$client_id","$vars_file");


$gip->print_end("$client_id","$vars_file","", "$daten");
