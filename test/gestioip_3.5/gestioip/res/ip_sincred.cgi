#!/usr/bin/perl -w

# Copyright (C) 2012 Marc Uebel

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
use Net::IP;
use Net::IP qw(:PROC);
use Parallel::ForkManager;
use Socket;
use Math::BigInt;
use POSIX;

my $start_time=time();

### disabled 0; enabled 1;
my $enable_ping_history=1;
my $update_type_audit="6";

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer($daten);

my $base_uri=$gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

my $lang = $daten{'lang'} || "";
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();

if ( $client_id !~ /^\d{1,4}$/ ) {
	$client_id = 1;        
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{llenar_red_message}","$vars_file");
        $gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
}

my $dns_udp_timeout = 4;
my $dns_retry = 1;

# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
if ( $user_management_enabled eq "yes" ) {
	my $required_perms="create_host_perm,update_host_perm,delete_host_perm,execute_update_dns_perm";
#	my $required_perms="create_host_perm,update_host_perm,delete_host_perm";
		$gip->check_perms (
		client_id=>"$client_id",
		vars_file=>"$vars_file",
		daten=>\%daten,
		required_perms=>"$required_perms",
	);
}

my @config = $gip->get_config("$client_id");
my $max_procs = $config[0]->[1] || "254";
my $ignorar = $config[0]->[2] || "";
my $ignore_generic_auto = $config[0]->[3] || "yes";
my $generic_dyn_host_name = $config[0]->[4] || "_NO_GENERIC_DYN_NAME_";
my $dyn_ranges_only = $config[0]->[5] || "n";
my $ping_timeout = $config[0]->[6] || "2";
my $ignore_dns = $config[0]->[14] || 0;
my $confirm_dns_delete = $config[0]->[15] || "no";
#my $delete_down_hosts = $config[0]->[16] || "no";
my $delete_down_hosts = "yes";


my $red_num = $daten{'red_num'} || "";
if ( ! $red_num ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{formato_malo_message}: red_num (1)","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
} elsif ( $red_num !~ /^\d{1,5}$/ ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{formato_malo_message}: red_num (2)","$vars_file");
	$gip->print_error("$client_id","$$lang_vars{formato_malo_message}");
} else {
	$red_num=$daten{'red_num'};
}

my @values_ignorar=();
if ( $ignorar ) {
	$ignorar =~ s/\s+//g;
	@values_ignorar=split(",",$ignorar);
} else {
	$values_ignorar[0]="__IGNORAR__";
}
$generic_dyn_host_name =~ s/,/|/g;

my @values_redes = $gip->get_red("$client_id","$red_num");

if ( ! $values_redes[0] ) {
	$gip->print_error("$client_id","$$lang_vars{algo_malo_message}");
}

my $red = "$values_redes[0]->[0]" || "";
my $BM = "$values_redes[0]->[1]" || "";
my $descr = "$values_redes[0]->[2]" || "";
my $loc_id = "$values_redes[0]->[3]" || "";
my $ip_version = "$values_redes[0]->[7]" || "";
my $redob = "$red/$BM";
my $host_loc = $gip->get_loc_from_redid("$client_id","$red_num");
$host_loc = "---" if $host_loc eq "NULL";
my $host_cat = "---";

if ( $dyn_ranges_only eq "y" ) {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{llenar_red_message} $red/$BM $$lang_vars{reserved_ranges_only_message}","$vars_file");
} else {
	$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{llenar_red_message} $red/$BM","$vars_file");
}

$gip->print_error("$client_id","$$lang_vars{formato_malo_message} (1)") if $ip_version !~ /^(v4|v6)$/;


$gip->debug("DEBUG: $red_num - $red/$BM\n");

#print <<EOF;
#
#<div class="modal hide fade" id="scanModal">
#  <div class="modal-header">
#    <a class="close" data-dismiss="modal">×</a>
#    <h3>SCAN IN PROGESS</h3>
#  </div>
#  <div class="modal-body">
#    <p>Scan in progress... be pationt</p>
#  </div>
#  <div class="modal-footer">
#    <a href="#" class="btn">Close</a>
#    <a href="#" class="btn btn-primary">Save changes</a>
#  </div>
#</div>
#
#
#<script type="text/javascript">
#    \$(window).on('load',function(){
#        \$('#scanModal').modal('show');
#console.log("Opening scanModal");
#    });
#</script>
#
#EOF

my $align="align=\"right\"";
my $align1="";
my $ori="left";
my $ori1="right";
my $rtl_helper="<font color=\"white\">x</font>";
if ( $vars_file =~ /vars_he$/ ) {
	$align="align=\"left\"";
	my $align1="align=\"right\"";
	$ori="right";
	$ori1="left";
}


my $module = "Net::DNS";
my $module_check=$gip->check_module("$module") || "0";
$gip->print_error("$client_id","$$lang_vars{net_dns_not_found_message}") if $module_check != "1";


my %cc_values=$gip->get_custom_host_column_values_host_hash("$client_id","$red_num");
my @linked_cc_id=$gip->get_custom_host_column_ids_from_name("$client_id","linkedIP");
my $linked_cc_id=$linked_cc_id[0]->[0] || "";


my @client_entries=$gip->get_client_entries("$client_id");
my $default_resolver = $client_entries[0]->[20];
my @dns_servers;

my $dns_server_group_id = $gip->get_custom_column_entry("$client_id","$red_num","DNSSG") || "";
my @dns_server_group_values;
if ( $dns_server_group_id ) {
    # check for DNS server group
    @dns_server_group_values = $gip->get_dns_server_group_from_id("$client_id","$dns_server_group_id");
}
if ( @dns_server_group_values ) {

    $default_resolver = "no";

    push @dns_servers, $dns_server_group_values[0]->[2] if $dns_server_group_values[0]->[2];
    push @dns_servers, $dns_server_group_values[0]->[3] if $dns_server_group_values[0]->[3];
    push @dns_servers, $dns_server_group_values[0]->[4] if $dns_server_group_values[0]->[4];
} else {
    push @dns_servers, $client_entries[0]->[21] if $client_entries[0]->[21];
    push @dns_servers, $client_entries[0]->[22] if $client_entries[0]->[22];
    push @dns_servers, $client_entries[0]->[23] if $client_entries[0]->[23];
}


my @zone_records=();
my $zone_name=();

if ( $ip_version eq "v6" ) {
	my ($nibbles, $rest);
	my $red_exp = ip_expand_address ($red,6) if $ip_version eq "v6";
        my $nibbles_pre=$red_exp;
        $nibbles_pre =~ s/://g;
        my @nibbles=split(//,$nibbles_pre);
        my @nibbles_reverse=reverse @nibbles;
        $nibbles="";
        $rest=128-$BM;
        my $red_part_helper = ($rest+1)/4;
        $red_part_helper = ceil($red_part_helper);
        my $n=1;
        foreach my $num (@nibbles_reverse ) {
		if ( $n<$red_part_helper ) {
			$n++;
			next;		
                } elsif ( $nibbles =~ /\w/) {
                        $nibbles .= "." . $num;
                } else {
                        $nibbles = $num;
                }
                $n++;
        }
        $nibbles .= ".ip6.arpa.";
	$zone_name=$nibbles;
	@zone_records=$gip->fetch_zone("$zone_name","$default_resolver",\@dns_servers);
}

my ($first_ip_int,$last_ip_int);
my $ipob = new Net::IP ($redob) or $gip->print_error("$client_id","$$lang_vars{comprueba_red_BM_message}: <b>$red/$BM</b>"); 
my $redint=($ipob->intip());
$redint = Math::BigInt->new("$redint");
$first_ip_int = $redint + 1;
$first_ip_int = Math::BigInt->new("$first_ip_int");
$last_ip_int = ($ipob->last_int());
$last_ip_int = Math::BigInt->new("$last_ip_int");
$last_ip_int = $last_ip_int - 1;

if ( $ip_version eq "v6" ) {
	$first_ip_int--;
	$last_ip_int++;
}

#NET32
if ( $BM == 31 || $BM == 32 ) {
        $first_ip_int--;
        $last_ip_int++;
}


my $cat_id="-1";
my $int_admin="n";
my $utype;
if ( $ignore_dns ) {
	$utype="dns";
} else {
	$utype="dns";
}
my $utype_id=$gip->get_utype_id("$client_id","$utype") || "";
$gip->print_error("$client_id","$$lang_vars{no_update_type_message}") if ! $utype_id;

my $host_hash_ref=$gip->get_host_hash_check("$client_id","$red_num");

my $debug_message = "DEBUG NUM: " . scalar( keys %$host_hash_ref);
$gip->debug("DEBUG: $debug_message \n");

# SELECT h.ip, INET_NTOA(h.ip),h.hostname, h.host_descr, h.comentario, h.range_id, h.id, h.red_num, h.ip_version, h.loc, h.categoria, h.update_type, h.int_admin, h.alive FROM host h WHERE h.red_num=$qred_num ORDER BY h.ip

for my $key ( keys %$host_hash_ref ) {
    my $hostname_bbdd = $host_hash_ref->{"$key"}[1];
    my $host_descr = $host_hash_ref->{"$key"}[2] || "";
    my $cat_id = $host_hash_ref->{"$key"}[11] || "-1";
    my $comentario = $host_hash_ref->{"$key"}[3] || "";
    my $utype_id = $host_hash_ref->{"$key"}[12] || "-1";
    my @utype=$gip->get_utype("$client_id","$utype_id");
    my $utype = $utype[0][0] if @utype;
    $utype = "dns" if $utype eq "NULL";
    $utype = "" if ! $utype;
    my $alive = $host_hash_ref->{"$key"}[14] || "-1";
    my $int_admin = $host_hash_ref->{"$key"}[13];
    my $range_id = $host_hash_ref->{"$key"}[4];

    $debug_message = "$key - $hostname_bbdd - $host_descr - $cat_id - $comentario - $utype_id - $utype - $alive - $int_admin - $range_id\n";
    $gip->debug("DEBUG: $debug_message\n");
}

my $mydatetime = time();


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


print "<span style=\"float:$ori1;\">\n";
print "<div id=\"SincButtons\">\n";
if ( $BM >= 20 ) { 
	print "<table border=\"0\" width=\"100%\"><tr><td $align><td $align><form method=\"POST\" action=\"$server_proto://$base_uri/ip_show.cgi\" style=\"display:inline\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"><input type=\"submit\" class=\"detailed_view_button\" value=\"\" title=\"detailed network view\" name=\"B1\"></form><form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_red_overview.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"view\" value=\"long\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"><input type=\"submit\" class=\"long_view_button\" value=\"\" title=\"network overview\" name=\"B1\"></form><form method=\"POST\" action=\"$server_proto://$base_uri/ip_show_red_overview.cgi\" style=\"display:inline\"><input type=\"hidden\" name=\"view\" value=\"short\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"><input type=\"submit\" class=\"short_view_button\" value=\"\" title=\"network status view\" name=\"B1\"></form></td></tr></table>\n";
} else {
	print "<table border=\"0\" width=\"100%\"><tr><td $align><td $align><form method=\"POST\" action=\"$server_proto://$base_uri/ip_show.cgi\" style=\"display:inline\"><input name=\"red_num\" type=\"hidden\" value=\"$red_num\"><input name=\"client_id\" type=\"hidden\" value=\"$client_id\"><input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\"><input type=\"submit\" class=\"detailed_view_button\" value=\"\" title=\"detailed network view\"name=\"B1\"></form></td></tr></table>\n";
}
print "</div>\n";
print "</span><br>\n";

if ( ! $zone_records[0] && $ip_version eq "v6" ) {
	if ( $vars_file =~ /vars_he$/ ) {
		print "<p><span style=\"float: $ori;\">$zone_name $$lang_vars{can_not_fetch_zone_message}<p>$$lang_vars{zone_transfer_allowed_message}</span><br><p><br>\n";
		$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
	} else {
		$gip->print_error("$client_id","$$lang_vars{can_not_fetch_zone_message} $zone_name<p>$$lang_vars{zone_transfer_allowed_message}");
	}
}


my $j=0;
my $hostname;
my ( $ip_int, $ip_bin, $ip_ad, $pm, $res, $pid, $ip );
my ( %res_sub, %res, %result);

my $MAX_PROCESSES=$max_procs || "254";
$pm = new Parallel::ForkManager($MAX_PROCESSES);

$pm->run_on_finish(
	sub { my ($pid, $exit_code, $ident) = @_;
		$res_sub{$ident}=$exit_code;
	}
);

my $res_dns;
my $dns_error = "";

if ( $default_resolver eq "yes" ) {
	$res_dns = Net::DNS::Resolver->new(
	retry       => 2,
	udp_timeout => 5,
	tcp_timeout => 5,
	recurse     => 1,
	debug       => 0,
	);
} else {
	$res_dns = Net::DNS::Resolver->new(
	retry       => 2,
	udp_timeout => 5,
	tcp_timeout => 5,
	nameservers => [@dns_servers],
	recurse     => 1,
	debug       => 0,
	);
}


my $test_ip_int=$first_ip_int;
my $test_ip=$gip->int_to_ip("$client_id","$test_ip_int","$ip_version");

my $ptr_query=$res_dns->query("$test_ip");

if ( ! $ptr_query) {
	if ( $res_dns->errorstring eq "query timed out" ) {
		$gip->print_error("$client_id","$$lang_vars{no_answer_from_dns_message} - $$lang_vars{check_nameserver_message}<p>$$lang_vars{skipping_update_message}");
    }
}

my $used_nameservers = $res_dns->nameservers;

my $all_used_nameservers = join (" ",$res_dns->nameserver());

if ( $used_nameservers eq "0" ) {
	$gip->print_error("$client_id","$$lang_vars{no_answer_from_dns_message} - $$lang_vars{check_nameserver_message}<p>$$lang_vars{skipping_update_message}");
}
if ( $all_used_nameservers eq "127.0.0.1" && $default_resolver eq "yes" ) {
	$gip->print_error("$client_id","$$lang_vars{no_answer_from_dns_message} - $$lang_vars{check_nameserver_message}<p>$$lang_vars{skipping_update_message}");
}


my @ip=();
my @found_ip=();
if ( $dyn_ranges_only eq "y" ) {
	@ip=$gip->get_host_rango("$client_id","$first_ip_int","$last_ip_int","$red_num");
} else {
	if ( $ip_version eq "v4" ) {
		@ip=$gip->get_host("$client_id","$first_ip_int","$last_ip_int","$red_num","","$ip_version");
	} else {
		@ip=$gip->get_host_from_red_num("$client_id","$red_num");
	}
}
my $p=0;
foreach my $found_ips (@ip) {
	if ( $found_ips->[0] ) {
		$found_ips->[0]=$gip->int_to_ip("$client_id","$found_ips->[0]","$ip_version");
		$found_ip[$p]=$found_ips->[0];
	}
	$p++;
}
	

my @records=();
if ( $ip_version eq "v4" ) {
	my $l=0;
	for (my $m = $first_ip_int; $m <= $last_ip_int; $m++) {
		push (@records,"$m");
	}
} else {
	@records=@zone_records;
	my @records_new=();
	my $n=0;
	foreach (@zone_records) {
		if ( $_ =~ /(IN.?SOA|IN.?NS)/ ) {
			next;
		}
		$_=/^(.*)\.ip6.arpa/;
		my $nibbles=$1;
		my @nibbles=split('\.',$nibbles);
		@nibbles=reverse(@nibbles);
		my $ip_nibbles="";
		my $o=0;
		foreach (@nibbles) {
			if ( $o == 4 || $o==8 || $o==12 || $o==16 || $o==20 || $o==24 || $o==28 ) {
				$ip_nibbles .= ":" . $_;
			} else {
				$ip_nibbles .= $_;
			}
			$o++;
		}
		$records_new[$n]=$ip_nibbles;
		$n++;
	}
	
	@records=@records_new;
	@records=(@records,@found_ip);
	my %seen;
	for ( my $q = 0; $q <= $#records; ) {
		splice @records, --$q, 1
		if $seen{$records[$q++]}++;
	}
	@records=sort(@records)
}

my @records_check=();
foreach ( @records ) {
	next if ! $_;
	next if $_ !~ /\w+/;
	push (@records_check,"$_");
}
@records=sort(@records_check);

my $i;
foreach ( @records ) {

	next if ! $_;

	$i=$_;
	my $exit;
	if ( $ip_version eq "v4" ) {
		$ip_ad=$gip->int_to_ip("$client_id","$i","$ip_version");
	} else {
		$ip_ad=$_;
	}
	
		##fork
		$pid = $pm->start("$ip_ad") and next;
			#child

			my $p = "";
			if ( $ip_version eq "v4" ) {
                delete @ENV{'PATH', 'IFS', 'CDPATH', 'ENV', 'BASH_ENV'};
                my $result=$gip->ping_system("$ip_ad","$ping_timeout");
				# success: 0
				$p=1 if $result == "0";
			} else {
				my $command='ping6 -c 1 ' .  $ip_ad;
				my $result=$gip->ping6_system("$command","0");
				$p=1 if $result == "0";
			}
			if ( $p ) {
				$exit=0;
				# 0 if ping was successful
			} else {
				$exit=1;
			}

			my $ptr_query="";
			my $dns_result_ip="";

			if ( $default_resolver eq "yes" && ! @dns_servers ) {
				$res_dns = Net::DNS::Resolver->new(
				retry       => $dns_retry,
				udp_timeout => $dns_udp_timeout,
				tcp_timeout => 5,
				recurse     => 1,
				debug       => 0,
				);
			} else {
				$res_dns = Net::DNS::Resolver->new(
				retry       => $dns_retry,
				udp_timeout => $dns_udp_timeout,
				tcp_timeout => 5,
				nameservers => [@dns_servers],
				recurse     => 1,
				debug       => 0,
				);
			}

			$ptr_query = $res_dns->send("$ip_ad");

			$dns_error = $res_dns->errorstring;

			if ( $dns_error eq "NOERROR" || ! $dns_error ) {
				if ($ptr_query) {
					foreach my $rr ($ptr_query->answer) {
						next unless $rr->type eq "PTR";
						$dns_result_ip = $rr->ptrdname;
					}
				}
			} else {
                # TEST TEST TEST DEFINE exit5 -> dns error
                # "query timed out"
            }
			
			if ( $dns_result_ip && $exit == 0 ) {
				$exit=2;
			} elsif ( $dns_result_ip && $exit == 1 ) {
				$exit=3;
			} elsif ( ! $dns_result_ip && $exit == 0 ) {
				$exit=4;
			}


		$pm->finish($exit); # Terminates the child process

}

$pm->wait_all_children;


print "<span class=\"sinc_text\">";


my @delete_hosts;
my $ip_ad_int="";

foreach ( @records ) {

	if ( ! $_ ) {
		next;
	}

	if ( $ip_version eq "v4" ) {
		$ip_ad_int=$_;
		$ip_ad = $gip->int_to_ip("$client_id","$ip_ad_int","$ip_version");
	} else {
		$ip_ad=$_;
		$ip_ad_int = $gip->ip_to_int("$client_id","$ip_ad","$ip_version");
	}
	
    my $exit=$res_sub{$ip_ad};

    if ( ! $exit ) {
        next;
    }

    $gip->debug("DEBUG: processing $ip_ad - $ip_ad_int\n");

	my $host_exists = "";
	my $hostname_bbdd = "";
	my $cat_id="-1";
	my $int_admin="n";
	my $utype="dns";
	my $utype_id = "";
	my $host_descr = "NULL";
	my $comentario = "NULL";
	my $alive = "";
	my $range_id="-1";

# SELECT h.ip, INET_NTOA(h.ip),h.hostname, h.host_descr, h.comentario, h.range_id, h.id, h.red_num, h.ip_version, h.loc, h.categoria, h.update_type, h.int_admin, h.alive FROM host h WHERE h.red_num=$qred_num ORDER BY h.ip
	if ( exists $host_hash_ref->{"$ip_ad_int"} ) {
		$host_exists = 1;
		$hostname_bbdd = $host_hash_ref->{"$ip_ad_int"}[1] || "";
		$host_descr = $host_hash_ref->{"$ip_ad_int"}[2] || "";
		$cat_id = $host_hash_ref->{"$ip_ad_int"}[11] || "-1";
		$comentario = $host_hash_ref->{"$ip_ad_int"}[3] || "";
		$utype_id = $host_hash_ref->{"$ip_ad_int"}[12] || "-1";
		my @utype=$gip->get_utype("$client_id","$utype_id");
		$utype = $utype[0][0] if @utype;
		$utype = "dns" if $utype eq "NULL";
		$alive = $host_hash_ref->{"$ip_ad_int"}[14] || "-1";
		$int_admin = $host_hash_ref->{"$ip_ad_int"}[13];
		$range_id = $host_hash_ref->{"$ip_ad_int"}[4];

        $gip->debug("DEBUG: host_exists: $host_exists\n");
	}

	if ( $dyn_ranges_only eq "y" ) {
		if ( $host_exists && $range_id == "-1" ) {
			next;
		} elsif ( ! $host_exists ) {
			next;
		}
	}

    $gip->debug("DEBUG: $ip_ad - $ip_ad_int - $hostname_bbdd - $host_descr - $cat_id - $comentario - $utype_id - $utype - $alive - $int_admin - $range_id\n");

	$utype_id=$gip->get_utype_id("$client_id","$utype") if ! $utype_id;
	$utype_id="-1" if ! $utype_id;

	my $ping_result=0;
	# $ping_result success: 1
	$ping_result=1 if $exit == "0" || $exit == "2" || $exit == "4";;

	# Ignor IP if update type has higher priority than "dns" 
	if ( $utype ne "dns" && $utype ne "---" ) {
		if ( $hostname_bbdd ) {
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$$lang_vars{ignorado_message} - $utype :update type - $hostname_bbdd :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $hostname_bbdd - update type: $utype - $$lang_vars{ignorado_message}<br>\n";
			}
			$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");
		} else {
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$$lang_vars{ignorado_message} - $utype :update type :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: update type: $utype - $$lang_vars{ignorado_message}<br>\n";
			}

		}
		next;
	}

	# Ignore "reserved" entries
	if ( $hostname_bbdd =~ /^reserved$/i ) {
		print "<b>$ip_ad</b>: reserved IP - ignored<br>";
		next;
	}

		
	my $ignore_reason=0; # 1: no dns entry; 2: hostname matches generic-auto-name; 3: hostname matches ignore-string 4: hostname matches generic-dynamic name, 5: ignore_dns activated
	my @dns_result_ip;

	my $hostname;
	if ( $exit == 2 || $exit == 3 ) {

		my $ptr_query="";
		my $dns_result_ip="";

		if ( $default_resolver eq "yes" && ! @dns_servers ) {
			$res_dns = Net::DNS::Resolver->new(
            retry       => $dns_retry,
            udp_timeout => $dns_udp_timeout,
			tcp_timeout => 5,
			recurse     => 1,
			debug       => 0,
			);
		} else {
			$res_dns = Net::DNS::Resolver->new(
            retry       => $dns_retry,
            udp_timeout => $dns_udp_timeout,
			tcp_timeout => 5,
			nameservers => [@dns_servers],
			recurse     => 1,
			debug       => 0,
			);
		}

		$ptr_query = $res_dns->send("$ip_ad");

		$dns_error = $res_dns->errorstring;

		if ( $dns_error eq "NOERROR" || ! $dns_error ) {
			if ($ptr_query) {
				foreach my $rr ($ptr_query->answer) {
					next unless $rr->type eq "PTR";
					$dns_result_ip = $rr->ptrdname;
				}
			}
		}

		$hostname = $dns_result_ip || "unknown";


		if ( $hostname eq "unknown" ) {
			$ignore_reason=1;
		}
	} else {
		$hostname = "unknown";
		$ignore_reason=1;
	}


	my $ptr_name = $ip_ad;
	my $generic_auto="";
	my $igno_name;
	my $igno_set = 0;

	if ( $ignore_dns ) {
		$igno_set = 1;
		$igno_name=$hostname;
		$ignore_reason=5;
	}
	if ( $ip_version eq "v4" ) {
		$ptr_name =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
		$generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
	} else {
		$ptr_name =~ /^(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+)$/;
		$generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
	}

	if ( $hostname =~ /$generic_auto/ && $ignore_generic_auto eq "yes" ) {
		$igno_set = 1;
		$hostname="unknown";
		$igno_name="$generic_auto";
		$ignore_reason=2;
	}

	foreach (@values_ignorar) {
		if ( $hostname =~ /$_/ ) {
			$igno_set = 1;
			$hostname="unknown";
			$igno_name="$_";
			$ignore_reason=3;
		}
		next;
	}

	if ( $hostname =~ /$generic_dyn_host_name/ ) {
		$igno_set = 1;
		$hostname="unknown";
		$igno_name="$generic_dyn_host_name";
		$ignore_reason=4;
	}


	if ( $hostname_bbdd ) {

        $gip->debug("DEBUG 1: hostname_bbdd: $hostname_bbdd\n");

		if ( $hostname_bbdd eq $hostname && $hostname ne "unknown" && $igno_set == "0") {
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$$lang_vars{ignorado_message} - $hostname_bbdd :$$lang_vars{tiene_entrada_message} :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $$lang_vars{tiene_entrada_message}: $hostname_bbdd - $$lang_vars{ignorado_message}<br>\n";
			}
			$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");

            $gip->debug("DEBUG 2: hostname_bbdd: $hostname_bbdd\n");
		} else {
			if ( $confirm_dns_delete eq "no" && $hostname eq "unknown" && $ping_result == "0" ) {
				if ( $delete_down_hosts ne "yes" ) {
                    if ( $hostname_bbdd eq "unknown" ) {
                        print "<b>$ip_ad</b>: $$lang_vars{ignorado_message}: $$lang_vars{no_dns_message} + $$lang_vars{no_ping_message}<br>\n";
                    } else {
                        $gip->update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$ip_version");
                        if ( $vars_file =~ /vars_he$/ ) {
                            print "<span style=\"float: $ori\">$rtl_helper($hostname_bbdd :$$lang_vars{entrada_antigua_message}) $hostname :$$lang_vars{entrada_actualizada_message} :<b>$ip_ad</b></span><br>\n";
                        } else {
                            print "<b>$ip_ad</b>: $$lang_vars{hostname_set_to_unknown_message}: $$lang_vars{no_dns_message} + $$lang_vars{no_ping_message} ($$lang_vars{entrada_antigua_message}: $hostname_bbdd)<br>\n";
                        }

                        my $audit_type="1";
                        my $audit_class="1";
                        my $host_descr_audit = $host_descr;
                        $host_descr_audit = "---" if $host_descr_audit eq "NULL";
                        my $comentario_audit = $comentario;
                        $comentario_audit = "---" if $comentario_audit eq "NULL";
                        my $event="$ip_ad: $hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit -> $hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
                        $gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
                    }
				} else {
					# DELETE
					if ( $range_id eq "-1" ) {
						my $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_ad_int");
						$gip->delete_custom_host_column_entry("$client_id","$host_id");
						if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
							my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
							$linked_ips =~ s/^X:://;
							my @linked_ips=split(",",$linked_ips);
							foreach my $linked_ip_delete(@linked_ips){
								$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
							}
						}
						$gip->delete_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version");
					} else {
                        $gip->debug("DEBUG 3: hostname_bbdd: $hostname_bbdd\n");
						my $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_ad_int");
						$gip->delete_custom_host_column_entry("$client_id","$host_id");
						if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
							my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
							$linked_ips =~ s/^X:://;
							my @linked_ips=split(",",$linked_ips);
							foreach my $linked_ip_delete(@linked_ips){
								$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
							}
						}
						$gip->clear_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version");

					}
					# no dns entry
					if ( $ignore_reason == "1" ) {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper($$lang_vars{no_dns_message} + $$lang_vars{no_ping_message}) $hostname_bbdd :$$lang_vars{entrada_borrado_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{entrada_borrado_message}: $hostname_bbdd ($$lang_vars{no_dns_message} + $$lang_vars{no_ping_message})<br>\n";
						}
					# generic auto name
					} elsif ( $ignore_reason == "2" ) {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper($$lang_vars{generico_message} + $$lang_vars{no_ping_message}) $hostname_bbdd :$$lang_vars{entrada_borrado_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{entrada_borrado_message}: $hostname_bbdd ($$lang_vars{generico_message} + $$lang_vars{no_ping_message})<br>\n";
						}
					# hostname matches ignore-string
					} elsif ( $ignore_reason == "3" ) {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper($$lang_vars{tiene_string_no_ping_message} \"$igno_name\") $hostname_bbdd :$$lang_vars{entrada_borrado_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{entrada_borrado_message}: $hostname_bbdd ($$lang_vars{tiene_string_no_ping_message} \"$igno_name\")<br>\n";
						}

					} elsif ( $ignore_reason == "4" ) {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{entrada_borrado_message} - $hostname_bbdd :$$lang_vars{generic_dyn_host_message} + $$lang_vars{no_ping_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{entrada_borrada_message}: $hostname_bbdd ($$lang_vars{generic_dyn_host_message} + $$lang_vars{no_ping_message})<br>\n";
						}

					} elsif ( $ignore_reason == "5" ) {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{entrada_borrado_message} - $hostname_bbdd :$$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message} - $$lang_vars{entrada_borrado_message}<br>\n";
						}
					} else {
						if ( $vars_file =~ /vars_he$/ ) {
							print "<span style=\"float: $ori\">$rtl_helper($$lang_vars{no_ping_message}) $hostname_bbdd :$$lang_vars{entrada_borrado_message} :<b>$ip_ad</b></span><br>\n";
						} else {
							print "<b>$ip_ad</b>: $$lang_vars{entrada_borrado_message}: $hostname_bbdd ($$lang_vars{no_ping_message})<br>\n";
						}
					}

					my $audit_type="14";
					my $audit_class="1";
					my $host_descr_audit = $host_descr;
					$host_descr_audit = "---" if $host_descr_audit eq "NULL";
					my $comentario_audit = $comentario;
					$comentario_audit = "---" if $comentario_audit eq "NULL";
					my $event="$ip_ad,$hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
					$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
                }

				next;

			} elsif ( $confirm_dns_delete eq "yes" && $hostname eq "unknown" && $ping_result == "0" ) {
                $gip->debug("DEBUG 4: hostname_bbdd: $hostname_bbdd\n");
				# no dns entry
				if ( $ignore_reason == "1" ) {
					print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{no_dns_message} + $$lang_vars{no_ping_message})<br>\n";
				# generic auto name
				} elsif ( $ignore_reason == "2" ) {
					print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{generico_message} + $$lang_vars{no_ping_message})<br>\n";
				# hostname matches ignore-string
				} elsif ( $ignore_reason == "3" ) {
					print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{tiene_string_no_ping_message} \"$igno_name\")<br>\n";
                # hostnamme matches dyn-generic-name
				} elsif ( $ignore_reason == "4" ) {
					print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{generic_dyn_host_message})<br>\n";
				} elsif ( $ignore_reason == "5" ) {
					print "<b>$ip_ad</b>: $$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message} - $$lang_vars{marked_for_delete_message}<br>\n";
				} else {
					print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{no_ping_message})<br>\n";
				}
                push @delete_hosts, "$ip_ad";

				next;

			} elsif ( $ignore_dns && $ping_result == 0 ) {
                $gip->debug("DEBUG 7: hostname_bbdd: $hostname_bbdd\n");
                # DELETE
				if ( $range_id eq "-1" ) {
					my $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_ad_int");
					$gip->delete_custom_host_column_entry("$client_id","$host_id");
					if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
						my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
						$linked_ips =~ s/^X:://;
						my @linked_ips=split(",",$linked_ips);
						foreach my $linked_ip_delete(@linked_ips){
							$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
						}
					}
					$gip->delete_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version");
				} else {
					my $host_id=$gip->get_host_id_from_ip_int("$client_id","$ip_ad_int");
					$gip->delete_custom_host_column_entry("$client_id","$host_id");
					if ( exists $cc_values{"${linked_cc_id}_${host_id}"} ) {
						my $linked_ips=$cc_values{"${linked_cc_id}_${host_id}"}[0];
						$linked_ips =~ s/^X:://;
						my @linked_ips=split(",",$linked_ips);
						foreach my $linked_ip_delete(@linked_ips){
							$gip->delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$ip_ad");
						}
					}
					$gip->clear_ip("$client_id","$ip_ad_int","$ip_ad_int","$ip_version");
				}
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$rtl_helper($$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message}) $hostname_bbdd  :$$lang_vars{entrada_borrado_message} :<b>$ip_ad</b></span><br>\n";
				} else {
					print "<b>$ip_ad</b>: $$lang_vars{entrada_borrado_message}: $hostname_bbdd ($$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message})<br>\n";
				}

				my $audit_type="14";
				my $audit_class="1";
				my $host_descr_audit = $host_descr;
				$host_descr_audit = "---" if $host_descr_audit eq "NULL";
				my $comentario_audit = $comentario;
				$comentario_audit = "---" if $comentario_audit eq "NULL";
				my $event="$ip_ad,$hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
				$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

				next;

			} elsif ( $confirm_dns_delete eq "yes" && $ignore_dns && $ping_result == 0 ) {
                $gip->debug("DEBUG 8: hostname_bbdd: $hostname_bbdd\n");
				print "<b>$ip_ad</b>: $$lang_vars{marked_for_delete_message}: $hostname_bbdd ($$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message})<br>\n";
                push @delete_hosts, "$ip_ad";

				next;

			} elsif ( $hostname eq "unknown" && $ping_result == "1" ) {
                $gip->debug("DEBUG 9: hostname_bbdd: $hostname_bbdd\n");
				# no dns entry
				if ( $ignore_reason == "1" ) {
					if ( $vars_file =~ /vars_he$/ ) {
						print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{ignorado_message} - ($$lang_vars{no_dns_message}) $hostname_bbdd  :$$lang_vars{tiene_entrada_message} :<b>$ip_ad</b></span><br>\n";
					} else {
						print "<b>$ip_ad</b>: $$lang_vars{tiene_entrada_message}: $hostname_bbdd ($$lang_vars{no_dns_message}) - $$lang_vars{ignorado_message}<br>\n";
					}
                    # 2 generic auto name
                    # 3 hostname matches ignore-string
                    # 4 hostname matches generic-dynamic name
                    # 5 ignore dns activated
				} elsif ( $ignore_reason == "2" || $ignore_reason == "3" || $ignore_reason == "4" || $ignore_reason == "5" ) {
					if ( $vars_file =~ /vars_he$/ ) {
						print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{ignorado_message} - $hostname_bbdd :$$lang_vars{tiene_entrada_message} :<b>$ip_ad</b></span><br>\n";
					} else {
						print "<b>$ip_ad</b>: $$lang_vars{tiene_entrada_message}: $hostname_bbdd - $$lang_vars{ignorado_message}<br>\n";
					}
				}
				$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");

				next;

			}

			if ( $hostname_bbdd ne $hostname ) {
                $gip->debug("DEBUG 10: hostname_bbdd: $hostname_bbdd\n");
				$gip->update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$ip_version");
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$rtl_helper($hostname_bbdd :$$lang_vars{entrada_antigua_message}) $hostname :$$lang_vars{entrada_actualizada_message} :<b>$ip_ad</b></span><br>\n";
				} else {
					print "<b>$ip_ad</b>: $$lang_vars{entrada_actualizada_message}: $hostname ($$lang_vars{entrada_antigua_message}: $hostname_bbdd)<br>\n";
				}

				my $audit_type="1";
				my $audit_class="1";
				my $host_descr_audit = $host_descr;
				$host_descr_audit = "---" if $host_descr_audit eq "NULL";
				my $comentario_audit = $comentario;
				$comentario_audit = "---" if $comentario_audit eq "NULL";
				my $event="$ip_ad: $hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit -> $hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
				$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

			} elsif ( $ping_result == 1 && $hostname_bbdd eq "unknown" && $hostname eq "unknown" ) {
                $gip->debug("DEBUG 11: hostname_bbdd: $hostname_bbdd\n");
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{ignorado_message} ($$lang_vars{generico_message}) - $hostname_bbdd :$$lang_vars{tiene_entrada_message} :<b>$ip_ad</b></span><br>\n";
				} else {
					print "<b>$ip_ad</b>: $$lang_vars{tiene_entrada_message}: $hostname_bbdd - ($$lang_vars{generico_message}) $$lang_vars{ignorado_message}<br>\n";
				}

				$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");

			} elsif ( $ping_result == 1 && $hostname_bbdd eq $hostname ) {
                $gip->debug("DEBUG 12: hostname_bbdd: $hostname_bbdd\n");
				$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$rtl_helper(<b>$ip_ad: $$lang_vars{no_changes1_message}: $hostname_bbdd</b></span><br>\n";
				} else {
					print "<b>$ip_ad</b>: $hostname_bbdd: $$lang_vars{no_changes1_message}<br>\n";
				}
			} else {
                $gip->debug("DEBUG 13: hostname_bbdd: $hostname_bbdd\n");
				$gip->update_host_ping_info("$client_id","$ip_ad_int","$ping_result","$enable_ping_history","$ip_ad","$update_type_audit","$vars_file");
				if ( $vars_file =~ /vars_he$/ ) {
					print "<span style=\"float: $ori\">$rtl_helper($utype :$$lang_vars{update_type_message}) $$lang_vars{ignorado_message} - ($hostname : DNS) $$lang_vars{entrada_cambiado_message} :$hostname_bbdd :<b>$ip_ad</b></span><br>\n";
				} else {
					print "<b>$ip_ad</b>: $hostname_bbdd: $$lang_vars{entrada_cambiado_message} (DNS: $hostname) - $$lang_vars{ignorado_message} ($$lang_vars{update_type_message}: $utype)<br>\n";
				}
			}
		}

		next;

	}

	# no hostname_bbdd; 2: dns ok, ping ok; 3: dns ok, ping failed; 4: DNS not ok, ping OK
	if ( $exit eq 2 || $exit eq 3 || $exit eq 4 ) {
        $gip->debug("DEBUG 14: exit: $exit\n");
		if ( $exit eq 3 && $hostname eq "unknown" && $igno_set == "1" ) {
            $gip->debug("DEBUG 15: exit: $exit\n");
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{ignorado_message} - \"$igno_name\" $$lang_vars{tiene_string_no_ping_message} :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $$lang_vars{tiene_string_no_ping_message} \"$igno_name\" - $$lang_vars{ignorado_message}<br>\n";
			}

			next;

		} elsif ( $exit eq 3 && $ignore_dns ) {
            $gip->debug("DEBUG 16: exit: $exit\n");
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$rtl_helper$$lang_vars{ignorado_message} - $hostname_bbdd :$$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message} :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $$lang_vars{ignore_dns_activated_message} + $$lang_vars{no_ping_message} - $$lang_vars{ignorado_message}<br>\n";
			}

			next;

		}

		if ( $range_id eq "-1" ) {
            $gip->debug("DEBUG 17: exit: $exit\n");
			if ( ! $host_exists ) {
                $gip->debug("DEBUG 18: exit: $exit - INSERT: $ip_ad_int - $hostname - $host_descr - $loc_id - $int_admin - $cat_id - $comentario - $utype_id - $mydatetime - $red_num - $ping_result - $ip_version\n");

				$gip->insert_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$ip_version");
			} else {
                $gip->debug("DUPLICATED ENTRY IGNORED: $host_hash_ref->{$ip_ad_int}[0], $host_hash_ref->{$ip_ad_int}[1] - $ip_ad, $hostname\n");
			}
		} else {
            $gip->debug("DEBUG 19: exit: $exit\n");

			$gip->update_ip_mod("$client_id","$ip_ad_int","$hostname","$host_descr","$loc_id","$int_admin","$cat_id","$comentario","$utype_id","$mydatetime","$red_num","$ping_result","$ip_version");

		}
		if ( $exit eq 2 && $hostname eq "unknown" && $igno_set == "1") {
            $gip->debug("DEBUG 20: exit: $exit\n");
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">${rtl_helper}unknown :$$lang_vars{host_anadido_message} - \"$igno_name\" $$lang_vars{tiene_string_message} :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $$lang_vars{tiene_string_message} \"$igno_name\" - $$lang_vars{host_anadido_message}: unknown<br>\n";
			}
		} else {
            $gip->debug("DEBUG 21: exit: $exit\n");
			if ( $vars_file =~ /vars_he$/ ) {
				print "<span style=\"float: $ori\">$rtl_helper$hostname :$$lang_vars{host_anadido_message} :<b>$ip_ad</b></span><br>\n";
			} else {
				print "<b>$ip_ad</b>: $$lang_vars{host_anadido_message}: $hostname<br>\n";
			}
		}

		my $audit_type="15";
		my $audit_class="1";
		my $host_descr_audit = $host_descr;
		$host_descr_audit = "---" if $host_descr_audit eq "NULL";
		my $comentario_audit = $comentario;
		$comentario_audit = "---" if $comentario_audit eq "NULL";
#		my $event="$ip_ad: $hostname_bbdd,$host_descr_audit,$host_loc,$host_cat,$comentario_audit -> $hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
		my $event="$ip_ad: $hostname,$host_descr_audit,$host_loc,$host_cat,$comentario_audit";
		$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

	} else {
		if ( $vars_file =~ /vars_he$/ ) {
			print "<span style=\"float: $ori\">$$lang_vars{ignorado_message} - $$lang_vars{no_ping_message} + $$lang_vars{no_dns_message} :<b>$ip_ad</b></span><br>\n";
		} else {
			print "<b>$ip_ad</b>: $$lang_vars{no_dns_message} + $$lang_vars{no_ping_message} - $$lang_vars{ignorado_message}<br>\n";
		}
	} 
}

print "</span>";

my $audit_type="4";
my $audit_class="2";
my $event="$red/$BM";
$gip->insert_audit("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");

#update net usage
$gip->update_net_usage_cc_column("$client_id", "$ip_version", "$red_num","$BM","no_rootnet");


my $end_time=time();
my $duration=$end_time - $start_time;
my @parts = gmtime($duration);
my $duration_string = "";
$duration_string = $parts[2] . "h, " if $parts[2] != "0";
$duration_string = $duration_string . $parts[1] . "m";
$duration_string = $duration_string . " and " . $parts[0] . "s";
if ( $vars_file =~ /vars_he$/ ) {
	print "<br><p><span style=\"float: $ori\"><i>${duration_string} :$$lang_vars{execution_time_message}</i></style><br><p>\n";
} else {
	print "<br><p><i>$$lang_vars{execution_time_message}: ${duration_string}</i><p>\n";
}

#if ( $confirm_dns_delete ) {
#    print "<br><p><b>$$lang_vars{confirm_delete_message}</b><p>\n";
#} else {
#    print "<br><h3 style=\"float: $ori\">$$lang_vars{listo_message}</h3><br><p><br>\n";
#}

if ( $delete_hosts[0] ) {
    print "<br><p><b>$$lang_vars{confirm_delete_message}</b><p>\n";
    $j = 0;
    print "<form method=\"POST\" action=\"$server_proto://$base_uri/res/ip_deleteip.cgi\">\n";
    print "<table>\n";
    foreach ( @delete_hosts ) {
        my $ip_ad = $_;
        my $ip_ad_int = $gip->ip_to_int("$client_id","$ip_ad","$ip_version");
        print "<tr><td>";
        print "<input type=\"checkbox\" name=\"mass_update_host_submit_${j}\" id=\"mass_update_host_submit_${j}\" value=\"$ip_ad\">\n";
        print "</td><td>";
        print "$host_hash_ref->{$ip_ad_int}[0]";
        print "</td><td>";
        print "$host_hash_ref->{$ip_ad_int}[1]";
        print "</td></tr>";
        $j++;
    }
    print "</table><p>\n";
    print "<input name=\"anz_hosts\" type=\"hidden\" value=\"$j\">";
    print "<input name=\"mass_submit\" type=\"hidden\" value=\"mass_submit\">";
    print "<input name=\"ip_version\" type=\"hidden\" value=\"$ip_version\">";
    print "<input name=\"red_num\" type=\"hidden\" value=\"$red_num\">";
    print "<input type=\"submit\" value=\"$$lang_vars{borrar_message}\" name=\"borrar\" class=\"btn\">\n";
    print "</form>\n";
} else {
    print "<br><h3 style=\"float: $ori\">$$lang_vars{listo_message}</h3><br><p><br>\n";
}



$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");
