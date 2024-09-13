#!/usr/bin/perl

# v3.4.3 20180606
# This scripts updates the usage column for all networks off all clients

# usage: update_net_usage.pl GESTIOIP_DOCUMENT_ROOT


use strict;
my ($gip_path, $gip_www_root, $gip_config_file, $cwd, $usage_path);

BEGIN
{
    use Cwd;
    $gip_www_root=$ARGV[0];
    $gip_path=${gip_www_root} . "/modules";
    $gip_config_file=${gip_www_root} . "/priv/ip_config";
    $cwd = cwd();
    $usage_path = $cwd . "/web/include";
#    if ( -e "/files/web/include" ) {
#        $usage_path = $cwd . "./files/web/include";
#    } elsif ( -e "./tmp/scripts/web/include" ) {
    if ( -e "./tmp/scripts/web/include" ) {
        $usage_path = $cwd . "/tmp/scripts/web/include";
    }
}

use lib "$gip_path";
use lib "$usage_path";
use GestioIP;
use Usage;

if ( ! $gip_www_root ) {
    print "usage: update_net_usage.pl GESTIOIP_DOCUMENT_ROOT\n";
}

my $verbose = 1;

my %args;
$args{'format'} = "no_format";
my $args = \%args;
my $gip  = GestioIP->new($args);

my @cc_ids = Usage::get_custom_column_ids_from_name("1","usage", $gip, "$gip_config_file");
if ( ! $cc_ids[0] ) {
    my $last_custom_column_id=Usage::get_last_custom_column_id("1", $gip, "$gip_config_file");
    my $insert_ok=Usage::insert_custom_column("9999","$last_custom_column_id","usage","9", $gip, "$gip_config_file");
}

my @clients = Usage::get_clients("1", $gip, "$gip_config_file");
foreach my $client( @clients ) {
	my $client_id = $client->[0]; 
    print "Processing Client: $client_id\n" if $verbose;
	my $redes_hash=Usage::get_redes_hash("1", "v4", "", "", $gip, "$gip_config_file");

	for my $red_num ( keys %$redes_hash ) {
		my $client_id_found=$redes_hash->{"$red_num"}[10] || "";
        next if $client_id != $client_id_found;
		my $rootnet=$redes_hash->{"$red_num"}[9] || "";
		next if $rootnet == 1;

		my $ip=$redes_hash->{"$red_num"}[0] || "";
		my $BM=$redes_hash->{"$red_num"}[1] || "";
		my $ip_version=$redes_hash->{"$red_num"}[7] || "";
		my $rootnet=$redes_hash->{"$red_num"}[9] || "";

        print "Processing network: $ip/$BM\n" if $verbose;

		Usage::update_net_usage_cc_column("$client_id", "$ip_version", "$red_num", "$BM","no_rootnet", $gip, "$gip_config_file");
	}
}

exit 0;
