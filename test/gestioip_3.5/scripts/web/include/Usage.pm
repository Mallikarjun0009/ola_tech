### Network usage column
use strict;
package Usage;

sub update_net_usage_cc_column {
    my ($client_id, $ip_version, $red_num, $BM, $no_rootnet, $gip, $gip_config_file) = @_;

    my ($ip_total, $ip_ocu, $free) = get_red_usage("$client_id", "$ip_version", "$red_num", "$BM", $gip, "$gip_config_file");
    my $cc_id_usage = get_custom_column_id_from_name("$client_id", "usage", $gip, "$gip_config_file") || "";
    my $cc_usage_entry = "$ip_total,$ip_ocu,$free" || "";
    update_or_insert_custom_column_value_red("$client_id", "$cc_id_usage", "$red_num", "$cc_usage_entry", $gip, "$gip_config_file") if $cc_id_usage && $cc_usage_entry;
}


sub get_red_usage {
    my ( $client_id, $ip_version, $red_num, $BM, $gip, $gip_config_file) = @_;

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



    my $ip_ocu=count_host_entries("$client_id","$red_num", $gip, "$gip_config_file") || 0;
    my $free=$ip_total-$ip_ocu;

    return ($ip_total, $ip_ocu, $free);
}


sub get_custom_column_id_from_name {
    my ( $client_id, $name, $gip, $gip_config_file ) = @_;

    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qname = $dbh->quote( $name );
    my $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qname
                        ") or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    my $id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $id;
}


sub update_or_insert_custom_column_value_red {
    my ( $client_id, $cc_id, $net_id, $entry, $gip, $gip_config_file ) = @_;

    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qcc_id = $dbh->quote( $cc_id );
    my $qnet_id = $dbh->quote( $net_id );
    my $qentry = $dbh->quote( $entry );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT entry FROM custom_net_column_entries WHERE cc_id=$qcc_id AND net_id=$qnet_id");
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    my $entry_found = $sth->fetchrow_array;

    if ( $entry_found ) {
        $sth = $dbh->prepare("UPDATE custom_net_column_entries SET entry=$qentry WHERE cc_id=$qcc_id AND net_id=$qnet_id") or die "Can not execute statement: $dbh->errstr";
    } else {
            $sth = $dbh->prepare("INSERT INTO custom_net_column_entries (cc_id,net_id,entry,client_id) VALUES ($qcc_id,$qnet_id,$qentry,$qclient_id)") or die "Can not execute statement: $dbh->errstr";
    }
    $sth->execute() or die "Can not execute statement: $dbh->errstr";

    $sth->finish();
    $dbh->disconnect;
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


sub count_host_entries {
    my ( $client_id, $red_num, $gip, $gip_config_file ) = @_;
    my $count_host_entries;
    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qred_num = $dbh->quote( $red_num );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT COUNT(*) FROM host WHERE red_num=$qred_num AND hostname != 'NULL' AND hostname != '' AND client_id = $qclient_id");
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    $count_host_entries = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $count_host_entries;
}


sub get_last_custom_column_id {
    my ( $client_id, $gip, $gip_config_file ) = @_;
    my $cc_id;
    my $dbh = $gip->_mysql_connection("$gip_config_file");
	my $sth = $dbh->prepare("SELECT id FROM custom_net_columns ORDER BY (id+0) desc
					") or die "Can not execute statement: $dbh->errstr";
	$sth->execute() or die "Can not execute statement: $dbh->errstr";
	$cc_id = $sth->fetchrow_array;
	$sth->finish();
	$dbh->disconnect;
	return $cc_id;
}


sub insert_custom_column {
    my ( $client_id, $id, $custom_column,$column_type_id, $gip, $gip_config_file ) = @_;

    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qcolumn_type_id = $dbh->quote( $column_type_id );
    my $qcustom_column = $dbh->quote( $custom_column );
    my $qid = $dbh->quote( $id );
    my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("INSERT INTO custom_net_columns (id,name,client_id,column_type_id) VALUES ($qid,$qcustom_column,$qclient_id,$qcolumn_type_id)");
	$sth->execute() or die "Can not execute statement: $dbh->errstr";
	$sth->finish();
	$dbh->disconnect;
}


sub get_clients {
    my ( $client_id, $gip, $gip_config_file ) = @_;
    my @values;
    my $ip_ref;
    my $dbh = $gip->_mysql_connection("$gip_config_file");
	my $sth = $dbh->prepare("SELECT id,client FROM clients ORDER BY client") or die "Can not execute statement: $dbh->errstr";
	$sth->execute() or die "Can not execute statement: $dbh->errstr";
	while ( $ip_ref = $sth->fetchrow_arrayref ) {
		push @values, [ @$ip_ref ];
	}
	$dbh->disconnect;
	return @values;
}


sub get_redes_hash {
    my ( $client_id,$ip_version,$return_int,$client_only, $gip, $gip_config_file ) = @_;
    my $ip_ref;
    $ip_version="" if ! $ip_version;
    $return_int="" if ! $return_int;
    my %values_redes;
    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qclient_id = $dbh->quote( $client_id );

    my $client_expr="";
    $client_expr="AND n.client_id=$qclient_id" if $client_only;

    my $ip_version_expr="";
    $ip_version_expr="AND n.ip_version='$ip_version'" if $ip_version;

    my $sth = $dbh->prepare("SELECT n.red_num, n.red, n.BM, n.descr, l.loc, n.vigilada, n.comentario, c.cat, n.ip_version, INET_ATON(n.red), n.rootnet, n.client_id FROM net n, categorias_net c, locations l WHERE c.id = n.categoria AND l.id = n.loc $ip_version_expr $client_expr");
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
        while ( $ip_ref = $sth->fetchrow_hashref ) {
            my $red_num = $ip_ref->{'red_num'} || "";
            my $red = $ip_ref->{'red'} || "";
            my $BM = $ip_ref->{'BM'};
            my $descr = $ip_ref->{'descr'};
            my $loc = $ip_ref->{'loc'} || "";
            my $cat = $ip_ref->{'cat'} || "";
            my $vigilada = $ip_ref->{'vigilada'} || "";
            my $comentario = $ip_ref->{'comentario'} || "";
            my $ip_version = $ip_ref->{'ip_version'} || "";
            my $red_int;
            if ( ! $return_int ) {
                $red_int="";
            } else {
                if ( $ip_version eq "v4" ) {
                    $red_int=$ip_ref->{'INET_ATON(n.red)'};
                } else {
                    # macht die sache langsam ....
                    $red_int = $gip->ip_to_int("$client_id",$red,"$ip_version");
                }
            }
            my $rootnet=$ip_ref->{'rootnet'};
            my $client_id=$ip_ref->{'client_id'};

            push @{$values_redes{$red_num}},"$red","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$client_id";
        }

        $dbh->disconnect;
        return \%values_redes;
}


sub get_custom_column_ids_from_name {
    my ($client_id, $column_name, $gip, $gip_config_file ) = @_;
    my @values;
    my $ip_ref;
    my $dbh = $gip->_mysql_connection("$gip_config_file");
    my $qcolumn_name = $dbh->quote( $column_name );
    my $sth;
    $sth = $dbh->prepare("SELECT id FROM custom_net_columns WHERE name=$qcolumn_name") or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values, [ @$ip_ref ];
    }
    $dbh->disconnect;
    return @values;
}


1;
