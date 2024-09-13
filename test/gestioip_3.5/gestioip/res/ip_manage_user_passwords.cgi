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

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        password=>"$user_password",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{manage_passwords_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;

my $user=$ENV{'REMOTE_USER'};

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_passwords_message} ($$lang_vars{user_message}: $user)","$vars_file");

my $user_management_enabled_db=$global_config[0]->[13];
if ( $user_management_enabled_db ne "yes" ) {
	$gip->print_error("$client_id","$$lang_vars{user_management_disabled_message}");
}


my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $id=$gip->get_user_id("$client_id","$user") || "";
$gip->print_error("$client_id","$$lang_vars{user_not_found_message}") if ! $id;

my ($check_user_pass,$master_key_change)=$gip->check_user_key("$client_id","$id","$user_password");

my $master_key_get=$gip->get_master_key("$client_id","$id") || "";

print <<EOF;

<script type="text/javascript">
<!--
function confirmation() {

        answer = confirm("$$lang_vars{change_master_key_confirm_message}")

        if (answer){
                return true;
        }
        else{
                return false;
        }
}
//-->
</script>
EOF

print "<p><br>\n";
if ( ! $ENV{HTTPS} ) {
	print "<b><font color=\"orange\">$$lang_vars{warning_message}:</font></b><br><i>$$lang_vars{no_ssl_warning_message}</i><br><p><br>\n";
}
if ( $master_key_get ) {
#	print "<p><i>$$lang_vars{master_key_exists_message}</i><p><br>\n";
#	print "<hr>\n";

	if ( $master_key_change ) {
        print "<p><br>\n";
        print "<font color=\"green\"><b>$$lang_vars{master_key_changed_message}</b></font><br><p>\n" if $master_key_change;
        print "<b>$$lang_vars{update_master_key_this_user}</b><p>\n";
        print "<form name=\"mod_user_password_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_user_password.cgi\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><br>\n";
        print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

		print "<tr><td $align>$$lang_vars{password_message}</td><td $align1><input name=\"user_password\" value=\"$user_password\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
		print "<tr><td $align>$$lang_vars{new_master_key_message}</td><td $align1><input name=\"master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
		print "<tr><td $align>$$lang_vars{repeat_new_master_key_message}</td><td $align1><input name=\"repeat_master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
        print "</table><p>\n";
        print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"yes\" name=\"master_key_only\"><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{update_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";
	print "<hr>\n";
    }

	print "<p><br>\n";
	print "<b>$$lang_vars{update_master_key_all_users}</b><br>\n";
	print "<i>$$lang_vars{update_master_key_info_message}</i><br>\n";
	print "<form name=\"mod_master_key_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_master_key.cgi\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><br>\n";
	print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
	print "<tr><td $align>$$lang_vars{password_message}</td><td $align1><input name=\"user_password\" value=\"$user_password\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
	print "<tr><td $align>$$lang_vars{new_master_key_message}</td><td $align1><input name=\"master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
	print "<tr><td $align>$$lang_vars{repeat_new_master_key_message}</td><td $align1><input name=\"repeat_master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
	print "</table><p>\n";
	print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{update_message}\" name=\"B2\" class=\"btn\" onclick=\"return confirmation(\'\',\'delete\');\"></form></span><br><p>\n";
	print "<p>\n";

	print "<hr>\n";

	if ( ! $master_key_change ) {
        print "<p><br>\n";
        print "<b>$$lang_vars{mod_user_password_message}</b><p>\n";
        print "<font color=\"green\"><b>$$lang_vars{master_key_changed_message}</b></font><br>\n" if $master_key_change;
        print "<form name=\"mod_user_password_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_mod_user_password.cgi\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><br>\n";
        print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

		print "<tr><td $align>$$lang_vars{password_message}</td><td $align1><input name=\"user_password\" value=\"$user_password\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
        print "<tr><td $align>$$lang_vars{new_password_message}</td><td $align1><input name=\"new_user_password\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
        print "<tr><td $align>$$lang_vars{repeat_new_password_message}</td><td $align1><input name=\"repeat_new_user_password\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";



        print "</table><p>\n";
        print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{update_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";
        print "<p>\n";

        print "<hr>\n";
	}

	print "<p>\n";



	print "<p><br><b>$$lang_vars{reset_user_password_message}</b>\n";
	print "<form name=\"reset_user_password_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_reset_user_password.cgi\">\n";
	print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{reset_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";

#	print "<hr>\n";
#
#	print "<p><br><b>$$lang_vars{delete_master_key_message}</b>\n";
#	print "<form name=\"delete_master_key_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_delete_master_key.cgi\">\n";
#	print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{borrar_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";
	print "<p><br><p><br><p><br>\n";

} else {

    print "<b>$$lang_vars{insert_master_key_message}</b><br>\n";
	print "<form name=\"insert_master_key_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_insert_master_key.cgi\"><input type=\"hidden\" value=\"$client_id\" name=\"client_id\"><br>\n";
	print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
	print "<tr><td $align>$$lang_vars{password_message}</td><td $align1><input name=\"user_password\" value=\"$user_password\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
	print "<tr><td $align>$$lang_vars{repeat_password_message}</td><td $align1><input name=\"repeat_user_password\" value=\"$user_password\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"15\" maxlength=\"50\"></td></tr>\n";
	print "<tr><td $align>$$lang_vars{master_key_message}</td><td $align1><input name=\"master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
	print "<tr><td $align>$$lang_vars{repeat_master_key_message}</td><td $align1><input name=\"repeat_master_key\" value=\"\" type=\"password\" class='form-control form-control-sm' style='width: 12em' size=\"30\" maxlength=\"200\"></td></tr>\n";
	print "</table><p>\n";
	print "<span style=\"float: $ori\"><br><p><input type=\"hidden\" value=\"$id\" name=\"id\"><input type=\"submit\" value=\"$$lang_vars{add_message}\" name=\"B2\" class=\"btn\"></form></span><br><p>\n";

	print "<p><br>\n";
	print "<b>$$lang_vars{mod_master_key_message}</b><br>\n";
	print "<p>$$lang_vars{no_master_key_defined_message}<p><br>\n";
	print "<p><br>\n";
	print "<b>$$lang_vars{delete_master_key_message}</b><br>\n";
	print "<p>$$lang_vars{no_master_key_defined_message}<p><br>\n";
	print "<p><br>\n";
}




print "<p>\n";

print "<script type=\"text/javascript\">\n";
	print "document.insert_master_key_form.user_password.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
