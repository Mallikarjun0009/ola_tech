#!/usr/bin/perl -w -T

# Copyright (C) 2020 Marc Uebel

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
use POSIX qw(strftime);
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
	my $required_perms="manage_scheduled_jobs_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $loc_hash=$gip->get_loc_hash("$client_id");

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{update_job_message}","$vars_file");

my $anz_ll_clients=$gip->count_ll_clients("$client_id");
my @values_locations=$gip->get_loc_all("$client_id");
my @values_smtp_server = $gip->get_smtp_server("$client_id");


my $id=$daten{'id'} || "";

my $values = $gip->get_scheduled_job_hash("$client_id","id");
my $name=$values->{$id}[0];
my $start_date=$values->{$id}[1] || "";
my $end_date=$values->{$id}[12];
my $run_once=$values->{$id}[3] || "";
my $status_id=$values->{$id}[4];
#my $status=$status_hash{$id};
my $comment=$values->{$id}[5];
my $arguments=$values->{$id}[6];
my $cron_time=$values->{$id}[7];
my $next_run=$values->{$id}[8];
my $repeat_interval=$values->{$id}[9];
my $discovery_type=$values->{$id}[10];
#my $job_type=$job_type_hash{$job_type_id};

my $disabled = "";
my $checked = "";
my $selected = "";

$cron_time =~ /^(.+) (.+) (.+) (.+) (.+)$/;
my $interval_minutes=$1;
my $interval_hours=$2;
my $interval_months=$3;
my $interval_day_of_month=$4;
my $interval_day_of_week=$5;

my $interval;
if ( $interval_months =~ /\*/ && $interval_day_of_month =~ /\*/ && $interval_day_of_week =~ /\*/ ) {
	$interval = 1;
} elsif ( $interval_day_of_week =~ /\d/ ) {
	$interval = 2;
} elsif ( $interval_day_of_month =~ /\d/ ) {
	$interval = 3;
}

$interval_minutes = "NULL_VALUE" if $interval_minutes eq "0";
$interval_minutes = "$$lang_vars{all_message}" if $interval_minutes eq "*";
$interval_hours = "NULL_VALUE" if $interval_hours eq "0";
$interval_hours = "$$lang_vars{all_message}" if $interval_hours eq "*";

print <<EOF;
<script type='text/javascript' src='$server_proto://$base_uri/js/PrintRedTabUnir.js' language='javascript'></script>
EOF

my ($form, $form_elements, @item_order, %items, $opt_name, $opt_value, $opt_id, $onclick, $required, $selected_value, $display);
my ($form_elements_global_discovery, $form_elements_network_snmp, $form_elements_host_dns, $form_elements_host_snmp, $form_elements_vlan, $form_elements_changes_only);
$form_elements_global_discovery=$form_elements_network_snmp=$form_elements_host_dns=$form_elements_host_snmp=$form_elements_vlan=$form_elements_changes_only="";
my @values_types;


# Name
$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{name_message},
    id => "name",
	required => "required",
	value => $name,
);


# DISCOVERY TYPE

my $cm_enabled = $gip->check_cm_enabled() || "no";

@item_order = ("$$lang_vars{global_discovery_message}", "$$lang_vars{network_discovery_message}", "$$lang_vars{host_discovery_dns_message}","$$lang_vars{host_discovery_snmp_message}", "$$lang_vars{vlan_discovery_message}","$$lang_vars{import_dhcp_leases_message}","$$lang_vars{local_database_backup_message}","$$lang_vars{cloud_discovery_aws_message}","$$lang_vars{cloud_discovery_azure_message}","$$lang_vars{cloud_discovery_gcp_message}");

#@item_order = ("$$lang_vars{global_discovery_message}", "$$lang_vars{network_discovery_message}", "$$lang_vars{host_discovery_dns_message}","$$lang_vars{host_discovery_snmp_message}", "$$lang_vars{vlan_discovery_message}", "$$lang_vars{import_dhcp_leases_message}","$$lang_vars{local_database_backup_message}");

if ( $cm_enabled eq "yes" ) {
    push @item_order, "$$lang_vars{cmm_job_message}";
}

$onclick = "onchange='changeHideOpts(this.value);'";
 
my $i = 1;
foreach (@item_order) {
    my $opt = $_;
    $items{$opt} = $i++;
}

$form_elements .= GipTemplate::create_form_element_select(
	label => $$lang_vars{tipo_message},
	item_order => \@item_order,
	items => \%items,
	onclick => $onclick,
	id => "discovery_type_disabled",
	width => "10em",
	size => 1,
	required => "required",
	selected_value => $discovery_type,
    disabled => 1,
);
$form_elements .= GipTemplate::create_form_element_hidden(
    value => $discovery_type,
    name => "discovery_type",
);

# STATUS
my @values_status = ("$$lang_vars{enabled_message}", "$$lang_vars{disabled_message}");
@item_order = ();
foreach (@values_status) {
    my $opt = $_;
	push @item_order, $opt;
}
undef %items;

$i = 1;
foreach (@item_order) {
    my $opt = $_;
    $items{$opt} = $i++;
}

$form_elements .= GipTemplate::create_form_element_select(
	label => $$lang_vars{status_message},
	item_order => \@item_order,
	items => \%items,
	id => "status",
	width => "10em",
	size => 1,
#	first_no_option_selected => 1,
	required => "required",
	selected_value => $status_id,
);



## RUN ONLY ONCE
my $readonly = 1;
my $execution_time_disabled = 1;
if ( $run_once ) {
	$checked = 1;
    $execution_time_disabled = "";
}
$onclick = "";
#$onclick = "onchange='disableJobInterval(\"$next_run\");'";
$form_elements .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{run_only_once_message},
    id => "run_once",
    value => 1,
    readonly => 1,
    onclick => $onclick,
    checked => $checked,
);

# EXECUTION TIME
my $element_execution_time = GipTemplate::create_form_element_text(
    label => $$lang_vars{execution_time_message},
    id => "execution_time",
    required => "required",
    value => "$start_date",
    disabled => $execution_time_disabled,
);

## START TIME
my $element_start_date .= GipTemplate::create_form_element_text(
    label => $$lang_vars{start_date_job_message},
    id => "start_date",
    value => "$start_date",
    required => "required",
    hint_text => $$lang_vars{time_explic_message},
);


my $element_end_date .= GipTemplate::create_form_element_text(
    label => $$lang_vars{end_date_job_message},
    id => "end_date",
    value => "$end_date",
    hint_text => $$lang_vars{time_explic_message},
);


# EXECUTION INTERVAL 
@item_order = ("$$lang_vars{daily_message}", "$$lang_vars{weekly_message}", "$$lang_vars{monthly_message}");
undef %items;

$i = 1;
foreach (@item_order) {
    my $opt = $_;
    $items{$opt} = $i++;
}
$onclick = "onchange='hideIntervalDetail(this.value);'";
my $element_execution_interval .= GipTemplate::create_form_element_select(
	label => $$lang_vars{execution_interval_message},
	item_order => \@item_order,
	items => \%items,
	id => "interval",
	width => "8em",
	size => 1,
    selected_value => $interval,
	hint_text => "$$lang_vars{at_message}",
	onclick => $onclick,
	no_row_end => 1,
);

# INTERVAL HOUR
my @repeat_interval = ("$$lang_vars{all_message}", 0..23);
$selected_value = $interval_hours;
$selected_value =~ s/,/\|/g;
my $element_interval_hours .= GipTemplate::create_form_element_select(
	item_order => \@repeat_interval,
	id => "interval_hours",
	width => "4em",
	size => 3,
	multiple => 1,
	hint_text => "$$lang_vars{hours_message} $$lang_vars{and_message}",
	no_label => 1,
	no_row_start => 1,
	no_row_end => 1,
	required => "required",
    selected_value => "$selected_value",
);

# INTERVAL MINUTES
@repeat_interval = (0..59);
$selected_value = $interval_minutes;
$selected_value =~ s/,/\|/g;
my $element_interval_minutes .= GipTemplate::create_form_element_select(
	item_order => \@repeat_interval,
	id => "interval_minutes",
	width => "4em",
	size => 3,
	multiple => 1,
	hint_text => $$lang_vars{minutes_message},
	no_label => 1,
	no_row_start => 1,
	no_row_end => 1,
	required => "required",
    selected_value => "$selected_value",
);

# DAY OF MONTH
#@repeat_interval = ("$$lang_vars{all_message}",1..31);
$display = "";
if ( $interval == 1 || $interval == 2 ) {
	$display = "none";
}
$selected_value = $interval_day_of_month;
$selected_value =~ s/,/\|/g;
@repeat_interval = (1..31);
my $element_day_of_month .= GipTemplate::create_form_element_select(
	item_order => \@repeat_interval,
	id => "interval_day_of_month",
	width => "4em",
	size => 3,
    display => $display,
	multiple => 1,
	no_label => 1,
	before_text => $$lang_vars{every_message},
	before_text_span_id => "before_text_interval_day_of_month",
#	hint_text => $$lang_vars{day_of_month_message},
#	hint_text_span_id => "hint_text_interval_day_of_month",
	no_row_start => 1,
	no_row_end => 1,
    selected_value => $selected_value,
);
 

# INTERVAL MONTH
undef %items;
@item_order = ("$$lang_vars{all_message}", "$$lang_vars{jan_message}", "$$lang_vars{feb_message}", "$$lang_vars{mar_message}", "$$lang_vars{apr_message}", "$$lang_vars{may_message}", "$$lang_vars{jun_message}", "$$lang_vars{jul_message}", "$$lang_vars{aug_message}", "$$lang_vars{sep_message}", "$$lang_vars{oct_message}", "$$lang_vars{nov_message}", "$$lang_vars{dec_message}");
%items = (
    $$lang_vars{all_message} => "$$lang_vars{all_message}",
    $$lang_vars{jan_message} => "1",
    $$lang_vars{feb_message} => "2",
    $$lang_vars{mar_message} => "3",
    $$lang_vars{apr_message} => "4",
    $$lang_vars{may_message} => "5",
    $$lang_vars{jun_message} => "6",
    $$lang_vars{jul_message} => "7",
    $$lang_vars{aug_message} => "8",
    $$lang_vars{sep_message} => "9",
    $$lang_vars{oct_message} => "10",
    $$lang_vars{nov_message} => "11",
    $$lang_vars{dec_message} => "12",
);

$display = "";
if ( $interval == 1 || $interval == 2 ) {
	$display = "none";
}
$selected_value = $interval_months;
$selected_value =~ s/,/\|/g;
my $element_interval_months .= GipTemplate::create_form_element_select(
	item_order => \@item_order,
	items => \%items,
	id => "interval_months",
	width => "8em",
	size => 3,
    display => "none",
	multiple => 1,
	no_label => 1,
	before_text => $$lang_vars{of_message},
	before_text_span_id => "before_text_interval_months",
	no_row_start => 1,
	no_row_end => 1,
    selected_value => $selected_value,
);


# INTERVAL DAY OF WEEK
undef %items;
#@item_order = ("$$lang_vars{all_message}", "$$lang_vars{mo_message}", "$$lang_vars{di_message}", "$$lang_vars{mi_message}", "$$lang_vars{do_message}", "$$lang_vars{fr_message}", "$$lang_vars{sa_message}", "$$lang_vars{so_message}");
@item_order = ("$$lang_vars{mo_message}", "$$lang_vars{di_message}", "$$lang_vars{mi_message}", "$$lang_vars{do_message}", "$$lang_vars{fr_message}", "$$lang_vars{sa_message}", "$$lang_vars{so_message}");
 
#$items{$$lang_vars{all_message}} = "all";
$items{$$lang_vars{mo_message}} = 1;
$items{$$lang_vars{di_message}} = 2;
$items{$$lang_vars{mi_message}} = 3;
$items{$$lang_vars{do_message}} = 4;
$items{$$lang_vars{fr_message}} = 5;
$items{$$lang_vars{sa_message}} = 6;
$items{$$lang_vars{so_message}} = 7;

$display = "";
if ( $interval == 1 || $interval == 3 ) {
	$display = "none";
}
$selected_value = $interval_day_of_week;
$selected_value =~ s/,/\|/g;
my $element_day_of_week .= GipTemplate::create_form_element_select(
	item_order => \@item_order,
	items => \%items,
	id => "interval_day_of_week",
	width => "8em",
	size => 3,
    display => $display,
#	first_no_option => 1,
	multiple => 1,
	no_label => 1,
	before_text => $$lang_vars{every_message},
	before_text_span_id => "before_text_interval_day_of_week",
#	hint_text => $$lang_vars{day_of_week_message},
#	hint_text_span_id => "hint_text_interval_day_of_week",
	no_row_start => 1,
    selected_value => $selected_value,
);

if ( $run_once ) {
	$form_elements .= $element_execution_time;
	$form_elements .= "<span id='HideExecutionTime'>";
	$form_elements .= "</span>";
} else {
	$form_elements .= "<span id='HideExecutionTime'>";
	$form_elements .= $element_start_date;
	$form_elements .= $element_end_date;
	$form_elements .= $element_execution_interval;
	$form_elements .= $element_interval_hours;
	$form_elements .= $element_interval_minutes;
	$form_elements .= $element_day_of_month;
	$form_elements .= $element_interval_months;
	$form_elements .= $element_day_of_week;
	$form_elements .= "</span>";
}

my $form_elements_execution_time .= $element_execution_time;
my $form_elements_interval .= $element_start_date;
$form_elements_interval .= $element_end_date;
$form_elements_interval .= $element_execution_interval;
$form_elements_interval .= $element_interval_hours;
$form_elements_interval .= $element_interval_minutes;
$form_elements_interval .= $element_day_of_month;
$form_elements_interval .= $element_interval_months;
$form_elements_interval .= $element_day_of_week;


$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{comentario_message},
    id => "comment",
    value => $comment,
);


###############
# Job specific parameters
################

my @tags;
my ($before_text_tags);

$form_elements .= "<p><br><h5>$$lang_vars{job_options_message}</h5><br>\n";


### FORM ELEMENTS ALL

# Verbose
$checked = "";
if ( $arguments =~ /--verbose/ ) {
	$checked = 1;
}
my $element_verbose .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{verbose_message},
    id => "verbose",
    value => "verbose",
    checked => $checked,
);

# Debug
$checked = "";
if ( $arguments =~ /--x/ ) {
	$checked = 1;
}
my $element_debug .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{debug_message},
    id => "debug",
    value => "debug",
    checked => $checked,
);

# send result by mail
my $send_mail = "";
$checked = "";
if ( $arguments =~ /--mail/ ) {
	$checked = 1;
	$send_mail = 1;
}

$onclick = "onchange='changeHideMail(this.value);'";
my $element_send_mail .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{send_result_by_mail_message},
    id => "send_result_by_mail",
    value => "send_result_by_mail",
	hint_text => $$lang_vars{send_result_by_mail_explic_message},
    onclick => $onclick,
	checked => $checked,
);

$onclick = "onchange='changeHideMailBackup(this.value);'";
my $element_send_mail_backup .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{send_result_by_mail_message},
    id => "send_result_by_mail",
    value => "send_result_by_mail",
	hint_text => $$lang_vars{send_result_by_mail_explic_message},
    onclick => $onclick,
	checked => $checked,
);

## only added mail
#$checked = "";
#if ( $arguments =~ /--only_added_mail/ ) {
#	$checked = 1;
#}
#my $element_only_added_mail .= GipTemplate::create_form_element_checkbox(
#    label => $$lang_vars{only_added_mail_message},
#    id => "only_added_mail",
#    value => "only_added_mail",
#	hint_text => $$lang_vars{only_added_mail_explic_message},
#	checked => $checked,
#);

# send changes_only
$checked = "";
if ( $arguments =~ /--changes_only/ ) {
	$checked = 1;
}
my $element_send_changes_only .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{send_changes_only_message},
    id => "send_changes_only",
    value => "send_changes_only",
    hint_text => $$lang_vars{send_changes_only_explic_message},
	checked => $checked,
);

# MAIL recipients
my $mail_recipients = "";
if ( $arguments =~ /--mail_to/ ) {
    $arguments =~ /--mail_to="(.+?)"\s/;
    $mail_recipients = $1;
}
my $element_mail_recipients .= GipTemplate::create_form_element_text(
    label => $$lang_vars{mail_recipients_message},
    id => "mail_recipients",
    required => "required",
    value => $mail_recipients,
);

# SMTP SERVER
undef %items;
my $j = 0;
my $default_from = "";
@item_order = ();
push @item_order, "";
foreach my $opt(@values_smtp_server) {
    $opt_id = $values_smtp_server[$j]->[0];
    $opt_name = $values_smtp_server[$j]->[1];
    push @item_order, $opt_name;
    $items{$opt_name} = $opt_id;
    $default_from .= ', ' .  $opt_id . ':"' . $values_smtp_server[$j]->[4] . '"';
    $j++;
}

my $smtp_server = "";
my $smtp_server_id = "";
if ( $arguments =~ /--smtp_server/ ) {
    $arguments =~ /--smtp_server="(.+?)"\s/;
    $smtp_server = $1;
	my %smtp_server_hash = $gip->get_smtp_server_hash("$client_id","name");
	$smtp_server_id = $smtp_server_hash{"$smtp_server"}[0];
}

my %smtp_server_hash = $gip->get_smtp_server_hash("$client_id","id");
my $smtp_server_name = $smtp_server_hash{"$smtp_server"}[0];

$default_from =~ s/^, //;
$default_from = '{' . $default_from . '}';

$onclick = "onchange='changeDefaultFrom(this.value);'";
my $element_smtp_server .= GipTemplate::create_form_element_select(
    label => $$lang_vars{smtp_server_message},
    id => "smtp_server",
    item_order => \@item_order,
    items => \%items,
    width => "10em",
    onclick => $onclick,
    required => "required",
    margin_bottom => "5",
	selected_value => $smtp_server_id,
);

# MAIL from

my $mail_from = "";
if ( $arguments =~ /--mail_from/ ) {
    $arguments =~ /--mail_from="(.+?)"\s/;
    $mail_from = $1;
}

my $element_mail_from .= GipTemplate::create_form_element_text(
    label => $$lang_vars{mail_from_message},
    id => "mail_from",
    type => "email",
    value => $mail_from,
    required => "required",
);

# SNMP GROUP
my $snmp_group = "";
if ( $arguments =~ /--snmp_group/ ) {
	$arguments =~ /--snmp_group="(.+?)"\s/;
	$snmp_group = $1;
}
my @snmp_groups=$gip->get_snmp_groups("$client_id");
$j = 0;
@item_order = ();
push @item_order, "";
foreach my $opt(@snmp_groups) {
	$opt_name = $snmp_groups[$j]->[1];
	push @item_order, $opt_name;
	$j++;
}

my $element_snmp_group .= GipTemplate::create_form_element_select(
    label => $$lang_vars{snmp_group_message},
	id => "snmp_group",
	item_order => \@item_order,
	hint_text => $$lang_vars{snmp_groups_explic_message},
	width => "10em",
	required => "required",
	margin_top => "5",
	margin_bottom => "5",
	selected_value => $snmp_group,
);


$form_elements .= "<span id='HideOpts'>";


###### NETWORK DISCOVERY - get_networks_snmp.pl

#CSV_nodes
my $CSV_nodes = "";
if ( $arguments =~ /--CSV_nodes/ ) {
	$arguments =~ /--CSV_nodes="(.+?)"\s/;
	$CSV_nodes = $1;
}
$disabled = "";
$checked = "";
if ( ! $CSV_nodes ) {
	$disabled = 1;
} else {
	$checked = "checked";
}
my $element_node_list .= GipTemplate::create_form_element_text(
    label => $$lang_vars{node_list_message},
    id => "CSV_nodes",
	width => "30em",
	disabled => $disabled,
	before_text => '<input type="radio" class="p-2" value="nodes_list" id="nodes_type" name="nodes_type" onchange="disableNodesFields(this.value)" ' .  $checked . '>',
	hint_text => $$lang_vars{node_list_explic_message},
	value => $CSV_nodes,
);

#networks_file
my $nodes_file = "";
if ( $arguments =~ /--nodes_file/ ) {
	$arguments =~ /--nodes_file="(.+?)"\s/;
	$nodes_file = $1;
}
$disabled = "";
$checked = "";
if ( ! $nodes_file ) {
	$disabled = 1;
} else {
	$checked = "checked";
}
my $element_node_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{nodes_file_message},
    id => "nodes_file",
	width => "30em",
	hint_text => $$lang_vars{nodes_file_explic_message},
	before_text => '<input type="radio" class="p-2" value="nodes_file" id="nodes_type" name="nodes_type" onchange="disableNodesFields(this.value)"' .  $checked . '>',
	disabled => $disabled,
	value => $nodes_file,
);


# use tags
my $tag = "";
if ( $arguments =~ /--tag/ ) {
	$arguments =~ /--tag="(.+?)"\s/;
	$tag = $1;
}

@tags = $gip->get_tag("$client_id");

my $tags_checked = "";
my $tags_disabled = "";
my $tag_object;
if ( $discovery_type == 1 || $discovery_type == 2 || $discovery_type == 5) {
	$tag_object = "host";
} else {
	$tag_object = "network";
}
	
if ( $discovery_type == 1 && ! $tag ) {
	$tags_disabled = "disabled";
}
if ( $tag ) {
    $tags_checked = "checked";
} else {
	$tags_disabled = "disabled";
}

my %object_tags = $gip->get_tag_hash("$client_id","name");
my @selected_tags = split(",", $tag);
my $selected_value_tags = "";
foreach my $tag_name ( @selected_tags ) {
	$selected_value_tags .= "|$object_tags{$tag_name}[0]";
}
$selected_value_tags =~ s/^\|//;
$selected_value_tags =~ s/\|{2,}/\|/;

$before_text_tags = '<input type="radio" class="p-2" value="use_tags" id="nodes_type" name="nodes_type" onchange="disableNodesFields(this.value)"' .  $tags_checked . '>';
my $element_tags_networks = "";
$element_tags_networks = $gip->print_tag_form("$client_id", "$vars_file", "", "$tag_object", "$$lang_vars{hint_text_tags_message}", "$before_text_tags", "$tags_disabled", "", "5", "$selected_value_tags", "use_tags", "use_tags") if @tags;

#Delete Networks
$checked = "";
if ( $arguments =~ /--delete_not_found_networks/ ) {
	$checked = 1;
}
my $element_delete_not_found_networks .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{delete_not_found_networks_message},
    id => "delete_not_found_networks",
    value => "delete_not_found_networks",
    hint_text => $$lang_vars{delete_not_found_networks_explic_message},
	checked => $checked,
);

# report not found networks
$checked = "";
if ( $arguments =~ /--report_not_found_networks/ ) {
	$checked = 1;
}
my $element_report_not_found_networks .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{report_not_found_networks_message},
    id => "report_not_found_networks",
    value => "report_not_found_networks",
	hint_text => $$lang_vars{report_not_found_networks_explic_message},
	checked => $checked,
    margin_bottom => "5",
);

# IPv4
$checked = "";
if ( $arguments =~ /--T="yes"/ ) {
    $checked = 1;
}
my $element_ipv4 .= GipTemplate::create_form_element_checkbox(
    label => "IPv4",
    id => "actualize_ipv4",
    value => "actualize_ipv4",
    checked => $checked,
);

# IPv6
$checked = "";
if ( $arguments =~ /--O="yes"/ ) {
    $checked = 1;
}
my $element_ipv6 .= GipTemplate::create_form_element_checkbox(
    label => "IPv6",
    id => "actualize_ipv6",
    value => "actualize_ipv6",
    checked => $checked,
);

# process v4 networks beginning with
my $process_networks_v4 = "";
if ( $arguments =~ /--process_networks_v4/ ) {
	$arguments =~ /--process_networks_v4="(.+?)"\s/;
	$process_networks_v4 = $1;
}
my $element_processs_networks_v4 .= GipTemplate::create_form_element_text(
    label => $$lang_vars{process_only_net_v4_message},
    id => "process_networks_v4",
    value => "$process_networks_v4",
);

# process v6 networks beginning with
my $process_networks_v6 = "";
if ( $arguments =~ /--process_networks_v6/ ) {
	$arguments =~ /--process_networks_v6="(.+?)"\s/;
	$process_networks_v6 = $1;
}
my $element_processs_networks_v6 .= GipTemplate::create_form_element_text(
    label => $$lang_vars{process_only_net_v6_message},
    id => "process_networks_v6",
    value => "$process_networks_v6",
);


# Force SITE
my $force_site = "";
if ( $arguments =~ /--force_site/ ) {
	$arguments =~ /--force_site="(.+?)"\s/;
	$force_site = $1;
}
@item_order = ();
foreach my $opt(@values_locations) {
    my $name = $opt->[1] || "";
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

my $element_force_site .= GipTemplate::create_form_element_select(
    name => $$lang_vars{loc_message},
    item_order => \@item_order,
    id => "loc",
    width => "10em",
	hint_text => $$lang_vars{force_site_explic_message},
	selected_value => $force_site,
);

# ASSIGN TAG
my $assign_tags = "";
if ( $arguments =~ /--assign_tags/ ) {
	$arguments =~ /--assign_tags="(.+?)"\s/;
	$assign_tags = $1;
}
my @selected_assign_tags = split(",", $assign_tags);
my $selected_assign_tags = "";
foreach my $tag_name ( @selected_assign_tags ) {
	$selected_assign_tags .= "|$object_tags{$tag_name}[0]";
}
$selected_assign_tags =~ s/^\|//;
$selected_assign_tags =~ s/\|{2,}/\|/;
my $element_assign_tags = "";
#$element_assign_tags = $gip->print_tag_form("$client_id", "$vars_file", "", "$tag_object", "$$lang_vars{force_tags_explic_message}", "", "", "", "", "$selected_assign_tags", "assign_tags", "", "$$lang_vars{assign_tags_message}") if @tags;
$element_assign_tags = $gip->print_tag_form("$client_id", "$vars_file", "", "$tag_object", "$$lang_vars{force_tags_explic_message}", "", "", "", "", "$selected_assign_tags", "assign_tags", "assign_tags") if @tags;


#VRF routes
$checked = "";
if ( $arguments =~ /--get_vrf_routes/ ) {
	$checked = 1;
}
my $element_import_vrf_routes .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{import_vrf_routes_message},
    id => "get_vrf_routes",
    value => "get_vrf_routes",
	hint_text => $$lang_vars{import_vrf_routes_explic_message},
	checked => $checked,
);

# import host route /32
$checked = "";
if ( $arguments =~ /--import_host_routes/ ) {
	$checked = 1;
}
my $element_import_host_route .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{import_host_routes_message},
    id => "import_host_routes",
    value => "import_host_routes",
	hint_text => $$lang_vars{import_host_routes_explic_message},
	checked => $checked,
);

# add if descr
$checked = "";
if ( $arguments =~ /--j / ) {
	$checked = 1;
}
$onclick = "onchange='disableIntDescIdent(this.value);'";
my $element_add_if_descr .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{add_if_descr_message},
    id => "add_if_descr",
    value => "add_if_descr",
	hint_text => $$lang_vars{add_if_descr_explic_message},
	onclick => $onclick,
	checked => $checked,
);

# interface descr ident
$disabled = "1";
my $if_ident = "";
if ( $arguments =~ /--k=/ ) {
	$arguments =~ /--k="(.+?)"\s/;
	$if_ident = $1;
    $disabled = "";
}
@item_order = ("Alias","Descr");

my $element_if_descr_ident .= GipTemplate::create_form_element_select(
    label => $$lang_vars{interface_descr_ident_message},
    item_order => \@item_order,
    id => "interface_descr_ident",
    value => $if_ident,
    width => "6em",
	hint_text => $$lang_vars{interface_descr_ident_explic_message},
	disabled => $disabled,
	selected_value=>$if_ident,
);

# set sync flag
$checked = "";
if ( $arguments =~ /--Set_sync_flag/ ) {
	$checked = 1;
}
my $element_set_sync_flag .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{set_sync_flag_message},
    id => "set_sync_flag",
    value => "set_sync_flag",
	hint_text => $$lang_vars{set_sync_flag_explic_message},
	checked => $checked,
);

# write result to file
my $write_file = "";
if ( $arguments =~ /--write_new_to_file/ ) {
	$arguments =~ /--write_new_to_file="(.+?)"\s/;
	$write_file = $1;
}
my $element_write_to_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{write_to_file_message},
    id => "write_to_file",
	value => $write_file,
);

$form_elements_network_snmp .= $element_snmp_group;
$form_elements_network_snmp .= $element_node_list;
$form_elements_network_snmp .= $element_node_file;
$form_elements_network_snmp .= $element_tags_networks;
$form_elements_network_snmp .= $element_delete_not_found_networks;
$form_elements_network_snmp .= $element_report_not_found_networks;
$form_elements_network_snmp .= $element_ipv4;
$form_elements_network_snmp .= $element_ipv6;
$form_elements_network_snmp .= $element_processs_networks_v4;
$form_elements_network_snmp .= $element_processs_networks_v6;
$form_elements_network_snmp .= $element_force_site;
$form_elements_network_snmp .= $element_assign_tags;
$form_elements_network_snmp .= $element_import_vrf_routes;
$form_elements_network_snmp .= $element_import_host_route;
$form_elements_network_snmp .= $element_add_if_descr;
$form_elements_network_snmp .= $element_if_descr_ident;
$form_elements_network_snmp .= $element_send_mail;
$form_elements_network_snmp .= "<span id='HideMail'>";
#$form_elements_network_snmp .= $element_only_added_mail;
$form_elements_network_snmp .= $element_send_changes_only if $send_mail;
$form_elements_network_snmp .= $element_mail_recipients if $send_mail;
$form_elements_network_snmp .= $element_smtp_server if $send_mail;
$form_elements_network_snmp .= $element_mail_from if $send_mail;
$form_elements_network_snmp .= "</span>";
$form_elements_network_snmp .= $element_set_sync_flag;
$form_elements_network_snmp .= $element_write_to_file;
$form_elements_network_snmp .= $element_verbose;
$form_elements_network_snmp .= $element_debug;



# COMMON OPTIONS HOST DNS AND SNMP

#CSV_networks
my $CSV_networks_checked = "";
my $CSV_networks = "";
$disabled = 1;
if ( $arguments =~ /--CSV_networks/ ) {
    $arguments =~ /--CSV_networks="(.+?)"\s/;
    $CSV_networks = $1;
    $checked = "checked";
    $CSV_networks_checked = "checked";
    $disabled = "";
}
my $element_network_list .= GipTemplate::create_form_element_text(
    label => $$lang_vars{network_list_message},
    id => "CSV_networks",
	width => "30em",
	before_text => '<input type="radio" class="p-2" value="network_list" id="network_type" name="network_type" onchange="disableNodesFieldsHost(this.value)" ' . $CSV_networks_checked . '>',
	hint_text => $$lang_vars{network_list_explic_message},
	value => $CSV_networks,
	disabled => $disabled,
);

#network file
my $networks_file = "";
my $network_file_checked = "";
$disabled = 1;
if ( $arguments =~ /--Network_file/ ) {
    $arguments =~ /--Network_file="(.+?)"\s/;
    $networks_file = $1;
    $network_file_checked = "checked";
	$disabled = "",
}

my $element_network_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{network_file_message},
    id => "networks_file",
	width => "30em",
	hint_text => $$lang_vars{network_file_explic_message},
	before_text => '<input type="radio" class="p-2" value="networks_file" id="network_type" name="network_type" onchange="disableNodesFieldsHost(this.value)" ' . $network_file_checked . '>',
	disabled => $disabled,
	value => $networks_file,
);

# use tags

$before_text_tags = '<input type="radio" class="p-2" value="use_tags" id="network_type" name="network_type" onchange="disableNodesFieldsHost(this.value)" ' . $tags_checked . '>';
my $element_tags = "";
#$element_tags = $gip->print_tag_form("$client_id", "$vars_file", "", "$tag_object", "$$lang_vars{hint_text_tags_message}", "$before_text_tags", "$tags_disabled", "", "", "$tag", "use_tags") if @tags;
$element_tags = $gip->print_tag_form("$client_id", "$vars_file", "", "$tag_object", "$$lang_vars{hint_text_tags_message}", "$before_text_tags", "$tags_disabled", "", "", "$selected_value_tags", "use_tags","use_tags") if @tags;


# IP RANGE
my $ip_range_checked = "";
my $range = "";
$disabled = 1;
if ( $arguments =~ /--range/ ) {
    $arguments =~ /--range="(.+?)"\s/;
    $range = $1;
    $ip_range_checked = "checked";
	$disabled = "",
}
my $before_text_ip_range = '<input type="radio" class="p-2" value="use_range" id="network_type" name="network_type" onchange="disableNodesFieldsHost(this.value)" ' . $ip_range_checked . '>';
my $element_ip_range .= GipTemplate::create_form_element_text(
    label => $$lang_vars{ip_range_message},
    id => "use_range",
	before_text => $before_text_ip_range,
	hint_text => $$lang_vars{ip_range_explic_message},
	disabled => $disabled,
	margin_bottom => "5",
	value => $range,
);


# LOCATION SCAN
my $location_scan_checked = "";
my $location_scan = "";
my @location_scan;
$disabled = 1;
if ( $arguments =~ /--Location_scan/ ) {
    $arguments =~ /--Location_scan="(.+?)"\s/;
    $location_scan = $1;
	@location_scan = split(",", $location_scan);
    $location_scan_checked = "checked";
	$disabled = "",
}
my $before_text_locations_scan = '<input type="radio" class="p-2" value="location_scan" id="network_type" name="network_type" onchange="disableNodesFieldsHost(this.value)" ' . $location_scan_checked . '>';

my $location_scan_id = "";
foreach ( @location_scan ) {
    my $loc_id_check = $gip->get_loc_id("$client_id","$_") || "";
    $location_scan_id .= "|" . $loc_id_check if $loc_id_check;
}
$location_scan_id =~ s/^\|//;

@item_order = ();
undef %items;
foreach my $opt(@values_locations) {
    my $id = $opt->[0] || "";
    my $name = $opt->[1] || "";
    if ( $name eq "NULL" ) {
        next;
    }
   
    if ( $locs_rw_perm ) {
        my $loc_id_opt = $loc_hash->{$name} || "";
        if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id_opt$/ || $locs_rw_perm =~ /^${loc_id_opt}_/ || $locs_rw_perm =~ /_${loc_id_opt}$/ || $locs_rw_perm =~ /_${loc_id_opt}_/ ) {
            push @item_order, $name;
            $items{$name} = $id;
        }
    } else {
        push @item_order, $name;
        $items{$name} = $id;
    }
}

my $element_location_scan .= GipTemplate::create_form_element_select(
    name => $$lang_vars{locs_message},
    multiple => 1,
    item_order => \@item_order,
    items => \%items,
    id => "location_scan",
    width => "10em",
    size => "3",
    before_text => $before_text_locations_scan,
    hint_text => $$lang_vars{location_scan_explic_message},
	selected_value => $location_scan_id,
    disabled => $disabled,
    margin_bottom => "5",
);



$disabled = "";
# DELETE DNS DOWN
$checked = "";
if ( $arguments =~ /--delete_down_hosts/ ) {
	$checked = 1;
}
my $element_delete_host .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{delete_hosts_message}",
    id => "delete_down_hosts",
    value => "delete_down_hosts",
    hint_text => $$lang_vars{delete_hosts_explic_message},
    checked => $checked,
);

# SITE (Location)
@item_order = ();
foreach my $opt(@values_locations) {
    my $name = $opt->[1] || "";
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

my $process_only_location = "";
if ( $arguments =~ /--Location/ ) {
    $arguments =~ /--Location="(.+?)"\s/;
    $process_only_location = $1;
}
my $element_sites .= GipTemplate::create_form_element_select(
    name => $$lang_vars{process_only_location_message},
    item_order => \@item_order,
    id => "process_only_location",
    width => "10em",
	hint_text => $$lang_vars{process_only_location_explic_message},
	selected_value => $process_only_location,
);

# Process number
my $max_sync_procs = "";
if ( $arguments =~ /--S/ ) {
    $arguments =~ /--S="(.+?)"\s/;
    $max_sync_procs = $1;
}
@item_order = ("256","128","64","32","16");

my $element_max_sync_procs .= GipTemplate::create_form_element_select(
    label => $$lang_vars{child_number_message},
    item_order => \@item_order,
    id => "max_sync_procs",
    value => $max_sync_procs,
    width => "6em",
	hint_text => $$lang_vars{max_sync_explic_message},
	selected_value => $max_sync_procs,
);


###### HOST DISCOVERY DNS - ip_update_gestioip_dns.pl

# IGNORE DNS
$checked = "";
my $ignore_dns = "";
if ( $arguments =~ /--ignore_dns/ ) {
    $checked = 1;
	$ignore_dns = 1;
}

$onclick = "onchange='disableDNSOptions();'";

my $element_ignore_dns .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ping_only_message}",
    id => "ignore_dns",
    value => "ignore_dns",
    hint_text => $$lang_vars{ping_only_explic_message},
    onclick => $onclick,
    checked => $checked,
);


# Generic auto
$checked = "";
$disabled = "";
$disabled = 1 if $ignore_dns;
my $ignore_generic_auto_disabled = "";
if ( $arguments =~ /--B/ ) {
    $checked = 1;
}
my $element_ignore_generic_auto .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ignorar_generic_auto_manage_message}",
    id => "ignore_generic_auto",
    value => "ignore_generic_auto",
    checked => $checked,
    disabled => $disabled,
);


## GENERIC DYN HOSTNAME
#my $generic_dyn_hostname = "";
#if ( $arguments =~ /--P/ ) {
#    $arguments =~ /--P="(.+?)"\s/;
#    $generic_dyn_hostname = $1;
#}
#my $element_generic_dyn_host .= GipTemplate::create_form_element_text(
#    label => $$lang_vars{generic_dyn_host_message},
#    id => "generic_dyn_host_name",
#    hint_text => $$lang_vars{generic_dyn_host_explic_message},
#	value => $generic_dyn_hostname,
#);

# Ignorar
my $ignorar = "";
$disabled = "";
$disabled = 1 if $ignore_dns;
if ( $arguments =~ /--Q/ ) {
    $arguments =~ /--Q="(.+?)"\s/;
    $ignorar = $1;
}
my $element_ignorar .= GipTemplate::create_form_element_text(
    label => $$lang_vars{ignorar_manage_message},
    id => "ignorar",
    hint_text => $$lang_vars{ignorar_explic_message},
	value => $ignorar,
    disabled => $disabled,
);

# Zone transfer
$checked = "";
$disabled = "";
$disabled = 1 if $ignore_dns;
if ( $arguments =~ /--Z/ ) {
    $checked = 1;
}
my $element_zone_transfer .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_zone_transfer_message},
    id => "zone_transfer",
    value => "zone_transfer",
    checked => $checked,
    hint_text => $$lang_vars{zone_transfer_explic_message},
    disabled => $disabled,
);

$form_elements_host_dns .= $element_network_list;
$form_elements_host_dns .= $element_network_file;
$form_elements_host_dns .= $element_tags;
$form_elements_host_dns .= $element_ip_range;
$form_elements_host_dns .= $element_location_scan;
$form_elements_host_dns .= $element_ipv4;
$form_elements_host_dns .= $element_ipv6;
$form_elements_host_dns .= $element_ignore_dns;
$form_elements_host_dns .= $element_delete_host;
$form_elements_host_dns .= $element_sites;
$form_elements_host_dns .= $element_max_sync_procs;
$form_elements_host_dns .= $element_ignore_generic_auto;
$form_elements_host_dns .= $element_ignorar;
#$form_elements_host_dns .= $element_generic_dyn_host;
$form_elements_host_dns .= $element_zone_transfer;
$form_elements_host_dns .= $element_send_mail;
$form_elements_host_dns .= "<span id='HideMail'>";
#$form_elements_host_dns .= $element_only_added_mail;
$form_elements_host_dns .= $element_send_changes_only if $send_mail;
$form_elements_host_dns .= $element_mail_recipients if $send_mail;
$form_elements_host_dns .= $element_smtp_server if $send_mail;
$form_elements_host_dns .= $element_mail_from if $send_mail;
$form_elements_host_dns .= "</span>";
$form_elements_host_dns .= $element_verbose;
$form_elements_host_dns .= $element_debug;

my $form_elements_host_dns_global .= $element_ignore_dns;
$form_elements_host_dns_global .= $element_delete_host;
$form_elements_host_dns_global .= $element_ignore_generic_auto;
$form_elements_host_dns_global .= $element_ignorar;
#$form_elements_host_dns_global .= $element_generic_dyn_host;
$form_elements_host_dns_global .= $element_zone_transfer;


###### HOST DISCOVERY SNMP - ip_update_gestioip_snmp.pl

# ignore ARP cache
$checked = "";
if ( $arguments =~ /--ignore_arp_cache/ ) {
    $checked = 1;
}
my $element_ignore_arp_cache .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ignore_arp_cache_message}",
    id => "ignore_arp_cache",
    value => "ignore_arp_cache",
    checked => $checked,
);

$form_elements_host_snmp .= $element_snmp_group;
$form_elements_host_snmp .= $element_network_list;
$form_elements_host_snmp .= $element_network_file;
$form_elements_host_snmp .= $element_tags;
$form_elements_host_snmp .= $element_ip_range;
$form_elements_host_snmp .= $element_location_scan;
$form_elements_host_snmp .= $element_sites;
$form_elements_host_snmp .= $element_ipv4;
$form_elements_host_snmp .= $element_ipv6;
$form_elements_host_snmp .= $element_ignore_arp_cache;
$form_elements_host_snmp .= $element_max_sync_procs;
$form_elements_host_snmp .= $element_send_mail;
$form_elements_host_snmp .= "<span id='HideMail'>";
#$form_elements_host_dns .= $element_only_added_mail;
$form_elements_host_snmp .= $element_send_changes_only if $send_mail;
$form_elements_host_snmp .= $element_mail_recipients if $send_mail;
$form_elements_host_snmp .= $element_smtp_server if $send_mail;
$form_elements_host_snmp .= $element_mail_from if $send_mail;
$form_elements_host_snmp .= "</span>";
$form_elements_host_snmp .= $element_verbose;
$form_elements_host_snmp .= $element_debug;

my $form_elements_host_snmp_global .= "";
$form_elements_host_snmp_global .= "$element_ignore_arp_cache";


###### VLAN DISCOVERY - get_vlans.pl

$form_elements_vlan .= $element_snmp_group;
$form_elements_vlan .= $element_node_list;
$form_elements_vlan .= $element_node_file;
$form_elements_vlan .= $element_tags_networks;
$form_elements_vlan .= $element_send_mail;
$form_elements_vlan .= "<span id='HideMail'>";
#$form_elements_host_dns .= $element_only_added_mail;
#$form_elements_host_snmp .= $element_send_changes_only;
$form_elements_vlan .= $element_mail_recipients if $send_mail;
$form_elements_vlan .= $element_smtp_server if $send_mail;
$form_elements_vlan .= $element_mail_from if $send_mail;
$form_elements_vlan .= "</span>";
$form_elements_vlan .= $element_verbose;
$form_elements_vlan .= $element_debug;


my $form_elements_vlan_global .= "";


###### GLOBAL DISCOVERY - discover_networks.pl

# network discovery
my $element_execute_network_discovery .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{execute_network_discovery_message},
    label_bold => 1,
    id => "use_network_discovery",
    value => "yes",
    checked => "1",
    disabled => "1",
    required => "required",
	margin_top => "5",
#	hint_text => $$lang_vars{network_discovery_message},
);

# vlan_discovery
$checked = "";
if ( $arguments =~ /--execute_vlan_discovery/ ) {
    $checked = 1;
}
$onclick = "onchange='changeHideVLAN();'";
my $element_execute_vlan_discovery .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{execute_vlan_discovery_message},
    label_bold => 1,
    id => "use_vlan_discovery",
    value => "yes",
	margin_top => "5",
	onclick => $onclick,
	checked => $checked,
#	hint_text => $$lang_vars{network_discovery_message},
);

# host discovery DNS
$checked = "";
my $host_discovery_dns_checked = "";
if ( $arguments =~ /--execute_host_discovery_dns/ ) {
    $checked = 1;
	$host_discovery_dns_checked = 1;
}
$onclick = "onchange='changeHideHostDNS();'";
my $element_execute_host_discovery_dns .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{execute_host_discovery_dns_message},
    label_bold => 1,
    id => "use_host_discovery_dns",
    value => "yes",
	margin_top => "5",
	onclick => $onclick,
	checked => $checked,
#	hint_text => $$lang_vars{network_discovery_message},
);

# host discovery SNMP
$checked = "";
if ( $arguments =~ /--execute_host_discovery_snmp/ ) {
    $checked = 1;
}
$onclick = "onchange='changeHideHostSNMP();'";
my $element_execute_host_discovery_snmp .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{execute_host_discovery_snmp_message},
    label_bold => 1,
    id => "use_host_discovery_snmp",
    value => "yes",
	margin_top => "5",
	onclick => $onclick,
	checked => $checked,
#	hint_text => $$lang_vars{network_discovery_message},
);

$form_elements_global_discovery .= $element_snmp_group;
$form_elements_global_discovery .= $element_ipv4;
$form_elements_global_discovery .= $element_ipv6;
$form_elements_global_discovery .= $element_max_sync_procs;
$form_elements_global_discovery .= $element_node_list;
$form_elements_global_discovery .= $element_node_file;
$form_elements_global_discovery .= $element_tags_networks;
$form_elements_global_discovery .= $element_send_mail;
$form_elements_global_discovery .= "<span id='HideMail'>";
$form_elements_global_discovery .= $element_mail_recipients if $send_mail;
$form_elements_global_discovery .= $element_send_changes_only if $send_mail;
$form_elements_global_discovery .= $element_smtp_server if $send_mail;
$form_elements_global_discovery .= $element_mail_from if $send_mail;
$form_elements_global_discovery .= "</span>";
$form_elements_global_discovery .= $element_verbose;
$form_elements_global_discovery .= $element_debug;
$form_elements_global_discovery .= $element_execute_network_discovery;
$form_elements_global_discovery .= $element_processs_networks_v4;
$form_elements_global_discovery .= $element_processs_networks_v6;
$form_elements_global_discovery .= $element_delete_not_found_networks;
$form_elements_global_discovery .= $element_report_not_found_networks;
$form_elements_global_discovery .= $element_import_vrf_routes;
$form_elements_global_discovery .= $element_import_host_route;
$form_elements_global_discovery .= $element_set_sync_flag;
$form_elements_global_discovery .= $element_add_if_descr;
$form_elements_global_discovery .= $element_if_descr_ident;
$form_elements_global_discovery .= $element_execute_vlan_discovery;
$form_elements_global_discovery .= "<span id='HideVLAN'></span>";
$form_elements_global_discovery .= $element_execute_host_discovery_dns;
$form_elements_global_discovery .= "<span id='HideHostDNS'>";
if ( $host_discovery_dns_checked ) {
	$form_elements_global_discovery .= $element_ignore_generic_auto;
	$form_elements_global_discovery .= $element_ignorar;
#	$form_elements_global_discovery .= $element_generic_dyn_host;
	$form_elements_global_discovery .= $element_zone_transfer;
	$form_elements_global_discovery .= $element_verbose;
}
$form_elements_global_discovery .= "</span>";
$form_elements_global_discovery .= $element_execute_host_discovery_snmp;
$form_elements_global_discovery .= "<span id='HideHostSNMP'></span>";


$form_elements .= $element_snmp_group;
$form_elements .= $element_ipv4;
$form_elements .= $element_ipv6;
$form_elements .= $element_max_sync_procs;
$form_elements .= $element_node_list;
$form_elements .= $element_node_file;
$form_elements .= $element_tags_networks;
$form_elements .= $element_send_mail;
$form_elements .= "<span id='HideMail'>";
$form_elements .= $element_mail_recipients if $send_mail;
$form_elements .= $element_send_changes_only if $send_mail;
$form_elements .= $element_smtp_server if $send_mail;
$form_elements .= $element_mail_from if $send_mail;
$form_elements .= "</span>";
$form_elements .= $element_verbose;
$form_elements .= $element_debug;
$form_elements .= $element_execute_network_discovery;
$form_elements .= $element_processs_networks_v4;
$form_elements .= $element_processs_networks_v6;
$form_elements .= $element_delete_not_found_networks;
$form_elements .= $element_report_not_found_networks;
$form_elements .= $element_import_vrf_routes;
$form_elements .= $element_import_host_route;
$form_elements .= $element_set_sync_flag;
$form_elements .= $element_add_if_descr;
$form_elements .= $element_if_descr_ident;
$form_elements .= $element_execute_vlan_discovery;
$form_elements .= "<span id='HideVLAN'></span>";
$form_elements .= $element_execute_host_discovery_dns;
$form_elements .= "<span id='HideHostDNS'></span>";
$form_elements .= $element_execute_host_discovery_snmp;
$form_elements .= "<span id='HideHostSNMP'></span>";


$form_elements .= "</span>\n";


#### OPTIONS LEASES

@item_order = ("$$lang_vars{kea_leases_file_message}", "$$lang_vars{kea_api_message}", "$$lang_vars{dhcpd_leases_file_message}", "$$lang_vars{ms_csv_leases_file_message}","$$lang_vars{generic_csv_leases_file_message}");

# leases type
my $leases_type = "";
if ( $arguments =~ /--type/ ) {
    $arguments =~ /--type="(.+?)"\s/;
    $leases_type = $1;
}

my %kea_type_hash = (
    kea_lease_file => "$$lang_vars{kea_leases_file_message}",
    kea_api => "$$lang_vars{kea_api_message}",
    dhcpd_lease_file => "$$lang_vars{dhcpd_leases_file_message}",
    ms_lease_file => "$$lang_vars{ms_csv_leases_file_message}",
    generic_lease_file => "$$lang_vars{generic_csv_leases_file_message}",
);


$onclick = "onchange='changeLeaseFile_URL(this.value);'";
my $element_leases_type .= GipTemplate::create_form_element_select(
    label => $$lang_vars{leases_type_message},
    item_order => \@item_order,
    id => "leases_type",
	value => $leases_type,
    width => "12em",
    onclick => $onclick,
    required => "required",
	selected_value => $kea_type_hash{$leases_type},
);

# Leases file name
my $leases_file = "";
if ( $arguments =~ /--leases_file/ ) {
    $arguments =~ /--leases_file="(.+?)"\s/;
    $leases_file = $1;
}

my $element_leases_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{leases_file_message},
    id => "leases_file",
	value => $leases_file,
    width => "500",
    required => "required",
    hint_text => $$lang_vars{leases_file_hint_message},
);

# Old Leases file name
my $leases_file_old = "";
if ( $arguments =~ /--leases_file_old/ ) {
    $arguments =~ /--leases_file_old="(.+?)"\s/;
    $leases_file_old = $1;
}

my $element_leases_file_old .= GipTemplate::create_form_element_hidden(
    name => "leases_file_old",
    value => "$leases_file_old",
);

# Kea URL
my $kea_url = "";
if ( $arguments =~ /--kea_url/ ) {
    $arguments =~ /--kea_url="(.+?)"/;
    $kea_url = $1;
}
my $element_kea_url .= GipTemplate::create_form_element_text(
    label => $$lang_vars{kea_url_message},
    id => "kea_url",
	value => $kea_url,
    width => "500",
    required => "required",
);


# Kea basic authentication
$checked = "";
if ( $arguments =~ /--kea_basic_auth/ ) {
    $checked = 1;
}
my $element_kea_basic_auth .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_kea_basic_auth_message},
    id => "kea_basic_auth",
    value => "1",
	hint_text => $$lang_vars{kea_user_file_message},
	checked => $checked,
);


# Kea API IP version
my $checked1 = "";
my $checked2 = "";
if ( $arguments =~ / --ipv4/ ) {
    $checked1 = 1;
}
if ( $arguments =~ / --ipv6/ ) {
    $checked2 = 1;
}
my $element_kea_ip_version .= GipTemplate::create_form_element_choice_radio(
    label => $$lang_vars{ip_version_message},
    id => "kea_api_ip_version",
    value1 => "ipv4",
    value2 => "ipv6",
    text1 => "IPv4",
    text2 => "IPv6",
    checked1 => "$checked1",
    checked2 => "$checked2",
);

$element_kea_url .= $element_kea_ip_version;
$element_kea_url .= $element_kea_basic_auth;

my $selcted_value = "";
if ( $arguments =~ /--tag/ ) {
    $arguments =~ /--tag="(.+?)"/;
    $selected_value = $1;
}

my @selected_tags_leases = split(",", $selected_value);
my $selected_value_tags_leases = "";
foreach my $tag_name ( @selected_tags_leases ) {
	$selected_value_tags_leases .= "|$object_tags{$tag_name}[0]";
}
$selected_value_tags_leases =~ s/^\|//;
$selected_value_tags_leases =~ s/\|{2,}/\|/;

my $element_tags_leases = "";
$element_tags_leases = $gip->print_tag_form("$client_id", "$vars_file", "", "network", "$$lang_vars{hint_text_tags_networks_message}", "", "", "", "5", "$selected_value_tags_leases", "leases_tag","leases_tag") if @tags;


my $form_elements_leases .= $element_leases_type;
$form_elements_leases .= "<span id='HideLeasesFile'>";
$form_elements_leases .= $element_leases_file if $leases_file;
$form_elements_leases .= "</span>";
$form_elements_leases .= "<span id='HideKeaUrl'>";
$form_elements_leases .= $element_kea_url if $kea_url;
$form_elements_leases .= "</span>";
$form_elements_leases .= $element_tags_leases;
$form_elements_leases .= $element_send_mail;
$form_elements_leases .= "<span id='HideMail'>";
$form_elements_leases .= $element_send_changes_only if $send_mail;
$form_elements_leases .= $element_mail_recipients if $send_mail;
$form_elements_leases .= $element_smtp_server if $send_mail;
$form_elements_leases .= $element_mail_from if $send_mail;
$form_elements_leases .= "</span>";
$form_elements_leases .= $element_leases_file_old;
$form_elements_leases .= $element_debug;


########### Options DATABASE BACKUP

my $form_elements_db_backup = $element_send_mail_backup;
$form_elements_db_backup .= "<span id='HideMailBackup'>";
$form_elements_db_backup .= $element_mail_recipients if $send_mail;
$form_elements_db_backup .= $element_smtp_server if $send_mail;
$form_elements_db_backup .= $element_mail_from if $send_mail;
$form_elements_db_backup .= "</span>";
$form_elements_db_backup .= $element_verbose;
$form_elements_db_backup .= $element_debug;


########### Options AWS

# checked and disabled are common for all clouds
my $dns_checked = "";
my $dns_disabled = "";
my $zt_checked = "";
my $zt_disabled = "";
my $ignore_dns_checked = "";
my $ignore_dns_disabled = "";

if ( $arguments =~ / --(aws_dns|azure_dns|gcp_dns)/ ) {
    $dns_checked = 1;
    $dns_disabled = 0;
	$zt_disabled = 1;
	$ignore_dns_disabled = 1;
}
if ( $arguments =~ /--Z/ ) {
    $zt_checked = 1;
    $dns_disabled = 1;
	$zt_disabled = 0;
	$ignore_dns_disabled = 1;
}
if ( $arguments =~ /--ignore_dns/ ) {
    $ignore_dns_checked = 1;
    $dns_disabled = 1;
	$zt_disabled = 1;
	$ignore_dns_disabled = 0;
}

$onclick = "onchange='disableDNSOptionsAWSDNS(\"aws_dns\");'";
my $element_aws_dns = GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_aws_dns_message},
    id => "aws_dns",
    value => "1",
    onclick => $onclick,
    checked => $dns_checked,
    disabled => $dns_disabled,
);

$onclick = "onchange='disableDNSOptionsAWSDNS(\"zone_transfer\");'";
my $element_zone_transfer_aws .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_zone_transfer_message},
    id => "zone_transfer",
    value => "zone_transfer",
    onclick => $onclick,
    hint_text => $$lang_vars{zone_transfer_explic_message},
    checked => $zt_checked,
    disabled => $zt_disabled,
);

$onclick = "onchange='disableDNSOptionsAWSDNS(\"ignore_dns\");'";
my $element_ignore_dns_aws .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ignore_dns_message}",
    id => "ignore_dns",
    value => "ignore_dns",
    onclick => $onclick,
    hint_text => $$lang_vars{ignore_dns_explic_message},
    onclick => $onclick,
    checked => $ignore_dns_checked,
    disabled => $ignore_dns_disabled,
);



my $aws_region = "";
if ( $arguments =~ /--aws_region/ ) {
    $arguments =~ /--aws_region="(.+?)"\s/;
    $aws_region = $1;
}
my $element_aws_region .= GipTemplate::create_form_element_text(
    label => $$lang_vars{region_message},
    id => "aws_region",
    value => "$aws_region",
    required => "required",
);


my $aws_access_key_id = "";
if ( $arguments =~ /--aws_access_key_id/ ) {
    $arguments =~ /--aws_access_key_id="(.+?)"\s/;
    $aws_access_key_id = $1;
}
my $element_aws_access_key_id .= GipTemplate::create_form_element_text(
    label => $$lang_vars{aws_access_key_id_message},
    id => "aws_access_key_id",
    value => "$aws_access_key_id",
    required => "required",
);

my $aws_secret_access_key = "";
if ( $arguments =~ /--aws_secret_access_key/ ) {
    $arguments =~ /--aws_secret_access_key="(.+?)"\s/;
    $aws_secret_access_key = $1;
}
my $element_aws_secret_access_key .= GipTemplate::create_form_element_text(
    label => $$lang_vars{aws_secret_access_key_message},
    id => "aws_secret_access_key",
    type => "password",
    value => "$aws_secret_access_key",
    required => "required",
);

my $form_elements_aws .= $element_aws_dns;
$form_elements_aws .= $element_zone_transfer_aws;
$form_elements_aws .= $element_ignore_dns_aws;
$form_elements_aws .= $element_aws_region;
$form_elements_aws .= $element_aws_access_key_id;
$form_elements_aws .= $element_aws_secret_access_key;
$form_elements_aws .= $element_send_mail_backup;
$form_elements_aws .= "<span id='HideMailBackup'>";
$form_elements_aws .= $element_mail_recipients if $send_mail;
$form_elements_aws .= $element_smtp_server if $send_mail;
$form_elements_aws .= $element_mail_from if $send_mail;
$form_elements_aws .= "</span>";
$form_elements_aws .= $element_verbose;
$form_elements_aws .= $element_debug;


########### Options AZURE

$onclick = "onchange='disableDNSOptionsAzureDNS(\"azure_dns\");'";
my $element_azure_dns = GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_azure_dns_message},
    id => "azure_dns",
    onclick => "$onclick",
    value => "1",
    checked => $dns_checked,
    disabled => $dns_disabled,
);

my $azure_resource_group = "";
if ( $arguments =~ /--azure_resource_group/ ) {
    $arguments =~ /--azure_resource_group="(.+?)"\s/;
    $azure_resource_group = $1;
}
my $element_azure_resource_group .= GipTemplate::create_form_element_text(
    label => $$lang_vars{azure_resource_group_message},
    id => "azure_resource_group",
    value => "$azure_resource_group",
    required => "required",
);

$onclick = "onchange='disableDNSOptionsAzureDNS(\"zone_transfer\");'";
my $element_zone_transfer_azure .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_zone_transfer_message},
    id => "zone_transfer",
    value => "zone_transfer",
    onclick => $onclick,
    hint_text => $$lang_vars{zone_transfer_explic_message},
    checked => $zt_checked,
    disabled => $zt_disabled,

);

$onclick = "onchange='disableDNSOptionsAzureDNS(\"ignore_dns\");'";
my $element_ignore_dns_azure .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ignore_dns_message}",
    id => "ignore_dns",
    value => "ignore_dns",
    onclick => $onclick,
    hint_text => $$lang_vars{ignore_dns_explic_message},
    onclick => $onclick,
    checked => $ignore_dns_checked,
    disabled => $ignore_dns_disabled
);

my $azure_tenant_id = "";
if ( $arguments =~ /--azure_tenant_id/ ) {
    $arguments =~ /--azure_tenant_id="(.+?)"\s/;
    $azure_tenant_id = $1;
}
my $element_azure_tenant_id .= GipTemplate::create_form_element_text(
    label => $$lang_vars{azure_tenant_id_message},
    id => "azure_tenant_id",
    value => "$azure_tenant_id",
    required => "required",
);

my $azure_app_id = "";
if ( $arguments =~ /--azure_app_id/ ) {
    $arguments =~ /--azure_app_id="(.+?)"\s/;
    $azure_app_id = $1;
}
my $element_azure_app_id .= GipTemplate::create_form_element_text(
    label => $$lang_vars{azure_app_id_message},
    id => "azure_app_id",
    value => "$azure_app_id",
    required => "required",
);

my $azure_cert_file = "";
my $azure_cert_file_radio_checked = "";
my $azure_cert_file_disabled = 1;
if ( $arguments =~ /--azure_cert_file/ ) {
    $arguments =~ /--azure_cert_file="(.+?)"\s/;
    $azure_cert_file = $1;
    $azure_cert_file_radio_checked = "checked";
    $azure_cert_file_disabled = 0;
}
my $before_text_cert_file = '<input type="radio" class="p-2" value="cert" id="azure_cert_file_radio" name="azure_cert_file_radio" onchange="disableAzureCert(this.value)"' . $azure_cert_file_radio_checked . '>';
my $element_azure_cert_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{azure_cert_file_message},
    before_text => $before_text_cert_file,
    id => "azure_cert_file",
    value => "$azure_cert_file",
    disabled => "$azure_cert_file_disabled",
    required => "required",
);

my $azure_secret_key_value = "";
$azure_cert_file = "";
$azure_cert_file_radio_checked = "";
$azure_cert_file_disabled = 1;
if ( $arguments =~ /--azure_secret_key_value/ ) {
    $arguments =~ /--azure_secret_key_value="(.+?)"\s/;
    $azure_secret_key_value = $1;
    $azure_cert_file_radio_checked = "checked";
    $azure_cert_file_disabled = 0;
}
my $before_text_client_secret = '<input type="radio" class="p-2" value="secret" id="azure_cert_file_radio" name="azure_cert_file_radio" onchange="disableAzureCert(this.value)"' . $azure_cert_file_radio_checked . '>';
my $element_azure_client_secret .= GipTemplate::create_form_element_text(
    label => $$lang_vars{azure_secret_key_value_message},
    before_text => $before_text_client_secret,
    id => "azure_secret_key_value",
    value => "$azure_secret_key_value",
    type => "password",
    required => "required",
    disabled => "$azure_cert_file_disabled",
);

my $form_elements_azure .= $element_azure_dns;
$form_elements_azure .= "<span id='HideAzueResourceGroup'></span>";
$form_elements_azure .= $element_zone_transfer_azure;
$form_elements_azure .= $element_ignore_dns_azure;
$form_elements_azure .= $element_azure_resource_group;
$form_elements_azure .= $element_azure_tenant_id;
$form_elements_azure .= $element_azure_app_id;
$form_elements_azure .= $element_azure_cert_file;
$form_elements_azure .= $element_azure_client_secret;
$form_elements_azure .= $element_send_mail_backup;
$form_elements_azure .= "<span id='HideMailBackup'>";
$form_elements_azure .= $element_mail_recipients if $send_mail;
$form_elements_azure .= $element_smtp_server if $send_mail;
$form_elements_azure .= $element_mail_from if $send_mail;
$form_elements_azure .= "</span>";
$form_elements_azure .= $element_verbose;
$form_elements_azure .= $element_debug;


########### Options GOOGLE GCP

$onclick = "onchange='disableDNSOptionsGCPDNS(\"aws_dns\");'";
my $element_gcp_dns = GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_gcp_dns_message},
    id => "gcp_dns",
    onclick => $onclick,
    value => "1",
    checked => $dns_checked,
    disabled => $dns_disabled,
);

$onclick = "onchange='disableDNSOptionsGCPDNS(\"zone_transfer\");'";
my $element_zone_transfer_gcp .= GipTemplate::create_form_element_checkbox(
    label => $$lang_vars{use_zone_transfer_message},
    id => "zone_transfer",
    value => "zone_transfer",
    onclick => $onclick,
    hint_text => $$lang_vars{zone_transfer_explic_message},
	checked => $zt_checked,
    disabled => $zt_disabled,
);

$onclick = "onchange='disableDNSOptionsGCPDNS(\"ignore_dns\");'";
my $element_ignore_dns_gcp .= GipTemplate::create_form_element_checkbox(
    label => "$$lang_vars{ignore_dns_message}",
    id => "ignore_dns",
    value => "ignore_dns",
    onclick => $onclick,
    hint_text => $$lang_vars{ignore_dns_explic_message},
    onclick => $onclick,
    checked => $ignore_dns_checked,
    disabled => $ignore_dns_disabled,
);

my $gcp_project = "";
if ( $arguments =~ /--gcp_project/ ) {
    $arguments =~ /--gcp_project="(.+?)"\s/;
    $gcp_project = $1;
}
my $element_gcp_project .= GipTemplate::create_form_element_text(
    label => $$lang_vars{gcp_project_message},
    id => "gcp_project",
    value => "$gcp_project",
    required => "required",
);

my $gcp_zone = "";
if ( $arguments =~ /--gcp_zone/ ) {
    $arguments =~ /--gcp_zone="(.+?)"\s/;
    $gcp_zone = $1;
}
my $element_gcp_zone .= GipTemplate::create_form_element_text(
    label => $$lang_vars{gcp_zone_id_message},
    id => "gcp_zone",
    value => "$gcp_zone",
    required => "required",
);

my $gcp_key_file = "";
if ( $arguments =~ /--gcp_key_file/ ) {
    $arguments =~ /--gcp_key_file="(.+?)"\s/;
    $gcp_key_file = $1;
}
my $element_gcp_key_file .= GipTemplate::create_form_element_text(
    label => $$lang_vars{gcp_key_file_message},
    id => "gcp_key_file",
    value => "$gcp_key_file",
    required => "required",
);


my $form_elements_gcp .= $element_gcp_dns;
$form_elements_gcp .= $element_zone_transfer_gcp;
$form_elements_gcp .= $element_ignore_dns_gcp;
$form_elements_gcp .= $element_gcp_zone;
$form_elements_gcp .= $element_gcp_key_file;
$form_elements_gcp .= $element_send_mail_backup;
$form_elements_gcp .= "<span id='HideMailBackup'>";
$form_elements_gcp .= $element_mail_recipients if $send_mail;
$form_elements_gcp .= $element_smtp_server if $send_mail;
$form_elements_gcp .= $element_mail_from if $send_mail;
$form_elements_gcp .= "</span>";
$form_elements_gcp .= $element_verbose;
$form_elements_gcp .= $element_debug;


########### Options CMM

my %job_groups = $gip->get_job_groups("$client_id");

my $cmm_group_id = "";
if ( $arguments =~ /--group_id/ ) {
    $arguments =~ /--group_id="(.+?)"/;
    $cmm_group_id = $1;
}

@item_order = ();
undef %items;
my $element_cmm_job_group = "";
if ( %job_groups ) {

    foreach my $jg_id ( keys %job_groups ) {
        my $name = $job_groups{$jg_id}->[0];
        push @item_order, $name;
        $items{$name} = $jg_id;
    }

    $element_cmm_job_group .= GipTemplate::create_form_element_select(
        label => $$lang_vars{job_group_message},
        item_order => \@item_order,
        items => \%items,
        id => "cmm_job_group_id",
        width => "12em",
		selected_value => $cmm_group_id,
        required => "required",
    );
} else {
    $element_cmm_job_group = "$$lang_vars{no_job_groups_found_message}";
}

my $form_elements_cmm = $element_cmm_job_group;
$form_elements_cmm .= $element_send_mail_backup;
$form_elements_cmm .= "<span id='HideMailBackup'>";
$form_elements_cmm .= "</span>";
$form_elements_cmm .= $element_verbose;
$form_elements_cmm .= $element_debug;



#job options end
###

# HIDDEN
$form_elements .= GipTemplate::create_form_element_hidden(
    value => $client_id,
    name => "client_id",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => $id,
    name => "id",
);

## BUTTON
$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{update_message},
    name => "B2",
);

## FORM
$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "mod_scheduled_job",
    link => "./ip_mod_scheduled_job.cgi",
    method => "POST",
    autocomplete => "off",
);

print $form;


print "<script type=\"text/javascript\">\n";
print "document.mod_scheduled_job.name.focus();\n";
print "</script>\n";


my $form_elements_mail_detail .= $element_send_changes_only;
$form_elements_mail_detail .= $element_mail_recipients;
$form_elements_mail_detail .= $element_smtp_server;
$form_elements_mail_detail .= $element_mail_from;


my $form_elements_mail_detail_backup .= $element_mail_recipients;
$form_elements_mail_detail_backup .= $element_smtp_server;
$form_elements_mail_detail_backup .= $element_mail_from;


$form_elements_global_discovery =~ s/'/\\'/g;
$form_elements_global_discovery =~ s/\n//g;
$form_elements_network_snmp =~ s/'/\\'/g;
$form_elements_network_snmp =~ s/\n//g;
$form_elements_host_dns =~ s/'/\\'/g;
$form_elements_host_dns =~ s/\n//g;
$form_elements_host_dns_global =~ s/'/\\'/g;
$form_elements_host_dns_global =~ s/\n//g;
$form_elements_host_snmp =~ s/'/\\'/g;
$form_elements_host_snmp =~ s/\n//g;
$form_elements_host_snmp_global =~ s/'/\\'/g;
$form_elements_host_snmp_global =~ s/\n//g;
$form_elements_vlan =~ s/'/\\'/g;
$form_elements_vlan =~ s/\n//g;
$form_elements_vlan_global =~ s/'/\\'/g;
$form_elements_vlan_global =~ s/\n//g;
$form_elements_changes_only =~ s/'/\\'/g;
$form_elements_changes_only =~ s/\n//g;
$form_elements_mail_detail =~ s/'/\\'/g;
$form_elements_mail_detail =~ s/\n//g;
$form_elements_leases =~ s/'/\\'/g;
$form_elements_leases =~ s/\n//g;
$element_kea_url =~ s/'/\\'/g;
$element_kea_url =~ s/\n//g;
$form_elements_db_backup =~ s/'/\\'/g;
$form_elements_db_backup =~ s/\n//g;
$form_elements_mail_detail_backup =~ s/'/\\'/g;
$form_elements_mail_detail_backup =~ s/\n//g;
$form_elements_aws =~ s/'/\\'/g;
$form_elements_aws =~ s/\n//g;
$form_elements_azure =~ s/'/\\'/g;
$form_elements_azure =~ s/\n//g;
$form_elements_gcp =~ s/'/\\'/g;
$form_elements_gcp =~ s/\n//g;
$form_elements_cmm =~ s/'/\\'/g;
$form_elements_cmm =~ s/\n//g;


print <<EOF;
<script type="text/javascript">
<!--
EOF
print '$(document).ready(function (){';
print <<EOF;
	changeHideOpts("$discovery_type");
});


function changeHideOpts(TYPE){
    console.log("changing form elements:" + TYPE);
    if ( TYPE == 1 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_global_discovery';
    } else if ( TYPE == 2 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_network_snmp';
    } else if ( TYPE == 3 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_host_dns';
    } else if ( TYPE == 4 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_host_snmp';
    } else if ( TYPE == 5 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_vlan';
    } else if ( TYPE == 6 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_leases';
    } else if ( TYPE == 7 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_db_backup';
    } else if ( TYPE == 8 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_aws';
    } else if ( TYPE == 9 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_azure';
    } else if ( TYPE == 10 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_gcp';
    } else if ( TYPE == 11 ) {
        document.getElementById('HideOpts').innerHTML = '$form_elements_cmm';
    }
}


function changeHideVLAN(){
    var x = document.getElementById('use_vlan_discovery').checked;
    if ( x == true ) {
		document.getElementById('HideVLAN').innerHTML = '$form_elements_vlan_global';
    } else {
		document.getElementById('HideVLAN').innerHTML = '';
    }
}    

function changeHideHostDNS(){
    var x = document.getElementById('use_host_discovery_dns').checked;
    if ( x == true ) {
		document.getElementById('HideHostDNS').innerHTML = '$form_elements_host_dns_global';
    } else {
		document.getElementById('HideHostDNS').innerHTML = '';
    }
}    

function changeHideHostSNMP(TYPE){
    var x = document.getElementById('use_host_discovery_snmp').checked;
    if ( x == true ) {
		document.getElementById('HideHostSNMP').innerHTML = '$form_elements_host_snmp_global';
    } else {
		document.getElementById('HideHostSNMP').innerHTML = '';
    }
}    
function changeHideMail(TYPE){
    var x = document.getElementById('send_result_by_mail').checked;
    if ( x == true ) {
        document.getElementById('HideMail').innerHTML = '$form_elements_mail_detail';
    } else {
        document.getElementById('HideMail').innerHTML = '';
    }
}    

function changeHideMailBackup(){
    var x = document.getElementById('send_result_by_mail').checked;
    if ( x == true ) {
        document.getElementById('HideMailBackup').innerHTML = '$form_elements_mail_detail_backup';
    } else {
        document.getElementById('HideMailBackup').innerHTML = '';
    }
} 

function disableDeleteNetwork(TYPE){
    if ( TYPE == "delete_not_found_networks" ) {
        document.getElementById('report_not_found_networks').checked = false;
    } else {
        document.getElementById('delete_not_found_networks').checked = false;
    }
}    

function changeDefaultFrom(TYPE){
    var default_from = $default_from;
    console.log("changing form elements:" + TYPE + ' - val:' + default_from[TYPE]);
    var val = default_from[TYPE];
    if ( val == undefined ) {
        val = "";
    }
    document.getElementById('mail_from').value = val;
}  

function disableDNSOptions(){
    var x = document.getElementById('ignore_dns').checked;
    if ( x == true ) {
        document.getElementById('ignore_generic_auto').disabled = true;
        document.getElementById('ignorar').disabled = true;
        document.getElementById('zone_transfer').disabled = true;
        document.getElementById('delete_down_hosts_hint_text').innerHTML = '$$lang_vars{delete_hosts_explic_ping_only_message}';
    } else {
        document.getElementById('ignore_generic_auto').disabled = false;
        document.getElementById('ignorar').disabled = false;
        document.getElementById('zone_transfer').disabled = false;
        document.getElementById('delete_down_hosts_hint_text').innerHTML = '$$lang_vars{delete_hosts_explic_message}';
    }
}

function disableDNSOptionsAWSDNS(TYPE){
    console.log("disableDNSOptionsAWSDNS: " + TYPE);
    if ( TYPE == "aws_dns" ) {
        var x = document.getElementById('aws_dns').checked;
        if ( x == true ) {
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('aws_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "ignore_dns" ) {
        var x = document.getElementById('ignore_dns').checked;
        if ( x == true ) {
            document.getElementById('aws_dns').checked = false;
            document.getElementById('aws_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('aws_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "zone_transfer" ) {
        var x = document.getElementById('zone_transfer').checked;
        if ( x == true ) {
            document.getElementById('aws_dns').checked = false;
            document.getElementById('aws_dns').disabled = true;
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
        } else {
            document.getElementById('aws_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    }
}

function disableDNSOptionsAzureDNS(TYPE){
    console.log("disableDNSOptionsAzureDNS: " + TYPE);
    if ( TYPE == "azure_dns" ) {
        var x = document.getElementById('azure_dns').checked;
        if ( x == true ) {
            document.getElementById('HideAzueResourceGroup').innerHTML = '$element_azure_resource_group';
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('HideAzueResourceGroup').innerHTML = '';
            document.getElementById('azure_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "ignore_dns" ) {
        var x = document.getElementById('ignore_dns').checked;
        if ( x == true ) {
            document.getElementById('HideAzueResourceGroup').innerHTML = '';
            document.getElementById('azure_dns').checked = false;
            document.getElementById('azure_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('azure_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "zone_transfer" ) {
        var x = document.getElementById('zone_transfer').checked;
        if ( x == true ) {
            document.getElementById('HideAzueResourceGroup').innerHTML = '';
            document.getElementById('azure_dns').checked = false;
            document.getElementById('azure_dns').disabled = true;
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
        } else {
            document.getElementById('azure_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    }
}

function disableAzureCert(VALUE){
    console.log("disableAzureCert:" + VALUE);
    if ( VALUE == "cert" ) {
        document.getElementById('azure_cert_file').disabled = false;
        document.getElementById('azure_secret_key_value').disabled = true;
    } else {
        document.getElementById('azure_cert_file').disabled = true;
        document.getElementById('azure_secret_key_value').disabled = false;
    }
}

function enableResourceGroup(){
    var x = document.getElementById('azure_dns').checked;
    console.log("enableResourceGroup");
    if ( x == true ) {
        document.getElementById('azure_resource_group').disabled = false;
    } else {
        document.getElementById('azure_resource_group').disabled = true;
    }
}

function disableDNSOptionsGCPDNS(TYPE){
    console.log("disableDNSOptionsGCPDNS: " + TYPE);
    if ( TYPE == "aws_dns" ) {
        var x = document.getElementById('gcp_dns').checked;
        if ( x == true ) {
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('gcp_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "ignore_dns" ) {
        var x = document.getElementById('ignore_dns').checked;
        if ( x == true ) {
            document.getElementById('gcp_dns').checked = false;
            document.getElementById('gcp_dns').disabled = true;
            document.getElementById('zone_transfer').checked = false;
            document.getElementById('zone_transfer').disabled = true;
        } else {
            document.getElementById('gcp_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    } else if ( TYPE == "zone_transfer" ) {
        var x = document.getElementById('zone_transfer').checked;
        if ( x == true ) {
            document.getElementById('gcp_dns').checked = false;
            document.getElementById('gcp_dns').disabled = true;
            document.getElementById('ignore_dns').checked = false;
            document.getElementById('ignore_dns').disabled = true;
        } else {
            document.getElementById('gcp_dns').disabled = false;
            document.getElementById('ignore_dns').disabled = false;
            document.getElementById('zone_transfer').disabled = false;
        }
    }
}

function changeLeaseFile_URL(TYPE){
    console.log("leases type: " + TYPE);
    if ( TYPE == "$$lang_vars{kea_api_message}" ) {
        document.getElementById('HideLeasesFile').innerHTML = '';
        document.getElementById('HideKeaUrl').innerHTML = '$element_kea_url';
    } else {
        document.getElementById('HideLeasesFile').innerHTML = '$element_leases_file';
        document.getElementById('HideKeaUrl').innerHTML = '';
    }
}

-->
</script>
EOF


$gip->print_end("$client_id", "", "", "");
