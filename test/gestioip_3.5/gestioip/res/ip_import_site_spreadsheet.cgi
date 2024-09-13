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
use lib '../modules';
use GestioIP;
use Net::IP qw(:PROC);
use Spreadsheet::ParseExcel;
use Encode qw(encode decode); 
use Cwd;
use locale;
use Math::BigInt;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
if ( $client_id !~ /^\d{1,4}$/ ) {
        $client_id = 1;
        $gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{redes_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

my $append_entries = $daten{'append_entries'} || 0;

$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{importar_sites_sheet_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}

my $perl_version = $];

my $module = "Spreadsheet::ParseExcel";
my $module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{no_spreadsheet_support}") if $module_check != "1";

my @config = $gip->get_config("$client_id");
my $smallest_bm = $config[0]->[0] || "22";


my $import_dir = getcwd;
$import_dir =~ s/res.*/import/;

$gip->print_error("$client_id","$$lang_vars{no_spreadsheet_message}") if $daten{'spreadsheet'} !~ /.+/;
my $spreadsheet = $daten{'spreadsheet'};
my $excel_file_name="../import/$spreadsheet";

if ( ! -e $excel_file_name ) {
	$gip->print_error("$client_id","$$lang_vars{no_spreadsheet_message} \"$spreadsheet\"<p>$$lang_vars{no_host_spreadsheet_explic_message} \"$spreadsheet\"");
}
if ( ! -r $excel_file_name ) {
	$gip->print_error("$client_id","$$lang_vars{spreadsheet_no_readable_message} \"$excel_file_name\"<p>$$lang_vars{check_permissions_message}");
}

$gip->print_error("$client_id","$$lang_vars{hoja_and_first_sheets_message}") if ( $daten{'hoja'} && $daten{'some_sheet_values'} );
$gip->print_error("$client_id","$$lang_vars{hoja_and_first_sheets_message}") if ( $daten{'one_sheet'} && $daten{'sheet_import_type'} ne "one_sheet" );
$gip->print_error("$client_id","$$lang_vars{hoja_and_first_sheets_message}") if ( $daten{'some_sheet_values'} && $daten{'sheet_import_type'} ne "some_sheet" );
$gip->print_error("$client_id","$$lang_vars{hoja_and_first_sheets_message}") if ( ( $daten{'hoja'} || $daten{'some_sheet_values'} ) && $daten{'sheet_import_type'} eq "all_sheet" );

my $allowd = $gip->get_allowed_characters();
my @cc_values=$gip->get_site_columns("$client_id");
my %custom_colums_select = $gip->get_custom_columns_select_hash("$client_id","site");
my $sites = $gip->get_loc_hash("$client_id");
my %values_sites_cc=$gip->get_site_column_values_hash("$client_id"); # $values{"${column_id}_${site_id}"}="$entry";



print <<EOF;

<SCRIPT LANGUAGE="Javascript" TYPE="text/javascript">
<!--

function scrollToTop() {
  var x = '0';
  var y = '0';
  window.scrollTo(x, y);
  eraseCookie('net_scrollx')
  eraseCookie('net_scrolly')
}

// -->
</SCRIPT>

EOF


my ($import_sheet_numbers,$some_sheet_values);
my $m = "0";
if ( $daten{'sheet_import_type'} eq "some_sheet" ) {
	$daten{'some_sheet_values'} =~ s/\s*//g;
	$gip->print_error("$client_id","$$lang_vars{check_sheet_number_format} $daten{'some_sheet_values'}") if ( $daten{'some_sheet_values'} !~ /[0-9\,\-]/ );
	$some_sheet_values = $daten{'some_sheet_values'};
	while ( 1 == 1 ) {
		my $hay_match = 1;
		$some_sheet_values =~ s/(\d+-\d+)//;
		if ( $1 ) {
			$1 =~ /(\d+)-(\d+)/;
			$gip->print_error("$client_id","$$lang_vars{'99_sheets_max_message'}") if $1 >= "100";
			$gip->print_error("$client_id","$$lang_vars{'99_sheets_max_message'}") if $2 >= "100";
			for (my $l = $1; $l <= $2; $l++) {
				if ( $import_sheet_numbers ) {
					$import_sheet_numbers = $import_sheet_numbers . "|" . $l;
				} else {
					$import_sheet_numbers = $l;
				}
			}
			$m++;
			$hay_match = 0;
			next;
		}
		$some_sheet_values =~ s/^,*(\d+),*//;
		if ( $1 ) {
			$gip->print_error("$client_id","$$lang_vars{'99_sheets_max_message'}") if $1 >= 100;
			if ( $import_sheet_numbers ) {
				$import_sheet_numbers = $import_sheet_numbers . "|" . $1;
			} else {
				$import_sheet_numbers = $1;
			}
			$hay_match = 0;
			$m++;
			next;
		}
		$m++;
		last if $m >= 100;
		last if $hay_match == 1;
	}
}

$gip->print_error("$client_id","$$lang_vars{check_sheet_number_format} $some_sheet_values") if ( $some_sheet_values );
$gip->print_error("$client_id","$$lang_vars{check_sheet_number_format}") if ( $daten{'some_sheet_values'} && ! $import_sheet_numbers );


if ( ! $daten{'site'} ) {
	$gip->print_error("$client_id","$$lang_vars{elige_columna_site_message}");
}
	
if ( $daten{site} && $daten{site} !~ /^\w{1}$/ ) { $gip->print_error("$client_id","$$lang_vars{formato_malo_message}") };

my $key;
my $found_value="NULL";
my $found_key="NULL";
foreach $key (sort {$daten{$a} cmp $daten{$b} } keys %daten) {
	next if ! $daten{$key}; 
	if ( $key =~ /^(append_entries|client_id|B1|IP_format|ip_version|sheet_import_type|spreadsheet)$/ ) {
		next;
	}
	if ( $found_value eq $daten{$key} ) {
		$gip->print_error("$client_id","$$lang_vars{column_duplicada_message}:<p>$found_key -> <b>$found_value</b><br>$key -> <b>$daten{$key}</b><p>$$lang_vars{comprueba_formulario_message}");
	}
	$found_value = $daten{$key};
	$found_key = $key;
}

my $excel_sheet_name=$daten{'hoja'} || "_NO__SHEET__GIVEN_";

my ($row_new, $sync,$loc_id,$cat_id,$loc_audit,$cat_audit,$last_k,$host_red,$host_red_bm,$redob_redes,$ipob_redes,$last_ip_int,$first_ip_int,$redbo_redes,$mydatetime,$red_num,$k,$to_ignore);

my $excel = Spreadsheet::ParseExcel::Workbook->Parse($excel_file_name);
my $sheet_found=1;
my $obj_found= 0;
my $firstfound = "0";
my $j = "1";

my $ip_version;
print "<span class=\"sinc_text\"><p>";
foreach my $sheet (@{$excel->{Worksheet}}) {
	if (( $sheet->{Name} eq "$excel_sheet_name" && $daten{'hoja'} && $daten{'sheet_import_type'} eq "one_sheet" ) || ( $daten{'sheet_import_type'} eq "all_sheet" && ! $daten{'hoja'} && ! $daten{'some_sheet_values'} ) || ( $daten{'sheet_import_type'} eq "some_sheet" && $j =~ /^($import_sheet_numbers)$/ )) {
		$sheet_found=0;
		$firstfound = "0";

		if ( ! defined($sheet->{MaxRow}) || ! defined($sheet->{MinRow}) ) {
			if ( $vars_file =~ /vars_he$/ ) {
				print "<p><span style=\"float: $ori\">$$lang_vars{empty_sheet_message} - <b><i>$sheet->{Name} :$$lang_vars{sheet_message}</i></b></span><br><p>\n";
			} else {
				print "<p><b><i>$$lang_vars{sheet_message}: $sheet->{Name}</i></b>\n";
				print "  - $$lang_vars{empty_sheet_message}<p>\n";
			}
			$j++;
			next;
		}

		if ( $vars_file =~ /vars_he$/ ) {
			print "<p><span style=\"float: $ori\"><b><i>$sheet->{Name} :$$lang_vars{sheet_message}</i></b></span><br>\n";
		} else {
			print "<p><b><i>$$lang_vars{sheet_message}: $sheet->{Name}</i></b>\n";
		}

		print "<p>\n";


		$sheet->{MaxRow} ||= $sheet->{MinRow};

		foreach my $row ($sheet->{MinRow} .. $sheet->{MaxRow}) {
			$to_ignore = "0";
			$sheet->{MaxCol} ||= $sheet->{MinCol};

			my $cell1 = $sheet->{Cells}[$row][0];
			my $cell2 = $sheet->{Cells}[$row][1];
			my $cell3 = $sheet->{Cells}[$row][2];
			my $cell4 = $sheet->{Cells}[$row][3];
			my $cell5 = $sheet->{Cells}[$row][4];
			my $cell6 = $sheet->{Cells}[$row][5];
			my $cell7 = $sheet->{Cells}[$row][6];
			my $cell8 = $sheet->{Cells}[$row][7];
			my $cell9 = $sheet->{Cells}[$row][8];
			my $cell10 = $sheet->{Cells}[$row][9];
			my $cell11 = $sheet->{Cells}[$row][10];
			my $cell12 =  $sheet->{Cells}[$row][11];
			my $cell13 =  $sheet->{Cells}[$row][12];
			my $cell14 =  $sheet->{Cells}[$row][13];
			my $cell15 =  $sheet->{Cells}[$row][14];
			my $cell16 =  $sheet->{Cells}[$row][15];
			my $cell17 =  $sheet->{Cells}[$row][16];
			my $cell18 =  $sheet->{Cells}[$row][17];
			my $cell19 =  $sheet->{Cells}[$row][18];
			my $cell20 =  $sheet->{Cells}[$row][19];
			my $cell21 =  $sheet->{Cells}[$row][20];
			my $cell22 =  $sheet->{Cells}[$row][21];
			my $cell23 =  $sheet->{Cells}[$row][22];
			my $cell24 =  $sheet->{Cells}[$row][23];
			my $cell25 =  $sheet->{Cells}[$row][24];
			my $cell26 =  $sheet->{Cells}[$row][25];

			my %entries = %daten;
			my $i = "1";
			while ( my ($key,$value) = each ( %entries ) ) {
				if ( $value eq "A" ) {
					$entries{"$key"} = $cell1->{Val} || "";
					if ( $cell1->{Val} && $cell1->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if (Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell1->{Val} ne "0" ) {
						$entries{"$key"} = $cell1->value() if $cell1->value();
					}
				} elsif ( $value eq "B" ) {
					$entries{"$key"} = $cell2->{Val} || "";
					if ( $cell2->{Val} && $cell2->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell2->{Val} ne "0" ) {
						$entries{"$key"} = $cell2->value() if $cell2->value();
					}
				} elsif ( $value eq "C" ) {
					$entries{"$key"} = $cell3->{Val} || "";
					if ( $cell3->{Val} && $cell3->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell3->{Val} ne "0" ) {
						$entries{"$key"} = $cell3->value() if $cell3->value();
					}
				} elsif ( $value eq "D" ) {
					$entries{"$key"} = $cell4->{Val} || "";
					if ( $cell4->{Val} && $cell4->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell4->{Val} ne "0" ) {
						$entries{"$key"} = $cell4->value() if $cell4->value();
					}
				} elsif ( $value eq "E" ) {
					$entries{"$key"} = $cell5->{Val} || "";
					if ( $cell5->{Val} && $cell5->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell5->{Val} ne "0" ) {
						$entries{"$key"} = $cell5->value() if $cell5->value();
					}
				} elsif ( $value eq "F" ) {
					$entries{"$key"} = $cell6->{Val} || "";
					if ( $cell6->{Val} && $cell6->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell6->{Val} ne "0" ) {
						$entries{"$key"} = $cell6->value() if $cell6->value();
					}
				} elsif ( $value eq "G" ) {
					$entries{"$key"} = $cell7->{Val} || "";
					if ( $cell7->{Val} && $cell7->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell7->{Val} ne "0" ) {
						$entries{"$key"} = $cell7->value() if $cell7->value();
					}
				} elsif ( $value eq "H" ) {
					$entries{"$key"} = $cell8->{Val} || "";
					if ( $cell8->{Val} && $cell8->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell8->{Val} ne "0" ) {
						$entries{"$key"} = $cell8->value() if $cell8->value();
					}
				} elsif ( $value eq "I" ) {
					$entries{"$key"} = $cell9->{Val} || "";
					if ( $cell9->{Val} && $cell9->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell9->{Val} ne "0" ) {
						$entries{"$key"} = $cell9->value() if $cell9->value();
					}
				} elsif ( $value eq "J" ) {
					$entries{"$key"} = $cell10->{Val} || "";
					if ( $cell10->{Val} && $cell10->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell10->{Val} ne "0" ) {
						$entries{"$key"} = $cell10->value() if $cell10->value();
					}
				} elsif ( $value eq "K" ) {
					$entries{"$key"} = $cell11->{Val} || "";
					if ( $cell11->{Val} && $cell11->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell11->{Val} ne "0" ) {
						$entries{"$key"} = $cell11->value() if $cell11->value();
					}
				} elsif ( $value eq "L" ) {
					$entries{"$key"} = $cell12->{Val} || "";
					if ( $cell12->{Val} && $cell12->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell12->{Val} ne "0" ) {
						$entries{"$key"} = $cell12->value() if $cell12->value();
					}
				} elsif ( $value eq "M" ) {
					$entries{"$key"} = $cell13->{Val} || "";
					if ( $cell13->{Val} && $cell13->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell13->{Val} ne "0" ) {
						$entries{"$key"} = $cell13->value() if $cell13->value();
					}
				} elsif ( $value eq "N" ) {
					$entries{"$key"} = $cell14->{Val} || "";
					if ( $cell14->{Val} && $cell14->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell14->{Val} ne "0" ) {
						$entries{"$key"} = $cell14->value() if $cell14->value();
					}
				} elsif ( $value eq "O" ) {
					$entries{"$key"} = $cell15->{Val} || "";
					if ( $cell15->{Val} && $cell15->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell15->{Val} ne "0" ) {
						$entries{"$key"} = $cell15->value() if $cell15->value();
					}
				} elsif ( $value eq "P" ) {
					$entries{"$key"} = $cell16->{Val} || "";
					if ( $cell16->{Val} && $cell16->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell16->{Val} ne "0" ) {
						$entries{"$key"} = $cell16->value() if $cell16->value();
					}
				} elsif ( $value eq "Q" ) {
					$entries{"$key"} = $cell17->{Val} || "";
					if ( $cell17->{Val} && $cell17->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell17->{Val} ne "0" ) {
						$entries{"$key"} = $cell17->value() if $cell17->value();
					}
				} elsif ( $value eq "R" ) {
					$entries{"$key"} = $cell18->{Val} || "";
					if ( $cell18->{Val} && $cell18->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell18->{Val} ne "0" ) {
						$entries{"$key"} = $cell18->value() if $cell18->value();
					}
				} elsif ( $value eq "S" ) {
					$entries{"$key"} = $cell19->{Val} || "";
					if ( $cell19->{Val} && $cell19->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell19->{Val} ne "0" ) {
						$entries{"$key"} = $cell19->value() if $cell19->value();
					}
				} elsif ( $value eq "T" ) {
					$entries{"$key"} = $cell20->{Val} || "";
					if ( $cell20->{Val} && $cell20->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell20->{Val} ne "0" ) {
						$entries{"$key"} = $cell20->value() if $cell20->value();
					}
				} elsif ( $value eq "U" ) {
					$entries{"$key"} = $cell21->{Val} || "";
					if ( $cell21->{Val} && $cell21->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell21->{Val} ne "0" ) {
						$entries{"$key"} = $cell21->value() if $cell21->value();
					}
				} elsif ( $value eq "V" ) {
					$entries{"$key"} = $cell22->{Val} || "";
					if ( $cell22->{Val} && $cell22->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell22->{Val} ne "0" ) {
						$entries{"$key"} = $cell22->value() if $cell22->value();
					}
				} elsif ( $value eq "W" ) {
					$entries{"$key"} = $cell23->{Val} || "";
					if ( $cell23->{Val} && $cell23->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell23->{Val} ne "0" ) {
						$entries{"$key"} = $cell23->value() if $cell23->value();
					}
				} elsif ( $value eq "X" ) {
					$entries{"$key"} = $cell24->{Val} || "";
					if ( $cell24->{Val} && $cell24->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell24->{Val} ne "0" ) {
						$entries{"$key"} = $cell24->value() if $cell24->value();
					}
				} elsif ( $value eq "Y" ) {
					$entries{"$key"} = $cell25->{Val} || "";
					if ( $cell25->{Val} && $cell25->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell25->{Val} ne "0" ) {
						$entries{"$key"} = $cell25->value() if $cell25->value();
					}
				} elsif ( $value eq "Z" ) {
					$entries{"$key"} = $cell26->{Val} || "";
					if ( $cell26->{Val} && $cell26->{Val} eq "0" ) {
						$entries{"$key"} = "0";
					}
					if ( Spreadsheet::ParseExcel::Cell->can('value') && $entries{"$key"} && $cell26->{Val} ne "0" ) {
						$entries{"$key"} = $cell26->value() if $cell26->value();
					}
				}
			}

			# check for unallowed characters
			foreach my $key( keys %entries ) {
				if ( $key eq "URL" ) {
					$entries{$key} =~ s/;/,/g;
					$entries{$key} =~ s/['<>\\*#%\^\`\$*]/_/g;
				} else {
					$entries{$key} =~ s/['<>\\\/*&#%\^\`=\$*]/_/g;
				}
				
				my $converted=encode("UTF-8",$entries{$key}); 
				$entries{$key} = $converted;

				$converted =~ s/['=?_\.,:\-\@()\w\/\[\]{}|~\+\n\r\f\t\s]//g;
				my $hex = join('', map { sprintf('%X', ord $_) } split('', "$converted"));
				my @hex_ar=split(' ',$converted); 

				foreach (@hex_ar) {
                    if ( $_ !~ /^[${allowd}]+$/i && $hex =~ /.+/) {
                        if ( $vars_file =~ /vars_he$/ ) {
                            print "<span style=\"float: $ori\">$$lang_vars{ignorado_message} $key - $$lang_vars{caracter_no_permitido_encontrado_message} :$key :<b>$entries{ip}/$entries{hostname}</b></span><br>\n";
                        } else {
#   TEST                         print "<b>$entries{ip}/$entries{hostname}</b>: $key: $$lang_vars{caracter_no_permitido_encontrado_message} - $key $$lang_vars{ignorado_message}<br>\n"s
                        }
                        $entries{$key} ="";
                        last;
                    }
				}

			}

			if ( ! $entries{site} ) {
				next;
			}

            $obj_found = 1;

            my $in_site = $entries{site};
            my $site_id=$gip->get_loc_id("$client_id","$in_site") || "";
            my $site_exits = 0;
            if ( $site_id ) {
                $site_exits = 1;
            }

			$mydatetime = time();

            my $update = 0;
			if ( ! $site_id ) {
				my $last_loc_id=$gip->get_last_loc_id("$client_id");
				$last_loc_id++;
				$last_loc_id = "1" if $last_loc_id == "0";
                $site_id = $last_loc_id;
				$gip->loc_add("$client_id","$in_site","$last_loc_id");
			}

            for ( my $k = 0; $k < scalar(@cc_values); $k++ ) {
                my $test = $cc_values[$k]->[0] || "";
				if ( $test ) {
					my $cc_id="$cc_values[$k]->[0]";
					my $cc_name="$cc_values[$k]->[1]";
					my $mandatory="$cc_values[$k]->[2]";
					my $cc_value=$entries{$cc_name} || "";
                    my $cc_entry_db=$values_sites_cc{"${cc_id}_${site_id}"} || "";

                    # if select, check if select entry exists
                    if ( exists $custom_colums_select{$cc_id} ) {
                        my $item = $custom_colums_select{$cc_id}->[2];
                        my @item = @$item;
                        my %ucheck = map { $_ => 1 } @item;
                        if( ! exists($ucheck{$cc_value})) { 
                            # entry is not within the values of the select items
                            next;
                        }
                    }

					if ( $cc_entry_db ) {
                        $gip->update_site_column_entry("$client_id","$cc_id","$site_id","$cc_value" );
                        $update = 1;
					} else {
                        $gip->insert_site_column_entry("$client_id","$cc_id","$site_id","$cc_value" );
					}
				}
            }

			if ( $update == 1 ) {
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$$lang_vars{entrada_actualizada_message} - $entries{hostname} :<b>$entries{ip}</b></span><br>\n";
				} else {
					print "<b>$entries{site}</b>: $$lang_vars{entrada_actualizada_message}<br>\n";
				}
			} else {
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$$lang_vars{added_message} - $entries{hostname} :<b>$entries{ip}</b></span><br>\n";
				} else {
					print "<b>$entries{site}</b>: $$lang_vars{added_message}<br>\n";
				}
			}


			my $audit_type = 156; # loc edited
			$audit_type = 10 if $update == 0; # loc added
			my $audit_class="23";
			my $update_type_audit="1";

			my $event=$entries{site};
			$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
		}
	}
	$j++;
}

print "</span>\n";


if ( $sheet_found == "1" ) {
	$gip->print_error("$client_id","$$lang_vars{no_sheet_message} \"$excel_sheet_name\"<p>$$lang_vars{comprueba_formulario_message}");
}

if ( $obj_found == 0 ) {
	$gip->print_error("$client_id","$$lang_vars{no_hosts_message}");
}

print "<h3 style=\"float: $ori\">$$lang_vars{listo_message}</h3><br><p><br>\n";

## update net usage
#my %seen = (); 
#my $item;
#my @uniq;
#foreach $item(@redes_usage_array) {
#    next if ! $item;
#    push(@uniq, $item) unless $seen{$item}++;
#}   

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
