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
use lib '../modules';
use GestioIP;
use Net::IP;
use Net::IP qw(:PROC);

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");


my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $red_num=$daten{'red_num'} || "";
if ( $red_num !~ /^\d{1,5}$/ ) {
        $gip->print_init("gestioip","$$lang_vars{modificar_red_message}","$$lang_vars{modificar_red_message}","$vars_file","$client_id");
        $gip->print_error("$client_id",$$lang_vars{formato_red_malo_message}) ;
}

my @values_redes = $gip->get_red("$client_id","$red_num");
my $loc_val = $values_redes[0]->[3] || "-1";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $global_dyn_dns_updates_enabled=$global_config[0]->[19] || "";
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_net_perm,update_net_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
        loc_id_rw=>"$loc_val",
	);
}


my $order_by=$daten{'order_by'} || "red_auf";

my $ip_version_ele = $daten{'ip_version_ele'} || $gip->get_ip_version_ele();
my $parent_network_id = $daten{'parent_network_id'} || "";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{modificar_red_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (version_ele)") if $ip_version_ele !~ /^(v4|v6|46)$/ ;

my $start_entry=$daten{'start_entry'} || '0';
$gip->print_error("$client_id",$$lang_vars{formato_malo_message}) if $start_entry !~ /^\d{1,5}$/;

my $loc=$daten{'loc'} || "";


my $red = "$values_redes[0]->[0]" || "";
my $BM = "$values_redes[0]->[1]" || "";
my $descr = "$values_redes[0]->[2]" || "";
$descr = "" if ( $descr eq "NULL" );
my $vigilada = $values_redes[0]->[4] || "n";
my $comentario = $values_redes[0]->[5] || "";
my $cat_net = $values_redes[0]->[6] || "-1";
my $ip_version = $values_redes[0]->[7] || "";
my $rootnet = $values_redes[0]->[9] || 0;
my $dyn_dns_updates = $values_redes[0]->[10] || 1;
$comentario = "" if ( $comentario eq "NULL" );
$red = ip_compress_address ($red, 6) if $ip_version eq "v6";




my $referer=$daten{'referer'} || "";
my ($bm_new);
if ( ! $referer ) {
	if ( $ENV{HTTP_REFERER} !~ /ip_modred_list/ ) {
		$referer="host_list_view";
	} else {
		$referer="red_view";
	}
}

$cat_net=$gip->get_cat_net_from_id("$client_id","$cat_net");
my @values_locations=$gip->get_loc("$client_id");
my @values_utype=$gip->get_utype();
my @values_cat_net=$gip->get_cat_net("$client_id");
my $loc_hash=$gip->get_loc_hash("$client_id");

my $cc_form_elements = $gip->print_custom_net_colums_form("$client_id","$vars_file","$red_num","$ip_version") || "";

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);
my $j = 0;

$form_elements .= GipTemplate::create_form_element_comment(
    label => $$lang_vars{redes_message},
    comment => $red,
);

if ( $rootnet == 0 ) {
    $form_elements .= GipTemplate::create_form_element_text(
        label => "BM",
        value => $BM,
        id => "BM_new",
        required => "required",
        size => 3,
        maxlength => 3,
    );
} else {
    $form_elements .= GipTemplate::create_form_element_comment(
        label => "BM",
        value => $BM,
    );

    $form_elements .= GipTemplate::create_form_element_hidden(
        value => $BM,
        name => "BM_new",
    );
}

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    value => $descr,
    id => "descr",
	maxlength => 100,
    required => "required",
);

# SITE
@item_order = ();
foreach my $opt(@values_locations) {
    my $name = $opt->[0] || "";
	if ( $name eq "NULL" ) {
		push @item_order, "";
		next;
	}
    if ( $locs_rw_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ ) {
            push @item_order, $name;
        }
    } else {
        push @item_order, $name;
    }
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{loc_message},
    item_order => \@item_order,
    selected_value => $loc,
    id => "loc",
    width => "10em",
    required => "required",
);

# CATEGORY
@item_order = ();
foreach my $opt(@values_cat_net) {
    my $name = $opt->[0] || "";
	if ( $name eq "NULL" ) {
		push @item_order, "";
		next;
	}
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{cat_message},
    item_order => \@item_order,
    selected_value => $cat_net,
    id => "cat_net",
    width => "10em",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_textarea(
    label => $$lang_vars{comentario_message},
	value => $comentario,
    rows => '5',
    cols => '30',
    id => "comentario",
    width => "10em",
	maxlength => 500,
);

my $vigilada_checked = "";
my $vigilada_disabled = "";
if ( ! $rootnet ) {
    $vigilada_checked="checked" if ($vigilada eq "y" );
} else {
	$vigilada_disabled = "disabled";
}

$form_elements .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{sinc_message},
    id => "vigilada",
    value => "y",
    width => "10em",
	checked => $vigilada_checked,
	disabled => $vigilada_disabled,
	
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $BM,
    name => "BM",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $red,
    name => "red",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $start_entry,
    name => "start_entry",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $referer,
    name => "referer",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $order_by,
    name => "order_by",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $ip_version_ele,
    name => "ip_version_ele",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $red_num,
    name => "red_num",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $parent_network_id,
    name => "parent_network_id",
);

$form_elements .= $cc_form_elements;


if ( $global_dyn_dns_updates_enabled eq "yes" ) {

    @item_order = ();
    undef %items;

    push @item_order, $$lang_vars{'no_update_message'};
    $items{$$lang_vars{'no_update_message'}} = 1;
    push @item_order, $$lang_vars{'a_and_ptr_message'};
    $items{$$lang_vars{'a_and_ptr_message'}} = 2;
    push @item_order, $$lang_vars{'a_update_only_message'};
    $items{$$lang_vars{'a_update_only_message'}} = 3;
    push @item_order, $$lang_vars{'ptr_update_only_message'};
    $items{$$lang_vars{'ptr_update_only_message'}} = 4;
    

    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{update_mode_message},
        items => \%items,
        item_order => \@item_order,
        selected_value => $dyn_dns_updates,
        id => "dyn_dns_updates",
        width => "14em",
        size => 1,
    );

}

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "modred_form",
    link => "./ip_modred.cgi",
    method => "POST",
);

print $form;


$gip->print_end("$client_id","$vars_file","", "$daten");
