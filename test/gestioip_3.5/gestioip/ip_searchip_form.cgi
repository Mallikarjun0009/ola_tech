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

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri=$gip->get_base_uri();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
my ($locs_ro_perm, $locs_rw_perm);
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my @values_locations=$gip->get_loc("$client_id");
my @values_categorias=$gip->get_cat("$client_id");
my @values_utype=$gip->get_utype();
my $anz_clients_all=$gip->count_clients("$client_id");
my $loc_hash=$gip->get_loc_hash("$client_id");


my $ipv4_only_mode=$global_config[0]->[5] || "yes";

$gip->print_init("$$lang_vars{buscar_host_message}","$$lang_vars{advanced_host_search_message}","$$lang_vars{advanced_host_search_message}","$vars_file","$client_id");

my @cc_values=$gip->get_custom_host_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","host");


#my $align="align=\"right\"";
#my $align1="";
#my $ori="left";
#if ( $vars_file =~ /vars_he$/ ) {
#	$align="align=\"left\"";
#	$align1="align=\"right\"";
#	$ori="right";
#}

#print "<br><form method=\"POST\" name=\"searchip\" action=\"$server_proto://$base_uri/ip_searchip.cgi\">\n";
#print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\"><tr><td $align>";

my $ip_version = "v4";

my ($form, $form_elements, @item_order, $opt_name, $opt_value);
my %items;
my $onclick;

my $maxlength = 15;

my ($disabled_ipv4, $disabled_ipv6, $checked_ipv4, $checked_ipv6);
$disabled_ipv4=$disabled_ipv6=$checked_ipv4=$checked_ipv4="";

if ( $anz_clients_all > 1 ) {

  $form_elements .= '
  <div class="form-group row">
    <div class="col-sm-1 control-label">' . $$lang_vars{client_independent_message} . '</div>
    <div class="col-sm-5">';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="yes" id="client_independent" name="client_independent">
          <span class="custom-control-label pr-2"></span>
        </label>
     </div>';

    $form_elements .= '</div></div>';
}

if ( $ipv4_only_mode eq "no" ) {

    $form_elements .= '
  <div class="form-group row">
    <div class="col-sm-1 control-label">' . $$lang_vars{ip_version_message} . '</div>
    <div class="col-sm-5">';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="ipv4" id="ip_version" name="ipv4" selected>
          <span class="custom-control-label pr-2">IPv4</span>
        </label>
     </div>';

    $form_elements .= '
    <div class="custom-control custom-control-inline">
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="ipv6" id="ip_version" name="ipv6">
          <span class="custom-control-label pr-2">IPv6</span>
        </label>
     </div>';

    $form_elements .= '</div></div>';
}

my $hint_text = '
        <label class="custom-control custom-checkbox">
        <input type="checkbox" class="custom-control-input custom-control-inline" value="on" id="hostname_exact" name="hostname_exact">
          <span class="custom-control-label pr-2">' . $$lang_vars{exact_match_message} . '</span>
        </label>';

$form_elements .= GipTemplate::create_form_element_text(
    label => "$$lang_vars{hostname_message}",
    id => "hostname",
    size => 30,
    maxlength => $maxlength,
    hint_text => $hint_text,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => "$$lang_vars{host_db_ID_message}",
    id => "host_id_db",
    size => 10,
    maxlength => $maxlength,
);

# DESCRIPTION

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "host_descr",
    maxlength => 100,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comentario",
    maxlength => 100,
);

# SITE
@item_order = ();
push @item_order, "";
foreach my $opt( @values_locations) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        next;
    }
	if ( $locs_rw_perm || $locs_ro_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ || $locs_ro_perm eq "9999" || $locs_ro_perm =~ /^$loc_id_opt$/ || $locs_ro_perm =~ /^${loc_id_opt}_/ || $locs_ro_perm =~ /_${loc_id_opt}$/ || $locs_ro_perm =~ /_${loc_id_opt}_/ ) {
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
    without_search => $$lang_vars{without_loc_message},
);

# CATEGORY
@item_order = ();
foreach my $opt( @values_categorias) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) {
        unshift @item_order, "EMPTY_OPTION";
        next;
    }
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{cat_message},
    item_order => \@item_order,
    id => "cat",
    width => "10em",
#    selected_value => 'EMPTY_OPTION',
    without_search => $$lang_vars{without_cat_message},
);

# UTYPE
@item_order = ();
foreach my $opt( @values_utype) {
    my $name = $opt->[0] || "";
    if ( $name eq "NULL" ) { 
        unshift @item_order, "EMPTY_OPTION";
        next;
    }
    push @item_order, $name;
}

$form_elements .= GipTemplate::create_form_element_select(
    name => $$lang_vars{update_type_message},
    item_order => \@item_order,
    id => "cat_red",
    width => "10em",
    without_search => $$lang_vars{without_utype_message},
);



$form_elements .= GipTemplate::create_form_element_hidden(
    value => "true",
    name => "search_index",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);


for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
    my $cc_name  = $cc_values[$k]->[0];
    my $cc_id  = $cc_values[$k]->[1];
    if ( $cc_name ) {
        if ( exists $custom_colums_select{$cc_id} ) {
            # CC column is a select

            my $select_values = $custom_colums_select{$cc_id}->[2];

            @item_order = ();
            push @item_order, "";
            foreach my $opt(@$select_values) {
                $opt = $gip->remove_whitespace_se("$opt");
                push @item_order, $opt;
            }

            $form_elements .= GipTemplate::create_form_element_select(
                name => $cc_name,
                item_order => \@item_order,
                id => "cc_id_${cc_id}",
                width => "10em",
            );

            next;
        } elsif ( $cc_name eq "CM" ) {

            @item_order = ();
            push @item_order, "";
            push @item_order, "enabeld";
            push @item_order, "disabled";

            $form_elements .= GipTemplate::create_form_element_select(
                name => "CM",
                item_order => \@item_order,
                id => "cc_id_${cc_id}",
                width => "10em",
            );
			
       } elsif ( $cc_name eq "SNMPGroup" ) {

                my @snmp_groups=$gip->get_snmp_groups("$client_id");

                my $j=0;
                if ( ! $snmp_groups[0] ) {

                    $form_elements .= GipTemplate::create_form_element_comment(
                        label => "SNMPGroup",
                        comment => "<font color=\"gray\"><i>$$lang_vars{no_snmp_groups_message}</i></font>",
                        id => "cc_id_${cc_id}",
                    );

                } else {

                    $j = 0;
                    @item_order = ();
                    push @item_order, "";
                    foreach my $opt(@snmp_groups) {
                        $opt_name = $snmp_groups[$j]->[1];
                        push @item_order, $opt_name;
                        $j++;
                    }

                    $form_elements .= GipTemplate::create_form_element_select(
                        name => $cc_name,
                        item_order => \@item_order,
                        id => "cc_id_${cc_id}",
                        width => "10em",
                    );
                }
       } elsif ( $cc_name eq "Tag" ) {
                my @tags = $gip->get_custom_host_column_ids_from_name("$client_id", "Tag");

				my $form_elements_tag = "";
				$form_elements_tag = $gip->print_tag_form("$client_id","$vars_file","","host") if @tags;

				$form_elements .= $form_elements_tag;

		} else {
#			print "<tr><td $align>$cc_name</td><td><input type=\"text\" name=\"cc_id_${cc_id}\" size=\"15\"></td></tr>";

            $form_elements .= GipTemplate::create_form_element_text(
                label => $cc_name,
                id => "cc_id_${cc_id}",
                maxlength => 500,
            );

		}
	}
}

#print "</tr><tr><td $align>$$lang_vars{ia_wrap_message}<td colspan=\"3\" $align1><input type=\"checkbox\" name=\"int_admin\" value=\"y\">\n";

$form_elements .= GipTemplate::create_form_element_checkbox(
	label => $$lang_vars{ia_wrap_message},
	id => "int_admin",
	value => "y",
);



$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{buscar_message},
    name => "B2",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "searchip",
    link => "./ip_searchip.cgi",
    method => "POST",
);


print $form;

print "<script type=\"text/javascript\">\n";
print "document.searchip.hostname.focus();\n";
print "</script>\n";

$gip->print_end("$client_id", "", "", "");
