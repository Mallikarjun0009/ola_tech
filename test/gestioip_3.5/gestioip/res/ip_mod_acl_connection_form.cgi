#!/usr/bin/perl -w -T

use strict;
use Socket;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm,update_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{mod_acl_connection_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}

my $id=$daten{'id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $id;

my @values = $gip->get_acl_connections("$client_id", "$id");
my @protocols = $gip->get_protocols("$client_id");

my $acl_nr = $values[0]->[1] || 0;
my $purpose = $values[0]->[2] || "";
my $status = $values[0]->[3];
my $src_vlan = $values[0]->[4];
my $source = $values[0]->[5] || "";
my $src = $values[0]->[6] || "";
my $application_protocol = $values[0]->[7] || "";
my $protocol = $values[0]->[8] || "";
my $src_port = $values[0]->[9] || "";
my $bidirectional = $values[0]->[10] || "";
my $bidirectional_checked = "";
$bidirectional_checked = "checked" if $bidirectional;
my $dst_vlan = $values[0]->[11] || "";
my $destination = $values[0]->[12] || "";
my $dst = $values[0]->[13] || "";
my $encrypted_base_proto = $values[0]->[14] || "";
my $remark = $values[0]->[15] || "";

print "<p>\n";
print "<form name=\"mod_acl_connection_form\" method=\"POST\" action=\"./ip_mod_acl_connection.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

print "<tr><td $align>$$lang_vars{ACL_nr_message}</td><td $align1><input name=\"acl_nr\" type=\"text\" class='form-control form-control-sm m-2' style='width: 6em' value=\"$acl_nr\" size=\"5\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{purpose_message}</td><td $align1><input name=\"purpose\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$purpose\" size=\"60\" maxlength=\"500\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{status_message}</td><td $align1><input name=\"status\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$status\" size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{src_vlan_message}</td><td $align1><input name=\"src_vlan\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$src_vlan\" size=\"15\" maxlength=\"30\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{source_message}</td><td $align1><input name=\"source\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$source\"  size=\"60\" maxlength=\"250\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{src_ip_message}</td><td $align1><input name=\"src\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$src\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{application_protocol_message}</td><td $align1><input name=\"application_protocol\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$application_protocol\"  size=\"60\" maxlength=\"100\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{protocol_message}</td><td $align1><input name=\"protocol\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$protocol\"  size=\"15\" maxlength=\"50\"></td></tr>\n";


my @protocols_sorted = sort {$a->[2] cmp $b->[2]} @protocols;
my $j=0;
print "<tr><td $align>$$lang_vars{protocol_message}</td><td><select class=\"custom-select custom-select-sm m-2 display-inline\" name=\"protocol\" style='width: 12em' size=\"1\">\n";
print "<option></option>";
foreach (@protocols_sorted) {
	my $protocol_selected = "";
	if ( $protocol eq $protocols_sorted[$j]->[1] ) {
		$protocol_selected = "selected";
	}
    print "<option value=\"$protocols_sorted[$j]->[1]\" $protocol_selected>$protocols_sorted[$j]->[2]</option>";
    $j++;
}   
print "</select></td></tr>\n";


print "<tr><td $align>$$lang_vars{port_message}</td><td $align1><input name=\"src_port\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$src_port\"  size=\"60\" maxlength=\"500\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{bidirectional_message}</td><td $align1><input type=\"checkbox\" name=\"bidirectional\" value=\"X\" $bidirectional_checked></td></tr>\n";
print "<tr><td $align>$$lang_vars{dst_vlan_message}</td><td $align1><input name=\"dst_vlan\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$dst_vlan\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{destination_message}</td><td $align1><input name=\"destination\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$destination\"  size=\"60\" maxlength=\"250\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{dst_ip_message}</td><td $align1><input name=\"dst\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"$dst\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{base_proto_encrypt_message}</td><td $align1><input name=\"encrypted_base_proto\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$encrypted_base_proto\"  size=\"60\" maxlength=\"100\"></td></tr>\n";
print "<tr><td $align>$$lang_vars{remark_message}</td><td $align1><input name=\"remark\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"$remark\"  size=\"60\" maxlength=\"100\"></td></tr>\n";
print "<td><input type=\"hidden\" name=\"id\" value=\"$id\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><br><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"btn\"></td>\n";

print "</table>\n";
print "</form>\n";

print "<p><br><p><br><p>\n";

$gip->print_end("$client_id", "", "", "");

