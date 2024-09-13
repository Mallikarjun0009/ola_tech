#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;
use Crypt::CBC;
use MIME::Base64;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $user_id = $daten{'id'};
my $user_password = $daten{'user_password'} || "";
my $new_user_password = $daten{'new_user_password'} || "";
my $repeat_new_user_password = $daten{'repeat_new_user_password'} || "";
my $new_master_key = $daten{'master_key'} || "";
my $repeat_new_master_key = $daten{'repeat_master_key'} || "";
my $master_key_only = $daten{'master_key_only'} || "";
if ( $master_key_only ) {
    $new_user_password = $user_password;
}

# Parameter check
my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	user_password=>"$user_password",
	device_password=>"$repeat_new_user_password",
	id_user=>"$user_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{mod_user_password_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="password_management_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mod_user_password_message}","$vars_file");


my ($check_user_pass,$master_key_change)=$gip->check_user_key("$client_id","$user_id","$user_password");
$gip->print_error("$client_id","$$lang_vars{insert_user_password_error_message}") if ! $user_password && ! $master_key_change && ! $master_key_only;
$gip->print_error("$client_id","$$lang_vars{insert_new_password_message}") if ! $new_user_password && ! $master_key_only;
$gip->print_error("$client_id","$$lang_vars{password_not_match_message}") if $new_user_password ne $repeat_new_user_password && ! $master_key_only;

$gip->print_error("$client_id","$$lang_vars{insert_master_key_error_message}") if ! $new_master_key && $master_key_change && $master_key_only;
$gip->print_error("$client_id","$$lang_vars{mater_key_not_match_message}") if $new_master_key ne $repeat_new_master_key && $master_key_change && $master_key_only;

#$gip->print_error("$client_id","$$lang_vars{master_key_changed_message}") if $master_key_change;
$gip->print_error("$client_id","$$lang_vars{wrong_user_password_message}") if $user_password && ! $check_user_pass && ! $master_key_only;

my $master_key;
if ( ! $master_key_change && ! $master_key_only ) {
	my $master_key_get=$gip->get_master_key("$client_id","$user_id") || "";
	$master_key=$gip->decryptString("$master_key_get","$user_password");
} else {
	$master_key=$new_master_key;
}

$gip->delete_master_key("$client_id","$user_id");

$gip->insert_master_key(
	client_id=>"$client_id",
	master_key=>"$master_key",
	user_id=>"$user_id",
	user_password=>"$new_user_password",
);

$gip->delete_user_key("$client_id","$user_id") if ! $master_key_only;

$gip->insert_user_key(
        client_id=>"$client_id",
        user_id=>"$user_id",
        user_password=>"$new_user_password",
) if ! $master_key_only;


my $audit_type;
my $event;
my $fin_message = $$lang_vars{user_password_updated_message};
if ( ! $master_key_only ) {
    $audit_type="130";
    $event="$$lang_vars{user_password_updated_message}";
    $fin_message = $$lang_vars{user_password_updated_message};
} else {
    $audit_type="167";
    $event="$$lang_vars{user_master_key_updated_message}";
    $fin_message = $$lang_vars{user_master_key_updated_message};
}

my $audit_class="24";
my $update_type_audit="1";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p><br><b>$fin_message</b><p><br><p>\n";
print "<form name=\"manage_user_passwords\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{password_management_perm_message}\" name=\"B1\"></form><p><br><p>\n";



$gip->print_end("$client_id","$vars_file","", "$daten");

