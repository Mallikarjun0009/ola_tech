#!/usr/bin/perl -T -w

# Copyright (C) 2011 Marc Uebel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


use strict;
use lib '../modules';
use GestioIP;
use Net::IP qw(:PROC);
use Math::BigInt;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

$gip->{print_sitebar} = 1;

my $tag_request = "";
if ( $daten =~ /tag=/ ) {
	$tag_request = 1;
}
my $scanazone_request = "";
if ( $daten =~ /scanazone=/ ) {
	$scanazone_request = 1;
}
my $scanptrzone_request = "";
if ( $daten =~ /scanptrzone=/ ) {
	$scanptrzone_request = 1;
}

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page);
if ( $daten{'entries_per_page'} ) {
        $daten{'entries_per_page'} = "500" if $daten{'entries_per_page'} !~ /^\d{1,3}$/;
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("$daten{'entries_per_page'}","$lang");
} else {
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $loc=$daten{'loc'} || "";
my $loc_id=$gip->get_loc_id("$client_id","$loc") || "-1";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_net_perm,update_net_perm";
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



my $ip_version_ele = $daten{'ip_version_ele'} || ""; 


my ($show_rootnet, $show_endnet, $hide_not_rooted);
$show_rootnet=$gip->get_show_rootnet_val() || "1";
$show_endnet=$gip->get_show_endnet_val() || "1";
$hide_not_rooted=$gip->get_hide_not_rooted_val() || "0";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{network_mass_update_message}","$vars_file");

# Check SITE permission
if ( $user_management_enabled eq "yes" ) {
    $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc", "$loc_id");
}

my $mass_update_type=$daten{'mass_update_type'};
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if ! $mass_update_type;

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if ! $daten{'mass_update_network_ids'};
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if ($daten{'mass_update_network_ids'} !~ /[0-9_]/ );
my $mass_update_network_ids=$daten{"mass_update_network_ids"} || "";

if ( $daten{descr} ) {
	$gip->print_error("$client_id",$$lang_vars{max_signos_descr_message}) if length($daten{descr}) > 100;
}
if ( $daten{comentario} ) {
	$gip->print_error("$client_id",$$lang_vars{max_signos_comentario_message}) if length($daten{comentario}) > 500;
}

my $tipo_ele = $daten{'tipo_ele'} || "NULL";
my $loc_ele = $daten{'loc_ele'} || "NULL";
my $start_entry=$daten{'start_entry'} || '0';
my $order_by=$daten{'order_by'} || 'red_auf';
my $host_order_by=$daten{'host_order_by'} || 'IP_auf';
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (4)") if $start_entry !~ /^\d{1,5}$/;

my @mass_update_types=();
my $n=0;
my %cc_columns_all=$gip->get_custom_columns_hash_client_all("$client_id");
foreach my $cc_name( reverse sort keys %cc_columns_all ) {
    if ( $mass_update_type =~ /$cc_name/ ) {
        push @mass_update_types, $cc_name;
    }
    $n++;
}

my @mass_update_types_standard = split("_",$mass_update_type);


my $descr="";
my $cat_net="";
my $comentario="";
my $vigilada="";
my $cat_net_id="";
my $dyn_dns_updates="";
my $standard_column_update=0;
my $mass_update_loc_id="";

foreach my $mut (@mass_update_types_standard) {
	if ( $mut eq $$lang_vars{description_message} ) {
		$gip->print_error("$client_id","$$lang_vars{introduce_description_message}") if ( ! $daten{'descr'} );
		$gip->print_error("$client_id","$$lang_vars{palabra_reservada_comment_NULL_message}") if $daten{'descr'} eq "NULL";
		$descr=$daten{'descr'} || "NULL";
		$standard_column_update++;
	}
	if ( $mut =~ /^$$lang_vars{loc_message}$/ ) {
		$gip->print_error("$client_id","$$lang_vars{introduce_loc_message}") if ( ! $daten{'loc'} );
		$loc=$daten{'loc'} || "NULL";
		$mass_update_loc_id=$gip->get_loc_id("$client_id","$loc") || "";
		$standard_column_update++;
	}
	if ( $mut =~ /^$$lang_vars{cat_message}$/ ) {
		$gip->print_error("$client_id","$$lang_vars{cat_red_message}") if ( ! $daten{'cat_net'} );
		$cat_net=$daten{'cat_net'} || "NULL";
		$cat_net_id=$gip->get_cat_net_id("$client_id","$cat_net") || "-1";
		$standard_column_update++;
	}
	if ( $mut =~ /^$$lang_vars{comentario_message}$/ ) {
		$gip->print_error("$client_id","$$lang_vars{palabra_reservada_comment_NULL_message}") if $daten{'comentario'} eq "NULL";
		$comentario=$daten{'comentario'} || "NULL";
		$standard_column_update++;
	}
	if ( $mut =~ /^$$lang_vars{sinc_message}$/ ) {
		$vigilada=$daten{'vigilada'} || "n";
		$standard_column_update++;
	}
	if ( $mut =~ /^$$lang_vars{update_mode_message}$/ ) {
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (5)") if ( $daten{'dyn_dns_updates'} !~ /^(1|2|3|4)$/ );
        $dyn_dns_updates=$daten{'dyn_dns_updates'} || "";
		$standard_column_update++;
	}
}


my $cc_anz=$daten{'cc_anz'};
my ($cc_ele, $cc_table,$cc_table_fill);


my $tipo_ele_id=$gip->get_cat_net_id("$client_id","$tipo_ele") || "-1";
my $loc_ele_id=$gip->get_loc_id("$client_id","$loc_ele") || "-1";

if ( $mass_update_loc_id ) {
	$gip->mass_update_host_loc_id("$client_id","$mass_update_loc_id","$mass_update_network_ids");
}
if ( $standard_column_update > 0 ) {
	$gip->mass_update_redes("$client_id","$mass_update_network_ids","$descr","$mass_update_loc_id","$cat_net_id","$comentario","$vigilada","$dyn_dns_updates");
}

my %cc_value=$gip->get_custom_columns_hash_client_all("$client_id");
#my @custom_columns = $gip->get_custom_columns("$client_id");

my $cc_event="";
my $mass_update_type_cc_name;
my $mass_update_type_cc_name_value;
foreach (@mass_update_types) {
	$mass_update_type_cc_name=$_;
	$mass_update_type_cc_name_value=$mass_update_type_cc_name . "_value";
	if ( defined($daten{"$mass_update_type_cc_name_value"}) ) {
		$gip->mass_update_custom_column_value_red("$client_id","$cc_value{$mass_update_type_cc_name}","$mass_update_network_ids","$daten{$mass_update_type_cc_name_value}");
		$cc_event.="," if $cc_event;
		$cc_event.="$mass_update_type_cc_name:$daten{$mass_update_type_cc_name_value}";
	}
}

# TAGS

my $tag = $daten{'tag'};
if ( $tag ) {
	$gip->delete_tag_from_network_object_mass_update("$client_id", "$mass_update_network_ids");
	my @new_tags = split("_", $tag);
	foreach (@new_tags) {
		my $id = $_;
		$gip->insert_tag_for_network_object_mass_update ("$client_id", "$id", "$mass_update_network_ids");
	}
} elsif ( $tag_request && ! $tag ) {
	$gip->delete_tag_from_network_object_mass_update("$client_id", "$mass_update_network_ids");
}

# scanzones
my $scanazone = $daten{'scanazone'};
if ( $scanazone ) {
	$gip->delete_scan_zone_from_network_object_mass_update("$client_id", "$mass_update_network_ids", "A");
	my @new_zones = split("_", $scanazone);
	foreach (@new_zones) {
		my $id = $_;
		$gip->insert_scan_zone_for_network_object_mass_update ("$client_id", "$id", "$mass_update_network_ids");
	}
} elsif ( $scanazone_request && ! $scanazone ) {
	$gip->delete_scan_zone_from_network_object_mass_update("$client_id", "$mass_update_network_ids", "A");
}

my $scanptrzone = $daten{'scanptrzone'};
if ( $scanptrzone ) {
	$gip->delete_scan_zone_from_network_object_mass_update("$client_id", "$mass_update_network_ids", "PTR");
	my @new_zones = split("_", $scanptrzone);
	foreach (@new_zones) {
		my $id = $_;
		$gip->insert_scan_zone_for_network_object_mass_update ("$client_id", "$id", "$mass_update_network_ids");
	}
} elsif ( $scanptrzone_request && ! $scanptrzone ) {
	$gip->delete_scan_zone_from_network_object_mass_update("$client_id", "$mass_update_network_ids", "PTR");
}


my @networks_ips=$gip->get_mass_update_networks("$client_id","$mass_update_network_ids"); 
my $network_ips_string=join(",",@networks_ips);

my $descr_audit = $descr;
$descr_audit = "---" if $descr eq "NULL";
my $comentario_audit = $comentario;
$comentario_audit = "---" if $comentario eq "NULL";

my $audit_type="2";
my $audit_class="2";
my $update_type_audit="1";
my $event="mass update: $network_ips_string: $descr_audit,$loc,$cat_net,$comentario_audit,$vigilada,$dyn_dns_updates";
$event.="," . $cc_event;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

my %changed_red_num;
my @changed_red_num=split("_",$mass_update_network_ids);
foreach(@changed_red_num) {
	$changed_red_num{$_}=$_;
}

my @ip=$gip->get_redes("$client_id","$tipo_ele_id","$loc_ele_id","$start_entry","$entries_per_page","$order_by","$ip_version_ele","$show_rootnet","$show_endnet","$hide_not_rooted");
my $anz_values_redes = scalar(@ip);
my $ip=$gip->prepare_redes_array("$client_id",\@ip,"$order_by","$start_entry","$entries_per_page","$ip_version_ele");
my $pages_links=$gip->get_pages_links_red("$client_id","$vars_file","$start_entry","$anz_values_redes","$entries_per_page","$tipo_ele","$loc_ele","$order_by","","","$show_rootnet","$show_endnet","$hide_not_rooted");
$gip->PrintRedTabHead("$client_id","$vars_file","$start_entry","$entries_per_page","$pages_links","$tipo_ele","$loc_ele","$ip_version_ele","$show_rootnet","$show_endnet","$hide_not_rooted");
$gip->PrintRedTab("$client_id",$ip,"$vars_file","extended","$start_entry","$tipo_ele","$loc_ele","$order_by","","$entries_per_page","$ip_version_ele","$show_rootnet","$show_endnet",\%changed_red_num,"","$hide_not_rooted");

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
