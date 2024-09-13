#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
my $host_id = $daten{'host_id'} || 0;
my $match = $daten{'match'} || "";
my $ip = $daten{'ip'} || "";
my $ip_version = $daten{'ip_version'};
my $red_num = $daten{'red_num'};
my $all_passwords = $daten{'all_passwords'} || "";
my $anz_hosts = $daten{'anz_hosts'} || 0;

my $k;
my $j=0;
my %mass_update_host_ips;
for ($k=0;$k<=$anz_hosts;$k++) {
	if ( $daten{"mass_update_host_submit_${k}"} ) {
		$mass_update_host_ips{$daten{"mass_update_host_submit_${k}"}}++;
		$j++;
	}
}
my $anz_hosts_found=$j;


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
        my $required_perms="password_management_perm";
        $gip->check_perms (
                client_id=>"$client_id",
                vars_file=>"$vars_file",
                daten=>\%daten,
                required_perms=>"$required_perms",
        );
}


# Parameter check
my $error_message;
if ( ! $all_passwords ) {
	$error_message=$gip->check_parameters(
		vars_file=>"$vars_file",
		client_id=>"$client_id",
		match=>"$match",
		ip=>"$ip",
		ip_version=>"$ip_version",
		host_id=>"$host_id",
		red_num=>"$red_num",

	) || "";
} else {
	$error_message=$gip->check_parameters(
		vars_file=>"$vars_file",
		client_id=>"$client_id",
		match=>"$match",
		ip_version=>"$ip_version",
		red_num=>"$red_num",
		save_char=>"$all_passwords",
	) || "";
}

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{device_passwords_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;



$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{device_passwords_message} $ip","$vars_file");


$gip->print_error("$client_id","$$lang_vars{no_ip_selected_message}") if $all_passwords && $anz_hosts_found == 0;


my $user=$ENV{'REMOTE_USER'};
my $user_id=$gip->get_user_id("$client_id","$user");

my $master_key_get=$gip->get_master_key("$client_id","$user_id") || "";
if ( ! $master_key_get ) {
	$gip->print_error("$client_id","$$lang_vars{no_master_key_defined_message}<p>$$lang_vars{insert_master_key_first_message}<p><br><form name=\"admin\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"input_link_w\" value=\"$$lang_vars{manage_passwords_message}\" name=\"B1\"></form>");

}

$gip->PrintPasswordTab("$client_id","$vars_file","$match","$host_id","$ip","$ip_version","$user_id","","","","$red_num","$all_passwords",\%mass_update_host_ips);


$gip->print_end("$client_id", "", "", "");

