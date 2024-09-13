#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;
use Crypt::CBC;
use MIME::Base64;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $user_id = $daten{'user_id'};
my $user_password = $daten{'user_password'};
my $device_password = $daten{'device_password'};
my $host_id = $daten{'host_id'};
my $name = $daten{'name'};
my $comment = $daten{'comment'} || "";
my $match = $daten{'match'} || "";
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

# Parameter check
my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
	user_password=>"$user_password",
	device_password=>"$device_password",
	match=>"$match",
	id=>"$user_id",
	id1=>"$host_id",
	ip=>"$ip",
	ip_version=>"$ip_version",
	red_num=>"$red_num",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{insert_master_key_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

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

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_device_password_message} $ip","$vars_file");


$gip->print_error("$client_id","$$lang_vars{insert_user_password_error_message}") if ! $user_password;
$gip->print_error("$client_id","$$lang_vars{insert_device_password_error_message}") if ! $device_password;
$gip->print_error("$client_id","$$lang_vars{insert_name_error_message}") if ! $name;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $user_id;

my ($check_user_pass,$master_key_change)=$gip->check_user_key("$client_id","$user_id","$user_password");
$gip->print_error("$client_id","$$lang_vars{master_key_changed_message}<p><br><a href=\"$server_proto://$base_uri/res/ip_manage_user_passwords.cgi\" class=\"help_link_link\">$$lang_vars{password_management_perm_message}</a>","no_back_link") if $master_key_change;
$gip->print_error("$client_id","$$lang_vars{wrong_user_password_message}") if $user_password && ! $check_user_pass;


## check if the name exists
my %values_passwords=$gip->get_device_key_hash("$client_id","$vars_file","$host_id","$user_id");
foreach my $key ( keys %{values_passwords} ) {
	my @value=$values_passwords{$key};
	my $name_old=$value[0]->[0];
	if ( $name_old eq $name ) {
		$gip->print_error("$client_id","$$lang_vars{device_name_exists_message}");
		print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"$$lang_vars{atras_message}\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM><p><br>\n";
		$gip->print_end("$client_id","$vars_file","", "$daten");
	} 
}

my $device_password_id=$gip->insert_device_key(
	client_id=>"$client_id",
	name=>"$name",
	comment=>"$comment",
	user_password=>"$user_password",
	device_password=>"$device_password",
	host_id=>"$host_id",
	user_id=>"$user_id",
);


my $audit_type="131";
my $audit_class="24";
my $update_type_audit="1";
my $event="$$lang_vars{device_password_added_message}";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


#print "$$lang_vars{device_password_added_info_message}<p><br><p>\n";

$gip->PrintPasswordTab("$client_id","$vars_file","$match","$host_id","$ip","$ip_version","$user_id","$user_password","","","$red_num","$all_passwords",\%mass_update_host_ips);


$gip->print_end("$client_id","$vars_file","", "$daten");

