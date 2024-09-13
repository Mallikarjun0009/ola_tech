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

my $id = $daten{'id'};
my $user_password = $daten{'user_password'};
my $repeat_user_password = $daten{'repeat_user_password'};
my $master_key = $daten{'master_key'};
my $repeat_master_key = $daten{'repeat_master_key'};

# Parameter check
my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	master_key=>"$master_key",
	user_password=>"$user_password",
	device_password=>"$repeat_user_password",
	id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{insert_master_key_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_master_key_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_user_password_error_message}") if ! $user_password;
$gip->print_error("$client_id","$$lang_vars{insert_master_key_error_message}") if ! $master_key;
$gip->print_error("$client_id","$$lang_vars{password_not_match_message}") if $user_password ne $repeat_user_password;
$gip->print_error("$client_id","$$lang_vars{mater_key_not_match_message}") if $master_key ne $repeat_master_key;

my $master_key_get=$gip->get_master_key("$client_id","$id") || "";
if ( $master_key_get ) {
	$gip->print_error("$client_id","$$lang_vars{master_key_exists_message}");

}


# insert master key

$gip->insert_master_key(
	client_id=>"$client_id",
	master_key=>"$master_key",
	user_id=>"$id",
	user_password=>"$user_password",
);

$gip->insert_user_key(
	client_id=>"$client_id",
	user_id=>"$id",
	user_password=>"$user_password",
);


my $audit_type="134";
my $audit_class="24";
my $update_type_audit="1";
my $event="$$lang_vars{master_key_added_message}";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p><br><b>$$lang_vars{master_key_added_info_message}</b><p><br><p>\n";
print "<form name=\"manage_user_passwords\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{password_management_perm_message}\" name=\"B1\"></form><p><br><p>\n";


$gip->print_end("$client_id","$vars_file","", "$daten");

