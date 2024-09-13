#!/usr/bin/perl -T -w


# Copyright (C) 2011 Marc Uebel

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


use DBI;
use strict;
use lib './modules';
use GestioIP;


my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file,$entries_per_page)=$gip->get_lang("","$lang");
my $server_proto=$gip->get_server_proto();
my $base_uri=$gip->get_base_uri();
my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

my $show_connection_acl = $daten{'show_connection_acl'} || "";
my $show_mass_acls = $daten{'show_mass_acls'} || "";

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
#my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_line_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}

my $message = $$lang_vars{comparison_acl_connection_message};
$message = $$lang_vars{acl_connection_acl_message} if $show_connection_acl;
$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$message","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


#print <<EOF;
#
#<script language="JavaScript" type="text/javascript" charset="utf-8">
#<!--
#function show_searchform(){
#document.getElementById('search_text').innerHTML='<input type=\"text\" size=\"15\" name=\"match\" > <input type="submit" value="" class="button" style=\"cursor:pointer;\"><br><p>';
#document.search_ll.match.focus();
#
#}
#-->
#</script>
#
#<form name="search_dns_zone" method="POST" action="$server_proto://$base_uri/ip_search_acl.cgi" style="display:inline"><input type="hidden" name="client_id" value="$client_id">
#EOF
#
#
#print "<span style=\"float: right;\"><span id=\"search_text\"><img src=\"$server_proto://$base_uri/imagenes/lupe.png\" alt=\"search\" style=\"float: right; cursor:pointer;\" onclick=\"show_searchform('');\"></span></span><br>";
#print "</form>\n";

my $id_string = "";
if ( $show_mass_acls ) {
	my $anz_entries = $daten{'anz_entries'} || "";
	my $k;
	if ( $anz_entries ) {
		for ($k=0;$k<=$anz_entries;$k++) {
			my $mu_id = "mass_update_acl_submit_${k}";
			my $id = $daten{$mu_id} || "";
			$id_string .= ", $id" if $id;
		}
		$id_string =~ s/^, //;
	}
    if ( ! $id_string ) {
        $gip->print_error("$client_id","ACLs IDs not found")
    }
}
my @acl_connections=$gip->get_acl_connections("$client_id","$id_string");
my %protocols = $gip->get_protocol_hash("$client_id");
my %protocols_by_name = $gip->get_protocol_name_hash("$client_id");

my @acl_connections_prepared;
my @acls_prepared;

my %acl_connections_prepared;
my %acl_connections_prepared_range_acl;
my %acls_prepared;

my %acl_connection_ports;
my %acl_connection_ports_range;
my %acl_ports;

my $j = 0;
foreach ( @acl_connections ) {
        my $id = $acl_connections[$j]->[0];
        my $acl_nr = $acl_connections[$j]->[1] || 0;
        my $purpose = $acl_connections[$j]->[2] || "";
        my $status = $acl_connections[$j]->[3];
        my $src_vlan = $acl_connections[$j]->[4];
        my $source = $acl_connections[$j]->[5] || "";
        my $src = $acl_connections[$j]->[6] || "";
        my $application_protocol = $acl_connections[$j]->[7] || "";
        my $proto_id = $acl_connections[$j]->[8] || "";
        my $protocol_found = "IP";
        my $protocol;
        $protocol_found = $protocols{$proto_id} || "" if $proto_id;

        my $src_port = $acl_connections[$j]->[9] || "";
        my $bidirectional = $acl_connections[$j]->[10] || "";
        my $dst_vlan = $acl_connections[$j]->[11] || "";
        my $destination = $acl_connections[$j]->[12] || "";
        my $dst = $acl_connections[$j]->[13] || "";

        if ( $status eq "deleted" ) {
            $j++;
            next;
        }

		if ( $src =~ /\// ) {
			$src =~ /^(.+)\/(.+)$/;
			my $src_ip = $1;
			my $bm = $2;
			my $src_wmask = $gip->get_wmask_from_bm("$bm");
			$src = "$src_ip $src_wmask";
		} elsif ( ! $src ) {
            $src = "any";
		} elsif ( $src =~ /^any$/ ) {
            # do nothing
		} else {
			$src = "host $src";
		}

		if ( $dst =~ /\// ) {
			$dst =~ /^(.+)\/(.+)$/;
			my $dst_ip = $1;
			my $bm = $2;
			my $dst_wmask = $gip->get_wmask_from_bm("$bm");
			$dst = "$dst_ip $dst_wmask";
		} elsif ( ! $dst ) {
            $dst = "any";
		} elsif ( $dst =~ /^any$/ ) {
            # do nothing
		} else {
			$dst = "host $dst";
		}

		my @src_port = split ",", $src_port;

        if ( @src_port ) {
            foreach my $found_port ( @src_port ) {
                $protocol = $protocol_found;
                my $port = "";
                my $dual_port = "";
                my $port_with_name = "";
                my $port_not_found = "";
                my $is_range = "";

                $found_port = $gip->remove_whitespace_se("$found_port");

                if ( $found_port =~ /range/i ) {
                    $found_port =~ s/R/r/;
                    $found_port =~ s/ -/-/;
                    $found_port =~ s/- /-/;
                    $found_port =~ s/-/ /;
                    $port = $found_port;
                    push @{$acl_connection_ports{$port}},"$acl_nr";

                    my $port_r;
                    $found_port =~ /^range (.+) (.+)$/;
                    my $r1 = $1;
                    my $r2 = $2;
                    if ( $r1 =~ /^\d+$/ ) {
                        my $r1_port_name = $gip->get_port_name("$client_id","$r1");
                        my $r2_port_name = $gip->get_port_name("$client_id","$r2");
                        if ( $r1_port_name ) {
                            $port_r = "range $r1_port_name $r2_port_name";
                        }
                    } else {
                        my $r1_port_nr = $gip->get_port_number("$client_id", "$r1");
                        my $r2_port_nr = $gip->get_port_number("$client_id", "$r2");
                        if ( $r1_port_nr ) {
                            $port_r = "range $r1_port_nr $r2_port_nr";
                        }
                    }

                    push @{$acl_connection_ports{$port_r}},"$acl_nr";

                    $is_range = 1;
                } elsif ( $found_port =~ /^\d+\s?-\s?\d+$/i ) {
                    $found_port =~ s/\s//g;
                    $found_port =~ s/ -/-/;
                    $found_port =~ s/- /-/;
                    $found_port =~ s/-/ /;
                    $port = "range " . $found_port;

                    my $port_r;
                    $found_port =~ /^(\d+) (\d+)$/i;
                    my $r1 = $1;
                    my $r2 = $2;
                    my $found;
                    if ( $r1 =~ /^\d+$/ ) {
                        my $r1_port_name = $gip->get_port_name("$client_id","$r1");
                        my $r2_port_name = $gip->get_port_name("$client_id","$r2");
                        if ( $r1_port_name ) {
                            $port_r = "range $r1_port_name $r2_port_name";
                            $found = 1;
                        }
                    } else {
                        my $r1_port_nr = $gip->get_port_number("$client_id", "$r1");
                        my $r2_port_nr = $gip->get_port_number("$client_id", "$r2");
                        if ( $r1_port_nr ) {
                            $port_r = "range $r1_port_nr $r2_port_nr";
                            $found = 1;
                        }
                    }
                    push @{$acl_connection_ports_range{$port_r}},"$acl_nr" if $found;
                    $is_range = 1;

                } elsif ( $found_port =~ /^any$/i ) {
                    $port = "";
                } elsif ( $found_port =~ /^icmp$/i ) {
                    $port = "";
                    $protocol = "ICMP";
                } elsif ( $found_port =~ /^ESP$/i ) {
                    $port = "";
                    $protocol = "ESP";
                } elsif ( $found_port !~ /^\d+$/ ) {
                    $dual_port = 1;
                    $port = $gip->get_port_number("$client_id", "$found_port") || "";
                    if ( ! $port ) {
                        $port_not_found = 1;
                        $port_with_name = $found_port;
                    } else {
                        $port_with_name = $port . '%%' . $found_port;
                    }
                    push @{$acl_connection_ports{$port_with_name}},"$acl_nr";
                    $port = "eq " . $port;
                    $found_port = "eq " . $found_port;
                } elsif ( $found_port =~ /^\d+$/ ) {
                    $port = $found_port;
                    $found_port = $gip->get_port_name("$client_id", "$found_port") || "";
                    if ( $found_port ) {
                        $port_with_name = $port . '%%' . $found_port;
                        $dual_port = 1;
                        $found_port = "eq " . $found_port;
                    } else {
                        $port_with_name = $port;
                    }
                    push @{$acl_connection_ports{$port_with_name}},"$acl_nr";
                    $port = "eq " . $port;
                } else {
                    push @{$acl_connection_ports{$found_port}},"$acl_nr" if $found_port;
                    $port = "eq " . $found_port;
                }

                my $c_acl = "";
                my $c_acl_dual = "";
                my $c_acl_out = "";
                my $c_acl_dual_out = "";

                if ( $dual_port ) {
                    $c_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " " .  $port if ! $port_not_found;
                    $c_acl = $gip->remove_whitespace_se("$c_acl");
                    $c_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " .  $port if ! $port_not_found;
                    $c_acl_out = $gip->remove_whitespace_se("$c_acl_out");

                    $c_acl_dual = "permit " . $protocol . " " .  $src . " " .  $dst . " " .  $found_port;
                    $c_acl_dual = $gip->remove_whitespace_se("$c_acl_dual");
                    $c_acl_dual_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " .  $found_port;
                    $c_acl_dual_out = $gip->remove_whitespace_se("$c_acl_dual_out");
                    if ( $c_acl ) {
                        $c_acl .= "%%" . $c_acl_dual;
                        $c_acl_out .= "%%" . $c_acl_dual_out;
                    } else {
                        $c_acl = $c_acl_dual;
                        $c_acl_out = $c_acl_dual_out;
                    }
                } else {
                    $c_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " " .  $port;
                    $c_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " .  $port;
                }    
                $c_acl =~ s/\s+/ /g;
                $c_acl = $gip->remove_whitespace_se("$c_acl");
                $c_acl = lc $c_acl;
                $c_acl_out =~ s/\s+/ /g;
                $c_acl_out = $gip->remove_whitespace_se("$c_acl_out");
                $c_acl_out = lc $c_acl_out;
                push @{$acl_connections_prepared{$c_acl}},"$acl_nr";
                push @{$acl_connections_prepared{$c_acl_out}},"$acl_nr";

                if ( $is_range ) {
                    if ( $found_port =~ /^range (\d+) (\d+)$/ ) {
                        $found_port =~ /^range (\d+) (\d+)$/;
                    } elsif ( $found_port =~ /^(\d+) (\d+)$/i ) {
                        $found_port =~ /^(\d+) (\d+)$/i;
                    }
                    my $start_port = $1 || "";
                    my $end_port = $2 || "";
                    my $port_dif = "";
                    $port_dif = $end_port - $start_port if $start_port && $end_port;
                    if ( $port_dif <= 30 && $start_port && $end_port ) {
                        for ( my $k = $start_port; $k <= $end_port; $k++ ) {
                            push @{$acl_connection_ports_range{$k}},"$acl_nr";

                            my $range_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " eq " .  $k;
                            my $range_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " eq " .  $k;
                            my $range_port_name = $gip->get_port_name("$client_id", "$k") || "";
                            my $range_acl_name = "";
                            my $range_acl_name_out = "";
                            if ( $range_port_name ) {
                                $range_acl_name = "permit " . $protocol . " " .  $src . " " .  $dst . " eq " .  $range_port_name;
                                $range_acl_name_out = "permit " . $protocol . " " .  $dst . " " .  $src . " eq " .  $range_port_name;
                                $range_acl .= "%%" . $range_acl_name;
                                $range_acl_out .= "%%" . $range_acl_name_out;
                            }

                            $range_acl =~ s/\s+/ /g;
                            $range_acl = $gip->remove_whitespace_se("$range_acl");
                            $range_acl = lc $range_acl;
                            $range_acl_out =~ s/\s+/ /g;
                            $range_acl_out = $gip->remove_whitespace_se("$range_acl_out");
                            $range_acl_out = lc $range_acl_out;

                            push @{$acl_connections_prepared_range_acl{$range_acl}},"$acl_nr";
                            push @{$acl_connections_prepared_range_acl{$range_acl_out}},"$acl_nr";

                            if ($bidirectional ) {
                                my $range_acl_bi = "permit " . $protocol . " " .  $src . " eq " . $k . " " .  $dst;
                                my $range_acl_bi_out = "permit " . $protocol . " " .  $dst . " eq " . $k . " " .  $src;
                                my $range_acl_name_bi = "";
                                my $range_acl_name_bi_out = "";
                                if ( $range_port_name ) {
                                    $range_acl_name_bi = "permit " . $protocol . " " .  $src . " eq " .  $range_port_name . " " . $dst;
                                    $range_acl_name_bi_out = "permit " . $protocol . " " .  $dst . " eq " .  $range_port_name . " " . $src;
                                    $range_acl_bi .= "%%" . $range_acl_name_bi;
                                    $range_acl_bi_out .= "%%" . $range_acl_name_bi_out;
                                }

                                $range_acl_bi =~ s/\s+/ /g;
                                $range_acl_bi = $gip->remove_whitespace_se("$range_acl_bi");
                                $range_acl_bi = lc $range_acl_bi;
                                $range_acl_bi_out =~ s/\s+/ /g;
                                $range_acl_bi_out = $gip->remove_whitespace_se("$range_acl_bi_out");
                                $range_acl_bi_out = lc $range_acl_bi_out;

                                push @{$acl_connections_prepared_range_acl{$range_acl_bi}},"$acl_nr";
                                push @{$acl_connections_prepared_range_acl{$range_acl_bi_out}},"$acl_nr";
                            }
                        }
                    }

                    my $port_r;
                    my $r1 = $start_port;
                    my $r2 = $end_port;
                    my $r1_port;
                    my $r2_port;
                    my $r_port_found;
                    if ( $r1 =~ /^\d+$/ ) {
                        $r1_port = $gip->get_port_name("$client_id","$r1");
                        $r2_port = $gip->get_port_name("$client_id","$r2");
                        if ( $r1_port ) {
                            $r_port_found = "range $r1_port $r2_port";
                        }
                    } else {
                        my $r1_port = $gip->get_port_number("$client_id", "$r1");
                        my $r2_port = $gip->get_port_number("$client_id", "$r2");
                        if ( $r1_port ) {
                            $r_port_found = "range $r1_port $r2_port";
                        }
                    }
                    if ( $r_port_found ) {
                            my $range_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " " . $r_port_found;
							$range_acl = lc $range_acl;
                            my $range_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " . $r_port_found;
							$range_acl_out = lc $range_acl_out;
                            push @{$acl_connections_prepared_range_acl{$range_acl}},"$acl_nr" if $r_port_found;
                            push @{$acl_connections_prepared_range_acl{$range_acl_out}},"$acl_nr" if $r_port_found;
                            if ($bidirectional ) {
                                my $range_acl_bi = "permit " . $protocol . " " .  $src . " " .  $r_port_found . " " .  $dst if $r_port_found;
                                $range_acl_bi = lc $range_acl_bi;
                                my $range_acl_out_bi = "permit " . $protocol . " " .  $dst . " " . $r_port_found . " " .  $src if $r_port_found;
                                $range_acl_out_bi = lc $range_acl_out_bi;
                                push @{$acl_connections_prepared_range_acl{$range_acl_bi}},"$acl_nr" if $r_port_found;
                                push @{$acl_connections_prepared_range_acl{$range_acl_out_bi}},"$acl_nr" if $r_port_found;
                            }
                    }
                }

                if ($bidirectional ) {
                    my $c_acl_bi = "";
                    my $c_acl_dual_bi = "";
                    my $c_acl_bi_out = "";
                    my $c_acl_dual_bi_out = "";
                    if ( $dual_port ) {
                        $c_acl_bi = "permit " . $protocol . " " .  $src . " " .  $port . " " .  $dst if ! $port_not_found;
                        $c_acl_bi = $gip->remove_whitespace_se("$c_acl_bi");
                        $c_acl_bi_out = "permit " . $protocol . " " .  $dst . " " .  $port . " " .  $src if ! $port_not_found;
                        $c_acl_bi_out = $gip->remove_whitespace_se("$c_acl_bi_out");

                        $c_acl_dual_bi = "permit " . $protocol . " " .  $src . " " .  $found_port . " " .  $dst;
                        $c_acl_dual_bi = $gip->remove_whitespace_se("$c_acl_dual_bi");
                        $c_acl_dual_bi_out = "permit " . $protocol . " " .  $dst . " " .  $found_port . " " .  $src;
                        $c_acl_dual_bi_out = $gip->remove_whitespace_se("$c_acl_dual_bi_out");

                        if ( $c_acl_bi ) {
                            $c_acl_bi .= "%%" . $c_acl_dual_bi;
                            $c_acl_bi_out .= "%%" . $c_acl_dual_bi_out;
                        } else {
                            $c_acl_bi = $c_acl_dual_bi;
                            $c_acl_bi_out = $c_acl_dual_bi_out;
                        }
                    } else {
                        $c_acl_bi = "permit " . $protocol . " " .  $src . " " .  $port . " " .  $dst;
                        $c_acl_bi_out = "permit " . $protocol . " " .  $dst . " " .  $port . " " .  $src;
                    }
                    $c_acl_bi =~ s/\s+/ /g;
                    $c_acl_bi = $gip->remove_whitespace_se("$c_acl_bi");
                    $c_acl_bi = lc $c_acl_bi;
                    $c_acl_bi_out =~ s/\s+/ /g;
                    $c_acl_bi_out = $gip->remove_whitespace_se("$c_acl_bi_out");
                    $c_acl_bi_out = lc $c_acl_bi_out;

                    push @{$acl_connections_prepared{$c_acl_bi}},"$acl_nr";
                    push @{$acl_connections_prepared{$c_acl_bi_out}},"$acl_nr";
                }
            }

            %acl_connections_prepared_range_acl = (%acl_connections_prepared_range_acl, %acl_connections_prepared);
            %acl_connection_ports_range = (%acl_connection_ports, %acl_connection_ports_range);

        } elsif ( $protocol_found && $protocol_found ne "IP" && ( $protocols{uc($protocol_found)} || $protocols_by_name{uc($protocol_found)})) {
            my $c_acl = "permit " . $protocol_found . " " .  $src . " " .  $dst;
            my $c_acl_out = "permit " . $protocol_found . " " .  $dst . " " .  $src;
            $c_acl = $gip->remove_whitespace_se("$c_acl");
            $c_acl = lc $c_acl;
            $c_acl_out = $gip->remove_whitespace_se("$c_acl_out");
            $c_acl_out = lc $c_acl_out;
#            $acl_connections_prepared{$c_acl} = $acl_nr;
#            $acl_connections_prepared{$c_acl_out} = $acl_nr;

            push @{$acl_connections_prepared{$c_acl}},"$acl_nr";
            push @{$acl_connections_prepared{$c_acl_out}},"$acl_nr";

            %acl_connections_prepared_range_acl = (%acl_connections_prepared_range_acl, %acl_connections_prepared);
            %acl_connection_ports_range = (%acl_connection_ports, %acl_connection_ports_range);
        }

		$j++;
}

if ( $show_connection_acl ) {
#	print "<br><p><b>$$lang_vars{acl_connection_acl_message}</b><p>\n";
	print "<br><p>\n";
	if ( keys %acl_connections_prepared_range_acl ) {
    print "<table border=\"1\" cellpadding=\"4\">\n";
    print "<tr><td><b>$$lang_vars{con_nr_message}</b></td><td><b>$$lang_vars{acl_message}</b></td></tr>\n";
    foreach my $acl_con_acl (sort {$acl_connections_prepared_range_acl{$a}->[0] <=> $acl_connections_prepared_range_acl{$b}->[0] or $a cmp $b } (keys %acl_connections_prepared_range_acl)) {
		my $con_nr_arr_ref = $acl_connections_prepared_range_acl{$acl_con_acl};

		my @con_nr_arr_ref = @$con_nr_arr_ref;
		@con_nr_arr_ref = uniq(@con_nr_arr_ref);

		my $class = "";
		if ( $con_nr_arr_ref[1] ) {
			$class ='class="text-info"';
		}
		foreach my $acl_nr ( @con_nr_arr_ref ) {
#				my $acl_nr = $acl_connections_prepared_range_acl{$_} || "";
                if ( $acl_nr ) {
					if ( $acl_con_acl =~ /%%/ ) {
						$acl_con_acl =~ /^(.+)%%(.+)$/;
						my $acl1 = $1;
						my $acl2 = $2;
						print "<tr><td>$acl_nr</td><td $class>$acl1</td></tr>\n";
						print "<tr><td>$acl_nr</td><td $class>$acl2</td></tr>\n";
					} else {
						print "<tr><td>$acl_nr</td><td $class>$acl_con_acl</td></tr>\n";
					}
                }
		}
    }
    print "</table>\n";
	} else {
		print "<p>$$lang_vars{no_resultado_message}<br>\n";
	}
    $gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
    exit 0;
}

my @acls=$gip->get_acls("$client_id");

$j = 0;
foreach ( @acls ) {
	my $id = $acls[$j]->[0];
	my $src = $acls[$j]->[1] || "";
	my $src_wmask = $acls[$j]->[2] || "";
	my $src_port = $acls[$j]->[3] || "";
	my $src_operator = $acls[$j]->[4];
	my $dst = $acls[$j]->[5] || "";
	my $dst_wmask = $acls[$j]->[6] || "";
	my $dst_port = $acls[$j]->[7] || "";
	my $dst_operator = $acls[$j]->[8];
	my $protocol = $acls[$j]->[10];
	my $action = $acls[$j]->[11];
	my $icmp_type = $acls[$j]->[12];

	my $src_acl = "";
	if ( $src_wmask eq "0.0.0.0" ) {
		$src_acl = "host" . " " . $src;
	} else {
		$src_acl = "$src $src_wmask";
	}

	my $dst_acl = "";
	if ( $dst_wmask eq "0.0.0.0" ) {
		$dst_acl = "host" . " " . $dst;
	} else {
		$dst_acl = "$dst $dst_wmask";
	}

    my $src_port_name = "";
    my $src_port_name_found = "";
    my $src_port_with_name = "";
    if ( $src_port =~ /^\d+$/ ) {
        $src_port_name = $gip->get_port_name("$client_id", "$src_port") || "" if $src_port !~ /range/i;
        if ( $src_port_name ) {
            $src_port_name_found = 1;
            $src_port_with_name = $src_port . '%%' . $src_port_name;
        } else {
            $src_port_name = $src_port;
            $src_port_with_name = $src_port;
        }
    } elsif ( $src_port =~ /^range/i ) {
        # do not try to resolve the ports
    } elsif ( $src_port ) {
        $src_port_name = $src_port;
        $src_port = $gip->get_port_number("$client_id", "$src_port") || "" if $src_port !~ /range/i;
        if ( $src_port ) {
            $src_port_name_found = 1;
            $src_port_with_name = $src_port . '%%' . $src_port_name;
        } else {
            $src_port = $src_port_name;
            $src_port_with_name = $src_port;
        }
    }

    my $dst_port_name = "";
    my $dst_port_name_found = "";
    my $dst_port_with_name = "";
    if ( $dst_port =~ /^\d+$/ ) {
        $dst_port_name = $gip->get_port_name("$client_id", "$dst_port") || "" if $dst_port !~ /range/i;
        if ( $dst_port_name ) {
            $dst_port_name_found = 1;
            $dst_port_with_name = $dst_port . '%%' . $dst_port_name;
        } else {
            $dst_port_name = $dst_port;
            $dst_port_with_name = $dst_port;
        }
    } elsif ( $dst_port =~ /^range/i ) {
        # do not try to resolve the ports
    } elsif ( $dst_port ) {
        $dst_port_name = $dst_port;
        $dst_port = $gip->get_port_number("$client_id", "$dst_port") || "" if $dst_port !~ /range/i;
        if ( $dst_port ) {
            $dst_port_name_found = 1;
            $dst_port_with_name = $dst_port . '%%' . $dst_port_name;
        } else {
            $dst_port = $dst_port_name;
            $dst_port_with_name = $dst_port;
        }
    }

    push @{$acl_ports{$src_port_with_name}},"$id" if $src_port;
    push @{$acl_ports{$dst_port_with_name}},"$id" if $dst_port;

	my $acl = $action . " " . $protocol . " " . $src_acl  . " " . $src_operator . " " . $src_port . " " . $dst_acl . " " . $dst_operator . " " . $dst_port . " " . $icmp_type;
    my $acl_port_name = "";
	$acl_port_name = $action . " " . $protocol . " " . $src_acl  . " " . $src_operator . " " . $src_port_name . " " . $dst_acl . " " . $dst_operator . " " . $dst_port_name . " " . $icmp_type if $src_port_name_found || $dst_port_name_found;

	$acl =~ s/\s+/ /g;
	$acl_port_name =~ s/\s+/ /g;
    $acl = $gip->remove_whitespace_se("$acl");
    $acl_port_name = $gip->remove_whitespace_se("$acl_port_name");

#    $acl .= "%%" . $acl_port_name if $src_port_name_found || $dst_port_name_found;
    $acl = $gip->remove_whitespace_se("$acl");
    $acl = lc $acl;
    $acls_prepared{$acl} = $id;
    $acl_port_name = $gip->remove_whitespace_se("$acl_port_name");
    $acl_port_name = lc $acl_port_name;
    $acls_prepared{$acl_port_name} = $id;

	$j++;
}


my $csv_file_name;
my $csv_file;
my $export_string;

my $acl_connections_only = $gip->compare_hash_array(\%acl_connections_prepared, \%acls_prepared);
my @acl_connections_only_export;

my $acls_only = $gip->compare_hash(\%acls_prepared, \%acl_connections_prepared_range_acl);
my @acl_only_export;

my $acl_connection_ports_only = $gip->compare_hash(\%acl_connection_ports, \%acl_ports);
my $acl_ports_only = $gip->compare_hash(\%acl_ports, \%acl_connection_ports_range);
my @acl_connection_ports_only_export;
my @acl_ports_only_export;


my %acl_connections_prepared_checked;
my %acls_prepared_checked;

foreach my $acl_key ( @$acl_connections_only ) {
    # list of ACLs
	my $acl1 = "";
	my $acl2 = "";
	if ( $_ =~ /%%/ ) {
		$_ =~ /^(.+)%%(.+)$/;
		$acl1 = $1;
		$acl2 = $2;
		$acl_key = $acl1;
	}

    if ( exists $acl_connections_prepared{$acl_key} ) {
		my $acl_nr = $acl_connections_prepared{$acl_key};
        foreach my $acl_nr ( @$acl_nr ) {
#    $acl_connections_prepared_checked{$acl_key} = $acl_connections_prepared{$acl_key} if exists $acl_connections_prepared{$acl_key};
            push @{$acl_connections_prepared_checked{$acl_key}},"$acl_nr";
        }
    }
}


# ACL Connections which are not found in the ACL List

print "<br><p><b>$$lang_vars{acl_con_only_message}</b><p>\n";
print "<table border=\"1\" cellpadding=\"4\">\n";
print "<tr><td><b>$$lang_vars{con_nr_message}</b></td><td><b>$$lang_vars{acl_connection_message}</b></td></tr>\n";

foreach my $acl_con_acl (sort {$acl_connections_prepared_checked{$a}->[0] <=> $acl_connections_prepared_checked{$b}->[0] or $a cmp $b } (keys %acl_connections_prepared_checked)) {
    my $con_nr_arr_ref = $acl_connections_prepared_checked{$acl_con_acl};

    my @con_nr_arr_ref = @$con_nr_arr_ref;
    @con_nr_arr_ref = uniq(@con_nr_arr_ref);

    my $class = "";
    if ( $con_nr_arr_ref[1] ) {
        $class ='class="text-info"';
    }
    foreach my $acl_nr ( @con_nr_arr_ref ) {
        if ( $acl_nr ) {
            if ( $acl_con_acl =~ /%%/ ) {
                $acl_con_acl =~ /^(.+)%%(.+)$/;
                my $acl1 = $1;
                my $acl2 = $2;
                print "<tr><td>$acl_nr</td><td $class>$acl1</td></tr>\n";
                print "<tr><td>$acl_nr</td><td $class>$acl2</td></tr>\n";
                $export_string = $acl_nr . "," . $acl1 . "\n";
                $export_string .= $acl_nr . "," . $acl2;
            } else {
                print "<tr><td>$acl_nr</td><td $class>$acl_con_acl</td></tr>\n";
                $export_string = $acl_nr . "," . $acl_con_acl . "\n";;
            }
        }
    }
    push @acl_connections_only_export, $export_string;
}

print "</table>\n";

$csv_file_name="acl_con_only.csv";
$csv_file="./export/$csv_file_name";

unlink $csv_file if -e $csv_file;

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!");

print EXPORT $$lang_vars{con_nr_message} . "," . $$lang_vars{acl_connection_message} . "\n";
foreach ( @acl_connections_only_export ) {
        print EXPORT "$_\n";
}
close EXPORT;

print "<p><span style=\"float: $ori\"><a href=\"$server_proto://$base_uri/export/$csv_file_name\">$$lang_vars{download_csv_file}</a></span><p><br>\n";


foreach ( @$acls_only ) {
	my $acl1 = "";
	my $acl2 = "";
	my $acl_key = $_;
	if ( $_ =~ /%%/ ) {
		$_ =~ /^(.+)%%(.+)$/;
		$acl1 = $1;
		$acl2 = $2;
		$acl_key = $acl1;
	}
    $acls_prepared_checked{$acl_key} = $acls_prepared{$_} if exists $acls_prepared{$_};
}

# ACLs which are not found in the Connection List

print "<br><p><b>$$lang_vars{acl_only_message}</b><p>\n";
print "<table border=\"1\" cellpadding=\"4\">\n";
print "<tr><td><b>$$lang_vars{id_message}</b></td><td><b>$$lang_vars{acl_message}</b></td></tr>\n";

foreach (sort {$acls_prepared_checked{$a} <=> $acls_prepared_checked{$b}} (keys %acls_prepared_checked)) {
	print "<tr><td>$acls_prepared_checked{$_}</td><td>$_</td></tr>\n" if exists $acls_prepared_checked{$_};
    $export_string = $acls_prepared_checked{$_} . "," . $_;
    push @acl_only_export, $export_string;
}
print "</table>\n";

$csv_file_name="acl_only.csv";
$csv_file="./export/$csv_file_name";

unlink $csv_file if -e $csv_file;

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!");

print EXPORT $$lang_vars{id_message} . "," . $$lang_vars{acl_message} . "\n";
foreach ( @acl_only_export ) {
        print EXPORT "$_\n";
}
close EXPORT;

print "<p><span style=\"float: $ori\"><a href=\"$server_proto://$base_uri/export/$csv_file_name\">$$lang_vars{download_csv_file}</a></span><p><br>\n";



# PORTS

# Ports in connections but not in ACLs

print "<br><p><b>$$lang_vars{non_acl_ports_message}</b><p>\n";
print "<table border=\"1\" cellpadding=\"4\">\n";
print "<tr><td><b>$$lang_vars{port_message}</b></td><td><b>$$lang_vars{con_nr_message}</b></td></tr>\n";
foreach ( sort { ($a =~ /(\d+)/)[0] <=> ($b =~ /(\d+)/)[0] } @$acl_connection_ports_only ) {
    my $port_string;
    if ( $_ =~ /%%/ ) {
        $_ =~ /^(.+)%%(.+)$/;
        $port_string = $1 . " (" . $2 . ")";
    } else {
        $port_string = $_;
    }
    print "<tr><td>$port_string</td><td> ";

    my $acl_list_s = $acl_connection_ports{$_};
    my $acl_list_s_nr = "";
    foreach my $x ( @$acl_list_s ) {
        $acl_list_s_nr .= ", " . $x;
    }
    $acl_list_s_nr =~ s/^, //;
    print "$acl_list_s_nr\n";
    print "</td></tr>\n";

    $export_string = $port_string . ",\"" . $acl_list_s_nr . "\"";
    push @acl_connection_ports_only_export, $export_string;
}
print "</table>\n";

$csv_file_name="acl_connection_ports_only.csv";
$csv_file="./export/$csv_file_name";

unlink $csv_file if -e $csv_file;

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!");

print EXPORT $$lang_vars{port_message} . "," . $$lang_vars{ACL_nr_message} . "\n";
foreach ( @acl_connection_ports_only_export ) {
        print EXPORT "$_\n";
}
close EXPORT;

print "<p><span style=\"float: $ori\"><a href=\"$server_proto://$base_uri/export/$csv_file_name\">$$lang_vars{download_csv_file}</a></span><p><br>\n";


# Ports in ACLs but not in Connections

print "<br><p><b>$$lang_vars{non_acl_con_ports_message}</b><p>\n";
print "<table border=\"1\" cellpadding=\"4\">\n";
print "<tr><td><b>$$lang_vars{port_message}</b></td><td><b>$$lang_vars{acl_id_message}</b></td></tr>\n";
foreach ( sort { ($a =~ /(\d+)/)[0] <=> ($b =~ /(\d+)/)[0] } @$acl_ports_only ) {
    my $port_string;
    if ( $_ =~ /%%/ ) {
        $_ =~ /^(.+)%%(.+)$/;
        $port_string = $1 . " (" . $2 . ")";
    } else {
        $port_string = $_;
    }
    print "<tr><td>$port_string</td><td> ";

    my $acl_list_s = $acl_ports{$_};
    my $acl_list_s_nr = "";
    foreach my $x ( @$acl_list_s ) {
        $acl_list_s_nr .= ", " . $x;
    }
    $acl_list_s_nr =~ s/^, //;

    print "$acl_list_s_nr\n";
    print "</td></tr>\n";

    $export_string = $port_string . ",\"" . $acl_list_s_nr . "\"";
    push @acl_ports_only_export, $export_string;
}
print "</table>\n";

$csv_file_name="acl_ports_only.csv";
$csv_file="./export/$csv_file_name";

unlink $csv_file if -e $csv_file;

open(EXPORT,">$csv_file") or $gip->print_error("$client_id","$!");

print EXPORT $$lang_vars{port_message} . "," . $$lang_vars{id_message} . "\n";
foreach ( @acl_ports_only_export ) {
        print EXPORT "$_\n";
}
close EXPORT;

print "<p><span style=\"float: $ori\"><a href=\"$server_proto://$base_uri/export/$csv_file_name\">$$lang_vars{download_csv_file}</a></span><p><br>\n";


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

sub uniq {
    my %seen;
    grep !$seen{$_}++, @_;
}
