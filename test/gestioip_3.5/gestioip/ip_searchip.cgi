#!/usr/bin/perl -T -w

# Copyright (C) 2014 Marc Uebel

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
use lib './modules';
use GestioIP;
use Net::IP;
use Net::IP qw(:PROC);


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");


my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();


my $locs_ro_perm = "";
my $locs_rw_perm = "";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}


$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my $match = $daten{'match'} || "";
$gip->{match} = $match;
my $password_management_enabled = $global_config[0]->[18] || "no";
$gip->{password_management_enabled} = 1 if $password_management_enabled eq "yes";

my $search_hostname = "";
if ( ! $daten{'hostname'} && $daten{'match'} ) {
   $search_hostname = $daten{'match'} || "";
   $daten{'hostname'} = $daten{'match'};
#   undef $daten{'match'};
} elsif ( $daten{'hostname'} && ! $daten{'match'} ) {
   $search_hostname = $daten{'hostname'} || "";
}

my $gip_query=$daten{'gip_query'} || "";

my $back_button="<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>";

my $cc_search_only="0";
foreach my $key (keys %daten) {
	if ( $key=~ /cc_id_/ ) {
		$cc_search_only="1";
		last;
	}
}

if ( ! $daten{'hostname'} && ! $daten{'host_descr'} && ! $daten{'comentario'} && ! $daten{'ip'} && ! $daten{'loc'} && ! $daten{'cat'} && ! $daten{'int_admin'} && ! $daten{'update_type'} && ! $daten{'tag'} && $cc_search_only != "1" ) {
        $gip->print_init("search ip","$$lang_vars{busqueda_host_message}","$$lang_vars{no_search_string_message} (1) $back_button","$vars_file","$client_id");
        $gip->print_end("$client_id", "", "", "");
        exit 1;
}

my $client_independent=$daten{client_independent} || "n";
my $search_index = $daten{'search_index'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{resultado_busqueda_message}","$vars_file");

my $hidden_form_fields = "";
my %advanced_search_hash=();

my $cc_value_exists=0;
my @cc_values=$gip->get_custom_host_columns("$client_id");
for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
	$hidden_form_fields .= "<input type=\"hidden\" name=\"cc_id_$cc_values[$k]->[1]\" value=\"$daten{\"cc_id_$cc_values[$k]->[1]\"}\">" if $daten{"cc_id_$cc_values[$k]->[1]"};
	# mass update
	if ( exists($daten{"cc_id_$cc_values[$k]->[1]"}) ) {
		if (  $daten{"cc_id_$cc_values[$k]->[1]"} ne "" ) {
			my $key="cc_id_$cc_values[$k]->[1]";
			$advanced_search_hash{"$key"}=$daten{"$key"} if exists($daten{"$key"});
			$cc_value_exists=1;
		}
	}
}

if ( ! $daten{'hostname'} && ! $daten{'host_id_db'} && ! $daten{'host_descr'} && ! $daten{'comentario'} && ! $daten{'ip'} && ! $daten{'loc'} && ! $daten{'cat'} && ! $daten{'int_admin'} && ! $daten{'update_type'} && ! $daten{'client_independent'} && ! $daten{'tag'} && ! $cc_value_exists ) {
	$gip->print_error("$client_id","$$lang_vars{no_search_string_message} (2)");
}


my ($host_hash_ref,$host_sort_helper_array_ref)=$gip->search_db_hash("$client_id","$vars_file",\%daten);

my $anz_values_hosts += keys %$host_hash_ref;
my $knownhosts="all";
my $start_entry_hosts="0";
my $entries_per_page_hosts="512";
my $pages_links="NO_LINKS";
my $host_order_by = "SEARCH";
my $red_num = "";
my $red_loc = "";
my $redbroad_int = "1";
my $first_ip_int = "";
my $last_ip_int = "";


if ( $anz_values_hosts < "1" ) {
	print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
	$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
} else {
	if ( $daten{'hostname'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"hostname\" value=\"$daten{'hostname'}\">";
		$advanced_search_hash{"hostname"}=$daten{'hostname'};
	}
	if ( $daten{'host_descr'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"host_descr\" value=\"$daten{'host_descr'}\">";
		$advanced_search_hash{"host_descr"}=$daten{'host_descr'};
	}
	if ( $daten{'comentario'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"comentario\" value=\"$daten{'comentario'}\">";
		$advanced_search_hash{"comentario"}=$daten{'comentario'};
	}
	if ( $daten{'ip'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"ip\" value=\"$daten{'ip'}\">";
		$advanced_search_hash{"ip"}=$daten{'ip'};
	}
	if ( $daten{'loc'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"loc\" value=\"$daten{'loc'}\">";
		$advanced_search_hash{"loc"}=$daten{'loc'};
	}
	if ( $daten{'cat'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"cat\" value=\"$daten{'cat'}\">";
		$advanced_search_hash{"cat"}=$daten{'cat'};
	}
	if ( $daten{'int_admin'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"int_admin\" value=\"$daten{'int_admin'}\">";
		$advanced_search_hash{"int_admin"}=$daten{'int_admin'};
	}
	if ( $daten{'search_index'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"search_index\" value=\"$daten{'search_index'}\">";
#		$advanced_search_hash{"host_descr"}=$daten{'host_descr'};
	}
	if ( $daten{'hostname_exact'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"hostname_exact\" value=\"$daten{'hostname_exact'}\">";
		$advanced_search_hash{"hostname_exact"}=$daten{'hostname_exact'};
	}
	if ( $daten{'client_independent'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"client_independent\" value=\"$daten{'client_independent'}\">";
		$advanced_search_hash{"client_independent"}=$daten{'client_independent'};
	}
	if ( $daten{'host_id_db'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"host_id_db\" value=\"$daten{'host_id_db'}\">";
		$advanced_search_hash{"host_id_db"}=$daten{'host_id_db'};
	}
	if ( $daten{'match'} ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"match\" value=\"$search_hostname\">";
		$advanced_search_hash{"host_id_db"}=$daten{'host_id_db'};
	}

#	my @cc_values=$gip->get_custom_host_columns("$client_id");
#	for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
#		# mass update
#		if ( exists($daten{"cc_id_$cc_values[$k]->[1]"}) ) {
#			$hidden_form_fields .= "<input type=\"hidden\" name=\"cc_id_$cc_values[$k]->[1]\" value=\"$daten{\"cc_id_$cc_values[$k]->[1]\"}\">" if $daten{"cc_id_$cc_values[$k]->[1]"};
#			if (  $daten{"cc_id_$cc_values[$k]->[1]"} ne "" ) {
#				my $key="cc_id_$cc_values[$k]->[1]";
#				$advanced_search_hash{"$key"}=$daten{"$key"} if exists($daten{"$key"});
#			}
#		}
#	}

	print "<form name=\"export_redlist_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_export.cgi\">\n";
	print "<input name=\"export_type\" type=\"hidden\" value=\"host_search\"><input type=\"hidden\" name=\"export_radio\" value=\"host_search\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\">${hidden_form_fields}<input type=\"submit\" value=\"$$lang_vars{export_search_result_message}\" name=\"B2\" class=\"input_link_w_right\"></form><br>\n";
	print "<p>\n";
}


if ( $gip_query ) {
	my ($query_ip,$query_hostname,$query_comment,$query_description,$query_loc,$query_cat,$query_ai,$host_id,$cc_value)="";
	my %custom_columns_values=$gip->get_custom_host_column_values_host_hash("$client_id");
	if ( $anz_values_hosts > 0 ) {
		for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
			print ", $cc_values[$k]->[0]";
		}
		print "\n\n";
	}
	foreach my $keys ( keys %{$host_hash_ref} ) {
		$host_id = $host_hash_ref->{$keys}[12];
		$query_ip = $host_hash_ref->{$keys}[0];
		$query_hostname = $host_hash_ref->{$keys}[1] || "";
		$query_description = $host_hash_ref->{$keys}[2] || "";
		$query_description =~ s// /g;
		$query_description =~ s/\n/ /g;
		$query_description = "---" if $query_description eq "NULL";
		$query_loc = $host_hash_ref->{$keys}[3];
		$query_loc = "---" if $query_loc eq "NULL";
		$query_cat = $host_hash_ref->{$keys}[4];
		$query_cat = "---" if $query_cat eq "NULL";
		$query_ai = $host_hash_ref->{$keys}[5];
		$query_comment = $host_hash_ref->{$keys}[6] || "";
		$query_comment = "---" if $query_comment eq "NULL";
		$query_comment =~ s// /g;
		$query_comment =~ s/\n/ /g;

		for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
			my $cc_id=$cc_values[$k]->[1];
			$cc_value=$custom_columns_values{"${cc_id}_${host_id}"}[0] || "---";
			print ", $cc_value";
		}
		print "\n\n";
	}
} else {

	my $advanced_search_hash=\%advanced_search_hash;

	$gip->PrintIpTab("$client_id",$host_hash_ref,"$first_ip_int","$last_ip_int","res/ip_modip_form.cgi","$knownhosts","$$lang_vars{modificar_message}","$red_num","$red_loc","$vars_file","$anz_values_hosts","$start_entry_hosts","$entries_per_page_hosts","$host_order_by",$host_sort_helper_array_ref,"$client_independent","","$search_index","$search_hostname","",$advanced_search_hash);
}

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

