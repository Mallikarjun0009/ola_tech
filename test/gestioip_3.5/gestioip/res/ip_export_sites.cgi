#!/usr/bin/perl -w -T

# Copyright (C) 2015 Marc Uebel

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
use Net::IP qw(:PROC);
use Cwd;
use File::Find;
use File::stat;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri = $gip->get_base_uri();

my ($lang_vars,$vars_file,$entries_per_page);
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
if ( $daten{'entries_per_page'} ) {
        $daten{'entries_per_page'} = "500" if $daten{'entries_per_page'} !~ /^\d{1,3}$/;
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("$daten{'entries_per_page'}","$lang");
} else {
        ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
}

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
        $client_id = 1;
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)");
}


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


my $match;
$match=$daten{'match'} || "";
	
$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{export_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $values_sites;
if ( $match ) {
	$values_sites=$gip->get_sites_match("$client_id","$match");
} else {
	$values_sites=$gip->get_loc_hash("$client_id");
}

my @site_columns=$gip->get_site_columns("$client_id"); # id, name
my %values_sites_cc=$gip->get_site_column_values_hash("$client_id"); # $values{"${column_id}_${site_id}"}="$entry";

my @csv_strings;
my @site_column_order_name;
my @site_column_order_id;
my $j=0;

foreach ( @site_columns ) {
	my $column_id=$site_columns[$j]->[0];
	my $column_name=$site_columns[$j]->[1];

	push @site_column_order_name,"$column_name";
	push @site_column_order_id,"$column_id";
	$j++;
}

$csv_strings[0]=$$lang_vars{name_message};
foreach my $site_cc ( @site_column_order_name ) {
	$csv_strings[0].= "," . $site_cc;
}


my $i=1;
foreach my $site ( sort keys %{$values_sites} ) {
	my $id=$values_sites->{$site};

	$csv_strings[$i]=$site;
	foreach my $column_id ( @site_column_order_id ) {
		my $entry=$values_sites_cc{"${column_id}_${id}"} || "";
        $entry = '"' . $entry . '"' if $entry =~ /,/;
#		$entry =~ s/,/;/g;
		$csv_strings[$i].= "," . $entry;
	}
	$i++;

}

my $export_dir = getcwd;
$export_dir =~ s/res.*/export/;

$export_dir =~ /^([\w.\/]+)$/;

# delete old files
my $found_file;
sub findfile {
	$found_file = $File::Find::name if ! -d;
	if ( $found_file ) {
		$found_file =~ /^(.*)$/;
		$found_file = $1;
		my $filetime = stat($found_file)->mtime;
		my $checktime=time();
		$checktime = $checktime - 3600;
		if ( $filetime < $checktime ) {
			unlink($found_file);
		}
	}
}

find( {wanted=>\&findfile,no_chdir=>1},$export_dir);

my $mydatetime=time();
my $csv_file_name="$mydatetime.sites.csv";
my $csv_file="../export/$csv_file_name";

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!"); 

foreach ( @csv_strings ) {
	print EXPORT "$_\n";
}

close EXPORT;

print "<p><b style=\"float: $ori\">$$lang_vars{export_successful_message}</b><br><p>\n";
print "<p><span style=\"float: $ori\"><a href=\"$server_proto://$base_uri/export/$csv_file_name\">$$lang_vars{download_csv_file}</a></span><p>\n";

$gip->print_end("$client_id", "", "", "");
