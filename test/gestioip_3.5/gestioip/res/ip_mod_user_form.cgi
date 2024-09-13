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
my $id = $daten{'id'};

my $error_message=$gip->check_parameters(
        vars_file=>"$vars_file",
        client_id=>"$client_id",
        id=>"$id",
) || "";

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{update_user_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_user_message}","$vars_file");

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 1") if ! $id;
$gip->print_error("$client_id","$$lang_vars{formato_malo_message} 2") if $id !~ /^\d{1,5}$/;


my $user=$ENV{'REMOTE_USER'};
my %values_user_groups=$gip->get_user_group_hash("$client_id");
my %values_users=$gip->get_user_hash("$client_id");

if ( ! %values_user_groups ) {
	print "<p><br>$$lang_vars{no_user_group_define_message}<br>";
	print "<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"$$lang_vars{atras_message}\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM><p><br>\n";
	$gip->print_end("$client_id", "", "", "");
}

my $name=$values_users{$id}[0];
my $group_id=$values_users{$id}[1] || "";
my $phone=$values_users{$id}[2] || "";
my $email=$values_users{$id}[3] || "";
my $comment=$values_users{$id}[4] || "";
my $type=$values_users{$id}[6] || "---";

my $new_apache_config = $gip->check_new_apache_config() || 0;

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $onclick);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    value => $name,
    id => "name",
    readonly => "1",
);

if ( $new_apache_config ) {
    $form_elements .= GipTemplate::create_form_element_comment(
        label => $$lang_vars{tipo_message},
        value => $type,
        id => "type",
    );
}

if ( $user_management_enabled eq "yes" ) {
    @item_order = ();
    undef %items;

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
        selected_value => $group_id,
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
    value => $email,
    id => "email",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{phone_message},
    value => $phone,
    id => "phone",
);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    value => $comment,
    id => "comment",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $id,
    name => "id",
);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_user_form",
    link => "./ip_mod_user.cgi",
    autocomplete => "off",
    method => "POST",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "    document.mod_user_form.name.focus();\n";
print "</script>\n";


$gip->print_end("$client_id", "", "", "");
