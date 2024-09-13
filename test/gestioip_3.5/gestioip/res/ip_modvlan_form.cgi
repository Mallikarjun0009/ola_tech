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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{edit_vlan_message}","$vars_file");


my $vlan_id=$daten{'vlan_id'} || "";
$gip->print_error("$client_id","$$lang_vars{formato_malo_message}") if ! $vlan_id;
my $vlan_name=$daten{'vlan_name'};
my $vlan_num=$daten{'vlan_num'};
my $vlan_provider_id=$daten{'vlan_provider_id'};
my $bg_color=$daten{'bg_color'} || "";
my $font_color=$daten{'font_color'} || "";
my $comment=$daten{'comment'} || "";


my @values_vlan=$gip->get_vlan("$client_id","$vlan_id");
my @values_clientes=$gip->get_vlan_providers("$client_id");

my $asso_vlan = $values_vlan[0]->[7] || "";
my ($bg_color_val,$font_color_val);

my $bg_color_old=$values_vlan[0]->[3];
if ( ! $values_vlan[0]->[3] ) { $bg_color_old = "white"; $bg_color_val="blan";}
if ( $bg_color_old eq "gold" || $bg_color_old eq "amar" ) { $bg_color_val="amar";
} elsif ( $bg_color_old eq "LightCyan" || $bg_color_old eq "azulcc" ) { $bg_color_val="azulcc";
} elsif ( $bg_color_old eq "LightBlue" || $bg_color_old eq "azulc" ) { $bg_color_val="azulc";
} elsif ( $bg_color_old eq "dodgerblue" || $bg_color_old eq "azulo" ) { $bg_color_val="azulo";
} elsif ( $bg_color_old eq "LimeGreen" || $bg_color_old eq "verc" ) { $bg_color_val="verc";
} elsif ( $bg_color_old eq "SeaGreen" || $bg_color_old eq "vero" ) { $bg_color_val="vero";
} elsif ( $bg_color_old eq "pink" ) { $bg_color_val="pink";
} elsif ( $bg_color_old eq "white" || $bg_color_old eq "blan" ) { $bg_color_val="blan";
} elsif ( $bg_color_old eq "black" || $bg_color_old eq "negro" ) { $bg_color_val="negr";
} elsif ( $bg_color_old eq "brown" || $bg_color_old eq "maro" ) { $bg_color_val="maro";
} elsif ( $bg_color_old eq "red" || $bg_color_old eq "rojo" ) { $bg_color_val="rojo";
} elsif ( $bg_color_old eq "DarkOrange" || $bg_color_old eq "orano" ) { $bg_color_val="orano";
}

my $font_color_old=$values_vlan[0]->[4] || "";
if ( ! $font_color_old ) { $font_color_old = "black"; $font_color_val="negr"; }
if ( $font_color_old eq "gold" || $font_color_old eq "amar" ) { $font_color_val="amar";
} elsif ( $font_color_old eq "LightCyan" || $font_color_old eq "azulcc" ) { $font_color_val="azulcc";
} elsif ( $font_color_old eq "LightBlue" || $font_color_old eq "azulc" ) { $font_color_val="azulc";
} elsif ( $font_color_old eq "dodgerblue" || $font_color_old eq "azulo" ) { $font_color_val="azulo";
} elsif ( $font_color_old eq "LimeGreen" || $font_color_old eq "cerc" ) { $font_color_val="verc";
} elsif ( $font_color_old eq "SeaGreen" || $font_color_old eq "vero" ) { $font_color_val="vero";
} elsif ( $font_color_old eq "pink" ) { $font_color_val="pink";
} elsif ( $font_color_old eq "white" || $font_color_old eq "blan" ) { $font_color_val="blan";
} elsif ( $font_color_old eq "black" || $font_color_old eq "negr" ) { $font_color_val="negr";
} elsif ( $font_color_old eq "negr" ) { $font_color_val="negr";
} elsif ( $font_color_old eq "brown" || $font_color_old eq "maro" ) { $font_color_val="maro";
} elsif ( $font_color_old eq "red" || $font_color_old eq "rojo" ) { $font_color_val="rojo";
} elsif ( $font_color_old eq "DarkOrange" ) { $font_color_val="orano";
}


my $anz_vlan_providers=$gip->count_vlan_providers("$client_id");


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{vlan_number_message},
    value => $vlan_num,
    id => "vlan_num",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{vlan_name_message},
    value => $vlan_name,
    id => "vlan_name",
    required => "required",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    value => $comment,
    id => "comment",
);

if ( $anz_vlan_providers >= "1" ) {
    my $j = 0;
    foreach my $opt(@values_clientes) {
        $opt_name = $values_clientes[$j]->[0] || "";
        $opt_value = $values_clientes[$j]->[1];
        push @item_order, $opt_name;
        $items{$opt_name} = $opt_value;
        $j++;
    }

    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{vlan_providers_message},
        item_order => \@item_order,
		items => \%items,
		selected_value => $vlan_provider_id,
        id => "vlan_provider_id",
        width => "10em",
    );

} else {
    $form_elements .= GipTemplate::create_form_element_comment(
        label => $$lang_vars{vlan_provider_message},
        comment => $$lang_vars{no_vlan_providers_message},
    );
}


$form_elements .= '
<div class="form-group row">
<label class="control-label col-sm-1" for="' . $$lang_vars{bg_message} . '">' . $$lang_vars{bg_message} . '</label>
<div class="col-sm-10">
<select name="bg_color" class="custom-select" size="3" style="width:150px">';
if ( $bg_color_old ) {
        $form_elements .= "<OPTION SELECTED class=\"$bg_color_old\">$bg_color_val</OPTION>";
}
$form_elements .= '
<OPTION class="gold" value="amar">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</OPTION>
<OPTION class="DarkOrange" value="orano"></OPTION>
<OPTION class="brown" value="maro"></OPTION>
<OPTION class="red" value="rojo"></OPTION>
<OPTION class="pink" value="pink"></OPTION>
<OPTION class="LightCyan" value="azulcc"></OPTION>
<OPTION class="LightBlue" value="azulc"></OPTION>
<OPTION class="dodgerblue" value="azulo"></OPTION>
<OPTION class="LimeGreen" value="verc"></OPTION>
<OPTION class="SeaGreen" value="vero"></OPTION>
<OPTION class="white" value="blan"></OPTION>
<OPTION class="black" value="negr"></OPTION>
</SELECT>
</div>
</div>';


$form_elements .= '
<div class="form-group row">
<label class="control-label col-sm-1" for="' . $$lang_vars{font_message} . '">' . $$lang_vars{font_message} . '</label>
<div class="col-sm-10">
<select name="font_color" class="custom-select" size="3" style="width:150px">';
if ( $font_color_old ) {
        $form_elements .= "<OPTION SELECTED class=\"$font_color_old\">$font_color_val</OPTION>";
}
$form_elements .= '
<OPTION class="gold" value="amar">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</OPTION>
<OPTION class="DarkOrange" value="orano"></OPTION>
<OPTION class="brown" value="maro"></OPTION>
<OPTION class="red" value="rojo"></OPTION>
<OPTION class="LightCyan" value="azulcc"></OPTION>
<OPTION class="LightBlue" value="azulc"></OPTION>
<OPTION class="dodgerblue" value="azulo"></OPTION>
<OPTION class="LimeGreen" value="verc"></OPTION>
<OPTION class="SeaGreen" value="vero"></OPTION>
<OPTION class="white" value="blan"></OPTION>
<OPTION class="black" value="negr"></OPTION>
</SELECT>
</div>
</div>';

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $vlan_id,
    name => "vlan_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);


$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "modvlan_form",
    link => "./ip_modvlan.cgi",
    method => "POST",
);

print $form;

print "<p><br><p><br><p>\n";

$gip->print_end("$client_id", "", "", "");

