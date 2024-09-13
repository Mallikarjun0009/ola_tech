#!/usr/bin/perl -T -w

# Copyright (C) 2013 Marc Uebel

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

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


# check Permissions
#TEST management_types beruecksichtigen
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="manage_custom_columns_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


my $management_type=$daten{manage_type} || "";

my ($ce_id,$ce_host_id);
my ($which_clients,$custom_column,$custom_host_column,$select_type,$select_type_host,$select_items,$select_items_hosts,$custom_site_column,$select_type_site,$select_items_sites,$mandatory_site,$custom_line_column,$select_type_line,$select_items_lines,$mandatory_line,$mandatory_custom_net, $mandatory_custom_host);
$which_clients = $daten{which_clients} || "9999";
if ( $which_clients !~ /^\d{1,4}/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

my $align="align=\"right\"";
my $align1="";
my $ori="left";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $object;

## Checks

if ( $management_type eq "insert_cc" || $management_type eq "insert_cc_custom" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_added_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{insert_cc_name_message}") if $management_type eq "insert_cc_custom" && ! $daten{'custom_column'};
	my %cc=$gip->get_custom_columns_hash_client_all("$client_id");
	$custom_column = $daten{'custom_column'} || "";
    $custom_column = $gip->remove_whitespace_se("$custom_column");
	$custom_column =~ s/^\++//;
	$custom_column =~ s/[.?]/_/g;
	if ( ! $custom_column && $daten{'ce_id'} ) {
		$ce_id = $daten{'ce_id'};
		$gip->print_error("$client_id","$$lang_vars{mal_signo_error_message}") if $ce_id !~ /^\d{1,4}$/;
		$custom_column=$gip->get_predef_column_name("$client_id","$ce_id");
	}
	$gip->print_error("$client_id","<i>$custom_column</i>: $$lang_vars{cc_exists_message}") if defined($cc{"$custom_column"}) && $which_clients ne "9999"; 
	$gip->print_error("$client_id","<i>$custom_column</i>: $$lang_vars{cc_no_whitespace_message}") if $custom_column =~ /\s/;
	$mandatory_custom_net = $daten{'mandatory_custom_net'} || 0;
    $mandatory_custom_net = 1 if $mandatory_custom_net eq "yes";
	$select_type = $daten{'select_type'} || "";
	$gip->print_error("$client_id","$$lang_vars{no_minus_sign_in_column_name_allowed_message}") if $select_type eq "select" && $daten{'custom_column'} =~ /-/;
	$select_items = $daten{'select_items'} || "";
    $select_items = $gip->remove_whitespace_all("$select_items");

	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $select_type ne "$$lang_vars{text_message}" && ! $daten{'select_items'} && $management_type ne "insert_cc";

} elsif ( $management_type eq "insert_host_cc" || $management_type eq "insert_host_cc_custom" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_added_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{insert_cc_name_message}") if $management_type eq "insert_host_cc_custom" && ! $daten{'custom_host_column'};
	my %cc_host=$gip->get_custom_host_columns_hash_client_all("$client_id");

	$mandatory_custom_host = $daten{'mandatory_custom_host'} || 0;
    $mandatory_custom_host = 1 if $mandatory_custom_host eq "yes";
	$custom_host_column = $daten{'custom_host_column'} || "";
    $custom_host_column = $gip->remove_whitespace_se("$custom_host_column");
	$select_type_host = $daten{'select_type_host'} || "";
	$gip->print_error("$client_id","$$lang_vars{no_minus_sign_in_column_name_allowed_message}") if $select_type_host eq "select" && $daten{'custom_host_column'} =~ /-/;
	$select_items_hosts = $daten{'select_items_hosts'} || "";
    $select_items_hosts = $gip->remove_whitespace_all("$select_items_hosts");
	$gip->print_error("$client_id","<i>$custom_host_column</i>: $$lang_vars{cc_no_whitespace_message}") if $custom_host_column =~ /\s/;
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $select_type_host ne "$$lang_vars{text_message}" && ! $daten{'select_items_hosts'} && $management_type ne "insert_host_cc";


	if ( ! $custom_host_column && $daten{'ce_host_id'} ) {
		$ce_host_id = $daten{'ce_host_id'};
		$gip->print_error("$client_id","$$lang_vars{mal_signo_error_message}") if $ce_host_id !~ /^\d{1,4}$/;
		$custom_host_column=$gip->get_predef_host_column_name("$client_id","$ce_host_id");
	}
	$gip->print_error("$client_id","<i>$custom_host_column</i>: $$lang_vars{cc_exists_message}") if defined($cc_host{"$custom_host_column"}) && $which_clients ne "9999"; 

} elsif ( $management_type eq "insert_site_cc" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_added_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{insert_cc_name_message}") if ! $daten{'custom_site_column'};

	$custom_site_column = $daten{'custom_site_column'} || "";
    $custom_site_column = $gip->remove_whitespace_se("$custom_site_column");
	$mandatory_site = $daten{'mandatory_site'} || 0;
    $mandatory_site = 1 if $mandatory_site eq "yes";
	my $cc_id = $gip->get_site_id_from_name("$client_id","$custom_site_column") || "";
	$gip->print_error("$client_id","<i>$custom_site_column</i>: $$lang_vars{cc_exists_message}") if $cc_id;
	$gip->print_error("$client_id","<i>$custom_site_column</i>: $$lang_vars{cc_no_whitespace_message}") if $custom_site_column =~ /\s/;

	$select_type_site = $daten{'select_type_site'} || "";
	$select_items_sites = $daten{'select_items_sites'} || "";
    $select_items_sites = $gip->remove_whitespace_all("$select_items_sites");
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $select_type_site ne "$$lang_vars{text_message}" && ! $daten{'select_items_sites'};

} elsif ( $management_type eq "insert_line_cc" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_added_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{insert_cc_name_message}") if ! $daten{'custom_line_column'};

	$custom_line_column = $daten{'custom_line_column'} || "";
    $custom_line_column = $gip->remove_whitespace_se("$custom_line_column");
	$mandatory_line = $daten{'mandatory_line'} || 0;
    $mandatory_line = 1 if $mandatory_line eq "yes";
	my $cc_id = $gip->get_line_id_from_name("$client_id","$custom_line_column") || "";
	$gip->print_error("$client_id","<i>$custom_line_column</i>: $$lang_vars{cc_exists_message}") if $cc_id;
	$gip->print_error("$client_id","<i>$custom_line_column</i>: $$lang_vars{cc_no_whitespace_message}") if $custom_line_column =~ /\s/;

	$select_type_line = $daten{'select_type_line'} || "";
	$select_items_lines = $daten{'select_items_lines'} || "";
    $select_items_lines = $gip->remove_whitespace_all("$select_items_lines");
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $select_type_line ne "$$lang_vars{text_message}" && ! $daten{'select_items_lines'};


} elsif ( $management_type eq "mod_cc" || $management_type eq "mod_host_cc" || $management_type eq "mod_site_cc" || $management_type eq "mod_line_cc" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_updated_message}","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $management_type eq "mod_cc" && ! $daten{mod_select_values};
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $management_type eq "mod_host_cc" && ! $daten{mod_select_host_values};
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $management_type eq "mod_site_cc" && ! $daten{mod_select_site_values};
	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $management_type eq "mod_line_cc" && ! $daten{mod_select_line_values};

} elsif ( $management_type =~ /^mod_cc_name/ ) {
	if ( $management_type =~ /network/ ) {
		$object = "network";
	} elsif ( $management_type =~ /host/ ) {
		$object = "host";
	} elsif ( $management_type =~ /site/ ) {
		$object = "site";
	} elsif ( $management_type =~ /line/ ) {
		$object = "line";
	}

	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_updated_message}","$vars_file");
	
#	$gip->print_error("$client_id","$$lang_vars{insert_item_message}") if $management_type eq "mod_cc_name" && ! $daten{mod_select_host_values};

} elsif ( $management_type eq "delete_cc" || $management_type eq "delete_host_cc" || $management_type eq "delete_site_column" || $management_type eq "delete_line_column" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}: $$lang_vars{cc_deleted_message}","$vars_file");
} else {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{manage_custom_columns_message}","$vars_file");
}

#print <<EOF;
#<input type="hidden" id="refreshed" value="no">
#<script type="text/javascript">
#onload=function(){
#var e=document.getElementById("refreshed");
#alert(e.value);
#if(e.value=="no") {
#e.value="yes";
#alert(e.value)
#} else { e.value="no";location.reload(); }
#}
#</script>
#EOF

#print <<EOF;
#<script type="text/javascript">
#if(!!window.performance && window.performance.navigation.type === 2)
#{
#    console.log('Reloading');
#    window.location.reload();
#}
#</script>
#EOF

my @clients = $gip->get_clients();
my @cc_values=$gip->get_custom_columns("$client_id");
#name,id,client_id,column_type_id FROM custom_net_columns
my @ce_values=$gip->get_predef_columns_all("$client_id");
#my %ce_values=$gip->get_predef_columns_hash("$client_id");
my %ce_net_values = $gip->get_predef_column_hash("$client_id","network");;
my %ce_host_values = $gip->get_predef_column_hash("$client_id","host");;
my @cc_host_values=$gip->get_custom_host_columns("$client_id");
my @ce_host_values=$gip->get_predef_host_columns_all("$client_id");
my @cc_site_values=$gip->get_custom_site_columns("$client_id");
my @cc_line_values=$gip->get_custom_line_columns("$client_id");
my $client_name=$gip->get_client_from_id("$client_id");
my $anz_clients_all=$gip->count_clients("$client_id");
my @site_columns=$gip->get_site_columns("$client_id");
my @line_columns=$gip->get_line_columns("$client_id");
my %custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","network");
my %custom_host_columns_select = $gip->get_custom_columns_select_hash("$client_id","host");
my %custom_site_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");
my %custom_line_columns_select = $gip->get_custom_columns_select_hash("$client_id","line");

my $event="";
my $event_new="";


print "<p>\n";

if ( $management_type eq "insert_cc" ) {
	my $last_custom_column_id=$gip->get_last_custom_column_id("$client_id");
	$last_custom_column_id++;
	$ce_id = '-1' if ! $ce_id;
	if ( $which_clients eq "9999" ) {
		my @ids_to_change=$gip->get_custom_column_ids_from_name("$client_id","$custom_column");
		foreach ( @ids_to_change ) {
			$gip->change_custom_column_entry_cc_id("$client_id","$_->[0]","$last_custom_column_id");
		}
		$gip->delete_custom_column_from_name("$client_id","$custom_column");
	}
	my $insert_ok=$gip->insert_custom_column("$which_clients","$last_custom_column_id","$custom_column","$ce_id","$vars_file","$select_type","$select_items");

	my $audit_type="31";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$custom_column ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	@cc_values=$gip->get_custom_columns("$client_id");
	@ce_values=$gip->get_predef_columns_all("$client_id");

} elsif ( $management_type eq "insert_cc_custom" ) {
	my $last_custom_column_id=$gip->get_last_custom_column_id("$client_id");
	$last_custom_column_id++;
	$ce_id = '-1' if ! $ce_id;

	@ce_values=$gip->get_predef_columns_all("$client_id");
	my $j="0";
	foreach ( @ce_values ) {
		if ( "$custom_column" eq "$ce_values[$j]->[1]" ) {
			$gip->print_error("$client_id","$$lang_vars{ce_name_exists_message}: $custom_column");
		}
		$j++;
	}
	@cc_values=$gip->get_custom_columns("$client_id");
	$j="0";
	foreach ( @cc_values ) {
		if ( "$custom_column" eq "$cc_values[$j]->[0]" && ( "$cc_values[$j]->[2]" eq $client_id || "$cc_values[$j]->[2]" eq "9999" ) ) {
			$gip->print_error("$client_id","$$lang_vars{cc_name_exists_message}: $custom_column");
		}
		$j++;
	}

	if ( $which_clients eq "9999" ) {
		my @ids_to_change=$gip->get_custom_column_ids_from_name("$client_id","$custom_column");
		foreach ( @ids_to_change ) {
			$gip->change_custom_column_entry_cc_id("$client_id","$_->[0]","$last_custom_column_id");
		}
		$gip->delete_custom_column_from_name("$client_id","$custom_column");
	}

	my $insert_ok=$gip->insert_custom_column("$which_clients","$last_custom_column_id","$custom_column","$ce_id","$vars_file","$select_type","$select_items","$mandatory_custom_net");

	my $audit_type="31";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$custom_column ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	@cc_values=$gip->get_custom_columns("$client_id");

} elsif ( $management_type eq "mod_cc" ) {
	my %custom_columns_select_old = $gip->get_custom_columns_select_hash("$client_id","network");
	my $cc_name = $daten{'cc_name'};

    mod_select_item_register("network", \%custom_columns_select_old, \@cc_values);

	my $audit_type="147";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$cc_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type =~ /^mod_cc_name/ ) {
    my $cc_id = $daten{'cc_id'};
    my $new_custom_column_name = $daten{'new_custom_column_name'} || "";


	my $param_name = "mandatory_custom_mod_" . $object;

    my $mandatory = $daten{$param_name} || 0;

# get old names
    my $old_name = "";
	if ( $object eq "network" ) {
        $old_name = $gip->get_custom_column_name("$client_id","$cc_id");
	} elsif ( $object eq "host" ) {
        $old_name = $gip->get_custom_host_column_name("$client_id","$cc_id");
	} elsif ( $object eq "site" ) {
        $old_name = $gip->get_site_column_name("$client_id","$cc_id");
	} elsif ( $object eq "line" ) {
        $old_name = $gip->get_line_column_name("$client_id","$cc_id");
	}

	$gip->update_custom_column("$client_id", "$cc_id", "$new_custom_column_name", "$mandatory", "$object");

    my( $audit_type);
	if ( $object eq "network" ) {
		@cc_values = $gip->get_custom_columns("$client_id");
        $audit_type = 147;
	} elsif ( $object eq "host" ) {
		@cc_host_values = $gip->get_custom_host_columns("$client_id");
        $audit_type = 148;
	} elsif ( $object eq "site" ) {
		@cc_site_values = $gip->get_custom_site_columns("$client_id");
        $audit_type = 149;
	} elsif ( $object eq "line" ) {
		@cc_line_values = $gip->get_custom_line_columns("$client_id");
        $audit_type = 150;
	}

	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$old_name > $new_custom_column_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


} elsif ( $management_type eq "mod_host_cc" ) {
    my %custom_columns_select_old = $gip->get_custom_columns_select_hash("$client_id","host");
    my $cc_name = $daten{'cc_name_host'};
    mod_select_item_register("host", \%custom_columns_select_old, \@cc_host_values);

	my $audit_type="148";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$cc_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "delete_cc" ) {
	my $cc_id = $daten{'cc_id'};
	$gip->print_error("$client_id","$$lang_vars{mal_signo_error_message}") if $cc_id !~ /^\d{1,4}$/;
	my $cc_name=$gip->get_custom_column_name("$client_id","$cc_id");
	my $cc_client_id=$gip->get_custom_column_client_id("$client_id","$cc_id");
	my $delete_ok=$gip->delete_custom_column("$client_id","$cc_id");
	my @clients = $gip->get_clients();
	@cc_values=$gip->get_custom_columns("$client_id");
	@ce_values=$gip->get_predef_columns_all("$client_id");

	my $audit_type="32";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $cc_client_id == "9999";
	my $event="$cc_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "insert_host_cc" ) {
	my $last_custom_host_column_id=$gip->get_last_custom_host_column_id();
	$last_custom_host_column_id++;
	$ce_host_id = '-1' if ! $ce_host_id;
	if ( $which_clients eq "9999" ) {
		my @ids_to_change=$gip->get_custom_host_column_ids_from_name("$client_id","$custom_host_column");
		foreach ( @ids_to_change ) {
			$gip->change_custom_host_column_entry_cc_id("$client_id","$_->[0]","$last_custom_host_column_id");
		}
		$gip->delete_custom_host_column_from_name("$client_id","$custom_host_column");
	}
	my $insert_ok=$gip->insert_custom_host_column("$which_clients","$last_custom_host_column_id","$custom_host_column","$ce_host_id","$vars_file","$select_type_host","$select_items_hosts");

	my $audit_type="42";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$custom_host_column ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	@cc_host_values=$gip->get_custom_host_columns("$client_id");
	@ce_host_values=$gip->get_predef_host_columns_all("$client_id");

} elsif ( $management_type eq "insert_host_cc_custom" ) {

	my $last_custom_host_column_id=$gip->get_last_custom_host_column_id();
	$last_custom_host_column_id++;
	$ce_host_id = '-1' if ! $ce_host_id;



	@ce_host_values=$gip->get_predef_host_columns_all("$client_id");
	my $j="0";
	foreach ( @ce_host_values ) {
		if ( "$custom_host_column" eq "$ce_host_values[$j]->[1]" ) {
			$gip->print_error("$client_id","$$lang_vars{ce_name_exists_message}: $custom_host_column");
		}
		$j++;
	}
	@cc_host_values=$gip->get_custom_host_columns("$client_id");
	$j="0";
	foreach ( @cc_host_values ) {
		if ( "$custom_host_column" eq "$cc_host_values[$j]->[0]" && ( "$cc_host_values[$j]->[2]" eq $client_id || "$cc_host_values[$j]->[2]" eq "9999" ) ) {
			$gip->print_error("$client_id","$$lang_vars{cc_name_exists_message}: $custom_host_column");
		}
		$j++;
	}

	if ( $which_clients eq "9999" ) {
	my @ids_to_change=$gip->get_custom_host_column_ids_from_name("$client_id","$custom_host_column");
		foreach ( @ids_to_change ) {
			$gip->change_custom_host_column_entry_cc_id("$client_id","$_->[0]","$last_custom_host_column_id");
		}
		$gip->delete_custom_host_column_from_name("$client_id","$custom_host_column");
	}

	my $insert_ok=$gip->insert_custom_host_column("$which_clients","$last_custom_host_column_id","$custom_host_column","$ce_host_id","$vars_file","$select_type_host","$select_items_hosts","$mandatory_custom_host");
	@cc_host_values=$gip->get_custom_host_columns("$client_id");
	@ce_host_values=$gip->get_predef_host_columns_all("$client_id");

	my $audit_type="42";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$custom_host_column ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
    
	@cc_host_values=$gip->get_custom_host_columns("$client_id");

} elsif ( $management_type eq "delete_host_cc" ) {
	my $cc_host_id = $daten{'cc_host_id'};
	my $cc_host_name=$gip->get_custom_host_column_name("$client_id","$cc_host_id");
	my $cc_client_id=$gip->get_custom_host_column_client_id("$client_id","$cc_host_id");
	my $delete_ok=$gip->delete_custom_host_column("$client_id","$cc_host_id");
	my @clients = $gip->get_clients();
	@cc_host_values=$gip->get_custom_host_columns("$client_id");
	@ce_host_values=$gip->get_predef_host_columns_all("$client_id");

	my $audit_type="43";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $cc_client_id == "9999";
	my $event="$cc_host_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");


} elsif ( $management_type eq "insert_site_cc" ) {

	my $site_column_name = $daten{'custom_site_column'};
	my $j=0;
	foreach ( @site_columns ) {
		my $site_column_name_db=$site_columns[0]->[1];
		if ( "$site_column_name" eq "$site_column_name_db" ) {
			$gip->print_error("$client_id","$$lang_vars{ce_name_exists_message}: $site_column_name");
		}
		$j++;
	}

	my $insert_ok=$gip->insert_site_column("$client_id","$site_column_name","$vars_file","$select_type_site","$select_items_sites","$mandatory_site");
    %custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");
    @cc_site_values=$gip->get_custom_site_columns("$client_id");

	my $audit_type="125";
	my $audit_class="5";
	my $update_type_audit="1";
	my $event="$site_column_name";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "mod_site_cc" ) {
	my %custom_site_columns_select_old = $gip->get_custom_columns_select_hash("$client_id","site");
	my $cc_name = $daten{'cc_name_site'};

    mod_select_item_register("site", \%custom_site_columns_select_old, \@cc_site_values);

	%custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");

	my $audit_type="149";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$cc_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "delete_site_column" ) {

	my $site_column_id = $daten{'site_column_id'};
	my $site_column_name=$gip->get_site_column_name("$client_id","$site_column_id");

	my $delete_ok=$gip->delete_site_column("$client_id","$site_column_id");
    %custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");
    @cc_site_values=$gip->get_custom_site_columns("$client_id");

	my $audit_type="126";
	my $audit_class="5";
	my $update_type_audit="1";
	my $event="$site_column_name";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
	%custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");

} elsif ( $management_type eq "insert_line_cc" ) {

	my $line_column_name = $daten{'custom_line_column'};
	my $j=0;
	foreach ( @line_columns ) {
		my $line_column_name_db=$line_columns[0]->[1];
		if ( "$line_column_name" eq "$line_column_name_db" ) {
			$gip->print_error("$client_id","$$lang_vars{ce_name_exists_message}: $line_column_name");
		}
		$j++;
	}

	my $insert_ok=$gip->insert_line_column("$client_id","$line_column_name","$vars_file","$select_type_line","$select_items_lines","$mandatory_line");
    %custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","line");
    @cc_line_values=$gip->get_custom_line_columns("$client_id");

	my $audit_type="151";
	my $audit_class="5";
	my $update_type_audit="1";
	my $event="$line_column_name";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "mod_line_cc" ) {

    my %custom_columns_select_old = $gip->get_custom_columns_select_hash("$client_id","line");
	my $cc_name = $daten{'cc_name_line'};

	mod_select_item_register("line", \%custom_columns_select_old, \@cc_line_values);

    @cc_line_values=$gip->get_custom_line_columns("$client_id");

	my $audit_type="150";
	my $audit_class="5";
	my $update_type_audit="1";
	my $audit_which_clients=$$lang_vars{actual_client_message};
	$audit_which_clients=$$lang_vars{all_clients_message} if $client_id == "9999";
	my $event="$cc_name ($audit_which_clients)";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

} elsif ( $management_type eq "delete_line_column" ) {

	my $line_column_id = $daten{'line_column_id'};
	my $line_column_name=$gip->get_line_column_name("$client_id","$line_column_id");

	my $delete_ok=$gip->delete_line_column("$client_id","$line_column_id");
	%custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","line");
    @cc_line_values=$gip->get_custom_line_columns("$client_id");

	my $audit_type="152";
	my $audit_class="5";
	my $update_type_audit="1";
	my $event="$line_column_name";
	$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
}


print "<br><p>\n";


print <<EOF;

<script type="text/javascript">
<!--
function showItemField(value,name){
  if( value == "$$lang_vars{select_message}" | value == "$$lang_vars{multiple_select_message}" ) {
    if( name == "select_items" ) {
      document.getElementById('Hide1').innerHTML = "$$lang_vars{select_items_message}";
      document.getElementById('Hide2').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"" + name + "\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
      document.getElementById('Hide3_host').innerHTML = "($$lang_vars{coma_separated_list})";
    } else if ( name == "select_items_hosts" ) { 
      document.getElementById('Hide1_host').innerHTML = "$$lang_vars{select_items_message}";
      document.getElementById('Hide2_host').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"" + name + "\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
      document.getElementById('Hide3_host').innerHTML = "($$lang_vars{coma_separated_list})";
    } else if ( name == "select_items_sites" ) { 
      document.getElementById('Hide1_site').innerHTML = "$$lang_vars{select_items_message}";
      document.getElementById('Hide2_site').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"" + name + "\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
      document.getElementById('Hide3_site').innerHTML = "($$lang_vars{coma_separated_list})";
    } else if ( name == "select_items_lines" ) { 
      document.getElementById('Hide1_line').innerHTML = "$$lang_vars{select_items_message}";
      document.getElementById('Hide2_line').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"" + name + "\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
      document.getElementById('Hide3_line').innerHTML = "($$lang_vars{coma_separated_list})";
    }
  } else {
    if( name == "select_items" ) {
      document.getElementById('Hide1').innerHTML = "";
      document.getElementById('Hide2').innerHTML = "";
      document.getElementById('Hide3').innerHTML = "";
    } else if ( name == "select_items_hosts" ) { 
      document.getElementById('Hide1_host').innerHTML = "";
      document.getElementById('Hide2_host').innerHTML = "";
      document.getElementById('Hide3_host').innerHTML = "";
    } else if ( name == "select_items_sites" ) { 
      document.getElementById('Hide1_site').innerHTML = "";
      document.getElementById('Hide2_site').innerHTML = "";
      document.getElementById('Hide3_site').innerHTML = "";
    } else if ( name == "select_items_lines" ) { 
      document.getElementById('Hide1_line').innerHTML = "";
      document.getElementById('Hide2_line').innerHTML = "";
      document.getElementById('Hide3_line').innerHTML = "";
    }
  }
}
-->
</script>

EOF



## CUSTOM NET COLUMNS

##print "<table border=\"1\" cellpadding=\"25\" cellspacing=\"1\" width=\"100%\"><tr><td valign=\"top\" $align1>\n";
print "<table border=\"0\" align='center' width=\"100%\"><tr><td align='center' valign=\"top\" $align1 width=\"25%\" style='border-right: 1px solid #cdd0d4;' >\n";
print "<h3>$$lang_vars{network_columns_message}</h3><p>\n";

my $j=0;
my $ce_values_count=@ce_values; 
if ( ( $ce_values_count == "1" && $ce_values[0]->[1] eq "NOTYPE" )  ||  $ce_values_count == 0 ) {
	print "<h5>$$lang_vars{insert_predef_column_message}</h5><p>\n";
	print "<font color=\"gray\"><i>$$lang_vars{no_predef_net_columns_available_message}</i></font><br><p>\n";
} else {
	print "<form  method=\"POST\" border=\"0\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<h5>$$lang_vars{insert_predef_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
	print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td>\n";

	print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"ce_id\" size=\"1\">\n";
	foreach (@ce_values) {
		print "<option value=\"$ce_values[$j]->[0]\">$ce_values[$j]->[1]</option>" if $ce_values[$j]->[1] ne "NOTYPE";
		$j++;
	}
	print "</select></td></tr>\n";

	if ( $anz_clients_all > 1 ) {
		print "<tr><td colspan=\"2\">$$lang_vars{all_clients_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"9999\" checked>&nbsp;&nbsp;&nbsp;$$lang_vars{actual_client_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"$client_id\"><font color=\"white\">x</font></td></tr>\n";
	}

        print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";

	print "</table>\n";
	print "</form>\n";
}

# INSERT CUSTOM NET COLUMN


print "<br><p>\n";
print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
print "<h5>$$lang_vars{insert_custom_column_message}</h5><p>\n";
print "<table border=\"0\" cellpadding=\"7\">\n";
print "<tr><td align=\"right\">$$lang_vars{tipo_message}</td><td>";

print <<EOF;
<select class='custom-select custom-select-sm m-1' style='width: 12em' size="1" name="select_type" id="select_type" onchange="showItemField(this.value,'select_items');">
<option selected>$$lang_vars{text_message}</option>
<option>$$lang_vars{select_message}</option>
</select>
</td><td align="right"></td></tr>
EOF

print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td><input type=\"text\" class='form-control form-control-sm m-1' style='width: 12em' size=\"15\" name=\"custom_column\" value=\"\" maxlength=\"15\"></td></tr>\n";
print "<tr><td align=\"right\"><span id=\"Hide1\"></span></td><td><span id=\"Hide2\"></span></td><td align=\"right\"><span id=\"Hide3\"></span></td></tr>\n";
print "<tr><td align=\"left\" colspan=\"2\">$$lang_vars{mandatory_message}  <input type=\"checkbox\" class='m-2' name=\"mandatory_custom_net\" value=\"yes\"></td></tr>\n";

if ( $anz_clients_all > 1 ) {
	print "<tr><td colspan=\"2\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\">$$lang_vars{all_clients_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"9999\" checked>&nbsp;&nbsp;&nbsp;$$lang_vars{actual_client_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"$client_id\"><font color=\"white\">x</font></td></tr>\n";
}
print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_cc_custom\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";
print "</table>\n";
print "</form>\n";



# MOD NET COLUMN

print "<br><p>\n";
print "<h5>$$lang_vars{edit_column_message}</h5><p>\n";

my @cc_values_custom_only;
$j=0;
foreach (@cc_values) {
	if ( ! $ce_net_values{$cc_values[$j]->[0]} ) {
		push @cc_values_custom_only, $_;
	}
	$j++;
}

if ( @cc_values_custom_only ) {
    print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	$gip->print_mod_column_form("$client_id", "$vars_file", \@cc_values, "network");
	$gip->create_custom_column_asso_js(\@cc_values, "network");
} else {
    print "<i>$$lang_vars{no_cc_message}</i><br>\n";
}



# MOD NET COLUMN SELECT OPTIONS

if ( $cc_values[0]->[0] ) {
	%custom_columns_select = $gip->get_custom_columns_select_hash("$client_id","network");
    my $select_values_string;
    my %select_values_strings;
	print "<br><p>\n";
    if ( ! %custom_columns_select ) {
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
        print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
    } else {
		print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
		print "<table border=\"0\" cellpadding=\"7\">\n";
		print "<tr><td>$$lang_vars{title_message}</td><td>";
		print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_name\" size=\"1\" id=\"cc_name\" onchange=\"showNameChangeField(this.value);\">\n";
		print "<option></option>\n";
		$j=0;
		foreach (@cc_values) {
			my $select_values_string_ref;
			my $cc_name = $cc_values[$j]->[0];
			my $cc_id = $cc_values[$j]->[1];
			$select_values_string_ref = $custom_columns_select{$cc_id}[2] if exists $custom_columns_select{$cc_id};
			if ( ! $select_values_string_ref ) {
				# ignore non select columns
				$j++;
				next;
			}

			$select_values_strings{$cc_name} = $select_values_string_ref;

			if ( $cc_values[$j]->[2] == "9999" ) {
				print "<option value=\"$cc_name\">$cc_name ($$lang_vars{for_all_clients_message})</option>";
			} else {
				print "<option value=\"$cc_name\">$cc_name</option>";
			}
			$j++;
		}
		print "</select></td></tr>\n";
		print "<tr><td><span id=\"Hide1_mod\"></span></td><td><span id=\"Hide2_mod\"></span></td></tr>\n";
		print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"mod_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{update_message}\" name=\"B1\"></td><td></td></tr>\n";
		print "</table>\n";
		print "</form>\n";

		# create js object: name => select-options
		my $js_object_select_values = 'var cc_values_select = {';
		foreach my $key ( keys %select_values_strings ) {
			my $select_values_string_ref = $select_values_strings{$key};
			my $select_string = join(",", @$select_values_string_ref);
			$js_object_select_values .= "$key: \"$select_string\",";
		}
		$js_object_select_values =~ s/,$//;
		$js_object_select_values .= '};';


print <<EOF;

<script type="text/javascript">
<!--

$js_object_select_values

function showNameChangeField(name){
  if ( cc_values_select[name] ) {
    document.getElementById('Hide1_mod').innerHTML = "$$lang_vars{select_items_message}";
    document.getElementById('Hide2_mod').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"mod_select_values\\\" id=\\\"mod_select_values\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
    document.getElementById('mod_select_values').value = cc_values_select[name];
  } else {
    document.getElementById('Hide1_mod').innerHTML = "";
    document.getElementById('Hide2_mod').innerHTML = "";
  }
}
-->
</script>
EOF
	}

}

# DELETE NET COLUMN

if ( $cc_values[0]->[0] ) {
	print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<br><p>\n";
	print "<h5>$$lang_vars{delete_custom_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
	print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
	print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_id\" size=\"1\">\n";
	$j=0;
	foreach (@cc_values) {
		if ( $cc_values[$j]->[2] == "9999" ) {
			print "<option value=\"$cc_values[$j]->[1]\">$cc_values[$j]->[0] ($$lang_vars{for_all_clients_message})</option>";
		} else {
			print "<option value=\"$cc_values[$j]->[1]\">$cc_values[$j]->[0]</option>";
		}
		$j++;
	}
	print "</select></td></tr>\n";
	print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"delete_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{borrar_message}\" name=\"B1\"></td><td></td></tr>\n";
	print "</table>\n";
	print "</form>\n";
}



print "</td><td align='center' valign=\"top\" $align1 width=\"25%\" style='border-right: 1px solid #cdd0d4;'>\n";


### CUSTOM HOST COLUMNS

	print "<h3>$$lang_vars{host_columns_message}</h3><p>\n";

$j=0;
my $ce_host_values_count=@ce_host_values; 
if ( ( $ce_host_values_count == "1" && $ce_host_values[0]->[1] eq "NOTYPE" ) || ( $ce_host_values_count == 0 ) ) {
	print "<h5>$$lang_vars{insert_predef_column_message}</h5><p>\n";
	print "<font color=\"gray\"><i>$$lang_vars{no_predef_host_columns_available_message}</i></font><br><p>\n";
} else {
	print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<h5>$$lang_vars{insert_predef_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
	print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td>\n";

	print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"ce_host_id\" size=\"1\">\n";
	foreach (@ce_host_values) {
		print "<option value=\"$ce_host_values[$j]->[0]\">$ce_host_values[$j]->[1]</option>" if $ce_host_values[$j]->[1] ne "NOTYPE";
		$j++;
	}
	print "</select></td></tr>\n";



	if ( $anz_clients_all > 1 ) {
		print "<tr><td colspan=\"2\">$$lang_vars{all_clients_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"9999\" checked>&nbsp;&nbsp;&nbsp;$$lang_vars{actual_client_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"$client_id\"><font color=\"white\">x</font></td></tr>\n";
	}

	print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_host_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";
	print "</table>\n";
	print "</form>\n";
}

# INSERT CUSTOM HOST COLUMN

print "<br><p>\n";
print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
print "<h5>$$lang_vars{insert_custom_column_message}</h5><p>\n";
print "<table border=\"0\" cellpadding=\"7\">\n";
print "<tr><td align=\"right\">$$lang_vars{tipo_message}</td><td>";

print <<EOF;
<select class='custom-select custom-select-sm m-1' style='width: 12em' size="1" name="select_type_host" id="select_type_host" onchange="showItemField(this.value,'select_items_hosts');">
<option selected>$$lang_vars{text_message}</option>
<option>$$lang_vars{select_message}</option>
</select>
</td><td align="right"></td></tr>
EOF


print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td><input type=\"text\" class='form-control form-control-sm m-1' style='width: 12em' size=\"15\" name=\"custom_host_column\" value=\"\" maxlength=\"15\"></td><td align=\"right\"></td></tr>\n";
print "<tr><td align=\"right\"><span id=\"Hide1_host\"></span></td><td><span id=\"Hide2_host\"></span></td><td align=\"right\"><span id=\"Hide3_host\"></span></td></tr>\n";
print "<tr><td align=\"left\" colspan=\"2\">$$lang_vars{mandatory_message}  <input type=\"checkbox\" class='m-2' name=\"mandatory_custom_host\" value=\"yes\"></td></tr>\n";

if ( $anz_clients_all > 1 ) {
	print "<tr><td colspan=\"3\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\">$$lang_vars{all_clients_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"9999\" checked>&nbsp;&nbsp;&nbsp;$$lang_vars{actual_client_message}<input type=\"radio\" class='m-2' name=\"which_clients\" value=\"$client_id\"><font color=\"white\">x</font></td></tr>\n";
}
print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_host_cc_custom\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";
print "</table>\n";
print "</form>\n";



# MOD HOST COLUMN

print "<br><p>\n";
print "<h5>$$lang_vars{edit_column_message}</h5><p>\n";

my @cc_host_values_custom_only;
$j=0;
foreach (@cc_host_values) {
    if ( ! $ce_host_values{$cc_host_values[$j]->[0]} ) {
        push @cc_host_values_custom_only, $_;
    }
    $j++;
}

if ( @cc_host_values_custom_only ) {
    print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	$gip->print_mod_column_form("$client_id", "$vars_file", \@cc_host_values, "host");
	$gip->create_custom_column_asso_js(\@cc_host_values, "host");
} else {
    print "<i>$$lang_vars{no_cc_message}</i><br>\n";
}



# MOD HOST COLUMN SELECT OPTIONS

if ( $cc_host_values[0]->[0] ) {
	%custom_host_columns_select = $gip->get_custom_columns_select_hash("$client_id","host");
    my $select_values_string;
    my %select_values_strings;
	print "<br><p>\n";
    if ( ! %custom_host_columns_select ) {
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
        print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
    } else {
        print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
        print "<table border=\"0\" cellpadding=\"7\">\n";
#        print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
        print "<tr><td>$$lang_vars{title_message}</td><td>";
        print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_name_host\" size=\"1\" id=\"cc_name_host\" onchange=\"showNameChangeFieldHost(this.value);\">\n";
        print "<option></option>\n";
        $j=0;
        foreach (@cc_host_values) {
            my $select_values_string_ref;
            my $cc_name = $cc_host_values[$j]->[0];
            my $cc_id = $cc_host_values[$j]->[1];
            $select_values_string_ref = $custom_host_columns_select{$cc_id}[2] if exists $custom_host_columns_select{$cc_id};
            if ( ! $select_values_string_ref ) {
                # ignore non select columns
                $j++;
                next;
            }

            $select_values_strings{$cc_name} = $select_values_string_ref;

            if ( $cc_host_values[$j]->[2] == "9999" ) {
                print "<option value=\"$cc_name\">$cc_name ($$lang_vars{for_all_clients_message})</option>";
            } else {
                print "<option value=\"$cc_name\">$cc_name</option>";
            }
            $j++;
        }
        print "</select></td></tr>\n";
        print "<tr><td><span id=\"Hide1_mod_host\"></span></td><td><span id=\"Hide2_mod_host\"></span></td></tr>\n";
        print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"mod_host_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{update_message}\" name=\"B1\"></td><td></td></tr>\n";
        print "</table>\n";
        print "</form>\n";

        # create js object: name => select-options
        my $js_object_select_values = 'var cc_values_select_host = {';
        foreach my $key ( keys %select_values_strings ) {
            my $select_values_string_ref = $select_values_strings{$key};
            my $select_string = join(",", @$select_values_string_ref);
            $js_object_select_values .= "$key: \"$select_string\",";
        }
        $js_object_select_values =~ s/,$//;
        $js_object_select_values .= '};';


print <<EOF;

<script type="text/javascript">
<!--

$js_object_select_values

function showNameChangeFieldHost(name){
  if ( cc_values_select_host[name] ) {
    document.getElementById('Hide1_mod_host').innerHTML = "$$lang_vars{select_items_message}";
    document.getElementById('Hide2_mod_host').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"mod_select_host_values\\\" id=\\\"mod_select_host_values\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
    document.getElementById('mod_select_host_values').value = cc_values_select_host[name];
  } else {
    document.getElementById('Hide1_mod_host').innerHTML = "";
    document.getElementById('Hide2_mod_host').innerHTML = "";
  }
}
-->
</script>
EOF
    }

}


## DELETE HOST

if ( $cc_host_values[0]->[0] ) {
	print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<br><p>\n";
	print "<h5>$$lang_vars{delete_custom_host_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
	print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
	print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_host_id\" size=\"1\">\n";
	$j=0;
	foreach (@cc_host_values) {
		if ( $cc_host_values[$j]->[2] == "9999" ) {
			print "<option value=\"$cc_host_values[$j]->[1]\">$cc_host_values[$j]->[0] ($$lang_vars{for_all_clients_message})</option>";
		} else {
			print "<option value=\"$cc_host_values[$j]->[1]\">$cc_host_values[$j]->[0]</option>";
		}
		$j++;
	}
	print "</select></td></tr>\n";
	print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"delete_host_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{borrar_message}\" name=\"B1\"></td><td></td></tr>\n";
	print "</table>\n";
	print "</form>\n";
}




### CUSTOM SITE COLUMNS

my $advanced_site_management=$global_config[0]->[17] || "";
$advanced_site_management="" if $advanced_site_management eq "no";

if ( $advanced_site_management ) {

### INSERT SITE COLUMN

	@site_columns=$gip->get_site_columns("$client_id");

	print "</td><td align='center' valign=\"top\" $align1 width=\"25%\" style='border-right: 1px solid #cdd0d4;'>\n";
	print "<h3>$$lang_vars{site_columns_message}</h3><p>\n";

	print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<h5>$$lang_vars{insert_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
    print "<tr><td align=\"right\">$$lang_vars{tipo_message}</td><td>";

print <<EOF;
<select class='custom-select custom-select-sm m-1' style='width: 12em' size="1" name="select_type_site" id="select_type_site" onchange="showItemField(this.value,'select_items_sites');">
<option selected>$$lang_vars{text_message}</option>
<option>$$lang_vars{select_message}</option>
</select>
</td><td align="right"></td></tr>
EOF


	print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td><input type=\"text\" class='form-control form-control-sm m-1' style='width: 12em' size=\"15\" name=\"custom_site_column\" value=\"\" maxlength=\"15\"></td></tr>\n";

	print "<tr><td align=\"right\"><span id=\"Hide1_site\"></span></td><td><span id=\"Hide2_site\"></span></td><td align=\"right\"><span id=\"Hide3_site\"></span></td></tr>\n";

	print "<tr><td align=\"left\" colspan=\"2\">$$lang_vars{mandatory_message}  <input type=\"checkbox\" class='m-2' name=\"mandatory_site\" value=\"yes\"></td></tr>\n";

	print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_site_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";
	print "</table>\n";
	print "</form>\n";



# MOD SITE COLUMN

print "<br><p>\n";
print "<h5>$$lang_vars{edit_column_message}</h5><p>\n";

if ( $cc_site_values[0]->[0] ) {
    print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	$gip->print_mod_column_form("$client_id", "$vars_file", \@cc_site_values, "site");
	$gip->create_custom_column_asso_js(\@cc_site_values, "site");
} else {
    print "<i>$$lang_vars{no_cc_message}</i><br>\n";
}




# MOD SITE COLUMN SELECT OPTIONS

print "<br><p>\n";
if ( $cc_site_values[0]->[0] ) {
    %custom_site_columns_select = $gip->get_custom_columns_select_hash("$client_id","site");
    my $select_values_string;
    my %select_values_strings;
    if ( ! %custom_site_columns_select ) {
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
        print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
    } else {
        print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{edit_select_items_message}</h5b><p>\n";
        print "<table border=\"0\" cellpadding=\"7\">\n";
        print "<tr><td>$$lang_vars{title_message}</td><td>";
        print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_name_site\" size=\"1\" id=\"cc_name_site\" onchange=\"showNameChangeFieldSite(this.value);\">\n";
        print "<option></option>\n";
        $j=0;
        foreach (@cc_site_values) {
            my $select_values_string_ref;
            my $cc_name = $cc_site_values[$j]->[0];
            my $cc_id = $cc_site_values[$j]->[1];
            $select_values_string_ref = $custom_site_columns_select{$cc_id}[2] if exists $custom_site_columns_select{$cc_id};

			if ( ! $cc_name ) {
                $j++;
                next;
            }

            if ( ! $select_values_string_ref ) {
                # ignore non select columns
                $j++;
                next;
            }

            $select_values_strings{$cc_name} = $select_values_string_ref;

            print "<option value=\"$cc_name\">$cc_name</option>";
            $j++;
        }

        print "</select></td></tr>\n";
        print "<tr><td><span id=\"Hide1_mod_site\"></span></td><td><span id=\"Hide2_mod_site\"></span></td></tr>\n";
        print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"mod_site_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{update_message}\" name=\"B1\"></td><td></td></tr>\n";
        print "</table>\n";
        print "</form>\n";

        # create js object: name => select-options
        my $js_object_select_values = 'var cc_values_select_site = {';
        foreach my $key ( keys %select_values_strings ) {
            my $select_values_string_ref = $select_values_strings{$key};
            my $select_string = join(",", @$select_values_string_ref);
            $js_object_select_values .= "$key: \"$select_string\",";
        }
        $js_object_select_values =~ s/,$//;
        $js_object_select_values .= '};';


print <<EOF;

<script type="text/javascript">
<!--

$js_object_select_values

function showNameChangeFieldSite(name){
  if ( cc_values_select_site[name] ) {
    document.getElementById('Hide1_mod_site').innerHTML = "$$lang_vars{select_items_message}";
    document.getElementById('Hide2_mod_site').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"mod_select_site_values\\\" id=\\\"mod_select_site_values\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
    document.getElementById('mod_select_site_values').value = cc_values_select_site[name];
  } else {
    document.getElementById('Hide1_mod_site').innerHTML = "";
    document.getElementById('Hide2_mod_site').innerHTML = "";
  }
}
-->
</script>
EOF
    }

} else {
    print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
   print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
}




### DELETE SITE COLUMN

    print "<br><p>\n";
	if ( $site_columns[0]->[0] ) {
		print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{delete_site_column_message}</h5><p>\n";
		print "<table border=\"0\" cellpadding=\"7\">\n";
		print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
		print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"site_column_id\" size=\"1\">\n";
		$j=0;
		foreach (@site_columns) {
			my $site_column_id=$site_columns[$j]->[0];
			my $site_column_name=$site_columns[$j]->[1];
			print "<option value=\"$site_column_id\">$site_column_name</option>";
			$j++;
		}
		print "</select></td></tr>\n";
		print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"delete_site_column\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{borrar_message}\" name=\"B1\"></td><td></td></tr>\n";
		print "</table>\n";
		print "</form>\n";
    } else {
        print "<h5>$$lang_vars{delete_site_column_message}</h5><p>\n";
        print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
	}

}



### CUSTOM LINE COLUMNS

my $ll_enabled_db=$global_config[0]->[7] || "";


if ( $ll_enabled_db eq "yes" ) {

### INSERT LINE COLUMN


	@line_columns=$gip->get_line_columns("$client_id");

	print "</td><td align='center' valign=\"top\" $align1 width=\"25%\" style='border-right: 1px solid #cdd0d4;'>\n";
	print "<h3>$$lang_vars{line_columns_message}</h3><p>\n";

	print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	print "<h5>$$lang_vars{insert_column_message}</h5><p>\n";
	print "<table border=\"0\" cellpadding=\"7\">\n";
    print "<tr><td align=\"right\">$$lang_vars{tipo_message}</td><td>";

print <<EOF;
<select class='custom-select custom-select-sm m-1' style='width: 12em' size="1" name="select_type_line" id="select_type_line" onchange="showItemField(this.value,'select_items_lines');">
<option selected>$$lang_vars{text_message}</option>
<option>$$lang_vars{select_message}</option>
</select>
</td><td align="right"></td></tr>
EOF


	print "<tr><td align=\"right\">$$lang_vars{title_message}</td><td><input type=\"text\" class='form-control form-control-sm m-1' style='width: 12em' size=\"15\" name=\"custom_line_column\" value=\"\" maxlength=\"15\"></td></tr>\n";

	print "<tr><td align=\"right\"><span id=\"Hide1_line\"></span></td><td><span id=\"Hide2_line\"></span></td><td align=\"right\"><span id=\"Hide3_line\"></span></td></tr>\n";

	print "<tr><td align=\"left\" colspan=\"2\">$$lang_vars{mandatory_message}  <input type=\"checkbox\" class='m-2' name=\"mandatory_line\" value=\"yes\"></td></tr>\n";

	print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"insert_line_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{crear_message}\" name=\"B1\"></td><td></td></tr>\n";
	print "</table>\n";
	print "</form>\n";




# MOD LINE COLUMN

print "<br><p>\n";
print "<h5>$$lang_vars{edit_column_message}</h5><p>\n";

if ( $cc_line_values[0]->[0] ) {
    print "<form  method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
	$gip->print_mod_column_form("$client_id", "$vars_file", \@cc_line_values, "line");
	$gip->create_custom_column_asso_js(\@cc_line_values, "line");
} else {
    print "<i>$$lang_vars{no_cc_message}</i><br>\n";
}


# MOD LINE COLUMN SELECT OPTIONS

print "<br><p>\n";
#if ( $cc_line_values[0]->[0] ) {
    %custom_line_columns_select = $gip->get_custom_columns_select_hash("$client_id","line");
    my $select_values_string;
    my %select_values_strings;
    my $select_values_string_ref;
#    if ( ! %custom_line_columns_select ) {
#        print "<b>$$lang_vars{edit_select_items_message}</b><p>\n";
#        print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
#    } else {
        print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{edit_select_items_message}</h5><p>\n";
        print "<table border=\"0\" cellpadding=\"7\">\n";
#        print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
        print "<tr><td>$$lang_vars{title_message}</td><td>";
        print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"cc_name_line\" size=\"1\" id=\"cc_name_line\" onchange=\"showNameChangeFieldLine(this.value);\">\n";
        print "<option></option>\n";

        # add type and service
        print "<option value=\"$$lang_vars{tipo_message}\">$$lang_vars{tipo_message}</option>";
        $select_values_strings{$$lang_vars{tipo_message}} = $select_values_string_ref = $custom_line_columns_select{9998}[2] if exists $custom_line_columns_select{9998};
        print "<option value=\"$$lang_vars{service_message}\">$$lang_vars{service_message}</option>";
        $select_values_strings{$$lang_vars{service_message}} = $select_values_string_ref = $custom_line_columns_select{9999}[2] if exists $custom_line_columns_select{9999};
        $j=0;
        foreach (@cc_line_values) {
            my $cc_name = $cc_line_values[$j]->[0] || "";
            my $cc_id = $cc_line_values[$j]->[1];
            if ( ! $cc_name ) {
                $j++;
                next;
            }
            $select_values_string_ref = $custom_line_columns_select{$cc_id}[2] if exists $custom_line_columns_select{$cc_id};
            if ( ! $select_values_string_ref ) {
                # ignore non select columns
                $j++;
                next;
            }

            $select_values_strings{$cc_name} = $select_values_string_ref;

            print "<option value=\"$cc_name\">$cc_name</option>";
            $j++;
        }

        print "</select></td></tr>\n";
        print "<tr><td><span id=\"Hide1_mod_line\"></span></td><td><span id=\"Hide2_mod_line\"></span></td></tr>\n";
        print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"mod_line_cc\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{update_message}\" name=\"B1\"></td><td></td></tr>\n";
        print "</table>\n";
        print "</form>\n";

        # create js object: name => select-options
        my $js_object_select_values = 'var cc_values_select_line = {';
        foreach my $key ( keys %select_values_strings ) {
            my $select_values_string_ref = $select_values_strings{$key};
            my $select_string = join(",", @$select_values_string_ref);
            $js_object_select_values .= "$key: \"$select_string\",";
        }
        $js_object_select_values =~ s/,$//;
        $js_object_select_values .= '};';


print <<EOF;

<script type="text/javascript">
<!--

$js_object_select_values

function showNameChangeFieldLine(name){
  if ( cc_values_select_line[name] ) {
    document.getElementById('Hide1_mod_line').innerHTML = "$$lang_vars{select_items_message}";
    document.getElementById('Hide2_mod_line').innerHTML = "<input type=\\\"text\\\" class='form-control form-control-sm m-1' style='width: 12em' size=\\\"15\\\" name=\\\"mod_select_line_values\\\" id=\\\"mod_select_line_values\\\" value=\\\"\\\" maxlength=\\\"500\\\">";
    document.getElementById('mod_select_line_values').value = cc_values_select_line[name];
  } else {
    document.getElementById('Hide1_mod_line').innerHTML = "";
    document.getElementById('Hide2_mod_line').innerHTML = "";
  }
}
-->
</script>
EOF
#    }
#} else {
#    print "<b>$$lang_vars{edit_select_items_message}</b><p>\n";
#    print "<i>$$lang_vars{no_select_columns_defined_message}</i><br>\n";
#}


### DELETE LINE COLUMN

    print "<br><p>\n";
	if ( $line_columns[0]->[0] ) {
		print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_modcolumns.cgi\">\n";
        print "<h5>$$lang_vars{delete_line_column_message}</h5><p>\n";
		print "<table border=\"0\" cellpadding=\"7\">\n";
		print "<tr><td colspan=\"2\">$$lang_vars{title_message} \n";
		print "<select class='custom-select custom-select-sm m-1' style='width: 12em' name=\"line_column_id\" size=\"1\">\n";
		$j=0;
		foreach (@line_columns) {
			my $line_column_id=$line_columns[$j]->[0];
			my $line_column_name=$line_columns[$j]->[1];
			print "<option value=\"$line_column_id\">$line_column_name</option>";
			$j++;
		}
		print "</select></td></tr>\n";
		print "<tr><td><input name=\"manage_type\" type=\"hidden\" value=\"delete_line_column\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input type=\"submit\" class=\"btn\" value=\"$$lang_vars{borrar_message}\" name=\"B1\"></td><td></td></tr>\n";
		print "</table>\n";
		print "</form>\n";
    } else {
        print "<h5>$$lang_vars{delete_line_column_message}</h5><p>\n";
        print "<i>$$lang_vars{no_cc_message}</i><br>\n";
	}
}


print "</td></tr></table>\n";
print "<br><p>\n";

$gip->print_end("$client_id","$vars_file","", "$daten");


sub mod_select_item_register {
    my ($object, $cc_select_old, $cc_values_work) = @_;

    my $select_values_string_ref;

	my %custom_columns_select_old = $gip->get_custom_columns_select_hash("$client_id","$object");
    my ($cc_name, $mod_select_values);
    my @cc_values_work = @$cc_values_work;
    my %cc_select_old = %$cc_select_old;
    if ( $object eq "site" ) {
        $cc_name = $daten{'cc_name_site'};
        $mod_select_values = $daten{'mod_select_site_values'};
    } elsif ( $object eq "line" ) {
        $cc_name = $daten{'cc_name_line'};
		$mod_select_values = $daten{'mod_select_line_values'};
    } elsif ( $object eq "network" ) {
        $cc_name = $daten{'cc_name'};
        $mod_select_values = $daten{'mod_select_values'};
    } elsif ( $object eq "host" ) {
		$cc_name = $daten{'cc_name_host'};
		$mod_select_values = $daten{'mod_select_host_values'};
    } else {
        return;
    }
    $mod_select_values = $gip->remove_whitespace_all("$mod_select_values");
	$mod_select_values =~ s/^,\s*//;
	$mod_select_values =~ s/\s*,$//;

	my @mod_select_values = split(",", $mod_select_values);
	my $j = 0;

	foreach (@cc_values_work) {
		my $cc_name_s = $cc_values_work[$j]->[0];
		if ( $cc_name ne $cc_name_s ) {
			$j++;
			next;
		}
		my $cc_id = $cc_values_work[$j]->[1];
		$select_values_string_ref = $cc_select_old{$cc_id}[2] if exists $cc_select_old{$cc_id};
        last;
    }
    
    if ( $object eq "line" && ! $select_values_string_ref ) {
        # entry is type or service
        if ( $cc_name eq "$$lang_vars{tipo_message}" ) {
            $select_values_string_ref = $cc_select_old{9998}[2]
        } elsif (  $cc_name eq "$$lang_vars{service_message}" ) {
            $select_values_string_ref = $cc_select_old{9999}[2]
        }
    }

	my @mod_select_values_old = @$select_values_string_ref;

	my %mod_select_values;
	map { $mod_select_values{$_} = 1 } @mod_select_values;
	my %mod_select_values_old;
	map { $mod_select_values_old{$_} = 1 } @mod_select_values_old;

	my $old_only = $gip->compare_array(\@mod_select_values_old,\@mod_select_values);
    my @old_only = @$old_only;
	if ( scalar(@mod_select_values) == scalar(@mod_select_values_old) ) {
		# number of items has not changed
		if ( @old_only > 1 ) {
			$gip->print_error("$client_id","$$lang_vars{solo_un_item_message}");
		}

		# update existing entries
		my $k = 0;
		foreach ( @$select_values_string_ref ) {
			my $new_val = $mod_select_values[$k];
			my $old_val = $_;
			if ( $old_val ne $new_val && ! exists ($cc_select_old{$new_val}) ) {
				$gip->update_column_select_entries("$client_id", "$vars_file", "$cc_name", "$new_val", "$old_val","$object");
			}
			$k++;
		}
	} else {
		# number of items has changed
		my $item_changed;
		my $new_count = scalar(@mod_select_values) - scalar(@mod_select_values_old);
		if ( $new_count > 0 ) {
			# error if more then one item added
			if ( $new_count > 1 ) {
				$gip->print_error("$client_id","$$lang_vars{solo_un_item_add_message}");
			}

			# item added
			foreach ( @mod_select_values_old ) {
				# check if other items has also changed
				if ( ! exists($mod_select_values{$_}) ) {
					$gip->print_error("$client_id","$$lang_vars{solo_un_item_message}");
				}
			}
		} elsif ( $new_count < 0 ) {
			# error if more then one item deleted
			if ( $new_count < -1 ) {
				$gip->print_error("$client_id","$$lang_vars{solo_un_item_delete_message}");
			}
			# item deleted
			foreach ( @mod_select_values_old ) {
				if ( ! exists($mod_select_values{$_}) ) {
					$gip->delete_column_select_entries("$client_id","$cc_name","$_","$object", "$vars_file");
				}
			}
		}
	}

	$gip->update_custom_column_select("$client_id", "$cc_name", "$mod_select_values", "$object", "$vars_file");
}
