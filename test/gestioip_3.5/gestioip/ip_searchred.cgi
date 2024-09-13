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
use lib './modules';
use GestioIP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{busqueda_red_message}","$vars_file");
	$client_id=$gip->get_first_client_id();
        $gip->print_error("$client_id","$$lang_vars{client_id_invalid_message}","");
}

my $locs_ro_perm = "";
my $locs_rw_perm = "";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_net_perm";
	($locs_ro_perm, $locs_rw_perm) = $gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

$gip->{locs_ro_perm} = $locs_ro_perm;
$gip->{locs_rw_perm} = $locs_rw_perm;


my $ipv4_only_mode=$global_config[0]->[5] || "yes";
my $ip_version_ele="";
if ( $ipv4_only_mode eq "no" ) {
        $ip_version_ele = $daten{'ip_version_ele'} || "";
        if ( $ip_version_ele ) {
                $ip_version_ele = $gip->set_ip_version_ele("$ip_version_ele");
        } else {
                $ip_version_ele = $gip->get_ip_version_ele();
        }
} else {
        $ip_version_ele = "v4";
}


my $modred=$daten{modred} || "";
my $client_independent=$daten{client_independent} || "n";
my $gip_query=$daten{'gip_query'} || "";


my $cc_search_only="0";
foreach my $key (keys %daten) {
        if ( $key=~ /cc_id_/ ) {
                $cc_search_only="1";
                last;
        }
}

#if ( ! $daten{'red_search'} && ! $daten{'red'} && ! $daten{'descr'} && ! $daten{'loc'} && ! $daten{'vigilada'} && ! $daten{'cat_red'} && ! $daten{'comentario'} && $cc_search_only != "1" ) {
if ( ! $daten{'match'} && ! $daten{'red'} && ! $daten{'descr'} && ! $daten{'loc'} && ! $daten{'vigilada'} && ! $daten{'cat_red'} && ! $daten{'comentario'} && $cc_search_only != "1" ) {
	my $back_button="<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>";
        $gip->print_init("search ip","$$lang_vars{busqueda_red_message}","$$lang_vars{no_search_string_message} $back_button","$vars_file","$client_id");
        $gip->print_end("$client_id", "", "", "");
        exit 1;
}


if ( $daten{'match'} && ! $daten{'red_search'} ) {
    $daten{'red_search'} = $daten{'match'};
	$gip->{red_search} = $daten{'match'};
    delete $daten{'match'};

}

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{resultado_busqueda_message}","$vars_file");


my ( @values_red ) = $gip->search_db_red("$client_id","$vars_file",\%daten);


my @cc_values;
if ( $values_red[0] ) {
	my $hidden_form_fields = "";
	$hidden_form_fields .= "<input type=\"hidden\" name=\"red\" value=\"$daten{'red'}\">" if $daten{'red'};
	$hidden_form_fields .= "<input type=\"hidden\" name=\"descr\" value=\"$daten{'descr'}\">" if $daten{'descr'};
	$hidden_form_fields .= "<input type=\"hidden\" name=\"comentario\" value=\"$daten{'comentario'}\">" if $daten{'comentario'};
	$hidden_form_fields .= "<input type=\"hidden\" name=\"loc\" value=\"$daten{'loc'}\">" if $daten{'loc'};
	$hidden_form_fields .= "<input type=\"hidden\" name=\"cat_red\" value=\"$daten{'cat_red'}\">" if $daten{'cat_red'};
	$hidden_form_fields .= "<input type=\"hidden\" name=\"vigilada\" value=\"$daten{'vigilada'}\">" if $daten{'vigilada'};
    if ( $daten{'match'} ) {
        $hidden_form_fields .= "<input type=\"hidden\" name=\"red_search\" value=\"$daten{'match'}\">";
    } elsif ( $daten{'red_search'} ) {
        $hidden_form_fields .= "<input type=\"hidden\" name=\"red_search\" value=\"$daten{'red_search'}\">";
    }
	$hidden_form_fields .= "<input type=\"hidden\" name=\"client_independent\" value=\"$daten{'client_independent'}\">" if $daten{'client_independent'};

	@cc_values=$gip->get_custom_columns("$client_id");
	for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
		$hidden_form_fields .= "<input type=\"hidden\" name=\"cc_id_$cc_values[$k]->[1]\" value=\"$daten{\"cc_id_$cc_values[$k]->[1]\"}\">" if $daten{"cc_id_$cc_values[$k]->[1]"};
	}

	print "<form name=\"export_redlist_form\" method=\"POST\" action=\"$server_proto://$base_uri/res/ip_export.cgi\">\n";
	print "<input name=\"export_type\" type=\"hidden\" value=\"red_search\"><input type=\"hidden\" name=\"export_radio\" value=\"red_search\"><input type=\"hidden\" name=\"ipv4\" value=\"ipv4\"><input type=\"hidden\" name=\"ipv6\" value=\"ipv6\"><input type=\"hidden\" name=\"client_id\" value=\"$client_id\">${hidden_form_fields}<input type=\"submit\" value=\"$$lang_vars{export_search_result_message}\" name=\"B2\" class=\"input_link_w_right\"></form><br>\n";
	print "<p>\n";
}

my $values_red_num = @values_red || "0";
my $colorcomment;



if ( $gip_query ) {
	my ($query_red,$query_bm,$query_comment,$query_description,$query_loc,$query_cat,$query_sync,$red_num,$cc_value)="";
	my %custom_columns_values=$gip->get_custom_column_values_red("$client_id");
	if ( $values_red[0] ) {
		print "SEARCH_DATA: Network/BM, comment, location, category, description, AI";
		for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
			print ", $cc_values[$k]->[0]";
		}
		print "\n\n";
	}
#	foreach my $keys ( keys %{$host_hash_ref} ) {
	my $j=0;
	foreach (@values_red) {
		$query_red = $values_red[$j]->[0] || "";
		$red_num = $values_red[$j]->[3] || "";
                $query_bm = $values_red[$j]->[1] || "";

		$query_description = $values_red[$j]->[2] || "---";
		$query_description =~ s// /g;
		$query_description =~ s/\n/ /g;
		$query_description = "---" if $query_description eq "NULL";
		$query_loc = $values_red[$j]->[4] || "---";
		$query_loc = "---" if $query_loc eq "NULL";
		$query_cat = $values_red[$j]->[7] || "---";
		$query_cat = "---" if $query_cat eq "NULL";
		$query_sync = $values_red[$j]->[5] || "n";
		$query_comment = $values_red[$j]->[6] || "---";
		$query_comment = "---" if $query_comment eq "NULL";
		$query_comment =~ s// /g;
		$query_comment =~ s/\n/ /g;

		print "SEARCH_DATA: $query_red/$query_bm, $query_comment, $query_loc, $query_cat, $query_description, $query_sync";

		for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
			my $cc_id=$cc_values[$k]->[1];
			$cc_value=$custom_columns_values{"${cc_id}_${red_num}"}[0] || "---";
			print ", $cc_value";
		}
		print "\n\n";
		$j++;
	}
} else {
	if ( ! $values_red[0] ) {
		print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";
		$colorcomment="nocomment";
	} else {
		print "<p>\n";
        print '<div id="content" class="w-100">';
#		if ( $modred eq "y" ) {
			$gip->PrintRedTab("$client_id",\@values_red,"$vars_file","extended","","","","","$client_independent","","$ip_version_ele");
#		} else { 
	#		$gip->PrintRedTab("$client_id",\@values_red,"$vars_file","simple","","","","","$client_independent","","$ip_version_ele");
#		}
        print "</div>";
		$colorcomment="nocomment";
	}
}

$gip->print_end("$client_id","$vars_file","", "$daten");
