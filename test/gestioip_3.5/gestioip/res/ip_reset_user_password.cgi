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

# Parameter check
my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	id_user=>"$user_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{reset_user_password_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

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


$gip->delete_master_key("$client_id","$user_id");
$gip->delete_user_key("$client_id","$user_id");

my $audit_type="166";
my $audit_class="24";
my $update_type_audit="1";
my $event="$$lang_vars{user_password_updated_message}";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p><br><b>$$lang_vars{user_password_reset_message}</b><p><br><p>\n";
print "<form name=\"manage_user_passwords\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{password_management_perm_message}\" name=\"B1\"></form><p><br><p>\n";



$gip->print_end("$client_id","$vars_file","", "$daten");

