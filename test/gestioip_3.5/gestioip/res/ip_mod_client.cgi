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


my $id = $daten{'id'} || "";

my $client_new=$daten{'client_name'} || "";
my $phone_new=$daten{'phone'} || "";
my $fax_new=$daten{'fax'} || "";
my $address_new=$daten{'address'} || "";
my $comment_new=$daten{'comment'} || "";
my $contact_name_1_new=$daten{'contact_name_1'} || "";
my $contact_phone_1_new=$daten{'contact_phone_1'} || "";
my $contact_cell_1_new=$daten{'contact_cell_1'} || "";
my $contact_email_1_new=$daten{'contact_email_1'} || "";
my $contact_comment_1_new=$daten{'contact_comment_1'} || "";
my $contact_name_2_new=$daten{'contact_name_2'} || "";
my $contact_phone_2_new=$daten{'contact_phone_2'} || "";
my $contact_cell_2_new=$daten{'contact_cell_2'} || "";
my $contact_email_2_new=$daten{'contact_email_2'} || "";
my $contact_comment_2_new=$daten{'contact_comment_2'} || "";
my $contact_name_3_new=$daten{'contact_name_3'} || "";
my $contact_phone_3_new=$daten{'contact_phone_3'} || "";
my $contact_cell_3_new=$daten{'contact_cell_3'} || "";
my $contact_email_3_new=$daten{'contact_email_3'} || "";
my $contact_comment_3_new=$daten{'contact_comment_3'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_client_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $id !~ /^\d{1,4}$/;

if ( ! $client_new ) {
	$gip->print_error("$client_id","$$lang_vars{introduce_client_name_message}");
}
if ( $client_new !~ /^.{2,30}$/ ) {
	$gip->print_error("$client_id","$$lang_vars{max_signos_clientname_message}");
}


my %values_clients=$gip->get_client_hash_all("$id");

while ( my ($key, @value) = each(%values_clients) ) {
	next if $key == $id;
	my $client_old = $value[0]->[0];
	if ( $client_new eq $client_old ) {
		$gip->print_error("$client_id","$$lang_vars{client_exists_message}")
	}
}


my $client = $values_clients{$id}[0];
my $phone = $values_clients{$id}[1] || "";
my $fax = $values_clients{$id}[2] || "";
my $address = $values_clients{$id}[3] || "";
my $comment = $values_clients{$id}[4] || "";
my $contact_name_1 = $values_clients{$id}[5] || "";
my $contact_phone_1 = $values_clients{$id}[6] || "";
my $contact_cell_1 = $values_clients{$id}[7] || "";
my $contact_email_1 = $values_clients{$id}[8] || "";
my $contact_comment_1 = $values_clients{$id}[9] || "";
my $contact_name_2 = $values_clients{$id}[10] || "";
my $contact_phone_2 = $values_clients{$id}[11] || "";
my $contact_cell_2 = $values_clients{$id}[12] || "";
my $contact_email_2 = $values_clients{$id}[13] || "";
my $contact_comment_2 = $values_clients{$id}[14] || "";
my $contact_name_3 = $values_clients{$id}[15] || "";
my $contact_phone_3 = $values_clients{$id}[16] || "";
my $contact_cell_3 = $values_clients{$id}[17] || "";
my $contact_email_3 = $values_clients{$id}[18] || "";
my $contact_comment_3 = $values_clients{$id}[19] || "";
my $default_resolver = $values_clients{$id}[20] || "";
my $dns_server_1 = $values_clients{$id}[21] || "";
my $dns_server_2 = $values_clients{$id}[22] || "";
my $dns_server_3 = $values_clients{$id}[23] || "";


if ( $client_new ne $client ) {
	$gip->update_client("$client_id","$id","$client_new");
}

$gip->update_client_entry("$client_id", "$id", "$phone_new", "$fax_new", "$address_new", "$comment_new", "$contact_name_1_new", "$contact_phone_1_new", "$contact_cell_1_new", "$contact_email_1_new", "$contact_comment_1_new", "$contact_name_2_new", "$contact_phone_2_new", "$contact_cell_2_new", "$contact_email_2_new", "$contact_comment_2_new", "$contact_name_3_new", "$contact_phone_3_new", "$contact_cell_3_new", "$contact_email_3_new", "$contact_comment_3_new");


my $audit_type="35";
my $audit_class="5";
my $update_type_audit="1";
my $event = $client;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintClientTab("$client_id","$vars_file","$id");

$gip->print_end("$client_id", "", "", "");
