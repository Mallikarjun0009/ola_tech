#!/usr/bin/perl -w

# Copyright (C) 2019 Marc Uebel

# This program is distributed under the Creative Commons Attribution-NonCommercial-NoDerivatives
# 4.0 International License.
# Visit http://creativecommons.org/licenses/by-nc-nd/4.0/ for details.

# 202010707 v3.5.3.5.2

 
use Expect;
use strict;
use warnings;
use Getopt::Long;
Getopt::Long::Configure ("no_ignore_case");
use POSIX qw(strftime);
use FindBin qw($Bin);
use DBI;
use File::Compare;
use File::Copy;
use Net::IP;
use Net::IP qw(:PROC);
use XML::Parser;
use XML::Simple;
use Data::Dumper;
use File::Path qw(make_path);
use Cwd;
use Mail::Mailer;
use Digest::MD5 qw(md5);
use Parallel::ForkManager;
use Time::HiRes;



my $VERSION="3.5.3";

my $timeout = 30;
my $enable_audit=1;

my $dir = $Bin;
$dir =~ /^(.*)\/bin/;
my $base_dir=$1;

my $conf = "${base_dir}/etc/ip_update_gestioip.conf";

my $start_time=time();

my ( $verbose,$debug,$hosts,$help,$log_file_name,$mail,$sql_sid,$sql_host,$sql_port,$sql_user,$sql_pass,$server_name_licence_param, $client_name );
my @ARGV_orig=@ARGV;
my $last_return="";
my $upload_config_file="";
my $backup_file_name_param="";
my $job_name_param="";
my $job_id_param="";
my $job_group_param="";
my $run_unassociated_job_param="";
my $audit_user_param="";
$debug=0;

print_help() if ! $ARGV[0];

GetOptions(
    "verbose!"=>\$verbose,
    "debug=s"=>\$debug,
    "csv_hosts=s"=>\$hosts,
    "log_file_name=s"=>\$log_file_name,
    "backup_file_name=s"=>\$backup_file_name_param,
    "upload_config_file=s"=>\$upload_config_file,
    "id=s"=>\$job_id_param,
    "group_id=s"=>\$job_group_param,
    "jobname=s"=>\$job_name_param,
    "name_client=s"=>\$client_name,
    "mail!"=>\$mail,
    "run_unassociated_job!"=>\$run_unassociated_job_param,
    "server_name_licence=s"=>\$server_name_licence_param,
    "audit_user=s"=>\$audit_user_param,
    "help!"=>\$help
) or print_help();

my $cm_conf_file = "/usr/share/gestioip/etc/cmm.conf";

my %params=get_params("$conf");

check_options();

my $client_id;

my $datetime=time();
my $date_log = strftime "%Y%m%d%H%M%S", localtime($datetime);
my $date_file = strftime "%Y%m%d%H%M", localtime($datetime);
my $date = strftime "%d/%m/%Y %H:%M:%S", localtime($datetime);

my $gip_document_root="";
if ( -d "/var/www/gestioip" ) {
    $gip_document_root="/var/www/gestioip";
} elsif ( -d "/var/www/html/gestioip" ) {
    $gip_document_root="/var/www/html/gestioip";
} elsif ( -d "/srv/www/htdocs/gestioip" ) {
    $gip_document_root="/srv/www/htdocs/gestioip";
}

my ( $sid_gestioip,$bbdd_host_gestioip,$bbdd_port_gestioip,$user_gestioip,$pass_gestioip);  
if (( $params{sid_gestioip} && $params{bbdd_host_gestioip} && $params{bbdd_port_gestioip} && $params{user_gestioip} && $params{pass_gestioip} ) && ( $params{pass_gestioip} !~ /^xxxxxx$/ )) {

    $sid_gestioip=$params{sid_gestioip};
    $bbdd_host_gestioip=$params{bbdd_host_gestioip};
    $bbdd_port_gestioip=$params{bbdd_port_gestioip};
    $user_gestioip=$params{user_gestioip};
    $pass_gestioip=$params{pass_gestioip};

} else {

    my $gip_priv_file=$gip_document_root . "/priv/ip_config";
    if ( -r $gip_priv_file ) {
        open(PRIV_FILE,"<$gip_priv_file") or die("ERROR: Can not open $gip_priv_file: $!");
        my $line;
        while (<PRIV_FILE>) {
            $line=$_;
            if ( $line =~ /bbdd_host=/ ) {
                $line =~ /bbdd_host=(.*)$/;
                $bbdd_host_gestioip=$1;
            } elsif ( $line =~ /bbdd_port=/ ) {
                $line =~ /bbdd_port=(.*)$/;
                $bbdd_port_gestioip=$1;
            } elsif ( $line =~ /sid=/ ) {
                $line =~ /sid=(.*)$/;
                $sid_gestioip=$1;
            } elsif ( $line =~ /user=/ ) {
                $line =~ /user=(.*)$/;
                $user_gestioip=$1;
            } elsif ( $line =~ /password=/ ) {
                $line =~ /password=(.*)$/;
                $pass_gestioip=$1;
            }
        }
        close PRIV_FILE;
    } else {
        print "ERROR: Can not access to database. Please check database parameter in $conf\n";
	exit 113;
    }
}

check_parameters();

$verbose=1 if $verbose || $debug;

my ($mail_destinatarios,$mail_from);
if ( $mail ) {
    $mail_destinatarios = \$params{mail_destinatarios};
    $mail_from = \$params{mail_from};
}

my $backup_always = $params{backup_always} || "no";
$backup_always = "no" if ! $backup_always eq "yes";

my @global_config = get_global_config("$client_id");

my $cm_backup_dir=$global_config[0]->[9] . "/" . $client_name;
my $cm_log_dir=$global_config[0]->[11];
my $cm_xml_dir=$global_config[0]->[12];

if ( ! -d $cm_log_dir ) {
	print "ERROR: Log directory not found: $cm_log_dir\n";
	exit 114;
}

$log_file_name=$date_log . "_" . $client_id . "_fetch_config.log" if ! $log_file_name;
my $logfile=$cm_log_dir . "/" . $log_file_name;

open(LOG,">>$logfile") or die("can not create logfile $logfile: $!");

print "using logfile: $logfile\n" if $verbose;
print_log("NOREF","$0 started at $date");
print_log("NOREF","executing fetch_config.pl @ARGV_orig");

if ( ! -d $cm_xml_dir ) {
	print_log("NOREF","ERROR: XML directory not found: $cm_xml_dir");
	print "ERROR: XML directory not found: $cm_xml_dir\n";
}


check_cm_licence("$client_id");

if ( -R $cm_conf_file ) {
     print_log("NOREF","check -R $cm_conf_file: OK")
} else {
     print_log("NOREF","check -R $cm_conf_file: NOT OK")
}
if ( -r $cm_conf_file ) {
     print_log("NOREF","check -r $cm_conf_file: OK")
} else {
     print_log("NOREF","check -r $cm_conf_file: NOT OK")
}

my $cm_enabled_db=$global_config[0]->[8] || "";
if ( $cm_enabled_db ne "yes" && ! -r $cm_conf_file ) {
    exit_error("ERROR - Configuration management disabled or can not read cmm.conf: $cm_conf_file","100");
}



# Create backup dir if not exists
if ( ! -d $cm_backup_dir ) {
    mkdir "$cm_backup_dir" or exit_error("ERROR: Can not create backup directory $cm_backup_dir: $!","101");
}


my %device_values=();
if ( $hosts ) {
    %device_values=get_device_values("$client_id","$hosts");
} elsif ( $job_id_param && ! $hosts ) {
    $hosts=get_host_id_from_job_id("$client_id","$job_id_param") || "";
    exit_error("ERROR: Job ID not found: $job_id_param","109") if ! $hosts;
    %device_values=get_device_values("$client_id","$hosts");
} else {
    %device_values=get_device_values("$client_id");
}

if ( ! %device_values ) {
    exit_error("ERROR: No valid IPs to fetch configuration from found. Check if Configuration Management is enabled for this IPs.","102");
}

my %values_cm_server=get_cm_server_hash_key_host_id("$client_id");
my @values_cm_server_keys=keys(%values_cm_server);
my $size=scalar @values_cm_server_keys;
if ( $size == 0 ) {
    exit_error("ERROR: no configuration backup server found","103");
}

my $global_error="";

my ($error_expr_command_1,$error_expr_command_2,$error_expr_command_3,$error_expr_command_4,$error_expr_command_5,$error_expr_command_6,$error_expr_command_7,$error_expr_command_8,$error_expr_command_9,$error_expr_command_10,$error_expr_command_11,$error_expr_command_12,$error_expr_command_13,$error_expr_command_14,$error_expr_command_15,$error_expr_command_16,$error_expr_command_17,$error_expr_command_18,$error_expr_command_19);

my $error_expr_login="[Ll]ogin invalid|[Ll]ogin failed|Login incorrect|.*ERROR.*|.*[Ee]rror.*|.*[Ff]ailed.*|.*[Ii]nvalid.*|.*[Uu]nsuccessful.*|.*[Ii]ncorrect.*|.*[Uu]nreachable.*|.*[Uu]nable.*|.*[Dd]enied.*|.*[Rr]efused.*|.*[Vv]iolation.*|.*[Tt]imed out.*|.*[Ti]meout.*";

my $generic_username_expr="[Ll]ogin.?:.?\$|[Uu]sername.?:.?\$|[Uu]ser [Nn]ame.?:.?\$|[Uu]ser.?:.?\$|[Ll]ogin [Nn]ame.?:.?\$";
my $generic_password_expr="[Pp]assword.?:.?\$|[Pp]asswd.?:.?\$";

my $logout_expr="[Cc]onnection to .* closed|[Cc]onnection closed|[Ss]ession terminated|logout";
# (Linux telnet: Login incorrect)

#Messages that indicate a successful login but that match with $error_expr_login
my $error_expr_login_execeptions=".*will be checked for errors at next reboot|Failed login attempts";

my $unsaved_changes_expr_generic='unsaved changes.*Would you like to save them now? (y/N)|The system has unsaved changes|Would you like to save them now|(Profile.Configuration) changes have occurred|Do you wish to save your configuration changes|Do you wish to save your configuration changes|Configuration modified, save|Do you want to save current configuration|Do you wish to save|Configuration modified, save';

my ($host_id,$device_type_group_id,$device_user_group_id,$description,$connection_proto,$connection_proto_port,$cm_server_id,$user_name,$login_pass,$enable_pass,$rsa_identity_file,$ip,$cm_server_ip,$backup_proto,$cm_server_username,$cm_server_password,$save_config_changes,$logged_out,$pager_expr,$enable_prompt,$found_enable_prompt_execute_commands,$loginConfirmationExpr,$preLoginConfirmationExpr,$showHostnameCommand);

my ($exp,$r);     
my @all_hosts=();
my @ok_hosts=();
my @unchanged_hosts=();
my ($anz_ok_hosts,$anz_failed_hosts);
my $error_detected=0;
#my $error_detected;
my $next_error_set=0;
my $login_pass_send=0;
my $username_send=0;
my $last_backup_state_host=0;
my $diffConfigIgnore="_NO_diffConfigIgnore_VALUE_";
my $cm_server_root="";
my $anz_device_values=scalar(keys %device_values);
my $hostname_from_command="";

my ($prompt_values,$login_atts,$backup_copy_commands,$enable_commands,$logout_commands,$jobs,$pager_disable_commands,$unsaved_changes_expr,$pager_expr_hash_ref,$loginConfirmationExpr_hash_ref,$preLoginConfirmationExpr_hash_ref,$showHostnameCommand_hash_ref)=get_device_type_values();
my %other_jobs=get_other_device_jobs_all($client_id);
my %jobs=%$jobs;

my $logfile_stdout;
$logfile_stdout=$logfile . "_stdout";
if ( $verbose ) {
    open STDOUT, '>>', "$logfile_stdout" or print_log("NOREF","WARNING: Can not open STDOUT log: $logfile_stdout; $!");
}

my %res_sub;
my %res;
my ($max_sinc_procs, $pid);

my $exit = 1;

my $MAX_PROCESSES = $max_sinc_procs || $params{max_sinc_procs};
$MAX_PROCESSES = "32" if ! $MAX_PROCESSES;
print_log("NOREF","Using $MAX_PROCESSES childs") if $verbose;
if ( $MAX_PROCESSES !~ /^4|8|16|32|64|128|254$/ ) {
        print "-max_sinc_procs must be one of this numbers: 4|8|16|32|64|128|254\n";
#	print_help("-max_sinc_procs must be one of this numbers: 4|8|16|32|64|128|254");
}
my $pm = new Parallel::ForkManager($MAX_PROCESSES);

$pm->run_on_finish(
	sub { my ($pid, $exit_code, $ident) = @_;
		$res_sub{$pid}=$exit_code;
	}
);
$pm->run_on_start(
	sub { my ($pid,$ident)=@_;
		$res{$pid}="$ident";
	}
);

my $child_log_dir = "/tmp/gip_childlog";
unless(mkdir $child_log_dir) {
	print_log("NOREF","Unable to create $child_log_dir: $!");
#    exit_error("Unable to create $child_log_dir: $!","115");
}
my $status_file = $child_log_dir . "/" . "status";
open(STATUS,">>$status_file") or print_log("NOREF","Unable open $status_file: $!");

close LOG;
#close STDOUT if $verbose;

for my $key_value ( sort { $device_values{$a}[12] <=> $device_values{$b}[12] } keys %device_values ) {
# sort by ip_int;

    Time::HiRes::sleep (0.4);

	##fork
	my $key = $key_value;
	$pid = $pm->start("$key") and next;

	# child start

	my $child_log_file = $child_log_dir . "/" . $key . ".log";
	my $child_log_file_stdout = $child_log_dir . "/" . $key . "_stdout.log";

	open(LOG, ">$child_log_file");
    if ( $verbose ) {
        open STDOUT, '>', "$child_log_file_stdout" or print_log("NOREF","WARNING: Can not open STDOUT log: $child_log_file_stdout; $!") if $verbose;
    }

    $error_detected=0;

    $next_error_set=0;
    $login_pass_send=0;
    $username_send=0;
    $logged_out=0;
    $found_enable_prompt_execute_commands=1;

    my $logged_in=0;
    my ($logout_command, $prompt);

    my @value = $device_values{$key};
    $host_id=$key;
    $device_type_group_id=$value[0][0] || "";
    $device_user_group_id=$value[0][1] || "";
    if ( ! $device_user_group_id ) {
        $user_name=$value[0][2] || "";
        $login_pass=$value[0][3] || "";
        $enable_pass=$value[0][4] || "";
    } else {
        $user_name=$value[0][8] || "";
        $login_pass=$value[0][9] || "";
        $enable_pass=$value[0][10] || "";
    }
    $description=$value[0][5] || "";
    $connection_proto=$value[0][6] || "";
    $connection_proto_port=$value[0][15] || "";
    $cm_server_id=$value[0][7] || "";
    $ip=$value[0][11] || "";
    $save_config_changes=$value[0][13] || "";
    my $hostname=$value[0][14] || "";
    $rsa_identity_file=$value[0][16] || "";

    my $save_running_config="yes";

    my %prompt_values=%$prompt_values;
    my %login_atts=%$login_atts;
    my %backup_copy_commands=%$backup_copy_commands;
    my %enable_commands=%$enable_commands;
    my %logout_commands=%$logout_commands;
    my %pager_disable_commands=%$pager_disable_commands;
    my %unsaved_changes_expr=%$unsaved_changes_expr;
    my %pager_expr_hash=%$pager_expr_hash_ref;
    my %loginConfirmationExpr_hash=%$loginConfirmationExpr_hash_ref;
    my %preLoginConfirmationExpr_hash=%$preLoginConfirmationExpr_hash_ref;
    my %showHostnameCommand_hash=%$showHostnameCommand_hash_ref;

    my $other_jobs_host=$other_jobs{$host_id} || "";
    my %other_jobs_host=();
    %other_jobs_host=%$other_jobs_host if $other_jobs_host;

    # check what commands should be executed
    my %other_jobs_to_execute=();
    my %other_jobs_to_execute_copy_local=();

    # get availabel job types
    my %job_types=get_job_types_id();


    if ( $run_unassociated_job_param ) {
        my $undef_job_id=99911;

        if ( $jobs{$device_type_group_id}{$job_name_param} ) {
            my $job_type_other_job=$jobs{$device_type_group_id}{$job_name_param}{jobType}[1] || "";
            my $job_type_other_job_id=$job_types{$job_type_other_job} || "";
            my $job_enabled=1;
            if ( $job_type_other_job_id == 4 ) {
                #copy_local
                push @{$other_jobs_to_execute_copy_local{$undef_job_id}},"$job_name_param","","","$job_type_other_job_id","$job_enabled";
            } else {
                push @{$other_jobs_to_execute{$undef_job_id}},"$job_name_param","","","$job_type_other_job_id","$job_enabled";
            }
        }
            
    } else {
        if ( scalar(keys %other_jobs_host ) == 0 ) {
            print_log("NOREF","NO VALID JOBS FOUND - Skipping $ip");
#            next;
			finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
        }

	    for my $other_job_id ( keys %other_jobs_host ) {
            my $other_job_name=$other_jobs_host{$other_job_id}[0];
            my $other_job_group=$other_jobs_host{$other_job_id}[1] || "";
            my $other_job_type=$jobs{$device_type_group_id}{$other_job_name}{jobType}[1] || "";
            my $other_job_enabled=$other_jobs_host{$other_job_id}[3] || 0;
            if ( $other_job_type eq "copy_file" ) {
                $other_job_type=1;
            } elsif ( $other_job_type eq "fetch_command_output" ) {
                $other_job_type=2;
            } elsif ( $other_job_type eq "task" ) {
                $other_job_type=3;
            } elsif ( $other_job_type eq "copy_local" ) {
                $other_job_type=4;
            } else {
                print_log("NOREF","Job has invalid JOB TYPE: $other_job_type - Job IGNORED");
                next;
            }

            $other_jobs_host{$other_job_id}[3]=$other_job_type;
            $other_jobs_host{$other_job_id}[4]=$other_job_enabled;

            if ( $other_job_type eq "4" ) {
                print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                $other_jobs_to_execute_copy_local{$other_job_id}=$other_jobs_host{$other_job_id};
            } else {
                if ( $job_id_param ) {
                    if ( $job_id_param == $other_job_id) {
                        $other_jobs_to_execute{$other_job_id}=$other_jobs_host{$other_job_id};
                        print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                        last;
                    }
                } elsif ( $job_name_param && $job_group_param) {
                    if ( $job_name_param eq $other_job_name && $job_group_param eq $other_job_group) {
                        $other_jobs_to_execute{$other_job_id}=$other_jobs_host{$other_job_id};
                        print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                    }
                } elsif ( $job_name_param ) {
                    if ( $job_name_param eq $other_job_name ) {
                        $other_jobs_to_execute{$other_job_id}=$other_jobs_host{$other_job_id};
                        print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                    }
                } elsif ( $job_group_param ) {
                    if ( $job_group_param eq $other_job_group ) {
                       $other_jobs_to_execute{$other_job_id}=$other_jobs_host{$other_job_id};
                        print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                    }
                } else {
                    #execute all command if nothing else is specified
                    $other_jobs_to_execute{$other_job_id}=$other_jobs_host{$other_job_id};
                    print_log("NOREF","$ip: Found Job: $other_job_name - $other_job_group - $other_job_type - $other_job_enabled") if $verbose;
                }
            }
	    }
    }

    if ( keys(%other_jobs_to_execute) == 0 && keys(%other_jobs_to_execute_copy_local) == 0 ) {
        my $no_job_error="";
        if ( $job_id_param ) {
            $no_job_error="Job ID \"$job_id_param\" not found for this device - Check parameter \"--id\"";
        } elsif ( $job_name_param ) {
            $no_job_error="Job Name \"$job_name_param\" not found for this device - Check parameter \"--name\"";
        } elsif ( $job_group_param && $hosts) {
            $no_job_error="No Jobs for group \"$job_group_param\" found for this device";
        }

        if ( $no_job_error ) {
            print_host_start_string("$ip","$hostname");

            print $no_job_error . " - skipping $ip\n" if $verbose;
            print $no_job_error . " - skipping $ip\n" if ! $verbose && $hosts;
            print_log ("NOREF","$no_job_error - skipping $ip");
            print STATUS "all:$ip\n";
            print_device_end_string();
            $error_detected=1;
        }
#        next;
        finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
    }

    print STATUS "all:$ip\n";

    print_host_start_string("$ip","$hostname");

    # check for disabled Jobs
    for my $other_job_id ( keys %other_jobs_to_execute ) {
        my $other_job_name=$other_jobs_to_execute{$other_job_id}[0];
        my $other_job_enabled=$other_jobs_to_execute{$other_job_id}[4] || 0;
        if ( $other_job_enabled != 1 ) {
            print_log("NOREF","$other_job_name: Job disabled - Job ignored (1)");
            delete $other_jobs_to_execute{$other_job_id};
        }
    }
    print_log("NOREF","CP 1") if $debug;
    for my $other_job_id ( keys %other_jobs_to_execute_copy_local ) {
        my $other_job_name=$other_jobs_to_execute_copy_local{$other_job_id}[0];
        my $other_job_enabled=$other_jobs_to_execute_copy_local{$other_job_id}[4] || 0;
        if ( $other_job_enabled != 1 ) {
            print_log("NOREF","$other_job_name: Job disabled - Job ignored (2)");
            delete $other_jobs_to_execute_copy_local{$other_job_id};
        }
    }
    print_log("NOREF","CP 2") if $debug;
    if ( keys(%other_jobs_to_execute) == 0 && keys(%other_jobs_to_execute_copy_local) == 0 ) {
        print_log("NOREF","No other Jobs: $ip") if $verbose;
        print STATUS "unchanged:$ip\n";
#        next;
        finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
    }

    print_log("NOREF","CP 3") if $debug;

    my $other_job_ids_list="";
    for my $other_job_id ( keys %other_jobs_to_execute ) {
        $other_job_ids_list.="," . $other_job_id;
    }
    $other_job_ids_list=~s/^,//;


    if ( ! exists $prompt_values{"$device_type_group_id"} ) {
        next_error("ERROR: Device type group ID not found");
        $error_detected=1;
        print_device_end_string();
        set_last_backup_date("$client_id","$host_id","3","$other_job_ids_list");
#        next;
        finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
    }

    $prompt=$prompt_values{$device_type_group_id}[0] || "__NO_UNPRIV_PROMPT__";
    $enable_prompt=$prompt_values{$device_type_group_id}[1];
    $prompt = "__NO_UNPRIV_PROMPT__" if $prompt eq $enable_prompt;

    my $username_expr=$login_atts{$device_type_group_id}[0];
    my $password_expr=$login_atts{$device_type_group_id}[1];
    my $enable_command=$enable_commands{$device_type_group_id}[0];
    $logout_command=$logout_commands{$device_type_group_id}[0];
    my $pager_disable_command=$pager_disable_commands{$device_type_group_id}[0] || "";
    my $unsaved_changes_expr=$unsaved_changes_expr{$device_type_group_id}[0] || "";
    my $pager_expr_pre=$pager_expr_hash{$device_type_group_id}[0] || "";
    my $loginConfirmationExpr_pre=$loginConfirmationExpr_hash{$device_type_group_id}[0] || "";
    my $preLoginConfirmationExpr_pre=$preLoginConfirmationExpr_hash{$device_type_group_id}[0] || "";
    my $showHostnameCommand=$showHostnameCommand_hash{$device_type_group_id}[0] || "";

    if ( $connection_proto ne "SSH" ) {
        if ( ! $login_pass ) {
            next_error("ERROR: No login pass found - skipping this device");
            $error_detected=1;
            print_device_end_string();
            set_last_backup_date("$client_id","$host_id","3","$other_job_ids_list");
#            next;
            finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
        }
    }

    print_log("NOREF","CP 4") if $debug;

    $cm_server_ip=$values_cm_server{$host_id}[1];
    $backup_proto=$values_cm_server{$host_id}[2];
    $cm_server_root=$values_cm_server{$host_id}[3];
    $cm_server_username=$values_cm_server{$host_id}[6] || "";
    $cm_server_password=$values_cm_server{$host_id}[7] || "";
    my $cm_server_pass_show="";
    $cm_server_pass_show="********" if $cm_server_password;

    if ( ! $cm_server_ip ) {
        next_error("ERROR: No Backup Server found - skipping this device");
        $error_detected=1;
        print_device_end_string();
        set_last_backup_date("$client_id","$host_id","3","$other_job_ids_list");
#        next;
        finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
    }

    print_log("NOREF","server username: $cm_server_username\nserver pass: $cm_server_pass_show\nbackup proto: $backup_proto\nserver root: $cm_server_root\nhost_id: $host_id") if $debug;

    ($prompt,$enable_prompt,$pager_expr,$loginConfirmationExpr,$preLoginConfirmationExpr)=replace_vars_prompt("$prompt","$enable_prompt","$user_name","$pager_expr_pre","$loginConfirmationExpr_pre","$preLoginConfirmationExpr_pre");

    print_log("NOREF","prompt: $prompt - enable prompt: $enable_prompt") if $verbose;
    print_log("NOREF","username expr: $username_expr - password expr: $password_expr") if $verbose;
    print_log("NOREF","unsaved_changes_expr: $unsaved_changes_expr - pager_expr: $pager_expr - loginConfirmationExpr_pre: $loginConfirmationExpr_pre - showHostnameCommand: $showHostnameCommand - preLoginConfirmationExpr_pre: $loginConfirmationExpr_pre") if $verbose && ( $unsaved_changes_expr || $pager_expr_pre || $loginConfirmationExpr_pre || $showHostnameCommand || $preLoginConfirmationExpr_pre );


    # Create backup dir if not exists
    my $cm_backup_dir_host=$cm_backup_dir . "/" . $host_id;
    if ( ! -d "$cm_backup_dir_host" ) {
        mkdir "$cm_backup_dir_host" or exit_error("ERROR: Can not create host backup directory $cm_backup_dir_host: $!","104");
        print_log("NOREF","Host backup dir created: $cm_backup_dir_host") if $verbose;
    }

    my $return_value;

    if ( $job_id_param ) {
        my $anz_other_jobs_to_execute=keys(%other_jobs_to_execute);
        my $anz_other_jobs_to_execute_local_copy=keys(%other_jobs_to_execute_copy_local);
        my $sum_all_jobs=$anz_other_jobs_to_execute+$anz_other_jobs_to_execute_local_copy;
        my $other_job_name="";
        my $other_job_enabled = 0;
        if ( $anz_other_jobs_to_execute > 0 ) {
            $other_job_name=$other_jobs_to_execute{$job_id_param}[0];
            $other_job_enabled=$other_jobs_to_execute{$job_id_param}[4] if $other_jobs_to_execute{$job_id_param};
        } else {
            $other_job_name=$other_jobs_to_execute_copy_local{$job_id_param}[0];
            $other_job_enabled=$other_jobs_to_execute_copy_local{$job_id_param}[4] if $other_jobs_to_execute_copy_local{$job_id_param};
        }
        if ( ! $other_job_name ) {
            print_log ("NOREF","Job not found (ID: $job_id_param) - Check Job ID - Job ignored");
#            next;
            finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
        }
        if ( $other_job_enabled != 1 && $sum_all_jobs == 1 ) {
            print_log ("NOREF","$other_job_name: Job disabled - Job ignored (3)");
#            next;
            finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
        }
    }

    # Login
    if ( keys(%other_jobs_to_execute) != 0 ) {
        set_error_expressions("set");
        $return_value=login("$connection_proto","$connection_proto_port","$username_expr","$password_expr","$login_pass","$prompt","$enable_prompt","$enable_command","$loginConfirmationExpr","$rsa_identity_file","$preLoginConfirmationExpr") || 0;
        if ( $return_value > 0 ) {
            $error_detected=1;
            close_connection();
            set_last_backup_date("$client_id","$host_id","3","$other_job_ids_list");
            my $jobs_not_executed;
            for my $other_job_id ( keys %other_jobs_to_execute ) {
                my $other_job_name=$other_jobs_to_execute{$other_job_id}[0];
                $jobs_not_executed.="$other_job_name ($other_job_id),";
            }
            $jobs_not_executed=~s/,$//;
            print_log("NOREF","The following Jobs could no be executed:\n$jobs_not_executed");
            
#            next;
            finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
        }
        $logged_in=1;
    }


    my $anz_jobs=scalar(keys %other_jobs_to_execute);
    my $anz_jobs_copy_local=scalar(keys %other_jobs_to_execute_copy_local);
    $anz_jobs = $anz_jobs + $anz_jobs_copy_local;
    print_log("NOREF","JOB COUNT: $anz_jobs") if $verbose;

    # execute commands
    for my $other_job_id ( keys %other_jobs_to_execute ) {
        
        #if found_enable_prompt_execute_commands ne 1 there is not enable prompt available - command before was executed with errors
        if ( $found_enable_prompt_execute_commands == 0 ) {

	    print_log("NOREF","ERROR: Did not detect an enable prompt after the last command - logging out and in again to obtain a clean session for the next Job");

            # logout and close connection
            logout("$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr");

            # Login again
            set_error_expressions("set");
            my $return_value=login("$connection_proto","$connection_proto_port","$username_expr","$password_expr","$login_pass","$prompt","$enable_prompt","$enable_command","$loginConfirmationExpr","$rsa_identity_file","$preLoginConfirmationExpr") || 0;
            if ( $return_value > 0 ) {
                $error_detected=1;
                close_connection();
                print_log("NOREF","ERROR: Can not login again - skipping remainig jobs for this device");
#                last;
                finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
            }
        }

        set_error_expressions("set");
        set_pager_expressions("set","$pager_expr");

        my $other_job_name=$other_jobs_to_execute{$other_job_id}[0];
        my $other_job_group=$other_jobs_to_execute{$other_job_id}[1] || "";
        my $other_job_type_id=$other_jobs_to_execute{$other_job_id}[3];
        my $other_job_enabled=$other_jobs_to_execute{$other_job_id}[4] || 0;
        my $valid_job=$backup_copy_commands{$device_type_group_id}{$other_job_name}{valid_job}->[0] || 0;

        if ( $valid_job == 1 ) {
            print_log ("NOREF","ERROR: Job $other_job_name INVALID - Job IGNORED - run check_xml_files.pl to check the XML file");
            $error_detected=1;
            next;
        }

        if ( $other_job_enabled != 1 ) {
            print_log ("NOREF","$other_job_name: Job disabled - Job ignored (4)");
            next;
        }

        print_log("NOREF","EXECUTING JOB: $other_job_name: ID: $other_job_id - Job Group ID: $other_job_group - Type ID: $other_job_type_id") if $verbose;

        my $commandTimeout=$backup_copy_commands{$device_type_group_id}{$other_job_name}{commandTimeout}->[0] || 92;
        print_log("NOREF","Using Timeout: $commandTimeout") if $commandTimeout != 92 && $verbose;

        my $cm_backup_file_name="";
        my $cm_backup_file;
        my $configExtension="";
        my $config_date="";
        my $config_dateFormat="";
        my $destConfigName="";
        my $localConfigName="";
        my $bckfile;

        my $command_type="";
        if ( $showHostnameCommand ) {
                $command_type="hostnameCommand";
                $return_value=execute_commands("$showHostnameCommand","$enable_prompt","$other_job_type_id","$host_id","$other_job_id","$pager_expr","$commandTimeout","0","$command_type") || 0;
                $command_type="";

                if ( $return_value > 0 ) {
                    last;
                }
        }

        if ( $other_job_type_id == 1 || $other_job_type_id == 2 || $other_job_type_id == 4 ) {

            # Create backup file

            $configExtension=$backup_copy_commands{$device_type_group_id}{$other_job_name}{configExtension}->[0] || "";
            $config_dateFormat=$backup_copy_commands{$device_type_group_id}{$other_job_name}{dateFormat}->[0] || "";
            $destConfigName=$backup_copy_commands{$device_type_group_id}{$other_job_name}{destConfigName}->[0] || "";
            $localConfigName=$backup_copy_commands{$device_type_group_id}{$other_job_name}{localConfigName}->[0] || "";
            $config_date=replace_date("$config_dateFormat") if $config_dateFormat;

            $cm_backup_file_name=get_backup_file_name("$host_id","$other_job_id","$other_job_type_id","$configExtension");
            # 201405301233_01_236_164.conf.tgz

            if ( $destConfigName ) {
                $bckfile=$destConfigName;
            } elsif ( $localConfigName ) {
                $bckfile=$localConfigName;
            } else {
                $bckfile=$cm_backup_file_name;
            } 


            $cm_backup_file=$cm_backup_dir_host . "/" . $cm_backup_file_name;


            if ( $other_job_type_id == 1 ) {
            # JOB TYPE: 1, copy_file

                if ( $backup_proto eq "tftp" ) {
                    #if backup proto = tftp, create file in tftproot dir
                    if ( $bckfile =~ /\*/ ) {
                        $error_detected=1;
                        close_connection();
                    print_log("NOREF","ERROR: WILDCARDS ARE NOT SUPPORTED WITHIN THE DEST_CONFIG_NAME FOR TFTP - JOB IGNORED");
    #                    last;
                        finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
                    }

                    $bckfile=get_bck_file_name("$cm_server_root","$bckfile","$other_job_type_id","$config_date");
                    # $job_type_id = 1 -> $cm_server_root/$bckfile
                    # $job_type_id = 2 -> /tmp/$bckfile

                    $return_value=create_backup_file("$client_id","$bckfile");
                    if ( $return_value > 0 ) {
                        $error_detected=1;
                        set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                        next;
                    }
                    print_log ("NOREF","EMPTY BACKUP FILE SUCCESSFULLY CREATED: $bckfile") if $verbose;
                }

                set_pager_expressions("unset");

            } elsif ( $other_job_type_id == 2 ) { 
                ### Fetch command output
                # Disable paging
                disable_paging("$pager_disable_command","$enable_prompt") if $pager_disable_command;
            }

        print_log("NOREF","CM_BACKUP_FILE NAME: $cm_backup_file") if $verbose;

        } elsif ( $other_job_type_id == 3 ) {
            if ( $upload_config_file ) {
                # $upload_config_file from commandline has full path, $upload_config_file from web-interface only the file name
                my $upload_config_file_full=$upload_config_file;
                $upload_config_file=~s/.*\///;
                my $ufile=$cm_server_root . '/' . $upload_config_file;
                if ( -e $ufile ) {
                    #run from web-interface - do nothing
                    # ip_do_job copies the file to server_root
                    print_log("NOREF","upload_config_file_server_root: $ufile") if $verbose;
                } else {
                    if ( ! -e $upload_config_file_full ) {
                        print_log ("NOREF","ERROR: file not found: $upload_config_file_full");
                    print "ERROR: file not found: $upload_config_file\n";
                        $error_detected=1;
                        set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                        next;
                    } else {
                        # copy upload file to server root
                        my $return_value=copy("$upload_config_file_full","$ufile");
                        if ( ! $return_value ) {
                            print_log("NOREF","ERROR: Failed to copy upload file to ServerRoot: copy $upload_config_file_full $ufile: $!");
                        print "ERROR: Failed to copy upload file to ServerRoot: copy $upload_config_file_full $ufile: $!\n";
                            set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                        }
                        print_log("NOREF","Successfully copied $upload_config_file_full to $ufile") if $verbose;
                    }
                }
            }
        }

        my $valid_job_parameter="diffConfigIgnore|configExtension|date|commandTimeout|jobType|localSourceFile|localSourceCommand|localSourceCommandPort|valid_job|destConfigName|dateFormat";
	

        for my $command_num ( sort keys %{$backup_copy_commands{$device_type_group_id}{$other_job_name}} ) {

            # process only commands and returns
            next if $command_num =~ /^($valid_job_parameter)/ || $command_num !~ /^\d+/;
#			$pm->finish($exit) if $command_num =~ /^($valid_job_parameter)/ || $command_num !~ /^\d+/;

            my $cmd=$backup_copy_commands{$device_type_group_id}{$other_job_name}{$command_num}->[0];
            my $return=$backup_copy_commands{$device_type_group_id}{$other_job_name}{$command_num}->[1];

            my $sleep="";
            ($return_value,$cmd,$return,$sleep)=replace_vars("$cmd","$return","$cm_server_ip","$cm_backup_file_name","$cm_server_username","$cm_server_password","$cm_server_root","$enable_prompt","$upload_config_file","$user_name","$config_date","$destConfigName","$localConfigName");

            if ( $return_value > 0 ) {
                print_log ("NOREF","ERROR FILE_CONTENT: Skipping Job") if $verbose;
                last;
            }

#            if ( $cmd =~ /\[\[IGNORE_ERRORS\]\]/ ) {
#                set_error_expressions("unset");
#                $cmd =~ s/\s*\[\[IGNORE_ERRORS\]\]//;
#                print_log ("NOREF","COMMAND IGNORES ERRORS: $cmd") if $verbose;
#            } else {
#                set_error_expressions("set");
#            }

            if ( $cmd =~ /\[\[IGNORE_ERRORS.*\]\]/ ) {
                $cmd =~ /\[\[IGNORE_ERRORS(.*)\]\]/;
                my $expr = $1;
                if ( $expr ) {
                        $expr =~ s/^,//;
                        my @expr = split(",",$expr);
                        set_error_expressions("set", \@expr);
                        print_log ("NOREF","COMMAND IGNORES ERROR \"@expr\": $cmd") if $verbose;
                } else {
                        set_error_expressions("unset");
                        print_log ("NOREF","COMMAND IGNORES ERRORS: $cmd") if $verbose;
                }
                $cmd =~ s/\s*\[\[IGNORE_ERRORS.*\]\]//;
            } else {
                set_error_expressions("set");
            }

            my $mask_cmd_log = 0;
            if ( $cmd =~ /\[\[SERVER_PASSWORD\]\]/ ) {
                $mask_cmd_log=1;
            }

            $return_value=execute_commands("$cmd","$return","$other_job_type_id","$host_id","$other_job_id","$pager_expr","$commandTimeout","$mask_cmd_log") || 0;

            if ( $return_value > 0 ) {
                last;
            }

            if ( $sleep ) {
                print_log("NOREF","SLEEPING $sleep SECONDS") if $verbose;
                sleep $sleep;
            }
        }


        if ( $backup_proto eq "tftp" && $other_job_type_id == 1 ) {
            # do nothing
        } else {
            $bckfile=get_bck_file_name("$cm_server_root","$bckfile","$other_job_type_id","$config_date");
            # $job_type_id = 1 -> $cm_server_root/$bckfile
            # $job_type_id = 2 -> /tmp/$bckfile
        }

        if ( $return_value > 0 ) {
            $error_detected=1;
            set_last_backup_date("$client_id","$host_id","3","$other_job_id");
            if ( $other_job_type_id == 1 || $other_job_type_id == 2 ) {
                if ( -z $bckfile ) {
                    unlink $bckfile or next_error("ERROR: can not remove $bckfile: $!");
                    print_log("NOREF","backup file deleted: $bckfile\n") if $verbose;
                    set_last_backup_date("$client_id","$host_id","2","$other_job_id");
                }
            }
            next;
        }


#        if ( $other_job_type_id == 1 || $other_job_type_id == 2 || $other_job_type_id == 4 ) {}
        if ( $other_job_type_id == 1 || $other_job_type_id == 2 ) {
            # check if configuration has changed
            
            $diffConfigIgnore=$backup_copy_commands{$device_type_group_id}{$other_job_name}{'diffConfigIgnore'}->[0] || "_NO_diffConfigIgnore_VALUE_";
            $return_value=compare_files("$client_id","$cm_backup_dir","$host_id","$ip","$bckfile","$other_job_id");
            if ( $return_value == 0 && $backup_always eq "no" ) {
                print_log("NOREF","$other_job_name: no changes - Skipping");
                print "$ip - No changes - Skipping\n" if $verbose;
                $error_detected=10;
                unlink $bckfile or next_error("ERROR: can not remove $bckfile: $!");
                print_log("NOREF","backup file deleted: $bckfile\n") if $verbose;
                print STATUS "unchanged:$ip\n";
                set_last_backup_date("$client_id","$host_id","0","$other_job_id");
                next;
            } elsif ( $return_value > 0 || ( $return_value == 0 && $backup_always eq "yes" )) {
                if ( $return_value == 999999 ) {
                    print_log("NOREF","$other_job_name: no old configurations found.");
                } elsif ( $return_value == 11 ) {
                    # bckfile or new_file do not exitst
                    $error_detected=1;
                    set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                    next;
                } else {
                    print_log("NOREF","$other_job_name: changes detected.");
                    print "Changes detected.\n" if $verbose;
                }

                $return_value=move_backup_file("$bckfile","$cm_backup_file","$other_job_id") || 0;
                my $conf_cmd_output_message="Configuration";
                $conf_cmd_output_message="Command Output" if $other_job_type_id == 2;
                $conf_cmd_output_message="File" if $other_job_type_id == 4;
                if ( $return_value == 1 ) {
                    $error_detected=1;
                    print_log("NOREF","ERROR: $conf_cmd_output_message NOT stored") if $verbose;
                    print "$conf_cmd_output_message NOT stored\n" if $verbose;
                    set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                    next;
                } elsif ( $return_value == 0 || $return_value == 2 ) {
                    set_last_backup_date("$client_id","$host_id","2","$other_job_id");
                    print_log("NOREF","$conf_cmd_output_message successfully stored: $cm_backup_file");
                    print "$conf_cmd_output_message successfully stored: $cm_backup_file\n" if $verbose;
                }

                print_log ("NOREF","DEBUG: File moved to backup directory: $bckfile -> $cm_backup_file") if $debug; 

                print STATUS "ok:$ip\n";
                set_last_backup_date("$client_id","$host_id","0","$other_job_id");
                next;
            } elsif ( $return_value == -1 ) {
                print_log("NOREF","ERROR: Can not compare files");
                print "ERROR: Can not compare files" if $verbose;
                $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
            }
	} else {
            # job_type_id=3 - Task
            print_log("NOREF","$other_job_name: job successfully finished");
            print "Job successfully finished\n" if $verbose;
            print STATUS "ok:$ip\n";
        }
    }

    # execute copy_local jobs
  
    for my $other_job_id ( keys %other_jobs_to_execute_copy_local ) {

        if ( $logged_in==1 && $logged_out==0 ) {
            logout("$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr");
        }

        my $other_job_name=$other_jobs_to_execute_copy_local{$other_job_id}[0];
        my $other_job_group=$other_jobs_to_execute_copy_local{$other_job_id}[1] || "";
        my $other_job_type_id=$other_jobs_to_execute_copy_local{$other_job_id}[3];
        my $other_job_enabled=$other_jobs_to_execute_copy_local{$other_job_id}[4] || 1;

        print_log("NOREF","Executing copy_local job: job_name: $other_job_name - job_group: $other_job_group - job_type_id: $other_job_type_id") if $verbose;

        my $localSourceFile=$backup_copy_commands{$device_type_group_id}{$other_job_name}{localSourceFile}->[0] || "";
        my $localSourceCommand=$backup_copy_commands{$device_type_group_id}{$other_job_name}{localSourceCommand}->[0] || "";
        my $localSourceCommandPort=$backup_copy_commands{$device_type_group_id}{$other_job_name}{localSourceCommandPort}->[0] || 80;
        if ( $localSourceCommand && $localSourceFile ) {
            print_log("NOREF","ERROR: Only one of the options localSourceFile or localSourceCommand allowed");
            print "ERROR: Only one of the options localSourceFile or localSourceCommand allowed" if $verbose;
            $error_detected=1;
            set_last_backup_date("$client_id","$host_id","3","$other_job_id");
            next;
        }

        my $cm_backup_file_name=get_backup_file_name("$host_id","$other_job_id","$other_job_type_id","") || "";
        # 201405301233_01_236_164.conf.tgz

        if ( $localSourceCommand && ! -x $localSourceCommand ) {
                print_log("NOREF","ERROR: localSourceCommand not executable: $localSourceCommand");
                print "ERROR: localSourceCommand not executable: $localSourceCommand\n" if $verbose;
                $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
        } elsif ( $localSourceCommand ) {
            #Execute localSourceFileCommand
            # Script execution OK: script returns name of localSourceFile (with full path)
            # NOT OK: script returns descriptive message containing the string "ERROR"
            print_log("NOREF","Found localSourceCommand: $localSourceCommand") if $verbose;
            eval {
                local $SIG{ALRM} = sub { die; };
                alarm(180); # timeout 3min 
                print_log("NOREF","Executing localSourceCommand: $localSourceCommand $ip $localSourceCommandPort $cm_backup_file_name $user_name XXXXXX") if $verbose;
                print "Executing localSourceCommand: $localSourceCommand $ip $localSourceCommandPort $cm_backup_file_name $user_name XXXXXX\n" if $verbose;
                $localSourceFile = `$localSourceCommand $ip $localSourceCommandPort $cm_backup_file_name $user_name $login_pass`;
                alarm(0); # turn off the alarm clock
            };
            if ($@) {
                print_log("NOREF","ERROR: Error executing localSourceCommand $localSourceCommand: $@");
                print "ERROR: Error executing localSourceCommand $localSourceCommand: $@\n" if $verbose;
                $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
            }

            $localSourceFile =~ s/\n\r\t\s//g;

            if ( $localSourceFile =~ /ERROR/ ) {
                    # If the run of localSourceCommand is successful it returns by definition the path to localSourceFile.
                    # If there occurs an error during the execution of the script, the sript must return a string containing
                    # the string "ERROR"
                    print_log("NOREF","ERROR: localSourceCommand $localSourceCommand returned an error: $localSourceFile");
                    print "ERROR: localSourceCommand $localSourceCommand returned an error: $localSourceFile\n" if $verbose;
                    $error_detected=1;
                    set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                    next;
            } else {
                    print_log("NOREF","localSourceCommand returned: $localSourceFile") if $verbose;
            }
        } elsif ( ! -e $localSourceFile ) {
                print_log("NOREF","ERROR: localSourceFile not found: $localSourceFile");
                print "ERROR: localSourceFile not found: $localSourceFile\n" if $verbose;
                $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
        } elsif ( -z $localSourceFile ) {
                print_log("NOREF","ERROR: localSourceFile has size of zero: $localSourceFile");
                print "ERROR: localSourceFile has size of zero: $localSourceFile\n" if $verbose;
                $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
        }

        my $cm_backup_file=$cm_backup_dir_host . "/" . $cm_backup_file_name;

        $return_value=compare_files("$client_id","$cm_backup_dir","$host_id","$ip","$localSourceFile","$other_job_id");
        if ( $return_value == 0 ) {
            print_log("NOREF","$other_job_name: no changes - Skipping");
            print "$ip - No changes - Skipping\n" if $verbose;
            $error_detected=10;
            unlink $localSourceFile or next_error("ERROR: can not remove $localSourceFile: $!");
            print_log("NOREF","local source file deleted: $localSourceFile\n") if $verbose;
            print STATUS "unchanged:$ip\n";
            set_last_backup_date("$client_id","$host_id","0","$other_job_id");
            next;
        } elsif ( $return_value > 0 || ( $return_value == 0 && $backup_always eq "yes" )) {
            if ( $return_value == 999999 ) {
                print_log("NOREF","$other_job_name: no old configurations found.");
            } elsif ( $return_value == 11 ) {
                # localSourceFile or new_file do not exitst
                 $error_detected=1;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
            } else {
                print_log("NOREF","$other_job_name: changes detected.");
                print "Changes detected.\n" if $verbose;
            }

            $return_value=move_backup_file("$localSourceFile","$cm_backup_file","$other_job_id") || 0;
            my $conf_cmd_output_message="Configuration";
            $conf_cmd_output_message="Command Output" if $other_job_type_id == 2;
            $conf_cmd_output_message="File" if $other_job_type_id == 4;
            if ( $return_value == 1 ) {
                $error_detected=1;
                print_log("NOREF","ERROR: $conf_cmd_output_message NOT stored") if $verbose;
                print "$conf_cmd_output_message NOT stored\n" if $verbose;
                set_last_backup_date("$client_id","$host_id","3","$other_job_id");
                next;
            } elsif ( $return_value == 0 || $return_value == 2 ) {
                set_last_backup_date("$client_id","$host_id","2","$other_job_id");
                print_log("NOREF","$conf_cmd_output_message successfully stored: $cm_backup_file");
                print "$conf_cmd_output_message successfully stored: $cm_backup_file\n" if $verbose;
            }

            print_log ("NOREF","DEBUG: File moved to backup directory: $localSourceFile -> $cm_backup_file") if $debug; 

            print STATUS "ok:$ip\n";
            set_last_backup_date("$client_id","$host_id","0","$other_job_id");
            next;
        } elsif ( $return_value == -1 ) {
            print_log("NOREF","ERROR: Can not compare files");
            print "ERROR: Can not compare files" if $verbose;
            $error_detected=1;
            set_last_backup_date("$client_id","$host_id","3","$other_job_id");
            next;
        }

    }

#    logout("$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr") if $logged_in==1 && $logged_out==0;

    if ( ! $error_detected ) {
        set_last_backup_date("$client_id","$host_id","0");
        print_device_end_string();
    }

    my $ufile = "";
    $ufile = $cm_server_root . '/' . $upload_config_file if $upload_config_file;
    if ( -e $ufile ) {
        unlink $ufile or print_log("NOREF","Warning: can not remove $ufile: $!") if $verbose;
        print_log("NOREF","upload file deleted: $ufile\n") if $verbose;
    }

    finish_child("$exit", "$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr", "$logged_in", "$logged_out");
	# child fork end
}

$pm->wait_all_children;


# reopen log and write client log to central log
open(LOG,">>$logfile") or die("can not open logfile $logfile: $!");
if ( $verbose ) {
#    open STDOUT, '>>', "$logfile_stdout" or print_log("NOREF","WARNING: Can not open STDOUT log: $logfile_stdout; $!");
	foreach my $fp (glob("$child_log_dir/*stdout.log")) {
	  open my $fh, "<", $fp or print_log("NOREF","can not open child log $fp: $!");
	  while (<$fh>) {
		print STDOUT $_;
	  }
	  close $fh;
	  unlink $fp or print_log("NOREF","can not DELETE $fp: $!");
	}
}

foreach my $fp (glob("$child_log_dir/*.log")) {
  open my $fh, "<", $fp or print_log("NOREF","can not open child log $fp: $!");
  while (<$fh>) {
    print LOG $_;
  }
  close $fh;
  unlink $fp or print_log("NOREF","can not DELETE $fp: $!");;
}

close STATUS;
open(STATUS,"<$status_file") or print_log("NOREF","Unable to open $status_file: $!");
while (<STATUS>) {
    chomp $_;
    $_ =~ s/(.*)://;
    if ( $1 =~ /all/ ) {
        push @all_hosts, $_;
    } elsif ( $1 =~ /ok/ ) {
        push @ok_hosts, $_;
    } elsif ( $1 =~ /unchanged/ ) {
        push @unchanged_hosts, $_;
    }
}
close STATUS;
unlink $status_file;

rmdir("$child_log_dir") or print_log("NOREF","can not DELETE $child_log_dir: $!");


my ($ok_host,$unchanged_hosts,$failed_hosts);
$ok_host=$unchanged_hosts=$failed_hosts="";
# Extract failed hosts
my @all_successful_hosts=();
push (@all_successful_hosts,@unchanged_hosts,@ok_hosts);

my %seen = ();
my @failed_hosts=();
@seen{@all_successful_hosts}=();
foreach my $item(@all_hosts) {
    push(@failed_hosts, $item) unless exists $seen{$item};
    $seen{$item}=1;
}

$anz_ok_hosts=scalar(@ok_hosts);
$anz_failed_hosts=scalar(@failed_hosts);

$failed_hosts=join(",",@failed_hosts) || "-";
$ok_host=join(",",@ok_hosts) || "-";
$unchanged_hosts=join(",",@unchanged_hosts) || "-";

if ( $enable_audit == 1 ) {
    my $audit_type=108;
    my $audit_class=20;
    my $update_type_audit=1;
    # asume that update_type_audit is "auto" if no "audit_user" argument is passed
    $update_type_audit = 2 if ! $audit_user_param;
    my $event="CHANGED: $ok_host; UNCHANGED: $unchanged_hosts; FAILED: $failed_hosts";
    insert_audit_auto("$client_id","$audit_class","$audit_type","$event","$update_type_audit","$audit_user_param");
}

my $execution_time=get_execution_time();

print_log_prepend("NOREF","############################\n\nJob execution details\n");
print_log_prepend("NOREF","Execution time: $execution_time\n\n");
print_log_prepend("NOREF","Configuration changed: $ok_host\n\nConfiguration unchanged: $unchanged_hosts\n\nBackup failed: $failed_hosts\n");
print_log_prepend("NOREF","Number of processed hosts: $anz_device_values\n");
print_log_prepend("NOREF","\nJob execution Summary:\n");


send_mail() if $mail;

close LOG;
close STDOUT if $verbose;

exit $error_detected;



###################################
######### Subroutines #############
###################################


sub execute_commands {
    my ($cmd,$return,$other_job_type_id,$host_id,$other_job_id,$pager_expr,$commandTimeout,$mask_cmd_log,$command_type) = @_;

    $command_type="" if ! $command_type;
    $found_enable_prompt_execute_commands=0;
    $last_return=$return;
    $commandTimeout=92 if ! $commandTimeout;

    my $cmd_log=$cmd;
    $cmd_log="******" if $mask_cmd_log;

    print_log("NOREF","EXECUTING: $cmd_log, EXPECTING: $return") if $verbose;

    my $clear_accum=$exp->clear_accum() || "";

    $r = $exp->send("$cmd\n");

    $r = $exp->expect($commandTimeout,
#TEST: WENN mehrere kommandos ausgefuehrt werden muss sichergestellt werden, dass vor dem naechsten kommando 
# ein enable prompt vorhanden ist und nicht zB tftp>
        [ -re => "Are you sure you want to continue connecting", \&send_string, "yes", "Problem storing key","exp_continue" ],
        [ -re => "Do you want to continue connecting", \&send_string, "yes", "Problem storing key","exp_continue" ],
        [ -re => $error_expr_command_1, \&print_error, "ERROR: Error expression 1 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_2, \&print_error, "ERROR: Error expression 2 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_3, \&print_error, "ERROR: Error expression 3 match (execute commands) - $error_expr_command_3","$ip","print_before" ],
        [ -re => $error_expr_command_4, \&print_error, "ERROR: Error expression 4 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_5, \&print_error, "ERROR: Error expression 5 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_6, \&print_error, "ERROR: Error expression 5 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_7, \&print_error, "ERROR: Error expression 7 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_8, \&print_error, "ERROR: Error expression 8 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_9, \&print_error, "ERROR: Error expression 9 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_10, \&print_error, "ERROR: Error expression 10 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_11, \&print_error, "ERROR: Error expression 11 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_12, \&print_error, "ERROR: Error expression 12 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_13, \&print_error, "ERROR: Error expression 13 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_14, \&print_error, "ERROR: Error expression 14 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_15, \&print_error, "ERROR: Error expression 15 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_16, \&print_error, "ERROR: Error expression 16 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_17, \&print_error, "ERROR: Error expression 17 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_18, \&print_error, "ERROR: Error expression 18 match (execute commands)","$ip","print_before" ],
        [ -re => $error_expr_command_19, \&print_error, "ERROR: Error expression 19 match (execute commands)","$ip","print_before" ],
        [ -re => $pager_expr, \&send_string,"","","exp_continue"],
        [ -re => $return, \&print_log, "GOT RETURN: '$return'","verbose","set_accum" ],
        [ 'timeout', \&print_error, "ERROR: Timeout executing '$cmd_log'","$ip","print_before" ],
        [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],
    );

    my $match=$exp->match() || "";
    print_log("NOREF","MATCH (execute commands): $match") if $verbose;

    if ( $next_error_set == 1 ) {
        $next_error_set = 0;
        return 1;
    }

    unless ( defined $r ) {
        print_error("NOREF","ERROR: Error executing command: $cmd_log","$ip","print_before");
        return 1;
    }

    my $after=$exp->after() || "";

    if ( $after =~ /$enable_prompt/ || $match =~ /$enable_prompt/ ) {
        $found_enable_prompt_execute_commands=1;
    }

    if ( $command_type eq "hostnameCommand" ) {
      my $before=$exp->before() || "";
      $hostname_from_command = $before;
      $hostname_from_command =~ s/${cmd}//;
      $hostname_from_command =~ s/^\s*//;
      $hostname_from_command =~ s/^\r*\n**//;
      $hostname_from_command =~ s/\r*\n**$//;
      print_log("NOREF","HOSTNAME EXTRUCTION: COMMAND: $cmd - BEFORE: $before - AFTER: $after - HOSTNAME: $hostname_from_command") if $verbose;
    }

    if ( $other_job_type_id == 2 ) {
    # JOB TYPE: FETCH COMMAND OUTPUT
         write_output_to_file("$host_id","$other_job_id");
    }

    return 0;
}



sub login {
    my ($connection_proto,$connection_proto_port,$username_expr,$password_expr,$login_pass,$prompt,$enable_prompt,$enable_command,$loginConfirmationExpr, $rsa_identity_file, $preLoginConfirmationExpr) = @_;

    $login_pass="" if ! $login_pass;

    # Start Expect

    my $command;
    my @command_params;
    if ( $connection_proto eq "telnet" ) {
        $connection_proto_port=23 if ! $connection_proto_port;
        $command="/usr/bin/telnet";
        $command_params[0]="$ip";
        if ( $connection_proto_port ne "23" ) {
            $command_params[1]="$connection_proto_port";
        }
    } elsif ( $connection_proto eq "SSH" ) {
        $connection_proto_port=22 if ! $connection_proto_port;
        $command="/usr/bin/ssh";
        $command_params[0]="$user_name\@$ip";
        if ( $connection_proto_port ne "22" ) {
            $command_params[1]="-p $connection_proto_port";
        }
        if ( $rsa_identity_file ) {
            $command_params[2]="-i $rsa_identity_file";
        }
    } else {
        print_error("NOREF","ERROR: No connection protocol found ****","$ip");
        return 1;
    }

    $exp = new Expect;
    my $command_param_string = join(" ", @command_params);
    print_log("NOREF","Trying to login with: $command $command_param_string") if $verbose;
    $exp->spawn($command, @command_params) or exit_error("ERROR: Cannot spawn $command: $!","108");
    sleep 1;
    $exp->debug(1) if $debug;
    $exp->log_stdout(0);

    if ( $verbose ) {
        $exp->log_stdout(1);
    }
    print LOG "PRELO: $preLoginConfirmationExpr\n";

    if ( $connection_proto eq "telnet" ) {
        $r = $exp->expect($timeout,
            [ -re => $preLoginConfirmationExpr, \&send_string, "", "Confirming preLogin \"$preLoginConfirmationExpr\" with ENTER", "exp_continue"],
            [ -re => $error_expr_login_execeptions, \&print_log,"LOGIN SUCCESSFUL - error expression exeception match","verbose" ],
            [ -re => $error_expr_login, \&print_error, "ERROR: Login failed: Error expression match","$ip","print_before" ],
            [ -re => $username_expr, \&send_username, $user_name ],
            [ -re => $password_expr, \&send_pass, $login_pass ],
            [ -re => $loginConfirmationExpr, \&send_string, "\n", "Confirming \"$loginConfirmationExpr\" with ENTER", "exp_continue"],
            [ -re => $prompt, \&enable, $password_expr,$enable_pass,$enable_prompt,$enable_command ],
            [ -re => $enable_prompt, \&print_log,"LOGIN SUCCESSFUL - Found 'enable' prompt: $enable_prompt","verbose" ],
            [ 'timeout', \&print_error, "ERROR: Login: Timeout","$ip","print_before"],
            [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],
        );
    } elsif ( $connection_proto eq "SSH" ) {
        $r = $exp->expect($timeout,
#            [ -re => $error_expr_login_execeptions, \&print_log,"LOGIN SUCCESSFUL - error expression exeception match","verbose" ],
            [ -re => $preLoginConfirmationExpr, \&send_string, "\n", "Confirming \"$preLoginConfirmationExpr\" with ENTER", "exp_continue"],
            [ -re => "refused|Connection closed by", \&print_error, "ERROR: Connecton refused","$ip","print_before" ],
            [ -re => "unreachable", \&print_error, "ERROR: Device unreachable","$ip","print_before" ],
            [ -re => "Are you sure you want to continue connecting", \&send_string, "yes", "Problem storing key","exp_continue" ],
            [ -re => "Do you want to continue connecting", \&send_string, "yes", "Problem storing key","exp_continue" ], #openwrt
            [ -re => "Host key not found |The authenticity of host .* be established", \&send_string, "yes", "Trying to added host key to the list of known hosts: $ip","exp_continue" ],
            [ -re => "HOST IDENTIFICATION HAS CHANGED.*yes/no", \&send_string_and_next, "no", "**** ERROR: HOST IDENTIFICATION HAS CHANGED - update SSH known_hosts" ],
            [ -re => "HOST IDENTIFICATION HAS CHANGED", \&print_error, "ERROR: HOST IDENTIFICATION HAS CHANGED - update SSH known_hosts","$ip","print_before" ],
            [ -re => "No address associated", \&print_error, "ERROR: No address associated with this host","$ip","print_before" ],
            [ -re => "Permission denied", \&print_error, "ERROR: Login failed: Username/Password incorrect ","$ip","print_before" ],
            [ -re => $username_expr, \&send_username, "$user_name" ],
            [ -re => $password_expr, \&send_pass, "$login_pass" ],

            # patch for AVAYA Ethernet Routing Switch
            [ -re => "Ethernet Routing Switch", \&send_string, "\cY", "Found string: 'Ethernet Routing Switch' - Sending CTRL-Y", "exp_continue"],
            [ -re => "Press ENTER to continue", \&send_string, "\n", "Found string 'Press ENTER to continue' - Sending newline", "exp_continue"],

            [ -re => "Press any key to continue", \&send_string ],
            [ -re => $loginConfirmationExpr, \&send_string, "", "Confirming \"$loginConfirmationExpr\" with ENTER", "exp_continue"],
            [ -re => $prompt, \&enable, $password_expr,$enable_pass,$enable_prompt,$enable_command ],
            [ -re => $enable_prompt, \&print_log,"LOGIN SUCCESSFUL - Found 'enable' prompt: $enable_prompt","verbose" ],
            [ 'timeout', \&print_error, "Login: Timeout","$ip","print_before" ],
            [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],
        );
    }

    my $match=$exp->match() || "";
    print_log("NOREF","MATCH LOGIN: $match") if $verbose;

    if ( $next_error_set == 1 ) {
        $next_error_set = 0;
        return 1;
    }

    unless ( defined $r ) {
        print_error("NOREF","ERROR: login failed (1) ****","$ip","print_before");
        return 1;
    }

    return 0;
}

sub send_username {
    my ($self,$user_name,$password_expr) = @_;

    my $match=$exp->match();

    $self->send("$user_name\n");
    print_log("NOREF","DEBUG: USERNAME SEND - MATCH: $match") if $debug;

    #avoid that $username_expr matches again
    my $clear_accum=$exp->clear_accum();
    print_log("NOREF","CLEAR ACCUM 'send_username': $clear_accum") if $debug==3;

    my $exp_continue="";
    $exp_continue="exp_continue" if ! $username_send;

    $username_send=1;

    return $exp_continue;

}

sub send_pass {
    my ($self,$password) = @_;

    $password="" if ! $password;

    my $match=$self->match();

    $self->send("$password\n");
    print_log("NOREF","PASSWORD SEND - MATCH: $match") if $verbose;

    #avoid that $username_expr matches again
    my $clear_accum=$exp->clear_accum();
    print_log("NOREF","CLEAR ACCUM 'send_pass': $clear_accum") if $debug==3;

    $login_pass_send=1;

    return exp_continue;
}

sub send_string {
    my ($self,$string,$message,$exp_continue) = @_;
    $string="" if ! $string;
    $exp_continue="" if ! $exp_continue;
    $self->send_slow(0, "$string\n");
    print_log("NOREF","SEND STRING: $string - $message") if $verbose;

    if ( $exp_continue ) {
        return exp_continue;
    }
}

sub send_string_and_next {
    my ($self,$string,$message) = @_;
    $string="" if ! $string;
    $self->send_slow(0, "$string\n");
    print_error("NOREF","$string - $message") if $verbose;
}


sub enable {
    my ($self,$password_expr,$enable_pass,$enable_prompt,$enable_command) = @_;

    $self->send_slow(0, "$enable_command\n");

    print_log("NOREF","VERBOSE: 'enable' pass send") if $verbose;

    $r = $self->expect($timeout,
#        [ -re => $error_expr, \&print_error, "ERROR: Error expression match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_1, \&print_error, "ERROR: Error expression 1 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_2, \&print_error, "ERROR: Error expression 2 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_3, \&print_error, "ERROR: Error expression 3 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_4, \&print_error, "ERROR: Error expression 4 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_5, \&print_error, "ERROR: Error expression 5 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_6, \&print_error, "ERROR: Error expression 5 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_7, \&print_error, "ERROR: Error expression 7 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_8, \&print_error, "ERROR: Error expression 8 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_9, \&print_error, "ERROR: Error expression 9 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_10, \&print_error, "ERROR: Error expression 10 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_11, \&print_error, "ERROR: Error expression 11 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_12, \&print_error, "ERROR: Error expression 12 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_13, \&print_error, "ERROR: Error expression 13 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_14, \&print_error, "ERROR: Error expression 14 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_15, \&print_error, "ERROR: Error expression 15 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_15, \&print_error, "ERROR: Error expression 16 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_17, \&print_error, "ERROR: Error expression 17 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_18, \&print_error, "ERROR: Error expression 18 match (enable)","$ip","print_before" ],
        [ -re => $error_expr_command_19, \&print_error, "ERROR: Error expression 19 match (enable)","$ip","print_before" ],
        [ -re => "Press ENTER to continue", \&send_string, "\n", "sub enable: Found string 'Press ENTER to continue' - Sending newline", "exp_continue"],
        [ -re => $password_expr, \&send_pass, $enable_pass,"exp_continue" ],
        [ -re => $enable_prompt, \&print_log, "FOUND ENABLE PROMPT: $enable_prompt","verbose" ],
        [ 'timeout', \&print_error, "ERROR: Timeout","$ip","print_before" ],
        [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],
    );

    print_log("NOREF","Enable MATCH: " . $exp->match()) if $debug;

    if ( $next_error_set == 1 ) {
        $next_error_set = 0;
        return 1;
    }

    unless ( defined $r ) {
        print_error("NOREF","ERROR: Can't access privileged mode","$ip","print_before");
        $global_error="1";
        return 1;
    }

    return 0;
}

sub disable_paging {
    my ($pager_disable_command,$enable_prompt) = @_;

    print_log("NOREF","Disableing paging: $pager_disable_command") if $verbose;

    $exp->send("$pager_disable_command\n");

    $r = $exp->expect($timeout,
        [ -re => $error_expr_command_1, \&print_error, "ERROR: Error expression 1 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_2, \&print_error, "ERROR: Error expression 2 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_3, \&print_error, "ERROR: Error expression 3 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_4, \&print_error, "ERROR: Error expression 4 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_5, \&print_error, "ERROR: Error expression 5 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_6, \&print_error, "ERROR: Error expression 5 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_7, \&print_error, "ERROR: Error expression 7 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_8, \&print_error, "ERROR: Error expression 8 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_9, \&print_error, "ERROR: Error expression 9 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_10, \&print_error, "ERROR: Error expression 10 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_11, \&print_error, "ERROR: Error expression 11 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_12, \&print_error, "ERROR: Error expression 12 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_13, \&print_error, "ERROR: Error expression 13 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_14, \&print_error, "ERROR: Error expression 14 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_15, \&print_error, "ERROR: Error expression 15 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_16, \&print_error, "ERROR: Error expression 16 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_17, \&print_error, "ERROR: Error expression 17 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_18, \&print_error, "ERROR: Error expression 18 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $error_expr_command_19, \&print_error, "ERROR: Error expression 19 match (disable paging) - Paging not disabled","verbose" ],
        [ -re => $enable_prompt, \&print_log, "disable paging: FOUND ENABLE PROMPT: $enable_prompt","verbose" ],
        [ 'timeout', \&print_error, "ERROR: Timeout","$ip","print_before" ],
        [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],
    );

    print_log("NOREF","disable paging MATCH: " . $exp->match()) if $verbose;

    unless ( defined $r ) {
        print_log("NOREF","ERROR: Paging not disabled","verbose");
    }

    return 0;
}

sub print_log {
    my ($ref,$error_message,$loglevel,$set_accum) = @_;

    $set_accum="" if ! $set_accum;

    my $output_before="";
    my $output_after="";
    if ( $exp ) {
        $output_before = $exp->before;
        $output_after = $exp->after;
    }

    $loglevel="" if ! $loglevel;

    if ( $loglevel eq "verbose" && ( $verbose || $debug ) ) {
        print LOG "\n$error_message\n";
    } elsif ( $loglevel eq "debug" && $debug ) {
        print LOG "\n$error_message\n";
    } elsif ( ! $loglevel ) {
        print LOG "\n$error_message\n";
    }
}

sub print_log_prepend {
    my ($ref,$message) = @_;
    open(LOG,"<","$logfile") or die("can not open logfile $logfile: $!");
    my @m = <LOG>;
    close(LOG);
    open(LOG,">","$logfile");
    print LOG "$message\n";
    print LOG @m;
    close(LOG);
}

sub print_error {
    my ($ref,$error_message,$ip,$before) = @_;

    $ip="" if ! $ip;


    my ($output_before, $output_after, $output_match);
    $output_before=$output_match=$output_after = "";
    if ( $exp ) {
        $output_before = $exp->before() || "";
        $output_after = $exp->after() || "";
        $output_match = $exp->match() || "";
    }

    if ( $exp ) {
        print_log("NOREF","$error_message");
        if ( $before ) {
            print_log("NOREF","\n#### OUT BEFORE:\n$output_before\n####\n#### MATCH:\n$output_match\n####\n#### OUT AFTER:\n$output_after\n####");
            print "#### ERROR:\n$error_message\n" if $verbose;
            print "#### OUT BEFORE:\n$output_before\n####\n" if $verbose;
            print "#### OUT MATCH:\n$output_match\n####\n" if $verbose;
            print "#### OUT AFTER:\n$output_after\n####\n" if $verbose;
        } else {
            print_log("NOREF","$error_message");
            print "$error_message\n" if $verbose;
        }
    } else {
        print_log("NOREF","$error_message");
        print_device_end_string();
    }

    if (( $backup_proto =~ /^.ftp$/ && ( $output_after =~ /ftp>.?$/ || $output_match =~ /ftp>.?$/ ))) {
        exit_tftp_prompt("print_error");
    }

    if ( $exp ) {
        $output_after = $exp->after() || "";
        $output_match = $exp->match() || "";
    }

    if ( $output_after =~ /$enable_prompt/ || $output_match =~ /$enable_prompt/ ) {
        $found_enable_prompt_execute_commands=1;
    }

    $next_error_set=1;

    return;
}


sub exit_error {
    my ($error_message,$exit) = @_;

    $exit=1 if ! $exit;

    print_log("NOREF","$error_message");
    print_log("NOREF","exiting");
    print "$error_message\n";
    print "exiting ($exit)\n";

    exit $exit;
}

sub next_error {
    my ($error_message) = @_;

    print "$error_message\n" if $verbose;
    print_log("NOREF","$error_message");

    $next_error_set=1;
}

sub get_backup_file_name {
    my ($host_id,$job_id,$job_type_id,$configExtension) = @_;

    $configExtension="" if ! $configExtension;
    $configExtension=~s/^\.+//;


    my $ext="";
    if ( $job_type_id == 1 || $job_type_id == 4 ) {
        $ext=".conf";
    } elsif ( $job_type_id == 2 ) {
        $ext=".txt";
    }
    $ext.="." . $configExtension if $configExtension;

    my ( $cm_backup_file,$cm_backup_file_name);
    if ( ! $backup_file_name_param ) {
        my $backup_file_serial=get_file_serial("$job_id");
        $cm_backup_file_name=$date_file . "_" . $backup_file_serial . "_" . $host_id . "_" . $job_id . $ext;
    } else {
        $cm_backup_file_name=$backup_file_name_param;
        $cm_backup_file_name.="." . $configExtension if $configExtension;
    }

    return $cm_backup_file_name;
}

sub create_backup_file {
    my ($client_id,$bckfile) = @_;

    print_log ("NOREF","Backup proto: $backup_proto") if $verbose;

    # create backup file (TFTP may not allow to create files)
    if ( $backup_proto eq "tftp" ) {
        open(BCKFILE,">$bckfile") or print_error("NOREF","ERROR: Failed to create BCKFILE $bckfile: $!");
        close BCKFILE;

        if ( ! -e $bckfile ) {
            print_error("NOREF","ERROR: Failed to create BCKFILE: $bckfile");  
            return 1;
        }
        chmod 0777, $bckfile or print_log("NOREF","WARNING: chmod 0777 $bckfile failed");
    }

    print_log ("NOREF","backup file created: $bckfile") if $verbose;

    return 0;
}



sub move_backup_file {
    my ($old,$new,$other_job_id) = @_;

    # Check if file is empty
    if ( -z $old ) {
        print_error("NOREF","ERROR: Failed to fetch config. Empty file: $old");    
        set_last_backup_date("$client_id","$host_id","3","$other_job_id");
        unlink $old;
        return 1;
    }


    my $return_value=copy("$old","$new");
    if ( ! $return_value ) {
        print_error("NOREF","ERROR: Failed to copy fetched configuration to the backup directory: copy $old to $new: $!");
        set_last_backup_date("$client_id","$host_id","3");
        return 1;
    }

    print_log("NOREF","successfully copied backup file to backup directory: copy $old -> $new\n") if $verbose;

    $return_value=unlink $old;
    if ( ! $return_value ) {
        print_error("NOREF","ERROR: Failed to delete fetched configuration from server root directory: rm $old: $!");
        set_last_backup_date("$client_id","$host_id","2");

        return 2;
    }

    print_log("NOREF","successfully deleted fetched configuration from server root directory: rm $old\n") if $verbose;

    return 0;
}


sub get_host_id_from_job_id {
    my ( $client_id,$job_id ) = @_;
    my $host_id;
    my $dbh = mysql_connection();
    my $qjob_id = $dbh->quote( $job_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT INET_NTOA(h.ip) FROM host h, device_jobs d WHERE d.host_id=h.id AND d.id=$qjob_id AND h.client_id = $qclient_id"
        ) or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "$DBI::errstr";  
    $host_id = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $host_id;
}


sub get_device_values {
    my ( $client_id, $host_ids ) = @_;

    $host_ids="" if ! $host_ids;
    my %values;
    my $ip_ref;
    my $dbh = mysql_connection();

    my $qclient_id = $dbh->quote( $client_id );
    

    my $or_host_id_expr_v4="";
    my $or_host_id_expr_v6="";
    my $or_host_id_expr="";
    if ( $host_ids =~ /,/ ) {
        my @host_ids=();
        @host_ids=split(",",$host_ids);
        foreach my $id(@host_ids) {
            my $valid_ip=check_valid_ip("$id") || "";
            print "'$id': INVALID IP - IGNORED\n" if ! $valid_ip;
            if ( $or_host_id_expr_v4 && $id =~ /^\d{1,3}\.\d{1,3}/ ) {
                $or_host_id_expr_v4.="OR h.ip = INET_ATON('$id')";
            } elsif ( $id =~ /^\d{1,3}\.\d{1,3}/ ) {
                $or_host_id_expr_v4="h.ip = INET_ATON('$id')";
            } elsif ( $or_host_id_expr_v6 && $id !~ /^\d{1,3}\.\d{1,3}/ ) {
                my $ip_int=ip_to_int("$client_id","$id","v6");
                $or_host_id_expr_v6.="OR h.ip = $ip_int)";
            } elsif ( $or_host_id_expr_v6 && $id !~ /^\d{1,3}\.\d{1,3}/ ) {
                my $ip_int=ip_to_int("$client_id","$id","v6");
                $or_host_id_expr_v6="h.ip = $ip_int";
            }
        }
    } elsif ( $host_ids ) {
        my $valid_ip=check_valid_ip("$host_ids") || "";
        print_log("NOREF","'$host_ids': INVALID IP - IGNORED") if ! $valid_ip;
        if ( $host_ids =~ /^\d{1,3}\.\d{1,3}/ ) {
            $or_host_id_expr_v4="h.ip = INET_ATON('$host_ids')";
        } else {
            my $ip_int=ip_to_int("$client_id","$host_ids","v6");
            $or_host_id_expr_v6="h.ip = $ip_int";
        }
    }

    $or_host_id_expr.= " AND (" . $or_host_id_expr_v4 . ")" if $or_host_id_expr_v4;
    $or_host_id_expr.= " AND (" . $or_host_id_expr_v6 . ")" if $or_host_id_expr_v6;

    my $sth = $dbh->prepare("SELECT dc.id,dc.host_id,dc.device_type_group_id,dc.device_user_group_id,dc.user_name,dc.login_pass,dc.enable_pass,dc.description,dc.connection_proto,dc.connection_proto_args,dc.cm_server_id,dc.client_id,dc.save_config_changes,ug.name AS name_ug,ug.user_name AS user_name_ug,ug.login_pass AS login_pass_ug,ug.enable_pass AS enable_pass_ug,h.ip,INET_NTOA(h.ip),h.ip_version,h.hostname, ug.rsa_identity_file FROM device_cm_config dc, device_user_groups ug, host h WHERE dc.client_id=$qclient_id AND dc.device_user_group_id=ug.id AND dc.host_id=h.id AND dc.host_id IN ( select cce.host_id from custom_host_column_entries cce where cce.pc_id = ( select column_type_id FROM custom_host_columns WHERE name='CM' ) AND cce.entry='enabled' $or_host_id_expr)"
        ) or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "$DBI::errstr";  
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{id} || "";
        my $host_id = $ip_ref->{host_id} || "";
        my $device_type_group_id = $ip_ref->{device_type_group_id} || "";
        my $device_user_group_id = $ip_ref->{device_user_group_id} || "";
        my $user_name = $ip_ref->{user_name} || "";
        my $login_pass = $ip_ref->{login_pass} || "";
        my $enable_pass = $ip_ref->{enable_pass} || "";
        my $description = $ip_ref->{description} || "";
        my $connection_proto = $ip_ref->{connection_proto} || "";
        my $connection_proto_port = $ip_ref->{connection_proto_args} || "";
        my $cm_server_id = $ip_ref->{cm_server_id} || "";
        my $user_name_ug = $ip_ref->{user_name_ug} || "";
        my $login_pass_ug = $ip_ref->{login_pass_ug} || "";
        my $enable_pass_ug = $ip_ref->{enable_pass_ug} || "";
        my $ip_version = $ip_ref->{ip_version} || "";
        my $save_config_changes = $ip_ref->{save_config_changes} || "";
        my $ip_int = $ip_ref->{ip} || "";
        my $ip;
        if ( $ip_version eq "v4" ) {
            $ip=$ip_ref->{'INET_NTOA(h.ip)'};
        } else {
            $ip = int_to_ip("$client_id","$ip_int","$ip_version");
        }
        my $hostname=$ip_ref->{hostname} || "";
        my $rsa_identity_file=$ip_ref->{rsa_identity_file} || "";

        if ( $device_user_group_id ) {
                push @{$values{$host_id}},"$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$description","$connection_proto","$cm_server_id","$user_name_ug","$login_pass_ug","$enable_pass_ug","$ip","$ip_int","$save_config_changes","$hostname","$connection_proto_port","$rsa_identity_file";
        }
    }

    $sth = $dbh->prepare("SELECT dc.id,dc.host_id,dc.device_type_group_id,dc.device_user_group_id,dc.user_name,dc.login_pass,dc.enable_pass,dc.description,dc.connection_proto,dc.connection_proto_args,dc.cm_server_id,dc.client_id,dc.save_config_changes, h.ip,INET_NTOA(h.ip),h.ip_version,h.hostname, ug.rsa_identity_file FROM device_cm_config dc, host h, device_user_groups ug WHERE dc.client_id=$qclient_id AND dc.host_id=h.id AND dc.host_id IN ( select cce.host_id from custom_host_column_entries cce where cce.pc_id = ( select column_type_id FROM custom_host_columns WHERE name='CM' ) AND cce.entry='enabled' $or_host_id_expr)"
        ) or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "$DBI::errstr";  
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{id} || "";
        my $host_id = $ip_ref->{host_id} || "";
        my $device_type_group_id = $ip_ref->{device_type_group_id} || "";
        my $device_user_group_id = $ip_ref->{device_user_group_id} || "";
        my $user_name = $ip_ref->{user_name} || "";
        my $login_pass = $ip_ref->{login_pass} || "";
        my $enable_pass = $ip_ref->{enable_pass} || "";
        my $description = $ip_ref->{description} || "";
        my $connection_proto = $ip_ref->{connection_proto} || "";
        my $connection_proto_port = $ip_ref->{connection_proto_args} || "";
        my $cm_server_id = $ip_ref->{cm_server_id} || "";
        my $user_name_ug = "";
        my $login_pass_ug = "";
        my $enable_pass_ug = "";
        my $ip_version = $ip_ref->{ip_version} || "";
        my $save_config_changes = $ip_ref->{save_config_changes} || "";
        my $ip_int = $ip_ref->{ip} || "";
        my $ip;
        if ( $ip_version eq "v4" ) {
            $ip=$ip_ref->{'INET_NTOA(h.ip)'};
        } else {
            $ip = int_to_ip("$client_id","$ip_int","$ip_version");
        }
        my $hostname=$ip_ref->{hostname} || "";
        my $rsa_identity_file=$ip_ref->{rsa_identity_file} || "";

	if ( ! $device_user_group_id ) {
		push @{$values{$host_id}},"$device_type_group_id","$device_user_group_id","$user_name","$login_pass","$enable_pass","$description","$connection_proto","$cm_server_id","$user_name_ug","$login_pass_ug","$enable_pass_ug","$ip","$ip_int","$save_config_changes","$hostname","$connection_proto_port";
        }
    }

    return %values;
}

sub mysql_connection {
    my $dbh = DBI->connect("DBI:mysql:$sid_gestioip:$bbdd_host_gestioip:$bbdd_port_gestioip",$user_gestioip,$pass_gestioip) or

    die "Cannot connect: ". $DBI::errstr;
    return $dbh;
}

sub get_params {
    my ($conf) = @_;

    if ( ! $conf ) {
        my $dir = $Bin;

        $dir =~ /^(.*)\/bin/;
        my $base_dir=$1;

        my $config_name="ip_update_gestioip.conf";

        if ( ! -r "${base_dir}/etc/${config_name}" ) {
            exit_error("$dir/$config_name\" doesn't exist","105");
        }

        $conf = $base_dir . "/etc/" . $config_name;
    }



    my %params;

    open(VARS,"<$conf") or exit_error("Can not open $conf: $!","110");
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

    return %params;
}

sub get_global_config {
    my ($client_id) = @_;
    my @values_config;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $sth = $dbh->prepare("SELECT version, default_client_id, confirmation, mib_dir, vendor_mib_dirs, ipv4_only, as_enabled, leased_line_enabled, configuration_management_enabled, cm_backup_dir, cm_licence_key, cm_log_dir, cm_xml_dir FROM global_config");
    $sth->execute() or die "$DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_arrayref ) {
        push @values_config, [ @$ip_ref ];
    }
    $dbh->disconnect;
    return @values_config;
}

sub get_configs_host {
    my ( $client_id,$cm_backup_dir,$host_id,$job_id ) = @_;
    my @configs=();
    my $return_check=0;
    my $dir=$cm_backup_dir . "/" .  $host_id;

    opendir (DIR, $dir) or $return_check=get_return("ERROR: Can't open configuration backup file directory \"$dir\": $!");
    return if $return_check == 1;
    my $j=0;
    while (my $file = readdir(DIR)) {
        next if $file eq "." || $file eq "..";
        push (@configs,"$file") if $file =~ /^(\d{12})_(\d{2,3})_(\d+)_${job_id}\./;
    }

    @configs = reverse sort @configs;

    return @configs;
}

sub int_to_ip {
    my ($client_id,$ip_int,$ip_version)=@_;
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

sub get_file_serial {
    my ($job_id)=@_;
    # create serial number
    my @configs=get_configs_host("$client_id","$cm_backup_dir","$host_id","$job_id");
    my $last_serial="";
    my @old_serials=();
    my $backup_file_serial="0";
    if ( scalar @configs > 0 ) {
        foreach (@configs) {
            my $config_name=$_;
            next if $config_name !~ /^(\d{12})_(\d{2,3})_(\d+)_${job_id}\./;
#            $config_name =~ /^(\d{12})_(\d{2})_(\d+)[._]./;
            $config_name =~ /^(\d{12})_(\d{2,3})_(\d+)_${job_id}\./;
            my $date=$1 || "";
            my $serial=$2 || "";
            $date =~ /^(\d{8})/;
            $date=$1;
            $date_file =~ /^(\d{8})/;
            my $date_file_check = $1;
            next if $date != $date_file_check;
            push(@old_serials,$serial)
        }

        foreach (@old_serials) {
            $_ =~ s/^0//;
            $backup_file_serial=$_ if $_ > $backup_file_serial;
        }
    }

    $backup_file_serial++;
    $backup_file_serial="0" . $backup_file_serial if $backup_file_serial !~ /^\d\d$/;

    return $backup_file_serial;
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


sub check_cm_licence {
    my ( $client_id ) = @_;

    my $return_string;

    my $licence_key = "";
	
	if ( -r $cm_conf_file ) {
		open(CM_CONF, "<$cm_conf_file");
		while (<CM_CONF>) {
			if ( $_ =~ /^cm_license_key/ ) {
				$_ =~ /^cm_license_key=(.*)$/;
				$licence_key = $1 || "";
			}
		}
		close CM_CONF;
	} else {
		$licence_key=$global_config[0]->[10] || "";
	}

    use Digest::MD5 qw(md5_hex);

    if ( ! $licence_key ) {
        exit_error("ERROR - Licence key not found","106");
    }

    my $hostname_command="/bin/hostname";
    my $server_name=`$hostname_command` or exit_error("Can not determine servername: $!\n");
    $server_name =~ s/^\s+//;
    $server_name =~ s/\s+$//;

    $licence_key =~ /^(\w+)_([0-9.]+)$/;
    my $licence_digest=$1 || "";
    my $licence_expire_seconds=$2 || "";

    if ( ! $licence_digest || ! $licence_expire_seconds ) {
        print_log("NOREF","\nInvalid licence key (1) - please check licence key from web-interface (manage->gestioip)");
        print "\nInvalid licence key (1) - please check licence key from web-interface (manage->gestioip)\n";
        exit_error("ERROR - Invalid licence key (1) - please check licence key from web-interface (manage->gestioip)","107");
    }

    my $licence_valid=0;
    my @device_counts=("50","100","250","500","1000","2500","5000","99999");
    my $device_count=0;

    foreach my $count ( @device_counts ) {
            my $md5_check_string=$server_name . "x" . $licence_expire_seconds . $count;
            my $md5_check=md5_hex($md5_check_string);
            if ( $licence_digest ne $md5_check ) {
                    next;
            } else {
                    $licence_valid=1;
                    $device_count=$count;
                    last;
            }
    }

    if ( $licence_valid ne 1 ) {
        exit_error("ERROR - Invalid licence key (3) - please check licence key from web-interface (manage->gestioip)","112");
    }


    my $md5_check_string=$server_name . "x" . $licence_expire_seconds . $device_count;
    my $md5_check=md5_hex($md5_check_string);

    if ( $licence_digest ne $md5_check ) {
        exit_error("ERROR - Invalid licence key (2) - please check licence key from web-interface (manage->gestioip)","114");
    }

    $licence_expire_seconds=$licence_expire_seconds * 17.4;
    my $seconds_one_month=1339200;
    my $seconds_two_month=2678400;
    my $licence_expire_warn_seconds=$licence_expire_seconds - $seconds_one_month;

    my $datetime=time();
    my $device_count_enabled=get_cm_host_count("$client_id");

    my $licence_expire_date = strftime "%d/%m/%Y", localtime($licence_expire_seconds);
    if ( $datetime > $licence_expire_warn_seconds && $datetime <= $licence_expire_seconds ) {
        print_log("NOREF","Licence valid - WARNING licence will expire soon on $licence_expire_date");
        print "WARNING: Licence will expire on $licence_expire_date\n";
        print "\nPlease visit http://www.gestioip.net to renew your licence key.\n";
    } elsif ( $datetime > $licence_expire_seconds ) {
        print_log ("NOREF","ERROR - Licence expired since $licence_expire_date");
        print "\nERROR - Licence expired since $licence_expire_date\n";
        print_log ("NOREF","\nPlease visit http://www.gestioip.net to renew your licence key.");
        print "\nPlease visit http://www.gestioip.net to renew your licence key.\n\n";
        exit 115;
    } elsif ( $device_count_enabled > $device_count ) {
        print_log ("NOREF","ERROR - License device count exceeded");
        print_log ("NOREF","Count of devices supported by current license: $device_count");
        print_log ("NOREF","Count of devices with enabled CM: $device_count_enabled");
        print "\nERROR - License device count exceeded\n";
        print "Count of devices supported by current license: $device_count\n";
        print "Count of devices with enabled CM: $device_count_enabled\n";
        exit 116;
    } else {
        print_log ("NOREF","Licence valid till $licence_expire_date") if $verbose;
        print "Licence valid till $licence_expire_date)\n" if $debug;
    }
}

sub get_cm_server_hash_key_host_id {
    my ( $client_id,$host_id ) = @_;
    my %values;
    my $ip_ref;
    my $dbh = mysql_connection();
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("SELECT cms.id,cms.name,cms.ip,cms.cm_server_type,cms.server_root,cms.cm_server_description,cms.client_id,cms.cm_server_username,cms.cm_server_password,dcmc.host_id FROM cm_server cms, device_cm_config dcmc WHERE cms.client_id=$qclient_id AND cms.id=dcmc.cm_server_id"
    ) or die "$DBI::errstr";
    $sth->execute() or die "$DBI::errstr";
    while ( $ip_ref = $sth->fetchrow_hashref ) {
        my $id = $ip_ref->{id};
        my $name = $ip_ref->{name};
        my $ip = $ip_ref->{ip};
        my $cm_server_type = $ip_ref->{cm_server_type};
        my $cm_server_root = $ip_ref->{server_root} || "";
        my $description = $ip_ref->{cm_server_description} || "";
        my $client_id = $ip_ref->{client_id};
        my $cm_server_username = $ip_ref->{cm_server_username} || "";
        my $cm_server_password = $ip_ref->{cm_server_password} || "";
        my $host_id = $ip_ref->{host_id};
        push @{$values{$host_id}},"$name","$ip","$cm_server_type","$cm_server_root","$description","$client_id","$cm_server_username","$cm_server_password";
    }
    $dbh->disconnect;
    return %values;
}

sub get_newest_configs_host {
    my ( $client_id,$cm_backup_dir,$host_id,$ip,$other_job_id ) = @_;
    my @configs=();
    my $return_check=0;
    my $dir=$cm_backup_dir . "/" .  $host_id;

    my $cwd = cwd();
    chdir( $dir ) or print_error("NOREF","Can not change to backup directory $dir: $!");

#    opendir (DIR, ".") or print_error("NOREF","ERROR: Can't open backup directory: $!","$ip");
    opendir (DIR, ".") or $return_check=get_return("ERROR: Can't open backup directory: $!");
    if ( $return_check == 1 ) {
        chdir( $cwd ) or print_error("NOREF","Can not change to backup directory $dir: $!");
        return;
    }
    my @files = readdir(DIR);
    close DIR;

    foreach my $file ( sort byDate @files ){
#        push (@configs,"$file") if $file =~ /_${other_job_id}\.(conf|txt)$/;
        push (@configs,"$file") if $file =~ /_${other_job_id}\.(conf|txt)/;
    }

    chdir( $cwd ) or print_error("NOREF","Can not change to backup directory $dir: $!");

    my $newest_config=$configs[-1] || "";

    return $newest_config;
}

sub byDate(){
    my @stat1 = stat( $a );
    my @stat2 = stat( $b );
    return $stat1[9] cmp $stat2[9];
}

sub ignore_compare_string {
    my ($a,$b)=@_;
#    if ( $a =~ /($diffConfigIgnore)/ && $b =~ /($diffConfigIgnore)/ ) {
    if ( $a =~ /($diffConfigIgnore)/ || $b =~ /($diffConfigIgnore)/ ) {
        print_log("NOREF","COMPARE FILES: IGNORED LINE (by XML configuration): $diffConfigIgnore") if $verbose;
	return 0;
    } elsif ( $a ne $b ) {
#        print_log("NOREF","COMPARE FILES: CHANGES DETECTED: $a - $b") if $verbose;
        print_log("NOREF","COMPARE FILES: CHANGES DETECTED") if $verbose;
	return 1;
    } else {
	return 0;
    }
}

sub compare_files {
    my ($client_id,$cm_backup_dir,$host_id,$ip,$new_file,$other_job_id ) = @_;

    my $last_stored_config=get_newest_configs_host("$client_id","$cm_backup_dir","$host_id","$ip","$other_job_id") || "";

    if ( ! $last_stored_config ) {
        return 999999;
    }
    $last_stored_config=$cm_backup_dir . "/" . $host_id . "/" . $last_stored_config;
    
    # files are the same -> returns 0
    my $return_value;
    my $return_check=0;
    if ( -B $last_stored_config ) {
        # compare does not work for compressed/binary files

#        open(FILE, $last_stored_config) or print_error("NOREF","Can't open last_stored_config '$last_stored_config': $!");
        open(FILE, $last_stored_config) or $return_check=get_return("Can't open last_stored_config '$last_stored_config': $!");
        return 11 if $return_check == 1;

        binmode(FILE);
        my $digest_old=Digest::MD5->new->addfile(*FILE)->hexdigest;
        close FILE;

#        open(FILE, $new_file) or print_error("NOREF","Can't open new config '$new_file': $!");
        open(FILE, $new_file) or $return_check=get_return("Can't open new config '$new_file': $!");
        return 11 if $return_check == 1;
        binmode(FILE);
        my $digest_new=Digest::MD5->new->addfile(*FILE)->hexdigest;
        close FILE;

        if ( $digest_old eq $digest_new ) {
            $return_value=0;
        } else {
            $return_value=1;
        }
        print_log("NOREF","COMPARE FILES (binary): $last_stored_config - $new_file: $return_value - $digest_old - $digest_new") if $verbose;
    } else {
        $return_value=compare("$last_stored_config","$new_file", \&ignore_compare_string );
        print_log("NOREF","COMPARE FILES (ascii): $last_stored_config - $new_file: $return_value") if $verbose;
    }

    return $return_value;
}

sub get_return{
    my ($error_message)=@_;
    print_error("NOREF","$error_message");
    return 1;
}


sub insert_audit_auto {
    my ($client_id,$event_class,$event_type,$event,$update_type_audit,$audit_user_param) = @_;

    my $user;
    if ( $audit_user_param && $audit_user_param ne "N/A" ) {
        $user=$audit_user_param;
    } else {
        $user=$ENV{'USER'} || "";
    }
    my $mydatetime=time();

    my $dbh = mysql_connection();
    my $qevent_class = $dbh->quote( $event_class );
    my $qevent_type = $dbh->quote( $event_type );
    my $qevent = $dbh->quote( $event );
    my $quser = $dbh->quote( $user );
    my $qupdate_type_audit = $dbh->quote( $update_type_audit );
    my $qmydatetime = $dbh->quote( $mydatetime );
    my $qclient_id = $dbh->quote( $client_id );
    my $sth = $dbh->prepare("INSERT INTO audit_auto (event,user,event_class,event_type,update_type_audit,date,client_id) VALUES ($qevent,$quser,$qevent_class,$event_type,$qupdate_type_audit,$qmydatetime,$qclient_id)") or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";
    $sth->finish();
}

sub print_help {
    print "\nusage: fetch_config.pl [OPTIONS...]\n\n";
#    print "-b, --backup_file_name=file_name	backup file name.\n";
    print "-c, --csv_hosts=list			coma separated list of IPs to process.\n";
    print "-d, --debug=LEVEL			debug level 1-3 (e.g. -d 2).\n";
    print "-g, --group_id=job_group_id  		group for which the commands should be executed.\n";
    print "-h, --help          			print help.\n";
    print "-i, --id=job_id				ID of the job to be executed.\n";
    print "-j, --jobname=job_short_name		job name to be executed.\n";
    print "-l, --log_file_name=file_name		log file name.\n";
    print "-m, --mail      			mail log file to \"mail_destinatarios\".\n";
    print "-n, --name_client      		client name\n";
    print "-r, --run_unassociated_job		run a job by it's shortname, independently if it is associated to a host.\n";
    print "					Requires paramter \"--jobname\" and \"--csv_hosts\"\n";
    print "-t, --type_id=job type ID		job type ID of the job to be executed.\n";
    print "-u, --upload_config_file=config_name	configuration file to upload to the device.\n";
    print "-v, --verbose				verbose.\n\n";
    exit 1;
}


sub print_version {
    print "\n$0 Version $VERSION\n\n";
    exit 0;
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

sub check_valid_ip {
        my ($ip) = @_;
        my $valid = "0";
    if ( ip_is_ipv4($ip) ) {
        $valid=1;
    } elsif ( ip_is_ipv6($ip) ) {
        $valid=1;
    }
    return $valid;
}

sub exit_tftp_prompt {
    my ($call_from) = @_;

    # send a return
    $exp->send("\n");

    print_log("NOREF","found prompt \".ftp>\" - quit sent") if $verbose;

    $r = $exp->send("quit\n");

    $r = $exp->expect(60,
        [ -re => $enable_prompt, \&print_log, "Logged out from ftp prompt - found enable prompt ($call_from)","verbose" ],
        [ 'timeout', \&print_error, "ERROR: Timeout while trying to logout from ftp prompt ($call_from))","","print_before" ],
        [ 'eof',\&print_error,"EOF FOUND (Logging out from ftp prompt) ($call_from)","","print_before" ],
    );

    if ( $next_error_set == 1 ) {
        $next_error_set = 0;
        return 1;
    }

    unless ( defined $r ) {
        print_error("NOREF","ERROR: logout from ftp prompt failed","","print_before");
        return 1;
    }
}


sub logout {
    my ($logout_command,$prompt,$enable_prompt,$unsaved_changes_expr) = @_;

    $next_error_set = 0;
    my $last_output = $exp->after() || "";
    my $last_match = $exp->match() || "";

    my $save_config_changes_answer;
    my $save_config_changes_message;

    if (( $backup_proto =~ /^.ftp$/ && ( $last_output =~ /ftp>.?$/ || $last_match =~ /ftp>.?$/ ))) {
        exit_tftp_prompt("logout");
    }

    if ( $save_config_changes ) {
        $save_config_changes_answer="y";
        $save_config_changes_message="Configuration saved on logout";
    } else {
        $save_config_changes_answer="n";
        $save_config_changes_message="Configuration not saved on logout";
    }

    if ( $last_match !~ /$prompt|$enable_prompt|$last_return/ && $last_output !~ /$prompt|$enable_prompt|$last_return|ftp>.?$/ ) {
        print "Didn't got prompt - waiting 20s more for prompt\n" if $verbose;
        print_log ("NOREF","Didn't got prompt - waiting 20s more for prompt") if $verbose;
	sleep 20;

        # send a return
        $exp->send("\n");
    }

    if ( ! $unsaved_changes_expr ) {
        $unsaved_changes_expr=$unsaved_changes_expr_generic;
    }

    $r = $exp->send("$logout_command\n");

    print_log("NOREF","Logout command send: $logout_command") if $verbose;

    my $clear_accum=$exp->clear_accum() || "";
    print_log("NOREF","'LOGOUT CLEAR ACCUM': $clear_accum") if $verbose && $clear_accum;


    $r = $exp->expect($timeout,
#        [ -re => $enable_prompt, \&send_string, $logout_command,"","" ],
        [ -re => $error_expr_command_1, \&print_error, "ERROR: Error expression 1 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_2, \&print_error, "ERROR: Error expression 2 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_3, \&print_error, "ERROR: Error expression 3 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_4, \&print_error, "ERROR: Error expression 4 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_5, \&print_error, "ERROR: Error expression 5 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_6, \&print_error, "ERROR: Error expression 5 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_7, \&print_error, "ERROR: Error expression 7 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_8, \&print_error, "ERROR: Error expression 8 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_9, \&print_error, "ERROR: Error expression 9 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_10, \&print_error, "ERROR: Error expression 10 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_11, \&print_error, "ERROR: Error expression 11 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_12, \&print_error, "ERROR: Error expression 12 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_13, \&print_error, "ERROR: Error expression 13 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_14, \&print_error, "ERROR: Error expression 14 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_15, \&print_error, "ERROR: Error expression 15 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_16, \&print_error, "ERROR: Error expression 16 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_17, \&print_error, "ERROR: Error expression 17 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_18, \&print_error, "ERROR: Error expression 18 match (logout)","$ip","print_before" ],
        [ -re => $error_expr_command_19, \&print_error, "ERROR: Error expression 19 match (logout)","$ip","print_before" ],
        [ -re => $unsaved_changes_expr, \&send_string, $save_config_changes_answer, $save_config_changes_message,"exp_continue" ],
        [ -re => 'Do you want to log out', \&send_string, "y","","exp_continue"],
        [ -re => $prompt, \&send_string, $logout_command,"","exp_continue" ],
        [ -re => '[Cc]onnection to .* closed|[Cc]onnection closed|[Ss]ession terminated|logout|Received disconnect' ],
        [ 'timeout', \&print_error, "ERROR: Timeout","$ip","print_before" ],
        [ 'eof',\&print_error,"EOF FOUND","$ip","print_before" ],

    );

    print_log("NOREF","logout MATCH: " . $exp->match()) if $verbose;

    if ( $next_error_set == 1 ) {
        $next_error_set = 0;
        if ( $verbose ) {
            print_error("NOREF","WARNING: Could not log out correctly","$ip","print_before") if $verbose;
        } else {
            print_log("NOREF","WARNING: Could not log out correctly");
        }
        return 1;
    }

    unless ( defined $r ) {
        print "WARNING: Could not log out correctly\n" if $verbose;
        print_error("NOREF","WARNING: Could not log out correctly","$ip","print_before");
        return 1;
    } 

    print_log("NOREF","Logged out correctly") if $verbose;
    print "Logged out correctly\n" if $verbose;

    $logged_out=1;

    close_connection();
}

sub close_connection {
    $exp->soft_close();
}

sub get_bck_file_name {
    my ($cm_server_root,$cm_backup_file_name,$job_type_id,$config_date) = @_;
    my $bckfile=$cm_backup_file_name;

    if ( $bckfile =~ /\[\[DATE\]\]/ ) {
        print_error("NOREF","ERROR: [[DATE]] variable found but no <dateFormat> specified") if ! $config_date;
        $bckfile =~ s/\[\[DATE\]\]/$config_date/;
    }

    if ( $bckfile =~ /\[\[HOSTNAME\]\]/ ) {
        $bckfile =~ s/\[\[HOSTNAME\]\]/$hostname_from_command/;
    }

    if ( $job_type_id == 1 ) {
        if ( $bckfile =~ /\*/ ) {
            my @files = glob("$cm_server_root/$bckfile");
            if ( scalar @files == 1 ) {
                $bckfile=$files[0];
                print_log("NOREF","BCKFILE successfully expanded from wildcard: $bckfile") if $verbose;
             } else {
                my $num=scalar @files;
                print_log("NOREF","WARNING: Can not expand filename from wildcard: $bckfile - $num");
            }
        } else {
            $bckfile=$cm_server_root . "/" . $bckfile;
        }
    } elsif ( $job_type_id == 2 ) {
        $bckfile="/tmp/" . $bckfile;
#    } elsif ( $job_type_id == 4 ) {
#        $bckfile=$localSourceFile;
    }
    
    return $bckfile;
}

sub get_execution_time {
    my $end_time=time();
    my $duration=$end_time - $start_time;
    my @parts = gmtime($duration);
    my $duration_string = "";
    $duration_string = $parts[2] . "h, " if $parts[2] != "0";
    $duration_string = $duration_string . $parts[1] . "m";
    $duration_string = $duration_string . " and " . $parts[0] . "s";
    return $duration_string;
}

sub set_last_backup_date {
    my ($client_id,$host_id,$last_backup_state,$job_id) = @_;

    my $mydatetime=time();
    my $mysql_date = strftime "%Y-%m-%d %H:%M:%S", localtime($datetime);

    if ( $last_backup_state < $last_backup_state_host ) {
        $last_backup_state=$last_backup_state_host;
    }

    # $last_backup_state: 0=ok,1=unchanged,2=warning,3=error
    $last_backup_state=0 if ! $last_backup_state;

    my $dbh = mysql_connection();

    $job_id="" if ! $job_id;
    my $job_id_expr="";
    my $qjob_id="";
    if ( $job_id =~ /,/ ) {
        my @job_ids=split(",",$job_id);
        foreach (@job_ids) {
           $qjob_id = $dbh->quote( $_ );
           $job_id_expr.=" AND id=$qjob_id";
        }
        $job_id_expr=~s/^ AND //;
    } else {
        $qjob_id = $dbh->quote( $job_id );
        $job_id_expr="id=$qjob_id";
    }

    my $qmysql_date = $dbh->quote( $mysql_date );
    my $qlast_backup_state = $dbh->quote( $last_backup_state );
    my $qlast_backup_log = $dbh->quote( $log_file_name );
    my $qhost_id = $dbh->quote( $host_id );
    my $qclient_id = $dbh->quote( $client_id );

    my $sth;

    $sth = $dbh->prepare("UPDATE device_cm_config SET last_backup_date=$qmysql_date, last_backup_status=$last_backup_state, last_backup_log=$qlast_backup_log WHERE client_id=$qclient_id AND host_id=$qhost_id")
         or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "Can not execute statement: $dbh->errstr";

    if ( $job_id ) {
        $sth = $dbh->prepare("UPDATE device_jobs SET last_execution_date=$qmysql_date, last_execution_status=$last_backup_state, last_execution_log=$qlast_backup_log WHERE $job_id_expr")
             or die "Can not execute statement: $dbh->errstr";
        $sth->execute() or die "Can not execute statement: $dbh->errstr";
    }
    $sth->finish();
}



sub get_device_type_values {

    my $valid_global_parameters='passwordExpr|models|enableCommand|enablePrompt|pagerDisableCmd|deviceGroupName|jobs|usernameExpr|deviceGroupID|logoutCommand|pagerExpr|loginPrompt|unsavedChangesMessage|loginConfirmationExpr|showHostnameCommand|preLoginConfirmationExpr';
    my $required_global_parameters='enablePrompt|deviceGroupName|deviceGroupID|logoutCommand';
    my $valid_job_parameter='comment|command|return|configExtension|dateFormat|diffConfigIgnore|commandTimeout|jobType|localSourceFile|localSourceCommand|localSourceCommandPort|destConfigName';
    my $valid_job_types='copy_file|fetch_command_output|task|copy_local';
    my %device_type_group_ids;

    my %commands=();
    my %prompt;
    my %login_atts;
    my %enable_commands;
    my %logout_commands;
    my %pager_disable_commands;
    my %unsaved_changes_expr;
    my %pager_expr;
    my %loginConfirmationExpr;
    my %preLoginConfirmationExpr;
    my %showHostnameCommand;
    my %jobs;

    my @xmlfiles=read_xml_files();

    my @xml_errors=();
    foreach my $xmlfile_name ( @xmlfiles) {

        my $xmlfile=$cm_xml_dir . "/" . $xmlfile_name;

        # initialize parser object and parse the string
        my $parser = XML::Parser->new( ErrorContext => 2 );
        eval { $parser->parsefile( "$xmlfile" ); };

        # report any error that stopped parsing, or announce success
        if( $@ ) {
            $@ =~ s/at \/.*?$//s;               # remove module line number
            print_log ("NOREF","ERROR in '$xmlfile': $@ - XML file ignored");
            print "ERROR in '$xmlfile': $@ - XML file ignored\n";
            next;
        } else {
            print_log ("NOREF","XML check: '$xmlfile' is well-formed") if $debug;
            print "XML check: '$xmlfile' is well-formed\n" if $debug;
        }


        # create object
        my $xml = new XML::Simple;

        # read XML file
        my $data = $xml->XMLin("$xmlfile");

        # access XML data
	if ( $debug ) {
            print_log("NOREF","deviceGroupName: " . $data->{deviceGroupName}) if $data->{deviceGroupName};
            print_log("NOREF","deviceGroupID: " . $data->{deviceGroupID}) if $data->{deviceGroupID};
            print_log("NOREF","models: " . $data->{models}) if $data->{models};
            print_log("NOREF","loginPrompt: " . $data->{loginPrompt}) if $data->{loginPrompt};
            print_log("NOREF","enableCommand:" . $data->{enableCommand}) if $data->{enableCommand};
            print_log("NOREF","usernameExpr:" . $data->{usernameExpr}) if $data->{usernameExpr};
            print_log("NOREF","passwordExpr: " . $data->{passwordExpr}) if $data->{passwordExpr};
            print_log("NOREF","logoutCommand: " . $data->{logoutCommand}) if $data->{logoutCommand};
            print_log("NOREF","pagerDisableCmd: " . $data->{pagerDisableCmd}) if $data->{pagerDisableCmd};
            print_log("NOREF","pagerExpr: " . $data->{pagerExpr}) if $data->{pagerExpr};
            print_log("NOREF","unsavedChangesMessage: " . $data->{unsavedChangesMessage}) if $data->{unsavedChangesMessage};
            print_log("NOREF","showHostnameCommand: " . $data->{showHostnameCommand}) if $data->{showHostnameCommand};
	}


        my $device_group_name = $data->{deviceGroupName} || "";
        $device_group_name = "" if ref $device_group_name eq "HASH";
        my $device_group_id = $data->{deviceGroupID} || "";
        $device_group_id = "" if ref $device_group_id eq "HASH";
        my $models = $data->{models};
        $models = "" if ref $models eq "HASH";
        my $login_prompt = $data->{loginPrompt} || "";
        $login_prompt = "NO_PROMPT" if ref $login_prompt eq "HASH";
        my $enable_prompt = $data->{enablePrompt} || "";
        $enable_prompt = "" if ref $enable_prompt eq "HASH";
        my $enable_command = $data->{enableCommand} || "";
        $enable_command = "" if ref $enable_command eq "HASH";
        my $username_expr = $data->{usernameExpr} || "";
        $username_expr = "" if ref $username_expr eq "HASH";
        my $password_expr = $data->{passwordExpr} || "";
        $password_expr = "" if ref $password_expr eq "HASH";
        my $logout_command = $data->{logoutCommand} || "";
        $logout_command = "" if ref $logout_command eq "HASH";
        my $pager_expr = $data->{pagerExpr} || "__NO_PAGER_EXPR__";
        $pager_expr = "__NO_PAGER_EXPR__" if ref $pager_expr eq "HASH";
        my $pager_disable_cmd = $data->{pagerDisableCmd} || "";
        $pager_disable_cmd = "" if ref $pager_disable_cmd eq "HASH";
        my $unsaved_change_expr = $data->{unsavedChangesMessage} || "";
        $unsaved_change_expr = "" if ref $unsaved_change_expr eq "HASH";
        my $loginConfirmationExpr = $data->{loginConfirmationExpr} || "";
        $loginConfirmationExpr = "" if ref $loginConfirmationExpr eq "HASH";
        my $preLoginConfirmationExpr = $data->{preLoginConfirmationExpr} || "";
        $preLoginConfirmationExpr = "" if ref $preLoginConfirmationExpr eq "HASH";
        my $showHostnameCommand = $data->{showHostnameCommand} || "";
        $showHostnameCommand = "" if ref $showHostnameCommand eq "HASH";


        unless ( $device_group_name ) {
            push @xml_errors,"ERROR: $xmlfile_name: No deviceGroupName defined - XML file ignored";
            next;
        }
        unless ( $device_group_id ) {
            push @xml_errors,"ERROR: $xmlfile_name: No deviceGroupID defined - XML file ignored";
            next;
        }


	$xmlfile_name =~ /^(\d+)_/;
	my $xmlfile_serial=$1 || "";
	if ( ! $xmlfile_serial ) {
                push @xml_errors,"ERROR: $xmlfile_name: Can not determine XML file's serial - XML file ignored";
		next;
	}
	if ( $xmlfile_serial ne $device_group_id ) {
                push @xml_errors,"ERROR: $xmlfile_name: Device Group ID and XML file's serial number are not identical - Please rename XML file or change the Device Group ID - XML file ignored";
		next;
	}

	if ( exists($device_type_group_ids{$device_group_id}) ) {
                push @xml_errors,"ERROR: $xmlfile_name: Dupicated Device Group ID $device_group_id. ID is already used by $device_type_group_ids{$device_group_id} - XML file ignored";
		next;
	}


	my $xml_invalid=0;

	# check for required global parameters;
	foreach my $vals( keys %{$data} ) {
		if ( $vals !~ /^($valid_global_parameters)$/ ) {
                        push @xml_errors,"ERROR: $xmlfile_name: unknown paramter: $vals - Parameter ignored";
		}
	}


	my @valid_global_parameters=split('\|',$valid_global_parameters);

	
	foreach my $param(@valid_global_parameters) {
		my $param_value=$data->{$param} || "";
		if ( $param =~ /^${required_global_parameters}$/ ) {
			if (ref $param eq 'HASH' || ! $param_value ) {
                                push @xml_errors,"ERROR: $xmlfile_name: $param: no value - XML file invalid";
				$xml_invalid=1;
				last;
			} else {
				print_log ("NOREF","param: $param_value") if $debug;
			}
		} else {
			if (ref $param eq 'HASH') {
				print_log ("NOREF","$param: HASH") if $debug;
			} else {
				print_log ("NOREF","$param: $param_value") if $debug;
			}
		}
	}

	next if $xml_invalid == 1;

        $device_type_group_ids{$device_group_id}=$xmlfile;


        push @{$prompt{$device_group_id}},"$login_prompt","$enable_prompt";
        push @{$enable_commands{$device_group_id}},"$enable_command";
        push @{$logout_commands{$device_group_id}},"$logout_command";
        push @{$pager_disable_commands{$device_group_id}},"$pager_disable_cmd";
        push @{$unsaved_changes_expr{$device_group_id}},"$unsaved_change_expr";
        push @{$pager_expr{$device_group_id}},"$pager_expr";
        push @{$loginConfirmationExpr{$device_group_id}},"$loginConfirmationExpr";
        push @{$preLoginConfirmationExpr{$device_group_id}},"$preLoginConfirmationExpr";
        push @{$showHostnameCommand{$device_group_id}},"$showHostnameCommand";

        if ( $username_expr eq '[[GENERIC_USERNAME_EXPR]]' ) {
            $username_expr=$generic_username_expr;
        }
        if ( $password_expr eq '[[GENERIC_PASSWORD_EXPR]]' ) {
            $password_expr=$generic_password_expr;
        }

        push @{$login_atts{$device_group_id}},"$username_expr","$password_expr";

        while ( my ($key, $value) = each(%{ $data->{jobs} }) ) {
           next if $key =~ /^(comment)$/;
           my $job_comment=$data->{jobs}{$key}{comment} || "";
           my $job_type=$data->{jobs}{$key}{jobType} || "";
           push @{$jobs{$device_group_id}{$key}{'jobType'}},"$job_comment","$job_type";
       }

        my ($commands,$comment,$returns,$diffConfigIgnore,$configExtension,$commandTimeout,$localSourceFile,$localSourceCommand,$localSourceCommandPort,$config_dateFormat,$destConfigName,$localConfigName);

        for my $job_name ( keys %{ $jobs{$device_group_id} } ) {

            my $invalid_job=0;

            next if $job_name =~ /^(comment)$/;

            my $jobType=$data->{jobs}{$job_name}{jobType} || "";

#            if ( $data->{jobs}{$job_name}{jobType} && $data->{jobs}{$job_name}{jobType} eq "copy_local" ) {}
            if ( $jobType && $jobType eq "copy_local" ) {
                # "copy_local" must not have other parameter than comment, jobType, localSourceFile, localSourceCommand, localSourceCommandPort
                foreach my $vals( keys %{$data->{jobs}{$job_name}} ) {
                    if ( $vals !~ /^(comment|jobType|localSourceFile|localSourceCommand|localSourceCommandPort)$/ ) {
                        push @xml_errors,"ERROR: Job: $job_name: Wrong parameter: $vals. Job type \"copy_local\" only allows the parameter jobType, comment, localSourceFile, localSourceCommand and localSourceCommandPort - Job ignored";
                        $invalid_job=1;
                        last;
                    }
                }
            }

            foreach my $vals( keys %{$data->{jobs}{$job_name}} ) {
                if ( $vals !~ /^($valid_job_parameter)$/ ) {
                    push @xml_errors,"ERROR: Job: $job_name: Wrong parameter: $vals - Job ignored";
                    $invalid_job=1;
                }
            }

            
            $comment = $data->{jobs}{$job_name}{comment} || "";
            if ( ref $data->{jobs}{$job_name}{comment} eq 'ARRAY' ) {
                push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: only one comment per Job allowed - Job will be ignored";
                $invalid_job=1;
            } elsif ( ref $data->{jobs}{$job_name}{comment} eq 'HASH' || ! $comment ) {
                push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: no comment for this job defined - Job will be ignored";
                $invalid_job=1;
            }
            
            if ( ! exists($data->{jobs}{$job_name}{jobType}) || ref $data->{jobs}{$job_name}{jobType} eq 'HASH' ) {
                push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: no jobType defined - Job will be ignored";
                $invalid_job=1;
            } else {
                if ( ref $data->{jobs}{$job_name}{jobType} eq 'ARRAY' ) {
                    push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: only one jobType per Job allowed - Job will be ignored";
                    $invalid_job=1;
                } elsif ( $data->{jobs}{$job_name}{jobType} !~ /^($valid_job_types)$/ ) {
                    push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: invalid jobType: $data->{jobs}{$job_name}{jobType} - Job will be ignored";
                    $invalid_job=1;
                }
            }
            
            if ( ! exists($data->{jobs}{$job_name}{command}) && $jobType ne "copy_local" ) {
                push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: no commands defined - Job will be ignored";
                $invalid_job=1;
            }
            if ( ! exists($data->{jobs}{$job_name}{return}) && $jobType ne "copy_local" ) {
                push @xml_errors,"ERROR: $xmlfile_name: Job: $job_name: no return prompts defined - Job will be ignored";
                $invalid_job=1;
            }


            if ( $invalid_job == 1 ) {
                push @{$commands{$device_group_id}{$job_name}{valid_job}},"1";
                next;
            }


            $commands=$data->{jobs}{$job_name}{command} || "";
            $returns=$data->{jobs}{$job_name}{return} || "";
            $diffConfigIgnore=$data->{jobs}{$job_name}{diffConfigIgnore} || "";
            $diffConfigIgnore="" if ref $diffConfigIgnore eq "HASH";
            $configExtension=$data->{jobs}{$job_name}{configExtension} || "";
            $configExtension="" if ref $configExtension eq "HASH" || ref $configExtension eq "ARRAY";
            $commandTimeout=$data->{jobs}{$job_name}{commandTimeout} || "";
            $commandTimeout="" if ref $commandTimeout eq "HASH" || ref $commandTimeout eq "ARRAY";
            $localSourceFile=$data->{jobs}{$job_name}{localSourceFile} || "";
            $localSourceFile="" if ref $localSourceFile eq "HASH" || ref $localSourceFile eq "ARRAY";
            $localSourceCommand=$data->{jobs}{$job_name}{localSourceCommand} || "";
            $localSourceCommand="" if ref $localSourceCommand eq "HASH" || ref $localSourceCommand eq "ARRAY";
            $localSourceCommandPort=$data->{jobs}{$job_name}{localSourceCommandPort} || "";
            $localSourceCommandPort="" if ref $localSourceCommandPort eq "HASH" || ref $localSourceCommandPort eq "ARRAY";
            $config_dateFormat=$data->{jobs}{$job_name}{dateFormat} || "";
            $config_dateFormat="" if ref $config_dateFormat eq "HASH" || ref $config_dateFormat eq "ARRAY";
            $destConfigName=$data->{jobs}{$job_name}{destConfigName} || "";
            $destConfigName="" if ref $destConfigName eq "HASH" || ref $destConfigName eq "ARRAY";
            $localConfigName=$data->{jobs}{$job_name}{localConfigName} || "";
            $localConfigName="" if ref $localConfigName eq "HASH" || ref $localConfigName eq "ARRAY";

            my $diffConfigIgnore_expr_u="";
            if ( ref $diffConfigIgnore eq "ARRAY"  ) {

                my @diffConfigIgnore=@$diffConfigIgnore;
                my $diffConfigIgnore_count=scalar @diffConfigIgnore;

                for ( my $i=0; $i < $diffConfigIgnore_count; $i++ ) {
                    my $diffConfigIgnore_expr;
                    if ( ref @$diffConfigIgnore[$i] eq "HASH" ) {
			$diffConfigIgnore_expr="";
                    } else {
                        $diffConfigIgnore_expr=@$diffConfigIgnore[$i];
                    }  
                    $diffConfigIgnore_expr_u.='|' . $diffConfigIgnore_expr;
                }
                $diffConfigIgnore_expr_u =~ s/^\|//;
                push @{$commands{$device_group_id}{$job_name}{diffConfigIgnore}},"$diffConfigIgnore_expr_u";
                print_log ("NOREF","DEBUG: MULTIPLE diffConfigIgnore: $diffConfigIgnore_expr_u") if $debug;
            } else {
                push @{$commands{$device_group_id}{$job_name}{diffConfigIgnore}},"$diffConfigIgnore";
                print_log ("NOREF","DEBUG: ONE diffConfigIgnore: $diffConfigIgnore") if $debug;
            }

            if ( ! $commands && $jobType ne "copy_local" ) { 
                    push @xml_errors,"WARNING: Check XML file $xmlfile_name: Job: $job_name: no commands defined - Job ignored";
                    $invalid_job=1;
            }

            if ( ! $returns && $jobType ne "copy_local" ) { 
                    push @xml_errors,"WARNING: Check XML file $xmlfile_name: Job: $job_name: no returns defined - Job ignored";
                    $invalid_job=1;
            }

            if ( ref $commands eq "ARRAY"  ) {
        #check if number of command and returns is equal

                my @commands=@$commands;
                my @returns=@$returns;
                my $commands_count=scalar @commands;
                my $returns_count=scalar @returns;

                if ( $commands_count != $returns_count ) {
                    push @xml_errors,"WARNING: Check XML file $xmlfile_name: Job: $job_name: there must be the same number of commands and returns - Job ignored";
                    $invalid_job=1;
                }

                # check DATE variable
                foreach ( @commands ) {
                    if ( $_=~/\[\[DATE\]\]/ && ! $config_dateFormat ) {
                        push @xml_errors,"ERROR: Job: $job_name: $_: no <dateFormat> specified - Job ignored";
                        $invalid_job=1;
                        last;
                    }
                }

                if ( $invalid_job == 1 ) {
                    push @{$commands{$device_group_id}{$job_name}{valid_job}},"1";
                    next;
                }

                for ( my $i=0; $i < $commands_count; $i++ ) {
                    my $command;
                    if ( ref @$commands[$i] eq "HASH" ) {
			$command="";
                    } else {
                        $command=@$commands[$i];
                    }  
                    my $return;
                    if ( ref @$returns[$i] eq "HASH" ) {
			$return="[[ENABLE_PROMPT]]";
                    } else {
                        $return=@$returns[$i];
                    }  

                    my $j=$i+1;
                    push @{$commands{$device_group_id}{$job_name}{$j}},"$command","$return";

                    print_log ("NOREF","DEBUG: COMMAND RETURN: $device_group_id - $job_name - @$commands[$i] - @$returns[$i]") if $debug;
                }

            } else {
                if ( $commands=~/\[\[DATE\]\]/ && ! $config_dateFormat ) {
                    push @xml_errors,"ERROR: Job: $job_name: $_: no <dateFormat> specified - Job ignored";
                    $invalid_job=1;
                }

                if ( $invalid_job == 1 ) {
                    push @{$commands{$device_group_id}{$job_name}{valid_job}},"1";
                    next;
                }

                push @{$commands{$device_group_id}{$job_name}{0}},"$commands","$returns";
                print_log ("NOREF","DEBUG: ONE COMMAND RETURN: $device_group_id - $job_name - $commands -  $returns") if $debug;
            }

            push @{$commands{$device_group_id}{$job_name}{configExtension}},"$configExtension";
            push @{$commands{$device_group_id}{$job_name}{localSourceFile}},"$localSourceFile";
            push @{$commands{$device_group_id}{$job_name}{localSourceCommand}},"$localSourceCommand";
            push @{$commands{$device_group_id}{$job_name}{localSourceCommandPort}},"$localSourceCommandPort";
            push @{$commands{$device_group_id}{$job_name}{commandTimeout}},"$commandTimeout";
            push @{$commands{$device_group_id}{$job_name}{dateFormat}},"$config_dateFormat";
            push @{$commands{$device_group_id}{$job_name}{destConfigName}},"$destConfigName";
            push @{$commands{$device_group_id}{$job_name}{localConfigName}},"$localConfigName";
            print_log ("NOREF","DEBUG: ONE configExtension: $configExtension") if $debug;
            print_log ("NOREF","DEBUG: commandTimeout: $commandTimeout") if $debug;
            print_log ("NOREF","DEBUG: dateFormat: $config_dateFormat") if $debug;
        }
    }

#    if ( $xml_errors[0] ) {
#        print_log ("NOREF","Errors in the XML files detected - run check_xml_files.pl - $xml_errors[0]");
#        foreach my $xmlerr ( @xml_errors ) {
#            print_log ("NOREF","$xmlerr");
#        }
#    }

    return (\%prompt,\%login_atts,\%commands,\%enable_commands,\%logout_commands,\%jobs,\%pager_disable_commands,\%unsaved_changes_expr,\%pager_expr,\%loginConfirmationExpr,\%preLoginConfirmationExpr,\%showHostnameCommand);
}


sub read_xml_files {

    my @files=();
    my $return_check=0;

#    opendir DIR, "$cm_xml_dir" or print_error("NOREF","ERROR: Can't open XML file directory \"$cm_xml_dir\": $!\n");
    opendir DIR, "$cm_xml_dir" or $return_check=get_return("ERROR: Can't open XML file directory \"$cm_xml_dir\": $!\n");
    return if $return_check == 1;
    rewinddir DIR;
    while ( my $file = readdir(DIR) ) {
        if ( $file =~ /.xml$/ ) {
            print_log ("NOREF","DEBUG: FOUND XML FILE: $file") if $debug;
            push @files,"$file";
        }
    }
    closedir DIR;

    @files;
}

sub replace_vars {
    my ($command,$return,$cm_server_ip,$cm_config_name,$cm_server_username,$cm_server_password,$cm_server_root,$enable_prompt,$upload_config_file,$user_name,$config_date,$destConfigName,$localConfigName) = @_;

    my $return_value=0;
    my $return_check=0;
    my $sleep="";

    $cm_server_username="" if ! $cm_server_username;
    $cm_server_ip="" if ! $cm_server_ip;
    $cm_server_root="" if ! $cm_server_root;
    $cm_server_password="" if ! $cm_server_password;
    $upload_config_file="" if ! $upload_config_file;
    $user_name="" if ! $user_name;
    $config_date="" if ! $config_date;
    $destConfigName="" if ! $destConfigName;
    $localConfigName="" if ! $localConfigName;

    if ( $command =~ /\[\[SLEEP\d{1,4}\]\]/ ) {
        $command =~ /\[\[SLEEP(\d{1,4})\]\]/;
	$sleep=$1 || "";
        $command =~ s/\[\[SLEEP(\d{1,4})\]\]//;
    }

    if ( $command =~ /\[\[DATE\]\]/ ) {
        print_error("NOREF","ERROR: [[DATE]] variable found but no <dateFormat> specified") if ! $config_date;
        $command =~ s/\[\[DATE\]\]/$config_date/;
    }

    if ( $destConfigName =~ /\[\[DATE\]\]/ ) {
        print_error("NOREF","ERROR: [[DATE]] variable found but no <dateFormat> specified") if ! $config_date;
        $destConfigName =~ s/\[\[DATE\]\]/$config_date/;
    }

    if ( $command =~ /\[\[FILE_CONTENT:\/.+\]\]/ ) {
        $command =~ /\[\[FILE_CONTENT:((\/.+)*\/[0-9a-zA-z_.\-]+)\]\]/;
        my $file=$1;
        my $content="";
#        open(FILE,"<$file") or $return_value=1;
        open(FILE,"<$file") or $return_check=get_return("Can't open file '$file': $!");
        if ( $return_check == 0 ) {
            while (<FILE>) {
                $content.=$_;
            }
            close FILE;
        } else {
            $return_value=1;
	}
        $content=~s/[\r\n]$//;
        $command =~ s/\[\[FILE_CONTENT:((\/.+)*\/[0-9a-zA-z_.\-]+)\]\]/$content/;
        print_log("NOREF","FILE_CONTENT: $file - $content - $command - $return_value") if $verbose;
    }

    if ( $command =~ /\[\[DEST_CONFIG_NAME\]\]/ ) {
        if ( ! $destConfigName ) {
            print_error("NOREF","ERROR: [[DEST_CONFIG_NAME]] variable found but no <destConfigName> attribut specified");
	    $return_value=1;
        } else {
            $command =~ s/\[\[DEST_CONFIG_NAME\]\]/$destConfigName/g;
        }
    }

    if ( $command =~ /\[\[LOCAL_CONFIG_NAME\]\]/ ) {
        if ( ! $localConfigName ) {
            print_error("NOREF","ERROR: [[LOCAL_CONFIG_NAME]] variable found but no <localConfigName> attribut specified");
	    $return_value=1;
        } else {
            $command =~ s/\[\[LOCAL_CONFIG_NAME\]\]/$localConfigName/g;
        }
    }

    $command=rep1("$command");
    $command=rep3("$command");
    $command=rep2("$command","$cm_server_ip","$cm_config_name","$cm_server_username","$cm_server_password","$cm_server_root","$enable_prompt","$upload_config_file");


    if ( $return =~ /\[\[DEST_CONFIG_NAME\]\]/ ) {
        if ( ! $destConfigName ) {
            print_error("NOREF","ERROR: [[DEST_CONFIG_NAME]] variable found but no <destConfigName> attribut specified");
	    $return_value=1;
        } else {
            $return =~ s/\[\[DEST_CONFIG_NAME\]\]/$destConfigName/g;
        }
    }

    $return=rep1("$return");
    $return=rep3("$return");
    $return=rep2("$return","$cm_server_ip","$cm_config_name","$cm_server_username","$cm_server_password","$cm_server_root","$enable_prompt","$upload_config_file");

    return ($return_value,$command,$return,$sleep);
}


sub replace_vars_prompt {
    my ($prompt,$enable_prompt,$user_name,$pager_expr_pre,$loginConfirmationExpr_pre,$preLoginConfirmationExpr_pre) = @_;

    $prompt="" if ! $prompt;
    $enable_prompt="" if ! $enable_prompt;

    $prompt=rep1("$prompt");
    $prompt=rep3("$prompt","replace_pipe");
    $prompt=rep2("$prompt","","","","","","","","$user_name");

    $enable_prompt=rep1("$enable_prompt");
    $enable_prompt=rep3("$enable_prompt","replace_pipe");
    $enable_prompt=rep2("$enable_prompt","","","","","","","","$user_name");

    $pager_expr_pre=rep1("$pager_expr_pre");
    $pager_expr_pre=rep3("$pager_expr_pre","replace_pipe");
    $pager_expr_pre=rep2("$pager_expr_pre","","","","","","","","$user_name");

    if ( $loginConfirmationExpr_pre ) {
	    $loginConfirmationExpr=rep1("$loginConfirmationExpr_pre");
	    $loginConfirmationExpr=rep3("$loginConfirmationExpr_pre","replace_pipe");
	    $loginConfirmationExpr=rep2("$loginConfirmationExpr_pre","","","","","","","","$user_name");
    } else {
	    $loginConfirmationExpr = "__NO_LOGIN_CONFIRMATION_EXPR__";
    }

    if ( $preLoginConfirmationExpr_pre ) {
	    $preLoginConfirmationExpr=rep1("$preLoginConfirmationExpr_pre");
	    $preLoginConfirmationExpr=rep3("$preLoginConfirmationExpr_pre","replace_pipe");
	    $preLoginConfirmationExpr=rep2("$preLoginConfirmationExpr_pre","","","","","","","","$user_name");
    } else {
	    $preLoginConfirmationExpr = "__NO_PRE_LOGIN_CONFIRMATION_EXPR__";
    }

    if ( $prompt =~ /\\\|/ ) {
        my $prompt_new="";
        my @eprompts=split(/\\\|/,$prompt);
        foreach my $p ( @eprompts ) {
            $p =~ s/^\\\\//;
            $p .= '.?$' if $p !~ /\.\?\$$/ && $p !~ / \$$/;
            $p = '.*' . $p if $p !~ /[\r\n]/;
            $prompt_new.='|' . $p;
        }
	
        $prompt_new =~ s/^\|//;
        $prompt=$prompt_new;
    } else {
        $prompt .= '.?$' if $prompt !~ /\.\?\$$/ && $prompt !~ / \$$/ && $prompt !~ /Ethernet Routing Switch/;
        $prompt = '.*' . $prompt if $prompt !~ /[\r\n]/;
    }

    if ( $enable_prompt =~ /\\\|/ ) {
        my $enable_prompt_new="";
        my @eprompts=split(/\\\|/,$enable_prompt);
        foreach my $p ( @eprompts ) {
            $p .= '.?$' if $p !~ /\.\?\$$/ && $p !~ / \$$/;
            $p = '.*' . $p if $p !~ /[\r\n]/;
            $enable_prompt_new.='|' . $p;
        }
	
	$enable_prompt_new =~ s/^\|//;
        $enable_prompt=$enable_prompt_new;
    } else {
        $enable_prompt .= '.?$' if $enable_prompt !~ /\.\?\$$/ && $enable_prompt !~ / \$$/;
        $enable_prompt = '.*' . $enable_prompt if $enable_prompt !~ /[\r\n]/;
    }

    return($prompt,$enable_prompt,$pager_expr_pre,$loginConfirmationExpr,$preLoginConfirmationExpr);
}



#sub replace_configName {
sub replace_date {
    my ($config_date) = @_;

    #replace date string
    my $datetime=time();
    my $date_d = strftime "%d", localtime($datetime);
    my $date_D = $date_d;
    $date_D =~ s/^0//;
    my $date_H = strftime "%H", localtime($datetime);
    my $date_I = strftime "%I", localtime($datetime);
    my $date_m = strftime "%m", localtime($datetime);
    my $date_b = strftime "%b", localtime($datetime);
    my $date_M = strftime "%M", localtime($datetime);
    my $date_y = strftime "%y", localtime($datetime);
    my $date_Y = strftime "%Y", localtime($datetime);

    $config_date =~ s/%d/$date_d/g;
    $config_date =~ s/%D/$date_D/g;
    $config_date =~ s/%H/$date_H/g;
    $config_date =~ s/%I/$date_I/g;
    $config_date =~ s/%m/$date_m/g;
    $config_date =~ s/%b/$date_b/g;
    $config_date =~ s/%M/$date_M/g;
    $config_date =~ s/%y/$date_y/g;
    $config_date =~ s/%Y/$date_Y/g;

    return $config_date;
}

sub get_other_device_jobs_all {
        my ( $client_id ) = @_;
        my %values;
        my $ip_ref;
        my $dbh = mysql_connection();
        my $qclient_id = $dbh->quote( $client_id );
	my $sth = $dbh->prepare("SELECT j.id,j.job_name,j.job_group_id,j.job_descr,j.host_id,j.enabled FROM device_jobs j ORDER BY j.job_name")
                 or die "Can not execute statement:<p>$DBI::errstr\n";
        $sth->execute() or die "Can not execute statement:<p>$DBI::errstr\n";
        while ( $ip_ref = $sth->fetchrow_hashref ) {
                my $host_id = $ip_ref->{host_id};
                my $job_id = $ip_ref->{id};
                my $job_name = $ip_ref->{job_name};
                my $job_group = $ip_ref->{job_group_id} || "";
		my $job_descr = $ip_ref->{job_descr} || "";
		my $job_enabled = $ip_ref->{enabled} || 0;
                push @{$values{$host_id}{$job_id}},"$job_name","$job_group","$job_descr","$job_enabled";
        }
        $dbh->disconnect;

        return %values;
}

sub write_output_to_file {
    my ($host_id,$job_id) = @_;

    print_log("NOREF","write_output_to_file") if $verbose;

    my ( $cm_backup_file,$cm_backup_file_name);
    if ( ! $backup_file_name_param ) {
        my $backup_file_serial=get_file_serial("$job_id") || "";
        print_log("NOREF","WARNING: Can not determine backup file serial number") if ! $backup_file_serial;
        $cm_backup_file_name=$date_file . "_" . $backup_file_serial . "_" . $host_id . "_" . "$job_id" . ".txt";
    } else {
        $cm_backup_file_name=$backup_file_name_param;
    }

    $cm_backup_file="/tmp/" . $cm_backup_file_name;


    my $clear_accum=$exp->clear_accum();
    print_log("NOREF","CLEAR ACCUM 'write_output_to_file': $clear_accum") if $debug==3;

    my $result = $exp->exp_before();
    my $match = $exp->match();


    ( my @result ) = split( /\n/, $result );
    $result = '';

#   delete first line which contains the command
    shift(@result);
    # delete prompt line after command output
    print_log("NOREF","LAST LINE: $result[-1]") if $debug;
    my $popped="";
    my $last_line=$result[-1] || "";
    $popped=pop(@result) if $last_line =~ /$enable_prompt/;
    print_log("NOREF","last-line: $last_line - enable-prompt: $enable_prompt - popped: $popped") if $debug;

    print_log("NOREF","WRITING OUTPUT TO $cm_backup_file") if $verbose;

    open(OUT,">>$cm_backup_file") or print_error("NOREF","ERROR: Can not open file for the command output ($cm_backup_file): $!");

    foreach my $x ( @result ) {
            my $temp = $x;

            if ( chop( $temp ) eq "\r" ) {
                    chop( $x );
            }
            print OUT "$x\n";
    }

    close OUT;
}

sub check_parameters {

    if ( $help ) { print_help(); }
    if ( $debug && $debug !~ /^(1|2|3)/ ) {
        print_help();
    }
    if ( ! $client_name ) {
        $client_name=$params{client} || "";
        if ( ! $client_name ) {
            print "ERROR: no client name found\n";
	    print "Specify parameter \"client\" in $conf\n\n";
            print_help();
	}
    }

    $client_id=get_client_id_from_name("$client_name") || "";
    if ( ! $client_id ) {
        print "ERROR: $client_name: client not found\n";
	print "Check parameter \"client\" in $conf\n\n";
        print_help();
    }

    if ( $mail ) {
        if ( ! $params{mail_destinatarios} ) {
            print "Please specify the recipients to send the mail to (\"mail_destinatarios\") in $conf\n\n";
            print_help();
            exit 1;
        } elsif ( ! $params{mail_from} ) {
            print "Please specify the mail sender address (\"mail_from\") in $conf\n\n";
            print_help();
            exit 1;
        }
    }

    if ( $run_unassociated_job_param ) {
        if ( ! $job_name_param || ! $hosts ) {
	    print "--run_unassociated_jobs requieres the parameters \"--jobname\" and \"--csv_hosts\"\n\n";
	    print_help();
        }
    }
}

sub send_mail {
    my $mailer;

    my $subject="GestioIP Job execution log";
    my $subject_status;
    if ( $anz_failed_hosts == 0 ) {
        $subject_status="- NO errors";
    } else {
        $subject_status="- $anz_failed_hosts errors";
    }

    if ( $params{smtp_server} ) {
            $mailer = Mail::Mailer->new('smtp', Server => $params{smtp_server});
    } else {
            $mailer = Mail::Mailer->new("");
    }
    $mailer->open({ From    => "$$mail_from",
                    To      => "$$mail_destinatarios",
                    Subject => "$subject $subject_status"
                 }) or print_error("NOREF","error while sending mail: $!");
    open (LOG_MAIL,"<$logfile") or print_error("NOREF","can not open log file: $!");
    while (<LOG_MAIL>) {
            print $mailer $_;
    }
    print $mailer "\n\n\n\n\n\n\n\n\n--------------------------------\n\n";
    print $mailer "This email has been automatically generated\n";
    $mailer->close();
    close LOG_MAIL;
}

sub print_host_start_string {
    my ($ip,$hostname) = @_;
    print "############## $ip ($hostname) ###############\n" if $verbose;
    print_log("NOREF","############## $ip ($hostname) ###############");
}

sub print_device_end_string {
#    print "############## END $ip ###############\n" if $verbose;
#    print_log("NOREF","############## END $ip ###############") if $verbose;
}

#sub set_error_expressions {
#    my ($set) = @_;
#
##Exceeded maximum number of allowed configuration script.
#    if ( $set eq "set" ) {
#        $error_expr_command_1=".*ERROR.*";
#        $error_expr_command_2=".*[Ee]rror.*";
#        $error_expr_command_3=".*[Ff]ailed.*";
#        $error_expr_command_4=".*[Ii]nvalid.*";
#        $error_expr_command_5=".*[Uu]nsuccessful.*";
#        $error_expr_command_6=".*[Ii]ncorrect.*";
#        $error_expr_command_7=".*[Uu]nreachable.*";
#        $error_expr_command_8=".*[Uu]nable.*";
#        $error_expr_command_9=".*[Dd]enied.*";
#        $error_expr_command_10=".*[Ww]rong.*";
#        $error_expr_command_11=".*[Vv]iolation.*";
#        $error_expr_command_12=".*[Tt]imed out.*";
#        $error_expr_command_13=".*[Tt]imeout.*";
#        $error_expr_command_14=".*[Rr]efused.*";
#        $error_expr_command_15=".*[Ff]ailure.*";
#        $error_expr_command_16=".*[Nn]ot [Ff]ound.*";
#        $error_expr_command_17=".*ftp: server says:.*"; # Fujitsu xg700 FTP/TFTP server error
#        $error_expr_command_18=".*[Nn]o space left.*";
#        $error_expr_command_19=".*[Nn]o such file or directory.*";
#    } else {
#        $error_expr_command_1="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_2="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_3="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_5="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_5="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_6="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_7="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_8="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_9="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_10="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_11="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_12="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_13="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_14="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_15="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_16="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_17="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_18="__ERROR_EXPR_DISABLED_NO_MATCH__";
#        $error_expr_command_19="__ERROR_EXPR_DISABLED_NO_MATCH__";
#    }
#}
#


sub set_error_expressions {
    my ($set, $expr) = @_;
    my @expr = ();
    if ( $expr ) {
        @expr = @$expr;
#        print_log("NOREF","IGNO ARRAY0000: @expr") if $verbose;
    }

    print_log("NOREF","IGNO ARRAY: @expr") if @expr && $verbose;
    if ( $set eq "set" ) {
	if ( @expr ) {
		foreach my $igno_expr ( @expr ) {
			if ( $igno_expr =~ /$error_expr_command_1/ ) {
				$error_expr_command_1="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_2/ ) {
				$error_expr_command_2="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_3/ ) {
				$error_expr_command_3="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_4/ ) {
				$error_expr_command_4="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_5/ ) {
				$error_expr_command_5="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_6/ ) {
				$error_expr_command_6="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_7/ ) {
				$error_expr_command_7="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_8/ ) {
				$error_expr_command_8="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_9/ ) {
				$error_expr_command_9="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_10/ ) {
				$error_expr_command_10="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_11/ ) {
				$error_expr_command_11="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_12/ ) {
				$error_expr_command_12="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_13/ ) {
				$error_expr_command_13="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_14/ ) {
				$error_expr_command_14="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_15/ ) {
				$error_expr_command_15="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_16/ ) {
				$error_expr_command_16="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_17/ ) {
				$error_expr_command_17="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_18/ ) {
				$error_expr_command_18="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
			if ( $igno_expr =~ /$error_expr_command_19/ ) {
				$error_expr_command_19="__ERROR_EXPR_DISABLED_NO_MATCH__";
			}
		}
        } else {
		$error_expr_command_1=".*ERROR.*";
		$error_expr_command_2=".*[Ee]rror.*";
		$error_expr_command_3=".*[Ff]ailed.*";
		$error_expr_command_4=".*[Ii]nvalid.*";
		$error_expr_command_5=".*[Uu]nsuccessful.*";
		$error_expr_command_6=".*[Ii]ncorrect.*";
		$error_expr_command_7=".*[Uu]nreachable.*";
		$error_expr_command_8=".*[Uu]nable.*";
		$error_expr_command_9=".*[Dd]enied.*";
		$error_expr_command_10=".*[Ww]rong.*";
		$error_expr_command_11=".*[Vv]iolation.*";
		$error_expr_command_12=".*[Tt]imed out.*";
		$error_expr_command_13=".*[Tt]imeout.*";
		$error_expr_command_14=".*[Rr]efused.*";
		$error_expr_command_15=".*[Ff]ailure.*";
		$error_expr_command_16=".*[Nn]ot [Ff]ound.*";
		$error_expr_command_17=".*ftp: server says:.*"; # Fujitsu xg700 FTP/TFTP server error
		$error_expr_command_18=".*[Nn]o space left.*";
		$error_expr_command_19=".*[Nn]o such file or directory.*";
        }
    } else {
        $error_expr_command_1="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_2="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_3="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_5="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_5="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_6="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_7="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_8="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_9="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_10="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_11="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_12="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_13="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_14="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_15="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_16="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_17="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_18="__ERROR_EXPR_DISABLED_NO_MATCH__";
        $error_expr_command_19="__ERROR_EXPR_DISABLED_NO_MATCH__";
    }
}


sub set_pager_expressions {
    my ($set,$pager_expr) = @_;
    if ( $set eq "set" && $pager_expr ) {
        $pager_expr=$pager_expr;
    } else {
        $pager_expr="__NO_PAGER_EXPR__";
    }
}

sub rep1 {
    my ($expression) = @_;

    $expression =~ s/\[\[SERVER_USERNAME\]\]/____SERVER_USERNAME____/;
    $expression =~ s/\[\[SERVER_IP\]\]/____SERVER_IP____/g;
    $expression =~ s/\[\[SERVER_ROOT\]\]/____SERVER_ROOT____/g;
    $expression =~ s/\[\[SERVER_PASSWORD\]\]/____SERVER_PASSWORD____/g;
    $expression =~ s/\[\[CONFIG_NAME\]\]/____CONFIG_NAME____/g;
    $expression =~ s/\[\[UPLOAD_CONFIG_NAME\]\]/____UPLOAD_CONFIG_NAME____/g;
    $expression =~ s/\[\[DEVICE_USERNAME\]\]/____DEVICE_USERNAME____/g;
    $expression =~ s/\[\[ENABLE_PROMPT\]\]/____ENABLE_PROMPT____/g;
    $expression =~ s/\[\[GENERIC_USERNAME_EXPR\]\]/____GENERIC_USERNAME_EXPR____/g;
    $expression =~ s/\[\[GENERIC_PASSWORD_EXPR\]\]/____GENERIC_PASSWORD_EXPR____/g;
    $expression =~ s/\[\[HOSTNAME\]\]/____HOSTNAME____/g;

    return $expression;
}

sub rep2 {
    my ($expression,$cm_server_ip,$cm_config_name,$cm_server_username,$cm_server_password,$cm_server_root,$enable_prompt,$upload_config_file,$user_name) = @_;

    $cm_server_username="" if ! $cm_server_username;
    $cm_server_ip="" if ! $cm_server_ip;
    $cm_server_root="" if ! $cm_server_root;
    $cm_server_password="" if ! $cm_server_password;
    $cm_config_name="" if ! $cm_config_name;
    $upload_config_file="" if ! $upload_config_file;
    $user_name="" if ! $user_name;

    $expression =~ s/____SERVER_USERNAME____/$cm_server_username/;
    $expression =~ s/____SERVER_IP____/$cm_server_ip/g;
    $expression =~ s/____SERVER_ROOT____/$cm_server_root/g;
    $expression =~ s/____SERVER_PASSWORD____/$cm_server_password/g;
    $expression =~ s/____CONFIG_NAME____/$cm_config_name/g;
    $expression =~ s/____UPLOAD_CONFIG_NAME____/$upload_config_file/g;
    $expression =~ s/____DEVICE_USERNAME____/$user_name/g;
    $expression =~ s/____ENABLE_PROMPT____/$enable_prompt/g;
    $expression =~ s/____GENERIC_USERNAME_EXPR____/$generic_username_expr/g;
    $expression =~ s/____GENERIC_PASSWORD_EXPR____/$generic_password_expr/g;
    $expression =~ s/____HOSTNAME____/$hostname_from_command/g;

    return $expression;
}

sub rep3 {
    my ($expression,$replace_pipe) = @_;

    $replace_pipe="" if ! $replace_pipe;
    #\. \* \? \+ \[ \] \r \n-> \ darf nicht nochmal escaped werden
    if ( $replace_pipe eq "replace_pipe" ) {
        $expression=~s/\\(?![\.\*\?\+\[\]\|rn])/\\\\/g;
#        $expression=~s/\|/\\|/g;
    } else {
        $expression=~s/\\(?![\.\*\?\+\[\]rn])/\\\\/g;
    }
    $expression=~s/\(/\\(/g;
    $expression=~s/\)/\\)/g;
#    $expression=~s/\[/\\[/g;
#    $expression=~s/\]/\\]/g;
#    $expression=~s/\//\\\//g;
    $expression=~s/\$/\\\$/g;
#    $expression =~ s/@/\\@/g;

    return $expression;
}

sub get_job_types_id {
    my %job_types;
    $job_types{'copy_file'}=1;
    $job_types{'fetch_command_output'}=2;
    $job_types{'task'}=3;
    $job_types{'copy_local'}=4;

    return %job_types;
}

sub check_options {
    if ( $job_id_param && $job_id_param !~ /^\d+$/ ) {
        print "Job ID must be nummerical\n";
        print_help();
    }
}

sub get_cm_host_count {
    my ( $client_id ) = @_;

    my $count;
    my $dbh = mysql_connection();
    my $qclient_id = $dbh->quote( $client_id );

    my $sth = $dbh->prepare("SELECT count(*) FROM custom_host_column_entries WHERE entry='enabled' AND pc_id IN ( SELECT column_type_id FROM custom_host_columns WHERE name='CM')"
        ) or die "Can not execute statement: $dbh->errstr";
    $sth->execute() or die "$DBI::errstr";  
    $count = $sth->fetchrow_array;
    $sth->finish();
    $dbh->disconnect;
    return $count;
}

sub finish_child {
    my ( $exit, $logout_command,$prompt,$enable_prompt,$unsaved_changes_expr,$logged_in,$logged_out ) = @_;

	$exit = "" if ! $exit;
    $logged_in = 0 if ! $logged_in;
    $logged_out = 0 if ! $logged_out;

    logout("$logout_command","$prompt","$enable_prompt","$unsaved_changes_expr") if $logged_in==1 && $logged_out==0;

	close LOG;
	close STDOUT;

	$pm->finish($exit);
}
