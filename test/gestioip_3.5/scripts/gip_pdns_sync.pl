#!/usr/bin/perl

# This script passes changes in the powerdns mysql backend to
# GestioIP

# version 3.5.5 20201218

# usage: gip_pdns_sync.pl --help


use warnings;
use strict;
use Net::IP;
use Net::IP qw(:PROC);
use Carp;
use Fcntl qw(:flock);
use FindBin qw($Bin);
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


my $verbose = 0;
my $debug = 0;
my $init_gip = 0;

my ($help, $config_name, $v4, $v6);

GetOptions(
        "debug!"=>\$debug,
        "help!"=>\$help,
        "init_gip!"=>\$init_gip,
        "verbose!"=>\$verbose,
        "config_file_name=s"=>\$config_name,
) or print_help();

if ( $help ) {
    print_help();
    exit;
}

$verbose = 1 if $debug;

my $dir = $Bin;
$dir =~ /^(.*)\/bin/;
my $base_dir=$1;
if ( ! -e "${base_dir}" ) {
        print "\nCan't find base directory \"$base_dir\"\n";
        exit 1;
}

$config_name="ip_update_gestioip.conf" if ! $config_name;
if ( ! -r "${base_dir}/etc/${config_name}" ) {
        print "\nCan't find configuration file \"$config_name\"\n";
        print "\n\"$base_dir/etc/$config_name\" doesn't exists\n";
        exit 1;
}
my $conf = $base_dir . "/etc/" . $config_name;


my $dyn_dns_updates = 3;
my $file = $base_dir . "/var/data/zone_records_check.txt";
my $exclude_file = $base_dir . "/var/data/exclude_records_check.txt";
my $log = $base_dir . "/var/log/gip_pdns_sync.log";

my $gip = GestioIP -> new();

$gip->{format} = "SCRIPT";

my $datestring = localtime();
open(LOG,">>$log") or die "Can not open $log: $!\n";
print LOG "### Starting gip_pdns_sync.pl $datestring\n";

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

my $client = $params{'client'} || "";
exit_error("No client found - Check parameter \"client\" in $conf") if ! $client;
my $client_id = get_client_id_from_name("$client");
exit_error("Client not found - Check parameter \"client\" in $conf") if ! $client_id;
print LOG "Client: $client - $client_id\n";

# create lock
my $lockfile = $base_dir . "/var/run/" . $client . "gip_pdns_sync.pl.lock";
no strict 'refs';
open($lockfile, '<', $0) or die("Unable to create lock file: $!\n");
use strict;
unless (flock($lockfile, LOCK_EX|LOCK_NB)) {
    print "$0 is already running. Exiting.\n";
    exit(1);
}


my $count = 0;
my $countu = 0;
my $counti = 0;
my $countd = 0;
my $countu6 = 0;
my $counti6 = 0;
my $countd6 = 0;


my @values_host_redes4 = get_host_redes_no_rootnet("$client_id","v4");
my $values_host_redes4_count = @values_host_redes4;
print LOG "Number networks IPv4: $values_host_redes4_count\n" if $debug;
my @values_host_redes6 = get_host_redes_no_rootnet("$client_id","v6");
my $values_host_redes6_count = @values_host_redes6;
print LOG "Number networks IPv6: $values_host_redes6_count\n" if $debug;
my @values_pdns_data_n = get_pdns_data();
my @values_pdns_data;
my @values_pdns_data_old;
my %values_pdns_data_hash = get_pdns_data_hash();
my %values_pdns_data_hash_old;
my %values_pdns_data_hash_delete;
my %ignore_records;
my @custom_columns = get_custom_host_columns("$client_id");
my @redes_usage_array;
my %duplicated_a_entries_hash;


# read exclude record file
if ( -e $exclude_file ) {
    open(FILE,"<$exclude_file") or exit_error("Can not open $exclude_file: $!");
    while (<FILE>) {
        $_ =~ /^(.+)\s(.+)\s(.+)$/;
        my $name = $1;
        my $type = $2;
        my $content = $3;

        print LOG "Ignore record: $name - $type - $content\n" if $debug;
#        push @{$ignore_records{$name}},"$type","$content";
        push @{$ignore_records{$content}},"$type","$name";
    }
    close FILE;

    #Delete content of exclude file
    open(FILE,">$exclude_file") or exit_error("Can not open $exclude_file: $!");
    close FILE;
}

# Get changed entries
my $j = 0;
if ( -e $file ) {
    open(FILE,"<$file") or exit_error("Can not open $file: $!");
    while (<FILE>) {
        # read check file with old records
        # name type record domain
        # host13.test.com A 10.1.4.13 test.com
        # host13.sub.test.com A 10.1.4.13 sub.test.com
        my ($name, $type, $content, $domain);
        $_ =~ /^(.+)\s(.+)\s(.+)\s(.+)\s/;
        $name = $1; # hostname
        $type = $2;
        $content = $3; # IP
        $domain = $4;

        if ( ! $name || ! $type || ! $content || ! $domain ) {
            next;
        }

        if ( exists $ignore_records{$content} && $ignore_records{$content}->[1] eq $name ) {
            # ignore record if it exists in ignore records
            next;
        }

        if ( $type ne "A" && $type ne "AAAA" ) {
            # Process only A and AAAA entries
            next;
        }

        print LOG "Old record: $name - $content - $type - $domain\n" if $debug;

        if ( exists $values_pdns_data_hash_old{$content} ) {
            $duplicated_a_entries_hash{$content} = 1;
            print LOG "Duplicate A record detected: $name - $content\n" if $debug;
        }

        push @{$values_pdns_data_hash_old{$content}},"$type","$name","$domain";
        $values_pdns_data_old[$j] = ["$name","$type","$content","$domain"];
        $j++;
    }
    close FILE;
}

my $count_pdns_data_old = @values_pdns_data_old;
print LOG "Count old records: $count_pdns_data_old\n" if $debug;

$j = 0;
my $k = 0;
my $i = 0;
foreach ( @values_pdns_data_old ) {
    # find CHANGED and DELETED entries

    # do nothing if init_gip
    last if $init_gip;

    my $hostname = $values_pdns_data_old[$j]->[0];
    my $type = $values_pdns_data_old[$j]->[1];
    my $content = $values_pdns_data_old[$j]->[2];
    my $domain = $values_pdns_data_old[$j]->[3];

    if ( exists $duplicated_a_entries_hash{$content} ) {
		print LOG "IP ignored - duplicated A records: $content - $domain\n" if $debug;
		$j++;
        next;
    }

	if ( ! $hostname || ! $type || ! $content || ! $domain ) {
		print LOG "Host ignored - parameter missing: $hostname - $type - $content - $domain\n" if $debug;
		$j++;
		next;
	}

    if ( exists $ignore_records{$content} && $ignore_records{$content}->[1] eq $hostname ) {
        # ignore record if it exists in ignore records
		print LOG "Host ignored - host found in ignore file: $hostname - $type - $content - $domain\n" if $debug;
		$j++;
        next;
    }

    if ( exists $values_pdns_data_hash{"$content"} ) {  # Actual pdns data
		my $hostname_new = $values_pdns_data_hash{"$content"}->[1];
		if ( $hostname_new ne $hostname ) {
			### IP for hostname has changed
			# hostname for IP has changed

            # Insert or update new entry
			$values_pdns_data[$k]->[0] = $hostname_new;
			$values_pdns_data[$k]->[1] = $type;
			$values_pdns_data[$k]->[2] = $content;
			$values_pdns_data[$k]->[3] = $domain;
			$k++;

			print LOG "prepare UPDATE: $content - $hostname -> $hostname_new\n" if $debug;
		}

    } else {
		# old hashkey does not exist in new -> delete
        $values_pdns_data_hash_delete{$content} = $hostname;
        $values_pdns_data[$k]->[0] = $hostname;
        $values_pdns_data[$k]->[1] = $type;
        $values_pdns_data[$k]->[2] = $content;
        $values_pdns_data[$k]->[3] = $domain;
        $k++;

		print LOG "prepare DELETE: $hostname - $content\n" if $debug;
    }
	$j++;
}

$j = 0;
open(FILE,">$file") or exit_error("Can not open $file for writing: $!");
foreach ( @values_pdns_data_n ) {
    # write all pdns data to $file

    # do nothing if init_gip
    last if $init_gip;

    my $hostname = $values_pdns_data_n[$j]->[0];
    my $type = $values_pdns_data_n[$j]->[1];
    my $content = $values_pdns_data_n[$j]->[2];
    my $domain = $values_pdns_data_n[$j]->[3];
    print LOG "Current record: $hostname - $content - $type\n" if $debug;

	# find values which are in actual but not in old hash -> add value
    if ( ! exists $values_pdns_data_hash_old{$content} ) {
        $values_pdns_data[$k]->[0] = $hostname;
        $values_pdns_data[$k]->[1] = $type;
        $values_pdns_data[$k]->[2] = $content;
        $values_pdns_data[$k]->[3] = $domain;
		$k++;
        print LOG "prepare ADD: $hostname - $content\n" if $debug;
	}

    # Create new check_file
	print FILE $hostname . " " . $type . " " . $content . " " . $domain . "\n";

	$j++;
}
close FILE;

# IF INITIALIZE PROCESS WHOLE DATABASE
if ( $init_gip ) {
    @values_pdns_data = @values_pdns_data_n;
}

my $count_pdns_data = @values_pdns_data;
print LOG "Count entries to process: $count_pdns_data\n" if $debug;

$j = 0;

my $neto_old;
my $red_num_old;
my $loc_id_old;
my $domain_old;
my $ip_version_old;
my %host_hash_old;

# delete duplicated values from @values_pdns_data

my %seen;
my @values_pdns_data_uniq;
foreach my $val ( @values_pdns_data ) {
    my $helper = join("%%%%", @$val);
    print LOG "Duplicated entry deleted: @$val\n" if exists $seen{$helper} && $debug;
    $seen{$helper} = 1;
}

my $l=0;
foreach my $key (keys %seen) {
    my @arr = split("%%%%", $key);
    $values_pdns_data_uniq[$l] = \@arr;
    $l++;
}
@values_pdns_data = @values_pdns_data_uniq;

foreach ( @values_pdns_data ) {
    my $hostname = $values_pdns_data[$j]->[0];
    my $record_type = $values_pdns_data[$j]->[1];
    my $content = $values_pdns_data[$j]->[2];

    print LOG "Processing: \"$hostname - $content - $record_type\" - $j\n" if $debug;

	$j++;

	if ( $record_type ne "A" && $record_type ne "AAAA" ) {
		next;
    }

    my $host_domain = $hostname;
    my $dot_count = $hostname =~ tr/\.// || 0;
    if ( $dot_count > 1 ) {
        $hostname =~ /^.+?\.(.+)$/;
        $host_domain = $1 || "";
    }
    if ( ! $host_domain ) {
        print LOG "Can not determine domain of the host: $hostname\n" if $debug;
        next;
    }

	# check if IP is from same network as the IP before - to find network for IP
	my $ipo = new Net::IP ($content);
	my $ipo_int = $ipo->intip();
	my $mydatetime = time();
	if ( $neto_old ) {
		if ( $ipo->overlaps($neto_old) ) {
            print LOG "Found net_old with overlap: $neto_old\n" if $debug;
            if ( $host_domain ne $domain_old ) {
                # discard network if the domain name does not corresponds with hosts domain
                print LOG "Discarding network - no domain match: $neto_old - $domain_old - $hostname - $host_domain\n" if $debug;
                next;
            }
			if ( $host_hash_old{$ipo_int} ) {
				my $host_id = $host_hash_old{$ipo_int}[1] || "";
				my $hostname_check = $host_hash_old{$ipo_int}[0] || "";
                my $ut = $host_hash_old{$ipo_int}[4] || "-1";
                my $red_num_usage = $host_hash_old{$ipo_int}[5] || "";

                # Delete host if it exits in host_hash and if is in %values_pdns_data_hash_delete
                if ( exists $values_pdns_data_hash_delete{$content} && $values_pdns_data_hash_delete{$content} eq $hostname ) {
                    print LOG "DELETE $content - $ut\n" if $verbose;
                    if ( $ut ne 1 ) {
                        # update type not "man"
                        delete_or_clear("$client_id", "$content", \%host_hash_old, "$ip_version_old");
                        push @redes_usage_array, $red_num_usage;
                    }
                    next;
                } elsif ( exists $values_pdns_data_hash_delete{$content} ) {
                    print LOG "Not deleted - hostname and hostname-old differ: $values_pdns_data_hash_delete{$content} - $hostname\n" if $debug;
                    next;
                }

                if ( $hostname ne $hostname_check ) {
                    if ( $ut ne 1 ) {
                        update_hostname("$client_id", "$host_id", "$hostname");
                        $countu++;
                        print LOG "UPDATE: $content - $host_id\n" if $verbose;
                    } else {
                        print LOG "update type man - ignored: $content - $host_id\n" if $debug;
                    }
                    next;
                }
			} else {
				insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id_old, "", "", "", "2", "$mydatetime", "$red_num_old", "-1", "$ip_version_old", "$dyn_dns_updates");
				$counti++;
				print LOG "INSERT: $content\n" if $verbose;
                push @redes_usage_array, $red_num_old;
                next;
			}
		} else {
            print LOG "Found net_old but no overlap: $neto_old\n" if $debug;
        }
	}

    if ( $record_type eq "A" ) {
        if ( ! $hostname || ! $content ) {
            print LOG "Missing hostname or content: $hostname - $content\n" if $debug;
            next;
        }
        my $ip_version = "v4";

        my $k = 0;
        foreach ( @values_host_redes4 ) {

            if ( ! $values_host_redes4[$k]->[0] || $values_host_redes4[$k]->[5] == 1 || ! $values_host_redes4[$k]->[6] ) {
                my $igno_net_ip = $values_host_redes4[$k]->[0] || "";
                print LOG "No IP or no Domain or rootnet: $igno_net_ip\n" if $debug;
                $k++;
                next;
            }

            my $n = $values_host_redes4[$k]->[0];
            my $bm = $values_host_redes4[$k]->[1];
            my $red_num = $values_host_redes4[$k]->[2];
            my $loc_id = $values_host_redes4[$k]->[3];
            my $domain = $values_host_redes4[$k]->[6] || "";

#            print LOG "TEST: Checking overlap network: $n/$bm - $domain - $red_num\n" if $debug;

            if ( $host_domain ne $domain ) {
                # discard network if the domain name does not corresponds with hosts domain
                print LOG "Discarding network - no domain match: $n/$bm - $domain - $hostname - $host_domain\n" if $debug;
                $k++;
                next;
            }

            $n =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $second_host_red_oct=$2;
            my $third_host_red_oct=$3;
            $content =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
            my $second_host_oct=$2;
            my $third_host_oct=$3;
            if (  $bm >= 24 && $third_host_red_oct != $third_host_oct ) {
                $count++;
                $k++;
                next;
            } elsif (  $bm >= 16 && $second_host_red_oct != $second_host_oct ) {
                $count++;
                $k++;
                next;
            }

            my $net = "$n/$bm";
            my $neto = new Net::IP ($net);

            if ( $ipo->overlaps($neto) ) {
                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");
                print LOG "Found network for host: $hostname - $net\n" if $debug;

                if ( exists $host_hash{$ipo_int} ) {
                    print LOG "Found host: $net\n" if $debug;
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;

                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    # Delete host if it exits in host_hash and if is in %values_pdns_data_hash_delete
                    if ( exists $values_pdns_data_hash_delete{$content} && $values_pdns_data_hash_delete{$content} eq $hostname ) {
                        print LOG "DELETE $content\n" if $verbose;
                        if ( $ut ne 1 ) {
                            # update type not "man"
                            delete_or_clear("$client_id", "$content", \%host_hash, "$ip_version");
                            push @redes_usage_array, $red_num_usage;
                        }
                        last;
                    } elsif ( exists $values_pdns_data_hash_delete{$content} ) {
                        print LOG "Not deleted - hostname and hostname-old differ: $values_pdns_data_hash_delete{$content} - $hostname\n" if $debug;
                        last;
                    }

                    if ( $ut eq 1 ) {
                        # update type "man"
                        print LOG "UPDATE: update type: man - ignored - $n/$bm - $content - $host_id - $ut\n" if $debug;
                    } else {
                        print LOG "UPDATE: $n/$bm - $content - $host_id\n" if $verbose;
                        update_hostname("$client_id", "$host_id", "$hostname");
                        $countu++;
                    }
                } else {
                    print LOG "INSERT: $n/$bm - $content \n" if $verbose;
                    insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates");
                    $counti++;
                    push @redes_usage_array, $red_num;
                }

				$neto_old = $neto;
				$red_num_old = $red_num;
				$ip_version_old = $ip_version;
				$loc_id_old = $loc_id;
				$domain_old = $domain;
				%host_hash_old = %host_hash;

                $count++;
                last;
            }

            $k++;
            $count++;
        }
    } elsif ( $record_type eq "AAAA" ) {

        if ( ! $hostname || ! $record_type || ! $content ) {
            next;
        }
        my $ip_version = "v6";

        my $k = 0;
        foreach ( @values_host_redes6 ) {

            if ( ! $values_host_redes6[$k]->[0] || $values_host_redes6[$k]->[5] == 1 || ! $values_host_redes6[$k]->[6] ) {
                $k++;
                next;
            }

            my $n = $values_host_redes6[$k]->[0];
            my $bm = $values_host_redes6[$k]->[1];
            my $red_num = $values_host_redes6[$k]->[2];
            my $loc_id = $values_host_redes6[$k]->[3];
            my $domain = $values_host_redes6[$k]->[6] || "";

            print LOG "Processing: $hostname - $domain\n" if $debug;

            if ( $host_domain ne $domain ) {
                # discard network if the domain name does not corresponds with hosts domain
                print LOG "Discarding network - no domain match: $n/$bm - $domain - $hostname - $host_domain\n" if $debug;
                $k++;
                next;
            }

			my $n_exp = ip_expand_address ($n, 6);
			my $content_exp = ip_expand_address ($content, 6);

            print LOG "IP expanded: $n_exp - $content_exp\n" if $debug;

            $n_exp =~ /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np=$1;
            $content_exp = /^([a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}:[a-f0-9]{1,4}):/;
            my $np_host=$1;
            if ( $bm == 64 && $np ne $np_host ) {
                $count++;
                $k++;
                next;
			}

            my $net = "$n/$bm";
            my $neto = new Net::IP ($net);

            if ( $ipo->overlaps($neto) ) {
                my %host_hash = get_host_hash("$client_id","$red_num","$ip_version");

                if ( exists $host_hash{$ipo_int} ) {
                    my $host_id = $host_hash{$ipo_int}[1] || "";
                    last if ! $host_id;
                    my $ut = $host_hash{$ipo_int}[4] || "-1";
                    my $red_num_usage = $host_hash{$ipo_int}[5] || "";

                    # Delete host if it exits in host_hash and if is in %values_pdns_data_hash_delete
                    if ( exists $values_pdns_data_hash_delete{$content} && $values_pdns_data_hash_delete{$content} eq $hostname ) {
                        print LOG "DELETE $content\n" if $verbose;
                        if ( $ut ne 1 ) {
                            # update type not "man"
                            delete_or_clear("$client_id", "$content", \%host_hash, "$ip_version");
                            push @redes_usage_array, $red_num_usage;
                        }
                        last;
                    } elsif ( exists $values_pdns_data_hash_delete{$content} ) {
                        print LOG "Not deleted - hostname and hostname-old differ: $values_pdns_data_hash_delete{$content} - $hostname\n" if $debug;
                        last;
                    }

                    if ( $host_id ) {
                        if ( $ut ne 1 ) {
                            update_hostname("$client_id", "$host_id", "$hostname");
                            $countu++;
                            print LOG "UPDATE: $n/$bm - $content - $host_id\n" if $debug;
                        } else {
                            print LOG "UPDATE: update type: man - ignored - $n/$bm - $content - $host_id - $ut\n" if $debug;
                        }
                    }
                } else {
                    insert_ip_mod("$client_id", "$ipo_int", "$hostname", "", $loc_id, "", "", "", "2", "$mydatetime", "$red_num", "-1", "$ip_version", "$dyn_dns_updates");
                    $counti++;
                    print LOG "INSERT: $n/$bm - $content \n" if $debug;
                    push @redes_usage_array, $red_num;
                }

                $neto_old = $neto;
                $red_num_old = $red_num;
                $ip_version_old = $ip_version;
                $loc_id_old = $loc_id;
                %host_hash_old = %host_hash;

                $count++;
                last;
            }

            $k++;
            $count++;
		}

    }
}

# update net usage
%seen = ();
my $item;
my @uniq;
foreach $item(@redes_usage_array) {
	next if ! $item;
	push(@uniq, $item) unless $seen{$item}++;
}
@redes_usage_array = @uniq;

foreach my $rn ( @redes_usage_array) {
		print LOG "updating net usage cc\n" if $verbose;
#        $gip->update_net_usage_cc_column("$client_id", "", "$rn","","no_rootnet");
        update_net_usage_cc_column("$client_id", "", "$rn","","no_rootnet");
}

print "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;
print LOG "Added: $counti - UPDATED: $countu - DELETED: $countd\n" if $verbose;

close LOG;




sub _mysql_connection {
    my $connect_error = "0";
    my $dbh = DBI->connect("DBI:mysql:$params{sid_gestioip}:$params{bbdd_host_gestioip}:$params{bbdd_port_gestioip}",$params{user_gestioip},$params{pass_gestioip}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}

sub _mysql_connection_pdns {
    my $connect_error = "0";
    my $dbh = DBI->connect("DBI:mysql:$params{sid_pdns}:$params{bbdd_host_pdns}:$params{bbdd_port_pdns}",$params{user_pdns},$params{pass_pdns}) or
    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}


sub get_host_redes_no_rootnet {
    my ( $client_id, $ip_version ) = @_;
    my @host_redes;
    my $ip_ref;
    my $dbh = _mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qip_version = $dbh->quote( $ip_version );

#    print LOG "SELECT n.red, n.BM, n.red_num, n.loc, n.ip_version, n.rootnet, ce.entry FROM net n, custom_net_columns c, custom_net_column_entries ce WHERE ce.cc_id IN ( SELECT id FROM custom_net_columns WHERE name='DNSZone' ) AND c.id=ce.cc_id AND n.red_num=ce.net_id AND n.rootnet = '0' AND n.ip_version=$qip_version AND n.client_id=$qclient_id\n" if $debug;
    my $sth = $dbh->prepare("SELECT n.red, n.BM, n.red_num, n.loc, n.ip_version, n.rootnet, ce.entry FROM net n, custom_net_columns c, custom_net_column_entries ce WHERE ce.cc_id IN ( SELECT id FROM custom_net_columns WHERE name='DNSZone' ) AND c.id=ce.cc_id AND n.red_num=ce.net_id AND n.rootnet = '0' AND n.ip_version=$qip_version AND n.client_id=$qclient_id")
        or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @host_redes, [ @$ip_ref ];
    }
    $dbh->disconnect;
    return @host_redes;
}


sub get_pdns_data {
    my @hosts;
    my $ip_ref;
    my $dbh = _mysql_connection_pdns();
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT r.name, r.type, r.content, d.name FROM records r, domains d WHERE (r.type='A' OR r.type='AAAA') AND r.domain_id=d.id ORDER BY r.content")
        or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @hosts, [ @$ip_ref ];
    }

    $dbh->disconnect;
    return @hosts;
}


sub get_pdns_data_hash {
    my %pdns_hash;
    my $ip_ref;
    my $dbh = _mysql_connection_pdns();
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT r.name, r.type, r.content, d.name AS domain FROM records r, domains d WHERE (r.type='A' OR r.type='AAAA') AND r.domain_id=d.id")
        or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $name = $ip_ref->{'name'};
        my $type = $ip_ref->{'type'};
        my $content = $ip_ref->{'content'} || "";
        my $domain = $ip_ref->{'domain'};

#		push @{$pdns_hash{$name}},"$type","$content","$domain";
		push @{$pdns_hash{$content}},"$type","$name","$domain";
	}

    $dbh->disconnect;
    return %pdns_hash;
}


sub get_host_hash {
    my ( $client_id, $red_num, $ip_version ) = @_;

	my %host_hash;
    my $ip_ref;
    my $dbh = _mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $qred_num = $dbh->quote( $red_num );

    my $sth = $dbh->prepare("SELECT ip, INET_NTOA(ip), hostname, id, range_id, update_type, red_num FROM host WHERE red_num=$qred_num AND client_id=$qclient_id")
        or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $ip_int = $ip_ref->{'ip'};
        my $ip = "";
        $ip = $ip_ref->{'INET_NTOA(ip)'} if $ip_version eq "v4";
        my $ip_version = $ip_ref->{'ip_version'};
        my $hostname = $ip_ref->{'hostname'} || "";
        my $id = $ip_ref->{'id'};
        my $range_id = $ip_ref->{'range_id'};
        my $update_type = $ip_ref->{'update_type'};
        my $red_num = $ip_ref->{'red_num'};

	    push @{$host_hash{$ip_int}},"$hostname","$id","$ip","$range_id","$update_type","$red_num";
	}

    $dbh->disconnect;
    return %host_hash;

}

sub insert_ip_mod {
    my ( $client_id, $ip_int, $hostname, $host_descr, $loc, $int_admin, $cat, $comentario, $update_type, $mydatetime, $red_num, $alive, $ip_version, $dyn_dns_updates ) = @_;

    my $dbh = _mysql_connection();
    my $sth;
    $loc="-1" if ! $loc;
    $cat="-1" if ! $cat;
    my $qhostname = $dbh->quote( $hostname );
    my $qhost_descr = $dbh->quote( $host_descr );
    my $qloc = $dbh->quote( $loc );
    my $qint_admin = $dbh->quote( $int_admin );
    my $qcat = $dbh->quote( $cat );
    my $qcomentario = $dbh->quote( $comentario );
    my $qupdate_type = $dbh->quote( $update_type );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qip_int = $dbh->quote( $ip_int );
    my $qred_num = $dbh->quote( $red_num );
    $alive = "-1" if ! defined($alive);
    my $qclient_id = $dbh->quote( $client_id );
    my $qdyn_dns_updates = $dbh->quote( $dyn_dns_updates );
    my $qip_version = $dbh->quote( $ip_version );
    if ( $alive != "-1" ) {
        my $qalive = $dbh->quote( $alive );
        my $qlast_response = $dbh->quote( time() );
        $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,alive,last_response,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qalive,$qlast_response,$qip_version,$qclient_id,$qdyn_dns_updates)"
                                ) or croak "Can not execute statement:<p>$DBI::errstr";
    } else {
        $sth = $dbh->prepare("INSERT INTO host (ip,hostname,host_descr,loc,red_num,int_admin,categoria,comentario,update_type,last_update,ip_version,client_id,dyn_dns_updates) VALUES ($qip_int,$qhostname,$qhost_descr,$qloc,$qred_num,$qint_admin,$qcat,$qcomentario,$qupdate_type,$qmydatetime,$qip_version,$qclient_id,$qdyn_dns_updates)"
                                ) or croak "Can not execute statement:<p>$DBI::errstr";
    }
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}


sub update_hostname {
    my ( $client_id, $id, $hostname ) = @_;

    print LOG "UPDATE HOSTNAME: $hostname - $id\n" if $verbose;

    my $dbh = _mysql_connection();
    my $sth;
    my $qhostname = $dbh->quote( $hostname );
    my $qid = $dbh->quote( $id );
    my $qclient_id = $dbh->quote( $client_id );

    $sth = $dbh->prepare("UPDATE host SET hostname=$qhostname WHERE id=$qid AND client_id=$qclient_id"
                                ) or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}

sub delete_ip {
    my ( $client_id, $first_ip_int, $last_ip_int ) = @_;

    my $dbh = _mysql_connection();
    my $qfirst_ip_int = $dbh->quote( $first_ip_int );
    my $qlast_ip_int = $dbh->quote( $last_ip_int );
    my $qclient_id = $dbh->quote( $client_id );

    my $match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";

    my $sth = $dbh->prepare("DELETE FROM host WHERE $match AND client_id = $qclient_id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}

sub clear_ip {
    my ( $client_id, $first_ip_int, $last_ip_int ) = @_;

    my $dbh = _mysql_connection();
    my $qfirst_ip_int = $dbh->quote( $first_ip_int );
    my $qlast_ip_int = $dbh->quote( $last_ip_int );
    my $qclient_id = $dbh->quote( $client_id );

    my $match="CAST(ip AS BINARY) BETWEEN $qfirst_ip_int AND $qlast_ip_int";

    my $sth = $dbh->prepare("UPDATE host SET hostname='', host_descr='', int_admin='n', alive='-1', last_response=NULL WHERE $match AND client_id = $qclient_id") or croak "Can not execute statement:<p>$DBI::errstr";

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
	
	print "\n$error\n\n";

	exit $sig;
}

sub delete_or_clear {
    my ( $client_id, $content, $host_hash, $ip_version ) = @_;

	my $ipo = new Net::IP ($content);
	my $ipo_int = $ipo->intip();
    $content = ip_compress_address ($content, 6) if $ip_version eq "v6";
	if ( exists $host_hash->{$ipo_int} ) {
		my $range_id = $host_hash->{$ipo_int}[3];
		my $host_id = $host_hash->{$ipo_int}[1];
	
		# Delete host
		if ( $range_id != -1 ) {
			# reserved range -> update
			clear_ip("$client_id","$ipo_int","$ipo_int");
		} else {
			# delete
			delete_ip("$client_id","$ipo_int","$ipo_int");
			
		}
		$countd++;

		my $linked_cc_id = get_custom_host_column_id_from_name_client("$client_id","linked IP") || "";
		if ( $linked_cc_id ) {
			# delete linked IP entries if exist

			my %cc_value=get_custom_host_columns_from_net_id_hash("$client_id","$host_id") if $host_id;
			my $audit_entry_cc="";

			my $cm_config_host=0;
			if ( $custom_columns[0] ) {

				my $n=0;
				foreach my $cc_ele(@custom_columns) {
					my $cc_name = $custom_columns[$n]->[0];
					my $pc_id = $custom_columns[$n]->[3];
					my $cc_id = $custom_columns[$n]->[1];
					my $cc_entry = $cc_value{$cc_id}[1] || "";

					$cm_config_host=1;

					if ( $cc_id == $linked_cc_id ) {
						my $linked_ips=$cc_entry;
						my @linked_ips=split(",",$linked_ips);
						foreach my $linked_ip_delete(@linked_ips){
							delete_linked_ip("$client_id","$ip_version","$linked_ip_delete","$content");
						}
					}

					if ( $cc_entry ) {
						if ( $audit_entry_cc ) {
							$audit_entry_cc = $audit_entry_cc . "," . $cc_entry;
						} else {
							$audit_entry_cc = $cc_entry;
						}
					}
					$n++;
				}
			}
		}

		delete_custom_host_column_entry("$client_id", "$host_id");

	} else {
		print LOG "HOST NOT FOUND - DO NOT DELETE NOTHING: $content - $ipo_int\n" if $debug > 0;
	} 
}

sub delete_custom_host_column_entry {
    my ( $client_id, $host_id ) = @_;
    my $dbh = _mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND client_id = $qclient_id"
                                ) or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_host_column_id_from_name_client {
    my ( $client_id, $column_name ) = @_;
    my $cc_id;
    my $dbh = _mysql_connection();
    my $qcolumn_name = $dbh->quote( $column_name );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT id FROM custom_host_columns WHERE name=$qcolumn_name AND ( client_id = $qclient_id OR client_id = '9999' )
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $cc_id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

    return $cc_id;
}

sub delete_linked_ip {
    my ( $client_id,$ip_version,$linked_ip_old,$ip,$host_id_linked ) = @_;

    my $ip_version_ip_old;
    if ( $linked_ip_old =~ /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/ ) {
        $ip_version_ip_old="v4";
    } else {
        $ip_version_ip_old="v6";
    }

    my $cc_name="linked IP";
    my $cc_id="";
    my $pc_id="";
    $host_id_linked="" if ! $host_id_linked;
    if ( ! $host_id_linked ) {
        my $ip_int_linked=ip_to_int("$client_id","$linked_ip_old","$ip_version_ip_old") || "";
        $host_id_linked=get_host_id_from_ip_int("$client_id","$ip_int_linked") || "";
    }
    return if ! $host_id_linked;
    my %custom_host_column_values=get_custom_host_columns_from_net_id_hash("$client_id","$host_id_linked");
    while ( my ($key, @value) = each(%custom_host_column_values) ) {
        if ( $value[0]->[0] eq $cc_name ) {
            $cc_id=$key;
            $pc_id=$value[0]->[2];
            last;
        }
    }

    my $linked_cc_entry=get_custom_host_column_entry("$client_id","$host_id_linked","$cc_name","$pc_id") || "";
    my $linked_ip_comp=$ip;
    $linked_ip_comp = ip_compress_address ($linked_ip_comp, 6) if $ip_version eq "v6";
    $linked_cc_entry =~ s/\b${linked_ip_comp}\b//;
    $linked_cc_entry =~ s/^,//;
    $linked_cc_entry =~ s/,$//;
    $linked_cc_entry =~ s/,,/,/;
    # delete entry from linked host
    if ( $linked_cc_entry ) {
        update_custom_host_column_value_host_modip("$client_id","$cc_id","$pc_id","$host_id_linked","$linked_cc_entry");
    } else {
        delete_single_custom_host_column_entry("$client_id","$host_id_linked","$linked_ip_comp","$pc_id");
    }
}

sub get_custom_host_columns_from_net_id_hash {
    my ( $client_id,$host_id ) = @_;

    my %cc_values;
    my $ip_ref;
    my $dbh = _mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT DISTINCT cce.cc_id,cce.entry,cc.name,cc.column_type_id FROM custom_host_column_entries cce, custom_host_columns cc WHERE  cce.cc_id = cc.id AND host_id = $host_id AND cce.client_id = $qclient_id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

	while ( $ip_ref = $sth->fetchrow_hashref ) {
		my $id = $ip_ref->{cc_id};
		my $name = $ip_ref->{name};
		my $entry = $ip_ref->{entry};
		my $column_type_id = $ip_ref->{column_type_id};
		push @{$cc_values{$id}},"$name","$entry","$column_type_id";
	}
	$dbh->disconnect;
	return %cc_values;
}

sub ip_to_int {
    my ($client_id,$ip,$ip_version)=@_;
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

sub get_host_id_from_ip_int {
    my ( $client_id,$ip_int,$red_num ) = @_;
    my $val;
    my $dbh = _mysql_connection();
    my $qip_int = $dbh->quote( $ip_int );
    my $qclient_id = $dbh->quote( $client_id );
    my $qred_num = $dbh->quote( $red_num );
    my $red_num_expr="";
    $red_num_expr="AND red_num = $qred_num" if $red_num;
    my $sth = $dbh->prepare("SELECT id FROM host WHERE ip=$qip_int AND client_id=$qclient_id $red_num_expr");
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $val = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $val;
}

sub update_custom_host_column_value_host_modip {
    my ( $client_id, $cc_id, $pc_id, $host_id, $entry ) = @_;

    my $dbh = _mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qhost_id = $dbh->quote( $host_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("UPDATE custom_host_column_entries SET entry=$qentry WHERE pc_id=$qpc_id AND host_id=$qhost_id AND cc_id=$qcc_id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->finish();
    $dbh->disconnect;
}

sub delete_single_custom_host_column_entry {
    my ( $client_id, $host_id, $cc_entry_host, $pc_id, $cc_id ) = @_;

    $cc_id="" if ! $cc_id;
    $cc_entry_host = "" if ! $cc_entry_host;

    my $dbh = _mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qcc_entry_host = $dbh->quote( $cc_entry_host );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qcc_id = $dbh->quote( $cc_id );
    my $qclient_id = $dbh->quote( $client_id );

    my $cc_id_expr="";
    $cc_id_expr="AND cc_id=$qcc_id" if $cc_id;
    my $sth;
    if ( $cc_entry_host ) {
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND entry = $qcc_entry_host AND pc_id = $qpc_id $cc_id_expr") or croak "Can not execute statement:<p>$DBI::errstr";
    } else {
        $sth = $dbh->prepare("DELETE FROM custom_host_column_entries WHERE host_id = $qhost_id AND pc_id = $qpc_id $cc_id_expr") or croak "Can not execute statement:<p>$DBI::errstr";
    }

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_host_column_entry {
    my ( $client_id, $host_id, $cc_name, $pc_id ) = @_;
    my $dbh = _mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qcc_name = $dbh->quote( $cc_name );
    my $qpc_id = $dbh->quote( $pc_id );
    my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT cce.cc_id,cce.entry from custom_host_column_entries cce, custom_host_columns cc, predef_host_columns pc WHERE cc.name=$qcc_name AND cce.host_id = $qhost_id AND cce.cc_id = cc.id AND cc.column_type_id= pc.id AND pc.id = $qpc_id AND cce.client_id = $qclient_id
					") or croak "Can not execute statement:<p>$DBI::errstr";
	$sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
	my $entry = $sth->fetchrow_array;
	$sth->finish();
	$dbh->disconnect;

	return $entry;
}

sub get_custom_host_columns {
    my ( $client_id ) = @_;

    my @values;
    my $ip_ref;
    my $dbh = _mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );
    my $sth;
    $sth = $dbh->prepare("SELECT cc.name,cc.id,cc.client_id,pc.id FROM custom_host_columns cc, predef_host_columns pc WHERE cc.column_type_id = pc.id AND (client_id = $qclient_id OR client_id = '9999') ORDER BY cc.id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $dbh->disconnect;

    return @values;
}

sub print_help {
        print "\nusage: gip_pdns_sync.pl.pl [OPTIONS...]\n\n";
        print "-c, --config_file_name=config_file_name  name of the configuration file (without path)\n";
        print "-d, --debug              debug\n";
        print "-h, --help               help\n";
        print "-i, --init_gip           initalze GestioIP database\n";
        print "-v, --verbose            verbose\n\n";
        print "\n\n\nconfiguration file: $conf\n\n" if $conf;
        exit;
}

sub update_net_usage_cc_column {
    my ($client_id, $ip_version, $red_num, $BM, $no_rootnet) = @_;
    
    my $rootnet = "";
    if ( ! $BM || ! $ip_version || ! $no_rootnet ) {
        my @values_redes=get_red("$client_id","$red_num");
        $BM = "$values_redes[0]->[1]" || "";
        $ip_version = "$values_redes[0]->[7]" || "";
        $rootnet = "$values_redes[0]->[9]" || "";
    }
    
    # no usage value for rootnetworks
    return if $rootnet eq 1;

    my ($ip_total, $ip_ocu, $free) = get_red_usage("$client_id", "$ip_version", "$red_num", "$BM");
    my $cc_id_usage = get_custom_column_id_from_name("$client_id", "usage") || "";
    my $cc_usage_entry = "$ip_total,$ip_ocu,$free" || "";
    update_or_insert_custom_column_value_red("$client_id", "$cc_id_usage", "$red_num", "$cc_usage_entry") if $cc_id_usage && $cc_usage_entry;
}

sub get_red {
    my ( $client_id, $red_num ) = @_;

    my $error;
    my $ip_ref;
    my @values_redes;
    my $dbh = _mysql_connection();
    my $qred_num = $dbh->quote( $red_num );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT red, BM, descr, loc, vigilada, comentario, categoria, ip_version, red_num, rootnet, dyn_dns_updates FROM net WHERE red_num=$qred_num AND client_id = $qclient_id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_redes, [ @$ip_ref ];
    }
    $dbh->disconnect;

    return @values_redes;
}

sub get_red_usage {
    my ( $client_id, $ip_version, $red_num, $BM) = @_;

    if ( ! $BM || ! $ip_version ) {
        my @values_redes=get_red("$client_id","$red_num");
        $BM = "$values_redes[0]->[1]" || "";
        $ip_version = "$values_redes[0]->[7]" || "";
    }

    my %anz_hosts = get_anz_hosts_bm_hash("$client_id","$ip_version");
    my $ip_total=$anz_hosts{$BM};
    $ip_total =~ s/,//g;

    if ( $ip_version eq "v4" ) {
           $ip_total = $ip_total - 2;
           $ip_total = 2 if $BM == 31;
           $ip_total = 1 if $BM == 32;
    }

    my $ip_ocu=count_host_entries("$client_id","$red_num");
    my $free=$ip_total-$ip_ocu;
    my ($free_calc,$percent_free,$ip_total_calc,$percent_ocu,$ocu_color);

    if ( $free == 0 ) {
        $percent_free = '0%';
    } elsif ( $free == $ip_total ) {
        $percent_free = '100%';
    } else {
        $free_calc = $free . ".0";
        $ip_total_calc = $ip_total . ".0";
        $percent_free=100*$free_calc/$ip_total_calc;
        $percent_free =~ /^(\d+\.?\d?).*/;
        $percent_free = $1 . '%';
    }
    if ( $ip_ocu == 0 ) {
        $percent_ocu = '0%';
    } elsif ( $ip_ocu == $ip_total ) {
        $percent_ocu = '100%';
    } else {
        $ip_total_calc = $ip_total . ".0";
        $percent_ocu=100*$ip_ocu/$ip_total_calc;
        if ( $percent_ocu =~ /e/ ) {
            $percent_ocu="0.1"
        } else {
            $percent_ocu =~ /^(\d+\.?\d?).*/;
            $percent_ocu = $1;
        }
        $percent_ocu = $percent_ocu . '%';
    }

    return ($ip_total, $ip_ocu, $free);
}

sub get_anz_hosts_bm_hash {
    my ( $client_id, $ip_version ) = @_;
    my %bm;
    if ( $ip_version eq "v4" ) {
        %bm = (
            8 => '16777216',
            9 => '8388608',
            10 => '4194304',
            11 => '2097152',
            12 => '1048576',
            13 => '524288',
            14 => '262144',
            15 => '131072',
            16 => '65536',
            17 => '32768',
            18 => '16384',
            19 => '8192',
            20 => '4096',
            21 => '2048',
            22 => '1024',
            23 => '512',
            24 => '256',
            25 => '128',
            26 => '64',
            27 => '32',
            28 => '16',
            29 => '8',
            30 => '4',
            31 => '1',
            32 => '1'
        );
    } else {
        %bm = (
#           1 => '9,223,372,036,854,775,808',
#           2 => '4,611,686,018,427,387,904',
#           3 => '2,305,843,009,213,693,952',
#           4 => '1,152,921,504,606,846,976',
#           5 => '576,460,752,303,423,488',
#           6 => '288,230,376,151,711,744',
#           7 => '144,115,188,075,855,872',
            8 => '72,057,594,037,927,936',
            9 => '36,028,797,018,963,968',
            10 => '18,014,398,509,481,984',
            11 => '9,007,199,254,740,992',
            12 => '4,503,599,627,370,496',
            13 => '2,251,799,813,685,248',
            14 => '1,125,899,906,842,624',
            15 => '562,949,953,421,312',
            16 => '281,474,976,710,656',
            17 => '140,737,488,355,328',
            18 => '70,368,744,177,664',
            19 => '35,184,372,088,832',
            20 => '17,592,186,044,416',
            21 => '8,796,093,022,208',
            22 => '4,398,046,511,104',
            23 => '2,199,023,255,552',
            24 => '1,099,511,627,776',
            25 => '549,755,813,888',
            26 => '274,877,906,944',
            27 => '137,438,953,472',
            28 => '68,719,476,736',
            29 => '34,359,738,368',
            30 => '17,179,869,184',
            31 => '8,589,934,592',
            32 => '4,294,967,296',
            33 => '2,147,483,648',
            34 => '1,073,741,824',
            35 => '536,870,912',
            36 => '268,435,456',
            37 => '134,217,728',
            38 => '67,108,864',
            39 => '33,554,432',
            40 => '16,777,216',
            41 => '8,388,608',
            42 => '4,194,304',
            43 => '2,097,152',
            44 => '1,048,576',
            45 => '524,288',
            46 => '262,144',
            47 => '131,072',
            48 => '65,536',
            49 => '32,768',
            50 => '16,384',
            51 => '8,192',
            52 => '4,096',
            53 => '2,048',
            54 => '1,024',
            55 => '512',
            56 => '256',
            57 => '128',
            58 => '64',
            59 => '32',
            60 => '16',
            61 => '8',
            62 => '4',
            63 => '2',
# hosts
            64 => '18,446,744,073,709,551,616',
            65 => '9,223,372,036,854,775,808',
            66 => '4,611,686,018,427,387,904',
            67 => '2,305,843,009,213,693,952',
            68 => '1,152,921,504,606,846,976',
            69 => '576,460,752,303,423,488',
            70 => '288,230,376,151,711,744',
            71 => '144,115,188,075,855,872',
            72 => '72,057,594,037,927,936',
            73 => '36,028,797,018,963,968',
            74 => '18,014,398,509,481,984',
            75 => '9,007,199,254,740,992',
            76 => '4,503,599,627,370,496',
            77 => '2,251,799,813,685,248',
            78 => '1,125,899,906,842,624',
            79 => '562,949,953,421,312',
            80 => '281,474,976,710,656',
            81 => '140,737,488,355,328',
            82 => '70,368,744,177,664',
            83 => '35,184,372,088,832',
            84 => '17,592,186,044,416',
            85 => '8,796,093,022,208',
            86 => '4,398,046,511,104',
            87 => '2,199,023,255,552',
            88 => '1,099,511,627,776',
            89 => '549,755,813,888',
            90 => '274,877,906,944',
            91 => '137,438,953,472',
            92 => '68,719,476,736',
            93 => '34,359,738,368',
            94 => '17,179,869,184',
            95 => '8,589,934,592',
            96 => '4,294,967,296',
            97 => '2,147,483,648',
            98 => '1,073,741,824',
            99 => '536,870,912',
            100 => '268,435,456',
            101 => '134,217,728',
            102 => '67,108,864',
            103 => '33,554,432',
            104 => '16,777,216',
            105 => '8,388,608',
            106 => '4,194,304',
            107 => '2,097,152',
            108 => '1,048,576',
            109 => '524,288',
            110 => '262,144',
            111 => '131,072',
            112 => '65,536',
            113 => '32,768',
            114 => '16,384',
            115 => '8,192',
            116 => '4,096',
            117 => '2,048',
            118 => '1,024',
            119 => '512',
            120 => '256',
            121 => '128',
            122 => '64',
            123 => '32',
            124 => '16',
            125 => '8',
            126 => '4',
            127 => '2',
           128 => '1'
        );
    }
    return %bm;
}

sub update_or_insert_custom_column_value_red {
    my ( $client_id, $cc_id, $net_id, $entry ) = @_;
    my $error;

    my $dbh = _mysql_connection();
    my $qcc_id = $dbh->quote( $cc_id );
    my $qnet_id = $dbh->quote( $net_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id") or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    my $entry_found = $sth->fetchrow_array;

    if ( $entry_found ) {
        $sth = $dbh->prepare("UPDATE custom_net_column_entries SET entry=$qentry WHERE cc_id=$qcc_id AND net_id=$qnet_id") or croak "Can not execute statement:<p>$DBI::errstr";
    } else {
        $sth = $dbh->prepare("INSERT INTO custom_net_column_entries (cc_id,net_id,entry,client_id) VALUES ($qcc_id,$qnet_id,$qentry,$qclient_id)") or croak "Can not execute statement:<p>$DBI::errstr";
    }

    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";

    $sth->finish();
    $dbh->disconnect;
}

sub get_custom_column_id_from_name {
    my ( $client_id, $name ) = @_;
    my $dbh = _mysql_connection();
    my $qname = $dbh->quote( $name );
    my $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qname
                    ") or croak "Can not execute statement:<p>$DBI::errstr";
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    my $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $id;
}

sub count_host_entries {
    my ( $client_id, $red_num ) = @_;
    my $count_host_entries;
    my $dbh = _mysql_connection();
    my $qred_num = $dbh->quote( $red_num );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT COUNT(*) FROM host WHERE red_num=$qred_num AND hostname != 'NULL' AND hostname != '' AND client_id = $qclient_id");
    $sth->execute() or croak "Can not execute statement:<p>$DBI::errstr";
    $count_host_entries = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $count_host_entries;
}
