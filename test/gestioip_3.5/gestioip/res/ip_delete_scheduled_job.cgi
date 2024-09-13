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
	my $required_perms="manage_snmp_group_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $id = $daten{'id'} || "";
my $name = $daten{'name'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_job_message}","$vars_file");

my $delete_cron_error = $gip->delete_cron_entry("$id");
if ( $delete_cron_error ) {
    $gip->print_error("$client_id","$$lang_vars{error_update_cron_entry_message}: $id");
} else {
    $gip->delete_scheduled_job("$client_id","$id");
}

my $audit_type="175";
my $audit_class="33";
my $update_type_audit="1";
my $event="$name";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

print <<EOF;
<script>
update_nav_text("$$lang_vars{job_deleted_message}");
</script>
EOF

my $div_notify = GipTemplate::create_div_notify_text(
	noti => "$$lang_vars{job_deleted_message}: $name ",
);
print "$div_notify\n";

$gip->PrintJobTab("$client_id", "$vars_file");


$gip->print_end("$client_id","$vars_file","", "$daten");

