#!/usr/bin/perl -w


# gip_check_hosts.pl version 3.4.1 20190308

use warnings;
use strict;
use Net::IP;
use Net::IP qw(:PROC);
use Carp;
use Fcntl qw(:flock);
use FindBin qw($Bin);
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use DBI;


my $base_dir = "/usr/share/gestioip";
my $fping = "/usr/bin/fping";
if ( ! -x $fping ) {
	print "fping not found.\n\nPlease install fping or change the path to fping directly in this script\n";
	exit 1;
}

#my ( $verbose, $log, $mail, $help, $import_host_routes, $debug, $report_not_found_networks, $get_vrf_routes, $ascend, $descend );
my ( $verbose, $log, $mail, $help, $client_id, $debug, $conf, $sync_networks, $unknown_hosts );
my $config_name="";
my $check_targets="";
my $set_sync_flag=0;
my $only_added_mail=0;

GetOptions(
        "client_id=s"=>\$client_id,
        "verbose!"=>\$verbose,
#        "log=s"=>\$log,
        "config_file=s"=>\$conf,
#        "mail!"=>\$mail,
        "file!"=>\$check_targets,
#        "unknown_hosts!"=>\$unknown_hosts,
        "sync_networks!"=>\$sync_networks,
        "help!"=>\$help,
#        "x!"=>\$debug,
#        "help!"=>\$help
) or print_help();

print_help() if $help;

if ( $client_id && $client_id !~ /\d{1,4}/ ) {
	print "\nInvalid client_id\n";
	exit 1;
}
$client_id = 1 if ! $client_id;

$conf = $base_dir . "/etc/ip_update_gestioip.conf" if ! $conf;

my %params;
$conf = $base_dir . "/etc/ip_update_gestioip.conf" if ! $conf;
get_params("$conf");


my $lockfile = $base_dir . "/var/run/" . $client_id . "_gip_check_hosts.lock";
no strict 'refs';
open($lockfile, '<', $0) or die("Unable to create lock file: $!\n");
use strict;
unless (flock($lockfile, LOCK_EX|LOCK_NB)) {
print "$0 is already running. Exiting.\n";
exit(1);
}



my @nets;

# use check_targets as default
if ( $sync_networks && $check_targets ) {
    print "\nSpecify either the -s or -f option\n\n";
    print_help();
} elsif ( $sync_networks ) {
    @nets = get_vigilada_redes("$client_id","","v4");
    if ( ! $nets[0] ) {
        print '\nNo networks with checked "sync" flag found\n\n';
        print_help();
        exit
    }
} elsif ( $check_targets ) {
	$check_targets="/usr/share/gestioip/etc/check_targets";

	open(IN,"<$check_targets") or die "Can't open $check_targets: $!\n";

	while (<IN>) {
		my $net = $_;
		my @net;
		next if $net =~ /^#/;
		next if $net !~ /.+/;
		chomp ($net);
		$net =~ /^(.+)\/(.+)$/;
		my $ip = $1;
		my $BM = $2;
		if ( ! $ip || ! $BM ) {
			print "\nInvalid network: $net - ignored\n" if $verbose;
			next;
		}
		push @net, $ip;
		push @net, $BM;
		push @nets, \@net;
	}

	if ( ! $nets[0] ) {
		print "\nNo valid networks to scan found\n\n";
        print_help();
		exit 1;
	}
} else {
    print "\nSpecify eiter -s or -f\n\n";
    print_help();
}


for my $net_data (@nets) {
    my %ping_result;

    my $ip = "$net_data->[0]";
    my $BM = "$net_data->[1]";
    my $net = $ip . '/' . $BM;

    print "PROCESSING NET: $net\n" if $verbose;

	my $red_num;
	if ( exists $net_data->[2] ) {
		$red_num = "$net_data->[2]";
    }

	if ( ! $red_num ) {
		$red_num = check_red_exists("$client_id", $ip, $BM, "1");
	}

	if ( ! $red_num ) {
		print "Red ID not found: $net - ignoring network\n" if $verbose;
		next;
    }

	my $host_hash = get_host_hash_check_from_rednum("$client_id", "$red_num");

#    my @alive = `/usr/bin/fping -r2 -g $net 2> /dev/null`;
    my @alive = `$fping -r2 -g $net 2> /dev/null`;

    for my $out (@alive) {
        my $host;
        if ( $out =~ /alive/ ) {
            $out =~ /^(.*) is alive/;
            $host = $1;
            $ping_result{$host} = 1 if $host;
        } else {
            $out =~ /^(.*) is unreachable/;
            $host = $1;
            $ping_result{$host} = 0 if $host;
        }
        my $ip_int=ip_to_int("$host","v4");
    }

	# Update ping info
	foreach my $ip ( keys %ping_result ) {
        # process only host which are already in the database
		if ( exists $host_hash->{$ip} ) {
			my $alive = $ping_result{$ip} || 0;
			my $host_id = $host_hash->{$ip}[0];
			my $alive_bbdd = $host_hash->{$ip}[1] || 0;
			
            my $status = "DOWN";
            $status = "UP" if $alive == 1;
            my $status_bbdd = "DOWN";
            $status_bbdd = "UP" if $alive_bbdd == 1;
			if ( $alive != $alive_bbdd ) {
				update_host_ping_info("$client_id","$host_id","$alive_bbdd","$alive","$ip","1");
				print "$ip: STATUS CHANGED ($status_bbdd > $status)\n" if $verbose;
			} else {
				print "$ip: STATUS UNCHANGED ($status)\n" if $verbose;
			}
		} else {
            # Host do not exist in the database - do nothing
			my $alive = $ping_result{$ip} || 0;
            my $status = "UP";
            if ( $alive == 1 ) {
				print "$ip: UNKNOWN HOST ($status)\n" if $verbose;
            }
		}
	}
}


#### Subroutines

sub check_red_exists {
    my ( $client_id, $net, $BM, $ignore_rootnet ) = @_;
    my $red_check="";
    $ignore_rootnet=1 if $ignore_rootnet eq "";
    my $ignore_rootnet_expr="AND rootnet='0'";
    if ( $ignore_rootnet == 0 ) {
        $ignore_rootnet_expr="AND rootnet='1'";
    }
    my $dbh = _mysql_connection();
    my $qnet = $dbh->quote( $net );
    my $qBM = $dbh->quote( $BM );
    my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT red_num FROM net WHERE red=$qnet AND BM=$qBM AND client_id = $qclient_id $ignore_rootnet_expr
					") or die "Can not execute statement: $dbh->errstr";
	$sth->execute() or die "Can not execute statement: $dbh->errstr";
	$red_check = $sth->fetchrow_array;
	$sth->finish();
	$dbh->disconnect;

    return $red_check;
}

sub ip_to_int {
        my ($ip,$ip_version)=@_;
        my ( $ip_bin, $ip_int);
        if ( $ip_version eq "v4" ) {
                $ip_bin = ip_iptobin ($ip,4);
                $ip_int = new Math::BigInt (ip_bintoint($ip_bin));
        } else {
                my $ip=ip_expand_address ($ip,6);
                $ip_bin = ip_iptobin ($ip,6);
                $ip_int = new Math::BigInt (ip_bintoint($ip_bin));
        }
        return $ip_int;
}

sub get_host_hash_check_from_rednum {
    my ( $client_id,$red_num ) = @_;

    my %values_ip = ();
    my $ip_ref;
    my $dbh = _mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qred_num = $dbh->quote( $red_num );

#    my $sth = $dbh->prepare("SELECT ip, id, hostname, alive, ip_version FROM host WHERE red_num=$qred_num AND client_id = $qclient_id ORDER BY INET_NTOA(ip)") or die "Can not execute statement: $dbh->errstr";
    my $sth = $dbh->prepare("SELECT ip, INET_NTOA(ip), id, hostname, alive, ip_version FROM host WHERE red_num=$qred_num AND client_id = $qclient_id ORDER BY INET_NTOA(ip)") or die "Can not execute statement: $dbh->errstr";

    $sth->execute() or die "$DBI::errstr";

    my $i=0;
    my $j=0;
    my $k=0;
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $hostname = $ip_ref->{'hostname'} || "";
        next if ! $hostname;
        my $ip_int = $ip_ref->{'ip'} || "";
        my $id = $ip_ref->{'id'} || "";
        my $ip_version = $ip_ref->{'ip_version'} || "";
        my $alive = $ip_ref->{'alive'} || "";
        my $ip;
        if ( $ip_version eq "v4" ) {
            $ip = $ip_ref->{'INET_NTOA(ip)'};
        } else {
            $ip = int_to_ip("$ip_int","$ip_version");
        }
        push @{$values_ip{$ip}},"$id","$alive";
    }

    $dbh->disconnect;
    return \%values_ip;
}


sub _mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$params{sid_gestioip}:$params{bbdd_host_gestioip}:$params{bbdd_port_gestioip}",$params{user_gestioip},$params{pass_gestioip}) or die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}

sub get_params {
	open(VARS,"<$conf") or die "Can not open $conf: $!\n";
	while (<VARS>) {
		chomp;
		s/#.*//;
		s/^\s+//;
		s/\s+$//;
		next unless length;
		my ($var, $value) = split(/\s*=\s*/, $_, 2);
		$params{$var} = $value;
	}
	close VARS;
}

#update host's alive field and last ping response field, given the ip_int and ping result
# Ping result should be 1 for a successful ping response and 0 for no response
sub update_host_ping_info {
    my ( $client_id,$id,$ping_result_bbdd,$ping_result,$enable_ping_history, $ip, $update_type_audit) = @_;

    $enable_ping_history="" if ! $enable_ping_history;
    $update_type_audit="1" if ! $update_type_audit; # "auto"

    my $dbh = _mysql_connection();
    my $qid = $dbh->quote( $id );

    my $qmydatetime = $dbh->quote( time() );
    my $alive = $dbh->quote( $ping_result );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth;

    $sth = $dbh->prepare("UPDATE host SET alive=$alive, last_response=$qmydatetime WHERE id=$qid") or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    $sth->finish();
    $dbh->disconnect;

    if ( $enable_ping_history eq 1 && $ping_result_bbdd ne $ping_result ) {
        my $ping_state_old;
        my $ping_state_new;
        if ( $ping_result_bbdd eq 1 ) {
            $ping_state_old="up";
            $ping_state_new="down";
        } else {
            $ping_state_old="down";
            $ping_state_new="up";
        }


        my $audit_type="100";
        my $audit_class="2";
        my $event="$ip: $ping_state_old -> $ping_state_new";
        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit");
    }
}

sub insert_audit_auto {
	my ($client_id,$event_class,$event_type,$event,$update_type_audit) = @_;
    my $user=$ENV{'USER'};
    my $mydatetime=time();
    my $dbh = mysql_connection();
    my $qevent_class = $dbh->quote( $event_class );
    my $qevent_type = $dbh->quote( $event_type );
    my $qevent = $dbh->quote( $event );
    my $quser = $dbh->quote( $user );
    my $qupdate_type_audit = $dbh->quote( $update_type_audit );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qclient_id)") or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    $sth->finish();
}

sub get_vigilada_redes {
    my ( $client_id,$red,$ip_version ) = @_;
    my $ip_ref;
    $ip_version="" if ! $ip_version;
    my $ip_version_expr="";
    if ( $ip_version eq "v4" ) {
        $ip_version_expr="AND ip_version='v4'";
    } elsif ( $ip_version eq "v6" ) {
        $ip_version_expr="AND ip_version='v6'";
    }
    my @vigilada_redes;
        my $dbh = _mysql_connection();
        my $sth = $dbh->prepare("SELECT red, BM, red_num, loc, dyn_dns_updates FROM net WHERE vigilada=\"y\" AND client_id=\"$client_id\" AND rootnet = 0 $ip_version_expr ORDER BY ip_version,INET_ATON(red)");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @vigilada_redes, [ @$ip_ref ];
        }
    $sth->finish();
        $dbh->disconnect;
        return @vigilada_redes;
}

sub print_help {
    print "\nusage: gip_check_hosts.pl [OPTIONS...]\n\n";
    print "\nThis script updates the alive status of the host in the GestioIP database. To specify the networks which should be scanned, specify eiter the -f or -s option\n\n";
    print "-c, --config_file=config_file  Full path and name of the configuration file\n\t\tDefault: /usr/share/gestioip/etc/ip_update_gestioip.conf\n";
    print "-h, --help\thelp\n";
    print "-i, --client_id\tClient ID. Default: 1\n";
#    print "-l, --log=logfile    logfile\n";
    print "-f,\t\tRead networks from /usr/share/gestioip/etc/check_targets\n";
    print "-s,\t\tScan networks with \"sync\" flag\n";
    print "-v, --verbose\tverbose\n";
#    print "-x, --x              debug\n\n";
    print "\n\nconfiguration file: $conf\n\n" if $conf;
    exit;
}

