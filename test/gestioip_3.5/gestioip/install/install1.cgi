#!/usr/bin/perl -T -w

# Copyright (C) 2011 Marc Uebel

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
use Socket;

my $daten=<STDIN>;
my %daten=Aufbereiter($daten);

my $webserver_host=$daten{'webserver_host'} || "127.0.0.1";
my $bbdd_port=$daten{'bbdd_port'} || "3306";
my $bbdd_host=$daten{'bbdd_host'} || "127.0.0.1";
my $bbdd_admin=$daten{'bbdd_admin'} || "root";
my $bbdd_admin_pass=$daten{'bbdd_admin_pass'};
my $user=$daten{'bbdd_user'} || "gestioip";
my $password=$daten{'bbdd_user_pass'};
my $password_retype=$daten{'bbdd_user_pass_retype'};
my $sid=$daten{'sid'} || "gestioip";

if ( $webserver_host eq $bbdd_host ) {
	$webserver_host="127.0.0.1";
	$bbdd_host="127.0.0.1";
}

my $lang;
if ( $ENV{'QUERY_STRING'} ) {
        $ENV{'QUERY_STRING'} =~ /.*lang=(\w{2}).*/;
        $lang=$1;
        my $fut_time=gmtime(time()+365*24*3600)." GMT";
        my $cookie = "GestioIPLang=$lang; path=/; expires=$fut_time; 0";
        print "Set-Cookie: " . $cookie . "\n";
} elsif ( $ENV{'HTTP_COOKIE'} ) {
        $ENV{'HTTP_COOKIE'} =~ /.*GestioIPLang=(\w{2}).*/;
        $lang=$1;
}
if ( ! $lang ) {
        $lang=$ENV{HTTP_ACCEPT_LANGUAGE};
        $lang =~ /(^\w{2}).*/;
        $lang = $1;
}

my $config;
if ( $lang eq "es" ) {
        $config="./vars_es";
} elsif ( $lang eq "en" ) {
        $config="./vars_en";
} elsif ( $lang eq "de" ) {
        $config="./vars_de";
} else {
        $config="./vars_es";
}

open(CONFIG,"<$config") or die "can't open datafile: $!";
       my %preferences;

       while (<CONFIG>) {
               chomp;
               s/#.*//;
               s/^\s+//;
               s/\s+$//;
               next unless length; 
               my ($var, $value) = split(/\s*=\s*/, $_, 2); 
               $preferences{$var} = $value; 
       }
close CONFIG; 


print <<EOF;
Content-type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<HTML>
<head><title>$preferences{title}</title>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<link rel="stylesheet" type="text/css" href="./stylesheet.css">
<link rel="shortcut icon" href="./favicon.ico">
</head>

<body>
<div id=\"AllBox\">
<div id=\"TopBox\">
<table border="0" width="100%" cellpadding="2"><tr><td width="20%">
  <span class="TopTextGestio">Gesti&oacute;IP</span>
</td><td>
  <p class="TopText">$preferences{instalacion_message}</p>
</td><td>
</td></tr></table>

</div>
<div id=\"LeftMenu\">
<div id=\"LeftMenuIntro1o\">
$preferences{welcome_message}
</div>
<div id=\"LeftMenuIntro2oa\">
$preferences{left_bbdd_crear_message}
</div>
<div id=\"LeftMenuIntro3\">
$preferences{left_bbdd_configuration_message}
</div>
<div id=\"LeftMenuIntro4\">
$preferences{left_bbdd_termination_message}
<br><hr>
</div>
</div>
<div id=\"Inhalt\">
EOF

print "<b>$preferences{left_bbdd_crear_message}</b><p><br>";

my $error=0;
if ( ! $bbdd_host ) {
	print "$preferences{install1_bbdd_host_error}<br>\n";
	$error = 1;
} elsif ( ! $bbdd_port ) {
	print "$preferences{install1_bbdd_port_error}<br>\n";
	$error = 1;
} elsif ( ! $bbdd_admin ) {
	print "$preferences{install1_bbdd_su_error}<br>\n";
	$error = 1;
} elsif ( ! $bbdd_admin_pass ) {
	print "$preferences{install1_bbdd_su_pass_error}<br>\n";
	$error = 1;
} elsif ( ! $user ) {
	print "$preferences{install1_bbdd_admin_error}<br>\n";
	$error = 1;
} elsif ( ! $password ) {
	print "$preferences{install1_bbdd_admin_pass_error}<br>\n";
	$error = 1;
} elsif ( ! $password_retype ) {
	print "$preferences{install1_bbdd_admin_pass_retype_error}<br>\n";
	$error = 1;
} elsif ( ! $sid ) {
	print "$preferences{install1_bbdd_sid_error}<br>\n";
	$error = 1;
} elsif ( $password ne $password_retype ) {
	print "$preferences{install1_admin_pass_noco_error}<br>\n";
	$error = 1;
}

if ( "$webserver_host" ne "$bbdd_host" ) {
	if ( $webserver_host =~ /127.0.0.1/ || $bbdd_host =~ /127.0.0.1/ ) {
		print "$preferences{install1_server_not_igual_error}<br>\n";
		$error = 1;
	}
}
	

if ( $error ne 0 ) {
	print "<p>$preferences{back_button}<p>\n";
	print "</div>\n";
	print "</div>\n";
	print "</body>\n";
	print "</html>\n";
	exit 1;
}


my $DocumentRoot=$0;
my $SCRIPT_NAME=$ENV{'SCRIPT_NAME'};
$DocumentRoot =~ s/$SCRIPT_NAME//;

my $ServerSoftware="$ENV{SERVER_SOFTWARE}";
my $se_linux_hint;

if ( $ServerSoftware =~ /fedora|red.?hat|centos/i ) {
	$se_linux_hint=$preferences{se_linux_hint_fedora_message};
}

my $config_file = "../priv/ip_config";

$preferences{check_derechos_message} =~ s/DocumentRoot/$DocumentRoot/g;
open(CONFIG,"+< $config_file") or die print_end("<b>ERROR</b>:<p> $config_file: $!<p>$preferences{check_derechos_message}<p><br>$preferences{back_button}");
my @config = <CONFIG>;
my $i="0";
my $item;
my @config_new;
foreach $item(@config) {
	$item =~ s/^bbdd_host=.*$/bbdd_host=$bbdd_host/;
	$item =~ s/^bbdd_port=.*$/bbdd_port=$bbdd_port/;
	$item =~ s/^sid=.*$/sid=$sid/;
	$item =~ s/^user=.*$/user=$user/;
	$item =~ s/^password=.*$/password=$password/;
	$config_new[$i++]=$item;
}
seek(CONFIG,0,0) or die "Seek: $!";
print CONFIG @config_new or die "print: $!";
truncate(CONFIG, tell(CONFIG)) or die "cut the rest: $!";
close CONFIG;

check_if_db_exists($bbdd_host,$bbdd_port,$bbdd_admin,$bbdd_admin_pass,$sid);
	
create_db($webserver_host,$bbdd_host,$bbdd_port,$bbdd_admin,$bbdd_admin_pass,$user,$password,$sid);
create_tables($bbdd_host,$bbdd_port,$user,$password,$sid);

print "<p><br>$preferences{install1_ok_message}<p><br>";


print "<a href=\"./install2_form.cgi\">$preferences{next}</a><p>\n";

print_end();


########### subroutines #######


sub print_end {
	my $message=shift(@_);
	print "$message\n" if $message;
	print "<p><br><p>\n";
	print "</div>\n";
	print "</div>\n";
	print "</body>\n";
	print "</html>\n";
	exit;
}

sub check_if_db_exists {
	my ($bbdd_host,$bbdd_port,$bbdd_admin,$bbdd_admin_pass,$sid) = @_;
	my $dbh = DBI->connect("DBI:mysql:$sid:$bbdd_host:$bbdd_port",$bbdd_admin,$bbdd_admin_pass,{
		PrintError => 0,
		RaiseError => 0
	} );
	print_end("<b>ERROR</b><p>\"$sid\": $preferences{bbdd_exists_error}<p><a href=\"./install2_form.cgi\">$preferences{next}</a><p><br>\n$preferences{bbdd_exists_error2} $preferences{back_button}") if ( $dbh );
	$dbh->disconnect() if ( $dbh );
}

sub create_db {
	my ($webserver_host, $bbdd_host, $bbdd_port, $bbdd_admin, $bbdd_admin_pass, $user, $password, $sid) = @_;
	my ( $bbdd_create_error_hint, $webserver_ip);
	if ( "$bbdd_host" eq "$webserver_host" ) {
		$bbdd_create_error_hint = "";
	} else {
		$bbdd_create_error_hint="$preferences{bbdd_remote_root_error_hint}";
	}
	print "$preferences{bbdd_connect_message}";
	my $connect_error_bbdd; 
	my $dbh = DBI->connect("dbi:mysql:host=$bbdd_host;port=$bbdd_port", $bbdd_admin, $bbdd_admin_pass, {
		PrintError => 1,
		RaiseError => 0
	} ) or $connect_error_bbdd = $DBI::errstr;
	if ( $connect_error_bbdd ) {
		if ($connect_error_bbdd =~ /Access denied/ || $connect_error_bbdd =~ /Host / ) {
			my $real_webserver;
			if ( $connect_error_bbdd =~ /Access denied/ ) {
				$connect_error_bbdd =~ /Access denied for user 'root'\@'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'.*/;
				$real_webserver = $1;
			} elsif ( $connect_error_bbdd =~ /Host / ) {
				$connect_error_bbdd =~ /Host '(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' is not allowed/;
				$real_webserver = $1;
			}
			if ( $real_webserver ) {
				$bbdd_create_error_hint =~ s/IP_OF_WEBSERVER/$real_webserver/g;
			}
			print_end("$preferences{bbdd_access_denied_error}<p>$connect_error_bbdd<p><br>$bbdd_create_error_hint<p><br><p>$preferences{back_button}");
			exit 1;
		} elsif ( $connect_error_bbdd =~ /Can't connect to MySQL|Can't create TCP\/IP socket/ ) {
			if ( $se_linux_hint ) {
				print_end("$preferences{bbdd_connection_error}<p>$connect_error_bbdd<p><br>$preferences{bbdd_connect_error_se}<p>$se_linux_hint<p><br><p>$preferences{back_button}");
			} else {
				print_end("$preferences{bbdd_connection_error}<p>$connect_error_bbdd<p><br><p>$preferences{back_button}");
			}
		} else {
			print_end("$preferences{bbdd_connect_error}<p>$connect_error_bbdd<p><br><p>$preferences{back_button}");
		}
			
	}

    # check mysql version
    my $mysql_version = "$dbh->{mysql_serverversion}\n";

	print "<span class=\"OKText\">OK</span><p>";
	print "Found MySQL version: $mysql_version<p>";
	my $qpassword = $dbh->quote( $password );
	my $qwebserver_host = $dbh->quote( $webserver_host );
	my $qwebserver_ip = $dbh->quote( $webserver_ip );
	my $quser = $dbh->quote( $user );
	print "$preferences{bbdd_crear_message} $sid...";
	$dbh->do("CREATE DATABASE IF NOT EXISTS $sid CHARACTER SET utf8 COLLATE utf8_general_ci") or die print_error("$preferences{bbdd_create_error}<p>$DBI::errstr<p><br><p>$bbdd_create_error_hint<p><br><p>$preferences{back_button}");
	print "<span class=\"OKText\">OK</span><p>";

    if ( $mysql_version =~ /^8/ ) {
        if ( $webserver_host eq "localhost" || $webserver_host =~ /127.0.0.1/ ) {
            $dbh->do("CREATE USER $quser\@'localhost' IDENTIFIED WITH 'mysql_native_password' BY $qpassword;") or die print_error("<p>Can not create user: $quser<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("CREATE USER $quser\@'127.0.0.1' IDENTIFIED WITH 'mysql_native_password' BY $qpassword;") or die print_error("<p>Can not create user: $quser<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("CREATE USER $quser\@'localhost.localdomain' IDENTIFIED WITH 'mysql_native_password' BY $qpassword;") or die print_error("<p>Can not create user: $quser<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL PRIVILEGES ON $sid.* TO $quser\@'localhost';") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL PRIVILEGES ON $sid.* TO $quser\@'127.0.0.1';") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL PRIVILEGES ON $sid.* TO $quser\@'localhost.localdomain';") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            print "GRANT ALL PRIVILEGES ON $sid.* to $user" . "@" . "127.0.0.1";
        } else {
            $dbh->do("CREATE USER $quser\@$qwebserver_host IDENTIFIED BY $qpassword;") or die print_error("<p>Can not create user: $quser<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL PRIVILEGES ON $sid.* TO $quser\@$qwebserver_host;") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            print "GRANT ALL ON $sid.* to $user" . "@" . "$webserver_host IDENTIFIED BY \"********\"...";
        }	
    } else {
        if ( $webserver_host eq "localhost" || $webserver_host =~ /127.0.0.1/ ) {
            $dbh->do("GRANT ALL ON $sid.* TO $quser\@localhost IDENTIFIED BY $qpassword;") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL ON $sid.* TO $quser\@127.0.0.1 IDENTIFIED BY $qpassword;") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            $dbh->do("GRANT ALL ON $sid.* TO $quser\@localhost.localdomain IDENTIFIED BY $qpassword;") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            print "GRANT ALL ON $sid.* to $user" . "@" . "127.0.0.1 IDENTIFIED BY \"********\"...";
        } else {
            $dbh->do("GRANT ALL ON $sid.* TO $quser\@$qwebserver_host IDENTIFIED BY $qpassword;") or die print_error("<p>$preferences{bbdd_grant_error}<p>$DBI::errstr<p>$preferences{back_button}");
            print "GRANT ALL ON $sid.* to $user" . "@" . "$webserver_host IDENTIFIED BY \"********\"...";
        }
    }
	print "<span class=\"OKText\">OK</span><p>";
}


sub create_tables {
	my ($bbdd_host,$bbdd_port,$user,$password,$sid) = @_;

	print "$preferences{bbdd_create_tables_message}";

        my $dbh = mysql_verbindung($bbdd_host,$bbdd_port,$sid,$user,$password) or die print_end("$preferences{bbdd_connect_gestioip_error}<p>$DBI::errstr<p>$preferences{back_button}");

        my $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS net (red varchar(40), BM varchar(3) NOT NULL, descr varchar(500), red_num mediumint(7) auto_increment, loc smallint(3) NOT NULL, vigilada varchar(1), comentario varchar(500), categoria smallint(3), ip_version varchar(2), rootnet smallint(1) DEFAULT '0', dyn_dns_updates smallint(1) DEFAULT '1', parent_network_id varchar(7) DEFAULT '', discover_device varchar(40) DEFAULT '', client_id smallint (4), INDEX (red), PRIMARY KEY (red_num))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS host (id int(10) AUTO_INCREMENT, ip varchar(40), hostname varchar(100), host_descr varchar(500), loc smallint(3), red_num mediumint(7) NOT NULL, categoria smallint(3), int_admin varchar(1), comentario varchar(500), update_type varchar(5), last_update bigint(20), alive tinyint(1) default '-1', last_response bigint(20), range_id smallint(3) default '-1', ip_version varchar(2), dyn_dns_updates smallint(1), client_id smallint (4), INDEX (ip), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS locations (id smallint(2), loc varchar(60), client_id smallint (4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS categorias (id smallint(2), cat varchar(60), UNIQUE (cat), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS categorias_net (id smallint(2), cat varchar(60), UNIQUE (cat), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS update_type (id smallint(2), type varchar(15), UNIQUE (type), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth = $dbh->prepare("INSERT INTO update_type VALUES ('-1','NULL'),(1,'man'),(2,'dns'),(3,'ocs')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

### Audit

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS audit (id int(10) AUTO_INCREMENT, event varchar(10000) not NULL, user varchar(50) default NULL, event_class smallint(3) default NULL, event_type smallint(4) default NULL, update_type_audit smallint(3) default NULL, date bigint(20) not NULL, remote_host varchar(42), client_id smallint (4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS audit_auto (id int(10) AUTO_INCREMENT, event varchar(10000) not NULL, user varchar(50) default NULL, event_class smallint(3) default NULL, event_type smallint(4) default NULL, update_type_audit smallint(3) default NULL, date bigint(20) not NULL, remote_host varchar(42), client_id smallint (4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS event_classes ( id smallint(5) NOT NULL, event_class varchar(150) default NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS event_types ( id smallint(5) NOT NULL, event_type varchar(150) default NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS update_types_audit ( id smallint(5) NOT NULL, update_types_audit varchar(25) default NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth = $dbh->prepare("INSERT INTO event_types VALUES (1,'host edited'),(2,'net edited'),(3,'range changed'),(4,'man synch'),(5,'red split'),(6,'red joined'),(7,'red cleared'),(8,'cat host added'),(9,'cat net added'),(10,'loc added'),(11,'cat host deleted'),(12,'cat net deleted'),(13,'loc deleted'),(14,'host deleted'),(15,'host added'),(16,'net deleted'),(17,'net added'),(18,'range deleted'),(19,'range added'),(20,'loc renamed'),(21,'cat host renamed'),(22,'cat net renamed'),(23,'auto synch dns'),(24,'auto synch ocs'),(25,'config edited'),(26,'auto audit deleted'),(27,'man audit deleted'),(28,'host reserved'),(29,'net list exported'),(30,'host list exported'),(31,'net column added'),(32,'net column deleted'),(33,'client added'),(34,'client deleted'),(35,'client edited'),(36,'vlan added'),(37,'vlan deleted'),(38,'vlan edited'),(39,'vlan prov added'),(40,'vlan prov deleted'),(41,'vlan prov edited'),(42,'host column added'),(43,'host column deleted'),(44,'auto synch snmp'),(45,'man ini'),(46,'auto auto ini'),(47,'all networks deleted'),(48,'AS added'),(49,'AS edited'),(50,'AS deleted'),(51,'AS client added'),(52,'AS client edited'),(53,'AS client deleted'),(54,'line added'),(55,'line edited'),(56,'line deleted'),(57,'line client added'),(58,'line client edited'),(59,'line client deleted'),(100,'ping status changed'),(101,'device user group added'),(102,'device user group edited'),(103,'device user group deleted'),(104,'device type group added'),(105,'device type group edited'),(106,'device type group deleted'),(107,'device conf mgnt edited'),(108,'fetch_config executed'),(110,'cm server added'),(111,'cm server edited'),(112,'cm server deleted'),(113,'job group added'),(114,'job group edited'),(115,'job group deleted'),(116,'user added'),(117,'user edited'),(118,'user deleted'),(119,'user group added'),(120,'user group edited'),(121,'user group deleted'),(125,'site column added'),(126,'site column deleted'),(127,'site edited'),(128,'Master key changed'),(129,'Master key deleted'),(130,'User password changed'),(131,'Device password added'),(132,'Device password changed'),(133,'Device password deleted'),(134,'Master key added'),(135,'DNS update user added'),(136,'DNS update user modified'),(137,'DNS update user deleted'),(138,'DNS zone added'),(139,'DNS zone modified'),(140,'DNS zone deleted'), (141,'ACLs imported'), (142,'ACLs deleted'), (143,'ACLs connections import'), (144,'ACLs connection added'), (145,'ACLs connection modified'), (146,'ACLs connection deleted'), (147,'net column edited'), (148,'host column edited'), (149,'site column edited'), (150,'line column edited'), (151,'line column added'), (152,'line column deleted'),  (153,'mac deleted'), (154,'mac added'), (155,'mac edited'), (156,'log edited'), (157,'tag added'), (158,'tag deleted'), (159,'tag edited'), (160,'DNS key added'), (161,'DNS key deleted'), (162,'DNS key edited'), (163,'SNMP group added'), (164,'SNMP group deleted'), (165,'SNMP group edited'), (166,'User password reset'), (167,'User master key updated'), (168,'DNS server group added'), (169,'DNS server group deleted'), (170,'DNS server group edited'), (171, 'Audit access'), (172, 'Login failure'),(173,'job added'), (174,'job edited'), (175,'job deleted'), (176,'job executed'), (177,'SMTP server added'), (178,'SMTP server edited'), (179,'SMTP server deleted'), (180,'LDAP server added'), (181,'LDAP server edited'), (182,'LDAP server deleted'), (183,'User login password changed')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");


	$sth = $dbh->prepare("INSERT INTO event_classes VALUES (1,'host'),(2,'net'),(3,'security'),(4,'dns'),(5,'admin'),(6,'conf'),(7,'vlan_man'),(8,'vlan_auto'),(9,'ini_man'),(10,'ini_auto'),(11,'AS'),(12,'AS client'),(13,'line'),(14,'line client'),(20,'conf mgnt'),(21,'user mgnt'),(22,'arin mgnt'),(23,'sites'),(24,'password mgnt'),(25,'DNS update'),(26,'ACL'),(27,'ACL connection'),(28,'MAC'),(29,'Tag'),(30,'SNMP Group'),(31,'DNS Server Group'),(33, 'scheduled job'),(34, 'smtp server'),(35, 'LDAP server'),(36,'dhcp sync')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth = $dbh->prepare("INSERT INTO update_types_audit VALUES (1,'man'),(2,'auto'),(3,'auto snmp'),(4,'auto dns'), (5,'auto ocs'),(6,'man dns'),(7,'man snmp'),(8,'man net sheet'),(9,'man range'),(10,'man host sheet'),(11,'red cleared'),('12','vlan sheet'),('13','api'),(14,'auto prtg'),(15,'dhcp sync'),(17,'sheet'),(18,'dhcp sync'),(19,'auto cloud')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");


### Ranges

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS ranges (id smallint(5) NOT NULL default '0', start_ip varchar(40) NOT NULL default '0', end_ip varchar(40) NOT NULL default '0', comentario varchar(50) default NULL, range_type varchar(2) default '-1', red_num varchar(5) default NULL, client_id smallint (4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ranges:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ranges:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE range_type (id smallint(4) NOT NULL default '0', range_type varchar(20) NOT NULL default '0', PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO range_type (id,range_type) VALUES ('1','workst (DHCP)'),('2','wifi (DHCP)'),('3','VoIP (DHCP)'),('4','other (DHCP)'),('5','other')");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>$preferences{back_button}");

### CONFIG

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS config (id smallint(8) AUTO_INCREMENT, smallest_bm smallint(2), max_sinc_procs smallint(3), ignorar varchar(250) default NULL, ignore_generic_auto varchar(3), generic_dyn_host_name varchar(250) default NULL, set_sync_flag varchar(3), dyn_ranges_only varchar(1) default 'n', ping_timeout tinyint(2) default '2', confirmation varchar(3) default 'no', client_id smallint (4), smallest_bm6 varchar(3), ocs_enabled varchar(3) DEFAULT 'no', ocs_database_user varchar(30), ocs_database_name varchar(30), ocs_database_pass varchar(30), ocs_database_ip varchar(42), ocs_database_port varchar(30), ignore_dns tinyint(1) DEFAULT 0, confirm_dns_delete varchar(3) DEFAULT 'no', delete_down_hosts varchar(3) DEFAULT 'no', PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ranges:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table config:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO config (smallest_bm,max_sinc_procs,ignore_generic_auto,set_sync_flag,confirmation,client_id,smallest_bm6,ocs_enabled,ocs_database_name,ocs_database_port,ocs_database_user) VALUES ('16','254','yes','no','yes','1','64','no','ocsweb','3306','ocs')");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table config:<p>$DBI::errstr<p>$preferences{back_button}");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS global_config (id smallint(8) AUTO_INCREMENT, version varchar(10) NOT NULL, default_client_id varchar(150) NOT NULL, confirmation varchar(4) NOT NULL, mib_dir varchar(100), vendor_mib_dirs varchar(500), ipv4_only varchar(3) , as_enabled varchar(3), leased_line_enabled varchar(3), configuration_management_enabled varchar(3), cm_backup_dir varchar(500), cm_licence_key varchar(500), cm_log_dir varchar(500), cm_xml_dir varchar(500), auth_enabled varchar(3) DEFAULT 'no', freerange_ignore_non_root tinyint(1) DEFAULT 0 NOT NULL, arin_enabled varchar(3) DEFAULT 'no', local_filter_enabled varchar(3) DEFAULT 'no' NOT NULL, site_management_enabled varchar(3) DEFAULT 'no' NOT NULL, password_management_enabled varchar(3) DEFAULT 'no', dyn_dns_updates_enabled varchar(3) DEFAULT 'no', acl_management_enabled varchar(3) DEFAULT 'no', mac_management_enabled varchar(3) DEFAULT 'no', site_search_main_menu tinyint(1) DEFAULT 0 NOT NULL, line_search_main_menu tinyint(1) DEFAULT 0 NOT NULL, limit_cc_output_enabled varchar(3) DEFAULT 'yes' NOT NULL, debug_enabled varchar(3) DEFAULT 'no' NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ranges:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table global_config:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO global_config (version,default_client_id,confirmation,mib_dir,vendor_mib_dirs,ipv4_only,as_enabled,leased_line_enabled,configuration_management_enabled,cm_backup_dir,cm_log_dir,cm_xml_dir) VALUES ('3.5.5','1','yes','/usr/share/gestioip/mibs','3com,aerohive,alcatel,allied,apc,arista,aruba,asante,avaya,bluecoat,bluesocket,cabletron,checkpoint,cisco,citrix,colubris,cyclades,dell,d-link,enterasys,extreme,extricom,f5,force10,fortinet,foundry,h3c,hp,huawei,ibm,juniper,lantronix,mikrotik,netapp,netgear,netscreen,net-snmp,nortel,packetfront,paloalto,pica8,rad,rfc,riverbed,ruckus,sonicwall,trapeze,xirrus','yes','no','no','no','/usr/share/gestioip/conf','/usr/share/gestioip/var/log','/usr/share/gestioip/var/devices')");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table global_config:<p>$DBI::errstr<p>$preferences{back_button}");


### CUSTOM NET COLUMNS

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_net_columns (id smallint(4) NOT NULL default '0', name varchar(40) NOT NULL, column_type_id tinyint(3) default '-1', client_id smallint(4) NOT NULL, mandatory tinyint(1) DEFAULT 0, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_net_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_net_columns:<p>$DBI::errstr<p>$preferences{back_button}");

    $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_net_column_entries (id mediumint(8) AUTO_INCREMENT, cc_id smallint(4) NOT NULL default '0', net_id mediumint(7) NOT NULL default '0', entry varchar(150) NOT NULL, client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_net_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_net_columns_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO custom_net_columns VALUES (1,'usage', 9, 9999, 0)") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

    $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_column_select (id mediumint(6) AUTO_INCREMENT, type varchar(1), items varchar(1000), cc_id smallint(5), PRIMARY KEY (id))")
		or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_column_select:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_column_select:<p>$DBI::errstr<p>$preferences{back_button}");



### PREDEFINDED NET COLUMNS

        $sth = $dbh->prepare("CREATE TABLE predef_net_columns (id smallint(4) NOT NULL default '0', name varchar(40) NOT NULL, PRIMARY KEY (id));") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table predef_net_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table predef_net_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO predef_net_columns VALUES ('-1','NOTYPE'),(1,'vlan'),(2,'Fav'),(3,'VRF'),(4,'ifDescr'),(5,'ifAlias'),(6,'local'),(7,'DNSZone'),(8,'DNSPTRZone'),(9,'usage'),(10,'SNMPGroup'),(11,'Tag'),(13,'DNSSG'),(14,'ScanAZone'),(15,'ScanPTRZone')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");



### CUSTOM HOST COLUMNS

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_host_columns (id smallint(4) NOT NULL default '0', name varchar(40) NOT NULL, column_type_id tinyint(3) default '-1', client_id smallint(4) NOT NULL, mandatory tinyint(1) DEFAULT 0, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_host_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_host_columns:<p>$DBI::errstr<p>$preferences{back_button}");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_host_column_entries (id int(10) AUTO_INCREMENT, cc_id smallint(4) NOT NULL default '0', pc_id smallint(4) NOT NULL, host_id int(10) NOT NULL default '0', entry varchar(10000) NOT NULL, client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_host_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_host_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");


        $sth = $dbh->prepare("CREATE INDEX host_id_index ON custom_host_column_entries(host_id)") or die print_end("<p>$preferences{bbdd_create_table_error}<p>INDEX host_id_index table custom_host_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>INDEX host_id_index table custom_host_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");

    $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_host_column_select (id mediumint(6) AUTO_INCREMENT, type varchar(1), items varchar(1000), cc_id smallint(5), PRIMARY KEY (id))")
		or die print_end("<p>$preferences{bbdd_create_table_error}<p>table host custom_column_select:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table host custom_colun_select:<p>$DBI::errstr<p>$preferences{back_button}");



### PREDEFINDED HOST COLUMNS

        $sth = $dbh->prepare("CREATE TABLE predef_host_columns (id smallint(4) NOT NULL default '0', name varchar(40) NOT NULL, PRIMARY KEY (id));") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table predef_host_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table predef_host_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO predef_host_columns VALUES ('-1','NOTYPE'),(1,'vendor'),(2,'model'),(3,'contact'),(4,'serial'),(5,'MAC'),(6,'OS'),(7,'device_descr'),(8,'device_name'),(9,'device_loc'),(10,'URL'),(11,'rack'),(12,'RU'),(13,'switch'),(14,'port'),(15,'linkedIP'),(16,'CM'),(17,'ifDescr'),(18,'ifAlias'),(19,'Line'),(20,'Tag'),(21,'SNMPGroup'),(22,'VLAN'),(23,'Sec_Zone'),(24,'Instance')") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");



### CLIENTS

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS clients (id smallint(4) NOT NULL default '0', client varchar(50) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO clients (id,client) VALUES ('1','DEFAULT')");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");


        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS client_entries ( id smallint(8) AUTO_INCREMENT, client_id smallint(4) NOT NULL, phone varchar(30), fax varchar(30), address varchar(500), comment varchar(500), contact_name_1 varchar(200), contact_phone_1 varchar(25), contact_cell_1 varchar(25), contact_email_1 varchar(50), contact_comment_1 varchar(500), contact_name_2 varchar(200), contact_phone_2 varchar(25), contact_cell_2 varchar(25), contact_email_2 varchar(50), contact_comment_2 varchar(500), contact_name_3 varchar(200), contact_phone_3 varchar(25), contact_cell_3 varchar(25), contact_email_3 varchar(50), contact_comment_3 varchar(500), default_resolver varchar(3) DEFAULT 'yes', dns_server_1 varchar(50) DEFAULT '', dns_server_2 varchar(50) DEFAULT '',dns_server_3 varchar(50) DEFAULT '', dns_server_1_key_name varchar(50),dns_server_2_key_name varchar(50),dns_server_3_key_name varchar(50),dns_server_1_key varchar(100),dns_server_2_key varchar(100),dns_server_3_key varchar(100), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table client_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table client_entries:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO client_entries (client_id) VALUES ('1')");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");


### VLANS

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS vlans (id smallint(8) AUTO_INCREMENT, vlan_num varchar(10), vlan_name varchar(250) default NULL, comment varchar(500) default NULL, provider_id smallint(5), bg_color varchar(20), font_color varchar(20), switches varchar(10000), asso_vlan smallint(5), client_id smallint(4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

        $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS vlan_providers (id smallint (4), name varchar(100) default NULL, comment varchar(500), client_id smallint(4), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

        $sth = $dbh->prepare("INSERT INTO vlan_providers (id,name,comment,client_id) VALUES ('-1','','','9999')") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");


### AUTONOMOUS SYSTMES

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS autonomous_systems (id int(10) AUTO_INCREMENT, as_number int(12), description varchar(500), comment varchar(500), as_client_id smallint(4) DEFAULT '-1', client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS autonomous_systems_clients (id int(10) AUTO_INCREMENT, client_name varchar(100), type varchar(100), description varchar(500), comment varchar(500), phone varchar(30), fax varchar(30), address varchar(500), contact varchar(500), contact_email varchar(100), contact_phone varchar(30), contact_cell varchar(30), client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO autonomous_systems_clients (id,client_name,client_id) VALUES ('-1','_DEFAULT_','9999')") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");


### LEASED LINES

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS llines (id int(10) AUTO_INCREMENT, phone_number varchar(50), description varchar(500), comment varchar(500), loc smallint(3) DEFAULT '-1', ll_client_id smallint(4) DEFAULT '-1', type varchar(100), service varchar(100), device varchar(500), room varchar(500), ad_number varchar(100), client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS llines_clients (id int(10) AUTO_INCREMENT, client_name varchar(100), type varchar(100), description varchar(500), comment varchar(500), phone varchar(30), fax varchar(30), address varchar(500), contact varchar(500), contact_email varchar(100), contact_phone varchar(30), contact_cell varchar(30), client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table lline_clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table lline_clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO llines_clients (id,client_name,client_id) VALUES ('-1','_DEFAULT_','9999')") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table clients:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_line_column_select (id mediumint(6) AUTO_INCREMENT, type varchar(1), items varchar(1000), cc_id smallint(5), PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_select:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_select:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO custom_line_column_select (type,items,cc_id) VALUES ('s','leased,dial-up','9998'),('s','T1,T2,T3,T4,ISDN,DSL,ADSL','9999')") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_select:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_select:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_line_columns (id smallint(4) AUTO_INCREMENT, name varchar(100) NOT NULL, mandatory tinyint(1) DEFAULT 0, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_columns:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_columns:<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_line_column_entries(id smallint(4) AUTO_INCREMENT, column_id smallint(4) NOT NULL, line_id smallint(4) NOT NULL, entry varchar(100) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_line_column_entries:<p>$DBI::errstr<p>$preferences{back_button}");



### MAC MANAGEMENT


	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS allowed_macs (id smallint(4) AUTO_INCREMENT, mac varchar(17) NOT NULL, duid varchar(50) NOT NULL, account varchar(300) NOT NULL, host varchar(300) NOT NULL, comment varchar(500) NOT NULL, client_id smallint(4) NOT NULL, PRIMARY KEY (id))") or die print_end("<p>$preferences{bbdd_create_table_error}<p>table allowed_macs:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table allowed_macs:<p>$DBI::errstr<p>$preferences{back_button}");




### CONFIGURATION MANAGEMENT CM


	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS device_cm_config ( id smallint(4) AUTO_INCREMENT, host_id int(10) NOT NULL, device_type_group_id smallint(4) NOT NULL, device_user_group_id smallint(4), user_name varchar(100), login_pass varchar(100), enable_pass varchar(100), description varchar(500), connection_proto varchar(20), connection_proto_args varchar(20), cm_server_id varchar(20), save_config_changes smallint(1) DEFAULT 0, last_backup_date datetime, last_backup_status smallint(2) DEFAULT '-1', last_backup_log varchar(40), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_cm_config:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_cm_config:<p>$DBI::errstr<p>$preferences{back_button}");


	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS device_jobs ( id smallint(4) AUTO_INCREMENT, host_id int(10) NOT NULL, job_name varchar(50), job_group_id smallint(4), job_descr varchar(500), job_type_id smallint(3), last_execution_date datetime, last_execution_status smallint(2) DEFAULT '-1', last_execution_log varchar(40), enabled smallint (1), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_jobs:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_jobs:<p>$DBI::errstr<p>$preferences{back_button}");



	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS device_user_groups ( id smallint(4) AUTO_INCREMENT, name varchar(100) NOT NULL, user_name varchar(100) NOT NULL, login_pass varchar(100) NOT NULL, enable_pass varchar(100) NOT NULL, description varchar(500), rsa_identity_file varchar(300), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_user_groups:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_user_groups>$DBI::errstr<p>$preferences{back_button}");


	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS device_job_groups ( id smallint(4) AUTO_INCREMENT, name varchar(100) NOT NULL, description varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_job_groups:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_job_groups<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO device_job_groups (name,description,client_id) VALUES ('backup_daily','example group',1)") or die print_end("<p>$preferences{bbdd_insert_error_message}: device_job_groups<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_job_groups<p>$DBI::errstr<p>$preferences{back_button}");



	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS cm_server ( id smallint(4) AUTO_INCREMENT, name varchar(100) NOT NULL, ip varchar(40) NOT NULL, server_root varchar(500) NOT NULL, cm_server_type varchar(10), cm_server_description varchar(500), cm_server_username varchar(100), cm_server_password varchar(100), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table cm_server:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table cm_server>$DBI::errstr<p>$preferences{back_button}");



### USER MANAGEMENT

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS gip_users ( id smallint(4) AUTO_INCREMENT, name varchar(60) NOT NULL, group_id smallint(4), email varchar(50), phone varchar(50), comment varchar(500), type varchar(12), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_users:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_users<p>$DBI::errstr<p>$preferences{back_button}");

    my $gip_user=$ENV{'REMOTE_USER'} || "";
    if ( $gip_user ) {
        my $qgip_user = $dbh->quote( $gip_user );
        $sth = $dbh->prepare("INSERT INTO gip_users (name, group_id, comment, type) VALUES ($qgip_user, 1, 'Default admin user', 'local')") or die print_end("<p>$preferences{bbdd_insert_error_message}<p>$DBI::errstr");
        $sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups<p>$DBI::errstr<p>$preferences{back_button}");
    }

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS gip_user_groups ( id smallint(4) AUTO_INCREMENT, name varchar(60) NOT NULL, description varchar(500), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO gip_user_groups (name,description) VALUES ('GestioIP Admin','Default group with all rights including rights to create, update and delete Users, clients and the GestioIP configuration')") or die print_end("<p>$preferences{bbdd_insert_error_message}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups<p>$DBI::errstr<p>$preferences{back_button}");
	$sth = $dbh->prepare("INSERT INTO gip_user_groups (name,description) VALUES ('Admin','Default group with rights to create, update, delete GestioIP objects like networks, hosts and VLANs')") or die print_end("<p>$preferences{bbdd_insert_error_message}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups<p>$DBI::errstr<p>$preferences{back_button}");
	$sth = $dbh->prepare("INSERT INTO gip_user_groups (name,description) VALUES ('Read Only','Default group with rights to show GestioIP objects like networks, hosts and VLANs')") or die print_end("<p>$preferences{bbdd_insert_error_message}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_groups<p>$DBI::errstr<p>$preferences{back_button}");



	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS gip_user_group_perms ( id smallint(4) AUTO_INCREMENT, group_id smallint(4), manage_gestioip_perm tinyint(1) NOT NULL, manage_user_perm tinyint(1) NOT NULL, manage_sites_and_cats_perm tinyint(1) NOT NULL, manage_custom_columns_perm tinyint(1) NOT NULL, read_audit_perm tinyint(1) NOT NULL, clients_perm varchar(100) NOT NULL, cat_perm varchar(200) NOT NULL, loc_perm varchar(200) NOT NULL, create_net_perm tinyint(1) NOT NULL, read_net_perm tinyint(1) NOT NULL, update_net_perm tinyint(1) NOT NULL, delete_net_perm tinyint(1) NOT NULL, read_host_perm tinyint(1) NOT NULL, create_host_perm tinyint(1) NOT NULL, update_host_perm tinyint(1) NOT NULL, delete_host_perm tinyint(1) NOT NULL, read_vlan_perm tinyint(1) NOT NULL, create_vlan_perm tinyint(1) NOT NULL, update_vlan_perm tinyint(1) NOT NULL, delete_vlan_perm tinyint(1) NOT NULL, read_device_config_perm tinyint(1) NOT NULL, write_device_config_perm tinyint(1) NOT NULL, administrate_cm_perm tinyint(1) NOT NULL, read_as_perm tinyint(1) NOT NULL, create_as_perm tinyint(1) NOT NULL, update_as_perm tinyint(1) NOT NULL, delete_as_perm tinyint(1) NOT NULL, read_line_perm tinyint(1) NOT NULL, create_line_perm tinyint(1) NOT NULL, update_line_perm tinyint(1) NOT NULL, delete_line_perm tinyint(1) NOT NULL, execute_update_dns_perm tinyint(1) NOT NULL, execute_update_snmp_perm tinyint(1) NOT NULL, execute_update_ping_perm tinyint(1) NOT NULL, password_management_perm tinyint(1) NOT NULL, manage_tags_perm tinyint(1) NOT NULL, manage_snmp_group_perm tinyint(1) NOT NULL, manage_dns_server_group_perm tinyint(1) NOT NULL, manage_dyn_dns_perm tinyint(1) NOT NULL, manage_macs_perm tinyint(1) NOT NULL, locs_ro_perm varchar(300) DEFAULT 9999 NOT NULL, locs_rw_perm varchar(300) DEFAULT 9999 NOT NULL, manage_scheduled_jobs_perm tinyint(1) NOT NULL, smtp_server_management_perm tinyint(1) DEFAULT 0 NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_group_perms:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_group_perms<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO gip_user_group_perms (group_id,clients_perm,loc_perm,cat_perm,manage_gestioip_perm, manage_user_perm, manage_sites_and_cats_perm, manage_custom_columns_perm, read_audit_perm, create_net_perm, read_net_perm, update_net_perm, delete_net_perm, create_host_perm, read_host_perm, update_host_perm, delete_host_perm, create_vlan_perm, read_vlan_perm, update_vlan_perm, delete_vlan_perm, read_device_config_perm, write_device_config_perm, administrate_cm_perm, read_as_perm, create_as_perm, update_as_perm, delete_as_perm, read_line_perm, create_line_perm, update_line_perm, delete_line_perm, execute_update_dns_perm,execute_update_snmp_perm, execute_update_ping_perm, password_management_perm, manage_tags_perm, manage_snmp_group_perm, manage_dns_server_group_perm, manage_dyn_dns_perm, manage_macs_perm, locs_ro_perm, locs_rw_perm, manage_scheduled_jobs_perm, smtp_server_management_perm) VALUES (1,9999,'','',1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9999,9999,1,1)") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_group_perms<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO gip_user_group_perms (group_id,clients_perm,loc_perm,cat_perm,manage_gestioip_perm, manage_user_perm, manage_sites_and_cats_perm, manage_custom_columns_perm, read_audit_perm, create_net_perm, read_net_perm, update_net_perm, delete_net_perm, create_host_perm, read_host_perm, update_host_perm, delete_host_perm, create_vlan_perm, read_vlan_perm, update_vlan_perm, delete_vlan_perm, read_device_config_perm, write_device_config_perm, administrate_cm_perm, read_as_perm, create_as_perm, update_as_perm, delete_as_perm, read_line_perm, create_line_perm, update_line_perm, delete_line_perm, execute_update_dns_perm,execute_update_snmp_perm, execute_update_ping_perm, password_management_perm, manage_tags_perm, manage_snmp_group_perm, manage_dns_server_group_perm, manage_dyn_dns_perm, manage_macs_perm, locs_ro_perm, locs_rw_perm, manage_scheduled_jobs_perm, smtp_server_management_perm) VALUES (2,9999,'','',0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,9999,9999,1,1)") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_group_perms<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("INSERT INTO gip_user_group_perms (group_id,clients_perm,loc_perm,cat_perm,manage_gestioip_perm, manage_user_perm, manage_sites_and_cats_perm, manage_custom_columns_perm, read_audit_perm, create_net_perm, read_net_perm, update_net_perm, delete_net_perm, create_host_perm, read_host_perm, update_host_perm, delete_host_perm, create_vlan_perm, read_vlan_perm, update_vlan_perm, delete_vlan_perm, read_device_config_perm, write_device_config_perm, administrate_cm_perm,read_as_perm, create_as_perm, update_as_perm, delete_as_perm, read_line_perm, create_line_perm, update_line_perm, delete_line_perm, execute_update_dns_perm,execute_update_snmp_perm, execute_update_ping_perm, password_management_perm, manage_tags_perm, manage_snmp_group_perm, manage_dns_server_group_perm, manage_dyn_dns_perm, manage_macs_perm, locs_ro_perm, locs_rw_perm, manage_scheduled_jobs_perm, smtp_server_management_perm) VALUES (3,9999,'','',0,0,0,0,1,0,1,0,0,0,1,0,0,0,1,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,9999,0,0,0)") or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table gip_user_group_perms<p>$DBI::errstr<p>$preferences{back_button}");



### SITE MANAGEMENT

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_site_columns ( id smallint(4) AUTO_INCREMENT, name varchar(100) NOT NULL, mandatory tinyint(1) DEFAULT 0, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_site_columns<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_site_columns<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_site_column_entries ( id mediumint(7) AUTO_INCREMENT, column_id smallint(4) NOT NULL, site_id mediumint(7) NOT NULL, entry varchar(100) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_site_column_entries<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table custom_site_column_entries<p>$DBI::errstr<p>$preferences{back_button}");

    $sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS custom_site_column_select (id mediumint(6) AUTO_INCREMENT, type varchar(1), items varchar(1000), cc_id smallint(5), PRIMARY KEY (id))")
		 or die print_end("<p>$preferences{bbdd_create_table_error}<p>table site custom_column_select:<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table site custom_colun_select:<p>$DBI::errstr<p>$preferences{back_button}");


### PASSWORD MANAGEMENT

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS master_keys ( id smallint(4) AUTO_INCREMENT, user_id smallint(4), master_key varchar(100) NOT NULL, client_id smallint(4), changed smallint(1) DEFAULT 0, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table master_keys<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table master_keys<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS device_keys ( id smallint(4) AUTO_INCREMENT, name varchar(60) NOT NULL, comment varchar(500) NOT NULL, password varchar(100) NOT NULL, host_id int(10), client_id smallint(4), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_keys<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table device_keys<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS user_passwords ( id smallint(4) AUTO_INCREMENT, password varchar(100) NOT NULL, user_id smallint(4) NOT NULL, client_id smallint(4), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 


### DYNAMIC DNS UPDATES

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS dns_user ( id smallint(4) AUTO_INCREMENT, name varchar(60) NOT NULL, password varchar(50), realm varchar(60) NOT NULL, description varchar(1500) NOT NULL, client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS dns_zone ( id smallint(4) AUTO_INCREMENT, name varchar(60) NOT NULL, dyn_dns_server varchar(500) NOT NULL, description varchar(500) NOT NULL, type varchar(4), dns_user_id smallint(4), ttl int(10), server_type varchar(12), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
        ) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
    $sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS dns_keys ( id smallint(4) AUTO_INCREMENT, name varchar(60), tsig_key varchar(150), description varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table dns_keys<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table dns_keys<p>$DBI::errstr<p>$preferences{back_button}"); 


# ACL management


	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS acl_connection_list ( id mediumint(6) AUTO_INCREMENT, acl_nr mediumint(6), purpose varchar(500), status varchar(100), source varchar(250), src_vlan varchar(10), src varchar (250), src_mask varchar (50), src_port varchar(500), dst_vlan varchar(10), destination varchar(250), dst varchar(250), dst_mask varchar (50), application_protocol varchar(100), proto_id varchar(20), icmp_type varchar(25), bidirectional varchar(1), encrypted_base_proto varchar(100), remark varchar(100), client_id smallint(4), no_acl smallint(1) DEFAULT 0, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS acl_list ( id mediumint(6) AUTO_INCREMENT, src varchar(15), src_wmask varchar(15), src_port varchar(75), src_operator varchar(5), dst varchar(15), dst_wmask varchar(15), dst_port varchar(75), dst_operator varchar(5), proto_id varchar(10), action varchar(6), icmp_type varchar(2), client_id smallint(4), con_exists smallint(1) DEFAULT 0, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS protocols ( id mediumint(6) AUTO_INCREMENT, protocol_nr mediumint(5) NOT NULL, protocol_name varchar(30) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS ports ( id mediumint(6) AUTO_INCREMENT, port_nr mediumint(5) NOT NULL, port_name varchar(30) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table user_passwords<p>$DBI::errstr<p>$preferences{back_button}"); 


	$sth = $dbh->prepare("INSERT INTO protocols (protocol_nr, protocol_name) VALUES (0, 'HOPOPT'), (1, 'ICMP'), (2, 'IGMP'), (3, 'GGP'), (4, 'IP'), (5, 'ST'), (6, 'TCP'), (7, 'CBT'), (8, 'EGP'), (9, 'IGP'), (10, 'BBN-RCC-MON'), (11, 'NVP-II'), (12, 'PUP'), (14, 'EMCON'), (15, 'XNET'), (16, 'CHAOS'), (17, 'UDP'), (18, 'MUX'), (19, 'DCN-MEAS'), (20, 'HMP'), (21, 'PRM'), (22, 'XNS-IDP'), (23, 'TRUNK-1'), (24, 'TRUNK-2'), (25, 'LEAF-1'), (26, 'LEAF-2'), (27, 'RDP'), (28, 'IRTP'), (29, 'ISO-TP4'), (30, 'NETBLT'), (31, 'MFE-NSP'), (32, 'MERIT-INP'), (33, 'DCCP'), (34, '3PC'), (35, 'IDPR'), (36, 'XTP'), (37, 'DDP'), (38, 'IDPR-CMTP'), (39, 'TP++'), (40, 'IL'), (41, 'IPv6'), (42, 'SDRP'), (43, 'IPv6-Route'), (44, 'IPv6-Frag'), (45, 'IDRP'), (46, 'RSVP'), (47, 'GRE'), (48, 'DSR'), (49, 'BNA'), (50, 'ESP'), (51, 'AH'), (52, 'I-NLSP'), (54, 'NARP'), (55, 'MOBILE'), (56, 'TLSP'), (57, 'SKIP'), (58, 'IPv6-ICMP'), (59, 'IPv6-NoNxt'), (60, 'IPv6-Opts'), (62, 'CFTP'), (64, 'SAT-EXPAK'), (65, 'KRYPTOLAN'), (66, 'RVD'), (67, 'IPPC'), (69, 'SAT-MON'), (70, 'VISA'), (71, 'IPCV'), (72, 'CPNX'), (73, 'CPHB'), (74, 'WSN'), (75, 'PVP'), (76, 'BR-SAT-MON'), (77, 'SUN-ND'), (78, 'WB-MON'), (79, 'WB-EXPAK'), (80, 'ISO-IP'), (81, 'VMTP'), (82, 'SECURE-VMTP'), (83, 'VINES'), (84, 'TTP'), (84, 'IPTM'), (85, 'NSFNET-IGP'), (86, 'DGP'), (87, 'TCF'), (88, 'EIGRP'), (89, 'OSPFIGP'), (90, 'Sprite-RPC'), (91, 'LARP'), (92, 'MTP'), (93, 'AX.25'), (94, 'IPIP'), (95, 'MICP'), (96, 'SCC-SP'), (97, 'ETHERIP'), (98, 'ENCAP'), (100, 'GMTP'), (101, 'IFMP'), (102, 'PNNI'), (103, 'PIM'), (104, 'ARIS'), (105, 'SCPS'), (106, 'QNX'), (107, 'A/N'), (108, 'IPComp'), (109, 'SNP'), (110, 'Compaq-Peer'), (111, 'IPX-in-IP'), (112, 'VRRP'), (113, 'PGM'), (115, 'L2TP'), (116, 'DDX'), (117, 'IATP'), (118, 'STP'), (119, 'SRP'), (120, 'UTI'), (121, 'SMP'), (123, 'PTP'), (124, 'ISIS over IPv4'), (125, 'FIRE'), (126, 'CRTP'), (127, 'CRUDP'), (128, 'SSCOPMCE'), (129, 'IPLT'), (130, 'SPS'), (131, 'PIPE'), (132, 'SCTP'), (133, 'FC'), (134, 'RSVP-E2E-IGNORE'), (135, 'Mobility Header'), (136, 'UDPLite'), (137, 'MPLS-in-IP'), (138, 'manet'), (139, 'HIP'), (140, 'Shim6'), (141, 'WESP'), (142, 'ROHC')"
		) or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");

	$sth = $dbh->prepare("INSERT INTO ports (port_name, port_nr) VALUES ('tcpmux', 1), ('echo', 7), ('discard', 9), ('systat', 11), ('daytime', 13), ('netstat', 15), ('qotd', 17), ('msp', 18), ('chargen', 19), ('ftp-data', 20), ('ftp', 21), ('fsp', 21), ('ssh', 22), ('telnet', 23), ('smtp', 25), ('time', 37), ('rlp', 39), ('nameserver', 42), ('whois', 43), ('tacacs', 49), ('re-mail-ck', 50), ('domain', 53), ('mtp', 57), ('tacacs-ds', 65), ('bootps', 67), ('bootpc', 68), ('tftp', 69), ('gopher', 70), ('rje', 77), ('finger', 79), ('http', 80), ('link', 87), ('kerberos', 88), ('supdup', 95), ('hostnames', 101), ('iso-tsap', 102), ('acr-nema', 104), ('csnet-ns', 105), ('rtelnet', 107), ('pop2', 109), ('pop3', 110), ('sunrpc', 111), ('auth', 113), ('sftp', 115), ('uucp-path', 117), ('nntp', 119), ('ntp', 123), ('pwdgen', 129), ('loc-srv', 135), ('netbios-ns', 137), ('netbios-dgm', 138), ('netbios-ssn', 139), ('imap2', 143), ('snmp', 161), ('snmp-trap', 162), ('cmip-man', 163), ('cmip-agent', 164), ('mailq', 174), ('xdmcp', 177), ('nextstep', 178), ('bgp', 179), ('prospero', 191), ('irc', 194), ('smux', 199), ('at-rtmp', 201), ('at-nbp', 202), ('at-echo', 204), ('at-zis', 206), ('qmtp', 209), ('z3950', 210), ('ipx', 213), ('imap3', 220), ('pawserv', 345), ('zserv', 346), ('fatserv', 347), ('rpc2portmap', 369), ('codaauth2', 370), ('clearcase', 371), ('ulistserv', 372), ('ldap', 389), ('imsp', 406), ('svrloc', 427), ('https', 443), ('snpp', 444), ('microsoft-ds', 445), ('kpasswd', 464), ('urd', 465), ('saft', 487), ('isakmp', 500), ('rtsp', 554), ('nqs', 607), ('npmp-local', 610), ('npmp-gui', 611), ('hmmp-ind', 612), ('asf-rmcp', 623), ('qmqp', 628), ('ipp', 631), ('biff', 512), ('login', 513), ('who', 513), ('syslog', 514), ('printer', 515), ('talk', 517), ('ntalk', 518), ('route', 520), ('timed', 525), ('tempo', 526), ('courier', 530), ('conference', 531), ('netnews', 532), ('netwall', 533), ('gdomap', 538), ('uucp', 540), ('klogin', 543), ('kshell', 544), ('dhcpv6-client', 546), ('dhcpv6-server', 547), ('afpovertcp', 548), ('idfp', 549), ('remotefs', 556), ('nntps', 563), ('submission', 587), ('ldaps', 636), ('tinc', 655), ('silc', 706), ('kerberos-adm', 749), ('webster', 765), ('rsync', 873), ('ftps-data', 989), ('ftps', 990), ('telnets', 992), ('imaps', 993), ('ircs', 994), ('pop3s', 995), ('socks', 1080), ('proofd', 1093), ('rootd', 1094), ('openvpn', 1194), ('rmiregistry', 1099), ('kazaa', 1214), ('nessus', 1241), ('lotusnote', 1352), ('ms-sql-s', 1433), ('ms-sql-m', 1434), ('ingreslock', 1524), ('prospero-np', 1525), ('datametrics', 1645), ('sa-msg-port', 1646), ('kermit', 1649), ('groupwise', 1677), ('l2f', 1701), ('radius', 1812), ('radius-acct', 1813), ('msnp', 1863), ('unix-status', 1957), ('log-server', 1958), ('remoteping', 1959), ('cisco-sccp', 2000), ('search', 2010), ('pipe-server', 2010), ('nfs', 2049), ('gnunet', 2086), ('rtcm-sc104', 2101), ('gsigatekeeper', 2119), ('gris', 2135), ('cvspserver', 2401), ('venus', 2430), ('venus-se', 2431), ('codasrv', 2432), ('codasrv-se', 2433), ('mon', 2583), ('dict', 2628), ('f5-globalsite', 2792), ('gsiftp', 2811), ('gpsd', 2947), ('gds-db', 3050), ('icpv2', 3130), ('iscsi-target', 3260), ('mysql', 3306), ('nut', 3493), ('distcc', 3632), ('daap', 3689), ('svn', 3690), ('suucp', 4031), ('sysrqd', 4094), ('sieve', 4190), ('epmd', 4369), ('remctl', 4373), ('f5-iquery', 4353), ('ipsec-nat-t', 4500), ('iax', 4569), ('mtn', 4691), ('radmin-port', 4899), ('rfe', 5002), ('mmcc', 5050), ('sip', 5060), ('sip-tls', 5061), ('aol', 5190), ('xmpp-client', 5222), ('xmpp-server', 5269), ('cfengine', 5308), ('mdns', 5353), ('postgresql', 5432), ('freeciv', 5556), ('amqps',   5671), ('amqp', 5672), ('ggz', 5688), ('x11', 6000), ('x11-1', 6001), ('x11-2', 6002), ('x11-3', 6003), ('x11-4', 6004), ('x11-5', 6005), ('x11-6', 6006), ('x11-7', 6007), ('gnutella-svc', 6346), ('gnutella-rtr', 6347), ('sge-qmaster', 6444), ('sge-execd', 6445), ('mysql-proxy', 6446), ('afs3-fileserver', 7000), ('afs3-callback', 7001), ('afs3-prserver', 7002), ('afs3-vlserver', 7003), ('afs3-kaserver', 7004), ('afs3-volser', 7005), ('afs3-errors', 7006), ('afs3-bos', 7007), ('afs3-update', 7008), ('afs3-rmtsys', 7009), ('font-service', 7100), ('http-alt', 8080), ('bacula-dir', 9101), ('bacula-fd', 9102), ('bacula-sd', 9103), ('xmms2', 9667), ('nbd', 10809), ('zabbix-agent', 10050), ('zabbix-trapper', 10051), ('amanda', 10080), ('dicom', 11112), ('hkp', 11371), ('bprd', 13720), ('bpdbm', 13721), ('bpjava-msvc', 13722), ('vnetd', 13724), ('bpcd', 13782), ('vopied', 13783), ('db-lsp', 17500), ('dcap', 22125), ('gsidcap', 22128), ('wnn6', 22273), ('nbp', 2), ('kerberos4', 750), ('kerberos-master', 751), ('passwd-server', 752), ('krb-prop', 754), ('krbupdate', 760), ('swat', 901), ('kpop', 1109), ('knetd', 2053), ('zephyr-srv', 2102), ('zephyr-clt', 2103), ('zephyr-hm', 2104), ('eklogin', 2105), ('kx', 2111), ('iprop', 2121), ('supfilesrv', 871), ('supfiledbg', 1127), ('linuxconf', 98), ('poppassd', 106), ('moira-db', 775), ('moira-update', 777), ('moira-ureg', 779), ('spamd', 783), ('omirr', 808), ('customs', 1001), ('skkserv', 1178), ('predict', 1210), ('rmtcfg', 1236), ('wipld', 1300), ('xtel', 1313), ('xtelw', 1314), ('support', 1529), ('cfinger', 2003), ('frox', 2121), ('ninstall', 2150), ('zebrasrv', 2600), ('zebra', 2601), ('ripd', 2602), ('ripngd', 2603), ('ospfd', 2604), ('bgpd', 2605), ('ospf6d', 2606), ('ospfapi', 2607), ('isisd', 2608), ('afbackup', 2988), ('afmbackup', 2989), ('xtell', 4224), ('fax', 4557), ('hylafax', 4559), ('distmp3', 4600), ('munin', 4949), ('enbd-cstatd', 5051), ('enbd-sstatd', 5052), ('pcrd', 5151), ('noclog', 5354), ('hostmon', 5355), ('rplay', 5555), ('nrpe', 5666), ('nsca', 5667), ('mrtd', 5674), ('bgpsim', 5675), ('canna', 5680), ('syslog-tls', 6514), ('sane-port', 6566), ('ircd', 6667), ('zope-ftp', 8021), ('tproxy', 8081), ('omniorb', 8088), ('clc-build-daemon', 8990), ('xinetd', 9098), ('mandelspawn', 9359), ('git', 9418), ('zope', 9673), ('webmin', 10000), ('kamanda', 10081), ('amandaidx', 10082), ('amidxtape', 10083), ('smsqp', 11201), ('xpilot', 15345), ('sgi-cmsd', 17001), ('sgi-crsd', 17002), ('sgi-gcd', 17003), ('sgi-cad', 17004), ('isdnlog', 20011), ('vboxd', 20012), ('binkp', 24554), ('asp', 27374), ('csync2', 30865), ('dircproxy', 57000), ('tfido', 60177), ('fido', 60179)"
		) or die print_end("<p>$preferences{bbdd_insert_cat_error}<p>$DBI::errstr");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>$DBI::errstr<p>");



# TAGs

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS tag (id mediumint(6) AUTO_INCREMENT, name varchar(20), color varchar(8), description varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS tag_entries_network (id mediumint(6) AUTO_INCREMENT, tag_id mediumint(6), net_id mediumint(6), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_networks<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_networks<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS tag_entries_host (id mediumint(6) AUTO_INCREMENT, tag_id mediumint(6), host_id mediumint(6), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_hosts<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_hosts<p>$DBI::errstr<p>$preferences{back_button}"); 


# Scan Zones

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS scan_zone_entries_network (id mediumint(6) AUTO_INCREMENT, zone_id mediumint(6), net_id mediumint(6), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scan_zone_entries_networks<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scan_zone_entries_networks<p>$DBI::errstr<p>$preferences{back_button}"); 


# SNMP groups

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS snmp_group (id mediumint(6) AUTO_INCREMENT, name varchar(250), snmp_version varchar(1), port mediumint(5), community varchar(250), user_name varchar(250), sec_level varchar(10), auth_algorithm varchar (4), auth_password varchar (250), priv_algorithm varchar(4), priv_password varchar(250), comment varchar(500), client_id smallint(4), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_hosts<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table tag_entries_hosts<p>$DBI::errstr<p>$preferences{back_button}"); 


# DNS server groups

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS dns_server_group (id mediumint(6) AUTO_INCREMENT, name varchar(20), dns_server1 varchar(50), dns_server2 varchar(50), dns_server3 varchar(50), description varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table dns_server_group<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table dns_server_group<p>$DBI::errstr<p>$preferences{back_button}"); 


# Scheduled Jobs

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS scheduled_jobs (id mediumint(6) AUTO_INCREMENT, name varchar(100), type tinyint(3), start_date varchar(20), end_date varchar(20), run_once tinyint(1), status tinyint(1), comment varchar(500), arguments varchar(700), cron_time varchar(50), next_run varchar(20), repeat_interval varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scheduled_jobs<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scheduled_jobs<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS scheduled_job_status (id mediumint(6) AUTO_INCREMENT, job_id mediumint(8), status smallint(2), start_time bigint(20), end_time bigint(20), exit_message varchar(1500), log_file varchar(300), PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scheduled_job_status<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table scheduled_job_status<p>$DBI::errstr<p>$preferences{back_button}"); 


# SMTP servers

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS smtp_server (id mediumint(6) AUTO_INCREMENT, name varchar(100), username varchar(100), password varchar(50), default_from varchar(100), security varchar(10), port smallint(5), timeout smallint(3), comment varchar(500), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table smtp_server<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table smtp_server<p>$DBI::errstr<p>$preferences{back_button}"); 


# LDAP servers

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS ldap_group (id mediumint(6) AUTO_INCREMENT, name varchar(100), dn varchar(100), user_group_id smallint(4), ldap_server_id smallint(4), comment varchar(500), group_attrib_is_dn smallint(1), enabled smallint(1), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_group<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_group<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS ldap_server (id mediumint(6) AUTO_INCREMENT, name varchar(100), server varchar(100), type varchar(25), protocol varchar(5), port smallint(5), bind_dn varchar(150), bind_password varchar(150), base_dn varchar(150), user_attribute varchar(150), user_filter varchar(150), comment varchar(500), enabled smallint(1), client_id smallint(4) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_server<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_server<p>$DBI::errstr<p>$preferences{back_button}"); 

	$sth = $dbh->prepare("CREATE TABLE IF NOT EXISTS ldap_user_groups (id mediumint(6) AUTO_INCREMENT, user varchar(100), user_group_id varchar(100), last_change varchar(250) NOT NULL, PRIMARY KEY (id))"
		) or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_user_groups<p>$DBI::errstr<p>$preferences{back_button}");
	$sth->execute() or die print_end("<p>$preferences{bbdd_create_table_error}<p>table ldap_user_groups<p>$DBI::errstr<p>$preferences{back_button}"); 

    $sth->finish();
    $dbh->disconnect;


	print "<span class=\"OKText\">OK</span><p><br>";
}


sub Aufbereiter {
        my ($datenskalar, $listeneintrag, $name, $daten);
        my @datenliste;
        my %datenhash;
        if ($_[0]) {
           $datenskalar=$_[0];
        @datenliste = split (/[&;]/, $datenskalar);
        foreach $listeneintrag (@datenliste) {
        $listeneintrag =~ s/\+/ /go;
        ($name, $daten) = split ( /=/, $listeneintrag);
        $name =~ s/\%(..)/pack("c",hex($1))/ge;
        $daten  =~ s/\%(..)/pack("c",hex($1))/ge;
        $datenhash{$name} = $daten;
        }

        }
        return %datenhash;
}

sub mysql_verbindung {
    my($bbdd_host,$ddbb_port,$sid,$user,$password)=@_;
    my $dbh = DBI->connect("dbi:mysql:host=$bbdd_host;database=$sid;port=$bbdd_port", $bbdd_admin, $bbdd_admin_pass, {
                PrintError => 1,
                RaiseError => 0
        } ) or die print_end("$preferences{bbdd_connect_error}<p>$DBI::errstr<p>$preferences{back_button}");;
    return $dbh;
}

sub print_error {
        my ( $error ) = @_;
        print "<p>$error<p>\n";
        print_end();
}
