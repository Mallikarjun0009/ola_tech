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
	my $required_perms="manage_sites_and_cats_perm";
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

$gip->print_error_with_head(title=>"$$lang_vars{gestioip_message}",headline=>"$$lang_vars{new_site_message}",notification=>"$error_message",vars_file=>"$vars_file",client_id=>"$client_id") if $error_message;


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{new_site_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my @site_columns=$gip->get_site_columns("$client_id");
my %values_sites_cc=$gip->get_site_column_values_hash("$client_id"); # $values{"${column_id}_${$site_id}"}="$entry";
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","site");



my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $required);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{loc_message},
    id => "site",
	required => "required",
);

my $j = 0;
foreach ( @site_columns ) {
	@item_order = ();
	$required = "";
    my $cc_id=$site_columns[$j]->[0];
    my $cc_name=$site_columns[$j]->[1];
	my $mandatory=$site_columns[$j]->[2] || "";
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
    form_id => "insert_site_form",
    link => "$server_proto://$base_uri/res/ip_insert_site.cgi",
    method => "POST",
);

print $form;


print "<p>\n";

print "<script type=\"text/javascript\">\n";
print "document.insert_site_form.site.focus();\n";
print "</script>\n";

print <<EOF;
<script>
// Example starter JavaScript for disabling form submissions if there are invalid fields
(function() {
  'use strict';
  window.addEventListener('load', function() {
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    var forms = document.getElementsByClassName('needs-validation');
    // Loop over them and prevent submission
    var validation = Array.prototype.filter.call(forms, function(form) {
      form.addEventListener('submit', function(event) {
        if (form.checkValidity() === false) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add('was-validated');
      }, false);
    });
  }, false);
})();
</script>
EOF


$gip->print_end("$client_id", "", "", "");
