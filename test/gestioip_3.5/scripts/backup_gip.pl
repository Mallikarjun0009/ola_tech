#!/usr/bin/perl -w

# 20210330 v1.1

use strict;
use FindBin qw($Bin);

my ( $dir, $base_dir, $gipfunc_path);
BEGIN {
    $dir = $Bin;
    $gipfunc_path = $dir . '/include';
}

use lib "$gipfunc_path";
use Gipfuncs;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use DBI;
use Time::Local;
use Date::Calc qw(Add_Delta_Days);
use Date::Manip qw(UnixDate);
use Mail::Mailer;
#use Socket;
#use Fcntl qw(:flock);
use POSIX;


my $VERSION="3.5.5";
my $CHECK_VERSION="3";

$dir =~ /^(.*)\/bin/;
$base_dir=$1;


my ( $help, $log, $run_once, $client, $logdir, $verbose, $debug, $gip_job_id, $user, $combined_job, $mail, $smtp_server, $mail_from, $mail_to, $changes_only);
$help=$log=$run_once=$client=$logdir=$verbose=$debug=$gip_job_id=$user=$combined_job=$mail=$smtp_server=$mail_from=$mail_to=$changes_only="";

GetOptions(
    "log=s"=>\$log,
    "combined_job!"=>\$combined_job,
    "mail!"=>\$mail,
    "smtp_server=s"=>\$smtp_server,
    "mail_from=s"=>\$mail_from,
    "mail_to=s"=>\$mail_to,
    "help!"=>\$help,
    "run_once!"=>\$run_once,
    "user=s"=>\$user,
    "verbose!"=>\$verbose,
    "x!"=>\$debug,

    "A=s"=>\$client,
    "M=s"=>\$logdir,
    "W=s"=>\$gip_job_id,
) or print_help("Argument error");

$debug=0 if ! $debug;
$verbose = 1 if $debug;

$client = "DEFAULT";
my $client_id = 9999;
my $vars_file=$base_dir . "/etc/vars/vars_update_gestioip_en";

# Get mysql parameter from priv
my ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip) = get_db_parameter();

if ( ! $sid_gestioip || ! $user_gestioip ) {
	print "Database parameter not found\n";
	exit 1;
}

my $job_name;
if ( $gip_job_id) {

    my $job_status = Gipfuncs::check_disabled("$gip_job_id");
    if ( $job_status != 1 ) {
        exit;
    }

    if ( ! $run_once) {
        my $check_start_date = Gipfuncs::check_start_date("$gip_job_id", "5") || "";
        if ( $check_start_date eq "TOO_EARLY" ) {
            exit;
        }
    }

    if ( ! $combined_job) {
        $job_name = Gipfuncs::get_job_name("$gip_job_id");
        my $audit_type="176";
        my $audit_class="33";
        my $update_type_audit="2";

        my $event="$job_name ($gip_job_id)";
        insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$vars_file");
    }
}


my $exit_message = "";

my $start_time=time();

my $datetime;
my $gip_job_status_id = "";
($log, $datetime) = Gipfuncs::create_log_file( "$client", "$log", "$base_dir", "$logdir", "backup_gip");

print "Logfile: $log\n" if $verbose;

open(LOG,">$log") or exit_error("Can not open $log: $!", "", 4);
*STDERR = *LOG;


my @mail_to;
if ( $mail && ! $smtp_server ) {
        exit_error("Missing argument --smtp_server", "$gip_job_status_id", 4);
}
if ( $smtp_server ) {
    if ( ! $mail_from ) {
            exit_error("Missing argument --mail_from", "$gip_job_status_id", 4);
    }
    if ( ! $mail_to ) {
            exit_error("Missing argument --mail_to", "$gip_job_status_id", 4);
    }
    @mail_to = split(",",$mail_to);
}


my $gip_job_id_message = "";
$gip_job_id_message = "Job ID: $gip_job_id" if $gip_job_id;
print LOG "$datetime backup_gip.pl, $gip_job_id_message\n\n" if $gip_job_id;

my $logfile_name = $log;
$logfile_name =~ s/^(.*\/)//;

my $delete_job_error;
if ( $gip_job_id && ! $combined_job) {
    if ( $run_once ) {
        $delete_job_error = delete_cron_entry("$gip_job_id");
        if ( $delete_job_error ) {
            print LOG "ERROR: Job not deleted from crontab: $delete_job_error";
        }
    } else {
        my $check_end_date = Gipfuncs::check_end_date("$gip_job_id", "5") || "";
        if ( $check_end_date eq "TOO_LATE" ) {
            $delete_job_error = delete_cron_entry("$gip_job_id");
            if ( $delete_job_error ) {
                $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
                exit_error("ERROR: Job not deleted from crontab: $delete_job_error", "$gip_job_status_id", 4 );
            } else {
                exit;
            }
        }
    }
    # status 2: running
    $gip_job_status_id = insert_job_status("$gip_job_id", "2", "$logfile_name" );
}


my $command = $base_dir . "/bin/backup_gip.sh";
my $output = `$command 2>&1`;

print LOG "backup_gip.sh: $output";

close LOG;

Gipfuncs::send_mail (
    debug       =>  "$debug",
    mail_from   =>  $mail_from,
    mail_to     =>  \@mail_to,
    subject     => "Result Job $job_name",
    smtp_server => "$smtp_server",
    smtp_message    => "",
    log         =>  "$log",
    gip_job_status_id   =>  "$gip_job_status_id",
    changes_only   =>  "$changes_only",
) if $mail;

if ( $output =~ /ERROR/ ) {
	exit_error("ERROR: $output", "$gip_job_status_id", 4 );
}

my $end_time=time();

if ( $gip_job_id && ! $combined_job ) {
    update_job_status("$gip_job_status_id", "3", "$end_time", "Job successfully finished", "");
}

print "Job successfully finished\n";
exit 0;




#######################
# Subroutiens
#######################

sub get_db_parameter {
    my @document_root = ("/var/www", "/var/www/html", "/srv/www/htdocs");
    foreach ( @document_root ) {
        my $priv_file = $_ . "/gestioip/priv/ip_config";
        if ( -R "$priv_file" ) {
            open("OUT","<$priv_file") or exit_error("Can not open $priv_file: $!", "$gip_job_status_id", 4);
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
#    if ( ! $sid_gestioip ) {
#        $sid_gestioip = $params{sid_gestioip};
#        $bbdd_host_gestioip = $params{bbdd_host_gestioip};
#        $bbdd_port_gestioip = $params{bbdd_port_gestioip};
#        $user_gestioip = $params{user_gestioip};
#        $pass_gestioip = $params{pass_gestioip};
#    }

    return ($sid_gestioip, $bbdd_host_gestioip, $bbdd_port_gestioip, $user_gestioip, $pass_gestioip);
}


sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip)  or die "Mysql ERROR: ". $DBI::errstr;
    return $dbh;
}

sub insert_job_status {
    my ( $gip_job_id, $status, $log_file ) = @_;

    $log_file = "" if ! $log_file;
    $status = 2 if ! $status; # "running"

    my $time = time();

    my $dbh = mysql_connection();

    my $qgip_job_id = $dbh->quote( $gip_job_id );
    my $qstatus = $dbh->quote( $status );
    my $qtime = $dbh->quote( $time );
    my $qlog_file = $dbh->quote( $log_file );

    my $sth = $dbh->prepare("INSERT INTO scheduled_job_status (job_id, status, start_time, log_file) values ($qgip_job_id, $status, $time, $qlog_file)");
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth = $dbh->prepare("SELECT LAST_INSERT_ID()") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    my $id = $sth->fetchrow_array;

    $sth->finish();
    $dbh->disconnect;

    return $id;
}


sub update_job_status {
    my ( $gip_job_status_id, $status, $end_time, $exit_message, $log_file ) = @_;

    $status = "" if ! $status;
    $exit_message = "" if ! $exit_message;
    $end_time = "" if ! $end_time;
    $log_file = "" if ! $log_file;

    if ( $delete_job_error ) {
        if ( $status != 4 ) {
            # warning
            $status = 5;
        }
    }

    my $dbh = mysql_connection();

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

    print "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug;
#   print LOG "UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id\n" if $debug && fileno LOG;
    my $sth = $dbh->prepare("UPDATE scheduled_job_status SET $expr WHERE id=$qgip_job_status_id") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);

    $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
    $sth->finish();
    $dbh->disconnect;
}


sub exit_error {
    my ( $message, $gip_job_status_id, $status, $exit_signal ) = @_;

    $exit_signal = "1" if ! $exit_signal;
    $exit_signal = "0" if $exit_signal eq "OK";

    print $message . "\n";
    print LOG $message . "\n" if fileno LOG;

    if ( $gip_job_status_id && ! $combined_job ) {
        # status 1 scheduled, 2 running, 3 completed, 4 failed, 5 warning

#        my $time = scalar(localtime(time + 0));
        my $time=time();

        update_job_status("$gip_job_status_id", "$status", "$time", "$message");
    }

    close LOG  if fileno LOG;

    exit $exit_signal;
}

sub delete_cron_entry {
    my ($id) = @_;

    $ENV{PATH} = "";

    my $crontab = "/usr/bin/crontab";

    my $echo = "/bin/echo";

    my $grep = "/bin/grep";

    my $command = $crontab . ' -l | ' . $grep . ' -v \'#ID: ' . $id . '$\' | ' . $crontab . ' -';

    my $output = `$command 2>&1`;
    if ( $output ) {
        return $output;
    }
}

sub insert_audit_auto {
        my ($client_id,$event_class,$event_type,$event,$update_type_audit,$vars_file) = @_;

        my $remote_host = "N/A";

        $user=$ENV{'USER'} if ! $user;
        my $mydatetime=time();
        my $dbh = mysql_connection();
        my $qevent_class = $dbh->quote( $event_class );
        my $qevent_type = $dbh->quote( $event_type );
        my $qevent = $dbh->quote( $event );
        my $quser = $dbh->quote( $user );
        my $qupdate_type_audit = $dbh->quote( $update_type_audit );
        my $qmydatetime = $dbh->quote( $mydatetime );
        my $qremote_host = $dbh->quote( $remote_host );
        my $qclient_id = $dbh->quote( $client_id );

        my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,remote_host,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qremote_host,$qclient_id)") or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->execute() or exit_error("Cannot execute statement: " . $DBI::errstr, "$gip_job_status_id", 4);
        $sth->finish();
}


sub print_help {
        print "\nusage: backup_gip.pl [OPTIONS...]\n\n";
        print "-d, --debug              debug\n";
        print "-h, --help               help\n";
        print "-v, --verbose            verbose\n\n";
        exit;
}

