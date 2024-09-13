#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel



use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();

my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
my $user_password = $daten{'user_password'} || "";


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
my $host_id = $daten{'host_id'};
my $match = $daten{'match'};
my $ip = $daten{'ip'} || "";
my $ip_version = $daten{'ip_version'};
my $red_num = $daten{'red_num'} || "";
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

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
	match=>"$match",
        ip=>"$ip",
        ip_version=>"$ip_version",
        id=>"$host_id",
	user_password=>"$user_password",
	red_num=>"$red_num",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{insert_device_password_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_device_password_message} $ip","$vars_file");


$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 1") if ! $host_id;

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $user=$ENV{'REMOTE_USER'};
my $user_id=$gip->get_user_id("$client_id","$user");


print "<p>\n";
print "<form name=\"insert_device_password_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_device_password.cgi\"><br>\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{user_password_message}</td><td $align1><input name=\"user_password\" value=\"$user_password\" type=\"password\" size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{name_message}</td><td $align1><input name=\"name\" value=\"\" type=\"text\" size=\"15\" maxlength=\"50\"></td></tr>\n";
#### Javascript to switch between password and text field.....
print "<tr><td $align>$$lang_vars{device_password_message}</td><td $align1><input name=\"device_password\" value=\"\" type=\"password\" size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" value=\"\" type=\"text\" size=\"50\" maxlength=\"200\"></td></tr>\n";

print "</table>\n";

print "<p>\n";

print "<script type=\"text/javascript\">\n";
	print "document.insert_master_key_form.user_password.focus();\n";
print "</script>\n";

my $hidden_vals_host_ips="";
$anz_hosts=0;
$j=0;
foreach my $key ( keys %mass_update_host_ips ) {
        $hidden_vals_host_ips.="<input type=\"hidden\" name=\"mass_update_host_submit_${j}\" value=\"$key\">";
        $anz_hosts++;
	$j++;
}
$hidden_vals_host_ips.="<input type=\"hidden\" name=\"anz_hosts\" value=\"$anz_hosts\"><input type=\"hidden\" name=\"all_passwords\" value=\"$all_passwords\">";


print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$user_id\" name=\"user_id\"><input type=\"hidden\" value=\"$host_id\" name=\"host_id\"><input type=\"hidden\" value=\"$ip\" name=\"ip\"><input type=\"hidden\" value=\"$ip_version\" name=\"ip_version\"><input type=\"hidden\" value=\"$red_num\" name=\"red_num\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\">$hidden_vals_host_ips<input type=\"submit\" value=\"$$lang_vars{add_message}\" name=\"B2\" class=\"input_link_w_net\"></form></span><br><p>\n";

$gip->print_end("$client_id", "", "", "");
