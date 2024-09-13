#!/usr/bin/perl -w -T

use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $loc_id=$daten{'loc_id'} || "-1";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_line_perm,update_line_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
        loc_id_rw=>"$loc_id",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my $phone_number=$daten{'phone_number'} || "";
my $ad_number=$daten{'ad_number'} || "";
my $ll_id=$daten{'ll_id'} || "";
if ( ! $ll_id ) { 
    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");
    $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)");
}
$phone_number = $gip->remove_whitespace_se("$phone_number");
$ad_number = $gip->remove_whitespace_se("$ad_number");

my @line_arr = $gip->get_ll_from_phone_number_and_as_number("$client_id","$phone_number","$ad_number");
my $line_id = $line_arr[0]->[0] || ""; 
if ( $line_id && $line_id != $ll_id ) { 
    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");
    $gip->print_error("$client_id","$phone_number/$ad_number - $$lang_vars{ll_exists_message}");
} 

#if ( ! $phone_number ) {
#        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message} (1)","$vars_file");
#        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)")
#}
#
#if ( $phone_number !~ /^\d{1,10}/ ) {
#        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{formato_malo_message} (2)","$vars_file");
#        $gip->print_error("$client_id","$$lang_vars{edit_ll_message}")
#}



my @line_columns=$gip->get_line_columns("$client_id");
my %values_lines_cc=$gip->get_line_column_values_hash("$client_id"); # $values{"${column_id}_${ll_id}"}="$entry";
my @cc_entries;
my @cc_entries_db;

my $comment=$daten{'comment'} || "";
my $description=$daten{'description'} || "";
my $ll_client_id=$daten{'ll_client_id'} || "-1";
my $type=$daten{'type'} || "";
my $service=$daten{'service'} || "";
my $device=$daten{'device'} || "";
my $room=$daten{'room'} || "";


my @values_ll=$gip->get_one_ll("$client_id","$ll_id");
my @value_ll_client=$gip->get_one_ll_client("$client_id","$ll_client_id");
my $loc=$gip->get_loc_from_id("$client_id","$loc_id") || "";

my $ll_client=$value_ll_client[0]->[1];

# mandatory check

my $j=0;
foreach ( @line_columns ) {

    my $column_id=$line_columns[$j]->[0];
    my $column_name=$line_columns[$j]->[1];
    my $mandatory=$line_columns[$j]->[2];

    my $entry=$daten{"$column_name"} || "";

    if ( $mandatory && ! $entry ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $column_name");
    }

    $j++;
}

my $mandatory_check_fail = "";
if ( ! $type ) {
    $mandatory_check_fail = $$lang_vars{tipo_message};
} elsif ( ! $ad_number ) {
    $mandatory_check_fail = $$lang_vars{ad_number_message};
} elsif ( ! $loc_id || $loc_id == "-1" ) {
    $mandatory_check_fail = $$lang_vars{loc_message};
} elsif ( ! $ll_client_id ) {
    $mandatory_check_fail = $$lang_vars{ll_client_message};
}

if ( $mandatory_check_fail ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $mandatory_check_fail");
}


### host check

my $host_id = "";
my $host_ip ="";
my $ip_version = "";
my $ip_int = "";
my $red_num = "";
if ( $device && $device =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
	$ip_version = "v4";

    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{line_updated_message}","$vars_file");
    $ip_int = $gip->ip_to_int("$client_id","$device","$ip_version");
    $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_int") || "";
    $host_ip = $device if $host_id;

} elsif ( $device && $device =~ /:/ ) {
	$ip_version = "v6";
    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{line_updated_message}","$vars_file");
    $ip_int = $gip->ip_to_int("$client_id","$device","$ip_version");
    $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_int") || "";
    $host_ip = $device if $host_id;

} elsif ( $device ) {
    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");
    my $ips=$gip->get_host_ip_int_from_hostname_all("$client_id","$device") || "";
    my @ips = @$ips;
    if ( scalar(@ips) > 1 ) {
		print "<br><p><b>$$lang_vars{hostname_ambigous_message}: <i>$device</i></b><p>$$lang_vars{host_asso_line_message}<p>\n";
        print "<form name=\"select_host_form\" method=\"POST\" action=\"./ip_insert_ll.cgi\">\n";
        print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

        foreach (@ips) {
            my $ip_int = $_->[0];
            my $ip_version = $_->[2];
            my $ip = $gip->int_to_ip("$client_id","$ip_int","$ip_version");

            print "<tr><td>$ip</td><td><input type=\"radio\" name=\"device\" value=\"$ip\"></td><tr>\n";
        }
        print "<tr><td><br></td></tr>\n";
        print "<tr><td><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"input_link_w\"></td><tr>\n";
        print "</table>\n";
        print "<input type=\"hidden\" name=\"comment\" value=\"$comment\">\n";
        print "<input type=\"hidden\" name=\"loc_id\" value=\"$loc_id\">\n";
        print "<input type=\"hidden\" name=\"ll_client_id\" value=\"$ll_client_id\">\n";
        print "<input type=\"hidden\" name=\"descripiton\" value=\"$description\">\n";
        print "<input type=\"hidden\" name=\"type\" value=\"$type\">\n";
        print "<input type=\"hidden\" name=\"service\" value=\"$service\">\n";
        print "<input type=\"hidden\" name=\"room\" value=\"$room\">\n";
        print "<input type=\"hidden\" name=\"ad_number\" value=\"$ad_number\">\n";
        print "<input type=\"hidden\" name=\"client_id\" value=\"$client_id\">\n";
		$j=0;
		foreach ( @line_columns ) {

			my $column_id=$line_columns[$j]->[0];
			my $column_name=$line_columns[$j]->[1];

			my $entry=$daten{"$column_name"} || "";
			$entry=$gip->remove_whitespace_se("$entry");
			print "<input type=\"hidden\" name=\"$column_name\" value=\"$entry\">\n";
			$j++;
		}

        print "</form>\n";


        $gip->print_end("$client_id","$vars_file","", "$daten");
    } elsif ( $ips[0] ) {
        $ip_int = $ips[0]->[0];
        $ip_version = $ips[0]->[2];
        $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_int") || "";
        $host_ip = $gip->int_to_ip("$client_id","$ip_int","$ip_version");
    }
} else {
    $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{parameter_changed_message}","$vars_file")  if ! $device;
}

if ( $device && ! $host_id ) {

    print "<br><p><b>$$lang_vars{host_not_found_message}: <i>$device</i></b><br>\n";

	if ( $device !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ && $device !~ /:/  ) {
        # hostname given

        print "<p><br>$$lang_vars{create_host_now_message}\n";

        print_mod_ip_form("text");

		print "<p><br><p><br><span style=\"float: left\"><FORM style=\"float: left\"><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM></span>\n";
		$gip->print_end("$client_id","$vars_file","", "$daten");
	}


    my $error;
    ($red_num, $error) = $gip->get_host_network(
        ip         => "$device",
        ip_int     => "$ip_int",
        ip_version => "$ip_version",
        client_id => "$client_id",
        vars_file => "$vars_file",
    );

    if ( ! $red_num ) {
        print "<p>$error<p>\n";
		print "<p><br><p><br><span style=\"float: left\"><FORM style=\"float: left\"><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM></span>\n";
		$gip->print_end("$client_id","$vars_file","", "$daten");
    }

    print "<p><br>$$lang_vars{create_host_now_message}\n";

    print_mod_ip_form("");

    print "<br>$$lang_vars{or_go_message}<br>\n";

    print "<br><span style=\"float: left\"><FORM style=\"float: left\"><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM></span>\n";
	$gip->print_end("$client_id","$vars_file","", "$daten");
}

$gip->print_error("$client_id","$$lang_vars{device_no_ip_message}") if $device && ! $host_ip;

### host check end


$gip->update_ll("$client_id","$ll_id","$comment","$description","$ll_client_id","$loc_id","$type","$service","$host_ip","$room","$phone_number","$ad_number");
#$gip->update_ll("$client_id","$ll_id","$comment","$description","$ll_client_id","$loc_id","$type","$service","$device","$room","$phone_number","$ad_number");

### update host Line column

if ( $host_id ) {
    my %predef_host_columns=$gip->get_predef_host_column_all_hash("$client_id");
    my $pc_id = $predef_host_columns{'Line'}[0] || "";
    my @host_cc_id = $gip->get_custom_host_column_ids_from_name( "$client_id", "Line" );
    my $host_cc_id = $host_cc_id[0]->[0] || "";

    my $host_line_entry = $gip->get_custom_host_column_entry("$client_id","$host_id","Line","$pc_id") || "";

    if  ( $host_line_entry ) {
        $gip->update_custom_host_column_value_host("$client_id","$host_cc_id","$pc_id","$host_id","$ll_id") if $host_cc_id;
    } else {
        $gip->insert_custom_host_column_value_host("$client_id","$host_cc_id","-1","$host_id","$ll_id") if $host_cc_id;
    }
}

my @line_columns_new = @line_columns;
$j=0;
foreach ( @line_columns ) {

    my $column_id=$line_columns[$j]->[0];
    my $column_name=$line_columns[$j]->[1];
    my $mandatory=$line_columns[$j]->[2];

    my $entry=$daten{"$column_name"} || "";

    $entry=$gip->remove_whitespace_se("$entry");
    push @cc_entries,"$entry";

    my $entry_db=$values_lines_cc{"${column_id}_${ll_id}"} || "";
    push @cc_entries_db,"$entry_db";

    if ( $entry_db && ! $entry ) {
        $gip->delete_line_column_entry("$client_id","$column_id","$ll_id" );
    } elsif ( $entry_db ) {
        $gip->update_line_column_entry("$client_id","$column_id","$ll_id","$entry" );
    } else {
        $gip->insert_line_column_entry("$client_id","$column_id","$ll_id","$entry" );
    }

    $j++;
}

@line_columns = @line_columns_new;

my $old_description=$values_ll[0]->[2] || "---";
my $old_comment=$values_ll[0]->[3] || "---";
my $old_ll_client=$values_ll[0]->[5] || "---";
my $old_loc=$values_ll[0]->[9] || "---";
my $old_type=$values_ll[0]->[10] || "---";
my $old_service=$values_ll[0]->[11] || "---";
my $old_device=$values_ll[0]->[12] || "---";
my $old_room=$values_ll[0]->[13] || "---";
my $old_ad_number=$values_ll[0]->[14] || "---";
$old_ll_client="---" if $old_ll_client eq "_DEFAULT_";
$ll_client="---" if $ll_client eq "_DEFAULT_";
$loc="---" if $loc eq "NULL";
$type="---" if ! $type;
$service="---" if ! $service;
$device="---" if ! $device;
$room="---" if ! $room;
$ad_number="---" if ! $ad_number;

my $audit_type="55";
my $audit_class="13";
my $update_type_audit="1";
my $event1="$old_comment, $old_description, $old_ll_client, $old_loc, $old_type, $old_service, $old_device, $old_room, $old_ad_number";
foreach ( @cc_entries_db ) {
    $event1 .= ", " . $_;
}

my $event2="$comment, $description, $ll_client, $loc, $type, $service, $device, $room, $ad_number";
foreach ( @cc_entries ) {
    $event2 .= ", " . $_;
}

my $event = "LL $phone_number: " . $event1 . " -> " . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


print "<p>\n";

my %changed_id;
$changed_id{$ll_id}=$ll_id;
$gip->PrintLLTab("$client_id", "$vars_file", "", "", "", "", \%changed_id);

$gip->print_end("$client_id", "", "", "");


sub print_mod_ip_form {
    my ( $ip_text_field ) = @_;

    print "<form name=\"select_host_form\" method=\"POST\" action=\"./ip_modip_form.cgi\">\n";
    print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";

    if ( $ip_text_field ) {
        print "<tr><td>$$lang_vars{ip_address_message}</td><td><input name=\"line_ip\" type=\"text\" size=\"39\" maxlength=\"39\">\n";
        print "<tr><td><br></td><td>\n";
    }

    print "<tr><td colspan=\"2\" align=\"left\"><input type=\"submit\" value=\"$$lang_vars{create_message}\" name=\"B2\" class=\"input_link_w\"></td><tr>\n";
    print "</table>\n";
    print "<input type=\"hidden\" name=\"line_phone_number\" value=\"$phone_number\">\n";
    print "<input type=\"hidden\" name=\"line_comment\" value=\"$comment\">\n";
    print "<input type=\"hidden\" name=\"line_loc_id\" value=\"$loc_id\">\n";
    print "<input type=\"hidden\" name=\"ll_client_id\" value=\"$ll_client_id\">\n";
    print "<input type=\"hidden\" name=\"line_description\" value=\"$description\">\n";
    print "<input type=\"hidden\" name=\"line_type\" value=\"$type\">\n";
    print "<input type=\"hidden\" name=\"line_service\" value=\"$service\">\n";
    print "<input type=\"hidden\" name=\"line_room\" value=\"$room\">\n";
    print "<input type=\"hidden\" name=\"line_device\" value=\"$device\">\n";
    print "<input type=\"hidden\" name=\"line_ad_number\" value=\"$ad_number\">\n";
    print "<input type=\"hidden\" name=\"client_id\" value=\"$client_id\">\n";
    print "<input type=\"hidden\" name=\"from_line\" value=\"mod\">\n";
    print "<input type=\"hidden\" name=\"ip\" value=\"$ip_int\">\n";
    print "<input type=\"hidden\" name=\"ip_version\" value=\"$ip_version\">\n";
    print "<input type=\"hidden\" name=\"red_num\" value=\"$red_num\">\n";
    print "<input type=\"hidden\" name=\"hostname_line\" value=\"$device\">\n" if $ip_text_field;
    print "<input type=\"hidden\" name=\"ll_id\" value=\"$ll_id\">\n";

    $j=0;
    foreach ( @line_columns ) {

        my $column_id=$line_columns[$j]->[0];
        my $column_name=$line_columns[$j]->[1];

        my $entry=$daten{"$column_name"} || "";
        $entry=$gip->remove_whitespace_se("$entry");
        print "<input type=\"hidden\" name=\"$column_name\" value=\"$entry\">\n";
        $j++;
    }

    print "</form>\n";
}
