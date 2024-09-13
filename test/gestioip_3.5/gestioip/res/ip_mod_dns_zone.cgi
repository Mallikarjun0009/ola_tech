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

my $id=$daten{'id'} || $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)");
my $description=$daten{'description'} || "";
my $name=$daten{'name'} || "";
my $type=$daten{'type'} || "";
my $dns_user_id=$daten{'dns_user_id'} || "";
my $ttl=$daten{'ttl'} || "";
my $dyn_dns_server=$daten{'dyn_dns_server'} || "";
my $server_type=$daten{'server_type'} || "";


# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        id=>"$id",
        id1=>"$dns_user_id",
        description=>"$description",
        dyn_dns_server=>"$dyn_dns_server",
        ttl=>"$ttl",
        dns_type=>"$type",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{user_updated_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{parameter_changed_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{ttl_to_big_message}") if $ttl && $ttl !~ /^\d{1,8}$/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}: server_type") if $server_type && $server_type !~ /^(GSS-TSIG|TSIG)$/;


my @values=$gip->get_dns_zones("$client_id","$id");
my $old_name=$values[0]->[1] || "---";
my @dns_user_values = $gip->get_dns_user("$client_id","$dns_user_id");
my $dns_user_name=$dns_user_values[0]->[1] || "---";

$gip->update_dns_zone("$client_id","$id","$name","$description","$type","$dns_user_id","$ttl","$dyn_dns_server","$server_type");
if ( $name ne $old_name ) {
	# update existing custom column entries
	my $cc_name = "DNSZone";
	$cc_name = "DNSPTRZone" if $type eq "PTR";
	my $cc_id = $gip->get_custom_column_id_from_name("$client_id", "$cc_name") || "";
	$gip->update_custom_column_entries_all("$client_id", "$cc_id", "$old_name", "$name", "network" ) if $cc_id;
}

my $old_description=$values[0]->[2] || "---";
my $old_type=$values[0]->[3] || "---";
my $old_dns_user_id=$values[0]->[4] || "---";
my $old_ttl=$values[0]->[5] || "---";

my @dns_user_values_old = $gip->get_dns_user("$client_id","$old_dns_user_id");
my $dns_user_name_old=$dns_user_values_old[0]->[1] || "---";

$type="---" if ! $type;
$name="---" if ! $name;
$ttl="---" if ! $ttl;
$dns_user_name="---" if ! $dns_user_name;
$description="---" if ! $description;

my $audit_type="139";
my $audit_class="25";
my $update_type_audit="1";
my $event1="$old_name, $old_description, $old_ttl, $old_type";
my $event2="$name, $description, $description, $ttl, $type";
my $event = $event1 . " -> " . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @as=$gip->get_dns_zones("$client_id");

print "<p>\n";

$gip->PrintDNSZoneTab("$client_id",\@as,"$vars_file");

$gip->print_end("$client_id", "", "", "");

