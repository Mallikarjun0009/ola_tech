#!/usr/bin/perl -w -T

use strict;
use Socket;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $base_uri = $gip->get_base_uri();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
my $loc_id=$daten{'loc_id'} || "-1";
my $loc_id_check = $loc_id;
$loc_id_check = "" if $loc_id_check eq "-1";
my $loc=$daten{'loc'} || "";
$loc_id_check = $gip->get_loc_id("$client_id","$loc") if $loc && ! $loc_id_check;

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
        loc_id_rw=>"$loc_id_check",
	);
}


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_ll_message}","$vars_file");

# Check SITE permission
if ( $user_management_enabled eq "yes" ) {
    $gip->check_loc_perm_rw("$client_id","$vars_file", "$locs_rw_perm", "$loc", "$loc_id");
}


my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}

my $ll_id=$daten{'ll_id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $ll_id;
my $phone_number=$daten{'phone_number'};
$phone_number = "" if $phone_number eq "0";
my $ll_client_id=$daten{'ll_client_id'};
my $comment=$daten{'comment'} || "";
my $description=$daten{'description'} || "";
my $type=$daten{'type'} || "";
my $service=$daten{'service'} || "";
my $device=$daten{'device'} || "";
my $room=$daten{'room'} || "";
my $ad_number=$daten{'ad_number'} || "";

my @values_clientes=$gip->get_ll_clients("$client_id");
my $anz_ll_clients=$gip->count_ll_clients("$client_id");
my @values_locations=$gip->get_loc_all("$client_id");
my $loc_hash=$gip->get_loc_hash("$client_id");

my @line_columns=$gip->get_line_columns("$client_id");
my %values_lines_cc=$gip->get_line_column_values_hash("$client_id"); # $values{"${column_id}_${$line_id}"}="$entry";
my @cc_values=$gip->get_custom_line_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","line");




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
        selected_value => $ll_client_id,
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
	selected_value => $type,
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
	selected_value => $service,
    width => "10em",
    size => 1,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "description",
    value => $description,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{phone_number_message},
    id => "phone_number",
    value => $phone_number,
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{administrative_number_message},
    id => "ad_number",
    required => "required",
    value => $ad_number,
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
	selected_value => $loc_id,
    width => "10em",
    size => 1,
    required => "required",
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{room_message},
    id => "room",
    value => $room,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{connected_device_message},
    id => "device",
    value => $device,
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
    value => $comment,
);


$j = 0;
foreach ( @line_columns ) {
    @item_order = ();
    $required = "";
    my $cc_id=$line_columns[$j]->[0];
    my $cc_name=$line_columns[$j]->[1];
    my $mandatory=$line_columns[$j]->[2] || "";
	my $entry=$values_lines_cc{"${cc_id}_${ll_id}"} || "";

    $required = "required" if $mandatory;

    if ( $cc_name ) {
        if ( exists $custom_colums_select{$cc_id} ) {
			my $selected ="";
            # CC column is SELECT
            my $select_values = $custom_colums_select{$cc_id}->[2];
            push @item_order, "";
            foreach (@$select_values) {
                my $opt = $gip->remove_whitespace_se("$_");
                push @item_order, $opt;
                $selected = "selected" if $opt eq $entry;
            }

            $form_elements .= GipTemplate::create_form_element_select(
                name => $cc_name,
                item_order => \@item_order,
                id => $cc_name,
                selected_value => $selected,
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


$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $ll_id,
    name => "ll_id",
);


$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_ll_form",
    link => "./ip_mod_ll.cgi",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.mod_ll_form.type.focus();\n";
print "</script>\n";








#print "<form name=\"modll_form\" method=\"POST\" action=\"./ip_mod_ll.cgi\">\n";
#print "<table border=\"0\" cellpadding=\"5\" cellspacing=\"2\">\n";
#
#print "<tr><td $align>$$lang_vars{ll_client_message}</td><td $align1>";
#my $j=0;
#if ( $anz_ll_clients >= 1 ) {
#
#        print "<select name=\"ll_client_id\" size=\"1\">";
#        print "<option></option>\n";
#        my $opt;
#        foreach $opt(@values_clientes) {
#            if ( $values_clientes[$j]->[0] == "-1" ) {
#                $j++;
#                next;
#            }
#            if ( $values_clientes[$j]->[0] == $ll_client_id ) {
#                print "<option value=\"$values_clientes[$j]->[0]\" selected>$values_clientes[$j]->[1]</option>";
#            } else {
#                print "<option value=\"$values_clientes[$j]->[0]\">$values_clientes[$j]->[1]</option>";
#            }
#            $j++;
#        }
#        print "</select></td></tr>\n";
#} else {
#        print "<font color=\"gray\"><i>$$lang_vars{no_ll_clients_message}</i></font></td></tr>\n";
#}
#
##print "<tr><td $align>$$lang_vars{tipo_message}</td><td $align1><input name=\"type\" type=\"text\" value=\"$type\" size=\"15\" maxlength=\"50\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{tipo_message}</td><td $align1><select name=\"type\" size=\"1\">";
#print "<option></option>";
#my $values_types = $custom_colums_select{"9998"}->[2];
#foreach (@$values_types) {
#    my $type_opt = $_;
#    if ( $type eq $type_opt ) {
#        print "<option value=\"$type_opt\" selected>$type_opt</option>";
#    } else {
#        print "<option value=\"$type_opt\">$type_opt</option>";
#    }
#}
#print "</select></td><td>";
#
##print "<tr><td $align>$$lang_vars{service_message}</td><td $align1><input name=\"service\" type=\"text\" value=\"$service\" size=\"15\" maxlength=\"50\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{service_message}</td><td $align1><select name=\"service\" size=\"1\">";
#print "<option></option>";
#my $values_service = $custom_colums_select{"9999"}->[2];
#foreach (@$values_service) {
#    my $opt = $_;
#    if ( $service eq $opt ) {
#        print "<option value=\"$opt\" selected>$opt</option>";
#    } else {
#        print "<option value=\"$opt\">$opt</option>";
#    }
#}
#print "</select></td><td>";
#
#print "<tr><td $align>$$lang_vars{description_message}</td><td $align1><input name=\"description\" type=\"text\" value=\"$description\" size=\"15\" maxlength=\"50\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{phone_number_message}</td><td $align1><input name=\"phone_number\" type=\"text\" value=\"$phone_number\" size=\"15\" maxlength=\"30\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{administrative_number_message}</td><td $align1><input name=\"ad_number\" type=\"text\" value=\"$ad_number\"  size=\"15\" maxlength=\"50\"></td></tr>\n";
#
#print "<tr><td $align>$$lang_vars{loc_message}</td><td $align1><select name=\"loc_id\" size=\"1\">";
#print "<option value=\"-1\"></option>";
#
#$j=0;
#foreach (@values_locations) {
#	if ( $values_locations[$j]->[0] eq "-1" ) {
#		$j++;
#		next;
#	}
#	if ( $values_locations[$j]->[0] eq $loc_id ) {
#		print "<option value=\"$loc_id\" selected>$values_locations[$j]->[1]</option>";
#	} else {
#		print "<option value=\"$values_locations[$j]->[0]\">$values_locations[$j]->[1]</option>";
#	}
#	$j++;
#}
#
#print "</select></td><td>";
#print "<tr><td $align>$$lang_vars{room_message}</td><td $align1><input name=\"room\" type=\"text\" value=\"$room\" size=\"15\" maxlength=\"100\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{connected_device_message}</td><td $align1><input name=\"device\" type=\"text\" value=\"$device\" size=\"15\" maxlength=\"100\"></td></tr>\n";
#print "<tr><td $align>$$lang_vars{comentario_message}</td><td $align1><input name=\"comment\" type=\"text\" value=\"$comment\" size=\"30\" maxlength=\"500\"></td></tr>\n";
#
#
#$j=0;
#foreach ( @line_columns ) {
#    my $cc_id=$line_columns[$j]->[0];
#    my $cc_name=$line_columns[$j]->[1];
#    my $entry=$values_lines_cc{"${cc_id}_${ll_id}"} || "";
#    if ( $cc_name ) {
#        if ( exists $custom_colums_select{$cc_id} ) {
#            # CC column is a select
#            my $select_values = $custom_colums_select{$cc_id}->[2];
#
#            print "<tr><td $align>$cc_name</td><td><select name=\"$cc_name\" size=\"1\">\n";
#            print "<option></option>";
#            foreach (@$select_values) {
#                my $opt = $_;
#                $opt = $gip->remove_whitespace_se("$opt");
#                my $selected = "";
#                $selected = "selected" if $opt eq $entry;
#                print "<option value=\"$opt\" $selected>$opt</option>";
#            }
#        print "</select></td></tr>\n";
#        $j++;
#        next;
#        } else {
#            print "<tr><td $align>$cc_name</td><td $align1><input name=\"$cc_name\" value=\"$entry\" type=\"text\" size=\"15\" maxlength=\"1000\"></td></tr>";
#        }
#    }
#    $j++;
#}
#
#
#
#print "<td><input type=\"hidden\" name=\"ll_id\" value=\"$ll_id\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\"><br><input type=\"submit\" value=\"$$lang_vars{submit_message}\" name=\"B2\" class=\"input_link_w\"></td>\n";

#print "</table>\n";
#print "</form>\n";

$gip->print_end("$client_id", "", "", "");

