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


# check Permissions
my @global_config = $gip->get_global_config("$client_id");
my $user_management_enabled=$global_config[0]->[13] || "";
#if ( $user_management_enabled eq "yes" ) {
#	my $required_perms="read_host_perm";
#	$gip->check_perms (
#		client_id=>"$client_id",
#		vars_file=>"$vars_file",
#		daten=>\%daten,
#		required_perms=>"$required_perms",
#	);
#}

my $advanced = $daten{'advanced'} || "";
my $match = $daten{'match'} || "";
my $match_ip = $daten{'match_ip'} || "";
my $starts_with = $daten{'starts_with'} || "";

my $back_button="<p><br><p><FORM><INPUT TYPE=\"BUTTON\" VALUE=\"back\" ONCLICK=\"history.go(-1)\" class=\"error_back_link\"></FORM>";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{resultado_busqueda_message}","$vars_file");

my $acl_nr=$daten{acl_nr} || "";
my $purpose=$daten{purpose} || "";
my $status=$daten{status} || "";
my $src_vlan=$daten{src_vlan} || "";
my $source=$daten{source} || "";
my $src=$daten{src} || "";
my $application_protocol=$daten{application_protocol} || "";
my $proto_id=$daten{proto_id} || "";
my $src_port=$daten{src_port} || "";
my $bidirectional=$daten{bidirectional} || "";
my $dst_vlan=$daten{dst_vlan} || "";
my $destination=$daten{destination} || "";
my $dst=$daten{dst} || "";
my $encrypted_base_proto=$daten{encrypted_base_proto} || "";
my $remark=$daten{remark} || "";
my $no_acl=$daten{no_acl} || "";
my $exact_match=$daten{exact_match} || "";
if ( ! $acl_nr && ! $purpose &&  ! $status && ! $src_vlan && ! $source && ! $src && ! $application_protocol && ! $proto_id && ! $src_port && ! $bidirectional && ! $dst_vlan && ! $destination && ! $dst && ! $encrypted_base_proto && ! $remark && $no_acl ne "with_acl" && $no_acl ne "without_acl" && ! $match_ip && ! $match) {
    $gip->print_error("$client_id","$$lang_vars{insert_search_string_message}");
}

my @acls;
my @acls_match;

if ( $advanced ) {

    @acls = $gip -> search_acl_connection_advanced (
        client_id => ${client_id},
        acl_nr => ${acl_nr},
        purpose => ${purpose},
        status => ${status},
        src_vlan => ${src_vlan},
        source => ${source},
        src => ${src},
        application_protocol => ${application_protocol},
        proto_id => ${proto_id},
        src_port => ${src_port},
        bidirectional => ${bidirectional},
        dst_vlan => ${dst_vlan},
        destination => ${destination},
        dst => ${dst},
        encrypted_base_proto => ${encrypted_base_proto},
        remark => ${remark},
        exact_match => ${exact_match},
        no_acl => ${no_acl},
    );

} else {
	if ( $match && ! $starts_with ) {
		@acls = $gip->search_acl_connection("$client_id", "$match");
	} elsif ( $starts_with ) {
		$gip->print_error("$client_id","$$lang_vars{only_number_search_message}") if $match !~ /^\d+$/;
		@acls = $gip->search_acl_connection_starts_with("$client_id", "$match");
	} else {
		@acls = $gip->get_acl_connections("$client_id");
		my $i = 0;
	# SELECT id, acl_nr, purpose, status, src_vlan, source, src, application_protocol, proto_id, src_port, bidirectional, dst_vlan, destination, dst, encrypted_base_proto, remark, client_id
		foreach ( @acls ) {
			my $src = $acls[$i]->[6];
			my $dst = $acls[$i]->[13];

			my $src_mask = "";
			if ( $src =~ /\// ) {
				$src =~ /^(.+)\/(.+)$/;
				$src = $1 || "";
				$src_mask = $2 || "";
			} else {
				$src_mask = 32;
			}

			my $dst_mask = "";
			if ( $dst =~ /\// ) {
				$dst =~ /^(.+)\/(.+)$/;
				$dst = $1 || "";
				$dst_mask = $2 || ""; 
			} else {
				$dst_mask = 32;
			}

			my $red_src = "$src/$src_mask";
			my $ipob_src = new Net::IP ($red_src);
			my $red_dst = "$dst/$dst_mask";
			my $ipob_dst = new Net::IP ($red_dst);
			my $ipm = "$match_ip/32";
			my $ipmob = new Net::IP ($ipm);

			if ( ! $ipob_src || ! $ipob_dst || ! $ipmob ) {
				# error creating ip objects - ignore entry
				$i++;
				next;
			}    
			if ( $ipmob->overlaps($ipob_src) == $IP_NO_OVERLAP && $ipmob->overlaps($ipob_dst) == $IP_NO_OVERLAP) {
				# no overlap
				$i++;
				next;
			}

			push @acls_match, $_;

			$i++;
		}

		@acls = @acls_match;
	}
}

if ( $acls[0] ) {
        $gip->PrintACLConnectionTab("$client_id",\@acls,"$vars_file","$match","$starts_with");
} else {
my $starts_with_checked = "";
$starts_with_checked ="checked" if $starts_with eq "y";
print <<EOF;
<form name="search_acl_connection" method="POST" action="$server_proto://$base_uri/ip_search_acl_connection.cgi" style="display:inline">
<input type="hidden" name="client_id" value="$client_id"><input type="submit" value="" class="button" style=\"float: right; cursor:pointer;\"><input type=\"text\" size=\"15\" name=\"match\" value=\"$match\" style=\"float: right; margin-left: 1em;\"><input type=\"checkbox\" name=\"starts_with\" value=\"y\" style=\"float: right;\" $starts_with_checked><span style=\"float: right; margin-right: 0.5em;\">ID starts with</span> 
</form>
<br><p><br><p>
EOF
        print "<p class=\"NotifyText\">$$lang_vars{no_resultado_message}</p><br>\n";

}

$gip->print_end("$client_id","$vars_file","go_to_top", "$daten");

