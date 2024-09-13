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
	my $required_perms="read_line_perm,update_line_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $dyn_dns_updates_enabled=$global_config[0]->[19] || "no";

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{insert_dns_zone_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
        $align="align=\"left\"";
        $align1="align=\"right\"";
        $ori="right";
}

my @values_dns_user=$gip->get_dns_user("$client_id");
my @values_dns_keys=$gip->get_dns_keys("$client_id");
my $anz_dns_user=scalar(@values_dns_user);
my $anz_dns_keys=scalar(@values_dns_keys);

my $j;

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $opt_id, $onclick, $required);

$form_elements .= "<span id='HideOpts'>";

my $element_name = GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    required => "required",
#    margin_bottom => "5",
);

my $element_server_purpose = "";
if ( $dyn_dns_updates_enabled eq "yes" ) {
    $onclick = "onchange='changeHidePurpose(this.value);'";
    $element_server_purpose .= GipTemplate::create_form_element_choice_radio(
        label => $$lang_vars{purpose_message},
        id => "purpose",
        value1 => "zone_transfer",
        value2 => "gip_dns_sync",
        text1 => "$$lang_vars{zone_transfer_or_update_message}",
        text2 => "$$lang_vars{dyn_gip_dns_updates_message}",
        onclick => $onclick,
        checked1 => 1,
    );
}


# Server type
@item_order = ("GSS-TSIG", "TSIG");

$onclick = "onchange='changeHideDNSUser(this.value);'";
my $element_server_type .= GipTemplate::create_form_element_select(
    label => $$lang_vars{server_type_message},
    id => "server_type",
    item_order => \@item_order,
    width => "10em",
	onclick => $onclick,
    required => "required",
);


# DNS USER

my $element_dns_user = "";
if ( $anz_dns_user >= 1 ) {

	$j = 0;
	undef %items;
	@item_order = ();
	push @item_order, "";
	foreach my $opt(@values_dns_user) {
		$opt_id = $values_dns_user[$j]->[0];
		$opt_name = $values_dns_user[$j]->[1];
		push @item_order, $opt_name;
		$items{$opt_name} = $opt_id;
		$j++;
	}

	$element_dns_user .= GipTemplate::create_form_element_select(
		label => $$lang_vars{dns_user_lb_message},
		id => "dns_user_id",
		item_order => \@item_order,
		items => \%items,
		width => "10em",
		required => "required",
	);
} else {
	$element_dns_user .= GipTemplate::create_form_element_comment(
		label => $$lang_vars{dns_user_lb_message},
		id => "dns_user_id",
		comment => "$$lang_vars{no_dns_user_message}",
	);
}


# DNS Keys
$j = 0;
undef %items;
@item_order = ();
push @item_order, "";
foreach my $opt(@values_dns_keys) {
    $opt_id = $values_dns_keys[$j]->[0];
    $opt_name = $values_dns_keys[$j]->[2];
    push @item_order, $opt_name;
    $items{$opt_name} = $opt_id;
    $j++;
}

#Key Name
my $element_dns_keys .= GipTemplate::create_form_element_select(
    label => $$lang_vars{tsig_key_message},
    id => "dns_user_id",
    item_order => \@item_order,
    items => \%items,
    width => "10em",
    required => "required",
);

# Type
@item_order = ("","A","AAAA","PTR");

my $element_type .= GipTemplate::create_form_element_select(
    label => $$lang_vars{tipo_message},
    id => "type",
    item_order => \@item_order,
    width => "5em",
    required => "required",
);

# DNS Server
my $element_dns_server = GipTemplate::create_form_element_textarea(
    label => $$lang_vars{dns_server_message},
    id => "dyn_dns_server",
    required => "required",
);

# TTL
my $element_ttl = GipTemplate::create_form_element_text(
    label => $$lang_vars{ttl_message},
    id => "ttl",
    required => "required",
);

# Description
my $element_description = GipTemplate::create_form_element_text(
    label => $$lang_vars{description_message},
    id => "description",
);

my $form_elements_dyn_dns = $element_server_type;
$form_elements_dyn_dns .= "<span id=\"HideDNSuser\">";
$form_elements_dyn_dns .= $element_dns_user;
$form_elements_dyn_dns .= "</span>";
$form_elements_dyn_dns .= $element_dns_server;
$form_elements_dyn_dns .= $element_ttl;

$form_elements .= $element_name;
$form_elements .= $element_server_purpose;
$form_elements .= $element_type;
$form_elements .= "<span id=\"HideDynDNS\"></span>";
$form_elements .= $element_description;

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

#$form_elements =~ s/'/\\'/g;

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_dns_zone_form",
    link => "./ip_insert_dns_zone.cgi",
    method => "POST",
    autocomplete => "off",
);

print $form;

$element_dns_user =~ s/'/\\'/g;
$element_dns_keys =~ s/'/\\'/g;
$form_elements_dyn_dns =~ s/'/\\'/g;
#$element_server_purpose =~ s/'/\\'/g;


print <<EOF;

<SCRIPT LANGUAGE="Javascript" TYPE="text/javascript">
<!--

function changeHideDNSUser(VAL){
    console.log("changing form elements:" + VAL);
    if( VAL == "GSS-TSIG" ) {
        document.getElementById('HideDNSuser').innerHTML = '$element_dns_user';
    } else if ( VAL == "TSIG" )  {
        document.getElementById('HideDNSuser').innerHTML = '$element_dns_keys';
  }
}

function changeHidePurpose(VAL){
    console.log("changeHidePurpose:" + VAL);
    if( VAL == "zone_transfer" ) {
        document.getElementById('HideDynDNS').innerHTML = '';
    } else if ( VAL == "gip_dns_sync" )  {
        document.getElementById('HideDynDNS').innerHTML = '$form_elements_dyn_dns';
  }
}

//-->
</SCRIPT>

EOF

print "<p><br><p><br><p>\n";

print "<script type=\"text/javascript\">\n";
print "   document.insert_dns_zone_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");

