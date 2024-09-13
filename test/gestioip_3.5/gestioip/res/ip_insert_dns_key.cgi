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
	my $required_perms="read_line_perm,create_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $name=$daten{'name'} || "";
my $tsig_key=$daten{'tsig_key'} || "";
my $description=$daten{'description'} || "";
my $dns_zone_id=$daten{'dns_zone_id'} || "";
$tsig_key=$gip->remove_whitespace_se("$tsig_key");

# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        description=>"$description",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{dns_key_added_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_key_added_message}","$vars_file");

my $check_key = $gip->check_dns_key("$client_id", "$tsig_key") || "";
$gip->print_error("$client_id","$$lang_vars{key_exists_message}") if $check_key;
$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{insert_tsig_key_message}") if ! $tsig_key;


$gip->insert_dns_key("$client_id","$tsig_key","$name","$description");


my $audit_type="160";
my $audit_class="25";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintDNSKeyTab("$client_id","$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

