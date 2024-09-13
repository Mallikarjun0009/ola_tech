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


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="update_net_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $order_by=$daten{'order_by'} || "red_auf";
my $ip_version_ele = $daten{'ip_version_ele'} || $gip->get_ip_version_ele();


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{network_mass_update_message}","$vars_file");

my $mass_update_type=$daten{'mass_update_type'};
$gip->print_error("$client_id","$$lang_vars{select_mass_update_type}") if ! $mass_update_type;

my @custom_columns = $gip->get_custom_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","network");
my $loc_hash=$gip->get_loc_hash("$client_id");

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

my $anz_nets=$daten{'anz_nets'} || "0";

my $k;
my $j=0;
my $mass_update_network_ids="";
for ($k=0;$k<=$anz_nets;$k++) {
	if ( $daten{"mass_update_red_submit_${k}"} ) {
		$mass_update_network_ids.=$daten{"mass_update_red_submit_${k}"} . "_";
		$j++;
	}
}
$mass_update_network_ids =~ s/_$//;
$gip->print_error("$client_id","$$lang_vars{select_network_message}") if ! $mass_update_network_ids;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} $mass_update_network_ids (1)") if ($mass_update_network_ids !~ /[0-9_]/ );

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (2)") if $ip_version_ele !~ /^(v4|v6|46)$/ ;

my $start_entry=$daten{'start_entry'} || '0';
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (3)") if $start_entry !~ /^\d{1,5}$/;

my @values_locations=$gip->get_loc("$client_id");
my @values_utype=$gip->get_utype();
my @values_cat_net=$gip->get_cat_net("$client_id");

my $color = "white";


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);
$j = 0;

foreach (@mass_update_types_standard) {
	if ( $_ eq $$lang_vars{description_message} ) {

		$form_elements .= GipTemplate::create_form_element_text(
			label => $$lang_vars{description_message},
			id => "descr",
			maxlength => 100,
		);

	}
	if ( $_ eq $$lang_vars{loc_message} ) {

		@item_order = ();
		foreach my $opt(@values_locations) {
			my $name = $opt->[0] || "";
			if ( $name eq "NULL" ) {
				push @item_order, "";
				next;
			}
			if ( $locs_rw_perm ) {
				my $loc_id_opt = $loc_hash->{$name} || "";
				if ($locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ ) {
					push @item_order, $name;
				}
			} else {
				push @item_order, $name;
			}
		}

		$form_elements .= GipTemplate::create_form_element_select(
			name => $$lang_vars{loc_message},
			item_order => \@item_order,
			id => "loc",
			width => "10em",
			required => "required",
		);

	}
	if ( $_ eq $$lang_vars{cat_message} ) {


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
			id => "cat_net",
			width => "10em",
			required => "required",
		);

	}
	if ( $_ eq $$lang_vars{comentario_message} ) {


		$form_elements .= GipTemplate::create_form_element_textarea(
			label => $$lang_vars{comentario_message},
			rows => '5',
			cols => '30',
			id => "comentario",
			width => "10em",
			maxlength => 500,
		);
	}
	if ( $_ eq $$lang_vars{sinc_message} ) {


		$form_elements .= GipTemplate::create_form_element_checkbox(
			label => $$lang_vars{sinc_message},
			value => "y",
			id => "vigilada",
		);
	}

    if ( $_ eq $$lang_vars{update_mode_message} ) {

		@item_order = ();
		%items = ();
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
			id => "dyn_dns_updates",
			width => "14em",
			size => 1,
		);
    }
}

my $cc_anz = scalar(@mass_update_types);
my %mass_elements;
foreach my $mass_element(@mass_update_types) {
	$mass_elements{$mass_element}++;
}

my $cc_form_elements = $gip->print_custom_net_colums_form("$client_id","$vars_file","","$ip_version_ele", \%mass_elements) || "";

$form_elements .= $cc_form_elements;

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $ip_version_ele,
    name => "ip_version_ele",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $mass_update_network_ids,
    name => "mass_update_network_ids",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $mass_update_type,
    name => "mass_update_type",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $cc_anz,
    name => "cc_anz",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $start_entry,
    name => "start_entry",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "modred_form",
    link => "./ip_modred_mass_update.cgi",
    method => "POST",
);

print $form;

$gip->print_end("$client_id","$vars_file","", "$daten");
