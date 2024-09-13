#!/usr/bin/perl -w

# This script updates the external MAC database
# GestioIP

# version 3.4.5 20190123

# usage: gip_process_mac.pl --help


use warnings;
use strict;
use Net::IP;
use Net::IP qw(:PROC);
use Carp;
use Fcntl qw(:flock);
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
if ( -e '/var/www/gestioip/modules' ) {
    use lib '/var/www/gestioip/modules';
} elsif ( -e '/srv/www/htdocs/gestioip/modules' ) {
    use lib '/srv/www/htdocs/gestioip/modules';
} elsif ( -e '/var/www/html/gestioip/modules' ) {
    use lib '/var/www/html/gestioip/modules';
}
use GestioIP;


my $log="/usr/share/gestioip/var/log/gip_process_mac.log";

my $verbose = 0;
my $debug = 0;
my $do_logging = 1;

my ($help, $mac, $insert, $delete, $config_name);

GetOptions(
        "config_file_name=s"=>\$config_name,
        "help!"=>\$help,
        "mac=s"=>\$mac,
        "delete!"=>\$delete,
        "insert!"=>\$insert,
        "x!"=>\$debug,
) or print_help();

if ( $help ) {
    print_help();
    exit;
}

$verbose = 1 if $debug;

my $base_dir="/usr/share/gestioip";
$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
        print "\nCan't find configuration file \"$config_name\"\n";
        print "\n\"$base_dir/etc/$config_name\" doesn't exists\n";
        exit 1;
}
my $conf = $base_dir . "/etc/" . $config_name;


my $gip = GestioIP -> new();

$gip->{format} = "SCRIPT";

my $datestring = localtime();
if ( $do_logging ) {
    open(LOG,">>$log") or die "Can not open $log: $!\n";
    print LOG "### Starting gip_pdns_sync.pl $datestring\n";
}

my %params;
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

my $table_name_mac = $params{'table_name_mac'} || "";
my $column_name_mac = $params{'column_name_mac'} || "";
my $client = $params{'client'} || "";
exit_error("No client found - Check parameter \"client\" in $conf") if ! $client;
my $client_id = get_client_id_from_name("$client");
exit_error("Client not found - Check parameter \"client\" in $conf") if ! $client_id;
print LOG "Client: $client - $client_id\n" if $do_logging;


exit_error("No MAC found - Please specify a MAC address") if ! $mac;
$mac = lc $mac;
exit_error("Format MAC incorrect - Please enter the MAC in the following format: 53:d2:8c:a1:c3:40") if $mac !~ /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/;
exit_error("No action found - Please specify either insert or delete") if ! $delete && ! $insert;

my $mac_exists = check_mac_exists("$mac");

# Errors
# 1 - general error
# 2 - MAC not found

if ($delete && ! $mac_exists ) {
    exit_error("MAC not found: $mac","2");
}

if ( $insert && ! $delete ) {
    if ($insert && $mac_exists ) {
        exit_error("MAC not found: $mac","2");
    }
    insert_mac("$mac");
    print LOG "MAC added: $mac\n" if $do_logging;
} elsif ( ! $insert && $delete) {
    delete_mac("$mac");
    print LOG "MAC deleted: $mac\n" if $do_logging;
} else {
    exit_error("Please specify either -i or -d");
}

close LOG if $do_logging;


###############
#### Subroutines

sub _mysql_connection {
    my $connect_error = "0";
    my $dbh = DBI->connect("DBI:mysql:$params{sid_gestioip}:$params{bbdd_host_gestioip}:$params{bbdd_port_gestioip}",$params{user_gestioip},$params{pass_gestioip}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}


sub _mysql_connection_mac {
    my $connect_error = "0";
    my $dbh = DBI->connect("DBI:mysql:$params{sid_mac}:$params{bbdd_host_mac}:$params{bbdd_port_mac}",$params{user_mac},$params{pass_mac}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}

sub check_mac_exists {
    my ( $mac ) = @_;
    my $dbh = _mysql_connection_mac();
    my $qmac = $dbh->quote( $mac );

    my $sth = $dbh->prepare("SELECT $column_name_mac FROM $table_name_mac WHERE mac=$qmac
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $mac = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    if ( $mac ) {
        return 1;
    } else {
        return;
    }
}

sub insert_mac {
    my ( $mac ) = @_;
    my $dbh = _mysql_connection_mac();
    my $qmac = $dbh->quote( $mac );

    my $sth = $dbh->prepare("INSERT INTO $table_name_mac ($column_name_mac) values ($qmac)
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}

sub delete_mac {
    my ( $mac ) = @_;
    my $dbh = _mysql_connection_mac();
    my $qmac = $dbh->quote( $mac );

    my $sth = $dbh->prepare("DELETE FROM $table_name_mac WHERE $column_name_mac=$qmac
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}

sub get_client_id_from_name {
    my ( $name ) = @_;
    my $id;
    my $dbh = _mysql_connection();
    my $qname = $dbh->quote( $name );

    my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qname
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $id;
}

sub exit_error {
    my ( $error, $sig ) = @_;

	$sig = 1 if ! $sig;
	
	print STDERR "\n$error\n\n" if $verbose;

	exit $sig;
}

sub print_help {
        print "\nusage: gip_process_mac.pl.pl [OPTIONS...]\n\n";
        print "-c, --config_file_name=config_file_name  name of the configuration file (without path)\n";
        print "-d, --delete             delete mac\n";
        print "-h, --help               help\n";
        print "-i, --insert             insert mac\n";
        print "-m, --mac=MAC-address    MAC address\n";
        print "-v, --verbose            verbose\n";
        print "-x, --debug              debug\n\n";
        print "\n\n\nconfiguration file: $conf\n\n" if $conf;
        exit;
}
