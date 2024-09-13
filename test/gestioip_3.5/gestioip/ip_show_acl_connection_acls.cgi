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


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{acl_connection_acl_message}","$vars_file");

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	$align1="align=\"right\"";
	$ori="right";
}


my @acl_connections=$gip->get_acl_connections("$client_id");
my %protocols = $gip->get_protocol_hash("$client_id");

my @acl_connections_prepared;
my @acls_prepared;

my %acl_connections_prepared;
my %acls_prepared;

my %acl_connection_ports;
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
        my $protocol = "IP";
        $protocol = $protocols{$proto_id} || "" if $proto_id;

        my $src_port = $acl_connections[$j]->[9] || "";
        my $bidirectional = $acl_connections[$j]->[10] || "";
        my $dst_vlan = $acl_connections[$j]->[11] || "";
        my $destination = $acl_connections[$j]->[12] || "";
        my $dst = $acl_connections[$j]->[13] || "";

		if ( $src =~ /\// ) {
			$src =~ /^(.+)\/(.+)$/;
			my $src_ip = $1;
			my $bm = $2;
			my $src_wmask = $gip->get_wmask_from_bm("$bm");
			$src = "$src_ip $src_wmask";
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
        } elsif ( $dst =~ /^any$/ ) {
            # do nothing
		} else {
			$dst = "host $dst";
		}

		my @src_port = split ",", $src_port;


		my $port = "";
		foreach my $found_port ( @src_port ) {
			$found_port = $gip->remove_whitespace_se("$found_port");

			if ( $found_port =~ /range/i ) {
				$found_port =~ s/R/r/;
				$found_port =~ s/-/ /;
				$port = $found_port;
                push @{$acl_connection_ports{$port}},"$acl_nr";
			} elsif ( $found_port =~ /^\d+-\d+$/i ) {
				$found_port =~ s/-/ /;
                $port = "range " . $found_port;
			} elsif ( $found_port =~ /^any$/i ) {
                $port = "";
			} elsif ( $found_port =~ /^icmp$/i ) {
                $port = "";
                $protocol = "ICMP" if $protocol eq "IP"; 
#                print "TEST" . $acl_nr . $found_port . " " . " " . $protocol . " " .  $src . " " .  $dst . " " .  $port . "<br>\n";
			} elsif ( $found_port !~ /^\d+$/ ) {
				$port = $gip->get_port_number("$client_id", "$found_port") || "";
                if ( ! $port ) {
                    # TEST: print list of not found ports....
                    $port = "<i>unknown port: $found_port</i>";
#                    next;
                }
                push @{$acl_connection_ports{$port}},"$acl_nr";
				$port = "eq " . $port;
			} else {
                push @{$acl_connection_ports{$found_port}},"$acl_nr" if $found_port;
				$port = "eq " . $found_port;
			}


			my $c_acl = "permit " . $protocol . " " .  $src . " " .  $dst . " " .  $port;
			$c_acl =~ s/\s+/ /g;
			$c_acl = $gip->remove_whitespace_se("$c_acl");
            $acl_connections_prepared{$c_acl} = $acl_nr;

			if ($bidirectional ) {
				my $c_acl_bi = "permit " . $protocol . " " .  $src . " " .  $port . " " .  $dst;
				$c_acl_bi =~ s/\s+/ /g;
                $c_acl_bi = $gip->remove_whitespace_se("$c_acl_bi");
                $acl_connections_prepared{$c_acl_bi} = $acl_nr;
			}
		}

		$j++;
}


print "<br><table border=\"1\" cellpadding=\"4\">\n";
print "<tr><td><b>$$lang_vars{ACL_nr_message}</b></td><td><b>$$lang_vars{acl_message}</b></td></tr>\n";
foreach (sort {$acl_connections_prepared{$a} <=> $acl_connections_prepared{$b}} (keys %acl_connections_prepared)) {
        print "<tr><td>$acl_connections_prepared{$_}</td><td>$_</td></tr>\n" if exists $acl_connections_prepared{$_};
}
print "</table>\n";


$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

