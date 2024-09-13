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
use CGI;
use lib './modules';
use GestioIP;
use POSIX qw(strftime);
use XML::Simple;
use JSON;
use Data::Dumper;
use Net::IP;
use Net::IP qw(:PROC);

my $q = CGI->new();
my %args;
$args{'format'} = "xml";
my $args = \%args;
my $gip  = GestioIP->new($args);

my $API_VERSION = "3.5.3";

#$CGI::LIST_CONTEXT_WARN = 0;

my $error     = "";
my $vars_file = "./vars/vars_en";

my $output_type = $q->param("output_type") || "xml";
my $output_type_header = "text/xml";
$output_type_header = "application/json" if $output_type eq "json";

my ( $dangerous_character_detected, $dangerous_parameter ) = check_characters();
if ($dangerous_character_detected) {
    if ($dangerous_parameter) {
        $error = "UNSUPPORTED CHARACTER IN ATTRIBUT-NAMES DETECTED";
    }
    else {
        $error = "UNSUPPORTED CHARACTER DETECTED";
    }
    exit_error(
        error              => "$error",
        main_container     => "Result",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}
if ( $output_type !~ /^(xml|json)$/ ) {
    $error = "UNSUPPORTED output_type. SUPPORTED VALUES: \"xml|json\"";
    exit_error(
        error              => "$error",
        main_container     => "Result",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}

if ( $q->param("ip_version") && $q->param("ip_version") !~ /^(v4|v6)$/ ) {
    $error = "UNSUPPORTED ip_version. SUPPORTED VALUES: \"v4|v6\"";
    exit_error(
        error              => "$error",
        main_container     => "Result",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}

my $request_type_param = $q->param("request_type") || "";
my $client_name        = $q->param("client_name")  || "";

my $all_request_types =
"listNetworks";
my $valid_output_types = "xml|json";

if ( !$request_type_param ) {
    my %attribs = (
        'request_type' => "$all_request_types",
        'client_name'  => 'CLIENT_NAME'
    );
    print_help(
        attribs            => \%attribs,
        main_container     => "help",
        http_status        => "200 OK",
        output_type_header => "$output_type_header",
    );
}
if ( $request_type_param eq "version" ) {
    print_version(
        main_container     => "versionResult",
        http_status        => "200 OK",
        output_type_header => "$output_type_header",
    );
}


my @param_names = $q->param;
my %param_names;
foreach (@param_names) {
    $param_names{$_}++;
}
my $num_params = keys %param_names;

my ( $ip_param, $hostname_param, $host_id_param, $ip_version, $ip_int,
    $main_container );

$main_container = $request_type_param . "Result";

if ( $request_type_param !~ /^($all_request_types)$/ ) {
    if ( !$request_type_param ) {
        $error .= "ERROR: PARAMETER request_type MISSING";
    }
    else {
        $error .= "ERROR: INVALID request_type: $request_type_param";
    }
    exit_error(
        error              => "$error",
        main_container     => "Result",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}
if ( !$client_name && $request_type_param !~ /[Hh]elp|listClients$/ ) {
    $error .= "ERROR: PARAMETER client_name MISSING";
    exit_error(
        error              => "$error",
        main_container     => "$main_container",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}

my $client_id = "";
my %clients_hash;
if ( $client_name =~ /^\d$/ ) {
    $client_id = $client_name;
} else {
    $client_id = getClientID("$client_name") if $client_name;
}

my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";

my @custom_columns;
my %cc_name_whitespace_hash;


if ( $request_type_param =~ /Network/ ) {
    if ( $request_type_param =~
/^(readNetwork|createNetwork|updateNetwork|freeNetworkAddresses|reserveFirstFreeNetworkAddress|firstFreeNetworkAddress|usedNetworkAddresses|listNetworks|output_type)$/
        && !$client_name )
    {
        $error .= "ERROR: PARAMETER client_name MISSING";
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    if ( $request_type_param =~
/^(readNetwork.*|deleteNetwork.*|freeNetworkAddresses.*|reserveFirstFreeNetworkAddress.*|usedNetworkAddresses*|firstFreeNetworkAddress.*)$/
      )
    {
        if ( $request_type_param =~ /^(reserveFirstFreeNetworkAddress)$/ ) {
            @custom_columns = $gip->get_custom_host_columns("$client_id");
        } else {
            @custom_columns = $gip->get_custom_columns("$client_id");
        }
        my $cc_names = "";
        my @cc_names = ();
        if ( $custom_columns[0] ) {
            my $n = 0;
            foreach my $cc_ele (@custom_columns) {
                my $cc_name = $custom_columns[$n]->[0];
                $cc_name = "vlan_id" if $cc_name eq "vlan";
                $cc_names .= "|new_" . $cc_name;
                push @cc_names, "$cc_name";
                $n++;

                createCCWhitespaceHash("$cc_name");
            }
            $cc_names =~ s/^\|//;
        }

        for my $key ( keys %param_names ) {
            my $filter = "";
            if ( $request_type_param =~ /^(readNetwork|deleteNetwork)$/ ) {
                $filter =
                  "ip|client_name|request_type|network_type|BM|output_type";
            }
            elsif ( $request_type_param =~ /^(usedNetworkAddresses)$/ ) {
                $filter = "ip|client_name|request_type|output_type|include_id|no_csv";
            }
            elsif ( $request_type_param =~ /^(reserveFirstFreeNetworkAddress)$/ ) {
                $filter = "ip|client_name|request_type|output_type|ip|new_hostname|new_descr|new_site|new_cat|new_comment|new_update_type|new_int_admin|${cc_names}";
                # overwrite custom network with custom host columns
                @custom_columns = $gip->get_custom_host_columns("$client_id");
            }
            else {
                $filter = "ip|client_name|request_type|output_type";
            }

            if ( $key !~ /^($filter)$/ ) {
                $error .= "ERROR: UNKNOWN PARAMETER: $key";
                exit_error(
                    error              => "$error",
                    main_container     => "$main_container",
                    http_status        => "400 Bad Request",
                    output_type_header => "$output_type_header",
                );
            }
        }
        if ( $request_type_param =~ /Help/ ) {
            my %attribs;
            my $request_type_attribs = $request_type_param;
            $request_type_attribs =~ s/Help//;
            %attribs = (
                'request_type' => "$request_type_attribs",
                'output_type'  => "$valid_output_types",
                'client_name'  => 'CLIENT_NAME',
                'ip'           => 'IP_ADDRESS'
            );
            if ( $request_type_param =~ /^(deleteNetworkHelp)$/ ) {
                $attribs{BM}           = "BM_OF_THE_NETWORK_TO_DELETE";
                $attribs{network_type} = "root|non-root";
            }
            elsif ( $request_type_param =~ /^(readNetworkHelp)$/ ) {
                $attribs{BM}           = "BM";
                $attribs{network_type} = "root|non-root";
            }
            elsif ( $request_type_param =~ /^(reserveFirstFreeNetworkAddress)$/ ) {
				%attribs = (
					'request_type'    => "$request_type_attribs",
					'output_type'     => "$valid_output_types",
					'client_name'     => 'CLIENT_NAME',
					'ip'              => 'IP_ADDRESS',
					'new_hostname'    => "NEW_HOSTNAME",
					'new_descr'       => 'NEW HOST DESCRIPTION',
					'new_site'        => 'NEW SITE',
					'new_cat'         => 'NEW CATEGORY',
					'new_comment'     => 'NEW COMMENT',
					'new_update_type' => 'man|dns|ocs',
					'new_int_admin'   => 'y|n'
				);
				foreach (@cc_names) {
					$attribs{"$_"} = "NEW VALUE";
				}
			}

            print_help(
                attribs            => \%attribs,
                main_container     => "$main_container",
                http_status        => "200 OK",
                output_type_header => "$output_type_header",
            );
        }

        $ip_param = $q->param("ip") || "";

        if ( !$ip_param ) {
            $error .= "ERROR: PARAMETER ip MISSING";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }

        ( $ip_param, $ip_int, $ip_version ) = check_ip("$ip_param");

        if ( $request_type_param eq "readNetwork" ) {

            readNetwork(
                main_container => "readNetworkResult",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }
        elsif ( $request_type_param eq "deleteNetwork" ) {
            deleteNetwork(
                main_container => "readNetworkResult",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }
        elsif ( $request_type_param =~
            /^(freeNetworkAddresses|firstFreeNetworkAddress)$/ )
        {
            freeNetworkAdds(
                main_container => "freeNetworkAddresses",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }
        elsif ( $request_type_param =~
            /^(reserveFirstFreeNetworkAddress)$/ )
        {
            reserveFirstFreeNetworkAdds(
                main_container => "reserveFirstFreeNetworkAddresses",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }
        elsif ( $request_type_param =~
            /^(usedNetworkAddresses)$/ )
        {
            usedNetworkAdds(
                main_container => "usedNetworkAddresses",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }

    }
    elsif ( $request_type_param =~ /^(updateNetwork.*|createNetwork.*)$/ ) {
        @custom_columns = $gip->get_custom_columns("$client_id");

        my $cc_names = "";
        my @cc_names = ();
        if ( $custom_columns[0] ) {
            my $n = 0;
            foreach my $cc_ele (@custom_columns) {
                my $cc_name = $custom_columns[$n]->[0];
                $cc_name = "vlan_id" if $cc_name eq "vlan";
                $cc_names .= "|new_" . $cc_name;
                push @cc_names, "$cc_name";
                $n++;

                createCCWhitespaceHash("$cc_name");
            }
            $cc_names =~ s/^\|//;
        }

        for my $key ( keys %param_names ) {
            if ( $key !~
/^(ip|client_name|request_type|BM|new_BM|new_descr|new_site|new_cat|new_comment|new_sync|new_dyn_dns_updates|network_type|output_type|${cc_names})$/
              )
            {
                $error .= "ERROR: UNKNOWN PARAMETER: $key";
                exit_error(
                    error              => "$error",
                    main_container     => "$main_container",
                    http_status        => "400 Bad Request",
                    output_type_header => "$output_type_header",
                );
            }
        }
        if ( $request_type_param =~ /Help/ ) {
            my %attribs;
            my $request_type_attribs = $request_type_param;
            $request_type_attribs =~ s/Help//;
            %attribs = (
                'request_type' => "$request_type_attribs",
                'output_type'  => "$valid_output_types",
                'network_type' => 'root|non-root',
                'client_name'  => 'CLIENT_NAME',
                'ip'           => 'IP_ADDRESS',
                'new_BM'       => "NEW BITMASK",
                'new_descr'    => "NEW DESCRIPTION",
                'new_site'     => "NEW SITE",
                'new_cat'      => "NEW CATEGORY",
                'new_comment'  => "NEW COMMENT",
                'new_sync'     => 'y|n'
            );
            if ( $request_type_param =~ /^updateNetwork.*$/ ) {
                $attribs{'network_type'} = "BM";
            }
            foreach (@cc_names) {
                if ( $_ eq "vlan_id" ) {
                    $attribs{"$_"} = "VLAN_ID";
                }
                else {
                    $attribs{"$_"} = "NEW VALUE";
                }
            }

            print_help(
                attribs            => \%attribs,
                main_container     => "$main_container",
                http_status        => "200 OK",
                output_type_header => "$output_type_header",
            );
        }

        $ip_param = $q->param("ip") || "";

        if ( !$ip_param ) {
            $error .= "ERROR: PARAMETER ip MISSING";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }

        ( $ip_param, $ip_int, $ip_version ) = check_ip("$ip_param");

        if ( $request_type_param eq "updateNetwork" ) {
            updateNetwork(
                main_container => "updateNetworkResult",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }
        elsif ( $request_type_param eq "createNetwork" ) {
            createNetwork(
                main_container => "updateNetworkResult",
                ip_param       => "$ip_param",
                ip_int         => "$ip_int",
            );
        }

    }
    elsif ( $request_type_param =~ /^(listNetworks.*|firstFreeNetwork.*)$/ ) {
		my ($locs_ro_perm, $locs_rw_perm, $perm_error);
		$locs_ro_perm=$locs_rw_perm=$perm_error="";
		if ( $user_management_enabled eq "yes" ) {

#			$client_id = $gip->get_allowed_client_perm("$client_id","$vars_file") || $client_id;

			my $required_perms="read_net_perm";
			($locs_ro_perm, $locs_rw_perm, $perm_error, $client_id) = $gip->check_perms (
				client_id=>"$client_id",
				vars_file=>"$vars_file",
				required_perms=>"$required_perms",
				from_api=>"1",
                return_client_id=>"1",
			);

			if ( $perm_error ) {
				exit_error(
					error              => "$perm_error",
					main_container     => "Result",
					http_status        => "400 Bad Request",
					output_type_header => "$output_type_header",
				);
			}
		}

        if ( $request_type_param =~ /^(firstFreeNetwork.*)$/ && ! $ip_version ) {
            if ( $q->param("rootnet_ip") =~ /^\d{1,3}\./ ) {
                $ip_version = "v4";
            } else {
                $ip_version = "v6";
            }
        }

        @custom_columns = $gip->get_custom_columns("$client_id");

        my $cc_names = "";
        my @cc_names = ();
        if ( $custom_columns[0] ) {
            my $n = 0;
            foreach my $cc_ele (@custom_columns) {
                my $cc_name = $custom_columns[$n]->[0];
                $cc_name = "vlan_id" if $cc_name eq "vlan";
                $cc_names .= "|" . $cc_name;
                push @cc_names, "$cc_name";
                $n++;

                createCCWhitespaceHash("$cc_name");
            }
            $cc_names =~ s/^\|//;
        }

        for my $key ( keys %param_names ) {
            my $filter = "";
            if ( $request_type_param =~ /^(listNetworks.*)$/ ) {
                $filter =
"client_name|request_type|filter|description|site|category|comment|network_type|output_type|limit|include_id|ip_version|no_csv|page|${cc_names}";

                check_filter( filter => "$filter", );
            }
            elsif ( $request_type_param =~ /^(firstFreeNetwork.*)$/ ) {
                $filter =
"ip|client_name|request_type|rootnet_ip|rootnet_BM|BM|output_type";
            }
            if ( $key !~ /^($filter)$/ ) {
                $error .= "ERROR: UNKNOWN PARAMETER: $key";
                exit_error(
                    error              => "$error",
                    main_container     => "$main_container",
                    http_status        => "400 Bad Request",
                    output_type_header => "$output_type_header",
                );
            }
        }
        if ( $request_type_param =~ /Help/ ) {
            my %attribs;
            my $request_type_attribs = $request_type_param;
            $request_type_attribs =~ s/Help//;
            %attribs = (
                'request_type' => "$request_type_attribs",
                'output_type'  => "$valid_output_types",
                'client_name'  => 'CLIENT_NAME'
            );
            if ( $request_type_param =~ /^(listNetworksHelp)$/ ) {
                $attribs{filter} =
                  "attributeA::value1|value2,attributeB::value";
                $attribs{ip_version} = "v4|v6";
                $attribs{network_type} = "root|non-root";
                $attribs{no_csv} = "no|yes";
                $attribs{limit} = "0-9999";
                $attribs{page} = "0-9999 (requires limit attribute)";
            }
            elsif ( $request_type_param =~ /^(firstFreeNetworkHelp)$/ ) {
                $attribs{rootnet_ip} = "ROOTNET IP";
                $attribs{rootnet_BM} = "ROOTNET BM";
                $attribs{BM}         = "BM OF THE FIRST FREE NETWORK";
                $attribs{region} =
                  "REGION (requires custom network column \"region\")";
                $attribs{city} =
                  "CITY (requires custom network column \"city\")";
                $attribs{type} =
"TYPE (requires custom network column \"type\"; allowed values: \"public\" or \"privat\")";
            }
            print_help(
                attribs            => \%attribs,
                main_container     => "$main_container",
                http_status        => "200 OK",
                output_type_header => "$output_type_header",
            );
        }

        my $BM_param = $q->param("BM") || "";

        if ( $request_type_param =~ /^(firstFreeNetwork)$/ ) {

            if ( !$BM_param ) {
                $error .= "ERROR: PARAMETER BM MISSING";
                exit_error(
                    error              => "$error",
                    main_container     => "$main_container",
                    http_status        => "400 Bad Request",
                    output_type_header => "$output_type_header",
                );
            }

        }

        if ( $request_type_param eq "listNetworks" ) {
            listNetworks(
				main_container => "listNetworksResult",
				locs_ro_perm => "$locs_ro_perm",
				locs_rw_perm => "$locs_rw_perm",
			 );
        } elsif ( $request_type_param eq "firstFreeNetwork" ) {
            firstFreeNetwork(
                main_container => "firstFreeNetworkResult",
                BM             => "$BM_param",
                ip_version     => "$ip_version",
            );
        }
    }

} else {
    $error = "UNSUPPORTED request_type";
    exit_error(
        error              => "$error",
        main_container     => "Result",
        http_status        => "400 Bad Request",
        output_type_header => "$output_type_header",
    );
}


# subroutines

sub listNetworks {
	my %args = @_;

    my $locs_ro_perm     = $args{"locs_ro_perm"}         || "";
    my $locs_rw_perm     = $args{"locs_rw_perm"}         || "";

    my $filter       = $q->param("filter")       || "";
    my $network_type = $q->param("network_type") || "non_root";
    my $ip_version   = $q->param("ip_version")   || "v4";
    my $include_id   = $q->param("include_id")   || "no";
    my $limit   = $q->param("limit")   || 0;
    my $page   = $q->param("page")   || 0;
    my $no_csv   = $q->param("no_csv") || "";

    my $start = 1;
    my $end = $limit;


    if ( $limit !~ /^\d{1,4}/ ) {
        $error .= "ERROR: limit MUST BE AN INTEGER BETWEEN 0 AND 9999";
    }

    if ( $page && ! $limit ) {
        $error .= "ERROR: page OPTION REQUIRES THE limit OPTION";
    }

    if ( $page !~ /^\d{1,4}/ ) {
        $error .= "ERROR: page MUST BE AN INTEGER BETWEEN 0 AND 9999";
    } elsif ( $page != 0 ) {
        $start = ($limit * $page) + 1;
        $end = $start + $limit - 1;
    }


    if ( $network_type ne "root" && $network_type ne "non_root" ) {
        $error .= "ERROR: INVALID VALUE FOR network_type";
    }

    if ( $include_id !~ /^(yes|no)$/i ) {
        $error .= "ERROR: INVALID VALUE FOR include_id";
    }

    if ( $error ) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    my %filter;

    my $match_all1 = 0;
    # MATCH_ALL filter founds all sub strings
    if ( $filter =~ /\[\[MATCH_ALL\]\]/ ) {
        $filter =~ s/\[\[MATCH_ALL\]\]//;
        $match_all1 = 1;
    }

    my @filter = split( ",", $filter );

    foreach (@filter) {
        $_ =~ /^(.+)::(.*)$/;
        my $filter_cat = $1;
        my $filter_arg = $2 || "";
        next if !$filter_cat;
        $filter{$filter_cat} = $filter_arg;
    }

    my $values_redes = $gip->get_redes_hash( "$client_id", "$ip_version", "return_int", "1" );

    my @custom_columns = $gip->get_custom_columns("$client_id");

    #name,id,client_id
    my %custom_columns_values = $gip->get_custom_column_values_red("$client_id");
    my @cc_ids = $gip->get_custom_column_ids("$client_id");
    my $custom_column_val;
    my %custom_columns;

    foreach my $cc_ele (@custom_columns) {
        my $name = $cc_ele->[0];
        my $id   = $cc_ele->[1];
        $custom_columns{$id} = $name;
    }

    my %values_redes_found;
    my @predef_columns = ( "site", "category", "comment", "descr" );

    my @listNetworks;
    my %network_values;
    my @network_order;
	my $loc_hash=$gip->get_loc_hash("$client_id");

	my $i = 1;
    foreach my $key ( sort { Math::BigInt->new($values_redes->{$a}[8]) <=> Math::BigInt->new($values_redes->{$b}[8]) } keys %$values_redes ) {

        my $red_num = $key;
        my $red     = ${$values_redes}{$key}->[0];
        my $rootnet = ${$values_redes}{$key}->[9];
        my $red_int = ${$values_redes}{$key}->[8];
        $red_int = Math::BigInt->new("$red_int");
        my $BM         = ${$values_redes}{$key}->[1];
        my $loc        = ${$values_redes}{$key}->[3] || "";
        my $cat        = ${$values_redes}{$key}->[4] || "";
        my $sync        = ${$values_redes}{$key}->[5] || "n";
        my $comment    = ${$values_redes}{$key}->[6] || "";
        my $ip_version = ${$values_redes}{$key}->[7];
        my $descr      = ${$values_redes}{$key}->[2] || "";
        my $parent_network_id      = ${$values_redes}{$key}->[10] || "";
        $cat     = "" if $cat eq "NULL";
        $loc     = "" if $loc eq "NULL";


		# Check permissions
		my $loc_id = $loc_hash->{"$loc"} || "-1";
        my $has_loc_rw_perm = 0;
		if ( $user_management_enabled eq "yes" && $loc_id != "-1" ) {
			if ( $locs_rw_perm eq "9999" || $locs_rw_perm =~ /^$loc_id$/ || $locs_rw_perm =~ /^${loc_id}_/ || $locs_rw_perm =~ /_${loc_id}$/ || $locs_rw_perm =~ /_${loc_id}_/ ) {
				# user has rw perm
				$has_loc_rw_perm = 1;
			}

			if ( $locs_ro_perm eq "9999" || $locs_ro_perm =~ /^$loc_id$/ || $locs_ro_perm =~ /^${loc_id}_/ || $locs_ro_perm =~ /_${loc_id}$/ || $locs_ro_perm =~ /_${loc_id}_/ ) {
				# user has ro perm
			} elsif ( ! $has_loc_rw_perm ) {
				# user has no permission for this site - skip entry
				next;
			}
		} else {
            $has_loc_rw_perm = 1;
        }

        $descr   = "" if $descr eq "NULL";
        $comment = "" if $comment eq "NULL";
        if ( $no_csv =~ /^yes$/i ) {
            # escape comas
            $loc =~ s/,/\\,/g;
            $cat =~ s/,/\\,/g;
            $descr =~ s/,/\\,/g;
            $comment =~ s/,/\\,/g;
        }

        $red = ip_compress_address ($red,6) if $ip_version eq "v6";

        if ( $network_type eq "root" ) {
            next if $rootnet != 1;
        } else {
            next if $rootnet == 1;
        }

        my %predef_columns = (
            site        => "$loc",
            category    => "$cat",
            description => "$descr",
            comment     => "$comment",
        );

        my $netfilter = "";


#        for my $key ( keys %filter ) {
#            my $filter_value = $filter{$key};
#
#            my @filter_values = split( /\|/, $filter_value );
#            my $anz_filter_values = scalar(@filter_values);
#
#            while ( my ( $pc_key, $pc_value ) = each(%predef_columns) ) {
#                if ( $key eq $pc_key ) {
#                    if ( $anz_filter_values == 0 || $anz_filter_values == 1 ) {
#                        $values_redes_found{$red_int} = $key;
#                        if ($netfilter) {
#                            if ($match_all1) {
#                                $netfilter .= " && \"$pc_value\" =~ /$filter_value/i";
#                            } else {
#                                $netfilter .= " && \"$filter_value\" eq \"$pc_value\"";
#                            }
#                        } else {
#                            if ($match_all1) {
#                                $netfilter = "\"$pc_value\" =~ /$filter_value/i";
#                            } else {
#                                $netfilter = "\"$filter_value\" eq \"$pc_value\"";
#                            }
#                        }
#                    }
#                    else {
#                        my $netfilter_tmp = "";
#                        foreach (@filter_values) {
#                            $netfilter_tmp .= " || \"$pc_value\" eq \"$_\"";
#                        }
#                        $netfilter_tmp =~ s/^ \|\| //;
#                        if ($netfilter) {
#                            $netfilter .= " && ( $netfilter_tmp )"
#                              if $netfilter_tmp;
#                        }
#                        else {
#                            $netfilter = "( $netfilter_tmp )" if $netfilter_tmp;
#                        }
#                    }
#                    next;
#                }
#            }
#        }

#        my $cc_value_show = "";
#        my %cc_hash;
#
#        foreach (@cc_ids) {
#            my $id = $_->[0];
#
#
#            my $cc_name = $custom_columns{$id};
#            my $cc_value = "";
#            if ( $custom_columns_values{"${id}_${red_num}"} ) {
#                $cc_value = $custom_columns_values{"${id}_${red_num}"};
#                # escape comas
#                $cc_value =~ s/,/\\,/g if ! $no_csv;
#                $cc_value =~ s/(&)/$1amp;/g;
#            }
#            $cc_value_show .= ",$cc_value";
#
#            $cc_hash{$cc_name} = $cc_value;
#
#            for my $key ( keys %filter ) {
#
#                if ( $key ne $cc_name ) {
#                    next;
#                }
#
#                my $filter_value = $filter{$key};
#
#                my @filter_values = split( /\|/, $filter_value );
#                my $anz_filter_values = scalar(@filter_values);
#
#                if ( $anz_filter_values == 0 || $anz_filter_values == 1 ) {
#                    if ($netfilter) {
#						if ($match_all1) {
#							$netfilter .= " && \"$cc_value\" =~ /$filter_value/i";
#						} else {
#							$netfilter .= " && \"$filter_value\" eq \"$cc_value\"";
#						}
#                    }
#                    else {
#						if ($match_all1) {
#							$netfilter = "\"$cc_value\" =~ /$filter_value/i";
#						} else {
#							$netfilter = "\"$filter_value\" eq \"$cc_value\"";
#						}
#                    }
#                } else {
#                    my $netfilter_tmp = "";
#                    foreach (@filter_values) {
#						if ($match_all1) {
#							$netfilter = " || $cc_value =~ /$_/i";
#						} else {
#							$netfilter = " || \"$cc_value\" eq \"$_\"";
#						}
#                    }
#                    $netfilter_tmp =~ s/^ \|\| //;
#                    if ($netfilter) {
#                        $netfilter .= " && ( $netfilter_tmp )" if $netfilter_tmp;
#                    } else {
#                        $netfilter = "$netfilter_tmp" if $netfilter_tmp;
#                    }
#                }
#            }
#        }

#        my $cc_hash = \%cc_hash;

        if ($filter) {
            if ( eval($netfilter) ) {
                $i++;
                next if $start && $i <= $start;
                if ( $include_id =~ /^yes$/i ) {
                    push @listNetworks,"$red_num,$red/$BM,$loc,$cat,$comment,${descr}";
					push @{$network_values{$red_num}},"$red","$BM","$descr","$loc","$cat","$sync","$comment","$ip_version","$rootnet","","$parent_network_id";
                    push @network_order,"$red_num";

                } else {
                    push @listNetworks,"$red/$BM,$loc,$cat,$comment,${descr}";
					push @{$network_values{$red_num}},"$red","$BM","$descr","$loc","$cat","$sync","$comment","$ip_version","$rootnet","","$parent_network_id";
                    push @network_order,"$red_num";
                }
                last if $end && $i > $end;
				$i++;
            }
        } else {
            $i++;
            next if $start && $i <= $start;
            if ( $include_id =~ /^yes$/i ) {
                push @listNetworks, "$red_num,$red/$BM,$loc,$cat,$comment,${descr}";
                push @{$network_values{$red_num}},"$red","$BM","$descr","$loc","$cat","$sync","$comment","$ip_version","$rootnet","","$parent_network_id";
                push @network_order,"$red_num";
            } else {
                push @listNetworks, "$red/$BM,$loc,$cat,$comment,${descr}";
                push @{$network_values{$red_num}},"$red","$BM","$descr","$loc","$cat","$sync","$comment","$ip_version","$rootnet","","$parent_network_id";
                push @network_order,"$red_num";
            }
            last if $end && $i > $end;
        }
    }

    my $listNetworks = \@listNetworks;
    my $network_values = \%network_values;
    my $network_order = \@network_order;

    my $output = "";
    my $ret    = "";

    $ret = printHeaders(
        output_type_header => "$output_type_header",
        output_type        => "$output_type",
        main_container     => "$main_container",
    ) || "";
    $output .= $ret if $ret;

    if ( $no_csv =~ /^yes$/i ) {
        $ret = printXmlBodyNetworkList_noCSV(
            network_values => $network_values,
            network_order => $network_order,
        ) || "";
    } else {
        $ret = printXmlBodyNetworkList(
            listNetworks => $listNetworks,
        ) || "";
    }
    $output .= $ret if $ret;

    printResponse(
        output         => "$output",
        main_container => "$main_container",
    );
}


sub printHtmlHeader {
    my %args = @_;

    my $type = $args{type} || "";
    $type = "-type => \"$type\"" if $type;
    my $allow = $args{allow} || "";
    $allow = "-allow => \"$allow\"" if $allow;
    my $location = $args{location} || "";
    $location = "-location => \"$location\"" if $location;
    my $status = $args{status} || "";
    $status = "-status => \"$status\"" if $status;

    my $header_params = $type . "," . $allow . "," . $location . "," . $status;
    $header_params =~ s/^,//;
    $header_params =~ s/,$//;

    print $q->header( eval($header_params) );
}

sub printXmlHeader {
    my %args           = @_;
    my $main_container = $args{main_container};

    my $output = "";
    if ( $output_type eq "xml" ) {
        $output .= "<?xml version='1.0' encoding='UTF-8'?>\n";
    }

    $output .= "<$main_container>\n";

    return $output;
}

sub printXmlEnd {
    my %args = @_;

    my $main_container = $args{main_container};

    return "</${main_container}>\n";
}

sub printXmlError {
    my ($error) = @_;

    my $return = "";

    $error = "" if !$error;
    $error =~ s/^,//;
    $error =~ s/,$//;
    my @errors = ();
    if ( $error =~ /,/ ) {
        @errors = split( ",", $error );
    }
    elsif ($error) {
        $errors[0] = $error;
    }

    $return = "    <error>\n";
    foreach (@errors) {
        $return .= "        <string>$_</string>\n" if $error;
    }
    $return .= "    </error>\n";

    return $return;
}

sub printXmlBodyHost {
    my %args = @_;

    my $return;

    for my $key ( keys %args ) {
        $args{$key} = "" if $args{$key} eq "NULL";
    }

    my $id              = $args{"id"};
    my $new_id          = $args{"new_id"};
    my $ip              = $args{"ip"};
    my $hostname        = $args{"hostname"};
    my $new_hostname    = $args{"new_hostname"};
    my $host_descr      = $args{"host_descr"} || "";
    my $new_descr       = $args{"new_descr"} || "";
    my $site            = $args{"site"} || "";
    my $new_site        = $args{"new_site"} || "";
    my $cat             = $args{"cat"} || "";
    my $new_cat         = $args{"new_cat"} || "";
    my $int_admin       = $args{"int_admin"} || "";
    my $new_int_admin   = $args{"new_int_admin"} || "";
    my $comment         = $args{"comment"} || "";
    my $new_comment     = $args{"new_comment"} || "";
    my $update_type     = $args{"update_type"} || "";
    my $new_update_type = $args{"new_update_type"} || "";
    my $alive           = $args{"alive"} || "";
    my $last_response   = $args{"last_response"} || "";
    my $ip_version      = $args{"ip_version"};

    my $last_response_date = "";
    if ($last_response && $last_response ne -1) {
        $last_response_date = strftime "%d/%m/%Y %H:%M:%S",
          localtime($last_response);
    }

    if ( $alive eq "-1" ) {
        $alive = "never checked";
    }
    elsif ( $alive eq "0" ) {
        $alive = "down";
    }
    elsif ( $alive eq "1" ) {
        $alive = "up";
    }

    $return = "    <Host>\n";
    if ($ip) {
        $return .= "        <id>$id</id>\n" if exists $args{id};
        $return .= "        <new_id>$id</new_id>\n" if exists $args{new_id};
        $return .= "        <IP>$ip</IP>\n";
        $return .= "        <hostname>$hostname</hostname>\n"
          if exists $args{hostname};
        $return .= "        <new_hostname>$new_hostname</new_hostname>\n"
          if exists $args{new_hostname};
        $return .= "        <descr>$host_descr</descr>\n"
          if exists $args{host_descr};
        $return .= "        <new_descr>$new_descr</new_descr>\n"
          if exists $args{new_descr};
        $return .= "        <site>$site</site>\n" if exists $args{site};
        $return .= "        <new_site>$new_site</new_site>\n"
          if exists $args{new_site};
        $return .= "        <cat>$cat</cat>\n" if exists $args{cat};
        $return .= "        <new_cat>$new_cat</new_cat>\n"
          if exists $args{new_cat};
        $return .= "        <int_admin>$int_admin</int_admin>\n"
          if exists $args{int_admin};
        $return .= "        <new_int_admin>$new_int_admin</new_int_admin>\n"
          if exists $args{new_int_admin};
        $return .= "        <comment>$comment</comment>\n"
          if exists $args{comment};
        $return .= "        <new_comment>$new_comment</new_comment>\n"
          if exists $args{new_comment};
        $return .= "        <update_type>$update_type</update_type>\n"
          if exists $args{update_type};
        $return .=
          "        <new_update_type>$new_update_type</new_update_type>\n"
          if exists $args{new_update_type};
        $return .= "        <alive>$alive</alive>\n";
        $return .=
          "        <last_response>$last_response_date</last_response>\n";
        $return .= "        <ip_version>$ip_version</ip_version>\n";

        my $custom_columns = $args{"custom_columns"};
        my %custom_columns = %$custom_columns;

        if ( keys %custom_columns ) {
            $return .= "        <customColumns>\n";
            for my $key ( sort { lc($a) cmp lc($b) } keys %custom_columns ) {
                my $key_tag = $key;
                $key_tag =~ s/\s+/_/g;
                $return .= "            <$key_tag>$custom_columns{$key}</$key_tag>\n";
            }
            $return .= "        </customColumns>\n";
        }
    }

    $return .= "    </Host>\n";

    return $return;
}

sub printXmlBodyNetwork {
    my %args = @_;

    my $return;

    for my $key ( keys %args ) {
        $args{$key} = "" if $args{$key} eq "NULL";
    }

    my $id               = $args{"id"};
    my $new_id           = $args{"new_id"};
    my $ip               = $args{"ip"};
    my $new_ip           = $args{"new_ip"};
    my $BM               = $args{"BM"};
    my $new_BM           = $args{"new_BM"};
    my $descr            = $args{"descr"} || "";
    my $new_descr        = $args{"new_descr"} || "";
    my $site             = $args{"site"} || "";
    my $new_site         = $args{"new_site"} || "";
    my $cat              = $args{"cat"} || "";
    my $new_cat          = $args{"new_cat"} || "";
    my $sync             = $args{"sync"} || "n";
    my $new_sync         = $args{"new_sync"} || "n";
    my $comment          = $args{"comment"} || "";
    my $new_comment      = $args{"new_comment"} || "";
    my $ip_version       = $args{"ip_version"};
    my $firstFreeAddress = $args{"firstFreeAddress"};
    my $rootnet          = $args{"rootnet"} || "";
    my $dyn_dns_updates  = $args{"dyn_dns_updates"} || "";

    my $values = $args{"host_values"} || "";

    $return .= "    <Network>\n";
    if ( $ip || $new_ip ) {
        $return .= "        <id>$id</id>\n" if exists $args{id};
        $return .= "        <new_id>$new_id</new_id>\n"
          if exists $args{"new_id"};
        $return .= "        <IP>$ip</IP>\n" if exists $args{ip};
        $return .= "        <new_IP>$new_ip</new_IP>\n"
          if exists $args{"new_ip"};
        $return .= "        <BM>$BM</BM>\n"             if exists $args{BM};
        $return .= "        <new_BM>$new_BM</new_BM>\n" if exists $args{new_BM};
        $return .= "        <descr>$descr</descr>\n"    if exists $args{descr};
        $return .= "        <new_descr>$new_descr</new_descr>\n"
          if exists $args{new_descr};
        $return .= "        <site>$site</site>\n" if exists $args{site};
        $return .= "        <new_site>$new_site</new_site>\n"
          if exists $args{new_site};
        $return .= "        <cat>$cat</cat>\n" if exists $args{cat};
        $return .= "        <new_cat>$new_cat</new_cat>\n"
          if exists $args{new_cat};
        $return .= "        <comment>$comment</comment>\n"
          if exists $args{comment};
        $return .= "        <new_comment>$new_comment</new_comment>\n"
          if exists $args{new_comment};
        $return .= "        <sync>$sync</sync>\n" if exists $args{sync};
        $return .= "        <new_sync>$new_sync</new_sync>\n"
          if exists $args{new_sync};
        $return .= "        <ip_version>$ip_version</ip_version>\n"
          if exists $args{ip_version};
        $return .= "        <firstFreeAddress>$firstFreeAddress</firstFreeAddress>\n"
          if exists $args{firstFreeAddress};
        $return .= "        <rootnet>$rootnet</rootnet>\n"
          if exists $args{rootnet};
        $return .= "        <dyn_dns_updates>$dyn_dns_updates</dyn_dns_updates>\n"
          if exists $args{dyn_dns_updates};

        my $custom_columns = $args{"custom_columns"};
        my %custom_columns = %$custom_columns if $custom_columns;

        if ( keys %custom_columns ) {
            $return .= "        <customColumns>\n";
            for my $key ( sort { lc($a) cmp lc($b) } keys %custom_columns ) {
                my $key_tag = $key;
                $key_tag =~ s/\s+/_/g;
                $return .= "            <$key_tag>$custom_columns{$key}</$key_tag>\n";
            }
            $return .= "        </customColumns>\n";
        }

        my $freeAddresses = $args{"freeAddresses"};
        my @freeAddresses = ();
        @freeAddresses = @$freeAddresses if $freeAddresses;

        if ( $freeAddresses[0] ) {
            foreach my $address (@freeAddresses) {
                $return .= "        <freeAddress>$address</freeAddress>\n";
            }
        }

        my $usedAddresses = $args{"usedAddresses"};
        my @usedAddresses = ();
        @usedAddresses = @$usedAddresses if $usedAddresses;

        if ( $usedAddresses[0] ) {
            foreach my $address (@usedAddresses) {
                $return .= "        <usedAddress>$address</usedAddress>\n";
            }
        } elsif ($values) {

			$return .= "        <HostList>\n";

			for my $key ( sort keys %$values ) {
				my $id    = ${$values}{$key}->[12];
				my $ip         = ${$values}{$key}->[0];
				my $hostname   = ${$values}{$key}->[1];
				my $descr      = ${$values}{$key}->[2] || "";
				my $ip_int     = $key;
				my $loc        = ${$values}{$key}->[3] || "";
				my $cat        = ${$values}{$key}->[4] || "";
				my $int_admin  = ${$values}{$key}->[5] || "n";
				my $comment    = ${$values}{$key}->[6] || "";
				my $ut         = ${$values}{$key}->[7] || "";
				my $alive      = ${$values}{$key}->[8] || "";
				my $last_response = ${$values}{$key}->[9] || "";
				my $range_id   = ${$values}{$key}->[10] || "";
				my $ip_version = ${$values}{$key}->[16];
				my $custom_columns = ${$values}{$key}->[18];
				my %custom_columns = %$custom_columns;
				$cat     = "" if $cat eq "NULL";
				$loc     = "" if $loc eq "NULL";
				$descr   = "" if $descr eq "NULL";
				$comment = "" if $comment eq "NULL";

				my $last_response_date = "";
				if ($last_response && $last_response ne -1) {
					$last_response_date = strftime "%d/%m/%Y %H:%M:%S",
					  localtime($last_response);
				}

				if ( $alive eq "-1" ) {
					$alive = "never checked";
				}
				elsif ( $alive eq "0" ) {
					$alive = "down";
				}
				elsif ( $alive eq "1" ) {
					$alive = "up";
				}
				$return .= "            <Host>\n";
				if ($ip) {
					$return .= "                <id>$id</id>\n";
					$return .= "                <IP>$ip</IP>\n";
					$return .= "                <hostname>$hostname</hostname>\n";
					$return .= "                <descr>$descr</descr>\n";
					$return .= "                <site>$loc</site>\n";
					$return .= "                <cat>$cat</cat>\n";
					$return .= "                <int_admin>$int_admin</int_admin>\n";
					$return .= "                <comment>$comment</comment>\n";
					$return .= "                <update_type>$ut</update_type>\n";
					$return .= "                <alive>$alive</alive>\n";
					$return .= "                <last_response>$last_response_date</last_response>\n";
					$return .= "                <ip_version>$ip_version</ip_version>\n";

					if ( keys %custom_columns ) {
						$return .= "                <customColumns>\n";
						for my $key ( sort { lc($a) cmp lc($b) } keys %custom_columns ) {


							my $key_tag = $key;
							$key_tag =~ s/\s+/_/g;
							$return .= "                    <$key_tag>$custom_columns{$key}</$key_tag>\n";
						}
						$return .= "                </customColumns>\n";
					}
				}
				$return .= "            </Host>\n";
			}
			$return .= "        </HostList>\n";
		}
	}

    $return .= "    </Network>\n";

    return $return;
}

sub printXmlBodyNetworkList {
    my %args = @_;

    my $return = "";

    $return .= "    <NetworkList>\n";

    my $listNetworks = $args{"listNetworks"};
    my @listNetworks = ();
    @listNetworks = @$listNetworks if $listNetworks;

    if ( $listNetworks[0] ) {
        foreach my $network (@listNetworks) {
            $return .= "        <Network>$network</Network>\n";
        }
    }

    $return .= "    </NetworkList>\n";

    return $return;
}

sub printXmlBodyNetworkList_noCSV {
    my %args = @_;

    my $values = $args{"network_values"};
    my $order = $args{"network_order"};

    my $return = "";

    $return .= "    <NetworkList>\n";

#    for my $key ( sort $sort_order_ref keys %$values ) {}
	foreach my $key ( @$order ) {
        my $id    = $key;
        my $ip    = ${$values}{$key}->[0];
        my $BM    = ${$values}{$key}->[1];
        my $descr    = ${$values}{$key}->[2] || "";
        my $site    = ${$values}{$key}->[3] || "";
        my $cat    = ${$values}{$key}->[4] || "";
        my $sync    = ${$values}{$key}->[5] || "";
        my $comment    = ${$values}{$key}->[6] || "";
        my $ip_version    = ${$values}{$key}->[7] || "";
        my $rootnet    = ${$values}{$key}->[8] || "";
#        my $custom_columns    = ${$values}{$key}->[9] || "";
#        my %custom_columns = %$custom_columns;
        my $parent_network_id    = ${$values}{$key}->[10] || "";

        $return .= "        <Network>\n";
        $return .= "            <id>$id</id>\n";
        $return .= "            <IP>$ip</IP>\n";
        $return .= "            <BM>$BM</BM>\n";
        $return .= "            <descr>$descr</descr>\n";
        $return .= "            <site>$site</site>\n";
        $return .= "            <cat>$cat</cat>\n";
        $return .= "            <comment>$comment</comment>\n";
        $return .= "            <sync>$sync</sync>\n";
        $return .= "            <ip_version>$ip_version</ip_version>\n";
        $return .= "            <rootnet>$rootnet</rootnet>\n";
        $return .= "            <parent_network_id>$parent_network_id</parent_network_id>\n";
#        $return .= "        <dyn_dns_updates>$dyn_dns_updates</dyn_dns_updates>\n";


#        if ( keys %custom_columns ) {
#            $return .= "            <customColumns>\n";
#            for my $key ( sort { lc($a) cmp lc($b) } keys %custom_columns ) {
#                my $key_tag = $key;
#                $key_tag =~ s/\s+/_/g;
#                $return .= "                <$key_tag>$custom_columns{$key}</$key_tag>\n";
#            }
#            $return .= "            </customColumns>\n";
#        }
        $return .= "        </Network>\n";
    }

    $return .= "    </NetworkList>\n";

    return $return;
}


sub listHosts {

    my $filter     = $q->param("filter")     || "";
    my $ip_version = $q->param("ip_version") || "v4";
    my $include_id   = $q->param("include_id")   || "no";
    my $limit   = $q->param("limit")   || 0;
    my $page   = $q->param("page")   || 0;
    my $no_csv   = $q->param("no_csv") || "";

    my $start = 1;
    my $end = $limit;

    if ( $limit !~ /^\d{1,4}/ ) {
        $error .= "ERROR: limit MUST BE AN INTEGER BETWEEN 0 AND 9999";
    }

    if ( $page && ! $limit ) {
        $error .= "ERROR: page OPTION REQUIRES THE limit OPTION";
    }

    if ( $page !~ /^\d{1,4}/ ) {
        $error .= "ERROR: page MUST BE AN INTEGER BETWEEN 0 AND 9999";
    } elsif ( $page != 0 ) {
        $start = ($limit * $page) + 1;
        $end = $start + $limit - 1;
    }

    if ( $include_id !~ /^(yes|no)$/i ) {
        $error .= "ERROR: INVALID VALUE FOR include_id";
	}

	if ( $error ) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    my %filter;
    my @filter;
    my $match_all = 0;
    my $match_all1 = 0;
    # ALL filter strips only the domain part
    if ( $filter =~ /\[\[ALL\]\]/ ) {
        $filter =~ s/\[\[ALL\]\]//;
        $match_all = 1;
    }
    # MATCH_ALL filter founds all sub strings
    if ( $filter =~ /\[\[MATCH_ALL\]\]/ ) {
        $filter =~ s/\[\[MATCH_ALL\]\]//;
        $match_all1 = 1;
    }

    if ( $filter =~ /,/ ) {
        @filter = split( ",", $filter );
    }
    else {
        $filter[0] = $filter;
    }

    foreach (@filter) {
        $_ =~ /^(.+)::(.+)$/;
        my $filter_cat = $1;
        my $filter_arg = $2;
        next if !$filter_cat || !$filter_arg;
        $filter{$filter_cat} = $filter_arg;
    }

    my $values;
    if ( $ip_version eq "v4" ) {
        $values = $gip->get_host_hash_between( "$client_id", "1", "4294967294", "$ip_version" );
    } else {
        $values = $gip->get_host_hash_between( "$client_id", "4294967294", "85070591730234615865843651857942052863", "$ip_version" );
    }
    # 3fff:ffff:ffff:ffff:ffff:ffff:ffff:ffff == 85070591730234615865843651857942052863
    my @custom_columns = $gip->get_custom_host_columns("$client_id");
    my %custom_columns_values = $gip->get_custom_host_column_values_host_hash("$client_id");
    my @cc_ids = $gip->get_custom_host_column_ids("$client_id");
    my $custom_column_val;
    my %custom_columns;

    foreach my $cc_ele (@custom_columns) {
        my $name = $cc_ele->[0];
        my $id   = $cc_ele->[1];
        $custom_columns{$id} = $name;
    }

    my @predef_columns = ( "hostname", "description", "site", "category", "comment" );

    my @list;
	my %host_values;

	my $i = 1;
    for my $key ( sort keys %$values ) {

        my $host_id    = ${$values}{$key}->[12];
        my $ip         = ${$values}{$key}->[0];
        my $hostname   = ${$values}{$key}->[1];
        my $ip_int     = $key;
        my $loc        = ${$values}{$key}->[3] || "-1";
        my $cat        = ${$values}{$key}->[4] || "-1";
        my $comment    = ${$values}{$key}->[6] || "";
        my $ip_version_found = ${$values}{$key}->[16];
        my $descr      = ${$values}{$key}->[2] || "";
        my $int_admin      = ${$values}{$key}->[5] || "n";
        my $ut      = ${$values}{$key}->[7] || "-1";
        my $alive      = ${$values}{$key}->[8] || "-1";
        my $last_response      = ${$values}{$key}->[9] || "-1";
        my $range_id      = ${$values}{$key}->[10] || "-1";
        $cat     = "" if $cat eq "NULL";
        $loc     = "" if $loc eq "NULL";
        $descr   = "" if $descr eq "NULL";
        $comment = "" if $comment eq "NULL";
        $ut = "" if $ut eq "NULL";

        $ip_int = Math::BigInt->new("$ip_int");

        if ( $ip_version eq "v4" && $ip_int > 4294967294 ) {
            next;
        } elsif ( $ip_version eq "v6" && $ip_int <= 4294967294 ) {
            next;
        }

        # escape comas
        $loc =~ s/,/\\,/g;
        $cat =~ s/,/\\,/g;
        $descr =~ s/,/\\,/g;
        $comment =~ s/,/\\,/g;
        $hostname =~ s/,/\\,/g;

        my %predef_columns = (
            hostname    => "$hostname",
            category    => "$cat",
            description => "$descr",
            comment     => "$comment",
            site        => "$loc",
        );

        my $netfilter        = "";
        my $compare_operator = "eq";

        for my $key ( keys %filter ) {
            my $filter_value = $filter{$key};

            my @filter_values = split( /\|/, $filter_value );
            my $anz_filter_values = scalar(@filter_values);

            while ( my ( $pc_key, $pc_value ) = each(%predef_columns) ) {
                if ( $key eq $pc_key ) {
                    $pc_value =~ s/\..*$// if $match_all && $key eq "hostname";
                    if ( $anz_filter_values == 1 ) {
                        if ($netfilter) {
                            if ($match_all1) {
                                $netfilter .= " && \"$pc_value\" =~ /$filter_value/i";
                            } else {
                                $netfilter .= " && \"$filter_value\" $compare_operator \"$pc_value\"";
                            }
                        }
                        else {
                            if ($match_all1) {
                                $netfilter .= "\"$pc_value\" =~ /$filter_value/i";
                            } else {
                                $netfilter = "\"$filter_value\" $compare_operator \"$pc_value\"";
                            }
                        }
                    } else {
                        my $netfilter_tmp = "";
                        foreach (@filter_values) {
                            $netfilter_tmp .=
                              " || \"$pc_value\" $compare_operator \"$_\"";
                        }
                        $netfilter_tmp =~ s/^ \|\| //;
                        if ($netfilter) {
                            $netfilter .= " && ( $netfilter_tmp )"
                              if $netfilter_tmp;
                        }
                        else {
                            $netfilter = "( $netfilter_tmp )" if $netfilter_tmp;
                        }
                    }
                    next;
                }
            }
        }

        my $cc_value_show = "";
        my %cc_hash;

        foreach (@cc_ids) {
            my $id = $_->[0];

            my $cc_name = $custom_columns{$id};
            my $cc_value = "";
            if ( $custom_columns_values{"${id}_${host_id}"} ) {
                $cc_value = $custom_columns_values{"${id}_${host_id}"}[0];
                # escape coma
                $cc_value =~ s/,/\\,/g if ! $no_csv;
                # convert ampersand
                $cc_value =~ s/(&)/$1amp;/g;
            }
            $cc_value_show .= ",$cc_value";

            $cc_hash{$cc_name} = $cc_value;

            for my $key ( keys %filter ) {

                if ( $key ne $cc_name ) {
                    next;
                }

                my $filter_value = $filter{$key};

                my @filter_values = split( /\|/, $filter_value );
                my $anz_filter_values = scalar(@filter_values);

                if ( $anz_filter_values == 1 ) {
                    if ($netfilter) {
                        $netfilter .=
" && \"$filter_value\" $compare_operator \"$cc_value\"";
                    }
                    else {
                        $netfilter =
                          "\"$filter_value\" $compare_operator \"$cc_value\"";
                    }
                }
                else {
                    my $netfilter_tmp = "";
                    foreach (@filter_values) {
                        $netfilter_tmp .=
                          " || \"$cc_value\" $compare_operator \"$_\"";
                    }
                    $netfilter_tmp =~ s/^ \|\| //;
                    if ($netfilter) {
                        $netfilter .= " && ( $netfilter_tmp )"
                          if $netfilter_tmp;
                    }
                    else {
                        $netfilter = "$netfilter_tmp" if $netfilter_tmp;
                    }
                }
            }
        }

        my $cc_hash = \%cc_hash;

        if ($filter) {
            if ( $include_id =~ /^yes$/i ) {
                if ( eval($netfilter) ) {
            		$i++;
                    next if $start && $i <= $start;
                    push @list, "$host_id,$ip,$hostname,$loc,$cat,$comment,${descr}${cc_value_show}";

					push @{$host_values{$ip_int}},"$ip","$hostname","$descr","$loc","$cat","$int_admin","$comment","$ut","$alive","$last_response","$range_id","$ip_int","$host_id","","","$client_id","$ip_version","",$cc_hash;
                    last if $end && $i > $end;
                }
            } else {
                if ( eval($netfilter) ) {
            		$i++;
                    next if $start && $i <= $start;
                    push @list, "$ip,$hostname,$loc,$cat,$comment,${descr}${cc_value_show}";
					push @{$host_values{$ip_int}},"$ip","$hostname","$descr","$loc","$cat","$int_admin","$comment","$ut","$alive","$last_response","$range_id","$ip_int","$host_id","","","$client_id","$ip_version","",$cc_hash;
                    last if $end && $i > $end;
                }
            }
        } else {
            $i++;
            next if $start && $i <= $start;
            if ( $include_id =~ /^yes$/i ) {
                push @list, "$host_id,$ip,$hostname,$loc,$cat,$comment,${descr}${cc_value_show}";
                push @{$host_values{$ip_int}},"$ip","$hostname","$descr","$loc","$cat","$int_admin","$comment","$ut","$alive","$last_response","$range_id","$ip_int","$host_id","","","$client_id","$ip_version","",$cc_hash;
            } else {
                push @list, "$ip,$hostname,$loc,$cat,$comment,${descr}${cc_value_show}";
                push @{$host_values{$ip_int}},"$ip","$hostname","$descr","$loc","$cat","$int_admin","$comment","$ut","$alive","$last_response","$range_id","$ip_int","$host_id","","","$client_id","$ip_version","",$cc_hash;
            }
            last if $end && $i > $end;
            $i++;
        }
#		$i++;
    }

    my $list = \@list;
    my $host_values = \%host_values;

    my $output = "";
    my $ret    = "";

    $ret = printHeaders(
        output_type_header => "$output_type_header",
        output_type        => "$output_type",
        main_container     => "$main_container",
    ) || "";
    $output .= $ret if $ret;

	if ( $no_csv =~ /^yes$/i ) {
		$ret = printXmlBodyHostList_noCSV( host_values => $host_values, ) || "";
	} else {
		$ret = printXmlBodyHostList( listHosts => $list, ) || "";
	}
    $output .= $ret if $ret;

    printResponse(
        output         => "$output",
        main_container => "$main_container",
    );
}

sub printXmlBodyHostList {
    my %args = @_;

    my $return = "";

    $return .= "    <HostList>\n";

    my $listHosts = $args{"listHosts"};
    my @listHosts = ();
    @listHosts = @$listHosts if $listHosts;

    if ( $listHosts[0] ) {
        foreach my $host (@listHosts) {
            $return .= "        <Host>$host</Host>\n";
        }
    }

    $return .= "    </HostList>\n";

    return $return;
}

sub printXmlBodyHostList_noCSV {
    my %args = @_;

    my $return = "";

    $return .= "    <HostList>\n";

    my $values = $args{"host_values"} || "";

    for my $key ( sort keys %$values ) {
        my $id    = ${$values}{$key}->[12];
        my $ip         = ${$values}{$key}->[0];
        my $hostname   = ${$values}{$key}->[1];
        my $descr      = ${$values}{$key}->[2] || "";
        my $ip_int     = $key;
        my $loc        = ${$values}{$key}->[3] || "";
        my $cat        = ${$values}{$key}->[4] || "";
		my $int_admin  = ${$values}{$key}->[5] || "n";
        my $comment    = ${$values}{$key}->[6] || "";
        my $ut         = ${$values}{$key}->[7] || "";
        my $alive      = ${$values}{$key}->[8] || "";
        my $last_response = ${$values}{$key}->[9] || "";
        my $range_id   = ${$values}{$key}->[10] || "";
        my $ip_version = ${$values}{$key}->[16];
        my $custom_columns = ${$values}{$key}->[18];
        my %custom_columns = %$custom_columns;
        $cat     = "" if $cat eq "NULL";
        $loc     = "" if $loc eq "NULL";
        $descr   = "" if $descr eq "NULL";
        $comment = "" if $comment eq "NULL";

		my $last_response_date = "";
		if ($last_response && $last_response ne -1) {
			$last_response_date = strftime "%d/%m/%Y %H:%M:%S",
			  localtime($last_response);
		}

		if ( $alive eq "-1" ) {
			$alive = "never checked";
		}
		elsif ( $alive eq "0" ) {
			$alive = "down";
		}
		elsif ( $alive eq "1" ) {
			$alive = "up";
		}

		$return .= "        <Host>\n";
		if ($ip) {
			$return .= "            <id>$id</id>\n";
			$return .= "            <IP>$ip</IP>\n";
			$return .= "            <hostname>$hostname</hostname>\n";
			$return .= "            <descr>$descr</descr>\n";
			$return .= "            <site>$loc</site>\n";
			$return .= "            <cat>$cat</cat>\n";
			$return .= "            <int_admin>$int_admin</int_admin>\n";
			$return .= "            <comment>$comment</comment>\n";
			$return .= "            <update_type>$ut</update_type>\n";
			$return .= "            <alive>$alive</alive>\n";
			$return .= "            <last_response>$last_response_date</last_response>\n";
			$return .= "            <ip_version>$ip_version</ip_version>\n";

			if ( keys %custom_columns ) {
				$return .= "            <customColumns>\n";
				for my $key ( sort { lc($a) cmp lc($b) } keys %custom_columns ) {

					my $key_tag = $key;
					$key_tag =~ s/\s+/_/g;
					$return .= "                <$key_tag>$custom_columns{$key}</$key_tag>\n";
				}
				$return .= "            </customColumns>\n";
			}
		}
        $return .= "        </Host>\n";
	}

    $return .= "    </HostList>\n";

    return $return;
}


sub printXmlBodyVlan {
    my %args = @_;

    my $return = "";

    for my $key ( keys %args ) {
        $args{$key} = "" if $args{$key} eq "NULL";
    }

    my $vlan_id        = $args{"vlan_id"};
    my $new_vlan_id    = $args{"new_vlan_id"};
    my $vlan_number    = $args{"vlan_number"};
    my $new_number     = $args{"new_number"};
    my $vlan_name      = $args{"vlan_name"};
    my $new_name       = $args{"new_name"};
    my $vlan_comment   = $args{"vlan_comment"} || "";
    my $new_comment    = $args{"new_comment"} || "";
    my $provider       = $args{"provider"} || "";
    my $new_provider   = $args{"new_provider"} || "";
    my $font_color     = $args{"font_color"} || "";
    my $new_font_color = $args{"new_font_color"} || "";
    my $bg_color       = $args{"bg_color"} || "";
    my $new_bg_color   = $args{"new_bg_color"} || "";

    $return .= "    <vlan>\n";

    #	if ( $vlan_id || $new_vlan_id )
    if ( $vlan_id || $new_vlan_id || $vlan_number ) {
        $return .= "        <id>$vlan_id</id>\n" if exists $args{vlan_id};
        $return .= "        <new_id>$new_vlan_id</new_id>\n"
          if exists $args{new_vlan_id};
        $return .= "        <number>$vlan_number</number>\n"
          if exists $args{vlan_number};
        $return .= "        <new_number>$new_number</new_number>\n"
          if exists $args{new_number};
        $return .= "        <name>$vlan_name</name>\n"
          if exists $args{vlan_name};
        $return .= "        <new_name>$new_name</new_name>\n"
          if exists $args{new_name};
        $return .= "        <comment>$vlan_comment</comment>\n"
          if exists $args{vlan_comment};
        $return .= "        <new_comment>$new_comment</new_comment>\n"
          if exists $args{new_comment};
        $return .= "        <provider>$provider</provider>\n"
          if exists $args{provider};
        $return .= "        <new_provider>$new_provider</new_provider>\n"
          if exists $args{new_provider};
        $return .= "        <font_color>$font_color</font_color>\n"
          if exists $args{font_color};
        $return .= "        <new_font_color>$new_font_color</new_font_color>\n"
          if exists $args{new_font_color};
        $return .= "        <bg_color>$bg_color</bg_color>\n"
          if exists $args{bg_color};
        $return .= "        <new_bg_color>$new_bg_color</new_bg_color>\n"
          if exists $args{new_bg_color};
    }
    $return .= "    </vlan>\n";

    return $return;
}

sub printXmlBodyVlanProvider {
    my %args = @_;

    my $return = "";

    for my $key ( keys %args ) {
        $args{$key} = "" if $args{$key} eq "NULL";
    }

    my $id          = $args{"id"};
    my $name        = $args{"name"};
    my $new_name    = $args{"new_name"};
    my $comment     = $args{"comment"} || "";
    my $new_comment = $args{"new_comment"} || "";

    $return .= "    <vlanProvider>\n";
    if ($id) {
        $return .= "        <id>$id</id>\n"       if exists $args{id};
        $return .= "        <name>$name</name>\n" if exists $args{name};
        $return .= "        <new_name>$new_name</new_name>\n"
          if exists $args{new_name};
        $return .= "        <comment>$comment</comment>\n"
          if exists $args{comment};
        $return .= "        <new_comment>$new_comment</new_comment>\n"
          if exists $args{new_comment};
    }
    $return .= "    </vlanProvider>\n";

    return $return;
}

sub listClients {
    my %args = @_;

    my $output = "";
    my $ret    = "";

    $ret = printHeaders(
        output_type_header => "$output_type_header",
        output_type        => "$output_type",
        main_container     => "$main_container",
    ) || "";
    $output .= $ret if $ret;

	my %values_clients=$gip->get_client_hash_all("$client_id");
	my %values_clients_new;

	if ( $client_id ) {
		$values_clients_new{$client_id} = $values_clients{$client_id};
		%values_clients = %values_clients_new;
	}

	$ret = printXmlBodyClients( listClients => \%values_clients ) || "";

    $output .= $ret if $ret;

    printResponse(
        output         => "$output",
        main_container => "$main_container",
    );

}

sub printXmlBodyClients {
    my %args = @_;

    my $values_clients = $args{"listClients"} || "";
	my %values_clients;
	if ( $values_clients ) {
		%values_clients = %$values_clients;
	}

    my $return = "";


	while ( my ($id, @value) = each(%values_clients) ) {

		$return .= "    <client>\n";

		my $client = $values_clients{$id}[0];
		my $phone = $values_clients{$id}[1] || "";
		my $fax = $values_clients{$id}[2] || "";
		my $address = $values_clients{$id}[3] || "";
		my $comment = $values_clients{$id}[4] || "";
		my $contact_name_1 = $values_clients{$id}[5] || "";
		my $contact_phone_1 = $values_clients{$id}[6] || "";
		my $contact_cell_1 = $values_clients{$id}[7] || "";
		my $contact_email_1 = $values_clients{$id}[8] || "";
		my $contact_comment_1 = $values_clients{$id}[9] || "";
		my $contact_name_2 = $values_clients{$id}[10] || "";
		my $contact_phone_2 = $values_clients{$id}[11] || "";
		my $contact_cell_2 = $values_clients{$id}[12] || "";
		my $contact_email_2 = $values_clients{$id}[13] || "";
		my $contact_comment_2 = $values_clients{$id}[14] || "";
		my $contact_name_3 = $values_clients{$id}[15] || "";
		my $contact_phone_3 = $values_clients{$id}[16] || "";
		my $contact_cell_3 = $values_clients{$id}[17] || "";
		my $contact_email_3 = $values_clients{$id}[18] || "";
		my $contact_comment_3 = $values_clients{$id}[19] || "";
		my $default_resolver = $values_clients{$id}[20] || "";
		my $dns_server_1 = $values_clients{$id}[21] || "";
		my $dns_server_2 = $values_clients{$id}[22] || "";
		my $dns_server_3 = $values_clients{$id}[23] || "";

		$return .= "        <client>$client</client>\n";
		$return .= "        <phone>$phone</phone>\n";
		$return .= "        <fax>$fax</fax>\n";
		$return .= "        <address>$address</address>\n";
		$return .= "        <comment>$comment</comment>\n";
		$return .= "        <contact_name_1>$contact_name_1</contact_name_1>\n";
		$return .= "        <contact_phone_1>$contact_phone_1</contact_phone_1>\n";
		$return .= "        <contact_cell_1>$contact_cell_1</contact_cell_1>\n";
		$return .= "        <contact_email_1>$contact_email_1</contact_email_1>\n";
		$return .= "        <contact_comment_1>$contact_comment_1</contact_comment_1>\n";
		$return .= "        <contact_name_2>$contact_name_2</contact_name_2>\n";
		$return .= "        <contact_phone_2>$contact_phone_2</contact_phone_2>\n";
		$return .= "        <contact_cell_2>$contact_cell_2</contact_cell_2>\n";
		$return .= "        <contact_email_2>$contact_email_2</contact_email_2>\n";
		$return .= "        <contact_comment_2>$contact_comment_2</contact_comment_2>\n";
		$return .= "        <contact_name_3>$contact_name_3</contact_name_3>\n";
		$return .= "        <contact_phone_3>$contact_phone_3</contact_phone_3>\n";
		$return .= "        <contact_cell_3>$contact_cell_3</contact_cell_3>\n";
		$return .= "        <contact_email_3>$contact_email_3</contact_email_3>\n";
		$return .= "        <contact_comment_3>$contact_comment_3</contact_comment_3>\n";
		$return .= "        <default_resolver>$default_resolver</default_resolver>\n";
		$return .= "        <dns_server_1>$dns_server_1</dns_server_1>\n";
		$return .= "        <dns_server_2>$dns_server_2</dns_server_2>\n";
		$return .= "        <dns_server_3>$dns_server_3</dns_server_3>\n";
		$return .= "    </client>\n";
	}

    return $return;
}

sub check_ip {
    my $ip = shift;

    my $ip_version;
    if ( $ip =~ /^\d{1,3}\./ ) {
        $ip_version = "v4";
        if ( $ip !~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
            $error .= "ERROR: INVALID IPV4 ADDRESS";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }
    }
    elsif ($ip) {
        my $valid_v6 = $gip->check_valid_ipv6("$ip") || "0";
        $ip_version = "v6";
        if ( $valid_v6 != 1 ) {
            $error .= "ERROR: INVALID IPV6 ADDRESS";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }
    }

    $ip_int = $gip->ip_to_int( "$client_id", "$ip", "$ip_version" );

    return ( $ip, $ip_int, $ip_version );
}

sub check_characters {
    my $dangerous_character_detected = 0;
    my $dangerous_parameter          = "";
    for my $key ( scalar($q->param()) ) {
        if ( $key =~ /[&;`'\\<>=^%#*]/ ) {
            $dangerous_character_detected = 1;
            last;
        }
        for my $value ( scalar($q->param($key)) ) {
            next if ! $value;
            if ( $value =~ /[&;`'\\<>=^%#*]/ ) {
                $dangerous_character_detected = 1;
                $dangerous_parameter          = $key;
                last;
            }
        }
    }

    return ( $dangerous_character_detected, $dangerous_parameter );
}

sub exit_error {
    my %args = @_;

    my $error              = $args{"error"};
    my $main_container     = $args{"main_container"};
    my $http_status        = $args{"http_status"};
    my $output_type_header = $args{"output_type_header"};

    my $output = "";
    my $ret    = "";

    $ret = printHeaders(
        output_type_header => "$output_type_header",
        output_type        => "$output_type",
        main_container     => "$main_container",
    ) || "";
    $output .= $ret if $ret;

    printResponse(
        output         => "$output",
        main_container => "$main_container",
    );

    exit 1;
}

sub print_help {
    my %args = @_;

    my $main_container     = $args{"main_container"};
    my $http_status        = $args{"http_status"};
    my $output_type_header = $args{"output_type_header"};
    my $attribs            = $args{"attribs"};

    my %attribs = %$attribs if $attribs;

    print $q->header( -type => "$output_type_header",
        -status => "$http_status" );

    my $output = "";
    my $ret    = "";

    $ret = printXmlHeader( main_container => "$main_container", ) || "";
    $output .= $ret if $ret;

    $output .= "    <supported_attributes>\n";

    $output .=
      "            <request_type>$attribs{request_type}</request_type>\n"
      if $attribs{request_type};
    $output .= "            <client_id>$attribs{client_id}</client_id>\n"
      if $attribs{client_id};

    if ( keys %attribs ) {
        for my $key ( sort keys %attribs ) {
            if ( $key =~ /^(request_type|client_id)$/ ) {
                next;
            }
            $output .= "            <$key>$attribs{$key}</$key>\n";
        }
    }

    $output .= "    </supported_attributes>\n";

    $ret = printXmlEnd( main_container => "$main_container", ) || "";
    $output .= $ret if $ret;

    $output = create_json("$output") if $output_type eq "json";

    print $output;

    exit;
}


sub print_version {
    my %args = @_;

    my $main_container     = $args{"main_container"};
    my $http_status        = $args{"http_status"};
    my $output_type_header = $args{"output_type_header"};


    print $q->header( -type => "$output_type_header",
        -status => "$http_status" );

    my $output = "";
    my $ret    = "";

    $ret = printXmlHeader( main_container => "$main_container", ) || "";
    $output .= $ret if $ret;

    $output .= "    <version>$API_VERSION</version>\n";

    $ret = printXmlEnd( main_container => "$main_container", ) || "";
    $output .= $ret if $ret;

    $output = create_json("$output") if $output_type eq "json";

    print $output;

    exit;
}

sub get_host_network {
    my %args = @_;

    my $ip         = $args{"ip"};
    my $ip_int     = $args{"ip_int"};
    my $ip_version = $args{"ip_version"};

    my $red_num = "";

# red, BM, red_num, site, ip_version, rootnet
# TEST include ip_version within query to fetch only networks for adequat ip_version
    my @values_host_redes = $gip->get_host_redes_no_rootnet("$client_id");

    my $k = 0;
    foreach (@values_host_redes) {
        if ( !$values_host_redes[$k]->[0] || $values_host_redes[$k]->[5] == 1 )
        {
            $k++;
            next;
        }

        my $ip_version_checkred = $values_host_redes[$k]->[4];

        if ( $ip_version ne $ip_version_checkred ) {
            $k++;
            next;
        }

        my $host_red    = $values_host_redes[$k]->[0];
        my $host_red_bm = $values_host_redes[$k]->[1];

        if ( $ip_version eq "v4" ) {
            $host_red =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $third_host_red_oct = $3;
            $ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $third_host_oct = $3;
            if ( $host_red_bm >= 24 && $third_host_red_oct != $third_host_oct )
            {
                $k++;
                next;
            }
        }

        if ( $ip_version eq "v6" ) {
            $host_red = ip_expand_address( $host_red, 6 );
            $ip       = ip_expand_address( $ip,       6 );
            $host_red =~ /^(.+:.+:.+:.+:).+:.+:.+:.+/;
            my $net_part_host_red = $1;
            $ip =~ /^(.+:.+:.+:.+:).+:.+:.+:.+/;
            my $net_part_ip = $1;
            if ( $host_red_bm == 64 && $net_part_host_red ne $net_part_ip ) {
                $k++;
                next;
            }
        }

        my $next        = 0;
        my $redob_redes = "$host_red/$host_red_bm";
        my $ipob_redes  = new Net::IP($redob_redes) or $next = 1;
        if ($next) {
            $k++;
            next;
        }

        my $last_ip_int = ( $ipob_redes->last_int() );
        $last_ip_int = Math::BigInt->new("$last_ip_int");
        my $first_ip_int = ( $ipob_redes->intip() );
        $first_ip_int = Math::BigInt->new("$first_ip_int");

        if ( $ip_int < $first_ip_int || $ip_int > $last_ip_int ) {
            $k++;
            next;
        } elsif ( $ip_int == $first_ip_int && $ip_version eq "v4" && $host_red_bm <= 30 ) {
            $error = "ERROR: $ip IS A NETWORK ADDRESS";
            last;
        } elsif ( $ip_int == $last_ip_int && $ip_version eq "v4" && $host_red_bm <= 30  ) {
            $error = "ERROR: $ip IS A BROADCAST ADDRESS";
            last;
        } else {
            $red_num = $values_host_redes[$k]->[2];
            last;
        }
    }

    if ( !$red_num && !$error ) {
        $error = "ERROR: NO NETWORK FOR IP FOUND";
    }

    if ($error) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    return $red_num;
}

sub process_custom_columns {
    my %args = @_;

    my $cc_name         = $args{"cc_name"};
    my $cc_entry        = $args{"cc_entry"} || "";
    my $new_cc_entry    = $args{"new_cc_entry"} || "";
    my $pc_id           = $args{"pc_id"};
    my $cc_id           = $args{"cc_id"};
    my $ip              = $args{"ip"};
    my $ip_version      = $args{"ip_version"};
    my $cc_entry_linked = "";
    my $error           = "";
    if ( $cc_name eq "URL" ) {

        if (   $new_cc_entry
            && $new_cc_entry !~ /^(.{1,30}::.{1,750})(,.{1,30}.{1,750};?)?$/ )
        {
            $error    = "ERROR: WRONG URL FORMAT";
            $cc_entry = "";
        }

    }
    elsif ( $cc_name eq "CM" ) {
        if ( $new_cc_entry !~ /^(enabled|disabled)$/ ) {
            $error    = "ERROR: new_CM: INVALID VALUE";
            $cc_entry = "";
        }
    }
    elsif ( $cc_name eq "linked IP" ) {

        my $ip_comp = $ip;
        $ip_comp = ip_compress_address( $ip_comp, 6 ) if $ip_version eq "v6";

        my %linked_ips_update;
        my %linked_ips_insert;

        $new_cc_entry =~ s/\s*//g;
        my @linked_ips = ();
        @linked_ips = split( ",", $new_cc_entry );
        my @linked_ips_old = ();
        @linked_ips_old = split( ",", $cc_entry );

        # elements which are only in linked_ips_old
        my %seen;
        my @linked_ips_old_only;
        @seen{@linked_ips} = ();
        foreach my $item (@linked_ips_old) {
            push( @linked_ips_old_only, $item ) unless exists $seen{$item};
        }

        # update linked IP
        my $cc_value_new = "";
        foreach my $linked_ip (@linked_ips) {

            if ( $linked_ip eq $ip ) {
                $error .= "," . "IP CAN NOT BE LINKED TO ITSELF: $linked_ip";
                next;
            }

            my $ip_version_linked_ip;
            if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
                $ip_version_linked_ip = "v4";
            }
            else {
                $ip_version_linked_ip = "v6";
            }

            next if $linked_ip eq $ip_comp;

            my $valid_ip = 0;
            if ( $linked_ip =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
                $valid_ip = 1;
            }
            else {
                $valid_ip = $gip->check_valid_ipv6("$linked_ip") || "0";
            }
            if ( $valid_ip != 1 ) {
                $error .= "," . "INVALID LINKED IP: $linked_ip";
                next;
            }

            my $ip_int_linked = $gip->ip_to_int( "$client_id", "$linked_ip",
                "$ip_version_linked_ip" );
            my @host = $gip->get_host( "$client_id", "$ip_int_linked",
                "$ip_int_linked" );
            if ( !$host[0] ) {
                $error .= "," . "LINKED HOST DOES NOT EXIST: $linked_ip";
                next;
            }

            my $linked_ip_comp;
            if ( $ip_version_linked_ip eq "v6" ) {
                $linked_ip_comp = ip_compress_address( $linked_ip, 6 );
            }
            else {
                $linked_ip_comp = $linked_ip;
            }
            $cc_value_new .= "," . $linked_ip_comp;

            my $linked_host_id = $host[0]->[11];
            my $linked_cc_entry =
              $gip->get_custom_host_column_entry( "$client_id",
                "$linked_host_id", "$cc_name", "$pc_id" )
              || "";

            if ($linked_cc_entry) {
                if ( $linked_cc_entry !~ /\b${ip_comp}\b/ ) {
                    $linked_cc_entry .= "," . $ip_comp;
                    $linked_ips_update{$linked_host_id} = $linked_cc_entry;
                }
            }
            else {
                $linked_ips_insert{$linked_host_id} = $linked_cc_entry;
            }

            $cc_value_new =~ s/^,//;
        }

        $cc_entry_linked = $cc_value_new;

        if ( !$error ) {

            # delete linked IP from elements of @linked_ips_old_only
            foreach my $linked_ip_old_only (@linked_ips_old_only) {
                $gip->delete_linked_ip(
                    "$client_id",          "$ip_version",
                    "$linked_ip_old_only", "$ip"
                );
            }
            while ( my ( $linked_host_id, $linked_cc_entry ) =
                each(%linked_ips_update) )
            {
                $gip->update_custom_host_column_value_host_modip(
                    "$client_id", "$cc_id",
                    "$pc_id",     "$linked_host_id",
                    "$linked_cc_entry"
                );
            }
            while ( my ( $linked_host_id, $linked_cc_entry ) =
                each(%linked_ips_insert) )
            {
                $gip->insert_custom_host_column_value_host(
                    "$client_id", "$cc_id",
                    "$pc_id",     "$linked_host_id",
                    "$ip_comp"
                );
            }
        }
    }
    return $error;
}

sub getClientID {
    my $client_name = shift;

    my $client_id = "";

    %clients_hash = $gip->get_clients_hash("1");

    for my $key ( keys %clients_hash ) {
        if ( $clients_hash{$key} eq $client_name ) {
            $client_id = $key;
            last;
        }
    }

    if ( !$client_id && $client_name ne "ALL" ) {
        $error .= "ERROR: CLIENT NOT FOUND";
        exit_error(
            error              => "$error",
            main_container     => "Result",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    return $client_id;
}

sub get_vlan {
    my $vlan_id = shift;

    my @values_vlan = $gip->get_vlan( "$client_id", "$vlan_id" );

# v.vlan_num,v.vlan_name,v.comment,v.bg_color,v.font_color,v.provider_id,v.switches,v.asso_vlan,vp.name
    my $vlan_num  = $values_vlan[0]->[0];
    my $vlan_name = $values_vlan[0]->[1];

    return ( $vlan_num, $vlan_name );
}

sub dec2bin {
    my $str = unpack( "B32", pack( "N", shift ) );
    $str =~ s/^0+(?=\d)//;    # otherwise you'll get leading zeros
    return $str;
}

sub bin2dec {
    return unpack( "N", pack( "B32", substr( "0" x 32 . shift, -32 ) ) );
}

sub find_network_address_from_ip {
    my %args = @_;

    my $ip         = $args{"ip"};
    my $BM_param   = $args{"BM"};
    my $ip_version = $args{"ip_version"};

    my $binmask_in;
    # find binmask for network*/BM_param
    if ( $ip_version eq "v4" ) {
        my %bm_to_mask = $gip->get_bm_to_netmask();
        my $netmask_in = $bm_to_mask{$BM_param};
        $netmask_in =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
        my $first_mask_oc     = $1;
        my $sec_mask_oc       = $2;
        my $thi_mask_oc       = $3;
        my $fou_mask_oc       = $4;
        my $first_mask_oc_bin = dec2bin("$first_mask_oc");
        my $sec_mask_oc_bin   = dec2bin("$sec_mask_oc");
        my $thi_mask_oc_bin   = dec2bin("$thi_mask_oc");
        my $fou_mask_oc_bin   = dec2bin("$fou_mask_oc");

        my $len_first = length($first_mask_oc_bin);
        my $len_sec   = length($sec_mask_oc_bin);
        my $len_thi   = length($thi_mask_oc_bin);
        my $len_fou   = length($fou_mask_oc_bin);
        my $len_falta;
        if ( $len_first < 8 ) {
            $len_falta         = 8 - $len_first;
            $first_mask_oc_bin = "$first_mask_oc_bin" . 0 x $len_falta;
        }
        if ( $len_sec < 8 ) {
            $len_falta       = 8 - $len_sec;
            $sec_mask_oc_bin = "$sec_mask_oc_bin" . 0 x $len_falta;
        }
        if ( $len_thi < 8 ) {
            $len_falta       = 8 - $len_thi;
            $thi_mask_oc_bin = "$thi_mask_oc_bin" . 0 x $len_falta;
        }
        if ( $len_fou < 8 ) {
            $len_falta       = 8 - $len_fou;
            $fou_mask_oc_bin = "$fou_mask_oc_bin" . 0 x $len_falta;
        }

        $binmask_in =
            "$first_mask_oc_bin"
          . "$sec_mask_oc_bin"
          . "$thi_mask_oc_bin"
          . "$fou_mask_oc_bin";
    }

    my $BM_version = 32;
    $BM_version = 128 if $ip_version eq "v6";
    my $redob    = "$ip/$BM_version";
    my $ipob_red = new Net::IP($redob)
      || die "Can not create ip object $redob: $!\n";

    my ( $red_in, $red_in_bin, $nibbles, $nibbles_red, $rest );
    my $bin_in = ( $ipob_red->binip() );
    if ( $ip_version eq "v4" ) {
        $red_in_bin = $binmask_in & $bin_in;
        $red_in_bin =~ /([01]{8})([01]{8})([01]{8})([01]{8})/;
        my $red_in_bin_first_oc = $1;
        my $red_in_bin_sec_oc   = $2;
        my $red_in_bin_thi_oc   = $3;
        my $red_in_bin_fou_oc   = $4;
        my $red_in_first        = bin2dec("$red_in_bin_first_oc");
        my $red_in_sec          = bin2dec("$red_in_bin_sec_oc");
        my $red_in_thi          = bin2dec("$red_in_bin_thi_oc");
        my $red_in_fou          = bin2dec("$red_in_bin_fou_oc");
        $red_in =
            $red_in_first . "."
          . $red_in_sec . "."
          . $red_in_thi . "."
          . $red_in_fou;
    } else {
        $binmask_in = "";
        for ( my $i = 1 ; $i <= $BM_param ; $i++ ) {
            $binmask_in = $binmask_in . "1";
        }
        $rest = 128 - $BM_param;
        for ( my $i = 1 ; $i <= $rest ; $i++ ) {
            $binmask_in = $binmask_in . "0";
        }
        $red_in_bin = $binmask_in & $bin_in;
        $red_in = ip_bintoip( $red_in_bin, 6 );
    }

    return $red_in;
}

sub check_bitmask {
    my %args = @_;

    my $BM         = $args{"BM"};
    my $ip_version = $args{"ip_version"};

    my $valid = 0;
    if ( $ip_version eq "v4" ) {
        if ( $BM !~ /^\d{1,2}$/ ) {
            return;
        }
        if ( $BM < 1 || $BM > 32 ) {
            return;
        }

    }
    else {
        if ( $BM !~ /^\d{1,3}$/ ) {
            return;
        }
        if ( $BM < 1 || $BM > 128 ) {
            return;
        }
    }
    return 1;
}

sub get_ip_from_hostname {
    my ($hostname) = @_;
    my $dbh        = $gip->_mysql_connection();
    my $qhostname  = $dbh->quote($hostname);
    my $qclient_id = $dbh->quote($client_id);
    my $sth        = $dbh->prepare(
"SELECT INET_NTOA(ip) FROM host WHERE HOSTNAME=$qhostname and client_id=$qclient_id limit 1 "
      )
      or exit_error(
        error =>
"Can not prepare SQL statement: SELECT INET_NTOA(ip) FROM host WHERE HOSTNAME=$qhostname and client_id=$qclient_id limit 1",
        main_container     => "$main_container",
        http_status        => "500 Internal Server Error",
        output_type_header => "$output_type_header",
      );

    $sth->execute()
      or exit_error(
        error =>
"Can not execute SQL statement: SELECT INET_NTOA(ip) FROM host WHERE HOSTNAME=$qhostname and client_id=$qclient_id limit 1",
        main_container     => "$main_container",
        http_status        => "500 Internal Server Error",
        output_type_header => "$output_type_header",
      );

    my $ip = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $ip;
}

sub check_filter {
    my %args = @_;

    my $filter = $args{"filter"};

    my $filter_param = $q->param("filter") || "";
    my @filter_param = split( /[,]/, $filter_param );

    my $filter_count = scalar @filter_param;


    foreach (@filter_param) {

        if ( $filter_count == 1 && $_ =~ /^(.+)::$/ ) {
             $error .= "ERROR: SINGLE FILTER ARGUMENT WITHOUT VALUE IS NOT SUPPORTED";
             exit_error(
                 error              => "$error",
                 main_container     => "$main_container",
                 http_status        => "400 Bad Request",
                 output_type_header => "$output_type_header",
            );
        }

        $_ =~ s/^\[\[ALL\]\]//;
        $_ =~ /^(.+)::(.*)$/;
        my $filter_cat = $1;
        my $filter_arg = $2 || "";

        if ( !$filter_cat ) {
            $error .= "ERROR: INVALID FILTER ARGUMENT";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }

        if ( $filter_cat !~ /^($filter)$/ ) {
            $error .= "ERROR: UNKNOWN FILTER ATTRIBUTE: $filter_cat - $filter";
            exit_error(
                error              => "$error",
                main_container     => "$main_container",
                http_status        => "400 Bad Request",
                output_type_header => "$output_type_header",
            );
        }
    }
}

sub createCCWhitespaceHash {
    my $cc_name = shift;

    if ( $cc_name =~ /\s/ ) {
        my $cc_name_no_whitespace = $cc_name;
        $cc_name_no_whitespace =~ s/[\s]/_/g;
        $cc_name_whitespace_hash{$cc_name_no_whitespace} = $cc_name;
    }
}

sub create_json {
    my ($output) = @_;

    # replace whitespaces in column name with _
    for my $cc_name_whitespace ( keys %cc_name_whitespace_hash ) {
        my $cc_name = $cc_name_whitespace_hash{$cc_name_whitespace};
        $output =~ s/$cc_name/$cc_name_whitespace/gm;
    }

#    $gip->debug("create_json: $output\n");
    if ( $output_type eq "json" ) {
        $output = "<container>" . $output . "</container>";
        my $output_xml;
        # Force list for list outputs if result is only a single entry
        if ( $request_type_param =~ /listHosts/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'Host' ]);
        } elsif ( $request_type_param =~ /listNetworks/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'Network' ]);
        } elsif ( $request_type_param =~ /freeNetworkAddresses/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'freeAddress' ]);
        } elsif ( $request_type_param =~ /usedNetworkAddresses/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'usedAddress' ]);
        } elsif ( $request_type_param =~ /listVlans/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'Vlan' ]);
        } elsif ( $request_type_param =~ /listVlanProviders/ ) {
            $output_xml = XMLin("$output", keyattr => {}, ForceArray => [ 'VlanProvider' ]);
        } else {
            $output_xml = XMLin($output);
        }

        my $output_show = "$output\n\n" . "$output_xml\n\n" . Dumper($output_xml);
#        $gip->debug("create_json: $output_show\n");

        $output = to_json $output_xml;
        # prevent double escaping of coma
#        $output =~ s/\\\\,/\\,/g;
        $output =~ s/\{\}/""/g;
    }

    # rereplace replaced _ with whitespaces
    for my $cc_name_whitespace ( keys %cc_name_whitespace_hash ) {
        my $cc_name = $cc_name_whitespace_hash{$cc_name_whitespace};
        $output =~ s/"$cc_name_whitespace"/"$cc_name"/g;
    }

    return $output;
}

sub printHeaders {
    my %args = @_;

    my $output = "";
    my $ret;

    my $output_type_header = $args{"output_type_header"};
    my $output_type        = $args{"output_type"};
    my $main_container     = $args{"main_container"};

    $ret = printXmlHeader(
        main_container => "$main_container",
        output_type    => "$output_type",
    ) || "";
    $output .= $ret if $ret;

    $ret = printXmlError( "$error", "$output_type" ) || "";
    $output .= $ret if $ret;

    return $output;
}

sub printResponse {
    my %args = @_;

    my $output         = $args{"output"};
    my $main_container = $args{"main_container"};

    my $ret = printXmlEnd( main_container => "$main_container", ) || "";
    $output .= $ret if $ret;

    $output = create_json("$output") if $output_type eq "json";

    $gip->debug("print Response output: $output\n");

    printHtmlHeader(
        type   => "$output_type_header",
        status => "200 OK",
    );

    print $output;

    exit 0;
}

sub listVlans {

    my $limit   = $q->param("limit")   || 0;
    my $page   = $q->param("page")   || 0;
    my $no_csv   = $q->param("no_csv") || "";

    my @values;
    my @list;
	my %vlan_hash;

    my $start = 1;
    my $end = $limit;

    if ( $limit !~ /^\d{1,4}/ ) {
        $error .= "ERROR: limit MUST BE AN INTEGER BETWEEN 0 AND 9999";
    }

    if ( $page && ! $limit ) {
        $error .= "ERROR: page OPTION REQUIRES THE limit OPTION";
    }

    if ( $page !~ /^\d{1,4}/ ) {
        $error .= "ERROR: page MUST BE AN INTEGER BETWEEN 0 AND 9999";
    } elsif ( $page != 0 ) {
        $start = ($limit * $page) + 1;
        $end = $start + $limit - 1;
    }

    if ( $error ) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }


    my $i = 1;
    if ( $client_name eq "ALL" ) {
        for my $id ( keys %clients_hash ) {

            my $v_client_name = $clients_hash{$id};
            @values = $gip->get_vlans("$id","$client_name");
            for my $vlan (@values) {

				$i++;
				next if $start && $i <= $start;

                my $client_id          = $vlan->[7] || "";
                my $vlan_id            = $vlan->[0];
                my $vlan_num           = $vlan->[1];
                my $vlan_name          = $vlan->[2];
                my $vlan_comment       = $vlan->[3] || "";
                my $vlan_provider_name = $vlan->[4] || "";
                my $vlan_bg_color      = $vlan->[5] || "";
                my $vlan_font_color    = $vlan->[6] || "";

                # escape comas
                $vlan_name =~ s/,/\\,/g;
                $vlan_comment =~ s/,/\\,/g;
                $vlan_provider_name =~ s/,/\\,/g;

                push @list, "$vlan_id,$vlan_num,$vlan_name,$vlan_comment,$vlan_provider_name,$vlan_bg_color,$vlan_font_color,$v_client_name";
				push @{$vlan_hash{$vlan_id}},"$vlan_num","$vlan_name","$vlan_comment","$vlan_provider_name","$vlan_bg_color","$vlan_font_color";
            }
            my %hash = map { $_ => 1 } @list;
            @list = keys %hash;
        }
    } else {
        @values = $gip->get_vlans("$client_id");
        for my $vlan (@values) {

			$i++;
			next if $start && $i <= $start;

            my $client_id          = $vlan->[7] || "";
            my $vlan_id            = $vlan->[0];
            my $vlan_num           = $vlan->[1];
            my $vlan_name          = $vlan->[2];
            my $vlan_comment       = $vlan->[3] || "";
            my $vlan_provider_name = $vlan->[4] || "";
            my $vlan_bg_color      = $vlan->[5] || "";
            my $vlan_font_color    = $vlan->[6] || "";

            # escape comas
            $vlan_name =~ s/,/\\,/g;
            $vlan_comment =~ s/,/\\,/g;
            $vlan_provider_name =~ s/,/\\,/g;

            push @list, "$vlan_id,$vlan_num,$vlan_name,$vlan_comment,$vlan_provider_name,$vlan_bg_color,$vlan_font_color";
			push @{$vlan_hash{$vlan_id}},"$vlan_num","$vlan_name","$vlan_comment","$vlan_provider_name","$vlan_bg_color","$vlan_font_color";
        }
    }

# v.id, v.vlan_num, v.vlan_name, v.comment, vp.name, v.bg_color, v.font_color, v.client_id

    my $output = "";
    my $ret    = "";

    my $list = \@list;
    my $vlan_hash = \%vlan_hash;

    $ret = printHeaders(
        output_type_header => "$output_type_header",
        output_type        => "$output_type",
        main_container     => "$main_container",
    ) || "";
    $output .= $ret if $ret;

	if ( $no_csv ) {
		$ret = printXmlBodyVlanList_noCSV( VLAN_values => $vlan_hash, ) || "";
    } else {
		$ret = printXmlBodyVlanList( listVlans => $list, ) || "";
	}
    $output .= $ret if $ret;

    printResponse(
        output         => "$output",
        main_container => "$main_container",
    );
}


sub printXmlBodyVlanList_noCSV {
    my %args = @_;

    my $values = $args{"VLAN_values"} || "";

    my $return = "    <VlanList>\n";

    for my $key ( sort keys %$values ) {
        my $id    = $key;
        my $number    = ${$values}{$key}->[0];
        my $name    = ${$values}{$key}->[1];
        my $comment    = ${$values}{$key}->[2] || "";
        my $provider_name    = ${$values}{$key}->[3] || "";
        my $bg_color    = ${$values}{$key}->[4] || "";
        my $font_color    = ${$values}{$key}->[5] || "";

		$return .= "        <Vlan>\n";
		$return .= "            <id>$id</id>\n";
		$return .= "            <number>$number</number>\n";
		$return .= "            <name>$name</name>\n";
		$return .= "            <comment>$comment</comment>\n";
		$return .= "            <provider>$provider_name</provider>\n";
		$return .= "            <bg_color>$bg_color</bg_color>\n";
		$return .= "            <font_color>$font_color</font_color>\n";
		$return .= "        </Vlan>\n";
    }

    $return .= "    </VlanList>\n";

    return $return;
}

sub printXmlBodyVlanList {
    my %args = @_;

    my $return = "";

    $return .= "    <VlanList>\n";

    my $listVlans = $args{"listVlans"};
    my @listVlans = ();
    @listVlans = @$listVlans if $listVlans;

    if ( $listVlans[0] ) {
        foreach my $vlan (@listVlans) {
            $return .= "        <Vlan>$vlan</Vlan>\n";
        }
    }

    $return .= "    </VlanList>\n";

    return $return;
}




sub insert_first_reserve_address {

    my ( $red, $client_id, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $alive, $ip_version, $dyn_dns_updates  ) = @_;

    my $dbh = $gip->_mysql_connection();
    my $qred = $dbh->quote( $red );
    my $qclient_id = $dbh->quote( $client_id );

    my @values_redes;

    my $sth = $dbh->prepare("SELECT red_num, BM, ip_version FROM net WHERE red=$qred AND rootnet=0 AND client_id = $qclient_id") or $error="Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
    if ($error) {
        $gip->debug("ERROR: $error\n");
        exit_error(
            error              => "ERROR: Can not execute SQL statement",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }    

	my $ip_ref;
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_redes, [ @$ip_ref ];
    }

    if ( ! $values_redes[0] && $ip_version eq "v6" ) {
        if ( $red =~ /::/ ) {
            $red = ip_expand_address ($ip_param,6);
        } else {
            $red = ip_compress_address ($ip_param,6);
        }
		$qred = $dbh->quote( $red );

		my $sth = $dbh->prepare("SELECT red_num, BM, ip_version FROM net WHERE red=$qred AND rootnet=0 AND client_id = $qclient_id") or $error="Can not execute statement:<p>$DBI::errstr";
		$sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
		if ($error) {
            $gip->debug("ERROR: $error\n");
			exit_error(
				error              => "ERROR: Can not execute SQL statement",
				main_container     => "$main_container",
				http_status        => "500 Internal Server Error",
				output_type_header => "$output_type_header",
			);
		}    

		my $ip_ref;
		while ( $ip_ref = $sth->fetchrow_arrayref ) {
			push @values_redes, [ @$ip_ref ];
		}
    }



    my $red_num = $values_redes[0]->[0];
    my $BM = $values_redes[0]->[1];

    $error = "ERROR: NETWORK NOT FOUND: $red" if ! $red_num;
    if ($error) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "400 Bad Request",
            output_type_header => "$output_type_header",
        );
    }

    my $redob = "$ip_param/$BM";
    my $ipob_red = new Net::IP($redob) or $error = "ERROR: CAN NOT CREATE IP OBJECT FOR $redob (6)";
    if ($error) {
        exit_error(
            error              => "$error",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }

    my $redint = ( $ipob_red->intip() );
    $redint = Math::BigInt->new("$redint");
    my $first_ip_int = $redint + 1;
    my $last_ip_int  = ( $ipob_red->last_int() );
    $last_ip_int = Math::BigInt->new("$last_ip_int");
    $last_ip_int = $last_ip_int - 1;

    # LOCK host table
    $sth = $dbh->prepare("LOCK TABLES host WRITE") or $error="Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
    if ($error) {
        $gip->debug("ERROR: $error\n");
        exit_error(
            error              => "ERROR: Can not lock table",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }

    my %host_hash;
    my $qred_num = $dbh->quote( $red_num );
    $sth = $dbh->prepare("SELECT ip as ip_int, INET_NTOA(ip) as ip, ip_version FROM host WHERE red_num=$qred_num ORDER BY inet_aton(ip)"
        ) or $error="Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
    if ($error) {
        $gip->debug("ERROR: $error\n");
        exit_error(
            error              => "ERROR: Can not execute SQL statement",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }

    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $ip_int = $ip_ref->{'ip_int'} || "";
        my $ip_version = $ip_ref->{'ip_version'};
        my $ip;
        if ( $ip_version eq "v4" ) {
            $ip = $ip_ref->{'ip'};
        } else {	
            $ip = $gip->int_to_ip("$client_id","$ip_int","v6");
        }
        push @{$host_hash{$ip_int}},"$ip"
    }

    my $firstFreeAddress;
	my $ip_int_host;
    for ( my $i = $first_ip_int; $i <= $last_ip_int ; $i++ ) {
        if ( ! $host_hash{$i}[0] ) {
#            my $ip_version = 
            $firstFreeAddress = $gip->int_to_ip( "$client_id", "$i", "$ip_version" );
            $ip_int_host = $i;
            last;
        }
    }
	if ( ! $firstFreeAddress ) {
		$error .= "ERROR: NETWORK HAS NO FREE ADDRESSES AVAILABLE";
		exit_error(
			error              => "$error",
			main_container     => "$main_container",
			http_status        => "200 OK",
			output_type_header => "$output_type_header",
		);
	}

    $loc="-1" if ! $loc;
    $cat="-1" if ! $cat;
    $dyn_dns_updates=1 if ! $dyn_dns_updates;

    my $qhostname = $dbh->quote( $hostname );
    my $qhost_descr = $dbh->quote( $host_descr );
    my $qloc = $dbh->quote( $loc );
    my $qint_admin = $dbh->quote( $int_admin );
    my $qcat = $dbh->quote( $cat );
    my $qcomentario = $dbh->quote( $comentario );
    my $qupdate_type = $dbh->quote( $update_type );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qip_int = $dbh->quote( $ip_int_host );
    $alive = "-1" if ! defined($alive);
    my $qip_version = $dbh->quote( $ip_version );
    my $qdyn_dns_updates = $dbh->quote( $dyn_dns_updates );

    $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qip_version,$qclient_id,$qdyn_dns_updates)"
                                ) or $error="Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
    if ($error) {
        $gip->debug("ERROR: $error\n");
        exit_error(
            error              => "ERROR: Can not execute SQL statement",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }
    my $new_id=$sth->{mysql_insertid};

    # UNLOCK host table
    $sth = $dbh->prepare("UNLOCK TABLES") or $error="Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or $error="Can not execute statement:<p>$DBI::errstr";
    if ($error) {
        $gip->debug("ERROR: $error\n");
        exit_error(
            error              => "ERROR: Can not unlock table",
            main_container     => "$main_container",
            http_status        => "500 Internal Server Error",
            output_type_header => "$output_type_header",
        );
    }

    $sth->finish();
    $dbh->disconnect;

    return ($new_id, $firstFreeAddress, $red_num);
}

sub get_cc_hash {
    my ( $h_object, $id  ) = @_;

    my %cc_value;
    if ( $h_object eq "host" ) {
        @custom_columns = $gip->get_custom_host_columns("$client_id");
        %cc_value = $gip->get_custom_host_columns_from_net_id_hash( "$client_id", "$id" );
    } elsif ( $h_object eq "network" ) {
        %cc_value = $gip->get_custom_columns_from_net_id_hash( "$client_id", "$id" );
    } else {
        return;
    }
    my %cc_hash;

    my $n = 0;
    foreach my $cc_ele (@custom_columns) {
        my $cc_name  = $custom_columns[$n]->[0];
        my $pc_id    = $custom_columns[$n]->[3];
        my $cc_id    = $custom_columns[$n]->[1];
        my $cc_entry = $cc_value{$cc_id}[1] || "";

   #            if ( $cc_name =~ /\s/ ) {
   #                my $cc_name_no_whitespace = $cc_name;
   #                $cc_name_no_whitespace =~ s/[\s]/_/;
   #                $cc_name_whitespace_hash{$cc_name_no_whitespace} = $cc_name;
   #            }

        # convert ampersand
        $cc_entry =~ s/(&)/$1amp;/g;

        $cc_hash{$cc_name} = $cc_entry;
        $n++;
    }

    my $cc_hash = \%cc_hash;

	return $cc_hash;
}
