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

my $user_password = $daten{'user_password'};
my $new_master_key = $daten{'master_key'};
my $repeat_new_master_key = $daten{'repeat_master_key'};

# Parameter check
my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	master_key=>"$new_master_key",
	user_password=>"$user_password",
	device_password=>"$repeat_new_master_key",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{mod_master_key_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mod_master_key_message}","$vars_file");

my $user=$ENV{'REMOTE_USER'};
my $user_id=$gip->get_user_id("$client_id","$user");

$gip->print_error("$client_id","$$lang_vars{insert_user_password_error_message}") if ! $user_password;
$gip->print_error("$client_id","$$lang_vars{insert_master_key_error_message}") if ! $new_master_key;
$gip->print_error("$client_id","$$lang_vars{mater_key_not_match_message}") if $new_master_key ne $repeat_new_master_key;

my ($check_user_pass,$master_key_change)=$gip->check_user_key("$client_id","$user_id","$user_password");
$gip->print_error("$client_id","$$lang_vars{wrong_user_password_message}") if $user_password && ! $check_user_pass;

my %values_passwords=$gip->get_device_key_hash("$client_id","$vars_file","","$user_id","$user_password");

$gip->delete_master_key("$client_id","$user_id");

my $changed=1;
$gip->update_master_key_changed("$client_id","$changed");

$gip->insert_master_key(
	client_id=>"$client_id",
	master_key=>"$new_master_key",
	user_id=>"$user_id",
	user_password=>"$user_password",
);

foreach my $key ( keys %{values_passwords} ) {
    my @value=$values_passwords{$key};
    my $name=$value[0]->[0];
    my $comment=$value[0]->[1];
    my $device_password=$value[0]->[3];
    my $host_id=$value[0]->[4];

	$gip->update_device_key(
		client_id=>"$client_id",
		name=>"$name",
		user_password=>"$user_password",
		comment=>"$comment",
		device_password=>"$device_password",
		id=>"$key",
		user_id=>"$user_id",
	);
}

my $audit_type="128";
my $audit_class="24";
my $update_type_audit="1";
my $event="$$lang_vars{master_key_added_message}";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p><br><b>$$lang_vars{master_key_updated_message}</b><p><br><p>\n";
print "<form name=\"manage_user_passwords\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{password_management_perm_message}\" name=\"B1\"></form><p><br><p>\n";


$gip->print_end("$client_id","$vars_file","", "$daten");

