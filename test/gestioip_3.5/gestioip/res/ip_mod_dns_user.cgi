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
my $name=$daten{'name'} || "";
my $description=$daten{'description'} || "";
my $password=$daten{'password'} || "";
my $realm=$daten{'realm'} || "";

my @values=$gip->get_dns_user("$client_id","$id");

$gip->update_dns_user("$client_id","$id","$name","$password","$realm","$description");

my $old_name=$values[0]->[1] || "---";
my $old_password=$values[0]->[2] || "---";
my $old_realm=$values[0]->[3] || "---";
my $old_description=$values[0]->[4] || "---";

$name="---" if ! $name;
$realm="---" if ! $realm;
$description="---" if ! $description;

my $audit_type="136";
my $audit_class="25";
my $update_type_audit="1";
my $event1="$old_name, $old_description, $old_realm";
my $event2="$name, $description, $realm";
my $event = $event1 . " -> " . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @as=$gip->get_dns_user("$client_id");

print "<p>\n";

$gip->PrintDNSUserTab("$client_id",\@as,"$vars_file");

$gip->print_end("$client_id", "", "", "");

