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
my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_line_perm,update_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{parameter_changed_message}","$vars_file");


my $id=$daten{'id'} || $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)");
my $tsig_key=$daten{'tsig_key'} || "";
my $name=$daten{'name'} || "";
my $description=$daten{'description'} || "";

my $check_key = $gip->check_dns_key("$client_id", "$tsig_key") || "";
$gip->print_error("$client_id","$$lang_vars{key_exists_message}") if $check_key && $tsig_key ne $check_key;
$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;

my @values=$gip->get_dns_keys("$client_id","$id");

$gip->update_dns_key("$client_id","$id","$tsig_key","$name","$description");

my $old_name=$values[0]->[2];
my $old_tsig_key=$values[0]->[1];
my $old_description=$values[0]->[3] || "---";

$description="---" if ! $description;

my $audit_type="162";
my $audit_class="25";
my $update_type_audit="1";
my $event1="$old_name, xxx, $old_description";
my $event2="$name, xxx, $description";
my $event = $event1 . " -> " . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p>\n";

$gip->PrintDNSKeyTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

