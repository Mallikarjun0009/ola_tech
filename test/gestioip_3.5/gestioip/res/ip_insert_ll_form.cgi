#!/usr/bin/perl -w -T

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
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_line_perm,create_line_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my @line_columns=$gip->get_line_columns("$client_id");
my %values_lines_cc=$gip->get_line_column_values_hash("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","line");
my $loc_hash=$gip->get_loc_hash("$client_id");


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_ll_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @values_clientes=$gip->get_ll_clients("$client_id");
my $anz_ll_clients=$gip->count_ll_clients("$client_id");
my @values_locations=$gip->get_loc_all("$client_id");


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick, $required);

@item_order = ();
undef %items;

my $j = 0;
if ( $anz_ll_clients > "1" ) {
	foreach my $opt(@values_clientes) {
		my $value = $opt->[0] || "";
		my $name = $opt->[1] || "";
		if ( $value == "-1" ) {
			push @item_order, "M1_OPTION";
			$j++;
			next;
		}
		push @item_order, $name;
		$items{$name} = $value;
		$j++;
	}

	$form_elements .= GipTemplate::create_form_element_select(
		label => $$lang_vars{ll_client_message},
		items => \%items,
		item_order => \@item_order,
		id => "ll_client_id",
		width => "10em",
		size => 1,
	);

} else {
    $form_elements .= GipTemplate::create_form_element_comment(
        label => $$lang_vars{ll_clients_message},
        id => $$lang_vars{ll_clients_message},
        comment => "$$lang_vars{no_ll_clients_message}",
    );
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => "-1",
		name => "ll_client_id",
	);
}

# TYPE
my $values_types = $custom_colums_select{"9998"}->[2];
@item_order = ();
push @item_order, "";
foreach (@$values_types) {
    my $opt = $_;
	push @item_order, $opt;
}

$form_elements .= GipTemplate::create_form_element_select(
	label => $$lang_vars{tipo_message},
	item_order => \@item_order,
	id => "type",
	width => "10em",
	size => 1,
	first_no_option_selected => 1,
	required => "required",
);


# SERVICE
my $values_service = $custom_colums_select{"9999"}->[2];
@item_order = ();
push @item_order, "";
foreach my $opt (@$values_service) {
	push @item_order, $opt;
}

$form_elements .= GipTemplate::create_form_element_select(
	label => $$lang_vars{service_message},
	item_order => \@item_order,
	id => "service",
	width => "10em",
	size => 1,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "description",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{phone_number_message},
    id => "phone_number",
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{administrative_number_message},
    id => "ad_number",
	required => "required",
);


# SITE
@item_order = ();
undef %items;

push @item_order, "M1_OPTION";
foreach my $opt(@values_locations) {
	my $value = $opt->[0] || "";
	my $name = $opt->[1] || "";
	if ( $value == "-1" ) {
		next;
	}
	if ( $locs_rw_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ ) {
            push @item_order, $name;
			$items{$name} = $value;
        }
    } else {
        push @item_order, $name;
		$items{$name} = $value;
    }
}

$form_elements .= GipTemplate::create_form_element_select(
	label => $$lang_vars{loc_message},
	items => \%items,
	item_order => \@item_order,
	id => "loc_id",
	width => "10em",
	size => 1,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{room_message},
    id => "room",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{connected_device_message},
    id => "device",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
);

$j = 0;
foreach ( @line_columns ) {
    @item_order = ();
    $required = "";
    my $cc_id=$line_columns[$j]->[0];
    my $cc_name=$line_columns[$j]->[1];
    my $mandatory=$line_columns[$j]->[2] || "";
    $required = "required" if $mandatory;

    if ( $cc_name ) {
        if ( exists $custom_colums_select{$cc_id} ) {
            # CC column is SELECT
            my $select_values = $custom_colums_select{$cc_id}->[2];
            push @item_order, "";
            foreach (@$select_values) {
                my $opt = $gip->remove_whitespace_se("$_");
                push @item_order, $opt;
            }

            $form_elements .= GipTemplate::create_form_element_select(
                name => $cc_name,
                item_order => \@item_order,
                id => $cc_name,
                width => "10em",
                required => $required,
            );

        } else {
            # CC column is TEXT
            $form_elements .= GipTemplate::create_form_element_text(
                label => $cc_name,
                id => $cc_name,
                required => $required,
            );
        }
    }
    $j++;
}

# HIDDEN
$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


## BUTTON

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{add_message},
    name => "B2",
);


## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_line_form",
    link => "./ip_insert_ll.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.insert_line_form.type.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
