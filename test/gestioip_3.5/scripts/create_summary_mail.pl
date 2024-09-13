#!/usr/bin/perl -w


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

# v3.5.4.0 20201117

use strict;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use Date::Calc qw(N_Delta_YMDHMS);
use DBI;
#use Time::Local;
#use Time::localtime;
use Time::HiRes qw(sleep);
use Mail::Mailer;
use FindBin qw($Bin);
use File::stat;
use Socket;


my $dir = $Bin;
$dir =~ /^(.*)\/bin/;
my $base_dir=$1;

my ( $help, $verbose, $days, $log_dir, $config_name );

GetOptions(
	"config_name=s"=>\$config_name,
	"days=s"=>\$days,
	"log_dir=s"=>\$log_dir,
	"help!"=>\$help,
	"verbose!"=>\$verbose,
) or print_help();


$days=1 if ! $days;
if ( $days !~ /^\d{1,3}$/ || $days < 0 || $days > 365 ) {
print "-d argument must be a number between 1 and 365\n\n";
print_help();
}
$days--;

$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
	print "\nCan't find configuration file \"$config_name\"\n";
	print "\n\"$dir/$config_name\" doesn't exists\n";
	exit 1;
}
my $conf = $base_dir . "/etc/" . $config_name;

if ( $help ) { print_help(); }

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

my $lang=$params{lang} || "en";
my $vars_file=$base_dir . "/etc/vars/vars_update_gestioip_" . "$lang";

my %lang_vars;

open(LANGVARS,"<$vars_file") or die "Can no open $vars_file: $!\n";
while (<LANGVARS>) {
	chomp;
	s/#.*//;
	s/^\s+//;
	s/\s+$//;
	next unless length;
	my ($var, $value) = split(/\s*=\s*/, $_, 2);
	$lang_vars{$var} = $value;
}
close LANGVARS;

my $log="/tmp/create_summary_mail.log";
open(LOG,">$log") or die "$log: $!\n";

my $mail_destinatarios="";
my $mail_from="";
if ( ! $params{mail_destinatarios} ) {
	print "\nPlease specify the recipients to send the mail to (\"mail_destinatarios\") in $conf\n\n";
	print_help();
	exit 1;
}
if ( ! $params{mail_from} ) {
	print "\nPlease specify the mail sender address (\"mail_from\") in $conf\n\n";
	print_help();
	exit 1;
}
$mail_destinatarios = \$params{mail_destinatarios};
$mail_from = \$params{mail_from};

if ( $params{pass_gestioip} !~ /.+/ ) {
	print  "\nERROR\n\n$lang_vars{no_pass_message} $conf)\n\n";
	exit 1;
}

my $client_name_conf = $params{client};
my $client_count = count_clients();
my $client_id;
if ( $client_count == "1" ) {
	my $one_client_name = check_one_client_name("$client_name_conf") || "";
	if ( $one_client_name eq $client_name_conf || $client_name_conf eq "DEFAULT" ) {
			$client_id=get_client_id_one() || "";
        }
} else {
        $client_id=get_client_id_from_name("$client_name_conf") || "";
}

if ( ! $client_id ) {
        print "$client_name_conf: $lang_vars{client_not_found_message} $conf\n";
        exit 1;
}

if ( ! $log_dir ) {
	$log_dir="$params{logdir}" if $params{logdir};
}

if ( ! $log_dir ) {
	print "Please specify the directory where the logfiles are stored";
	exit 1;
}


my @log_files = glob($log_dir . '/' . '*');

if ( ! $log_files[0] ) {
	print "No logfiles found\n";
	exit 1;
}


my ($s,$mm,$h,$d,$m,$y,$wday,$yday,$isdst) = localtime(time);
$m++;
$y+=1900;


@log_files=sort @log_files;

my %ip_hash_dns;
my %ip_hash_snmp;
my %ip_hash_net;
my $origin_script;
foreach my $logfile ( @log_files ) {
#	print "TEST: $logfile\n" if $verbose;
	next if $logfile !~ /.*(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})_${client_name_conf}.*/;
	$logfile =~ /.*(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2}).*/;
	my $y2=$1;
	my $m2=$2;
	my $d2=$3;
	my $h2=$4;
	my $mm2=$5;
	my $s2=$6;

	if ( $logfile =~ /ip_update_gestioip_snmp/ ) {
		$origin_script="snmp";
	} elsif ( $logfile =~ /ip_update_gestioip_dns/ ) {
		$origin_script="dns";
	} elsif ( $logfile =~ /get_networks_snmp/ ) {
		$origin_script="net";
	}


	my ($D_y,$D_m,$D_d, $Dhh,$Dmm,$Dss) = N_Delta_YMDHMS($y2,$m2,$d2,$h2,$mm2,$s2, $y,$m,$d,$h,$mm,$s);



	if ($D_y == 0 && $D_m == 0 && $D_d <= $days ) {
#		print "TEST DELTA: $logfile: year: $D_y, month: $D_m, days: $D_d, hours: $Dhh, minutes: $Dmm, seconds: $Dss\n";
		open (FILE,"<$logfile");
		while (<FILE>) {
			if ( $_ =~ /ignored/ ) {
				next;
			}

			if ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:/ || $_ =~ /^Found in Arp-cache of/ ) {
				my $ip;
				my $event;
				if ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:/ ) {
					# 127.0.0.1: has already an entry in the database: localhost - ignored
					# 127.0.0.2: entry added: unknown
					# 127.0.0.2: hostname updated: unknown
					# 127.0.0.2: entry deleted: unknown
					# 127.0.0.2: updated: unknown
					# 127.0.0.2: auto generic name....
					# 127.0.0.2: generic dyn name....
					$_ =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}): (.*)/;
					$ip=$1;
					$event=$2;
				} elsif ( $_ =~ /^Found in Arp-cache of/ ) {
					$_ =~ /^Found in Arp-cache of (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}): (.*)/;
					$ip=$1;
					$event="Found in Arp-cache: $2";
				}

				if ( $origin_script eq "dns" ) {
					push @{$ip_hash_dns{$ip}{"event"}},"$event";
					push @{$ip_hash_dns{$ip}{"date"}},"$y2$m2$d2$h2$mm2";
				} elsif ( $origin_script eq "snmp" ) {
					push @{$ip_hash_snmp{$ip}{"event"}},"$event";
					push @{$ip_hash_snmp{$ip}{"date"}},"$y2$m2$d2$h2$mm2";
				} elsif ( $origin_script eq "net" ) {
				}
			} elsif ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$/  && ( $origin_script eq "dns" || $origin_script eq "snmp" )) {
				my $ip;
				my $mask;
				my $event;
#print "TEST FOUND: $logfile - $_\n";
				if ( $_ =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2})$/ ) {
					# network entry z.b.
					# 127.0.0.0/29
					$_ =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2})/;
					$ip=$1;
					$mask=$2;
				}

				$ip_hash_dns{$ip}{"mask"}="$mask";
				$ip_hash_snmp{$ip}{"mask"}="$mask";

			} elsif ( $_ =~ /^Host added \(\/\d{1,2} route from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/ ) {
				# Host added (/32 route from 2.2.2.2): 1.1.1.1 - unknown
				$_ =~ /^Host added \(\/\d{1,2} route from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/;
				my $ip=$1;
				my $event=$_;
				chomp($event);
				push @{$ip_hash_net{$ip}{"event"}},"$event";
				push @{$ip_hash_net{$ip}{"date"}},"$y2$m2$d2$h2$mm2";
			} elsif ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}:? .*/ && $origin_script eq "net") {
				# 1.1.15.0/30: ADDED
				# 213.73.39.0/24 overlaps with 213.73.39.0/24 -  ignored
				$_ =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/(\d{1,2}):? (.*)/;
				my $ip=$1;
				my $mask=$2;
				my $event=$3;

				push @{$ip_hash_net{$ip}{"event"}},"$event";
				$ip_hash_net{$ip}{"mask"}="$mask";
				push @{$ip_hash_net{$ip}{"date"}},"$y2$m2$d2$h2$mm2";
#print "TESTY: ADDED: $ip - $event - DATE: $ip_hash_net{$ip}{'date'}[0]\n";
			} elsif ( $_ =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:? .*/ && $origin_script eq "net") {
				# 1.1.1.2/255.255.255.255: HOSTROUTE - ignored
				$_ =~ /^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:? (.*)/;
				my $ip=$1;
				my $event=$2;
				my $mask=32;

				push @{$ip_hash_net{$ip}{"event"}},"$event";
				$ip_hash_net{$ip}{"mask"}="$mask";
				push @{$ip_hash_net{$ip}{"date"}},"$y2$m2$d2$h2$mm2";
#			} elsif ( $_ =~ /Importing networks from/ && $origin_script eq "net" ) {
#				# +++ Importing networks from $node +++
#				$_ =~ /.*Importing networks from (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/;
#				my $ip=$1;
#				my $event="Importing networks from";
#print "TEST TEST TEST: MESS: Importing networks from - $ip\n";
#				push @{$ip_hash_net{$ip}{"event"}},"$event";
#				$ip_hash_net{$ip}{"host"}++;
			}
		}
		close FILE;
	}
}

my @sortedKeys_ip_hash_dns = map { inet_ntoa($_) }
               sort map { inet_aton($_) }
                keys %ip_hash_dns;

my @sortedKeys_ip_hash_snmp = map { inet_ntoa($_) }
               sort map { inet_aton($_) }
                keys %ip_hash_snmp;

my @sortedKeys_ip_hash_net = map { inet_ntoa($_) }
               sort map { inet_aton($_) }
                keys %ip_hash_net;


print "SUMMARY Network import:\n\n" if $verbose;
print LOG "SUMMARY Network import:\n\n";
foreach my $ip_key( @sortedKeys_ip_hash_net ) {
	if ( $ip_hash_net{$ip_key}{"host"} ) {
		print "\nProcessing host $ip_key\n" if $verbose;
		print LOG "\nProcessing host $ip_key\n";
	} else {
		for my $ip_event_arr ( $ip_hash_net{$ip_key}{"event"} ) {
			my $mask=$ip_hash_net{$ip_key}{"mask"} || "";
			my $different_events=0;
			my $old_ip_event="";
			my $i=0;
			foreach my $ip_event ( @$ip_event_arr ) {
				if ( $old_ip_event ne $ip_event && $i > 0 ) {
					$different_events=1;
				}	
				$old_ip_event=$ip_event;
				$i++;
			}
			my $ip_key_mask=$ip_key;
			$ip_key_mask = $ip_key . "/" . $mask if $mask;
			if ( $different_events == 0 ) {
				print "------------: $ip_key_mask: $old_ip_event\n" if $verbose;
				print LOG "------------: $ip_key_mask: $old_ip_event\n";
			} else {
				my $j=0;
				foreach my $ip_event ( @$ip_event_arr ) {
					my $date=$ip_hash_net{$ip_key}{"date"}[$j];
					print "$date: $ip_key_mask: $ip_event\n" if $verbose;
					print LOG "$date: $ip_key_mask: $ip_event\n";
					$j++;
				}
			}
		}
	}
}

print "\nSUMMARY update against DNS:\n\n" if $verbose;
print LOG "\nSUMMARY update against DNS:\n\n";
foreach my $ip_key( @sortedKeys_ip_hash_dns ) {
	for my $ip_event_arr ( $ip_hash_dns{$ip_key}{"event"} ) {
		if ( $ip_hash_dns{$ip_key}{"mask"} ) {
			my $mask=$ip_hash_dns{$ip_key}{"mask"};
			print "\n$ip_key/$mask\n\n" if $verbose;
			print LOG "\n$ip_key/$mask\n\n";
		} else {
			my $different_events=0;
			my $old_ip_event="";
			my $i=0;
			foreach my $ip_event ( @$ip_event_arr ) {
				if ( $old_ip_event ne $ip_event && $i > 0 ) {
					$different_events=1;
				}	
				$old_ip_event=$ip_event;
				$i++;
			}
			if ( $different_events == 0 ) {
				print "------------: $ip_key: $old_ip_event\n" if $verbose;
				print LOG "------------: $ip_key: $old_ip_event\n";
			} else {
				my $j=0;
				foreach my $ip_event ( @$ip_event_arr ) {
					my $date=$ip_hash_dns{$ip_key}{"date"}[$j];
					print "$date: $ip_key: $ip_event\n" if $verbose;
					print LOG "$date: $ip_key: $ip_event\n";
					$j++;
				}
			}
		}
	}
}

print "\nSUMMARY update via SNMP:\n\n" if $verbose;
print LOG "\nSUMMARY update via SNMP:\n\n";
foreach my $ip_key( @sortedKeys_ip_hash_snmp ) {
	for my $ip_event_arr ( $ip_hash_snmp{$ip_key}{"event"} ) {
		if ( $ip_hash_snmp{$ip_key}{"mask"} ) {
			my $mask=$ip_hash_snmp{$ip_key}{"mask"};
			print "\n$ip_key/$mask\n\n" if $verbose;
			print LOG "\n$ip_key/$mask\n\n";
		} else {
			my $different_events=0;
			my $old_ip_event="";
			my $i=0;
			foreach my $ip_event ( @$ip_event_arr ) {
				if ( $old_ip_event ne $ip_event && $i > 0 ) {
					$different_events=1;
				}	
				$old_ip_event=$ip_event;
				$i++;
			}
			if ( $different_events == 0 ) {
				print "------------: $ip_key: $old_ip_event\n" if $verbose;
				print LOG "------------: $ip_key: $old_ip_event\n";
			} else {
				my $j=0;
				foreach my $ip_event ( @$ip_event_arr ) {
					my $date=$ip_hash_snmp{$ip_key}{"date"}[$j];
					print "$date: $ip_key: $ip_event\n" if $verbose;
					print LOG "$date: $ip_key: $ip_event\n";
					$j++;
				}
			}
		}
	}
}

close LOG;

send_mail();

###### Subroutines


sub print_help {
        print "\nusage: create_summary_mail.pl [OPTIONS...]\n\n";
	print "-c, --config_file_name=config_file_name  name of the configuration file (without path)\n";
        print "-d, --days=NUMBER	number of day which should be processed\n";
	print "-l, --log_dir=log_directory        directory where the logfiles are stored\n";
        print "-v, --verbose            verbose\n";
        print "\n\nconfiguration file: $conf\n\n";
        exit;
}

sub send_mail {
        my $mailer;
        my $added_count=0;
        if ( $params{smtp_server} ) {
                $mailer = Mail::Mailer->new('smtp', Server => $params{smtp_server});
        } else {
                $mailer = Mail::Mailer->new("");
        }
        $mailer->open({ From    => "$$mail_from",
                        To      => "$$mail_destinatarios",
                        Subject => "Resultado update BBDD GestioIP DNS"
                     }) or die "error while sending mail: $!\n";
        open (LOG_MAIL,"<$log") or die "can not open log file: $!\n";
        while (<LOG_MAIL>) {
                print $mailer $_ if $_ !~ /$lang_vars{ignorado_message}/;
        }

        print $mailer "\n\n\n\n\n\n\n\n\n--------------------------------\n\n";
        print $mailer "This is an automatically generated mail\n";
        $mailer->close;
        close LOG;
}

sub count_clients {
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT count(*) FROM clients
                        ") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub check_one_client_name {
        my ($client_name) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT client FROM clients WHERE client=\"$client_name\"
                        ") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}

sub get_client_id_one {
    my ($client_name) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT id FROM clients
                        ") or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}


sub get_client_id_from_name {
        my ( $client_name ) = @_;
        my $val;
        my $dbh = mysql_connection();
        my $qclient_name = $dbh->quote( $client_name );
        my $sth = $dbh->prepare("SELECT id FROM clients WHERE client=$qclient_name");
        $sth->execute() or  die "Can not execute statement:$sth->errstr";
        $val = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
        return $val;
}


sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$params{sid_gestioip}:$params{bbdd_host_gestioip}:$params{bbdd_port_gestioip}",$params{user_gestioip},$params{pass_gestioip}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}


