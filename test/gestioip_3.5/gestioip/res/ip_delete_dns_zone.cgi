#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang();
my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();
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
my $name = $daten{'name'} || "";

if ( $id !~ /^\d{1,10}/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_dns_zone_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)")
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_zone_deleted_message}: \"$name\"","$vars_file");

print "<form name=\"ip_insert_dns_zone_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_dns_zone_form.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w_right\" value=\"$$lang_vars{new_dns_zone_message}\" name=\"B1\"></form><p><br>\n";


my @values=$gip->get_dns_zones("$client_id","$id");

$gip->delete_dns_zone("$client_id","$id");


my $audit_type="140";
my $audit_class="25";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @ll=$gip->get_dns_zones("$client_id");

if ( $ll[0] ) {
	print "<p>\n";
	$gip->PrintDNSZoneTab("$client_id",\@ll,"$vars_file");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id", "", "", "");

