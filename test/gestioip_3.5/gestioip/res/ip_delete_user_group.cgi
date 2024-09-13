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

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
        name=>"$name",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{delete_user_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_user_group_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;
$gip->print_error("$client_id","$$lang_vars{default_user_group_no_delete_message}") if $id =~ /^(1|2|3)$/;

my $in_use = $gip->check_user_group_in_use("$client_id","$id") || "";
my @in_use=@$in_use;
if ( $in_use[0]->[0] ) {
	my $j=0;
	my $in_use_group_users="";
	foreach (@in_use) {
		$in_use_group_users.="<br>$in_use[$j]->[0]";
		$j++;
	}
	$in_use_group_users=~s/^, //;
        $gip->print_error("$client_id","$$lang_vars{job_group_in_use_message}:<p>$in_use_group_users");
}

$gip->delete_user_group("$client_id","$id");
$gip->delete_user_group_perms("$client_id","$id");


my $audit_type="121";
my $audit_class="21";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

print "<p><b>$$lang_vars{user_group_deleted_message}: $name</b><p>\n";

$gip->PrintUserGroupTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

