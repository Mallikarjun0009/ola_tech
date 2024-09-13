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
use DBI;
use lib './modules';
use GestioIP;
#use GD::Graph::pie;
#use CGI ':standard';

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $base_uri = $gip->get_base_uri();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

$gip->{client_id} = $client_id;
$gip->{vars_file} = $vars_file;

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_net_perm,read_host_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $client_name = $gip->get_client_from_id("$client_id");

#my $ip_version_ele=$gip->get_ip_version_ele() || "v4";
my $client_name_head="$client_name -";
$client_name_head="" if $client_name eq "DEFAULT";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$client_name_head $$lang_vars{statistics_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $ipv4_only_mode=$global_config[0]->[5] || "yes";

my @used_vendors4 = $gip->get_used_vendor_array("$client_id","v4");
my @used_vendors6 = $gip->get_used_vendor_array("$client_id","v6");

my $i=0;
my %counts_vendors4 = ();
my %counts_vendors4_lc = ();
for (@used_vendors4) {
	$counts_vendors4_lc{lc($used_vendors4[$i]->[0])}++;
	$counts_vendors4{ucfirst(lc($used_vendors4[$i++]->[0]))}++;
}

$i=0;
my %counts_vendors6 = ();
my %counts_vendors6_lc = ();
for (@used_vendors6) {
	$counts_vendors6_lc{lc($used_vendors6[$i]->[0])}++;
	$counts_vendors6{ucfirst(lc($used_vendors6[$i++]->[0]))}++;
}

my $anz_red_all=$gip->count_red_entries_all("$client_id","NULL","NULL");
my $anz_red_all4=$gip->count_red_entries_all("$client_id","NULL","NULL","","v4");
my $anz_host_all=$gip->count_all_host_entries("$client_id");
my $anz_host_all4=$gip->count_all_host_entries("$client_id","","v4");
my $anz_vlans=$gip->count_all_vlan_entries("$client_id");

my @stat_net_cats4 = $gip->get_stat_net_cats("$client_id","v4");
my @stat_net_locs4 = $gip->get_stat_net_locs("$client_id","v4");

my @stat_net_cats6=();
my @stat_net_locs6=();
my ($anz_red_all6,$anz_host_all6);
if ( $ipv4_only_mode ne "yes" ) {
	@stat_net_cats6 = $gip->get_stat_net_cats("$client_id","v6");
	@stat_net_locs6 = $gip->get_stat_net_locs("$client_id","v6");
	$anz_red_all6=$gip->count_red_entries_all("$client_id","NULL","NULL","","v6");
	$anz_host_all6=$gip->count_all_host_entries("$client_id","","v6");
}

my ( $charts_data_net_cats4, $charts_data_net_cats6, $charts_data_net_sites4, $charts_data_net_sites6);
$charts_data_net_cats4=$charts_data_net_cats6=$charts_data_net_sites4=$charts_data_net_sites6="";
my ( $charts_data_host_cats4, $charts_data_host_cats6, $charts_data_host_sites4, $charts_data_host_sites6, $charts_data_host_vendor4, $charts_data_host_vendor6);
$charts_data_host_cats4=$charts_data_host_cats6=$charts_data_host_sites4=$charts_data_host_sites6=$charts_data_host_vendor4=$charts_data_host_vendor6="";

my $content = "";
my $host_net_cats_count4;
my %counts_4 = ();
if ( $stat_net_cats4[0] ) {
	$i=0;
	for (@stat_net_cats4) {
		$counts_4{$stat_net_cats4[$i++]->[0]}++;
	}

	$host_net_cats_count4 = $gip->create_stat_pie_chart(\%counts_4,"cat","networks4_by_cat","v4","$client_id","$vars_file","$$lang_vars{networks4_by_cat_message}");

	$charts_data_net_cats4 = $gip->create_stat_pie_chart_data(
		counts => \%counts_4,
		type => "cat",
		im_name => "networks4_by_cat",
		im_title => $$lang_vars{networks4_by_cat_message},
	);
}

my $m;

my %counts_6 = ();
my $host_net_cats_count6;
my $host_net_cats_im_name6="networks6_by_cat";
if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_net_cats6[0] ) {
		$i=0;
		for (@stat_net_cats6) {
			$counts_6{$stat_net_cats6[$i++]->[0]}++;
		}
		$host_net_cats_count6 = $gip->create_stat_pie_chart(\%counts_6,"cat","networks6_by_cat","v6","$client_id","$vars_file","$$lang_vars{networks6_by_cat_message}");

        $charts_data_net_cats6 = $gip->create_stat_pie_chart_data(
            counts => \%counts_6,
            type => "cat",
            im_name => "networks4_by_cat",
            im_title => $$lang_vars{networks6_by_cat_message},
        );
	}
}


my %counts1_4 = ();
my $host_net_locs_count4;
my $host_net_locs_im_name4 = "networks4_by_site";
if ( $stat_net_locs4[0] ) {
	$i=0;
	for (@stat_net_locs4) {
		$counts1_4{$stat_net_locs4[$i++]->[0]}++;
	}
	$host_net_locs_count4 = $gip->create_stat_pie_chart(\%counts1_4,"loc","networks4_by_site","v4","$client_id","$vars_file","$$lang_vars{networks4_by_site_message}");

	$charts_data_net_sites4 = $gip->create_stat_pie_chart_data(
		counts => \%counts1_4,
		type => "loc",
		im_name => "networks4_by_site",
		im_title => $$lang_vars{networks4_by_site_message},
	);
}


my %counts1_6 = ();
my $host_net_locs_count6;
my $host_net_locs_im_name6 = "networks6_by_site";
if ( $ipv4_only_mode ne "yes" ) {
	$i=0;
	for (@stat_net_locs6) {
		$counts1_6{$stat_net_locs6[$i++]->[0]}++;
	}

	if ( $stat_net_locs6[0] ) {
		$host_net_locs_count6 = $gip->create_stat_pie_chart(\%counts1_6,"loc","networks6_by_site","v6","$client_id","$vars_file","$$lang_vars{networks6_by_site_message}");

        $charts_data_net_sites6 = $gip->create_stat_pie_chart_data(
            counts => \%counts1_6,
            type => "loc",
            im_name => "networks6_by_site",
            im_title => $$lang_vars{networks6_by_site_message},
        );
	}
}



my @stat_host_cats4 = $gip->get_stat_host_cats("$client_id","v4");

my %counts2_4 = ();
my $hosts4_by_host_cat_im_name = "hosts4_by_host_cat";
if ( $stat_host_cats4[0] ) {
	$i=0;
	for (@stat_host_cats4) {
		$counts2_4{$stat_host_cats4[$i++]->[0]}++;
	}
	$gip->create_stat_pie_chart(\%counts2_4,"","hosts4_by_host_cat","v4","$client_id","$vars_file","$$lang_vars{hosts4_by_host_cat_message}");

	$charts_data_host_cats4 = $gip->create_stat_pie_chart_data(
		counts => \%counts2_4,
		type => "",
		im_name => "hosts4_by_host_cat",
		im_title => $$lang_vars{hosts4_by_host_cat_message},
	);
}


my @stat_host_cats6 = $gip->get_stat_host_cats("$client_id","v6");

my %counts2_6 = ();
my $hosts6_by_host_cat_im_name = "hosts6_by_host_cat";
if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_host_cats6[0] ) {
		$i=0;
		for (@stat_host_cats6) {
			$counts2_6{$stat_host_cats6[$i++]->[0]}++;
		}
		$gip->create_stat_pie_chart(\%counts2_6,"","hosts6_by_host_cat","v6","$client_id","$vars_file","$$lang_vars{hosts6_by_host_cat_message}");

		$charts_data_host_cats6 = $gip->create_stat_pie_chart_data(
			counts => \%counts2_6,
			type => "",
			im_name => "hosts6_by_host_cat",
			im_title => $$lang_vars{hosts6_by_host_cat_message},
		);
	}
}

my @stat_host_locs4 = $gip->get_stat_host_locs("$client_id","v4");

my %counts3_4 = ();
my $hosts4_by_host_site_im_name="hosts4_by_host_site";
if ( $stat_host_locs4[0] ) {
	$i=0;
	for (@stat_host_locs4) {
		$counts3_4{$stat_host_locs4[$i++]->[0]}++;
	}
	$gip->create_stat_pie_chart(\%counts3_4,"","hosts4_by_host_site","v4","$client_id","$vars_file","$$lang_vars{hosts4_by_host_site_message}");

	$charts_data_host_sites4 = $gip->create_stat_pie_chart_data(
		counts => \%counts3_4,
		type => "",
		im_name => "hosts4_by_host_site",
		im_title => $$lang_vars{hosts4_by_host_site_message},
	);
}

my @stat_host_locs6 = $gip->get_stat_host_locs("$client_id","v6");

my %counts3_6 = ();
my $hosts6_by_host_site_im_name="hosts6_by_host_site";
if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_host_locs6[0] ) {
		$i=0;
		for (@stat_host_locs6) {
			$counts3_6{$stat_host_locs6[$i++]->[0]}++;
		}
		$gip->create_stat_pie_chart(\%counts3_6,"","hosts6_by_host_site","v6","$client_id","$vars_file","$$lang_vars{hosts6_by_host_site_message}");

		$charts_data_host_sites6 = $gip->create_stat_pie_chart_data(
			counts => \%counts3_6,
			type => "",
			im_name => "hosts6_by_host_site",
			im_title => $$lang_vars{hosts6_by_host_site_message},
		);
	}
}

my $stat_struct = "";

$stat_struct .= '
<div id="stat_struct" class="container-fluid">
  <div class="row p-3">
    <div class="col-6">';


$stat_struct .= "<table class='table'>\n";
$stat_struct .= "<tr><th></th><th>$$lang_vars{networks_total_message}</th><th>$$lang_vars{hosts_total_message}</th><th>$$lang_vars{vlans_total_message}</th></tr>\n";
if ( $ipv4_only_mode ne "yes" ) {
	$stat_struct .= "<tr class=\"stat_table\"><td>Total</td><td>$anz_red_all</td><td>$anz_host_all</td><td>$anz_vlans</td></tr>\n";
	$stat_struct .= "<tr class=\"stat_table\"><td>IPv4</td><td>$anz_red_all4</td><td>$anz_host_all4</td><td></td></tr>\n";
	$stat_struct .= "<tr class=\"stat_table\"><td>IPv6</td><td>$anz_red_all6</td><td>$anz_host_all6</td><td></td></tr>\n";
} else {
	$stat_struct .= "<tr class=\"stat_table\"><td></td><td><b>$anz_red_all4</b></td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>$anz_host_all4</b></b></td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>$anz_vlans</b></td></tr>\n";
}
$stat_struct .= "</table>\n";

#$stat_struct .= '</div>';



#if ( $ipv4_only_mode ne "yes" ) {
#    $stat_struct .= '
#    <div class="col-6"><h6>' .
#		$$lang_vars{networks6_by_cat_message}
#	. '</h6></div>';
#}
#$stat_struct .= '</div>';





# TEST 
my $create_custom_stat = $daten{'create_custom_stat'} || "";
my $stat_object = $daten{'stat_object'} || "";
my $show_by = $daten{'show_by'} || "";
my $filter = $daten{'stat_filter'} || "";
my $filter_value = $daten{'filter_value'} || "";


# NETWORKS

my @cc_values=$gip->get_custom_columns("$client_id");
my %custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","network");
my %custom_net_columns_select_name_items;
my @custom_net_columns = $gip->get_custom_columns("$client_id");

my $site_hash = $gip->get_loc_hash("$client_id"); # (loc = id)
my $net_cat_hash = $gip->get_net_cat_hash("$client_id");  # (cat = id)

$stat_struct .="<p></p><br><h4>$$lang_vars{show_custom_stat_message}</h4><p></p>\n";
$stat_struct .= "<form name=\"create_custom_stat\" method=\"POST\" action=\"$server_proto://$base_uri/ip_show_stat.cgi\" style=\"display:inline;\">\n";
$stat_struct .= "<input name=\"create_custom_stat\" type=\"hidden\" value=\"create_custom_stat\"><input name=\"stat_object\" type=\"hidden\" value=\"network\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\">\n";

my $selected = "";
$stat_struct .= "<table name='show_networks_by' border='0'>\n";
$stat_struct .= "<tr><td align=\"left\">$$lang_vars{Show_message}";
$stat_struct .= " <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 75px\" name=\"ip_version\" size=\"1\">\n";
$stat_struct .= "<option value='v4'>IPv4</option>";
$stat_struct .= "<option value='v6'>IPv6</option>";
$stat_struct .= "</select>";
$stat_struct .= " $$lang_vars{networks_by_message} ";
$stat_struct .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"show_by\" size=\"1\">\n";
$stat_struct .= "<option>$$lang_vars{loc_message}</option>\n";
$stat_struct .= "<option>$$lang_vars{cat_message}</option>\n";

my ( $tag_active, $dnssg_active);
my $j = 0;
my %cc_values_name_id_hash;
foreach ( sort { $a->[0] cmp $b->[0] } @cc_values) {
    my $select_values_string_ref;
    my $cc_name = $cc_values[$j]->[0];
    my $cc_id = $cc_values[$j]->[1];

    $select_values_string_ref = $custom_columns_select{$cc_id}[2] if exists $custom_columns_select{$cc_id};

    if ( ! $select_values_string_ref ) {
        # ignore non select columns
		if ( $cc_name eq "Tag" ) {
			$tag_active = 1;
		} elsif ( $cc_name eq "DNSSG" ) {
			$dnssg_active = 1;
		}

		$j++;
		next;
    }

    $cc_values_name_id_hash{$cc_name} = $cc_id;

	my $items = $custom_columns_select{$cc_id}->[2]; 
	$custom_net_columns_select_name_items{$cc_name} = $items;

	$stat_struct .= "<option>$cc_name</option>\n";

	$j++;
}
$stat_struct .= "<option>Tag</option>\n" if $tag_active;
$stat_struct .= "<option>DNSSG</option>\n" if $dnssg_active;
$stat_struct .= "</select> $$lang_vars{filter_by_message} ";

my $onclick = "onchange='changeHideOpts(this.value);'";
$stat_struct .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"stat_filter\" size=\"1\" $onclick>\n";
$stat_struct .= "<option></option>\n";
$stat_struct .= "<option>$$lang_vars{loc_message}</option>\n";
$stat_struct .= "<option>$$lang_vars{cat_message}</option>\n";

$j = 0;
foreach (@cc_values) {
    my $select_values_string_ref;
    my $cc_name = $cc_values[$j]->[0];
    my $cc_id = $cc_values[$j]->[1];

    $select_values_string_ref = $custom_columns_select{$cc_id}[2] if exists $custom_columns_select{$cc_id};

    if ( ! $select_values_string_ref ) {
        # ignore non select columns
        $j++;
        next;
    }

	if ( $cc_name ne "Tag" && $cc_name ne "DNSSG") {
		my $items = $custom_columns_select{$cc_id}->[2]; 
		$custom_net_columns_select_name_items{$cc_name} = $items;
	}

	$stat_struct .= "<option>$cc_name</option>\n";

	$j++;
}
$stat_struct .= "<option>Tag</option>\n" if $tag_active;
$stat_struct .= "<option>DNSSG</option>\n" if $dnssg_active;
$stat_struct .= "</select> ";

$stat_struct .= "<span id='Hide_net_filter_details'></span>\n";

$stat_struct .= "<input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{submit_message}\" style=\"cursor:pointer;\">\n";

$stat_struct .= "</td></tr></table></form>\n";
$stat_struct .="<p></p><br>\n";



my $select_site = "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
$select_site .= "<option value='NULL'>$$lang_vars{without_value_message}</option>";
foreach my $key ( keys %$site_hash ) {
    if ( $key eq "NULL" ) {
        next;
    }
    $select_site .= "<option>$key</option>";
}
$select_site .= "</select>";

my $select_net_cat = "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
$select_net_cat .= "<option value='NULL'>$$lang_vars{without_value_message}</option>";
foreach my $key ( keys %$net_cat_hash ) {
    if ( $key eq "NULL" ) {
        next;
    }
    $select_net_cat .= "<option>$key</option>";
}
$select_net_cat .= "</select>";

my %tag_hash = $gip->get_tag_hash("$client_id", "name");
my $select_net_tag = "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
my $n=0;
foreach my $tag_name (keys %tag_hash) {
    $select_net_tag .= "<option>$tag_name</option>";
}
$select_net_tag .= "</select>";
my $select_host_tag = $select_net_tag;

my %dnssg_hash = $gip->get_dns_server_group_hash("$client_id", "name");
my %network_dnssg;
my $select_dnssg = "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
$n=0;
foreach my $dnssg_name (keys %dnssg_hash) {
    $select_dnssg .= "<option>$dnssg_name</option>";
}
$select_dnssg .= "</select>";



###### HOSTS

my @cc_host_values=$gip->get_custom_host_columns("$client_id");
%custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","host");
my %custom_host_columns_select_name_items;
my @custom_host_columns = $gip->get_custom_host_columns("$client_id");
my $cc_id_os = $gip->get_custom_host_column_id_from_name_client("$client_id","OS") || "";
my $cc_id_vendor = $gip->get_custom_host_column_id_from_name_client("$client_id","vendor") || "";

my $host_cat_hash = $gip->get_cat_hash("$client_id");  # (cat = id)

$stat_struct .= "<form name=\"create_custom_host_stat\" method=\"POST\" action=\"$server_proto://$base_uri/ip_show_stat.cgi\" style=\"display:inline;\">\n";
$stat_struct .= "<input name=\"create_custom_stat\" type=\"hidden\" value=\"create_custom_stat\"><input name=\"stat_object\" type=\"hidden\" value=\"host\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\">\n";

$selected = "";
$stat_struct .= "<table name='select_host_cc' border='0'>\n";
$stat_struct .= "<tr><td align=\"left\">$$lang_vars{Show_message}";
$stat_struct .= " <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 75px\" name=\"ip_version\" size=\"1\">\n";
$stat_struct .= "<option value='v4'>IPv4</option>";
$stat_struct .= "<option value='v6'>IPv6</option>";
$stat_struct .= "</select>";
$stat_struct .= " $$lang_vars{hosts_by_message} ";
$stat_struct .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"show_by\" size=\"1\">\n";
$stat_struct .= "<option>$$lang_vars{loc_message}</option>\n";
$stat_struct .= "<option>$$lang_vars{cat_message}</option>\n";
$stat_struct .= "<option>OS</option>\n" if $cc_id_os;
$stat_struct .= "<option>vendor</option>\n" if $cc_id_vendor;

$j = 0;
foreach (@cc_host_values) {
    my $select_values_string_ref;
    my $cc_name = $cc_host_values[$j]->[0];
    my $cc_id = $cc_host_values[$j]->[1];

    $select_values_string_ref = $custom_columns_select{$cc_id}[2] if exists $custom_columns_select{$cc_id};

    if ( ! $select_values_string_ref ) {
        # ignore non select columns
		if ( $cc_name eq "Tag" ) {
			$tag_active = 1;
		}

		$j++;
		next;
    }

	my $items = $custom_columns_select{$cc_id}->[2]; 
	$custom_host_columns_select_name_items{$cc_name} = $items;

	$stat_struct .= "<option>$cc_name</option>\n";

	$j++;
}
$stat_struct .= "<option>Tag</option>\n" if $tag_active;
$stat_struct .= "</select> $$lang_vars{filter_by_message} ";

$onclick = "onchange='changeHostHideOpts(this.value);'";
$stat_struct .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"stat_filter\" size=\"1\" $onclick>\n";
$stat_struct .= "<option></option>\n";
$stat_struct .= "<option>$$lang_vars{loc_message}</option>\n";
$stat_struct .= "<option>$$lang_vars{cat_message}</option>\n";

$j = 0;
foreach (@cc_host_values) {
    my $select_values_string_ref;
    my $cc_name = $cc_host_values[$j]->[0];
    my $cc_id = $cc_host_values[$j]->[1];

    $select_values_string_ref = $custom_columns_select{$cc_id}[2] if exists $custom_columns_select{$cc_id};

    if ( ! $select_values_string_ref ) {
        # ignore non select columns
        $j++;
        next;
    }

	if ( $cc_name ne "Tag" ) {
		my $items = $custom_columns_select{$cc_id}->[2]; 
		$custom_host_columns_select_name_items{$cc_name} = $items;
	}

	$stat_struct .= "<option>$cc_name</option>\n";

	$j++;
}
$stat_struct .= "<option>Tag</option>\n" if $tag_active;
$stat_struct .= "</select> ";

$stat_struct .= "<span id='Hide_host_filter_details'></span>\n";

$stat_struct .= "<input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{submit_message}\" style=\"cursor:pointer;\">\n";

$stat_struct .= "</td></tr></table></form>\n";
$stat_struct .="<p></p><br>\n";


my $select_host_cat = "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
foreach my $key ( keys %$host_cat_hash ) {
    if ( $key eq "NULL" ) {
        next;
    }
    $select_host_cat .= "<option>$key</option>";
}
$select_host_cat .= "</select>";



# Create stat
my @stat_arr;
my $ip_version = $daten{'ip_version'} || "";
if ( $create_custom_stat ) {

	my $object_name;
	if ( $stat_object eq "network" ) {
		$object_name = $$lang_vars{networks_may_message};
	} elsif ( $stat_object eq "host" ) {
		$object_name = $$lang_vars{hosts1_message};
	}

    my $ip_version_show = "IPv4";
    $ip_version_show = "IPv6" if $ip_version eq "v6";
    my $filter_value_show = $filter_value;
    $filter_value_show = "$$lang_vars{without_value_message}" if $filter_value eq "NULL";

	$stat_struct .= "<H4>$ip_version_show $object_name $$lang_vars{by_message} $show_by";
	$stat_struct .= " ($$lang_vars{filter_message}: $filter: $filter_value_show)" if $filter_value;
	$stat_struct .= "</H4><p></p>\n";


    $gip->debug("$show_by - $filter - $filter_value - $ip_version");

	if ( ($show_by eq $$lang_vars{loc_message} || $show_by eq $$lang_vars{cat_message}) && ($filter eq $$lang_vars{cat_message} || $filter eq $$lang_vars{loc_message} || ! $filter)) {
        
        $gip->debug("STAT 1 - $client_id");

		@stat_arr = $gip->get_stat_site_cat_generic("$client_id", "$vars_file", "$stat_object", "$show_by","$filter","$filter_value", "$ip_version");

	} elsif (( $show_by eq "Tag" && ! $filter ) || ( $show_by eq "Tag" && ($filter eq $$lang_vars{cat_message} || $filter eq $$lang_vars{loc_message}))) {

        $gip->debug("STAT 2");

		@stat_arr = $gip->get_stat_tag_site_cat("$client_id", "$vars_file", "$stat_object", "$filter","$filter_value", "$ip_version");

	} elsif ( $show_by eq "Tag" && $filter eq "DNSSG" ) {

		my $filter_cc_id;
		if ( $stat_object eq "network" ) {
			$filter_cc_id = $gip->get_custom_column_id_from_name("$client_id", "$filter" );
		} elsif ( $stat_object eq "host" ) {
			$filter_cc_id = $gip->get_custom_host_column_id_from_name("$client_id", "$filter" );
		}

        $gip->debug("STAT 3 - $filter_cc_id");

		@stat_arr = $gip->get_stat_tag_dnssg("$client_id", "$vars_file", "$stat_object", "$filter_cc_id", "$filter_value", "$ip_version"); 


	} elsif ( $show_by eq "Tag" ) {

		my $filter_cc_id;
		if ( $stat_object eq "network" ) {
			$filter_cc_id = $gip->get_custom_column_id_from_name("$client_id", "$filter" );
		} elsif ( $stat_object eq "host" ) {
			$filter_cc_id = $gip->get_custom_host_column_id_from_name_client("$client_id", "$filter" );
		}

        $gip->debug("STAT 4 - $filter_cc_id");

		@stat_arr = $gip->get_stat_tag_cc_select("$client_id", "$vars_file", "$stat_object", "$filter_cc_id","$filter_value", "$ip_version");

	} elsif (( $show_by eq "DNSSG" && ! $filter ) || ( $show_by eq "DNSSG" && ($filter eq $$lang_vars{cat_message} || $filter eq $$lang_vars{loc_message}))) {


		my $cc_id;
		if ( $stat_object eq "network" ) {
			$cc_id = $gip->get_custom_column_id_from_name("$client_id", "$show_by" );
		} elsif ( $stat_object eq "host" ) {
			$cc_id = $gip->get_custom_host_column_id_from_name("$client_id", "$show_by" );
		}

        $gip->debug("STAT 5 - $cc_id");

		@stat_arr = $gip->get_stat_dnssg_site_cat("$client_id", "$vars_file", "$stat_object", "$show_by", "$cc_id", "$filter","$filter_value", "$ip_version");
	} elsif ($show_by eq "DNSSG" && $filter eq "Tag" ) {

        $gip->debug("STAT 6");

		@stat_arr = $gip->get_stat_dnssg_tag("$client_id", "$vars_file", "$stat_object", "$filter_value", "$ip_version" );

	} elsif ($show_by eq "DNSSG") {

		my $filter_cc_id;
		if ( $stat_object eq "network" ) {
			$filter_cc_id = $gip->get_custom_column_id_from_name("$client_id", "$filter" );
		} elsif ( $stat_object eq "host" ) {
			$filter_cc_id = $gip->get_custom_host_column_id_from_name("$client_id", "$filter" );
		}

        $gip->debug("STAT 7 - $filter_cc_id");

		@stat_arr = $gip->get_stat_dnssg_cc_select("$client_id", "$vars_file", "$stat_object", "$filter_cc_id", "$filter_value", "$ip_version");


	} elsif ( $show_by eq $$lang_vars{loc_message} || $show_by eq $$lang_vars{cat_message} ) {


		my $filter_cc_id;
		if ( $stat_object eq "network" ) {
			$filter_cc_id = $gip->get_custom_column_id_from_name("$client_id", "$filter" );
		} elsif ( $stat_object eq "host" ) {
			$filter_cc_id = $gip->get_custom_host_column_id_from_name_client("$client_id", "$filter" );
		}

        $gip->debug("STAT 8 - $filter_cc_id");

		@stat_arr = $gip->get_stat_site_cat_cc_select_generic("$client_id", "$vars_file", "$stat_object", "$show_by", "$filter", "$filter_cc_id","$filter_value", "$ip_version"); 

	} elsif ( $filter eq $$lang_vars{loc_message} || $filter eq $$lang_vars{cat_message} ) {

		my $cc_id;
		if ( $stat_object eq "network" ) {
			$cc_id = $gip->get_custom_column_id_from_name("$client_id", "$show_by" );
		} elsif ( $stat_object eq "host" ) {
			$cc_id = $gip->get_custom_host_column_id_from_name_client("$client_id", "$show_by" );
		}

        $gip->debug("STAT 9 - $cc_id");

		@stat_arr = $gip->get_stat_cc_select_site_cat_generic("$client_id", "$vars_file", "$stat_object", "$show_by", "$cc_id", "$filter","$filter_value", "$ip_version");
	
	} else {

		my $cc_id;
		my $filter_cc_id;
		if ( $stat_object eq "network" ) {
			$cc_id = $gip->get_custom_column_id_from_name("$client_id", "$show_by" );
			$filter_cc_id = $gip->get_custom_column_id_from_name("$client_id", "$filter" );
		} elsif ( $stat_object eq "host" ) {
			$cc_id = $gip->get_custom_host_column_id_from_name_client("$client_id", "$show_by" );
			$filter_cc_id = $gip->get_custom_host_column_id_from_name_client("$client_id", "$filter" );
		}

        $gip->debug("STAT 10 - $filter - $cc_id - $filter_cc_id");

		@stat_arr = $gip->get_stat_cc_select_cc_select_generic("$client_id", "$vars_file", "$stat_object", "$cc_id", "$filter_cc_id","$filter_value", "$ip_version","$filter");
	}
}


my ($stat_count, $charts_data);
$i = 0;
my %counts;

my $count_null;
my $stat_table = "";

if ( $create_custom_stat && @stat_arr ) {
    $i=0;
    for (@stat_arr) {
        $counts{$stat_arr[$i++]->[0]}++;
    }

    $stat_count = $gip->create_stat_pie_chart(\%counts,"$show_by","$show_by","v4","$client_id","$vars_file","$show_by");

    $charts_data = $gip->create_stat_pie_chart_data(
        counts => \%counts,
        type => "cat",
        im_name => "$show_by",
        im_title => "$show_by",
    );

	my ($cat_name, $head_line_object, $search_script);
    if ( $stat_object eq "network" ) {
        $cat_name = "cat_red";
        $head_line_object = "$$lang_vars{redes_dispo_message}";
        $search_script = "ip_searchred.cgi";
    } elsif ( $stat_object eq "host" ) {
        $cat_name = "cat";
        $head_line_object = "$$lang_vars{hosts_message}";
        $search_script = "ip_searchip.cgi";
    }

    $stat_table .= '<table class="table-bordered">';
    $stat_table .= "<tr><th class='m-2 p-2'>$show_by</th><th class='m-2 p-2'>$head_line_object</th></tr>\n";
    foreach my $keys (sort keys %counts) {


        my $cc_id = $cc_values_name_id_hash{$keys} || "";
        my $hidden_values = "";
        if ( $show_by eq $$lang_vars{loc_message} ) { 
            $hidden_values .= "<input name=\"loc\" type=\"hidden\" value=\"$keys\">";
        } 
        if ( $filter eq $$lang_vars{loc_message} ) {
            $hidden_values .= "<input name=\"loc\" type=\"hidden\" value=\"$filter_value\">";
        } 
        if ( $show_by eq $$lang_vars{cat_message} ) {
            $hidden_values .= "<input name=\"$cat_name\" type=\"hidden\" value=\"$keys\">";
        }
        if ( $filter eq $$lang_vars{cat_message} ) {
            $hidden_values .= "<input name=\"$cat_name\" type=\"hidden\" value=\"$filter_value\">";
        }
        if ( $cc_id && $show_by eq $keys ) {
            $hidden_values .= "<input name=\"cc_id_${cc_id}\" type=\"hidden\" value=\"$keys\">";
        }
#		if ( $show_by eq "Tag" ) {
#            $hidden_values .= "<input name=\"Tag\" type=\"hidden\" value=\"$keys\">";
#        }
#        if ( $filter eq "Tag" ) {
#            $hidden_values .= "<input name=\"Tag\" type=\"hidden\" value=\"$filter_value\">";
#        }
        if ( $cc_id && $filter eq $keys ) {
            $hidden_values .= "<input name=\"cc_id_${cc_id}\" type=\"hidden\" value=\"$filter_value\">";
        }

        if ( $keys eq "NULL" ) {
            $count_null=$stat_count->{$keys};
        } else {
			my $stat_list_form = "$counts{$keys}";
			if ( $show_by eq $$lang_vars{loc_message} || $show_by eq $$lang_vars{cat_message} || $filter eq $$lang_vars{cat_message} || $filter eq $$lang_vars{loc_message} ) {
				$stat_list_form ="<form name=\"search_stat\" method=\"POST\" action=\"$server_proto://$base_uri/$search_script\" style=\"display:inline;\">${hidden_values}<input name=\"ipv4\" type=\"hidden\" value=\"$ip_version\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts{$keys}\" style=\"cursor:pointer;\"></form>";
			}
            $stat_table .= "<tr><td class='p-2'>$keys</td><td class='p-2'>$stat_list_form</form></td></tr>";
        }
    }

	my $hidden_values_null = "";
	if ( $show_by eq $$lang_vars{loc_message} ) {
		$hidden_values_null .= "<input name=\"loc\" type=\"hidden\" value=\"NULL\">";
	}
	if ( $show_by eq $$lang_vars{cat_message} ) {
		$hidden_values_null .= "<input name=\"$cat_name\" type=\"hidden\" value=\"NULL\">";
	}

	my $stat_list_form_null = "";
	$stat_list_form_null = "$counts{'NULL'}" if $counts{'NULL'};
	if ( $show_by eq $$lang_vars{loc_message} || $show_by eq $$lang_vars{cat_message} || $filter eq $$lang_vars{cat_message} || $filter eq $$lang_vars{loc_message} ) {
		$stat_list_form_null ="<form name=\"search_stat_null\" method=\"POST\" action=\"$server_proto://$base_uri/$search_script\" style=\"display:inline;\">$hidden_values_null<input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$stat_list_form_null\" style=\"cursor:pointer;\"></form>";
	}
    $stat_table .= "<tr><td class='p-2'>$$lang_vars{without_message} $show_by</td><td class='p-2'>$stat_list_form_null</td></tr>" if $counts{'NULL'};
    $stat_table .= "</table>\n";


$stat_struct .= '
    </div>
  </div>';

} elsif ( $create_custom_stat) {
    $stat_table .= "<font color=\"gray\">N/A</font>\n";
$stat_struct .= '
    </div>
  </div>';

} else {


















# TEST START


$stat_struct .= '
    </div>
  </div>';


# ROW Title 
$stat_struct .= '
  <div class="row m-3">
    <div class="col-6"><h4>' . 
		$$lang_vars{networks_may_message}
	. '</h4></div>
  </div>';


# ROW
$stat_struct .= '
  <div class="row m-3">
    <div class="col-6"><h6>' . 
		$$lang_vars{networks4_by_cat_message}
	. '</h6></div>';

if ( $ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-6"><h6>' .
		$$lang_vars{networks6_by_cat_message}
	. '</h6></div>';
}
$stat_struct .= '</div>';


my $cat_net4_table = "";
my $cat_net6_table = "";
my $site_net4_table = "";
my $site_net6_table = "";
my $cat_host4_table = "";
my $cat_host6_table = "";
my $site_host4_table = "";
my $site_host6_table = "";
my $vendor_host4_table = "";
my $vendor_host6_table = "";



if ( $stat_net_cats4[0] ) {
		$cat_net4_table .= '<table class="table-bordered">';
		$cat_net4_table .= "<tr><th>$$lang_vars{cat_message}</th><th>$$lang_vars{redes_dispo_message} ($$lang_vars{hosts1_message})</th></tr>\n";
		foreach my $keys (sort keys %counts_4) {
			if ( $keys eq "NULL" ) {
				$count_null=$host_net_cats_count4->{$keys};
			} else {
				$cat_net4_table .= "<tr><td>$keys</td><td><form name=\"search_red_${keys}_cat_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"cat_red\" type=\"hidden\" value=\"$keys\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_4{$keys}\" style=\"cursor:pointer;\"></form> ($host_net_cats_count4->{$keys})</td></tr>";

			}
		}
		$cat_net4_table .= "<tr><td>$$lang_vars{without_cat_message}</td><td><form name=\"search_red_NULL_cat_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"cat_red\" type=\"hidden\" value=\"NULL\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_4{'NULL'}\" style=\"cursor:pointer;\"></form> ($count_null)</td></tr>" if $counts_4{'NULL'};
		$cat_net4_table .= "</table>\n";

#		if ( keys (%$host_net_cats_count4) >=250 ) {
#			print "<font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<a href=\"./imagenes/dyn/${host_net_cats_im_name4}_big.png\"><img src=\"./imagenes/dyn/${host_net_cats_im_name4}.png\" alt=\"$$lang_vars{networks4_by_cat_message} chart\"></a>";
#		}
#		print "</td></tr>\n";
	} else {
		$cat_net4_table .= "<font color=\"gray\">N/A</font>\n";
	}


$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
			  $cat_net4_table
	. '</div>
    <div class="col-4">
			  <canvas id="pieChartCat" width="8" height="8"></canvas> 
	</div>';


if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_net_cats6[0] ) {
		$cat_net6_table .= "<table class='table-bordered'>\n";
		$cat_net6_table .= "<tr><td> <b>$$lang_vars{cat_message}</b></td><td><b>$$lang_vars{redes_dispo_message} ($$lang_vars{hosts1_message})</b></td></tr>\n";
		foreach my $keys (sort keys %counts_6) {
			if ( $keys eq "NULL" ) {
				$count_null=$host_net_cats_count6->{$keys};
			} else {
				$cat_net6_table .= "<tr><td>$keys</td><td><form name=\"search_red_${keys}_cat_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"cat_red\" type=\"hidden\" value=\"$keys\"><input name=\"ipv6\" type=\"hidden\" value=\"ipv6\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_6{$keys}\" style=\"cursor:pointer;\"></form> ($host_net_cats_count6->{$keys})</td></tr>";
			}
		}
		$cat_net6_table .= "<tr><td>$$lang_vars{without_cat_message}</td><td><form name=\"search_red_NULL_cat_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"cat_red\" type=\"hidden\" value=\"NULL\"><input name=\"ipv6\" type=\"hidden\" value=\"ipv6\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_6{'NULL'}\" style=\"cursor:pointer;\"></form> ($count_null)</td></tr>" if $counts_6{'NULL'};
		$cat_net6_table .= "</table>\n";

#		if ( keys (%$host_net_cats_count6) >=250 ) {
#			print "<font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<a href=\"./imagenes/dyn/${host_net_cats_im_name6}_big.png\"><img src=\"./imagenes/dyn/${host_net_cats_im_name6}.png\" alt=\"$$lang_vars{networks6_by_cat_message} chart\"></a>";
#		}
	} else {
		$cat_net6_table .= "<font color=\"gray\">N/A</font>\n";
	}

$stat_struct .= '
    <div class="col-2">' .
		$cat_net6_table
	. '</div>
    <div class="col-4">
			<div class="col-sm ">
			  <canvas id="pieChartCat2" width="8" height="8"></canvas> 
			</div>
    </div>';

}
$stat_struct .= '</div>';

	if ($stat_net_locs4[0]) {
		$site_net4_table .= "<table class=\"table-bordered\">\n";
		$site_net4_table .= "<tr><td><b>$$lang_vars{loc_message}</b></td><td><b>$$lang_vars{redes_dispo_message} ($$lang_vars{hosts1_message})</b></td></tr>\n";
		foreach my $keys (sort keys %counts1_4) {
			if ( $keys eq "NULL" ) {
				$count_null=$host_net_locs_count4->{$keys};
			} else {
				$site_net4_table .= "<tr><td>$keys</td><td><form name=\"search_red_${keys}_loc_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"loc\" type=\"hidden\" value=\"$keys\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts1_4{$keys}\" style=\"cursor:pointer;\"></form> ($host_net_locs_count4->{$keys})</td></tr>";
			}
		}
		$site_net4_table .= "<tr><td>$$lang_vars{without_loc_message}</td><td><form name=\"search_red_NULL_loc_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"loc\" type=\"hidden\" value=\"NULL\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts1_4{'NULL'}\" style=\"cursor:pointer;\"></form> ($count_null)</td></tr>" if $counts1_4{'NULL'};
		$site_net4_table .= "</table>\n";
#		if ( keys (%$host_net_locs_count4) >=250 ) {
#			print "<i><b><font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<a href=\"./imagenes/dyn/${host_net_locs_im_name4}_big.png\"><img src=\"./imagenes/dyn/${host_net_locs_im_name4}.png\" alt=\"$$lang_vars{networks4_by_site_message} chart\"></a>\n";
#		}
#		print "</td></tr>\n";
#		print "</table>\n";
} else {
	$site_net4_table .=  "<font color=\"gray\">N/A</font>\n";
}

if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_net_locs6[0] ) {
		$site_net6_table .= "<table class=\"table-bordered\">\n";
		$site_net6_table .= "<tr><td><b>$$lang_vars{loc_message}</b></td><td><b>$$lang_vars{redes_dispo_message} ($$lang_vars{hosts1_message})</b></td></tr>\n";
		foreach my $keys (sort keys %counts1_6) {
			if ( $keys eq "NULL" ) {
				$count_null=$host_net_locs_count6->{$keys};
			} else {
				$site_net6_table .= "<tr><td>$keys</td><td><form name=\"search_red_${keys}_loc_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"loc\" type=\"hidden\" value=\"$keys\"><input name=\"ipv6\" type=\"hidden\" value=\"ipv6\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts1_6{$keys}\" style=\"cursor:pointer;\"></form> ($host_net_locs_count6->{$keys})</td></tr>";
			}
		}
		$site_net6_table .= "<tr><td>$$lang_vars{without_loc_message}</td><td><form name=\"search_red_NULL_loc_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchred.cgi\" style=\"display:inline;\"><input name=\"loc\" type=\"hidden\" value=\"NULL\"><input name=\"ipv6\" type=\"hidden\" value=\"ipv6\"><input name=\"modred\" type=\"hidden\" value=\"y\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts1_6{'NULL'}\" style=\"cursor:pointer;\"></form> ($count_null)</td></tr>" if $counts1_6{'NULL'};
		$site_net6_table .= "</table>\n";
#		if ( keys (%$host_net_locs_count6) >=250 ) {
#			print "<font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<a href=\"./imagenes/dyn/${host_net_locs_im_name6}_big.png\"><img src=\"./imagenes/dyn/${host_net_locs_im_name6}.png\" alt=\"$$lang_vars{networks6_by_site_message} chart\"></a>\n";
#		}
#		print "</td></tr>\n";
	} else {
		$site_net6_table .= "<tr><td><i><b><font color=\"gray\">N/A</font></b></i></td></tr>\n";
	}
	
#	print "</table>\n";
}

# ROW
$stat_struct .= '
  <div class="row m-3">
  </div>
  <div class="row m-3">
    <div class="col-6"><h6>' .
        $$lang_vars{networks4_by_site_message}
    . '</h6></div>';
if ( $ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-6"><h6>' .
        $$lang_vars{networks6_by_site_message}
    . '</h6></div>';
}
$stat_struct .= '</div>';

# ROW
$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
              $site_net4_table
    . '</div>
    <div class="col-4">
            <div class="col-sm ">
              <canvas id="pieChartSite" width="8" height="8"></canvas> 
            </div>
    </div>';

if ( $ipv4_only_mode ne "yes" ) {

    $stat_struct .= '
    <div class="col-2">' .
              $site_net6_table
    . '</div>
    <div class="col-4">
            <div class="col-sm ">
              <canvas id="pieChartSite2" width="8" height="8"></canvas> 
            </div>
    </div>';
}
$stat_struct .= '</div>';






if ( $stat_host_cats4[0] ) {
	$cat_host4_table .= "<table class=\"table-bordered\">\n";
	$cat_host4_table .= "<tr><td><b>$$lang_vars{cat_message}</b></td><td><b>$$lang_vars{hosts1_message}</b></td></tr>\n";
	foreach my $keys (sort keys %counts2_4) {
		if ( $keys eq "NULL" ) {
	#		$count_null=$host_net_locs_count4{$keys};
		} else {
			$cat_host4_table .= "<tr><td>$keys</td><td><form name=\"search_host_${keys}\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cat\" type=\"hidden\"  value=\"$keys\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts2_4{$keys}\" style=\"cursor:pointer;\"></form></td></tr>";
		}
	}
	$cat_host4_table .= "<tr><td>$$lang_vars{without_cat_message}</td><td><form name=\"search_host_NULL\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cat\" type=\"hidden\" value=\"NULL\"><input name=\"ipv4\" type=\"hidden\" value=\"ipv4\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts2_4{'NULL'}\" style=\"cursor:pointer;\"></form></td></tr>" if $counts2_4{'NULL'};
	$cat_host4_table .= "</table>\n";
#	if ( keys (%counts2_4) >= 250 ) {
#		print "<td><font color=\"gray\">N/A</font></b></i>\n";
#	} else {
#		print "<td valign=\"top\"><a href=\"./imagenes/dyn/${hosts4_by_host_cat_im_name}_big.png\"><img src=\"./imagenes/dyn/${hosts4_by_host_cat_im_name}.png\" alt=\"$$lang_vars{hosts4_by_host_cat_message} chart\"></a>\n";
#	}
#	print "</td></tr>\n";
} else {
	$cat_host4_table .= "<font color=\"gray\">N/A</font>\n";
}




my @vendor_cc_id=$gip->get_custom_host_column_ids_from_name("$client_id","vendor");
my $vendor_cc_id=1;
$vendor_cc_id=$vendor_cc_id[0]->[0] if $vendor_cc_id[0]->[0];

my @vendors = $gip->get_vendor_array();
my $vendor_list=join("|",@vendors);


#if ( $stat_net_locs4[0] ) {
#    $i=0;
#    for (@stat_net_locs4) {
#        $counts1_4{$stat_net_locs4[$i++]->[0]}++;
#    }
#
#    $charts_data_net_sites4 = $gip->create_stat_pie_chart_data(
#        counts => \%counts1_4,
#        type => "loc",
#        im_name => "networks4_by_site",
#        im_title => $$lang_vars{networks4_by_site_message},
#    );
#}

my %counts_host4_vendor = ();
my $anz_counts_vendors4=scalar(keys(%counts_vendors4));

my @stat_host_vendors4 = $gip->get_stat_host_vendors("$client_id");

if ( $anz_counts_vendors4 > 0 ) {

	$i=0;
	for (@stat_host_vendors4) {
        my $vendor_name = lc($stat_host_vendors4[$i]->[0]);
        if ( ! $counts_vendors4_lc{$vendor_name} ) {
            $i++;
            next;
        }
		$counts_host4_vendor{$stat_host_vendors4[$i++]->[0]}++;
	}

	$charts_data_host_vendor4 = $gip->create_stat_pie_chart_data(
		counts => \%counts_host4_vendor,
		type => "loc",
		im_name => "hosts4_by_vendor",
		im_title => $$lang_vars{hosts4_by_vendor_message},
	);
}



$vendor_host4_table .= "<table class=\"table-bordered\">";
$vendor_host4_table .= "<tr><td colspan=\"3\"><b>$$lang_vars{hosts4_by_vendor_message}</b></td></tr>\n";
	if ( $anz_counts_vendors4 > 0 ) {
		foreach my $key (sort keys(%counts_vendors4)) {
			if ( $key =~ /(${vendor_list})/i ) {
				my $image_name="";
				if ( $key =~ /(hp\s|hewlett.?packard)/i ) {
					$image_name = "hp";
				} elsif ( $key =~ /(alcatel|lucent)/i ) {
					$image_name = "lucent-alcatel";
				} elsif ( $key =~ /(palo.?alto)/i ) {
					$image_name = "palo_alto";
				} elsif ( $key =~ /cyclades/i ) {
					$image_name = "avocent";
				} elsif ( $key =~ /d-link|dlink/i ) {
					$image_name = "dlink";
				} elsif ( $key =~ /okilan|okidata/i ) {
					$image_name = "oki";
				} elsif ( $key =~ /orinoco/i ) {
					$image_name = "lucent-alcatel";
				} elsif ( $key =~ /phaser/i ) {
					$image_name = "xerox";
				} elsif ( $key =~ /minolta/i ) {
					$image_name = "konica";
				} elsif ( $key =~ /check.?point/i ) {
					$image_name = "checkpoint";
				} elsif ( $key =~ /tally|genicom/i ) {
					$image_name = "tallygenicom";
				} elsif ( $key =~ /top.?layer/i ) {
					$image_name = "toplayer";
				} elsif ( $key =~ /seiko|infotec/i ) {
					$image_name = "seiko_infotec";
				} elsif ( $key =~ /silver.?peak/i ) {
					$image_name = "silver_peak";
				} else {
					$image_name = lc($key);
				}

				if ( $image_name ) {
					$vendor_host4_table .= "<tr><td>$key</td><td valign=\"top\"><img src=\"./imagenes/vendors/${image_name}.png\" alt=\"${image_name}\"></td><td><form name=\"search_red\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cc_id_${vendor_cc_id}\" type=\"hidden\"  value=\"$key\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_vendors4{$key}\" style=\"cursor:pointer;\"></form></td></tr>\n";
				} else {
					$vendor_host4_table .= "<tr><td>$key</td><td>$key\"></td><td>$counts_vendors4{$key}</td></tr>\n";
				}
			} else {
				$vendor_host4_table .= "<tr><td>$key</td><td>N/A</td><td><form name=\"search_red\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cc_id_${vendor_cc_id}\" type=\"hidden\"  value=\"$key\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_vendors4{$key}\" style=\"cursor:pointer;\"></form></td></tr>\n";
			}
		}
	} else {
		$vendor_host4_table .= "<tr><td colspan=\"3\"><i><b><font color=\"gray\">N/A</font></b></i></td><tr>\n";
	}
$vendor_host4_table .= "</table>\n";


if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_host_cats6[0] ) {
		$cat_host6_table .= "<table class=\"table-bordered\">\n";
		$cat_host6_table .= "<tr><td><b>$$lang_vars{cat_message}</b></td><td><b>$$lang_vars{hosts1_message}</b></td></tr>\n";
		foreach my $keys (sort keys %counts2_6) {
			if ( $keys eq "NULL" ) {
		#		$count_null=$host_net_locs_count6{$keys};
			} else {
				$cat_host6_table .= "<tr><td>$keys</td><td><form name=\"search_host_${keys}_cat_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cat\" type=\"hidden\"  value=\"$keys\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts2_6{$keys}\" style=\"cursor:pointer;\"></form></td></tr>";
			}
		}
		$cat_host6_table .= "<tr><td>$$lang_vars{without_cat_message}</td><td><form name=\"search_host_NULL_cat_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cat\" type=\"hidden\"  value=\"NULL\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts2_6{'NULL'}\" style=\"cursor:pointer;\"></form></td></tr>" if $counts2_6{'NULL'};
		$cat_host6_table .= "</table>\n";
#		if ( keys (%counts2_6) >= 250 ) {
#			print "<td><font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<td valign=\"top\"><a href=\"./imagenes/dyn/${hosts6_by_host_cat_im_name}_big.png\"><img src=\"./imagenes/dyn/${hosts6_by_host_cat_im_name}.png\" alt=\"$$lang_vars{hosts6_by_host_cat_message} chart\"></a>\n";
#		}
#		print "</td></tr>\n";
	} else {
		$cat_host6_table .= "<tr><td><i><b><font color=\"gray\">N/A</font></b></i></td></tr>\n";
	}
#print "</table>\n";





my %counts_host6_vendor = ();
my $anz_counts_vendors6=scalar(keys(%counts_vendors6));

my @stat_host_vendors6 = $gip->get_stat_host_vendors("$client_id");

if ( $anz_counts_vendors6 > 0 ) {

	$i=0;
	for (@stat_host_vendors6) {
        my $vendor_name = lc($stat_host_vendors6[$i]->[0]);
        if ( ! $counts_vendors6_lc{$vendor_name} ) {
            $i++;
            next;
        }
		$counts_host6_vendor{$vendor_name}++;
        $i++;
	}

	$charts_data_host_vendor6 = $gip->create_stat_pie_chart_data(
		counts => \%counts_host6_vendor,
		type => "loc",
		im_name => "hosts6_by_vendor",
		im_title => $$lang_vars{hosts6_by_vendor_message},
	);
}




#my %counts_host6_vendor = ();
#my $anz_counts_vendors6=scalar(keys(%counts_vendors6));
#if ( $anz_counts_vendors6 > 0 ) {
#
#	foreach my $key (sort keys(%counts_vendors6)) {
#		$counts_host6_vendor{$key}++;
#	}
#
#	$charts_data_host_vendor6 = $gip->create_stat_pie_chart_data(
#		counts => \%counts_host6_vendor,
#		type => "loc",
#		im_name => "hosts6_by_vendor",
#		im_title => $$lang_vars{hosts6_by_vendor_message},
#	);
#}



	$vendor_host6_table .= "<table class=\"table-bordered\">";
	$vendor_host6_table .= "<tr><td colspan=\"3\"><b>$$lang_vars{hosts6_by_vendor_message}</b></td></tr>\n";
	if ( $anz_counts_vendors6 > 0 ) {
		foreach my $key (sort keys(%counts_vendors6)) {
			if ( $key =~ /(${vendor_list})/i ) {
				my $image_name="";
				if ( $key =~ /(aficio|ricoh)/i ) {
					$image_name = "ricoh";
				} elsif ( $key =~ /(hp\s|hewlett.?packard)/i ) {
					$image_name = "hp";
				} elsif ( $key =~ /(alcatel|lucent)/i ) {
					$image_name = "lucent-alcatel";
				} elsif ( $key =~ /(palo.?alto)/i ) {
					$image_name = "palo_alto";
				} elsif ( $key =~ /cyclades/i ) {
					$image_name = "avocent";
				} elsif ( $key =~ /d-link|dlink/i ) {
					$image_name = "dlink";
				} elsif ( $key =~ /okilan|okidata/i ) {
					$image_name = "oki";
				} elsif ( $key =~ /orinoco/i ) {
					$image_name = "lucent-alcatel";
				} elsif ( $key =~ /phaser/i ) {
					$image_name = "xerox";
				} elsif ( $key =~ /minolta/i ) {
					$image_name = "konica";
				} elsif ( $key =~ /check.?point/i ) {
					$image_name = "checkpoint";
				} elsif ( $key =~ /top.?layer/i ) {
					$image_name = "toplayer";
				} elsif ( $key =~ /tally|genicom/i ) {
					$image_name = "tallygenicom";
				} elsif ( $key =~ /seiko|infotec/i ) {
					$image_name = "seiko_infotec";
				} elsif ( $key =~ /silver.?peak/i ) {
					$image_name = "silver_peak";
				} else {
					$image_name = lc($key);
				}
				if ( $image_name ) {
					$vendor_host6_table .= "<tr><td>$key</td><td valign=\"top\"><img src=\"./imagenes/vendors/${image_name}.png\" alt=\"${image_name}\"></td><td><form name=\"search_red\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cc_id_${vendor_cc_id}\" type=\"hidden\"  value=\"$key\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_vendors6{$key}\" style=\"cursor:pointer;\"></form></td></tr>\n";
				} else {
					$vendor_host6_table .= "<tr><td>$key</td><td>$key\"></td><td>$counts_vendors6{$key}</td></tr>\n";
				}
			} else {
				$vendor_host6_table .= "<tr><td>$key</td><td>N/A</td><td><form name=\"search_red\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"cc_id_${vendor_cc_id}\" type=\"hidden\"  value=\"$key\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts_vendors6{$key}\" style=\"cursor:pointer;\"></form></td></tr>\n";
			}
		}
	} else {
		$vendor_host6_table .= "<tr><td colspan=\"3\"><i><b><font color=\"gray\">N/A</font></b></i></td><tr>\n";
	}
$vendor_host6_table .= "</table>\n";
}


if ( $stat_host_locs4[0] ) {
	$site_host4_table .= "<table class=\"table-bordered\">\n";
	$site_host4_table .= "<tr><td><b>$$lang_vars{loc_message}</b></td><td><b>$$lang_vars{hosts1_message}</b></td></tr>\n";
		foreach my $keys (sort keys %counts3_4) {
			if ( $keys eq "NULL" ) {
		#		$count_null=$host_net_locs_count4{$keys};
			} else {
				$site_host4_table .= "<tr><td>$keys</td><td><form name=\"search_host_${keys}_loc_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"loc\" type=\"hidden\" value=\"$keys\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts3_4{$keys}\" style=\"cursor:pointer;\"></form></td></tr>";
			}
		}
		$site_host4_table .= "<tr><td>$$lang_vars{without_loc_message}</td><td><form name=\"search_host_NULL_loc_4\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"loc\" type=\"hidden\" value=\"NULL\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts3_4{'NULL'}\" style=\"cursor:pointer;\"></form></td></tr>" if $counts3_4{'NULL'};

	$site_host4_table .= "</table>\n";
#	if ( keys (%counts3_4) >= 250 ) {
##		print "<td><font color=\"gray\">N/A</font></b></i>\n";
#	} else {
##		print "<td valign=\"top\"><a href=\"./imagenes/dyn/${hosts4_by_host_site_im_name}_big.png\"><img src=\"./imagenes/dyn/${hosts4_by_host_site_im_name}.png\" alt=\"$$lang_vars{hosts4_by_host_site_message} chart\"></a>\n";
#	}
##	print "</td></tr>\n";
} else {
		$site_host4_table .= "<font color=\"gray\">N/A</font>\n";
}
#print "</table>\n";

if ( $ipv4_only_mode ne "yes" ) {
	if ( $stat_host_locs6[0] ) {
		$site_host6_table .= "<table class=\"table-bordered\">\n";
		$site_host6_table .= "<tr><td><b>$$lang_vars{loc_message}</b></td><td><b>$$lang_vars{hosts1_message}</b></td></tr>\n";
		foreach my $keys (sort keys %counts3_6) {
			if ( $keys eq "NULL" ) {
			#	$count_null=$host_net_locs_count6{$keys};
			} else {
				$site_host6_table .= "<tr><td>$keys</td><td><form name=\"search_host_${keys}_loc_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"loc\" type=\"hidden\" value=\"$keys\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts3_6{$keys}\" style=\"cursor:pointer;\"></form></td></tr>";
			}
		}
		$site_host6_table .= "<tr><td>$$lang_vars{without_loc_message}</td><td><form name=\"search_host_NULL_loc_6\" method=\"POST\" action=\"$server_proto://$base_uri/ip_searchip.cgi\" style=\"display:inline;\"><input type=\"hidden\" name=\"search_index\" value=\"true\"> <input name=\"loc\" type=\"hidden\" value=\"NULL\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$counts3_6{'NULL'}\" style=\"cursor:pointer;\"></form></td></tr>" if $counts3_6{'NULL'};
		$site_host6_table .= "</table>\n";
#		if ( keys (%counts3_6) >= 250 ) {
#			print "<td><font color=\"gray\">N/A</font></b></i>\n";
#		} else {
#			print "<td valign=\"top\"><a href=\"./imagenes/dyn/${hosts6_by_host_site_im_name}_big.png\"><img src=\"./imagenes/dyn/${hosts6_by_host_site_im_name}.png\" alt=\"$$lang_vars{hosts6_by_host_site_message} chart\"></a>\n";
#		}
#		print "</td></tr>\n";
#	} else {
#		print "<tr><td><i><b><font color=\"gray\">N/A</font></b></i></td></tr>\n";
	}
#print "</table>\n";
}


# ROW
$stat_struct .= '
  <div class="row m-3">
    <div class="col-6"><h4>' .
        $$lang_vars{hosts_may_message}
    . '</h4></div>
  </div>
  <div class="row m-3">
  </div>
  <div class="row m-3">
    <div class="col-6"><h6>' .
        $$lang_vars{hosts4_by_host_cat_message}
    . '</h6></div>';

if ($ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-6"><h6>' .
        $$lang_vars{hosts6_by_host_cat_message}
    . '</h6></div>';
}
$stat_struct .= '</div>';


$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
              $cat_host4_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostCat" width="8" height="8"></canvas> 
  </div>';

if ($ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
   <div class="col-2">' .
              $cat_host6_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostCat2" width="8" height="8"></canvas> 
    </div>';
}
$stat_struct .= '</div>';


# ROW HOST SITE
$stat_struct .= '
  <div class="row m-3">
  </div>
  <div class="row m-3">
    <div class="col-6"><h6>' .
        $$lang_vars{hosts4_by_host_site_message}
    . '</h6></div>';
if ($ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-6"><h6>' .
        $$lang_vars{hosts6_by_host_site_message}
    . '</h6></div>
  </div>';
}
$stat_struct .= '</div>';


$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
              $site_host4_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostSite" width="8" height="8"></canvas> 
    </div>';

if ($ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-2">' .
              $site_host6_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostSite2" width="8" height="8"></canvas> 
    </div>';
}
$stat_struct .= '</div>';



# ROW HOST VENDOR
$stat_struct .= '
  <div class="row m-3">
  </div>
  <div class="row m-3">
    <div class="col-6"><h6>' .
        $$lang_vars{hosts4_by_vendor_message}
    . '</h6></div>';
if ($ipv4_only_mode ne "yes" ) {
    $stat_struct .= '
    <div class="col-6"><h6>' .
        $$lang_vars{hosts6_by_vendor_message}
    . '</h6></div>';
}
$stat_struct .= '</div>';

# ROW
$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
              $vendor_host4_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostVendor" width="8" height="8"></canvas> 
    </div>';

if ($ipv4_only_mode ne "yes" ) {
$stat_struct .= '
    <div class="col-2">' .
              $vendor_host6_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartHostVendor2" width="8" height="8"></canvas> 
        </div>';
}
$stat_struct .= '</div>';


## TEST END
}

if ( $create_custom_stat ) {
$stat_struct .= '
  <div class="row">
    <div class="col-2">' .
              $stat_table
    . '</div>
    <div class="col-4">
              <canvas id="pieChartStat" width="8" height="8"></canvas> 
    </div>
	</div>';
}


print $stat_struct;



print "<p><br><p><br>\n";
print "<p><b style=\"float: $ori\">$$lang_vars{network_occu_message}</b><br>\n";

print "<form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_percent_usage.cgi\">\n";
print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td align=\"right\">$$lang_vars{percent_network_usage_bigger_than_message} <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 60px\" name=\"percent_usage\" size=\"1\">\n";
my @values_percent_usage = ("1","5","10","20","30","40","50","60","70","80","90","95","98");
foreach (@values_percent_usage) {
	if ( $_ eq 90 ) {
		print "<option selected>$_</option>";
		next;
	}
	print "<option>$_</option>";
}
print "</select>%\n";
print "&nbsp;&nbsp;&nbsp; $$lang_vars{filter_message} <input type=\"text\" size=\"15\" name=\"filter\" value=\"\" maxlength=\"45\">\n";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;v4<input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked>&nbsp;&nbsp;&nbsp;v6<input type=\"checkbox\" name=\"ipv6\" value=\"ipv6\"><font color=\"white\">x</font>&nbsp;&nbsp;&nbsp;";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "<input type=\"hidden\" name=\"stat_type\" value=\"percent_network_bigger\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></td></tr>\n";
print "</table></form>\n";


print "<p>\n";
print "<form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_percent_usage.cgi\">\n";
print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td align=\"right\">$$lang_vars{percent_network_usage_smaller_than_message} <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 60px\" name=\"percent_usage\" size=\"1\">\n";
@values_percent_usage = ("1","3","5","10","20","30","40","50","60","70","80","90","95","98");
foreach (@values_percent_usage) {
	if ( $_ eq 10 ) {
		print "<option selected>$_</option>";
		next;
	}
	print "<option>$_</option>";
}
print "</select>%\n";
print "&nbsp;&nbsp;&nbsp; $$lang_vars{filter_message} <input type=\"text\" size=\"15\" name=\"filter\" value=\"\" maxlength=\"45\">\n";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;v4<input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked>&nbsp;&nbsp;&nbsp;v6<input type=\"checkbox\" name=\"ipv6\" value=\"ipv6\"><font color=\"white\">x</font>&nbsp;&nbsp;&nbsp;";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "<input type=\"hidden\" name=\"stat_type\" value=\"percent_network_smaller\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></td></tr>\n";
print "</table></form>\n";


print "<br><p><b style=\"float: $ori\">$$lang_vars{range_occu_message}</b><br>\n";
print "<form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_percent_usage.cgi\">\n";
print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td align=\"right\">$$lang_vars{percent_range_usage_bigger_than_message} <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 60px\"  name=\"percent_usage\" size=\"1\">\n";
@values_percent_usage = ("1","5","10","20","30","40","50","60","70","80","90","95","98");
foreach (@values_percent_usage) {
	if ( $_ eq 90 ) {
		print "<option selected>$_</option>";
		next;
	}
	print "<option>$_</option>";
}
print "</select>%\n";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;<font color=\"gray\">v4</font><input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked disabled><font color=\"white\">x</font>";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "<input type=\"hidden\" name=\"stat_type\" value=\"percent_range_bigger\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></td></tr>\n";
print "</table></form>\n";

print "<p>\n";
print "<form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_percent_usage.cgi\">\n";
print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td align=\"right\">$$lang_vars{percent_range_usage_smaller_than_message} <select class=\"custom-select custom-select-sm display-inline\" style=\"width: 60px\" name=\"percent_usage\" size=\"1\">\n";
@values_percent_usage = ("1","3","5","10","20","30","40","50","60","70","80","90","95","98");
foreach (@values_percent_usage) {
	if ( $_ eq 10 ) {
		print "<option selected>$_</option>";
		next;
	}
	print "<option>$_</option>";
}
print "</select>%\n";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;<font color=\"gray\">v4</font><input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked disabled><font color=\"white\">x</font>";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "<input type=\"hidden\" name=\"stat_type\" value=\"percent_range_smaller\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></td></tr>\n";
print "</table></form><br>\n";


print "<br><p><b style=\"float: $ori\">$$lang_vars{misc_message}</b><br>\n";
print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td><form  method=\"POST\" action=\"$server_proto://$base_uri/ip_show_networks_host_down.cgi\">$$lang_vars{down_hosts_networks_message} ";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;v4<input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked>&nbsp;&nbsp;&nbsp;v6<input type=\"checkbox\" name=\"ipv6\" value=\"ipv6\"><font color=\"white\">x</font>&nbsp;&nbsp;&nbsp;";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "</td>\n";
print "<td><input type=\"hidden\" name=\"down_hosts\" value=\"down\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></form></td></tr></table>\n";

print "<table border=\"0\" cellspacing=\"10\">\n";
print "<tr><td><form  method=\"POST\" action=\"$server_proto://$base_uri/ip_show_networks_host_down.cgi\">$$lang_vars{down_never_checked_hosts_networks_message} ";
if ( $ipv4_only_mode ne "yes" ) {
	print "&nbsp;&nbsp;&nbsp;v4<input type=\"checkbox\" name=\"ipv4\" value=\"ipv4\" checked>&nbsp;&nbsp;&nbsp;v6<input type=\"checkbox\" name=\"ipv6\" value=\"ipv6\"><font color=\"white\">x</font>&nbsp;&nbsp;&nbsp;";
} else {
	print "<input type=\"hidden\" name=\"ipv4\" value=\"ipv4\">";
}
print "</td>\n";
print "<td><input type=\"hidden\" name=\"down_hosts\" value=\"down_and_never_checked\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><input type=\"submit\" class=\"btn btn-sm\" value=\"$$lang_vars{show_message}\" name=\"B1\"></form></td></tr></table>\n";


if (  $charts_data ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartStat').getContext('2d');
var pieChartStat = new Chart(ctx, {
    type: 'pie',
	$charts_data,
    options: {
    }
});
</script>
EOF
}


if ( $charts_data_net_cats4 && ! $create_custom_stat ) {
$gip->debug("charts_data_net_cats4: $charts_data_net_cats4");
print <<EOF;
<script>
var ctx = document.getElementById('pieChartCat').getContext('2d');
var pieChartCat = new Chart(ctx, {
    type: 'pie',
	$charts_data_net_cats4,
    options: {
    }
});
</script>
EOF
}


if ( $charts_data_net_cats6 && ! $create_custom_stat ) {
print <<EOF;

<script>
var ctx = document.getElementById('pieChartCat2').getContext('2d');
var pieChartCat2 = new Chart(ctx, {
    type: 'pie',
    $charts_data_net_cats6,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_net_sites4 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartSite').getContext('2d');
var pieChartSite = new Chart(ctx, {
    type: 'pie',
    $charts_data_net_sites4,
    options: {
		responsive: true
    }
});
</script>
EOF
}

if ( $charts_data_net_sites6 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartSite2').getContext('2d');
var pieChartSite2 = new Chart(ctx, {
    type: 'pie',
    $charts_data_net_sites6,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_cats4 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostCat').getContext('2d');
var pieChartHostCat = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_cats4,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_cats6 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostCat2').getContext('2d');
var pieChartHostCat2 = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_cats6,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_sites4 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostSite').getContext('2d');
var pieChartHostSite = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_sites4,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_sites6 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostSite2').getContext('2d');
var pieChartHostSite2 = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_sites6,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_vendor4 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostVendor').getContext('2d');
var pieChartHostVendor = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_vendor4,
    options: {
    }
});
</script>
EOF
}

if ( $charts_data_host_vendor6 && ! $create_custom_stat ) {
print <<EOF;
<script>
var ctx = document.getElementById('pieChartHostVendor2').getContext('2d');
var pieChartHostVendor2 = new Chart(ctx, {
    type: 'pie',
    $charts_data_host_vendor6 && ! $create_custom_stat,
    options: {
    }
});
</script>
EOF
}

$select_site =~ s/'/\\'/g;
$select_site =~ s/\n//g;
$select_net_cat =~ s/'/\\'/g;
$select_net_cat =~ s/\n//g;
$select_net_tag =~ s/'/\\'/g;
$select_net_tag =~ s/\n//g;
#$select_tag =~ s/'/\\'/g;
#$select_tag =~ s/\n//g;
$select_host_cat =~ s/'/\\'/g;
$select_host_cat =~ s/\n//g;
$select_host_tag =~ s/'/\\'/g;
$select_host_tag =~ s/\n//g;
$select_dnssg =~ s/'/\\'/g;
$select_dnssg =~ s/\n//g;


print <<EOF;
<script type="text/javascript">
<!--

function changeHideOpts(TYPE){
    console.log("changing form elements:" + TYPE);
    if ( TYPE == "$$lang_vars{loc_message}" ) {
        document.getElementById('Hide_net_filter_details').innerHTML = '$select_site';
    } else if ( TYPE == "$$lang_vars{cat_message}" ) {
        document.getElementById('Hide_net_filter_details').innerHTML = '$select_net_cat';
    } else if ( TYPE == "Tag" ) {
        document.getElementById('Hide_net_filter_details').innerHTML = '$select_net_tag';
    } else if ( TYPE == "DNSSG" ) {
        document.getElementById('Hide_net_filter_details').innerHTML = '$select_dnssg';
EOF


foreach my $cc_name ( keys %custom_net_columns_select_name_items ) {
	my $select_cc = "";
	print "} else if ( TYPE == \"$cc_name\" ) {\n";

	$select_cc .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
	my $items = $custom_net_columns_select_name_items{$cc_name} || "";
	foreach my $it ( @$items ) {
		$select_cc .= "<option>$it</option>";
	}
	$select_cc .= "</select>";
	$select_cc =~ s/'/\\'/g;
	$select_cc =~ s/\n//g;

	print "    document.getElementById('Hide_net_filter_details').innerHTML = '$select_cc';\n";
}
	

print <<EOF;
    } else {
        document.getElementById('Hide_net_filter_details').innerHTML = '';
    }
}


function changeHostHideOpts(TYPE){
    console.log("changing form elements:" + TYPE);
    if ( TYPE == "$$lang_vars{loc_message}" ) {
        document.getElementById('Hide_host_filter_details').innerHTML = '$select_site';
    } else if ( TYPE == "$$lang_vars{cat_message}" ) {
        document.getElementById('Hide_host_filter_details').innerHTML = '$select_host_cat';
    } else if ( TYPE == "Tag" ) {
        document.getElementById('Hide_host_filter_details').innerHTML = '$select_host_tag';
EOF


foreach my $cc_name ( keys %custom_host_columns_select_name_items ) {
	my $select_cc = "";
	print "} else if ( TYPE == \"$cc_name\" ) {\n";

	$select_cc .= "<select class=\"custom-select custom-select-sm display-inline\" style=\"width: 100px\" name=\"filter_value\" size=\"1\">\n";
	my $items = $custom_host_columns_select_name_items{$cc_name} || "";
	foreach my $it ( @$items ) {
		$select_cc .= "<option>$it</option>";
	}
	$select_cc .= "</select>";
	$select_cc =~ s/'/\\'/g;
	$select_cc =~ s/\n//g;

	print "    document.getElementById('Hide_host_filter_details').innerHTML = '$select_cc';\n";
}
	

print <<EOF;
    } else {
        document.getElementById('Hide_host_filter_details').innerHTML = '';
    }
}

-->
</script>
EOF

$gip->print_end("$client_id", "", "", "");

