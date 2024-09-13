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
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="delete_line_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my $ll_id = $daten{'ll_id'} || "";
my $phone_number = $daten{'phone_number'} || "";

if ( $ll_id !~ /^\d{1,10}/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_ll_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)")
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{ll_deleted_message}: \"$phone_number\"","$vars_file");


my @values_ll=$gip->get_ll("$client_id","$ll_id");
my $ll_client=$values_ll[0]->[5] || "";
my $loc_id=$values_ll[0]->[8] || "";
my $loc=$values_ll[0]->[9] || "";

# Check SITE permission
if ( $user_management_enabled eq "yes" ) {
    $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc", "$loc_id");
}

$gip->delete_ll("$client_id","$ll_id");


my $audit_type="56";
my $audit_class="13";
my $update_type_audit="1";
my $event="$phone_number";
$event=$event . "," . $ll_client if $ll_client;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintLLTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

