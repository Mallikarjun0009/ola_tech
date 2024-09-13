# Helper function for the GestioIP discovery scripts

# v1.1 20210416

package Gipfuncs;

use strict;
use Net::SMTP;
use POSIX qw(strftime);
use Time::Local;
use LWP::UserAgent;
use HTTP::Request::Common;
use Net::IP;
use Net::IP qw(:PROC);
use XML::LibXML;
use XML::LibXML::NodeList;
use Data::Dumper;


sub send_mail {
	my %args = @_;

    my $mail_from=$args{mail_from};
	#"user\@domain.net";
    my $mail_to=$args{mail_to} || "";
    my $subject=$args{'subject'} || "";
    my $server=$args{'smtp_server'} || "";
    my $smtp_server_values=$args{'smtp_server_values'};
    print main::LOG "send_mail SMTP_SERVER: $smtp_server_values\n" if $main::debug && fileno main::LOG;
    my $message=$args{'smtp_message'} || "";
    my $log=$args{'log'} || "";
    my $changes_only=$args{'changes_only'} || "";

    if ( ! $smtp_server_values ) {
        print STDERR "WARNING: CAN NOT SEND MAIL: No SMTP server values\n";
        return;
    }
	my @smtp_server_values = @$smtp_server_values;

	my $user = $smtp_server_values[0]->[2] || "";
	my $pass = $smtp_server_values[0]->[3] || "";
	my $security = $smtp_server_values[0]->[5] || "";
	my $port = $smtp_server_values[0]->[6] || "";
	my $timeout = $smtp_server_values[0]->[7] || "";


    print main::LOG "MAIL VALS: $smtp_server_values - $smtp_server_values[0] - $smtp_server_values[0]->[0] - $user - $port - $timeout - $mail_to - $mail_to->[0]\n" if $main::debug && fileno main::LOG;

	my $error = "";

    my @months = qw( Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec );
	my @days = qw(Sun Mon Tue Wed Thu Fri Sat Sun);
    my $zone_num = strftime("%z", localtime());
    my $zone_string = strftime("%Z", localtime());

    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime();
	$year = $year + 1900;
   	my $mail_date = "$days[$wday], $mday $months[$mon] $year $hour:$min:$sec $zone_num ($zone_string)";

	my @log;
    $log =~ /^(.*)$/;
    $log = $1;
	if ( $log =~ /,/ ) {
		@log = split(",", $log);
	} else {
		push @log, $log if $log;
	}

	if ( $log ) {
        my $script_name_message = "";
        my $execution_time_message = "";
		foreach my $log_mail ( @log ) {
			open (LOG_MAIL,"<$log_mail") or $error = "can not open log file: $!\n";
			while (<LOG_MAIL>) {
                if ( $changes_only ) {
                    if ( $_ =~ /###/ ) {
                        $script_name_message = $_ if $log !~ /discover_network/;
                        next;
                    }
                    if ( $_ =~ /Execution time/i ) {
                        $execution_time_message = $_;
                        next;
                    }
                    if ( $_ !~ /added|updated|deleted|ERROR|EXECUTING|discovery|Execution time/i ) {
                        next;
                    }
                    if ( $_ =~ /Network discovery -|VLAN discovery -|Host discovery DNS -|Host discovery SNMP -/i ) {
                        $_ .= "\n";
                    }
                }
                $message .= $_;
			}
			close LOG_MAIL;
		}
        $message = $script_name_message . "\n" . $message if $script_name_message;
        if ( $changes_only && $message !~ /added|updated|deleted/i ) {
            $message .= "\nNo changes\n" if $log !~ /discover_network/;
        }
        $message .= "\n" . $execution_time_message if $execution_time_message;
	}

    $message = "\n$message";

	open (LOG_MAIL,">>$log") or $error = "can not open log file: $!\n";
	*STDERR = *LOG_MAIL;

	foreach my $to ( @$mail_to ) {

        print STDERR "SEND MAIL: $to - $server - $port - $timeout - $user\n" if $main::debug;
        $server =~ /^([\w.\-_\/]{0,100})$/;
        $server = $1;
        if ( ! $server ) {
            print STDERR "SEND MAIL ERROR: can not untaint smtp server: $server\n";
        }

		my $mailer = "";
        eval {
			$mailer = new Net::SMTP(  
				$server,  
				Hello	=>      'localhost',
				Port	=>      $port,  
				Timeout	=>      $timeout,
				Debug	=>      $main::debug,
		#		SSL		=>		1,
			);
		};
		if($@) {
			exit_error("Can not connect to $server: $@", "$main::gip_job_status_id", 4);
		}

		if ( $security eq "starttls" ) {
			$mailer->starttls();
        }
		if ( $user ) {
			$mailer->auth($user,$pass) or $error = $mailer->message();
		}
		$mailer->mail($mail_from) or $error .= $mailer->message();  
		$mailer->to($to) or $error .= $mailer->message();  
		$mailer->data() or $error .= $mailer->message();  
		$mailer->datasend('Date: ' . $mail_date) or $error .= $mailer->message();
		$mailer->datasend("\n") or $error .= $mailer->message();
		$mailer->datasend('Subject: ' . $subject) or $error .= $mailer->message();
		$mailer->datasend("\n") or $error .= $mailer->message();
		$mailer->datasend('From: ' . $mail_from) or $error .= $mailer->message();
		$mailer->datasend("\n") or $error .= $mailer->message();
		$mailer->datasend('To: ' . $to) or $error .= $mailer->message();
		$mailer->datasend("\n") or $error .= $mailer->message();
		$mailer->datasend($message) or $error .= $mailer->message();
		$mailer->dataend or $error .= $mailer->message();  
		$mailer->quit or $error .= $mailer->message(); 

        print STDERR "SEND MAIL ERROR: $error\n" if $main::debug && $error;

		sleep 1;
	} 

	close LOG_MAIL;
	*STDERR = *STDOUT;

	return $error;
}

sub get_smtp_server_by_name {
    my ( $name ) = @_;

    my @values;
    my $ip_ref;
    if ( ! $main::create_csv ) {
		my $dbh = ::mysql_connection() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		my $qname = $dbh->quote( $name );
		my $sth = $dbh->prepare("SELECT id, name, username, password, default_from, security, port, timeout, comment, client_id FROM smtp_server WHERE name=$qname") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		$sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		while ( $ip_ref = $sth->fetchrow_arrayref ) {
			push @values, [ @$ip_ref ];
		}
		$sth->finish();
		$dbh->disconnect;

	} else {
        my $path = '/readSMTPServerResult/SMTPServer';
        my $content = "request_type=readSMTPServer&client_name=$main::client&name=$name";
        my @query_values = ("id", "name", "username", "password", "default_from", "security", "port", "timeout", "comment", "client_id");
        @values = make_call_array("$path", "$content", \@query_values);
    }

    print main::LOG "get_smtp_server_by_name: " . Dumper(\@values) . "\n" if $main::debug;

    return @values;
}

sub create_log_file {
	my ( $client, $logfile_name, $base_dir, $log_dir, $script ) = @_;

	if ( ! $log_dir ) {
		$log_dir = $base_dir . '/var/log';
		if ( ! -d $log_dir ) {
			$log_dir = "/usr/share/gestioip/var/log";
		}
	}
	if ( ! -d $log_dir ) {
		::exit_error("Log directory not found $log_dir", "", "");
	}
	if ( ! -w $log_dir ) {
		::exit_error("Log directory not writable $log_dir", "", "");
	}

    my ($s, $mm, $h, $d, $m, $y) = (localtime) [0,1,2,3,4,5];
	$m++;
	$y+=1900;
	if ( $d =~ /^\d$/ ) { $d = "0$d"; }
	if ( $s =~ /^\d$/ ) { $s = "0$s"; }
	if ( $m =~ /^\d$/ ) { $m = "0$m"; }
	if ( $mm =~ /^\d$/ ) { $mm = "0$mm"; }

	my $log_date="$y$m$d$h$mm$s";
	my $datetime = "$y-$m-$d $h:$mm:$s";

	if ( $logfile_name ) {
		$logfile_name =~ s/\s/_/g;
		$logfile_name =~ s/\//_/g;
		$logfile_name =~ s/_+/_/g;
	} else {
		$logfile_name = $log_date . "_" . $client . "_" . $script . ".log";
	}

	my $log=$log_dir . "/" . $logfile_name;

	return ($log, $datetime);
}


sub insert_tag_for_object {
	my ( $tag_id, $object_id, $object ) = @_;

	my ($table, $col_name);
	if ( $object eq "network" ) {
		$table = "tag_entries_network";
		$col_name = "net_id";
	} elsif ( $object eq "host" ) {
		$table = "tag_entries_host";
		$col_name = "host_id";
	}

	my @values;
	my $ip_ref;
	my $dbh = ::mysql_connection() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
	my $qtag_id = $dbh->quote( $tag_id );
	my $qobject_id = $dbh->quote( $object_id );
	my $qcol_name = $dbh->quote( $col_name );
	my $sth = $dbh->prepare("INSERT INTO $table (tag_id, $col_name) VALUES ($qtag_id, $qobject_id)") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
	$sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
	$sth->finish();
	$dbh->disconnect;
}


sub get_scheduled_job_hash {
    my ( $gip_job_id, $key ) = @_;

    my %values;
    my $ip_ref;
    $key = "id" if ! $key;
	if ( ! $main::create_csv ) {
		my $dbh = ::mysql_connection() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		my $qgip_job_id = $dbh->quote( $gip_job_id );
		my $sth = $dbh->prepare("SELECT id, name, type, start_date, end_date, run_once, status, comment, arguments, cron_time, next_run, repeat_interval, client_id FROM scheduled_jobs WHERE id=$qgip_job_id ORDER BY id"
			) or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		$sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		while ( $ip_ref = $sth->fetchrow_hashref ) {
			my $id = $ip_ref->{id};
			my $name = $ip_ref->{name};
			my $type = $ip_ref->{type};
			my $start_date = $ip_ref->{start_date};
			my $end_date = $ip_ref->{end_date};
			my $run_once = $ip_ref->{run_once};
			my $status = $ip_ref->{status};
			my $comment = $ip_ref->{comment};
			my $arguments = $ip_ref->{arguments};
			my $cron_time = $ip_ref->{cron_time};
			my $next_run = $ip_ref->{next_run};
			my $repeat_interval = $ip_ref->{repeat_interval};
			my $client_id = $ip_ref->{client_id};
			if ( $key eq "id" ) {
				push @{$values{$id}},"$name", "$start_date","$end_date", "$run_once", "$status", "$comment", "$arguments", "$cron_time", "$next_run", "$repeat_interval", "$type", "$client_id", "$end_date";
			} elsif ( $key eq "name" ) {
				push @{$values{$name}},"$id", "$start_date","$end_date", "$run_once", "$status", "$comment", "$arguments", "$cron_time", "$next_run", "$repeat_interval", "$type", "$client_id", "$end_date";
			}
		}
		$sth->finish();
		$dbh->disconnect;

		return \%values;

	} else {
		my $path = '/Jobs/Job';
		my $content = "request_type=listJobs&client_name=$main::client";
		my @values = ("name", "start_date", "end_date", "run_once", "status", "comment", "arguments", "cron_time", "next_run", "repeat_interval", "type", "client_id", "end_date");

		my $values = Gipfuncs::make_call_hash("$path", "$content", \@values, "name");

		return $values;
	}

}

sub check_start_date {
    my ( $gip_job_id ) = @_;

	my $job_hash = get_scheduled_job_hash("$gip_job_id", "id", $main::gip_job_status_id);

	my $start_time = $job_hash->{$gip_job_id}[1] || "";

	if ( $start_time !~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/ ) {
		print "start_time: WRONG FORMAT\n";
		exit 1;
	}

    $start_time =~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;
    my $st_day = $1;
    my $st_month = $2;
    my $st_year = $3;
    my $st_hour = $4;
    my $st_minute = $5;
    my $st_sec = "00";
    my $st_epoch = timelocal($st_sec,$st_minute,$st_hour,$st_day,$st_month-1,$st_year);

    my $now_epoch = time();
    my $now_time = strftime "%d/%m/%Y %H:%M", localtime($now_epoch);

	if ( $now_epoch < $st_epoch ) {
		return "TOO_EARLY";
	} else {
		return;
	}

}

sub check_end_date {
    my ( $gip_job_id ) = @_;

	my $job_hash = get_scheduled_job_hash("$gip_job_id", "id", $main::gip_job_status_id);

	my $end_time = $job_hash->{$gip_job_id}[2] || "";

    return if ! $end_time;

	if ( $end_time !~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/ ) {
		print "end_time: WRONG FORMAT\n";
		exit 1;
	}

    $end_time =~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;
    my $et_day = $1;
    my $et_month = $2;
    my $et_year = $3;
    my $et_hour = $4;
    my $et_minute = $5;
    my $et_sec = "00";
    my $et_epoch = timelocal($et_sec,$et_minute,$et_hour,$et_day,$et_month-1,$et_year);

    my $now_epoch = time();
    my $now_time = strftime "%d/%m/%Y %H:%M", localtime($now_epoch);

	if ( $now_epoch > $et_epoch ) {
		return "TOO_LATE";
	} else {
		return;
	}
}

sub check_disabled {
    my ( $gip_job_id ) = @_;

	my $job_hash = get_scheduled_job_hash("$gip_job_id", "id", "");

	my $status = $job_hash->{$gip_job_id}[4] || "";

	return $status;

}

sub get_job_name {
    my ( $gip_job_id ) = @_;

	my $job_hash = get_scheduled_job_hash("$gip_job_id", "id", "");

	my $name = $job_hash->{$gip_job_id}[0] || "";

	return $name;
}



sub make_call_name_id_hash {
    my ($path, $content) = @_;
   
	print "make_call_name_id_hash: $path - $content\n" if $main::debug;
	print main::LOG "make_call_name_id_hash: $path - $content\n" if $main::debug;

    my %hash;
   
    my $error;
    my $response = make_request("$content");

    my @result;

    if ($response->is_success) {

        my $con = $response->content;

        my $dom = XML::LibXML->load_xml(string => "$con");

        foreach my $fn ($dom->findnodes($path)) {
			my $id = $fn->findvalue('./id');
			my $name = $fn->findvalue('./name');
			$hash{$name} = $id;
        }
    } else {
        $error= $response->status_line;
        print "ERROR make_call_name_id_hash: $error\n";
        print main::LOG "ERROR make_call_name_id_hash: $error\n";
        return;
    }

    return \%hash;
}

sub make_call_hash {
    my ($path, $content, $values, $key) = @_;

    my $this_function = (caller(1))[3];
    print "make_call_hash: $this_function - $path, $content, $values, $key\n" if $main::debug;
    print main::LOG "make_call_hash: $this_function - $path, $content, $values, $key\n" if $main::debug;
  
    my %hash;
  
    my $error;
    my $response = make_request("$content");

	my %update_types = (
		man => 1,
		dns => 2,
		ocs => 3,
		NULL => "-1",
	);

    my @result;

    if ($response->is_success) {

        my $con = $response->content;

        my $dom = XML::LibXML->load_xml(string => "$con");

        foreach my $fn ($dom->findnodes($path)) {
			my $name_name = $fn->findvalue("./name") || "";

			my $name = $fn->findvalue("./hostname") || "";
			my $id = $fn->findvalue("./id") || "";
			my $ip = $fn->findvalue("./IP") || "";
            my $ip_version = $fn->findvalue("./ip_version") || "";
            my $ip_int = "";
            $ip_int = ip_to_int("$ip","$ip_version") if $ip && $ip_version;
# push @{$values_redes{$red}},"$red_num","$BM","$descr","$loc","$cat","$vigilada","$comentario","$ip_version","$red_int","$rootnet","$loc_id","$dyn_dns_updates";

			foreach my $qval ( @$values ) {
				my $val = "";
				if ( $qval eq "ip_int" ) {
					$val = $ip_int;
				} elsif ( $qval eq "rootnet0" ) {
					$val = 0;
				} elsif ( $qval eq "rootnet1" ) {
					$val = 1;
				} elsif ( $qval eq "loc_id" ) {
					my $site = $fn->findvalue("./site") || "";
					$val = $main::db_locations->{$site} if $site;
					$val = "-1" if ! $val;;
				} elsif ( $qval eq "cat_id" ) {
					my $cat = $fn->findvalue("./cat") || "";
					$val = $main::host_categories_hash->{$cat} if $cat;
					$val = "-1" if ! $val;;
				} elsif ( $qval eq "utype_id" ) {
					my $utype = $fn->findvalue("./update_type") || "";
					$val = $update_types{$utype} if $utype;
					$val = "-1" if ! $val;;
				} else {
					$val = $fn->findvalue("./$qval") || "";
				}

				if ( $key eq "hostname" ) {
					push @{$hash{$name}},"$val" if $name;
				} elsif ( $key eq "ip" ) {
					push @{$hash{$ip}},"$val" if $ip;
				} elsif ( $key eq "ip_int" ) {
					push @{$hash{$ip_int}},"$val" if $ip_int;
				} elsif ( $key eq "name" ) {
					push @{$hash{$name_name}},"$id" if $name_name;
				} else {
					push @{$hash{$id}},"$val" if $id;
				}
			}
		}
    } else {
        $error= $response->status_line;
        print "ERROR make_call_hash: $error\n";
        print main::LOG "ERROR make_call_hash: $error\n";
        return;
    }

    return \%hash;
}


sub make_call_array {
    my ($path, $content, $values) = @_;

    my $this_function = (caller(1))[3];

	print "make_call_array: $this_function - $path - $content - $values\n" if $main::debug;
	print main::LOG "make_call_array: $this_function - $path - $content - $values\n" if $main::debug;

	my %clients;
	my $client_id;

	$path =~ /^(\/.+?)\//;
    my $base_path = $1;

    my $error;
    my $response = make_request("$content");

	my @result;

	if ($response->is_success) {

		my $con = $response->content;

		my $dom = eval { XML::LibXML->load_xml(string => "$con") };
		if($@) {
			print main::LOG "ERROR PARSING XML: $@\n";
			print main::LOG "CON: $con\n" if $main::debug;
			return;
		}

        foreach my $fn ($dom->findnodes("$base_path/error")) {
            my $ret_error = $fn->findvalue('./string');
			if ( $ret_error ) {
				print main::LOG "ERROR API: make_call_arrary: $ret_error\n";
				return;
			}
        }

		my $tag = "";
		my $scanazone = "";
		my $scanptrzone = "";
		foreach my $fn ($dom->findnodes($path)) {
			my @r2;

			foreach my $val ( @$values ) {
				if ( $val !~ /\// ) {
					my $found = $fn->findvalue('./' . $val) if $val;
                    $found = "" if ! $found;
					push @r2, "$found" ;
				} else {
                    if ( $val eq "customColumns/Tags" ) {
                        my @tag_arr;
                        foreach ( $fn->findnodes('./customColumns/Tags/Tag') ) {
                            $tag = $_->to_literal();
                            print main::LOG "FOUND TAG: $tag\n" if $main::debug;
							push @r2, "$tag";
                        }
                    }
                    if ( $val =~ /ScanAZones/ ) {
                        my @scanazones;
                        foreach ( $fn->findnodes('./' . $val) ) {
                            $scanazone = $_->to_literal();
                            $scanazone = "" if ! $scanazone;
                            print main::LOG "FOUND SCANAZONE: $scanazone\n" if $main::debug;
							push @r2, "$scanazone";
                        }
                    }
                    if ( $val =~ /ScanPTRZones/ ) {
                        foreach ( $fn->findnodes('./' . $val) ) {
                            $scanptrzone = $_->to_literal();
                            $scanptrzone = "" if ! $scanptrzone;
                            print main::LOG "FOUND SCANPTRZONE: $scanptrzone\n" if $main::debug;
							push @r2, "$scanptrzone";
                        }
                    }
				}
			}
			push @result, \@r2;
		}
    } else {
        $error= $response->status_line;
		print main::LOG  "MAKE_CALL_ARRAY: FAILED: $error\n";
        return;
	}

	return @result;
}


sub make_call_value {
    my ($path, $content, $value) = @_;

    my $this_function = (caller(1))[3];
    print "make_call_value: $this_function - $path - $content - $value\n" if $main::debug;
    print main::LOG "make_call_value:  $path - $content - $value\n" if $main::debug && fileno main::LOG;
    
	my $found = "";
    $path =~ /^(\/.+?)\//;
    my $base_path = $1;
    
    my $error;
    my $response = make_request("$content");

    my @result;

    if ($response->is_success) {

        my $con = $response->content;

        my $dom = XML::LibXML->load_xml(string => "$con");
        foreach my $fn ($dom->findnodes("$base_path/error")) {
            my $ret_error = $fn->findvalue('./string');
            print "ERROR: make_call_value $ret_error\n" if $ret_error; 
            print main::LOG "ERROR: make_call_value $ret_error\n" if $ret_error; 
        }

        foreach my $fn ($dom->findnodes($path)) {
			$found = $fn->findvalue('./' . $value) || "";
        }

    } else {
        $error= $response->status_line;
        print "ERROR: $error\n";
        print main::LOG "ERROR: $error\n";
        return;
    }

    return $found;
}

sub get_api_values {

    my $usr = $main::params{API_USER};
    my $pass = $main::params{API_PASSWORD};
    my $URL = $main::params{API_URL};

    print main::LOG "API VALUES: $usr - $URL\n" if $main::debug;

    if ( ! $usr || ! $pass || ! $URL ) {
        print "API user/pass/URL not found\n";
        exit 1;
    }

    return ($usr, $pass, $URL);
}

sub get_params {
    my ($conf) = @_;
	my %params;

	open(VARS,"<$conf") or ::exit_error("Can not open $conf: $!", "$main::gip_job_status_id", 4);
	while (<VARS>) {
	chomp;
	s/#.*//;
	s/^\s+//;
	s/\s+$//;
	next unless length;
	my ($var, $value) = split(/\s*=\s*/, $_, 2);
        $var =~ /^(.*)$/;
        $var = $1;
        if ( $var !~ /pass/ ) {
            $value =~ /^([\w.\-_\/:]{0,100})$/;
            $value = $1;
        } else {
            $value =~ /^(.*)$/;
            $value = $1;
        }

		$params{$var} = $value;
	}
	close VARS;

	return %params;

}


sub make_request {
    my ($content) = @_;

	my $this_function = (caller(1))[3];
	print main::LOG "CONTENT: $this_function - $content\n" if $main::debug;

    my ( $user, $pass, $URL) = get_api_values();

	print main::LOG "Did not got API user\n" if ! $user;
	print main::LOG "Did not got API password\n" if ! $pass;
	print main::LOG "Did not got API URL\n" if ! $URL;
	print "Did not got API user\n" if ! $user;
	print "Did not got API password\n" if ! $pass;
	print "Did not got API URL\n" if ! $URL;

	my $ua = new LWP::UserAgent;
	$ua->timeout(20);

	my ($request, $response, $error);

	$request = POST $URL, Content => $content;

	$request->authorization_basic($user, $pass);
	$response = $ua->request($request);

	print "response: $response\n" if $main::debug;

    return $response;
}


sub get_version {
        my $val;
        if ( ! $main::create_csv ) {
            my $dbh = ::mysql_connection();
            my $sth = $dbh->prepare("SELECT version FROM global_config");
            $sth->execute() or  die "Can not execute statement:$sth->errstr";
            $val = $sth->fetchrow_array;
            $sth->finish();
            $dbh->disconnect;
        } else {
            my $path = '/listGlobalConfigResult/globalConfig';
            my $content = "request_type=listGlobalConfig&client_name=$main::client";
            my $value = "version";
            $val = make_call_value("$path", "$content", "$value");
        }

        return $val;
}

sub get_dyn_dns_updates_enabled {
        my $val;
        if ( ! $main::create_csv ) {
            my $dbh = ::mysql_connection();
            my $sth = $dbh->prepare("SELECT dyn_dns_updates_enabled FROM global_config");
            $sth->execute() or  die "Can not execute statement:$sth->errstr";
            $val = $sth->fetchrow_array;
            $sth->finish();
            $dbh->disconnect;
        } else {
            my $path = '/listGlobalConfigResult/globalConfig';
            my $content = "request_type=listGlobalConfig&client_name=$main::client";
            my $value = "dyn_dns_updates_enabled";
            $val = make_call_value("$path", "$content", "$value");
        }

        return $val;
}


sub get_vigilada_redes {
	my ( $client_id,$red,$ip_version, $tag, $location_scan_ids ) = @_;

	my $ip_ref;
    my $exit_message = "";

	$ip_version="" if ! $ip_version;
	my $ip_version_expr="";
	if ( $ip_version eq "v4" ) {
		$ip_version_expr="AND ip_version='v4'";
	} elsif ( $ip_version eq "v6" ) {
		$ip_version_expr="AND ip_version='v6'";
	}
	my @vigilada_redes;
	if ( ! $main::create_csv ) {
		my $dbh = ::mysql_connection();

		my $sth;
		if ( $tag ) {
			my %tags = get_tag_hash("$client_id", "name");
			my $tag_expr = "";
			if ( %tags ) {
				$tag_expr = " AND red_num IN ( SELECT net_id from tag_entries_network WHERE (";
				foreach my $item ( @${tag} ) {
					if ( ! defined $tags{$item}->[0] ) {
						$exit_message = "$item: Tag NOT FOUND - exiting";
						::exit_error("$exit_message", "$main::gip_job_status_id", 4);
					}
					$tag_expr .= " tag_id=\"$tags{$item}->[0]\" OR";
				}
				$tag_expr =~ s/OR$//;
				$tag_expr .= " ))";
			}
			$sth = $dbh->prepare("SELECT red, BM, red_num, loc, dyn_dns_updates FROM net WHERE client_id=\"$client_id\" $ip_version_expr $tag_expr ORDER BY ip_version,red");
			$sth->execute() or print "error while prepareing query: $DBI::errstr\n";

		} elsif ( $location_scan_ids ) {
			my $loc_expr = " AND loc IN ( $location_scan_ids )";
			$sth = $dbh->prepare("SELECT red, BM, red_num, loc, dyn_dns_updates FROM net WHERE client_id=\"$client_id\" $ip_version_expr $loc_expr ORDER BY ip_version,red");
			$sth->execute() or print "error while prepareing query: $DBI::errstr\n";
			
		} else {
			$sth = $dbh->prepare("SELECT red, BM, red_num, loc, dyn_dns_updates FROM net WHERE vigilada=\"y\" AND client_id=\"$client_id\" $ip_version_expr ORDER BY ip_version,red");
			$sth->execute() or print "error while prepareing query: $DBI::errstr\n";
		}

		while ( $ip_ref = $sth->fetchrow_arrayref ) {
			push @vigilada_redes, [ @$ip_ref ];
		}

		$sth->finish();
		$dbh->disconnect;

	} else {

        my $path = '/listNetworksResult/NetworkList/Network';
        my $content = "request_type=listNetworks&client_name=$main::client&no_csv=yes";
        my @values = ("IP", "BM", "id", "site", "dyn_dns_updates", "customColumns/Tag", "site");

		if ( $ip_version eq "v4" ) {
			$content .= "&ip_version=v4";
		} elsif ( $ip_version eq "v6" ) {
			$content .= "&ip_version=v6";
		}
        if ( $tag ) {
            my $tag_string = join "|", @$tag;
            $content .= "&filter=TAG::$tag_string";
        }

        my @host_redes = Gipfuncs::make_call_array("$path", "$content", \@values);

		my $i = 0;
		my @new;
		foreach my $red ( @host_redes ) {
			my @arr;
			my $red = $host_redes[$i]->[0];
			my $BM = $host_redes[$i]->[1];
			my $red_num = $host_redes[$i]->[2];
			my $loc = $host_redes[$i]->[3];
			my $dyn_dns_updates = $host_redes[$i]->[4];
			my $tag_found = $host_redes[$i]->[5] || "";
			my $site_found = $host_redes[$i]->[6] || "";
			if ( $tag ) {
				$tag_found =~ s/\s//g;
				my @tag_arr = split ($tag,",");
				foreach my $t ( @tag_arr ) {
					if ( grep( /^$t$/, @main::tag ) ) {
						@arr = ( "$red", "$BM", "$red_num", "$loc", "$dyn_dns_updates", "$tag" );	
					}
				}
			} elsif ( $location_scan_ids ) {
				my @location_scan_vals = split(",", $location_scan_ids);
				if ( grep( /^${loc}$/, @location_scan_vals ) ) {
					@arr = ( "$red", "$BM", "$red_num", "$loc", "$dyn_dns_updates", "$tag" );	
				}
			}

			$i++;

			push @vigilada_redes, \@arr if @arr;
		}
	}

	return @vigilada_redes;
}

sub check_for_reserved_range {
	my ( $client_id,$red_num ) = @_;

    my @ranges;

	if ( ! $main::create_csv ) {
        my $ip_ref;
        my $dbh = mysql_connection();
        my $sth = $dbh->prepare("SELECT red_num FROM ranges WHERE red_num = \"$red_num\" AND client_id=\"$client_id\"");
        $sth->execute() or print "error while prepareing query: $DBI::errstr\n";
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
            push @ranges, [ @$ip_ref ];
        }
        $sth->finish();
        $dbh->disconnect;
    } else {
		my $path = '/listRangesResult/rangesList/Range';
        my $content = "request_type=listRanges&client_name=$main::client";
        my @values = ("red_num");
        @ranges = Gipfuncs::make_call_array("$path", "$content", \@values);
    }

    return @ranges;
}

sub get_tag_hash {
    my ( $client_id, $key ) = @_;

    return if $main::create_csv;

    my %values;
    my $ip_ref;
    $key = "id" if ! $key;

    my $dbh = ::mysql_connection();

    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT id, name, description, color, client_id FROM tag WHERE ( client_id = $qclient_id OR client_id = '9999' ) ORDER BY name"
        ) or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
    $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{id};
        my $name = $ip_ref->{name};
        my $description = $ip_ref->{description};
        my $color = $ip_ref->{color};
        my $client_id = $ip_ref->{client_id};
        if ( $key eq "id" ) {
            push @{$values{$id}},"$name","$description","$color","$client_id";
        } elsif ( $key eq "name" ) {
            push @{$values{$name}},"$id","$description","$color","$client_id";
        }
    }    
    $sth->finish();
    $dbh->disconnect;

    return %values;
}

sub get_loc_from_redid {
    my ( $client_id, $red_num ) = @_;
    my ( $ip_ref, $red_loc );

    if ( ! $main::create_csv ) {
        my $dbh = ::mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $sth = $dbh->prepare("SELECT l.loc FROM locations l, net n WHERE n.red_num = $qred_num AND n.loc = l.id AND n.client_id=\"$client_id\"") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $red_loc = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
    } else {
        my $path = '/readNetworkResult/Network';
        my $content = "request_type=readNetwork&client_name=$main::client&id=$red_num";
        my $value = "site";
        $red_loc = Gipfuncs::make_call_value("$path", "$content", "$value");
    }

    return $red_loc;
}

sub get_loc_hash {
    my ( $client_id, $key ) = @_;
    my %values;
    my $values;

	$key = "name" if ! $key;

    if ( ! $main::create_csv ) {
        my $ip_ref;
        my $dbh = ::mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT id,loc FROM locations WHERE ( client_id = $qclient_id OR client_id = '9999' )") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
   
        while ( $ip_ref = $sth->fetchrow_hashref ) {
            my $id = $ip_ref->{'id'};
            my $loc = $ip_ref->{'loc'};
			if ( $key eq "id" ) {
				$values{$id}="$loc";
			} else {
				$values{$loc}="$id";
			}
        }

        $dbh->disconnect;

        $values = \%values;
    } else {
        my $path = '/listSitesResult/siteList/Site';
        my $content = "request_type=listSites&client_name=$main::client";
        $values = Gipfuncs::make_call_name_id_hash("$path", "$content");
    }

    return $values;
}

sub get_cat_hash {
    my ( $client_id, $key ) = @_;
    my %values;
    my $values;

	$key = "name" if ! $key;

    if ( ! $main::create_csv ) {
        my $ip_ref;
        my $dbh = ::mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT id,cat FROM categorias") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);

        while ( $ip_ref = $sth->fetchrow_hashref ) {
            my $id = $ip_ref->{'id'};
            my $cat = $ip_ref->{'cat'};
			if ( $key eq "id" ) {
				$values{$id}="$cat";
			} else {
				$values{$cat}="$id";
			
			}
        }

        $dbh->disconnect;

        $values = \%values;
    } else {
        my $path = '/categoriesList/Category';
        my $content = "request_type=listCategories&client_name=$main::client";
        $values = Gipfuncs::make_call_name_id_hash("$path", "$content");
    }

    return $values;
}

sub get_utype_id {
    my ( $utype ) = @_;

    my $utype_id;

    if ( ! $main::create_csv ) {

        my $dbh = ::mysql_connection();
        my $qutype = $dbh->quote( $utype );
        my $sth = $dbh->prepare("SELECT id FROM update_type WHERE type=$qutype
                        ") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $utype_id = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
    } else {
        my %update_types = (
            man => 1,
            dns => 2,
            ocs => 3,
            NULL => "-1",
        );

        $utype_id = $update_types{$utype} || "-1";
    }

    return $utype_id;
}


sub get_host_redes_no_rootnet {
    my ( $client_id, $ip_version, $tag ) = @_;
    my @host_redes;
    my $ip_ref;

    if ( ! $main::create_csv ) {

		my $tag_expr = "";
		if ( $tag ) {
			my %tags = get_tag_hash("$client_id", "name");
			if ( %tags ) {
				$tag_expr = " AND red_num IN ( SELECT net_id from tag_entries_network WHERE (";
				foreach my $item ( @${tag} ) {
					if ( ! defined $tags{$item}->[0] ) {
						my $exit_message = "$item: Tag NOT FOUND - exiting";
						::exit_error("$exit_message", "$main::gip_job_status_id", 4);
					}
					$tag_expr .= " tag_id=\"$tags{$item}->[0]\" OR";
				}
				$tag_expr =~ s/OR$//;
				$tag_expr .= " ))";
			}
		}

        my $dbh = ::mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $ip_version_expr = "";
        if ( $ip_version ) {
            my $qip_version = $dbh->quote( $ip_version ) if $ip_version;
            $ip_version_expr = "AND ip_version=$qip_version";
        }
        my $sth = $dbh->prepare("SELECT red, BM, red_num, loc, ip_version, rootnet FROM net WHERE rootnet = '0' AND client_id = $qclient_id $ip_version_expr $tag_expr")
        or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
            push @host_redes, [ @$ip_ref ];
        }
        $dbh->disconnect;
    } else {
        my $ip_version_expr = "";
        if ( $ip_version ) {
            $ip_version_expr = "&ip_version=$ip_version";
        }
		my $tag_expr = "";
        if ( $tag ) {
			my $tag_string = join "|", @$tag;
            $tag_expr = "&filter=TAG::$tag_string";
        }
        my $path = '/listNetworksResult/NetworkList/Network';
        my $content = "request_type=listNetworks&client_name=$main::client&no_csv=yes${ip_version_expr}${tag_expr}";
        my @values = ("IP", "BM", "id", "loc", "ip_version", "rootnet");
        @host_redes = Gipfuncs::make_call_array("$path", "$content", \@values);
    }

    return @host_redes;
}

sub get_client_entries {
    my ( $client_id ) = @_;
    my @values;

    if ( ! $main::create_csv ) {
        my $ip_ref;
        my $dbh = ::mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
        my $sth;
        $sth = $dbh->prepare("SELECT c.client,ce.phone,ce.fax,ce.address,ce.comment,ce.contact_name_1,ce.contact_phone_1,ce.contact_cell_1,ce.contact_email_1,ce.contact_comment_1,ce.contact_name_2,ce.contact_phone_2,ce.contact_cell_2,ce.contact_email_2,ce.contact_comment_2,ce.contact_name_3,ce.contact_phone_3,ce.contact_cell_3,ce.contact_email_3,ce.contact_comment_3,ce.default_resolver,ce.dns_server_1,ce.dns_server_2,ce.dns_server_3 FROM clients c, client_entries ce WHERE c.id = ce.client_id AND c.id = $qclient_id") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
            push @values, [ @$ip_ref ];
        }
        $dbh->disconnect;

    } else {
        my $path = '/readClientResult/client';
        my $content = "request_type=readClient&client_name=$main::client";
        my @query_values = ("client", "phone", "fax", "address", "comment", "contact_name_1", "contact_phone_1", "contact_cell_1", "contact_email_1", "contact_name_2", "contact_comment_1", "contact_phone_2", "contact_cell_2", "contact_comment_2", "contact_email_2", "contact_name_3", "contact_phone_3", "contact_cell_3", "contact_comment_3", "contact_email_3", "default_resolver", "dns_server_1", "dns_server_2", "dns_server_3");
        @values = Gipfuncs::make_call_array("$path", "$content", \@query_values);
    }

    return @values;
}

sub get_custom_column_entry {
    my ( $client_id, $red_num, $cc_name ) = @_;

    my $entry;

    if ( ! $main::create_csv ) {
        my $dbh = ::mysql_connection();
        my $qred_num = $dbh->quote( $red_num );
        my $qcc_name = $dbh->quote( $cc_name );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT cce.entry from custom_net_column_entries cce WHERE cce.net_id = $qred_num AND cce.cc_id = ( SELECT id FROM custom_net_columns WHERE name = $qcc_name AND (client_id = $qclient_id OR client_id='9999'))
            ") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $entry = $sth->fetchrow_array;
        $sth->finish();
        $dbh->disconnect;
    } else {
        my $path = '/readNetworkResult/Network/customColumns';
        my $content = "request_type=readNetwork&client_name=$main::client&id=$red_num";
        my $value = $cc_name;
        $entry = Gipfuncs::make_call_value("$path", "$content", "$value");
    }

    return $entry;
}


sub get_dns_server_group_from_id {
    my ( $client_id, $id ) = @_;
    my @values;

    if ( ! $main::create_csv ) {
        my $ip_ref;
        my $dbh = ::mysql_connection();
        my $qid = $dbh->quote( $id );
        my $qclient_id = $dbh->quote( $client_id );
        my $sth = $dbh->prepare("SELECT name, description, dns_server1, dns_server2, dns_server3, client_id FROM dns_server_group WHERE id=$qid ORDER BY name") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
        while ( $ip_ref = $sth->fetchrow_arrayref ) {
            push @values, [ @$ip_ref ];
        }
        $sth->finish();
        $dbh->disconnect;
    } else {
        my $path = '/readDNSServerGroupResult/DNSServer';
        my $content = "request_type=readDNSServerGroup&client_name=$main::client&id=$id";
        my @vals = ("name", "description", "server1", "server2", "server3");
        @values = Gipfuncs::make_call_array("$path", "$content", \@vals);
    }
    print main::LOG "get_dns_server_froum_from_id: $values[0]->[0]\n" if $main::debug;

    return @values;
}

sub update_job_status {
    my ( $gip_job_status_id, $status, $end_time, $exit_message, $log_file ) = @_;

    $status = "" if ! $status;
    $exit_message = "" if ! $exit_message;
    $end_time = "" if ! $end_time;
    $log_file = "" if ! $log_file;

    if ( $main::delete_job_error ) {
        if ( $status != 4 ) {
            # warning
            $status = 5;
        }
    }

    my $dbh = ::mysql_connection();

    my $qgip_job_status_id = $dbh->quote( $gip_job_status_id );
    my $qstatus = $dbh->quote( $status );
    my $qend_time = $dbh->quote( $end_time );
    my $qlog_file = $dbh->quote( $log_file );
    my $qexit_message = $dbh->quote( $exit_message );

    if ( ! $status && ! $exit_message && ! $end_time && ! $log_file ) {
        return;
    }

    my $expr = "";
    $expr .= ", status=$qstatus" if $status;
    $expr .= ", exit_message=$qexit_message" if $exit_message;
    $expr .= ", end_time=$qend_time" if $end_time;
    $expr .= ", log_file=$qlog_file" if $log_file;
    $expr =~ s/^,//;

   print main::LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $main::debug && fileno main::LOG;
    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}

sub exit_error {
    my ( $message, $gip_job_status_id, $status, $exit_signal ) = @_;

    $exit_signal = "1" if ! $exit_signal;
    $exit_signal = "0" if $exit_signal eq "OK";

    print $message . "\n";
    print main::LOG $message . "\n" if fileno main::LOG;

    if ( $main::gip_job_status_id && ! $main::combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

#        my $time = scalar(localtime(time + 0));
        my $time=time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close main::LOG if fileno main::LOG;

	if ( $main::mail ) {

	    my @smtp_server_values = get_smtp_server_by_name("$main::smtp_server");

		send_mail (
			debug       =>  "$main::debug",
			mail_from   =>  $main::mail_from,
			mail_to     =>  \@main::mail_to,
			subject     => "Result $main::job_name - ERROR",
			smtp_server => "$main::smtp_server",
			smtp_message    => "",
			log         =>  "$main::log",
			gip_job_status_id   =>  "$main::gip_job_status_id",
			changes_only   =>  "$main::changes_only",
			smtp_server_values   =>  \@smtp_server_values,
		);
	}

    exit $exit_signal;
}


sub ip_to_int {
	my ($ip,$ip_version)=@_;

    if ( ! $ip_version ) {
        if ( $ip =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/ ) {
            $ip_version = "v4";
        } elsif ( $ip =~ /^(\w+):(\w+)/ ) {
            $ip_version = "v6";
        } else {
            print main::LOG "$ip - can not determine IP version\n" if $main::debug;
            return;
        }
    }

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

sub int_to_ip {
    my ($ip_int,$ip_version)=@_;

    my ( $ip_bin, $ip_ad);
    if ( $ip_version eq "v4" ) {
        $ip_bin = ip_inttobin ($ip_int,4);
        $ip_ad = ip_bintoip ($ip_bin,4);
    } else {
        $ip_bin = ip_inttobin ($ip_int,6);
        $ip_ad = ip_bintoip ($ip_bin,6);
    }
    return $ip_ad;
}


sub get_generic_auto {
    my ($ip, $ip_version) = @_;

    my $generic_auto = "";
    if ( $ip_version eq "v4" ) {
        $ip =~ /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/;
        $generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
    } else {
        $ip =~ /^(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+):(\w+)$/;
        $generic_auto = "$2-$3-$4|$4-$3-$2|$1-$2-$3|$3-$2-$1";
    }

    return $generic_auto;
}

sub get_network_scan_zones { 
	my ( $net_id, $type ) = @_;

	my @values;
	my $ip_ref;
	if ( ! $main::create_csv ) {
		my $dbh = ::mysql_connection();
		my $qnet_id = $dbh->quote( $net_id );
		my $qtype = $dbh->quote( $type );
		my $qclient_id = $dbh->quote( $main::client_id );

		my $sth = $dbh->prepare("SELECT t.id, t.name, t.description, t.type, t.client_id FROM dns_zone t WHERE t.type=$qtype AND t.id IN ( SELECT te.zone_id from scan_zone_entries_network te WHERE te.net_id=$qnet_id ) AND ( t.client_id=$qclient_id OR t.client_id='9999' ) ORDER BY id") or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		$sth->execute() or ::exit_error("Cannot execute statement: " . $DBI::errstr, "$main::gip_job_status_id", 4);
		while ( $ip_ref = $sth->fetchrow_arrayref ) {
			push @values, [ @$ip_ref ];
		}
		$sth->finish();
		$dbh->disconnect;
	} else {
        my $path = '/readNetworkResult/Network';
        my $content = "request_type=readNetwork&client_name=$main::client&id=$net_id";
		my @values_param;
		if ( $type eq "A" ) {
			@values_param = ("customColumns/ScanAZones/ScanAZone");
		} elsif ( $type eq "PTR" ) {
			@values_param = ("customColumns/ScanPTRZones/ScanPTRZone");
		} else {
			return;
		}

		@values = Gipfuncs::make_call_array("$path", "$content", \@values_param);
    }

	return @values;
}

sub compare_hashes {
    my ($reverse_records, $reverse_records_zone, $ip_version) = @_;

	if ( keys( %$reverse_records ) && ! keys( %$reverse_records_zone )) {
        print "R1\n" if $main::debug;
		return $reverse_records;
	}
	if ( ! keys( %$reverse_records ) && keys( %$reverse_records_zone )) {
        print "R2\n" if $main::debug;
		return $reverse_records_zone;
	}

    my %new_hash;

    # prefere PTR records
    my $generic_auto;
    foreach my $k (keys %{ $reverse_records_zone }) {
        $generic_auto = get_generic_auto("$k", "$ip_version");
        if ( $main::ignore_generic_auto =~ /^yes$/i && $reverse_records_zone->{$k} !~ /$generic_auto/) {
            $new_hash{$k} = $reverse_records_zone->{$k};
#        } elsif ( $main::ignore_generic_auto =~ /^no$/i ) {
        } else {
            $new_hash{$k} = $reverse_records_zone->{$k};
        }
    }

    # use A record if no PTR record defined
    foreach my $k (keys %{ $reverse_records }) {
        if (not exists $new_hash{$k}) {
            $generic_auto = get_generic_auto("$k", "$ip_version");
            if ( $main::ignore_generic_auto =~ /^yes$/i && $reverse_records->{$k} !~ /$generic_auto/) {
                $new_hash{$k} = $reverse_records->{$k};
#            } elsif ( $main::ignore_generic_auto =~ /^no$/i ) {}
            } else {
                $new_hash{$k} = $reverse_records->{$k};
            }
        }
    }

    return \%new_hash;
}

sub get_db_parameter {
	my @document_root;
    if ( $main::document_root ) {
        push @document_root, "$main::document_root";
    } else {
        @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    }
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or exit_error("Can not open $priv_file: $!", "$main::gip_job_status_id", 4);
            while (<OUT>) {
                if ( $_ =~ /^sid=/ ) {
                    $_ =~ /^sid=(.*)$/;
                    $main::sid_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_host=/ ) {
                    $_ =~ /^bbdd_host=(.*)$/;
                    $main::bbdd_host_gestioip = $1;
                } elsif ( $_ =~ /^bbdd_port=/ ) {
                    $_ =~ /^bbdd_port=(.*)$/;
                    $main::bbdd_port_gestioip = $1;
                } elsif ( $_ =~ /^user=/ ) {
                    $_ =~ /^user=(.*)$/;
                    $main::user_gestioip = $1;
                } elsif ( $_ =~ /^password=/ ) {
                    $_ =~ /^password=(.*)$/;
                    $main::pass_gestioip = $1;
                }
            }
            close OUT;
            last;
        }
    }
    if ( ! $main::sid_gestioip ) {
        $main::sid_gestioip = $main::params{sid_gestioip};
        $main::bbdd_host_gestioip = $main::params{bbdd_host_gestioip};
        $main::bbdd_port_gestioip = $main::params{bbdd_port_gestioip};
        $main::user_gestioip = $main::params{user_gestioip};
        $main::pass_gestioip = $main::params{pass_gestioip};
    }

	if ( ! $main::sid_gestioip ) {
		print "Can not determine database parameter\n";
		exit 1;
	}

    return ($main::sid_gestioip, $main::bbdd_host_gestioip, $main::bbdd_port_gestioip, $main::user_gestioip, $main::pass_gestioip);
}


1;
