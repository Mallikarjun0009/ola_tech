#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

use strict;
use DBI;
use lib '../modules';
use GestioIP;
#use WWW::CSRF qw(check_csrf_token CSRF_OK);



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
my $site_id=$daten{'id'} || "";
my $site=$daten{'site'} || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$site",
        id=>"$site_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{site_updated_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{site_updated_message}","$vars_file");


#if ( defined($ENV{'X-Csrf-Token'}) ) {
    
#my $status = check_csrf_token($username, "s3kr1t", $csrf_token) || "";

#    print "TEST STATUS ENV: $ENV{'X-Csrf-Token'}<br>\n";
#}

#print "TEST ENV: $ENV{'CSRFToken'} - $daten{'CSRFToken'}<br>\n";

my $username = "gipadmin";
#my $csrf_token = $daten{'CSRFToken'};
#my $status = check_csrf_token($username, "s3kr1t", $csrf_token) || "";
#if ($status ne "CSRF_OK") {
#        print "TEST CSRF ERROR: $status - $csrf_token\n";
#}



$gip->print_error("$client_id","$$lang_vars{introduce_loc_message}") if ! $site;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $site_id;


my @site_columns=$gip->get_site_columns("$client_id");
my %values_sites_cc=$gip->get_site_column_values_hash("$client_id"); # $values{"${column_id}_${site_id}"}="$entry";
my @cc_entries_db;
my @cc_entries;


# Check if this site exists

my $site_db = "";
my @sites=$gip->get_loc_all("$client_id");
foreach my $loc( @sites ) {
    if ( $site eq $loc->[1] && $loc->[0] != $site_id  ) {
            $gip->print_error("$client_id","<b>$site</b>: $$lang_vars{loc_exists_message}");
    }
}


my $j=0;
foreach ( @site_columns ) {

    my $column_id=$site_columns[$j]->[0];
    my $column_name=$site_columns[$j]->[1];
    my $mandatory=$site_columns[$j]->[2];

	my $entry=$daten{"$column_name"} || "";
	$entry=$gip->remove_whitespace_se("$entry");
    push @cc_entries,"$entry";

	if ( $mandatory && ! $entry ) {
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $column_name");
    }

	my $entry_db=$values_sites_cc{"${column_id}_${site_id}"} || "";
    push @cc_entries_db,"$entry_db";

	if ( $entry_db && ! $entry ) {
		$gip->delete_site_column_entry("$client_id","$column_id","$site_id" );
	} elsif ( $entry_db ) {
		$gip->update_site_column_entry("$client_id","$column_id","$site_id","$entry" );
	} else {
		$gip->insert_site_column_entry("$client_id","$column_id","$site_id","$entry" );
	}

	$j++;
}


##### datenbank updaten

$site_db=$gip->get_loc_from_id("$client_id","$site_id");

$gip->rename_loc("$client_id","$site_id","$site") if $site ne $site_db;

my $audit_type="127";
my $audit_class="23";
my $update_type_audit="1";
my $event1="$site_db";
foreach ( @cc_entries_db ) {
        $event1 .= ", " . $_;
}
my $event2="$site";
foreach ( @cc_entries ) {
        $event2 .= ", " . $_;
}

my $event = $event1 . " -> " . $event2;


$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

my %changed_id;
$changed_id{$site_id}=$site_id;
$gip->PrintSiteTab("$client_id", "$vars_file", "", "", \%changed_id);

$gip->print_end("$client_id","$vars_file","", "$daten");

