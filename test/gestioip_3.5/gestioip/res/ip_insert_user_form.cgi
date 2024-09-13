#!/usr/bin/perl -w -T

# Copyright (C) 2014 Marc Uebel


use strict;
use DBI;
use lib '../modules';
use GestioIP;


my $gip = GestioIP -> new();
my $daten=<STDIN> || "";
my %daten=$gip->preparer($daten);

my $server_proto=$gip->get_server_proto();
my $base_uri = $gip->get_base_uri();
my ($lang_vars,$vars_file)=$gip->get_lang();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_user_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

# Parameter check
my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{new_user_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{new_user_message}","$vars_file");

my $new_apache_config = $gip->check_new_apache_config() || 0;

my $user=$ENV{'REMOTE_USER'};
my %values_user_groups=$gip->get_user_group_hash("$client_id");

if ( ! %values_user_groups ) {
	print "<p><br>$$lang_vars{no_user_group_define_message}<br>";
	print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"$$lang_vars{atras_message}\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM><p><br><p>\n";
	$gip->print_end("$client_id", "", "", "");
}


my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
    required => "required",
);

my $form_elements_pass = "";
if ( $new_apache_config ) {
    @item_order = ();
    my @values_types = ("$$lang_vars{local_message}", "LDAP");
    foreach my $opt(@values_types) {
        my $name = $opt || "";
        push @item_order, $name;
    }

    $onclick = "onchange='changeHidePass(this.value);'";
    $form_elements .= GipTemplate::create_form_element_select(
        name => $$lang_vars{tipo_message},
        item_order => \@item_order,
        id => "type",
        width => "10em",
        onclick => $onclick,
        required => "required",
    );

    $form_elements_pass .= GipTemplate::create_form_element_text(
        label => $$lang_vars{login_pass_message},
        id => "login_pass",
        type => "password",
    );

    $form_elements_pass .= GipTemplate::create_form_element_text(
        label => $$lang_vars{retype_login_pass_message},
        id => "retype_login_pass",
        type => "password",
    );

    $form_elements .= "<span id='HidePass'>";
    $form_elements .= $form_elements_pass;
    $form_elements .= "</span>";
}



@item_order = ();
undef %items;

if ( $user_management_enabled eq "yes" ) {

	while ( my ($key, @value) = each(%values_user_groups) ) {
			my $name=$value[0]->[0];
			my $id=$key;
			push @item_order, $name;
			$items{$name} = $id;
	}

	$form_elements .= GipTemplate::create_form_element_select(
		name => $$lang_vars{user_group_message},
		items => \%items,
		item_order => \@item_order,
		id => "group_id",
		width => "10em",
		size => 1,
	);
} else {
	$form_elements .= GipTemplate::create_form_element_hidden(
		value => 1,
		name => "group_id",
	);
}

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{mail_message},
    id => "email",
);


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{phone_message},
    id => "phone",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{add_message},
    name => "B2",
);

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_user_form",
    link => "./ip_insert_user.cgi",
    autocomplete => "off",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
	print "document.insert_user_form.name.focus();\n";
print "</script>\n";

$form_elements_pass =~ s/'/\\'/g;
$form_elements_pass =~ s/\n//g;


print <<EOF;
<script type="text/javascript">
<!--
function changeHidePass(VAL){
    if ( VAL == "$$lang_vars{local_message}" ) {
        document.getElementById('HidePass').innerHTML = '$form_elements_pass';
    } else {
        document.getElementById('HidePass').innerHTML = '';
    }
}
-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
