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
	my $required_perms="read_vlan_perm,create_vlan_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $vlan_name=$daten{'vlan_name'};
my $vlan_num=$daten{'vlan_num'};
$daten{'vlan_num'}=~s/^\s+//;
$daten{'vlan_num'}=~s/\s+$//;

if ( ! $vlan_num ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{insert_vlan_number_message}")
}

if ( $vlan_num !~ /^\d+$/ ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{vlan_numerical_message}")
}
if ( $vlan_num < 0 || $vlan_num > 4095 ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{vlan_4095_message}")
}

if ( ! $vlan_name ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{insert_vlan_name_message}")
}

# delete whitespace waste from vlan_name

$vlan_name=~s/^\s*//;
$vlan_name=~s/\s*$//;
$vlan_name=~s/\s+/ /g;

##### pruefen, ob der VLAN name oder VLAN number schon vergeben ist

my @vlans=$gip->get_vlans_with_asso_vlans("$client_id");
foreach ( @vlans ) {
	if ( $_->[1] eq $vlan_num && $_->[2] eq $vlan_name ) {
		$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{add_vlan_message}","$vars_file");
		$gip->print_error("$client_id","$vlan_num ($vlan_name) - $$lang_vars{vlan_name_exists_message}");
	}
}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{vlan_added_message}: \"$vlan_num - $vlan_name\"","$vars_file");


my $comment=$daten{'comment'};
$gip->print_error("$client_id","$$lang_vars{check_vlan_number_message}") if $daten{'vlan_num'} !~ /^\d{1,10}$/;
my $vlan_provider_id=$daten{'vlan_provider_id'} || '-1';
my $switches=$daten{'switches'};
my $font_color=$daten{'font_color'} || "black";
my $bg_color=$daten{'bg_color'} || "white";


if ( $font_color eq "amar" ) { $font_color="gold";
} elsif ( $font_color eq "azulc" ) { $font_color="LightBlue";
} elsif ( $font_color eq "aculo" ) { $font_color="dodgerblue";
} elsif ( $font_color eq "verc" ) { $font_color="LimeGreen";
} elsif ( $font_color eq "vero" ) { $font_color="SeaGreen";
#} elsif ( $font_color eq "vero" ) { $font_color="DarkSeaGreen";
} elsif ( $font_color eq "pink" ) { $font_color="pink";
} elsif ( $font_color eq "blan" ) { $font_color="white";
} elsif ( $font_color eq "negr" ) { $font_color="black";
} elsif ( $font_color eq "maro" ) { $font_color="brown";
} elsif ( $font_color eq "rojo" ) { $font_color="red";
} elsif ( $font_color eq "orano" ) { $font_color="DarkOrange";
}

if ( $bg_color eq "amar" ) { $bg_color="gold";
} elsif ( $bg_color eq "azulc" ) { $bg_color="LightBlue";
} elsif ( $bg_color eq "aculo" ) { $bg_color="dodgerblue";
} elsif ( $bg_color eq "verc" ) { $bg_color="LimeGreen";
} elsif ( $font_color eq "vero" ) { $font_color="SeaGreen";
#} elsif ( $bg_color eq "vero" ) { $bg_color="DarkSeaGreen";
} elsif ( $bg_color eq "pink" ) { $bg_color="pink";
} elsif ( $bg_color eq "blan" ) { $bg_color="white";
} elsif ( $bg_color eq "negr" ) { $bg_color="black";
} elsif ( $bg_color eq "maro" ) { $bg_color="brown";
} elsif ( $bg_color eq "rojo" ) { $bg_color="red";
} elsif ( $bg_color eq "orano" ) { $bg_color="DarkOrange";
}


##### vlan in datenbank einstellen

$gip->insert_vlan("$client_id","$vlan_num","$vlan_name","$comment","$vlan_provider_id","$font_color","$bg_color","");


my $audit_type="36";
my $audit_class="7";
my $update_type_audit="1";
my $event="$vlan_num,$vlan_name";
$event=$event . "," .  $comment if $comment;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


@vlans=$gip->get_vlans("$client_id");
if ( $vlans[0] ) {
        $gip->PrintVLANTab("$client_id",\@vlans,"show_ip.cgi","detalles","$vars_file");
} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}


$gip->print_end("$client_id","$vars_file","", "$daten");

