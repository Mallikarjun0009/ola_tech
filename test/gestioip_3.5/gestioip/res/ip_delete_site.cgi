#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_sites_and_cats_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $id = $daten{'id'} || "";
my $site = $daten{'site'} || "";

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
        name=>"$site",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{delete_site_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{delete_site_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if ! $site;


$gip->reset_host_loc_id("$client_id","$id");
$gip->reset_net_loc_id("$client_id","$id");
$gip->reset_line_loc_id("$client_id","$id");
$gip->loc_del("$client_id","$site");


my $audit_type="13";
my $audit_class="23";
my $update_type_audit="1";
my $event="$site";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

#print "<p><b>$$lang_vars{site_deleted_message}: $site</b><p>\n";
print <<EOF;
<script>
update_nav_text("$$lang_vars{site_deleted_message}: $site");
</script>
EOF

$gip->PrintSiteTab("$client_id","$vars_file");

$gip->print_end("$client_id", "", "", "");

