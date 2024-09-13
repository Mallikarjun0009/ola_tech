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
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
        my $required_perms="manage_gestioip_perm";
        $gip->check_perms (
                client_id=>"$client_id",
                vars_file=>"$vars_file",
                daten=>\%daten,
                required_perms=>"$required_perms",
        );
}

my $client=$daten{'client_name'} || "";
my $loc=$daten{'loc'} || "";
my $phone=$daten{'phone'} || "";
my $fax=$daten{'fax'} || "";
my $address=$daten{'address'} || "";
my $comment=$daten{'comment'} || "";
my $contact_name_1=$daten{'contact_name_1'} || "";
my $contact_phone_1=$daten{'contact_phone_1'} || "";
my $contact_cell_1=$daten{'contact_cell_1'} || "";
my $contact_email_1=$daten{'contact_email_1'} || "";
my $contact_comment_1=$daten{'contact_comment_1'} || "";
my $contact_name_2=$daten{'contact_name_2'} || "";
my $contact_phone_2=$daten{'contact_phone_2'} || "";
my $contact_cell_2=$daten{'contact_cell_2'} || "";
my $contact_email_2=$daten{'contact_email_2'} || "";
my $contact_comment_2=$daten{'contact_comment_2'} || "";
my $contact_name_3=$daten{'contact_name_3'} || "";
my $contact_phone_3=$daten{'contact_phone_3'} || "";
my $contact_cell_3=$daten{'contact_cell_3'} || "";
my $contact_email_3=$daten{'contact_email_3'} || "";
my $contact_comment_3=$daten{'contact_comment_3'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{clients_message}","$vars_file");

my %values_clients=$gip->get_client_hash_all("$client_id");

if ( ! $client ) {
	$gip->print_error("$client_id","$$lang_vars{introduce_client_name_message}");
}
if ( $client !~ /^.{2,30}$/ ) {
	$gip->print_error("$client_id","$$lang_vars{max_signos_clientname_message}");
}
if ( $client =~ /\s/ ) {
	$gip->print_error("$client_id","$$lang_vars{name_no_whitespace_message}");
}
if ( $client =~ /^\d+$/ ) {
	$gip->print_error("$client_id","$$lang_vars{no_solo_number_message}");
}
while ( my ($key, @value) = each(%values_clients) ) {
	my $client_old = $value[0]->[0];
	if ( $client eq $client_old ) {
		$gip->print_error("$client_id","$$lang_vars{client_exists_message}")
	}
}

$gip->print_error("$client_id","$$lang_vars{introduce_loc_min_message}") if ! $loc;

my $last_client_id=$gip->insert_client("$client");
$gip->insert_client_entry("$last_client_id", "$phone", "$fax", "$address", "$comment", "$contact_name_1", "$contact_phone_1", "$contact_cell_1", "$contact_email_1", "$contact_comment_1", "$contact_name_2", "$contact_phone_2", "$contact_cell_2", "$contact_email_2", "$contact_comment_2", "$contact_name_3", "$contact_phone_3", "$contact_cell_3", "$contact_email_3", "$contact_comment_3");
$gip->insert_config("$last_client_id","22","254","","yes","","no","n","2");

$loc =~ s/[\n\r\f\t]+//g;
$loc =~ s/,\s*/,/g;
$loc =~ s/\s*,/,/g;
my @values_loc=split(",",$loc);
foreach my $locs(@values_loc) {
	$locs =~ s/^\s*//;
	if ( $locs !~ /^.{1,30}$/ ) {
		$gip->print_error("$client_id","$$lang_vars{max_signos_loc_message}");
	}
}
foreach my $locs(@values_loc) {
	my $last_loc_id=$gip->get_last_loc_id("$client_id");
	$last_loc_id++;
	$gip->loc_add("$last_client_id","$locs","$last_loc_id");
}



my $audit_type="33";
my $audit_class="5";
my $update_type_audit="1";
my $event = $client;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintClientTab("$client_id","$vars_file","$last_client_id");

$gip->print_end("$client_id", "", "", "");
