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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_user_added_message}","$vars_file");


my $name=$daten{'name'} || "";
my $description=$daten{'description'} || "";
my $password=$daten{'password'} || "";
my $realm=$daten{'realm'} || "";
$realm=$gip->remove_whitespace_se("$realm");
$password=$gip->remove_whitespace_se("$password");
$name=$gip->remove_whitespace_se("$name");

##### dns zone in datenbank einstellen

$gip->insert_dns_user("$client_id","$name","$password","$realm","$description");

my $audit_type="135";
my $audit_class="25";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @obj=$gip->get_dns_user("$client_id");
if ( $obj[0] ) {
        $gip->PrintDNSUserTab("$client_id",\@obj,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}


$gip->print_end("$client_id","$vars_file","", "$daten");

