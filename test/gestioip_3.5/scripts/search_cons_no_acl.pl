#!/usr/bin/perl -T -w

# v1.8.6 20210926

use strict;
use DBI;
use strict;
use Net::IP;
use Net::IP qw(:PROC);

my $client_id = 1;

my $debug = 1;

# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = get_db_parameter();

if ( ! $pass_gestioip ) {
    print "Database password not found\n";
    exit 1;
}

my @acl_connections=get_acl_connections("$client_id","");
my %protocols = get_protocol_hash("$client_id");
my %protocols_by_name = get_protocol_name_hash("$client_id");
my %port_name_hash = get_port_hash("name");
my %port_number_hash = get_port_hash("number");


my @acl_connections_prepared;
my @acls_prepared;

my %acl_connections_prepared;
my %acl_connections_prepared_range_acl;
my %acls_prepared;

my %acl_connection_ports;
my %acl_connection_ports_range;
my %acl_ports;

my @used_acl_cons;
my @acl_con_ip_list;

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

        print "$acl_nr - $proto_id - $protocol_found\n" if $debug;

        my $src_port = $acl_connections[$j]->[9] || "";
        my $bidirectional = $acl_connections[$j]->[10] || "";
        my $dst_vlan = $acl_connections[$j]->[11] || "";
        my $destination = $acl_connections[$j]->[12] || "";
        my $dst = $acl_connections[$j]->[13] || "";

		if ( $src =~ /\// ) {
			$src =~ /^(.+)\/(.+)$/;
			my $src_ip = $1;
			my $bm = $2 || "";
            if ( $bm !~ /^\d{1,3}$/ ) {
                print "invalid SRC: $src - ID: $id - CON.NR.: $acl_nr - ignored\n" if $debug;
                $j++;
                next;
            }
			if ( $bm eq 32 ) {
				$src = "host $src";
			} else {
				my $src_wmask = get_wmask_from_bm("$bm");
				$src = "$src_ip $src_wmask";
			}
		} elsif ( $src =~ /^any$/ ) {
            # do nothing
		} elsif ( ! $src ) {
            $src = "any";
		} else {
			push @acl_con_ip_list, $src;
			$src = "host $src";
		}

		if ( $dst =~ /\// ) {
			$dst =~ /^(.+)\/(.+)$/;
			my $dst_ip = $1;
			my $bm = $2 || "";
            if ( $bm !~ /^\d{1,3}$/ ) {
                print "invalid DST: $dst - ID: $id - CON.NR.: $acl_nr - ignored\n" if $debug;
                $j++;
                next;
            }
			if ( $bm eq 32 ) {
				$dst = "host $dst";
			} else {
				my $dst_wmask = get_wmask_from_bm("$bm");
				$dst = "$dst_ip $dst_wmask";
			}
		} elsif ( $dst =~ /^any$/ ) {
            # do nothing
		} elsif ( ! $dst ) {
            $dst = "any";
		} else {
			push @acl_con_ip_list, $dst;
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

                $found_port = remove_whitespace_se("$found_port");

                if ( $found_port =~ /range/i ) {
                    $found_port =~ s/R/r/;
                    $found_port =~ s/ -/-/;
                    $found_port =~ s/- /-/;
                    $found_port =~ s/-/ /;
                    $port = $found_port;

                    push @{$acl_connection_ports{$port}},"$acl_nr";
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
#						my $r1_port_name = get_port_name("$r1");
#						my $r2_port_name = get_port_name("$r2");
						my $r1_port_name = $port_number_hash{"$r1"} || "";
						my $r2_port_name = $port_number_hash{"$r2"} || "";
                        my $r1_pn_show = $r1;
                        my $r2_pn_show = $r2;
                        $r1_pn_show = $r1_port_name if $r1_port_name;
                        $r2_pn_show = $r2_port_name if $r2_port_name;
						if ( $r1_port_name || $r2_port_name ) {
							$port_r = "range $r1_pn_show $r2_pn_show";
							$found = 1;
						}
					} else {
#						my $r1_port_nr = get_port_number("$client_id", "$r1");
#						my $r2_port_nr = get_port_number("$client_id", "$r2");
						my $r1_port_nr = $port_name_hash{"$r1"} || "";
						my $r2_port_nr = $port_name_hash{"$r2"} || "";
                        my $r1_pn_show = $r1;
                        my $r2_pn_show = $r2;
                        $r1_pn_show = $r1_port_nr if $r1_port_nr;
                        $r2_pn_show = $r2_port_nr if $r2_port_nr;
						if ( $r1_port_nr || $r2_port_nr ) {
							$port_r = "range $r1_pn_show $r2_pn_show";
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
#                    $port = get_port_number("$client_id", "$found_port") || "";
                    $port = $port_name_hash{"$found_port"} || "";

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
#                    $found_port = get_port_name("$found_port") || "";
                    $found_port = $port_number_hash{"$found_port"} || "";
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
                    $c_acl = remove_whitespace_se("$c_acl");
                    $c_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " .  $port if ! $port_not_found;
                    $c_acl_out = remove_whitespace_se("$c_acl_out");

                    $c_acl_dual = "permit " . $protocol . " " .  $src . " " .  $dst . " " .  $found_port;
                    $c_acl_dual = remove_whitespace_se("$c_acl_dual");
                    $c_acl_dual_out = "permit " . $protocol . " " .  $dst . " " .  $src . " " .  $found_port;
                    $c_acl_dual_out = remove_whitespace_se("$c_acl_dual_out");
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
                $c_acl = remove_whitespace_se("$c_acl");
                $c_acl = lc $c_acl;
                $c_acl_out =~ s/\s+/ /g;
                $c_acl_out = remove_whitespace_se("$c_acl_out");
                $c_acl_out = lc $c_acl_out;
                #$acl_connections_prepared{$c_acl} = $acl_nr;
#                $acl_connections_prepared{$c_acl_out} = $acl_nr;
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
                    if ( $port_dif && $port_dif <= 30 && $start_port && $end_port ) {
                        for ( my $k = $start_port; $k <= $end_port; $k++ ) {
                            push @{$acl_connection_ports_range{$k}},"$acl_nr";

                            my $range_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " eq " .  $k;
                            my $range_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src . " eq " .  $k;
#                            my $range_port_name = get_port_name("$k") || "";
                            my $range_port_name = $port_number_hash{"$k"} || "";
                            my $range_acl_name = "";
                            my $range_acl_name_out = "";
                            if ( $range_port_name ) {
                                $range_acl_name = "permit " . $protocol . " " .  $src . " " .  $dst . " eq " .  $range_port_name;
                                $range_acl_name_out = "permit " . $protocol . " " .  $dst . " " .  $src . " eq " .  $range_port_name;
                                $range_acl .= "%%" . $range_acl_name;
                                $range_acl_out .= "%%" . $range_acl_name_out;
                            }

                            $range_acl =~ s/\s+/ /g;
                            $range_acl = remove_whitespace_se("$range_acl");
                            $range_acl = lc $range_acl;
                            $range_acl_out =~ s/\s+/ /g;
                            $range_acl_out = remove_whitespace_se("$range_acl_out");
                            $range_acl_out = lc $range_acl_out;

#                            $acl_connections_prepared_range_acl{$range_acl} = $acl_nr;
#                            $acl_connections_prepared_range_acl{$range_acl_out} = $acl_nr;

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
                                $range_acl_bi = remove_whitespace_se("$range_acl_bi");
                                $range_acl_bi = lc $range_acl_bi;
                                $range_acl_bi_out =~ s/\s+/ /g;
                                $range_acl_bi_out = remove_whitespace_se("$range_acl_bi_out");
                                $range_acl_bi_out = lc $range_acl_bi_out;

#                                $acl_connections_prepared_range_acl{$range_acl_bi} = $acl_nr;
#                                $acl_connections_prepared_range_acl{$range_acl_bi_out} = $acl_nr;

                                push @{$acl_connections_prepared_range_acl{$range_acl_bi}},"$acl_nr";
                                push @{$acl_connections_prepared_range_acl{$range_acl_bi_out}},"$acl_nr";
                            }
                        }
                    }

					my $port_r;
#					$found_port =~ /^range (.+) (.+)$/;
					my $r1 = $start_port;
					my $r2 = $end_port;
					my $r1_port;
					my $r2_port;
					my $r_port_found;
					if ( $r1 =~ /^\d+$/ ) {
#						$r1_port = get_port_name("$r1") || "";
#						$r2_port = get_port_name("$r2") || "";
                        $r1_port = $port_number_hash{"$r1"} || "";
                        $r2_port = $port_number_hash{"$r2"} || "";

						if ( $r1_port && $r2_port ) {
							$r_port_found = "range $r1_port $r2_port";
						} else {
                            print "Range (1): start or end port not found: $r1_port ($r1) - $r2_port ($r2)\n";
                        }
					} else {
#						my $r1_port = get_port_number("$client_id", "$r1") || "";
#						my $r2_port = get_port_number("$client_id", "$r2") || "";
                        my $r1_port = $port_name_hash{"$r1"} || "";
                        my $r2_port = $port_name_hash{"$r2"} || "";

						if ( $r1_port && $r2_port ) {
							$r_port_found = "range $r1_port $r2_port";
						} else {
                            print "Range (2): start or end port not found: $r1_port ($r1) - $r2_port ($r2)\n";
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
                        $c_acl_bi = remove_whitespace_se("$c_acl_bi");
                        $c_acl_bi_out = "permit " . $protocol . " " .  $dst . " " .  $port . " " .  $src if ! $port_not_found;
                        $c_acl_bi_out = remove_whitespace_se("$c_acl_bi_out");

                        $c_acl_dual_bi = "permit " . $protocol . " " .  $src . " " .  $found_port . " " .  $dst;
                        $c_acl_dual_bi = remove_whitespace_se("$c_acl_dual_bi");
                        $c_acl_dual_bi_out = "permit " . $protocol . " " .  $dst . " " .  $found_port . " " .  $src;
                        $c_acl_dual_bi_out = remove_whitespace_se("$c_acl_dual_bi_out");

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
                    $c_acl_bi = remove_whitespace_se("$c_acl_bi");
                    $c_acl_bi = lc $c_acl_bi;
                    $c_acl_bi_out =~ s/\s+/ /g;
                    $c_acl_bi_out = remove_whitespace_se("$c_acl_bi_out");
                    $c_acl_bi_out = lc $c_acl_bi_out;

                    push @{$acl_connections_prepared{$c_acl_bi}},"$acl_nr";
                    push @{$acl_connections_prepared{$c_acl_bi_out}},"$acl_nr";
                }
            }

            # create generic con-acl without ports to make sure that an ACL without ports, which includes this con-acl, matches
            my $gen_acl = "permit " . $protocol . " " .  $src . " " .  $dst;
            $gen_acl = lc $gen_acl;
            push @{$acl_connections_prepared{$gen_acl}},"$acl_nr";
#            print "TEST CON GEN PUSH: $gen_acl - $acl_nr\n";
            if ($bidirectional ) {
                my $gen_acl_out = "permit " . $protocol . " " .  $dst . " " .  $src;
                $gen_acl_out = lc $gen_acl_out;
                push @{$acl_connections_prepared{$gen_acl_out}},"$acl_nr";
#                print "TEST CON GEN OUT PUSH: $gen_acl_out - $acl_nr\n";
            }

            %acl_connections_prepared_range_acl = (%acl_connections_prepared_range_acl, %acl_connections_prepared);
            %acl_connection_ports_range = (%acl_connection_ports, %acl_connection_ports_range);

        } elsif ( $protocol_found && $protocol_found ne "IP" && ( $protocols{uc($protocol_found)} || $protocols_by_name{uc($protocol_found)})) {
            my $c_acl = "permit " . $protocol_found . " " .  $src . " " .  $dst;
            my $c_acl_out = "permit " . $protocol_found . " " .  $dst . " " .  $src;
            $c_acl = remove_whitespace_se("$c_acl");
            $c_acl = lc $c_acl;
            $c_acl_out = remove_whitespace_se("$c_acl_out");
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

#print "TEST ACL CON IP LIST: @acl_con_ip_list\n";

my %seen = ();
my @uniqu = grep { ! $seen{$_} ++ } @acl_con_ip_list;
@acl_con_ip_list = @uniqu;
my %mask = get_netmask_to_bm();

my @acls=get_acls("$client_id");


my @acls_new;
$j = 0;
foreach ( @acls ) {
	# foreach ACLs
	# if ACL contains subnet
	# src or dst subnet
	# check if src or dest IP overlaps with src or dst IP in acl-cons
	# > create ACL with this IP
	# check if exists $acl_connections_prepared_range_acl{"ACL"}

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
	$j++;

# TEST PORT NR - PORT NAME???

    if ( $src_wmask !~ /^0\.0\.0\.0$/ || $dst_wmask !~ /^0\.0\.0\.0$/ ) {
#        print "TEST RANGE ACL FOUND - $src_wmask - $dst_wmask\n";
		my $src_mask = get_netmask_from_wildcard("$src_wmask");
		my $dst_mask = get_netmask_from_wildcard("$dst_wmask");
		my $src_bm = $mask{$src_mask};
		my $dst_bm = $mask{$dst_mask};
		my $red_src = "$src/$src_bm";
#			print "TEST RED SRC: $red_src\n";
		my $ipob_src = new Net::IP ($red_src);
		my $red_dst = "$dst/$dst_bm";
#			print "TEST RED DST: $red_dst\n";
		my $ipob_dst = new Net::IP ($red_dst);

		if ( ! $ipob_src || ! $ipob_dst ) {
			# error creating ip objects - ignore entry
            print "Can not create ip object: $red_src - $red_dst \n" if $debug; 
			$j++;
			next;
		}

		foreach ( @acl_con_ip_list ) {
            my $con_ip = $_;
			my $ipm = "$con_ip/32";
			my $ipmob = new Net::IP ($ipm);

			next if ! $ipmob;

			if ( $ipmob->overlaps($ipob_src) == $IP_A_IN_B_OVERLAP || $ipmob->overlaps($ipob_dst) == $IP_A_IN_B_OVERLAP) {
				# overlap
				if ( $src_wmask !~ /^0\.0\.0\.0$/ ) {
					$src = "$con_ip";
				}
				if ( $dst_wmask !~ /^0\.0\.0\.0$/ ) {
					$dst = "$con_ip";
				}

				my $acl = $action . " " . $protocol . " " . $src  . " " . $src_operator . " " . $src_port . " " . $dst . " " . $dst_operator . " " . $dst_port . " " . $icmp_type;
#				print "TEST OVERLAP: ADD TO ACLS: $acl\n";
#
#                # Add generated ACL (with /32 address) to acls_prepared
#                $acls_prepared{$acl} = $id;
#
				my @gen_acl;
                push @gen_acl, "$id", "$src", "0.0.0.0", "$src_port", "$src_operator", "$dst", "0.0.0.0", "$dst_port", "$dst_operator", "", "$protocol", "$action", "$icmp_type";
                push @acls_new, \@gen_acl;
			} else {
#				print "TEST NO OVERLAPPPPP\n";
			}
		}
    }
}

my $anz_acls = @acls;
my $anz_acls_new = @acls_new;
print "TEST ANZ ACLs: $anz_acls\n" if $debug;
print "TEST ANZ ACLs NEW: $anz_acls_new\n" if $debug;
push @acls, @acls_new;


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

    #print "TEST PROCESSING ACL: $id - $src - $dst\n";

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
#        $src_port_name = get_port_name("$src_port") || "" if $src_port !~ /range/i;
        if ( $src_port !~ /range/i ) {
            $src_port_name = $port_number_hash{"$src_port"} || "";
        }
        if ( $src_port_name ) {
            $src_port_name_found = 1;
            $src_port_with_name = $src_port . '%%' . $src_port_name;
        } else {
            $src_port_name = $src_port;
            $src_port_with_name = $src_port;
        }
    } elsif ( $src_port =~ /^range/i ) {
		$src_port =~ /^range (.+) (.+)$/;
		my $r1 = $1;
		my $r2 = $2;

        my ( $r1_port_name, $r2_port_name, $r1_port_nr, $r2_port_nr);
		if ( $r1 =~ /^\d+$/ ) {
#            $r1_port_name = get_port_name("$r1");
#            $r2_port_name = get_port_name("$r2");
            $r1_port_name = $port_number_hash{"$r1"} || "";
            $r2_port_name = $port_number_hash{"$r2"} || "";
            my $r1_pn_show = $r1;
            my $r2_pn_show = $r2;
            $r1_pn_show = $r1_port_name if $r1_port_name;
            $r2_pn_show = $r2_port_name if $r2_port_name;
            if ( $r1_port_name || $r2_port_name ) {
				$src_port_name = "range $r1_pn_show $r2_pn_show";
				$src_port_name_found = 1;
            }
            $r1_port_nr = $r1;
            $r2_port_nr = $r2;
        } else {
#            $r1_port_nr = get_port_number("$client_id", "$r1");
#            $r2_port_nr = get_port_number("$client_id", "$r2");
            $r1_port_nr = $port_name_hash{"$r1"} || "";
            $r2_port_nr = $port_name_hash{"$r2"} || "";
            my $r1_pn_show = $r1;
            my $r2_pn_show = $r2;
            $r1_pn_show = $r1_port_nr if $r1_port_nr;
            $r2_pn_show = $r2_port_nr if $r2_port_nr;
            if ( $r1_port_nr || $r2_port_nr ) {
				$src_port_name = "range $r1_pn_show $r2_pn_show";
				$src_port_name_found = 1;
            }
		}

        my $port_dif = "";
        $port_dif = $r2_port_nr - $r1_port_nr if $r1_port_nr && $r2_port_nr;
#        print "TEST PORT DIFF: $port_dif\n";
        if ( $port_dif && $port_dif <= 30 && $r1_port_nr && $r2_port_nr ) {
            for ( my $k = $r1_port_nr; $k <= $r2_port_nr; $k++ ) {

                my $acl = $action . " " . $protocol . " " . $src_acl  . " " . $src_operator . " " . $k . " " . $dst_acl . " " . $dst_operator . " " . $dst_port . " " . $icmp_type;

                $acl =~ s/\s+/ /g;
                $acl = remove_whitespace_se("$acl");
                $acl = lc $acl;
                $acls_prepared{$acl} = $id;
#                print "TEST ACL src_port: $acl (GEN)\n";
            }
        }
    } elsif ( $src_port ) {
        # src port is name
        $src_port_name = $src_port;
        if ( $src_port !~ /range/i ) {
            $src_port = $port_number_hash{"$src_port"} || "";
        }
        
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
#        $dst_port_name = get_port_name("$dst_port") || "" if $dst_port !~ /range/i;
        if ( $dst_port !~ /range/i ) {
            $dst_port_name = $port_number_hash{"$dst_port"} || "";
        }
        if ( $dst_port_name ) {
            $dst_port_name_found = 1;
            $dst_port_with_name = $dst_port . '%%' . $dst_port_name;
        } else {
            $dst_port_name = $dst_port;
            $dst_port_with_name = $dst_port;
        }
    } elsif ( $dst_port =~ /^range/i ) {
        # do not try to resolve the ports
		$dst_port =~ /^range (.+) (.+)$/;
		my $r1 = $1;
		my $r2 = $2;
        my ( $r1_port_name, $r2_port_name, $r1_port_nr, $r2_port_nr);
		if ( $r1 =~ /^\d+$/ ) {
            $r1_port_name = $port_number_hash{"$r1"} || "";
            $r2_port_name = $port_number_hash{"$r2"} || "";
            if ( $r1_port_name && $r2_port_name ) {
				$dst_port_name = "range $r1_port_name $r2_port_name";
				$dst_port_name_found = 1;
            } else {
                print "Range (3): start or end port not found: $r1_port_name ($r1) - $r2_port_name ($r2)\n";
            }
            $r1_port_nr = $r1;
            $r2_port_nr = $r2;
		} else {
            $r1_port_nr = $port_name_hash{"$r1"} || "";
            $r2_port_nr = $port_name_hash{"$r2"} || "";
            if ( $r1_port_nr && $r2_port_nr ) {
				$dst_port_name = "range $r1_port_nr $r2_port_nr";
				$dst_port_name_found = 1;
            } else {
                print "Range (4): start or end port not found: $r1_port_nr ($r1) - $r2_port_nr ($r2)\n";
            }
		}
        my $port_dif = "";
        $port_dif = $r2_port_nr - $r1_port_nr if $r1_port_nr && $r2_port_nr;
#        print "TEST PORT DIFF: $port_dif - $r1_port_nr - $r2_port_nr\n" if $r1_port_nr && $r2_port_nr && $port_dif;
        if ( $port_dif && $port_dif <= 30 && $r1_port_nr && $r2_port_nr ) {
            for ( my $k = $r1_port_nr; $k <= $r2_port_nr; $k++ ) {

                my $acl = $action . " " . $protocol . " " . $src_acl  . " " . $src_operator . " " . $src_port . " " . $dst_acl . " " . $dst_operator . " " . $k . " " . $icmp_type;
                $acl =~ s/\s+/ /g;
                $acl = remove_whitespace_se("$acl");
                $acl = lc $acl;
                $acls_prepared{$acl} = $id;

#                print "TEST ACL: $acl dst_port (GEN)\n";
            }
        }
    } elsif ( $dst_port ) {
        $dst_port_name = $dst_port;
        if ( $dst_port !~ /range/i ) {
            $dst_port = $port_name_hash{"$dst_port"} || "";
        }
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
	$acl =~ s/\s+/ /g;
    $acl = remove_whitespace_se("$acl");

    my $acl_port_name = "";
    if ( $src_port_name_found || $dst_port_name_found ) {
        $acl_port_name = $action . " " . $protocol . " " . $src_acl  . " " . $src_operator . " " . $src_port_name . " " . $dst_acl . " " . $dst_operator . " " . $dst_port_name . " " . $icmp_type;
        $acl_port_name =~ s/\s+/ /g;
        $acl_port_name = remove_whitespace_se("$acl_port_name");
        $acl .= "%%" . $acl_port_name;
    }

    $acl = remove_whitespace_se("$acl");
    $acl = lc $acl;
    $acls_prepared{$acl} = $id;
    $acl_port_name = remove_whitespace_se("$acl_port_name");
    $acl_port_name = lc $acl_port_name;
    $acls_prepared{$acl_port_name} = $id if $acl_port_name;

#    print "TEST ACL: $acl\n";

	$j++;
}

#foreach my $key ( keys %acls_prepared ) {
#    print "TEST ACLS prepared: $key - $acls_prepared{$key}\n";
#}


my $csv_file_name;
my $csv_file;
my $export_string;

my @no_acl_acl_connnection;
my $exists = 0;
my $acl_con_acl_old = "";
my %all_con_nr;
my $i = 0;

my %acl_exists;
my %match_acls;

foreach my $acl_con_acl ( sort keys %acl_connections_prepared_range_acl ) {
    my $con_nr_arr_ref = $acl_connections_prepared_range_acl{$acl_con_acl};

    foreach my $con_nr ( @$con_nr_arr_ref ) {
        $all_con_nr{$con_nr}++;
    }

    if ( $acl_con_acl =~ /%%/ ) {
		$acl_con_acl =~ /^(.+)%%(.+)$/;
		my $acl1 = $1;
		my $acl2 = $2;
		print "Processing from ACL-Conection generated ACL: $acl1\n" if $debug;
		print "Processing from ACL-Conection generated ACL: $acl2\n" if $debug;
		if ( exists ($acls_prepared{"$acl1"}) ) {
			my $acl_nr = $acls_prepared{$acl1};
			foreach my $con_nr ( @$con_nr_arr_ref ) {
				print "EXISTS: Con.-Nr: $con_nr - ACL-NR.: $acls_prepared{$acl1} - $acl1\n" if $debug;
				$acl_exists{$con_nr}++;
				$match_acls{"$acl_nr"}++;
			}
		}
		if ( exists $acls_prepared{"$acl2"} ) {
			my $acl_nr = $acls_prepared{$acl1};
			foreach my $con_nr ( @$con_nr_arr_ref ) {
				print "EXISTS: Con.-Nr: $con_nr - ACL-NR.: $acls_prepared{$acl2} - $acl2\n" if $debug;
				$acl_exists{$con_nr}++;
				$match_acls{"$acl_nr"}++;
			}
		}

    } else {
		print "Processing from ACL-Conection generated ACL: $acl_con_acl\n" if $debug;
		if ( exists $acls_prepared{"$acl_con_acl"} ) {
			my $acl_nr = $acls_prepared{$acl_con_acl};
			foreach my $con_nr ( @$con_nr_arr_ref ) {
				print "EXISTS: Con.-Nr: $con_nr - ACL-NR.: $acls_prepared{$acl_con_acl} - $acl_con_acl\n" if $debug;
				$acl_exists{$con_nr}++;
				$match_acls{"$acl_nr"}++;
			}
		} else {
            # check 
        }
    }
}

$j = 0;
my %acl_found;
my %acl_updated;
foreach ( @acls ) {
	my $id = $acls[$j]->[0];
	$j++;

        next if exists $acl_updated{$id};

	if ( exists $match_acls{"$id"} ) {
	    $acl_found{$id}++;
	    delete($match_acls{"$id"});
	} else {
	    update_acl_match("$id", "") if ! $acl_updated{$id};
	}
        $acl_updated{$id}++;
}

$j = 0;
my %acl_found_updated;
foreach ( @acls ) {
    my $id = $acls[$j]->[0];
    $j++;
    next if exists $acl_found_updated{$id};
    print "UPDATE ACL LIST FOUND: $id\n" if $debug;
    if ( exists $acl_found{"$id"} ) {
        print "UPDATE ACL LIST: CON EXISTS: $id\n" if $debug;
	$acl_found_updated{$id}++;
        update_acl_match("$id", 1);
    }
}

foreach my $all_con_nr ( keys %all_con_nr ) {
	if ( exists $acl_exists{$all_con_nr} ) {
            print "ACL CON NR: $all_con_nr ($acl_exists{$all_con_nr} matches)\n" if $debug;
            update_connection_no_acl("$all_con_nr", "1");
	} else {
            update_connection_no_acl("$all_con_nr", "");
	}
}



####### Subroutines

sub get_db_parameter {
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or die "Can not open $priv_file: $!";
            while (<OUT>) {
                if ( $_ =~ /^sid=/ ) {
                    $_ =~ /^sid=(.*)$/;
                    $sid_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_host=/ ) {
                    $_ =~ /^bbdd_host=(.*)$/;
                    $bbdd_host_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_port=/ ) {
                    $_ =~ /^bbdd_port=(.*)$/;
                    $bbdd_port_gestioip = $1;
                } elsif ( $_ =~ /^user=/ ) {
                    $_ =~ /^user=(.*)$/;
                    $user_gestioip = $1;
                } elsif ( $_ =~ /^password=/ ) {
                    $_ =~ /^password=(.*)$/;
                    $pass_gestioip = $1;
                }
            }
            close OUT;
            last;
        }
    }

    return ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip);
}


sub mysql_connection {
#    print "TEST: DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip,$user_gestioip,$pass_gestioip\n";
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip)  or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}


sub get_acl_connections {
my ($client_id, $id_list ) = @_;
my (@values,$ip_ref);

my $dbh = mysql_connection();
my $qclient_id = $dbh->quote( $client_id );

my $id_expr = "";
if ( $id_list ) {
    $id_expr = " AND id IN ( $id_list )";
}


my $sth = $dbh->prepare("SELECT id, acl_nr, purpose, status, src_vlan, source, src, application_protocol, proto_id, src_port, bidirectional, dst_vlan, destination, dst, encrypted_base_proto, remark, client_id FROM acl_connection_list WHERE client_id=$qclient_id $id_expr ORDER BY acl_nr");
$sth->execute() or die "Can not executing statement: $DBI::errstr";
while ( $ip_ref = $sth->fetchrow_arrayref ) {
    push @values, [ @$ip_ref ];
}
$dbh->disconnect;
$sth->finish(  );
return @values;
}


sub get_protocol_hash {
my ( $client_id ) = @_;

my %values;
my $ip_ref;
my $dbh = mysql_connection();

my $sth = $dbh->prepare("SELECT protocol_nr, protocol_name FROM protocols")
 or die "Can not executing statement: $DBI::errstr";

$sth->execute() or die "Can not executing statement: $DBI::errstr";

while ( $ip_ref = $sth->fetchrow_hashref ) {
    my $number = $ip_ref->{protocol_nr};
    my $name = $ip_ref->{protocol_name};
    $values{$number} = "$name";
}

$sth->finish();
$dbh->disconnect;

return %values;
}

sub get_protocol_name_hash {
my ( $client_id ) = @_;

my %values;
my $ip_ref;
my $dbh = mysql_connection();

my $sth = $dbh->prepare("SELECT protocol_nr, protocol_name FROM protocols")
 or die "Can not executing statement: $DBI::errstr";

$sth->execute() or die "Can not executing statement: $DBI::errstr";

while ( $ip_ref = $sth->fetchrow_hashref ) {
    my $number = $ip_ref->{protocol_nr};
    my $name = $ip_ref->{protocol_name};
    $values{$name} = "$number";
}

$sth->finish();
$dbh->disconnect;

return %values;
}


sub get_wmask_from_bm {
my ( $bm ) = @_;

my %bm = get_bm_to_netmask();
my $mask = $bm{$bm};

my $mask_wild_packed = pack 'C4', split /\./, $mask;
my $mask_packed = ~$mask_wild_packed;
my $wmask = join '.', unpack 'C4', $mask_packed;

return $wmask;
}


sub remove_whitespace_se {
my ( $value ) = @_;
$value =~ s/^\s*//;
$value =~ s/\s*$//;
return $value;
}

sub get_port_hash {
    my ($key) = @_;

    $key = "" if ! $key;
    my $ip_ref;
    my $dbh = mysql_connection();

    my %hash;
    my $sth = $dbh->prepare("SELECT port_name, port_nr FROM ports");
    $sth->execute() or die "Can not executing statement: $DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $port_name = $ip_ref->{'port_name'};
        my $port_nr = $ip_ref->{'port_nr'};
        if ( $key eq "name" ) {
            push @{$hash{$port_name}},"$port_nr",
        } else {
            push @{$hash{$port_nr}},"$port_name",
        }
    }

    $sth->finish();
    $dbh->disconnect;

    return %hash;
}


sub get_port_number {
my ($client_id, $port_name) = @_;

my $dbh = mysql_connection();

my $qport_name = $dbh->quote( $port_name ) || "";

my $port_number = "";
my $sth = $dbh->prepare("SELECT port_nr FROM ports WHERE port_name=$qport_name");
$sth->execute() or die "Can not executing statement: $DBI::errstr";
$port_number = $sth->fetchrow_array;

$sth->finish();
$dbh->disconnect;

return $port_number;
}


sub get_port_name {
my ( $port_number) = @_;

my $dbh = mysql_connection();

my $qport_number = $dbh->quote( $port_number ) || "";

my $port_name = "";
my $sth = $dbh->prepare("SELECT port_name FROM ports WHERE port_nr=$qport_number");
$sth->execute() or die "Can not executing statement: $DBI::errstr";
$port_number = $sth->fetchrow_array;

$sth->finish();
$dbh->disconnect;

return $port_number;
}


sub get_acls {
my ( $client_id, $id ) = @_;
my (@values,$ip_ref);
my $dbh = mysql_connection();
my $qclient_id = $dbh->quote( $client_id );
my $qid = $dbh->quote( $id ) if $id;

my $filter = "";
$filter = " AND z.id=$qid" if $id;

#print "SELECT a.id, a.src, a.src_wmask, a.src_port, a.src_operator, a.dst, a.dst_wmask, a.dst_port, a.dst_operator, a.proto_id, p.protocol_name, a.action, a.icmp_type, a.client_id FROM acl_list a, protocols p WHERE a.client_id=$qclient_id AND a.proto_id=p.protocol_nr $filter ORDER BY id\n";
my $sth = $dbh->prepare("SELECT a.id, a.src, a.src_wmask, a.src_port, a.src_operator, a.dst, a.dst_wmask, a.dst_port, a.dst_operator, a.proto_id, p.protocol_name, a.action, a.icmp_type, a.client_id FROM acl_list a, protocols p WHERE a.client_id=$qclient_id AND a.proto_id=p.protocol_nr $filter ORDER BY id");
$sth->execute() or die "Can not executing statement: $DBI::errstr";
while ( $ip_ref = $sth->fetchrow_arrayref ) {
    push @values, [ @$ip_ref ];
}
$dbh->disconnect;
$sth->finish(  );
return @values;
}


sub compare_hash {
my ($A, $B) = @_;

my @aonly = ();
my @bfound = ();

foreach my $key_a (keys %$A) {
    next if ! $key_a;
    my $value_a = $A->{$key_a};
    if ( $key_a =~ /%%/ ) {
        $key_a =~ /^(.+)%%(.+)$/;
        my $acl1 = $1;
        my $acl2 = $2;
        if ( ! exists $B->{$acl1} && ! exists $B->{$acl2} && ! exists $B->{$key_a} ) {
            push (@aonly, $key_a);
        } else {
            push (@bfound, $value_a);
        }
    } else {
        if ( ! exists $B->{$key_a} ) {
            push (@aonly, $key_a);
        }
    }
}

return \@aonly;
}

sub get_bm_to_netmask {
	my %bm = (
		32 => '255.255.255.255',
		31 => '255.255.255.254',
		30 => '255.255.255.252',
		29 => '255.255.255.248',
		28 => '255.255.255.240',
		27 => '255.255.255.224',
		26 => '255.255.255.192',
		25 => '255.255.255.128',
		24 => '255.255.255.0',
		23 => '255.255.254.0',
		22 => '255.255.252.0',
		21 => '255.255.248.0',
		20 => '255.255.240.0',
		19 => '255.255.224.0',
		18 => '255.255.192.0',
		17 => '255.255.128.0',
		16 => '255.255.0.0',
		15 => '255.254.0.0',
		14 => '255.252.0.0',
		13 => '255.248.0.0',
		12 => '255.240.0.0',
		11 => '255.224.0.0',
		10 => '255.192.0.0',
		9 => '255.128.0.0',
		8 => '255.0.0.0'
	);
	return %bm;
}

sub get_netmask_to_bm {
	my %mask = (
		'255.255.255.255' => 32,
		'255.255.255.254' => 31,
		'255.255.255.252' => 30,
		'255.255.255.248' => 29,
		'255.255.255.240' => 28,
		'255.255.255.224' => 27,
		'255.255.255.192' => 26,
		'255.255.255.128' => 25,
		'255.255.255.0' => 24,
		'255.255.254.0' => 23,
		'255.255.252.0' => 22,
		'255.255.248.0' => 21,
		'255.255.240.0' => 20,
		'255.255.224.0' => 19,
		'255.255.192.0' => 18,
		'255.255.128.0' => 17,
		'255.255.0.0' => 16,
		'255.254.0.0' => 15,
		'255.252.0.0' => 14,
		'255.248.0.0' => 13,
		'255.240.0.0' => 12,
		'255.224.0.0' => 11,
		'255.192.0.0' => 10,
		'255.128.0.0' => 9,
		'255.0.0.0' => 8
	);
	return %mask;
}

sub update_connection_no_acl {
	my ( $acl_nr, $no_acl) = @_;

	$no_acl = 0 if ! $no_acl;

	my $dbh = mysql_connection();

	my $qacl_nr = $dbh->quote( $acl_nr ) || "";
	my $qno_acl = $dbh->quote( $no_acl ) || "";
	my $qclient_id = $dbh->quote( $client_id ) || "";

	print "UPDATE acl_connection_list SET no_acl=$qno_acl WHERE id=$qacl_nr\n";
	my $sth = $dbh->prepare("UPDATE acl_connection_list SET no_acl=$qno_acl WHERE acl_nr=$qacl_nr");
	$sth->execute()  or die "Can not executing statement: $DBI::errstr";

	$sth->finish();
	$dbh->disconnect;
}

sub update_acl_match {
	my ( $id, $con_exists ) = @_;

	if ( $con_exists ) {
		$con_exists = 1;
	} else {
		$con_exists = 0;
	}

	my $dbh = mysql_connection();

	my $qid = $dbh->quote( $id ) || "";
	my $qcon_exists = $dbh->quote( $con_exists ) || "";

	print "UPDATE acl_list SET con_exists=$qcon_exists WHERE id=$qid\n";
	my $sth = $dbh->prepare("UPDATE acl_list SET con_exists=$qcon_exists WHERE id=$qid");
	$sth->execute()  or die "Can not executing statement: $DBI::errstr";

	$sth->finish();
	$dbh->disconnect;
}

sub get_netmask_from_wildcard {
	my ( $mask_wild_dotted ) = @_;
	my $mask_wild_packed = pack 'C4', split /\./, $mask_wild_dotted;
	my $mask_norm_packed = ~$mask_wild_packed;
	my $mask_norm_dotted = join '.', unpack 'C4', $mask_norm_packed;

	return $mask_norm_dotted;
}
