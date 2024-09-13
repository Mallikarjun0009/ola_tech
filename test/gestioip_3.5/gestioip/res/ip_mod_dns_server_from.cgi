#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
# strip # sign from the color
$daten =~ s/color=%23/color=/;
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
my $id=$daten{'id'} || "";
my $name=$daten{'name'} || "";
$name=$gip->remove_whitespace_se("$name");
my $description=$daten{'description'} || "";
my $color=$daten{'color'} || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{site_updated_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{site_updated_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{tag_no_whitespace_message}") if $name =~ /\s/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;


# Check if this name exists

my @objects = $gip->get_tag("$client_id");
foreach my $obj( @objects ) {
    if ( $name eq $obj->[1] && $id != $obj->[0]) {
        $gip->print_error("$client_id","<b>$name</b>: $$lang_vars{tag_exists_message}");
    }
}

my @tag = $gip->get_tag_from_id("$client_id", "$id");
my $name_db = $tag[0][0];
my $description_db = $tag[0][1];
my $color_db = $tag[0][2];


##### datenbank updaten

$gip->update_tag("$client_id", "$id", "$name", "$description", "$color");



my $audit_type="159";
my $audit_class="29";
my $update_type_audit="1";
my $event="$name_db,$description_db,#${color_db} -> $name,$description,#${color}";

$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintTagTab("$client_id","$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

