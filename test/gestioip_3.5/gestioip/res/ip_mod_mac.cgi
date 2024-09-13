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


## check Permissions
#my @global_config = $gip->get_global_config("$client_id");
#my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm,create_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{modify_mac_message}","$vars_file");

my $mac = $daten{'mac'} || "";

if ( ! $mac ) {
        $gip->print_error("$client_id","$$lang_vars{insert_mac_message}")
}
$mac = $gip->remove_whitespace_se("$mac");
$mac = lc $mac;
if ( $mac !~ /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/ ) {
        $gip->print_error("$client_id","$$lang_vars{check_mac_message}")
}

my $id=$daten{'id'} || "";
my $duid=$daten{'duid'} || "";
my $account=$daten{'account'} || "";
my $comment=$daten{'comment'} || "";
my $host=$daten{'host'} || "";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        comment=>"$comment",
) || "";

$gip->print_error("$client_id","$$lang_vars{'duid_message'}: $$lang_vars{'max_signos_50_message'}") if $duid !~ /^.{0,300}$/;
$gip->print_error("$client_id","$$lang_vars{'account_message'}: $$lang_vars{'max_signos_300_message'}") if $account !~ /^.{0,300}$/;
$gip->print_error("$client_id","$$lang_vars{'host_message'}: $$lang_vars{'max_signos_300_message'}") if $host !~ /^.{0,300}$/;

my @values = $gip->get_macs("$client_id","$id");
my $mac_old = $values[0]->[1];
my $duid_old = $values[0]->[2] || "";
my $account_old = $values[0]->[3] || "";
my $host_old = $values[0]->[4] || "";
my $comment_old = $values[0]->[5] || "";


##### MAC in datenbank einstellen

my $return = $gip->mod_mac("$client_id","$id","$mac","$duid","$account","$host","$comment");

if ( $return ) {
        $gip->print_error("$client_id","$$lang_vars{mac_exists_message}")
}
if ( $mac_old ne $mac ) {
    delete @ENV{'PATH', 'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};
    my ($exit, $error) = $gip->update_mac_extern("$client_id","$mac_old","delete");
    print "$error<br><p>" if $error;
    ($exit, $error) = $gip->update_mac_extern("$client_id","$mac","insert");
    print "$error<br><p>" if $error;
}

my $audit_type="148";
my $audit_class="28";
my $update_type_audit="1";
my $event="$mac_old,$duid_old,$account_old,$host_old,$comment_old -> $mac,$duid,$account,$host,$comment";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my @vals=$gip->get_macs("$client_id");
if ( $vals[0] ) {
        $gip->PrintMACTab("$client_id",\@vals,"$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id","$vars_file","", "$daten");
