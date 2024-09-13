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


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="update_vlan_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_vlan_perm_descr_message}","$vars_file");


my $vlan_id=$daten{'vlan_id'} || $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)");
my $vlan_num=$daten{'vlan_num'} || $gip->print_error("$client_id","$$lang_vars{insert_vlan_number_message} (2)");
my $vlan_name=$daten{'vlan_name'} || $gip->print_error("$client_id","$$lang_vars{insert_vlan_name_message} (3)");
my $comment=$daten{'comment'} || "";
my $vlan_provider_id=$daten{'vlan_provider_id'} || "-1";
my $bg_color=$daten{'bg_color'} || "";
my $font_color=$daten{'font_color'} || "";

if ( $vlan_num !~ /^\d+$/ ) {
        $gip->print_error("$client_id","$$lang_vars{vlan_numerical_message}")
}
if ( $vlan_num < 0 || $vlan_num > 4095 ) {
        $gip->print_error("$client_id","$$lang_vars{vlan_4095_message}")
}

if ( $font_color eq "amar" ) { $font_color="gold";
} elsif ( $font_color eq "azulcc" ) { $font_color="LightCyan";
} elsif ( $font_color eq "azulc" ) { $font_color="LightBlue";
} elsif ( $font_color eq "aculo" ) { $font_color="dodgerblue";
} elsif ( $font_color eq "verc" ) { $font_color="LimeGreen";
} elsif ( $font_color eq "vero" ) { $font_color="SeaGreen";
} elsif ( $font_color eq "pink" ) { $font_color="pink";
} elsif ( $font_color eq "blan" ) { $font_color="white";
} elsif ( $font_color eq "negr" ) { $font_color="black";
} elsif ( $font_color eq "maro" ) { $font_color="brown";
} elsif ( $font_color eq "rojo" ) { $font_color="red";
} elsif ( $font_color eq "orano" ) { $font_color="DarkOrange";
}


if ( $bg_color eq "amar" ) { $bg_color="gold";
} elsif ( $bg_color eq "azulcc" ) { $bg_color="LightCyan";
} elsif ( $bg_color eq "azulc" ) { $bg_color="LightBlue";
} elsif ( $bg_color eq "aculo" ) { $bg_color="dodgerblue";
} elsif ( $bg_color eq "verc" ) { $bg_color="LimeGreen";
} elsif ( $bg_color eq "vero" ) { $bg_color="SeaGreen";
} elsif ( $bg_color eq "pink" ) { $bg_color="pink";
} elsif ( $bg_color eq "blan" ) { $bg_color="white";
} elsif ( $bg_color eq "negr" ) { $bg_color="black";
} elsif ( $bg_color eq "maro" ) { $bg_color="brown";
} elsif ( $bg_color eq "rojo" ) { $bg_color="red";
} elsif ( $bg_color eq "orano" ) { $bg_color="DarkOrange";
}


print "</table>\n";
print "</td></tr></table>\n";

my @values_vlan=$gip->get_vlan("$client_id","$vlan_id");
my $old_vlan_num=$values_vlan[0]->[0];
my $old_vlan_name=$values_vlan[0]->[1];


$gip->update_vlan("$client_id","$vlan_id","$vlan_num","$vlan_name","$vlan_provider_id","$comment","$bg_color","$font_color");
$gip->update_cc_vlan_entry("$client_id","$old_vlan_num - $old_vlan_name","$vlan_num - $vlan_name");


my @new_provider = $gip->get_vlan_provider("$client_id","$vlan_provider_id");
$new_provider[0]->[0] = "---" if $vlan_provider_id == "-1";
$values_vlan[0]->[2] = "---" if ! $values_vlan[0]->[2];
$values_vlan[0]->[8] = "---" if ! $values_vlan[0]->[8];
$comment = "---" if ! $comment;
my $audit_type="38";
my $audit_class="7";
my $update_type_audit="1";
my $event1="$values_vlan[0]->[0], $values_vlan[0]->[1] ,$values_vlan[0]->[2] ,$values_vlan[0]->[8]";
my $event2="$vlan_num, $vlan_name, $comment, $new_provider[0]->[0]";
my $event = $event1 . " -> " . $event2;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


#print "<b>$$lang_vars{vlan_modificado_message} \"$vlan_num - $vlan_name\"</b><p>\n";
my $div_notify = GipTemplate::create_div_notify_text(
	noti => "$$lang_vars{vlan_modificado_message} \"$vlan_num - $vlan_name\"",
);
print "$div_notify\n";

my @vlans=$gip->get_vlans("$client_id");

if ( $vlans[0] ) {
        $gip->PrintVLANTab("$client_id",\@vlans,"show_ip.cgi","detalles","$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}

$gip->print_end("$client_id", "", "", "");

