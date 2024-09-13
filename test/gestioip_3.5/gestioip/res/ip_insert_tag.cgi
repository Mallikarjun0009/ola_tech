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
	my $required_perms="manage_tags_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


# Parameter check
my $name=$daten{'name'} || "";
my $color=$daten{'color'} || "";
my $description=$daten{'description'} || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{add_tag_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_tag_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$name=$gip->remove_whitespace_se("$name");
$gip->print_error("$client_id","$$lang_vars{tag_no_whitespace_message}") if $name =~ /\s/;

$name=$gip->remove_whitespace_se("$name");

# Check if the object exists

my @objects = $gip->get_tag("$client_id");
foreach my $obj( @objects ) {
    if ( $name eq $obj->[1] ) {
        $gip->print_error("$client_id","<b>$name</b>: $$lang_vars{tag_exists_message}");
    }
}


# Insert Object
$gip->tag_add("$client_id","$name","$description","$color");

my $audit_type="157";
my $audit_class="29";
my $update_type_audit="1";
my $event="$name,$description";
$event =~ s/,$//;

$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$gip->PrintTagTab("$client_id","$vars_file");

$gip->print_end("$client_id","$vars_file","", "$daten");

