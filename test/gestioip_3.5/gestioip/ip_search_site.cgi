#!/usr/bin/perl -T -w

# Copyright (C) 2019 Marc Uebel

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


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="read_host_perm";
	$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my $search_loc = $daten{'loc'} || "";
my $gip_query=$daten{'gip_query'} || "";

my $back_button="<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>";


my $client_independent=$daten{client_independent} || "n";
my $search_index = $daten{'search_index'} || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{resultado_busqueda_message}","$vars_file");

my $hidden_form_fields = "";
my %advanced_search_hash=();

my $cc_value_exists=0;
my @cc_values=$gip->get_custom_site_columns("$client_id");

for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
	$hidden_form_fields .= "<input type=\"hidden\" name=\"cc_id_$cc_values[$k]->[1]\" value=\"$daten{\"cc_id_$cc_values[$k]->[1]\"}\">" if $daten{"cc_id_$cc_values[$k]->[1]"};
	# mass update
	if ( exists($daten{"cc_id_$cc_values[$k]->[1]"}) && $daten{"cc_id_$cc_values[$k]->[1]"} ne "" ) {
        $cc_value_exists=1;
	}
}

if ( ! $daten{'loc'} && ! $cc_value_exists ) {
	$gip->print_error("$client_id","$$lang_vars{no_search_string_message}");
}


$gip->PrintSiteTab("$client_id","$vars_file","",\%daten);

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

