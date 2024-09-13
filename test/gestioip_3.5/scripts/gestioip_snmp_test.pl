#!/usr/bin/perl -w

# If there appear problems with GestioIP's SNMP based discovery mechanisms
# use this script to check if Perl Modules SNMP and SNMP::Info generally working correctly

# gestioip_snmp_test.pl v0.2
# Copyright (C) 2011 Marc Uebel <contact@gestioip.net>


# Some possible errors:
# Timeout -> probably wrong IP or wrong community or IP not reachable by snmp (port udp:161)


# SNMP: Unknown Object Identifier -> requiered MIBs (SNMPv2-MIB, IP-FORWARD-MIB, RFC1213-MIB) not correctly installed:
#
# check with snmpwalk if the requiered MIBs are correctly installed:
#
# snmpwalk -c public -v 1 ip-address | egrep "ipRouteDest|ipCidrRouteDest"
# snmpwalk -c public -v 1 ip-address | grep sysDescr
#
# no output => check if the OIDs appear as string and not nummerically:
#
# snmpwalk -c public -v 1 ip-address  | head -3
# example output "OIDs as string" (good):
#SNMPv2-MIB::sysDescr.0 = STRING: Linux CPUL1770 2.6.22-16-generic #1 SMP Thu Apr 2 01:27:50 GMT 2009 i686
#SNMPv2-MIB::sysObjectID.0 = OID: NET-SNMP-MIB::netSnmpAgentOIDs.10
#DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (8595000) 23:52:30.00
#
# example output "OIDs numerically" (bad):
#.1.3.6.1.2.1.1.1.0 = STRING: Linux CPUL1770 2.6.22-16-generic #1 SMP Thu Apr 2 01:27:50 GMT 2009 i686
#.1.3.6.1.2.1.1.2.0 = OID: .1.3.6.1.4.1.8072.3.2.10
#.1.3.6.1.2.1.1.3.0 = Timeticks: (8612177) 23:55:21.77
#
# numerically output means that required MIBs are not correctly installed.


# SNMP::Info (with $debug set to "1")
# The following messages mean that the device does not support the requiered MIBs or that there is some kind of
# problem with the installation of SNMP::Info:
# SNMP::Info::_global layers : sysServices.0
# SNMP::Info::_global(layers) (noSuchName) There is no such variable name in this MIB. at ./snmp_test.pl line 88
#
# Check the device compatibility matrix (http://www.netdisco.org/DeviceMatrix.html) if your device is supported




use SNMP;
use SNMP::Info;
use strict;



#################
### Edit from here...
#################

# node to query
my $node="192.168.0.1";
#my $node="127.0.0.1";

# SNMP v1/2 community
my $community="public";

#SNMP version
my $snmp_version=1;


#SNMP::Info only:
# set $debug to 1 for more output
my $debug=1;

# IMPORTANT!
# $mib_dir: put here the same path as specified in "MIB directory" (manage->GestioIP)
my $mib_dir="/usr/share/gestioip/mibs";

#################
### ... to here
#################



print "\nChecking SNMP:\n";

my $snmp_session = new SNMP::Session(
			DestHost => $node,
                        Community => $community,
                        Version => $snmp_version,
                        UseSprintValue => 1,
                        Verbose => 1
                        );

if ( ! $snmp_session ) {
	print "SNMP: Can not connect to $node. Please check \"community\"\n";
	print "SNMP: Not OK\n";
}

no strict 'subs';
my $vars = new SNMP::VarList([sysDescr,0],
                             [sysName,0],
                             [sysContact,0],
                             [sysLocation,0]);
use strict 'subs';

my @values = $snmp_session->get($vars);

if ( ($snmp_session->{ErrorStr}) ) {
	print "SNMP: Not OK\n\n";
	print "$snmp_session->{ErrorStr}\n\n";
} else {
	print "SNMP: OK\n";
}



print "\nChecking SNMP::Info:\n";


my @mibdirs_array=();

my @vendor_mib_dirs=("allied","arista","aruba","asante","cabletron","cisco","cyclades","dell","enterasys","extreme","foundry","hp","juniper","netscreen","net-snmp","nortel","rfc");

foreach ( @vendor_mib_dirs ) {
	my $mib_vendor_dir = $mib_dir . "/" . $_;
	if ( ! -e $mib_vendor_dir ) {
		print "Directory does not exists: $mib_vendor_dir\n";
	}
	push (@mibdirs_array,$mib_vendor_dir);
}


my $mibdirs_ref=\@mibdirs_array;

my $session = new SNMP::Info (
                        AutoSpecify => 1,
                        Debug       => $debug,
                        DestHost    => $node,
                        Community => $community,
                        Version     => $snmp_version,
                        MibDirs     => $mibdirs_ref,
                        ) or die "SNMP::Info: Not OK.\n\n";

my $err = $session->error();
die "SNMP Community or Version probably wrong connecting to device. $err\n" if defined $err;

my $name="";
my $class="";
$name  = $session->name();
$class = $session->class();
if ( $name || $class ) { 
	print "SNMP::Info OK (SNMP::Info is using this device class : $class (hostname: $name)\n";
} else {
	print "NO OK: SNMP::Info does not return a result\n";
	print "set \$debug to \"1\" to display debugging information and run this script again\n";
}
print "\n";
