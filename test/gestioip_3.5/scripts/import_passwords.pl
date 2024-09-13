#!/usr/bin/perl

# import_passwords.pl v1.0 202003103

# use this script to import password from a csv file into GestioIP
# the CSV file must come in the following format:
# IP,username,password,comment
# for example:
# 192.168.1.2,admin,PASSWORD,my comment

# edit the variables $client_id, $pw_file and $master_key and
# below and execute the script without parameters
# cd /usr/share/gestioip/bin
# ./import_passwords.pl

use warnings;
use strict;
use Text::CSV;
use Crypt::CBC;
use MIME::Base64;
use DBI;

########################
#### change from here...
########################

my $client_id = 1;
my $pw_file = "./passwords.csv";
my $master_key= "XXXXXXX";

########################
#### ...to here
########################


# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = get_db_parameter();

if ( ! $pass_gestioip ) {
    print "Database password not found\n";
    exit 1;
}

# Read/parse CSV
my %result_hash;
my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1 });
open my $fh, "<:encoding(utf8)", "$pw_file" or die "$pw_file: $!";
while (my $row = $csv->getline ($fh)) {
	my $ip = $row->[0] || "";
	my $user = $row->[1] || "";
	my $pass = $row->[2] || "";
	my $comment = $row->[3] || "";

	if ( ! $ip || ! $user || ! $pass ) {
		print "Information missing: $ip - $user - $pass\n";
		next;
	}

	push @{$result_hash{$ip}},"$user","$pass","$comment";
}
close $fh;


foreach my $key ( keys %result_hash ) {
	my $ip = $key;
	my $user = $result_hash{$key}->[0];
	my $pass = $result_hash{$key}->[1];
	my $comment = $result_hash{$key}->[2] || "";

	my $host_id = check_host_exists("$client_id", "$ip");

	if ( $host_id ) {
		my $device_password_id=insert_device_key(
			client_id=>"$client_id",
			name=>"$user",
			comment=>"$comment",
			device_password=>"$pass",
			host_id=>"$host_id",
		);

		if ( $device_password_id ) {
			print "$ip: password for $user added\n";
		} else {
			print "error password ${ip}/${user} could not be added\n";
		}
	} else {
		print "host not found: $ip - ignored\n";
	}

}

print "done\n";




#### Subroutines

sub insert_device_key {
    my %args = @_;

    my $client_id=$args{client_id};
    my $name=$args{name};
    my $comment=$args{comment};
    my $device_password=$args{device_password};
    my $host_id=$args{host_id};

	my $device_password_enc_mime=encryptString("$device_password","$master_key");

    my $dbh = mysql_connection();

    my $qname = $dbh->quote( $name );
    my $qcomment = $dbh->quote( $comment );
    my $qhost_id = $dbh->quote( $host_id );
    my $qdevice_password_enc_mime = $dbh->quote( $device_password_enc_mime );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("INSERT INTO device_keys (name,comment,password,host_id,client_id) VALUES ($qname,$qcomment,$qdevice_password_enc_mime,$qhost_id,$qclient_id)"
                            ) or die "insert db: $DBI::errstr";
    $sth->execute() or die "insert db: $DBI::errstr";

    my $new_id=$sth->{mysql_insertid} || 0;

    $sth->finish();
    $dbh->disconnect;

	return $new_id;
}

sub check_host_exists {
	my ( $client_id, $ip ) = @_;

	my $id;

    my $dbh = mysql_connection();

	my $qip = $dbh->quote( $ip );
	my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT id FROM host WHERE ip=inet_aton($qip) AND client_id = $qclient_id AND hostname !=''") or die "db: $DBI::errstr";
    $sth->execute() or die "db: $DBI::errstr";
    $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;

	$id = "" if ! $id;

    return $id;
}


sub encryptString {
	my ( $master_key,$user_password ) = @_;

	my $cipher = Crypt::CBC->new(
		-key        => $user_password,
		-cipher     => 'Blowfish',
		-padding  => 'space',
		-add_header => 1
	);

	my $enc = $cipher->encrypt($master_key);
	my $enc_mime = encode_base64($enc);
	return $enc_mime;
}

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip)  or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}

sub get_db_parameter {
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or die "Can not open $priv_file: $!\n";
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

