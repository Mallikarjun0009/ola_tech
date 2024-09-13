#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
        my $required_perms="manage_gestioip_perm,delete_net_perm,delete_host_perm";
        $gip->check_perms (
                client_id=>"$client_id",
                vars_file=>"$vars_file",
                daten=>\%daten,
                required_perms=>"$required_perms",
        );
}

my $base_uri = $gip->get_base_uri();
my $id = $daten{'id'} || "";
my $client = $daten{'client_name'} || "";

$gip->CheckInput("1",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_client_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if ! $client;

my $count_clients=$gip->count_clients();
my $default_client_id=$gip->get_default_client_id("$client_id") || "1";

$gip->print_error("$client_id","$$lang_vars{default_client_not_delete_message}") if $id == 1;

$gip->delete_client("$client_id","$id");
$gip->update_default_client("1","1") if $id == $default_client_id;


my $audit_type="34";
my $audit_class="5";
my $update_type_audit="1";
my $event="$client";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

print "<p><b>$$lang_vars{client_deleted_message}: $client</b><p>\n";

$gip->PrintClientTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

