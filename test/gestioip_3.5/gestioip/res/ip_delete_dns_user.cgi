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
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_dns_user_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)")
}

my @values_dns_zone = $gip->check_dns_user_in_use("$client_id","$id") || "";
my $anz_dns_zones = scalar(@values_dns_zone);

if ( $values_dns_zone[0] ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_user_in_use_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{dns_user_in_use_message}");
    print "<p>\n";
    my $j = 0;
    foreach (@values_dns_zone) {
        print "$values_dns_zone[$j]->[1]";
        $j++;
    }
}    

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_user_deleted_message}: \"$name\"","$vars_file");

print "<form name=\"ip_insert_dns_user_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_dns_user_form.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w_right\" value=\"$$lang_vars{new_user_message}\" name=\"B1\"></form><p><br>\n";


my @values=$gip->get_dns_user("$client_id","$id");

$gip->delete_dns_user("$client_id","$id");


my $audit_type="137";
my $audit_class="25";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @ll=$gip->get_dns_user("$client_id");

if ( $ll[0] ) {
	print "<p>\n";
	$gip->PrintDNSUserTab("$client_id",\@ll,"$vars_file");
} else {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id", "", "", "");

