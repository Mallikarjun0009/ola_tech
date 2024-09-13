#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

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
my $site=$daten{'site'} || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$site",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{admin_loc_add_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{admin_loc_add_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{introduce_loc_message}") if ! $site;


$site=$gip->remove_whitespace_se("$site");

# Check if the site exists

my @sites=$gip->get_loc("$client_id");
foreach my $loc( @sites ) {
        if ( $site eq $loc->[0] ) {
                $gip->print_error("$client_id","<b>$site</b>: $$lang_vars{loc_exists_message}");
        }
}


my @site_columns=$gip->get_site_columns("$client_id");

# mandatory checck
my $j=0;
foreach ( @site_columns ) {

	my $column_id=$site_columns[$j]->[0];
	my $column_name=$site_columns[$j]->[1];
    my $mandatory=$site_columns[$j]->[2];

	my $entry=$daten{"$column_name"} || "";

	if ( $mandatory && ! $entry ) {
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $column_name");
    }

    $j++;
}



my $last_loc_id=$gip->get_last_loc_id("$client_id");
$last_loc_id++;
$last_loc_id = "1" if $last_loc_id == "0";

# Insert Site
$gip->loc_add("$client_id","$site","$last_loc_id");



$j=0;
my @cc_entries;
foreach ( @site_columns ) {

	my $column_id=$site_columns[$j]->[0];
	my $column_name=$site_columns[$j]->[1];

	my $entry=$daten{"$column_name"} || "";
	$entry=$gip->remove_whitespace_se("$entry");
	push @cc_entries,"$entry";

	$gip->insert_site_column_entry("$client_id","$column_id","$last_loc_id","$entry" );

	push @cc_entries,"$entry";

	$j++;
}

my $audit_type="10";
my $audit_class="23";
my $update_type_audit="1";
my $event="$site";

foreach ( @cc_entries ) {
	$event.="${_},";
}
$event =~ s/,$//;

$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


my %changed_id;
$changed_id{$last_loc_id}=$last_loc_id;
$gip->PrintSiteTab("$client_id", "$vars_file", "", "", \%changed_id);



$gip->print_end("$client_id","$vars_file","", "$daten");

