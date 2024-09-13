#!/usr/bin/perl -T -w

# Copyright (C) 2015 Marc Uebel

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
use Net::IP;
use Net::IP qw(:PROC);
use lib '../modules';
use GestioIP;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);


$gip->{print_sitebar} = 1;
$gip->{uncheck_free_ranges} = 1;


my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page);
if ( $daten{'entries_per_page'} ) {
        $daten{'entries_per_page'} = "500" if $daten{'entries_per_page'} !~ /^\d{1,3}$/;
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("$daten{'entries_per_page'}","$lang");
} else {
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";

my $loc_check_id = "";
if ( $daten{new_redes} ) {
	my $new_redes_check = $daten{new_redes};
	my @new_redes_check = split('-',$daten{new_redes});
	my %new_redes_check_check;
	my $new_redes_count_check = @new_redes_check;
    for (my $l=0; $l <= $new_redes_count_check - 1; $l++) {
		my $loc_check_check = $daten{"loc_$l"} || "NULL";
		next if $new_redes_check_check{$loc_check_check};
		$new_redes_check_check{$loc_check_check}++;
		my $loc_id_check=$gip->get_loc_id("$client_id","$loc_check_check") || "-1";
		$loc_check_id .= '_' . $loc_id_check;
	}
	$loc_check_id =~ s/^_//;
} else {
	my $loc_check = $daten{'loc'};
    $loc_check_id=$gip->get_loc_id("$client_id","$loc_check") || "-1";
}

my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_net_perm,create_net_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
		loc_id_rw=>"$loc_check_id",

	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;

my $global_dyn_dns_updates_enabled=$global_config[0]->[19] || "";



my $ip_version = $daten{'ip_version'} || "v4";

my $global_ip_version=$global_config[0]->[5] || "v4";
my $ip_version_ele="";
if ( $global_ip_version ne "yes" ) {
	$ip_version_ele = $ip_version || "";
	if ( $daten{'ip_version_ele'} ) {
		$ip_version_ele = $daten{'ip_version_ele'} if ! $ip_version_ele;
	}
        if ( $ip_version_ele ) {
                $ip_version_ele = $gip->set_ip_version_ele("$ip_version_ele");
        } else {
                $ip_version_ele = $gip->get_ip_version_ele();
        }

} else {
	$ip_version_ele = "$ip_version";
}

my ($show_rootnet, $show_endnet, $hide_not_rooted, $local_filter_enabled);
$show_rootnet=$gip->get_show_rootnet_val() || "1";
$show_endnet=$gip->get_show_endnet_val() || "1";
$hide_not_rooted=$gip->get_hide_not_rooted_val() || "0";

my $local_filter=$global_config[0]->[16] || 0;
$local_filter=0 if $local_filter eq "no";
if ( $local_filter ) {
	$local_filter_enabled=$gip->get_local_filter_enabled_val() || 0;
}
$local_filter_enabled=0 if ! $local_filter_enabled;
$gip->{local_filter} = $local_filter || 0;

my $rootnet = $daten{'rootnet'} || "n";
my $rootnet_val = "0";
$rootnet_val = "1" if $rootnet eq "y";

my $dyn_dns_updates = $daten{'dyn_dns_updates'} || 1;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{crear_red_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if $ip_version !~ /(v4|v6)/; 
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if ( $global_dyn_dns_updates_enabled eq "yes" && $dyn_dns_updates !~ /^(1|2|3|4)$/ );

my $event_cc = "";
my @custom_columns = $gip->get_custom_columns("$client_id");
my $cc_anz=@custom_columns;
my %cc_mandatory_check_hash;

# prepare mandatory check
my $j=0;
foreach ( @custom_columns ) {
    my $column_name=$custom_columns[$j]->[0];
    my $mandatory=$custom_columns[$j]->[4];
	$cc_mandatory_check_hash{$column_name}++ if $mandatory;
    $j++;
}

my $dyn_dns_zone_name = "";
my $dyn_dns_ptr_zone_name = "";
for (my $o=0; $o<$cc_anz; $o++) {
    my $cc_name=$daten{"custom_${o}_name"} || "";
    my $cc_value=$daten{"custom_${o}_value"} || "";
    my $cc_id=$daten{"custom_${o}_id"} || "";
    if ( $cc_name eq "DNSZone" ) {
        $dyn_dns_zone_name = $cc_value;
    }
    if ( $cc_name eq "DNSPTRZone" ) {
        $dyn_dns_ptr_zone_name = $cc_value;
    }
    $event_cc .= ", " . $cc_value;

	# mandatory check
	if ( exists $cc_mandatory_check_hash{$cc_name} && ! $cc_value) {
        $gip->print_error("$client_id","$$lang_vars{mandatory_field_message}: $cc_name");
	}
}

if ( $global_dyn_dns_updates_enabled eq "yes" ) {
    $gip->print_error("$client_id","$$lang_vars{no_zone_message}") if ! $dyn_dns_zone_name && $dyn_dns_updates =~ /^[23]$/;
    $gip->print_error("$client_id","$$lang_vars{no_ptr_zone_message}") if ! $dyn_dns_ptr_zone_name && $dyn_dns_updates =~ /^[24]$/;
}



my $start_entry=$daten{'start_entry'} || '0';
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if $start_entry !~ /^\d{1,5}$/;
my $tipo_ele = $daten{'tipo_ele'} || "NULL";
my $loc_ele = $daten{'loc_ele'} || "NULL";
my $order_by = $daten{'order_by'} || "red_auf";

my ($new_redes, $new_redes_count);
my (@new_redes, @new_redes_detail);
my @new_networks_noti;
my %changed_red_num;
my $loc_hash=$gip->get_loc_hash("$client_id");


if ( $daten{new_redes} ) {
### MULTIPLE REDES
	if ( $ip_version eq "v4" ) {
		if ( $daten{new_redes} !~ /(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}-?)+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2})*$/ ) { $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") };
	} else {
#### TEST
#		$gip->check_valid_ipv6("$daten{new_redes}");
	}
	$new_redes = $daten{new_redes};
	@new_redes=split('-',$daten{new_redes});
	$new_redes_count = @new_redes;
    $new_redes_count--;

	for (my $l=0; $l <= $new_redes_count; $l++) {
		$new_redes_detail[$l]->[0] = $daten{"red_$l"};
		$new_redes_detail[$l]->[1] = $daten{"BM_$l"};
		$new_redes_detail[$l]->[2] = $daten{"descr_$l"} || "NULL";
		$new_redes_detail[$l]->[3] = $daten{"loc_$l"} || "NULL";
		$new_redes_detail[$l]->[4] = $daten{"cat_net_$l"} || "NULL";
		$new_redes_detail[$l]->[5] = $daten{"comentario_$l"} || "NULL";
		$new_redes_detail[$l]->[6] = $daten{"vigilada_$l"} || "n";

        my $loc_id_check = $loc_hash->{$daten{"loc_$l"}};
        my $loc_check = $daten{"loc_$l"};

        if ( $user_management_enabled eq "yes" ) {
            $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc_check", "$loc_id_check");
        }
	}

	my $m = "0";
	my $event;
	foreach my $ele (@new_redes_detail) {
        if ( ! $ele || ! $new_redes_detail[$m]->[0] ) { next; }

		my $red_nuevo=$new_redes_detail[$m]->[0];
		my $BM_nuevo=$new_redes_detail[$m]->[1];
		my $descr_nuevo = $new_redes_detail[$m]->[2] || "NULL";
		my $loc_nuevo = $new_redes_detail[$m]->[3] || "-1";
		my $loc_id_nuevo=$gip->get_loc_id("$client_id","$loc_nuevo") || "-1";
		my $cat_nuevo = $new_redes_detail[$m]->[4] || "-1";
		my $cat_id_nuevo=$gip->get_cat_net_id("$client_id","$cat_nuevo") || "-1";
		my $comentario_nuevo = $new_redes_detail[$m]->[5] || "NULL";
		my $vigilada_nuevo = $new_redes_detail[$m]->[6] || "n";

		my $redob = $red_nuevo . "/" . $BM_nuevo;
		my $ipob = new Net::IP ($redob) or $gip->print_error("$client_id","$$lang_vars{formato_malo_message}<b>$redob</b>");

		my $ignore_rootnet="1";
#		$rootnet_val=1 if $ip_version eq "v6" && $BM_nuevo < 64; 
		if ( $rootnet_val == 1 ) {
			$ignore_rootnet="0";
		}
		my $red_exists=$gip->check_red_exists("$client_id","$red_nuevo","$BM_nuevo","$ignore_rootnet");
		if ( $red_exists ) {
			$gip->print_error("$client_id","$$lang_vars{red_exists_message} $redob");
		}

		my @overlap_redes=$gip->get_overlap_red("$ip_version","$client_id");
		$red_nuevo = ip_expand_address ($red_nuevo,6) if $ip_version eq "v6";

		if ( $rootnet_val == 0 ) {

			# Check for overlapping networks
			if ( $overlap_redes[0]->[0] ) {
				my @overlap_found = $gip->find_overlap_redes("$client_id","$red_nuevo","$BM_nuevo",\@overlap_redes,"$ip_version",$vars_file);
				if ( $overlap_found[0] ) {
					$gip->print_error("$client_id","$red_nuevo/$BM_nuevo $$lang_vars{overlaps_con_message} $overlap_found[0]");
					next;
				}
			}
		} else {
			if ( $overlap_redes[0]->[0] ) {
				my @overlap_found = $gip->find_overlap_redes("$client_id","$red_nuevo","$BM_nuevo",\@overlap_redes,"$ip_version","$vars_file","","","1");
				my $check_bigger_bm="";
				foreach (@overlap_found) {
					$_ =~ /.+\/(\d{1,3})$/;
					my $overlap_bm_bigger_check = $1;
					if ( $overlap_bm_bigger_check < $BM_nuevo ) {
						$check_bigger_bm="true";
						last;
					}
				}
				if ( $check_bigger_bm ) {
					$gip->print_error("$client_id","$$lang_vars{rootnet_not_smaller_message}: $red_nuevo/$BM_nuevo -  $overlap_found[0]");
					next;
				}
			}
		}

#		my $red_id_nuevo=$gip->get_last_red_num("$client_id");
#		$red_id_nuevo++;
#		$gip->insert_net("$client_id","$red_id_nuevo","$red_nuevo","$BM_nuevo","$descr_nuevo","$loc_id_nuevo","$vigilada_nuevo","$comentario_nuevo","$cat_id_nuevo","$ip_version","$rootnet_val") or die $gip->print_error("$client_id");
		my $red_id_nuevo = $gip->insert_net("$client_id","$red_nuevo","$BM_nuevo","$descr_nuevo","$loc_id_nuevo","$vigilada_nuevo","$comentario_nuevo","$cat_id_nuevo","$ip_version","$rootnet_val") or die $gip->print_error("$client_id");
#		print "<p><b>$$lang_vars{redes_nuevos_done_message}</b><p>\n" if $m == "0";
#		print "$red_nuevo/$BM_nuevo</b><br>\n";
        push @new_networks_noti, "<b>$$lang_vars{redes_nuevos_done_message}</b><p>";
        push @new_networks_noti, "$red_nuevo/$BM_nuevo";

		#audit
		my $audit_type="17";
		my $audit_class="2";
		my $update_type_audit="1";
		$descr_nuevo = "---" if $descr_nuevo eq "NULL";
		$loc_nuevo = "---" if $loc_nuevo eq "NULL";
		$cat_nuevo = "---" if $cat_nuevo eq "NULL";
		$comentario_nuevo = "---" if $comentario_nuevo eq "NULL";
		$event = "$red_nuevo/$BM_nuevo,$descr_nuevo,$loc_nuevo,$cat_nuevo,$comentario_nuevo,$vigilada_nuevo" if $new_redes_detail[$m]->[0];
        $event .= $event_cc;
		$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

		$changed_red_num{$red_id_nuevo}=$red_id_nuevo;

        #update net usage
        $gip->update_net_usage_cc_column("$client_id", "$ip_version", "$red_id_nuevo","$BM_nuevo","no_rootnet") if $rootnet_val ne 1;

		$m++;
	}

} else {
## ONE NETWORKK

if ( $daten{'BM'} =~ /^(\d\d\d).*/ ) {
    $daten{'BM'} =~ /^(\d\d\d).*/;
    $daten{'BM'} = $1;
} elsif ( $daten{'BM'} =~ /^(\d\d).*/ ) {
    $daten{'BM'} =~ /^(\d\d).*/;
    $daten{'BM'} = $1;
} elsif ( $daten{'BM'} =~ /^(\d).*/ ) {
    $daten{'BM'} =~ /^(\d).*/;
    $daten{'BM'} = $1;
}

my $red = $daten{'red'}  || $gip->print_error("$client_id","$$lang_vars{introduce_red_id_message}");

$red =~ s/^\+*//;
$red =~ s/\s*$//;
my $BM = $daten{'BM'} || $gip->print_error("$client_id","$$lang_vars{introduce_BM_message}");
my $descr = $daten{'descr'} || $gip->print_error("$client_id","$$lang_vars{introduce_description_message}");
my $comentario = $daten{'comentario'} || "NULL";
my $vigilada = $daten{'vigilada'} || "n";

if ( $ip_version eq "v4" ) {
    $gip->CheckInIP("$client_id","$red","$$lang_vars{formato_red_malo_message} - $$lang_vars{comprueba_red_id_message}<br>");
} else {
    my $valid_v6 = $gip->check_valid_ipv6("$red") || "0";
    $gip->print_error("$client_id","$$lang_vars{'no_valid_ipv6_address_message'}: <b>$red</b>") if $valid_v6 != "1";
}

my ( $broad,$mask,$hosts) = $gip->get_red_nuevo("$client_id","$red","$BM","$vars_file");

my $check_exist_red = $red;
$check_exist_red= ip_expand_address ($red,6) if $ip_version eq "v6";
my $ignore_rootnet="1";
#	$rootnet_val=1 if $ip_version eq "v6" && $BM < 64; 
if ( $rootnet_val == 1 ) {
    $ignore_rootnet="0";
}
my $red_check=$gip->check_red_exists("$client_id","$check_exist_red","$BM","$ignore_rootnet");
if ( $red_check ) {
    $gip->print_error("$client_id","$$lang_vars{red_exists_message}: <b>$red</b>");
}

my $loc="";
my $cat_net="";
$loc = $daten{'loc'} || "";
if ( ! $loc && $rootnet_val == 0 ) {
    $gip->print_error("$client_id","$$lang_vars{introduce_loc_message}")
}
$cat_net = $daten{'cat_red'} || "";
if ( ! $cat_net && $rootnet_val == 0 ) {
    $gip->print_error("$client_id","$$lang_vars{cat_red_message}")
}
my $loc_id=$gip->get_loc_id("$client_id","$loc") || "-1";
my $cat_net_id=$gip->get_cat_net_id("$client_id","$cat_net") || "-1";

my $ip = new Net::IP ("$red/$BM") or $gip->print_error("$client_id","$$lang_vars{comprueba_red_BM_message}: <b>$red/$BM</b> (1)");

my @overlap_redes=$gip->get_overlap_red("$ip_version","$client_id");
$red = ip_expand_address ($red,6) if $ip_version eq "v6";

if ( $rootnet_val == 0 ) {

    # Check for overlapping networks
    if ( $overlap_redes[0]->[0] ) {
        my @overlap_found = $gip->find_overlap_redes("$client_id","$red","$BM",\@overlap_redes,"$ip_version",$vars_file);
        if ( $overlap_found[0] ) {
            $gip->print_error("$client_id","$red/$BM $$lang_vars{overlaps_con_message} $overlap_found[0]");
            next;
        }
    }
} else {
    if ( $overlap_redes[0]->[0] ) {
        my @overlap_found = $gip->find_overlap_redes("$client_id","$red","$BM",\@overlap_redes,"$ip_version",$vars_file,"","","1");
        my $check_bigger_bm="";
        foreach (@overlap_found) {
            $_ =~ /.+\/(\d{1,3})$/;
            my $overlap_bm_bigger_check = $1;
            if ( $overlap_bm_bigger_check < $BM ) {
                $check_bigger_bm="true";
                last;
            }
        }
        if ( $check_bigger_bm ) {
            $gip->print_error("$client_id","Rootnetworks can not be smaller then endnetworks: $red/$BM - $overlap_found[0]");
            next;
        }
    }
}

$red = ip_expand_address ($red,6) if $ip_version eq "v6";
my $new_red_num = $gip->insert_net("$client_id","$red","$BM","$descr","$loc_id","$vigilada","$comentario","$cat_net_id","$ip_version","$rootnet_val","$dyn_dns_updates") || "";

my %cc_value=$gip->get_custom_columns_id_from_net_id_hash("$client_id","$new_red_num");

$event_cc = "";
for (my $o=0; $o<$cc_anz; $o++) {
    my $cc_name=$daten{"custom_${o}_name"};
    my $cc_value=$daten{"custom_${o}_value"} || "";
    my $cc_id=$daten{"custom_${o}_id"};

    if ( $cc_value ) {
        $gip->insert_custom_column_value_red("$client_id","$cc_value{$cc_name}","$new_red_num","$cc_value");
    }

    $event_cc .= ", " . $cc_value;
}

my $tag = $daten{'tag'};
if ( $tag ) {
	my @new_tags = split("_", $tag);
	foreach (@new_tags) {
		my $id = $_;
		$gip->insert_tag_for_object ("$client_id", "$id", "$new_red_num", "network");
	}
}

my $scanazone = $daten{'scanazone'};
if ( $scanazone ) {
	my @new_scanazone = split("_", $scanazone);
	foreach (@new_scanazone) {
		my $id = $_;
		$gip->insert_scan_zone_for_object ("$client_id", "$id", "$new_red_num");
	}
}

my $scanptrzone = $daten{'scanptrzone'};
if ( $scanptrzone ) {
	my @new_scanptrzone = split("_", $scanptrzone);
	foreach (@new_scanptrzone) {
		my $id = $_;
		$gip->insert_scan_zone_for_object ("$client_id", "$id", "$new_red_num");
	}
}


my $audit_type="17";
my $audit_class="2";
my $update_type_audit="1";
$descr="---" if $descr eq "NULL";
$comentario="---" if $comentario eq "NULL";

my $event="$red/$BM,$descr,$loc,$cat_net,$comentario,$vigilada";
$event .= $event_cc;
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

$changed_red_num{$new_red_num}=$new_red_num;

#update net usage
$gip->update_net_usage_cc_column("$client_id", "$ip_version", "$new_red_num","$BM","no_rootnet") if $new_red_num && $rootnet_val ne 1;
}



my $tipo_ele_id= "-1";
my $loc_ele_id= "-1";

my @ip=$gip->get_redes("$client_id","$tipo_ele_id","$loc_ele_id","$start_entry","$entries_per_page","$order_by","$ip_version","$show_rootnet","$show_endnet","$hide_not_rooted","","$local_filter_enabled","$local_filter");

my $anz_values_redes = scalar(@ip);
my $pages_links=$gip->get_pages_links_red("$client_id","$vars_file","$start_entry","$anz_values_redes","$entries_per_page","$tipo_ele","$loc_ele","$order_by","","","$show_rootnet","$show_endnet","$hide_not_rooted");

my $ip=$gip->prepare_redes_array("$client_id",\@ip,"$order_by","$start_entry","$entries_per_page","$ip_version");

$gip->PrintRedTabHead("$client_id","$vars_file","$start_entry","$entries_per_page","$pages_links","$tipo_ele","$loc_ele","$ip_version","$show_rootnet","$show_endnet","$hide_not_rooted","","$local_filter_enabled");

if ( @ip ) {

my $noti;
foreach ( @new_networks_noti ) {
    $noti .= $_;
}



	$gip->PrintRedTab("$client_id",$ip,"$vars_file","simple","$start_entry","$tipo_ele","$loc_ele","$order_by","","$entries_per_page","$ip_version","$show_rootnet","$show_endnet",\%changed_red_num,"","$hide_not_rooted");

} else {
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
}


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
