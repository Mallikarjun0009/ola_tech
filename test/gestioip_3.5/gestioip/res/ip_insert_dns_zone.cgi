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



my $dns_user_id=$daten{'dns_user_id'} || "";
my $description=$daten{'description'} || "";
my $type=$daten{'type'} || "";
my $ttl=$daten{'ttl'} || "";
my $dyn_dns_server=$daten{'dyn_dns_server'} || "";
my $name=$daten{'name'} || "";
$name=$gip->remove_whitespace_se("$name");
my $server_type=$daten{'server_type'} || "";

# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        id1=>"$dns_user_id",
        description=>"$description",
        dyn_dns_server=>"$dyn_dns_server",
        ttl=>"$ttl",
        dns_type=>"$type",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{dns_zone_added_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

my $dyn_dns_updates_enabled=$global_config[0]->[19] || "";


$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{dns_zone_added_message}",notification=>"$$lang_vars{formato_malo_message}: server_type",vars_file=>"$vars_file",client_id=>"$client_id") if $server_type && $server_type !~ /^(GSS-TSIG|TSIG)$/;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{dns_zone_added_message}","$vars_file");


my $id = $gip->check_dns_zone_name_exists("$client_id", "$name") || "";
$gip->print_error("$client_id","$$lang_vars{dns_zone_name_exists_message}") if $id; 
if ( $dyn_dns_updates_enabled eq "yes" ) {
    $gip->print_error("$client_id","$$lang_vars{ttl_to_big_message}") if $ttl && $ttl !~ /^\d{1,8}$/; 
    if ( $server_type eq "GSS-TSIG" ) {
        $gip->print_error("$client_id","$$lang_vars{insert_dns_user_name_error_message}") if ! $dns_user_id;
    } elsif ( $server_type eq "GSS-TSIG" ) {
        $gip->print_error("$client_id","$$lang_vars{insert_tsig_key_error_message}") if ! $dns_user_id;
    }
} else {
    $ttl = 43200;
}
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}: DNS Type") if $type !~ /^(A|AAAA|PTR)$/;

##### dns zone in datenbank einstellen

$gip->insert_dns_zone("$client_id","$name","$description","$type","$dns_user_id","$ttl","$dyn_dns_server","$server_type");


my $audit_type="138";
my $audit_class="25";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

print "<p></p>\n";
my @zones=$gip->get_dns_zones("$client_id");
if ( $zones[0] ) {
        $gip->PrintDNSZoneTab("$client_id",\@zones,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","", "$daten");

