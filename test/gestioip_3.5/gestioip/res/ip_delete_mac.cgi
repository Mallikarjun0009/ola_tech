#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang();
my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="delete_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $id = $daten{'id'} || "";
my $mac = $daten{'mac'} || "";

if ( $mac !~ /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_mac_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)")
}

if ( $id !~ /^\d{1,10}/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_mac_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)")
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mac_deleted_message}: \"$mac\"","$vars_file");


$gip->delete_macs("$client_id","$id");
delete @ENV{'PATH', 'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};
my ($exit, $error) = $gip->update_mac_extern("$client_id","$mac","delete");
print "$error<br><p>" if $error;

my $audit_type="149";
my $audit_class="28";
my $update_type_audit="1";
my $event="$mac";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @values=$gip->get_macs("$client_id");

if ( $values[0] ) {
	print "<p>\n";
	$gip->PrintMACTab("$client_id",\@values,"$vars_file");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id", "", "", "");
