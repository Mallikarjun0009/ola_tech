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
	my $required_perms="manage_dns_server_group_perm";
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
my $dns_server1=$daten{'dns_server1'} || "";
my $dns_server2=$daten{'dns_server2'} || "";
my $dns_server3=$daten{'dns_server3'} || "";
my $description=$daten{'description'} || "";


my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        name=>"$name",
        id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_dns_server_group_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_dns_server_group_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{tag_no_whitespace_message}") if $name =~ /\s/;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;

if ( ! $dns_server1 && ! $dns_server2 && ! $dns_server3 ) {
    $gip->print_error("$client_id","$$lang_vars{no_dns_server_message}");
}

my $valid_ip;
$dns_server1=$gip->remove_whitespace_se("$dns_server1");
$dns_server2=$gip->remove_whitespace_se("$dns_server2");
$dns_server3=$gip->remove_whitespace_se("$dns_server3");
my @dns_servers = ("$dns_server1","$dns_server2","$dns_server3");
foreach ( @dns_servers ) {
    next if ! $_;
    $valid_ip = $gip->check_valid_ipv4("$_") || "";
    if ( ! $valid_ip ) {
        $valid_ip = $gip->check_valid_ipv6("$_") || "";
    }
    $gip->print_error("$client_id","$$lang_vars{ip_invalid_message}: $_") if ! $valid_ip;
}



# Check if this name exists

my @objects = $gip->get_dns_server_group("$client_id");

foreach my $obj( @objects ) {
    if ( $name eq $obj->[1] && $id != $obj->[0]) {
        $gip->print_error("$client_id","<b>$name</b>: $$lang_vars{dns_server_group_exists_message}");
    }
}

my @obj = $gip->get_dns_server_group_from_id("$client_id", "$id");
my $name_db = $obj[0][0];
my $description_db = $obj[0][1] || "";
my $dns_server1_db = $obj[0][2] || "";
my $dns_server2_db = $obj[0][3] || "";
my $dns_server3_db = $obj[0][4] || "";


##### datenbank updaten

$gip->update_dns_server_group("$client_id", "$id", "$name", "$description", "$dns_server1", "$dns_server2", "$dns_server3");


my $audit_type="168";
my $audit_class="31";
my $update_type_audit="1";
my $event="$name_db,$description_db,$dns_server1_db,$dns_server2_db,$dns_server3_db -> $name,$description,$dns_server1,$dns_server2,$dns_server3";

$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

my %changed_id;
$changed_id{$id}=$id;

$gip->PrintDNSServerGroupTab("$client_id","$vars_file", \%changed_id);

$gip->print_end("$client_id","$vars_file","", "$daten");

