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

my $mass_update_type=$daten{'mass_update_type'};
$gip->print_error("$client_id","$$lang_vars{select_mass_update_type}") if ! $mass_update_type;
my @mass_update_types_standard = split("_",$mass_update_type);

my $id_string = "";
my $anz_entries = $daten{'anz_entries'} || "";
my $k;
if ( $anz_entries ) {
	for ($k=0;$k<=$anz_entries;$k++) {
		my $mu_id = "mass_update_acl_submit_${k}";
		my $id = $daten{$mu_id} || "";
		$id_string .= ",$id" if $id;
	}
	$id_string =~ s/^,//;
}

if ( ! $id_string ) {
    $gip->print_error("$client_id","No ACL IDs found")
}

my @protocols = $gip->get_protocols("$client_id");

print "<p>\n";
print "<form name=\"mod_acl_connection_form\" method=\"POST\" action=\"./ip_mod_acl_connection_mass_update.cgi\">\n";
print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";


foreach (@mass_update_types_standard) {
    if ( $_ eq $$lang_vars{ACL_nr_message} ) {
		print "<tr><td $align>$$lang_vars{ACL_nr_message}</td><td $align1><input name=\"acl_nr\" type=\"text\" class='form-control form-control-sm m-2' style='width: 6em' value=\"\" size=\"5\" maxlength=\"50\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{purpose_message} ) {
print "<tr><td $align>$$lang_vars{purpose_message}</td><td $align1><input name=\"purpose\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\" size=\"60\" maxlength=\"500\"></td></tr>\n";

    } elsif ( $_ eq $$lang_vars{status_message} ) {
		print "<tr><td $align>$$lang_vars{status_message}</td><td $align1><input name=\"status\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"\" size=\"15\" maxlength=\"50\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{src_vlan_message} ) {
		print "<tr><td $align>$$lang_vars{src_vlan_message}</td><td $align1><input name=\"src_vlan\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"\" size=\"15\" maxlength=\"30\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{source_message} ) {
		print "<tr><td $align>$$lang_vars{source_message}</td><td $align1><input name=\"source\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"250\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{src_ip_message} ) {
		print "<tr><td $align>$$lang_vars{src_ip_message}</td><td $align1><input name=\"src\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{application_protocol_message} ) {
		print "<tr><td $align>$$lang_vars{application_protocol_message}</td><td $align1><input name=\"application_protocol\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"100\"></td></tr>\n";

    } elsif ( $_ eq $$lang_vars{protocol_message} ) {
		my @protocols_sorted = sort {$a->[2] cmp $b->[2]} @protocols;
		my $j=0;
		print "<tr><td $align>$$lang_vars{protocol_message}</td><td><select class=\"custom-select custom-select-sm m-2 display-inline\" name=\"protocol\" size=\"1\">\n";
		print "<option></option>";
		foreach (@protocols_sorted) {
			print "<option value=\"$protocols_sorted[$j]->[1]\">$protocols_sorted[$j]->[2]</option>";
			$j++;
		}   
		print "</select></td></tr>\n";


    } elsif ( $_ eq $$lang_vars{port_message} ) {
		print "<tr><td $align>$$lang_vars{port_message}</td><td $align1><input name=\"src_port\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"500\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{bidirectional_message} ) {
		print "<tr><td $align>$$lang_vars{bidirectional_message}</td><td $align1><input type=\"checkbox\" name=\"bidirectional\" value=\"X\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{dst_vlan_message} ) {
		print "<tr><td $align>$$lang_vars{dst_vlan_message}</td><td $align1><input name=\"dst_vlan\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{destination_message} ) {
		print "<tr><td $align>$$lang_vars{destination_message}</td><td $align1><input name=\"destination\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"250\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{dst_ip_message} ) {
		print "<tr><td $align>$$lang_vars{dst_ip_message}</td><td $align1><input name=\"dst\" type=\"text\" class='form-control form-control-sm m-2' style='width: 12em' value=\"\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{base_proto_encrypt_message} ) {
		print "<tr><td $align>$$lang_vars{base_proto_encrypt_message}</td><td $align1><input name=\"encrypted_base_proto\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"100\"></td></tr>\n";
    } elsif ( $_ eq $$lang_vars{remark_message} ) {
		print "<tr><td $align>$$lang_vars{remark_message}</td><td $align1><input name=\"remark\" type=\"text\" class='form-control form-control-sm m-2' style='width: 35em' value=\"\"  size=\"60\" maxlength=\"100\"></td></tr>\n";
	}
}
print "<td><input type=\"hidden\" name=\"mass_update_type\" value=\"$mass_update_type\"><input type=\"hidden\" name=\"mass_update_acls\" value=\"$id_string\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><br><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"btn\"></td>\n";

print "</table>\n";
print "</form>\n";

print "<p><br><p><br><p>\n";

$gip->print_end("$client_id", "", "", "");

