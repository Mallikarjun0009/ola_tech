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
use lib './modules';
use GestioIP;
use Time::Local;
use POSIX qw(strftime);

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $base_uri = $gip->get_base_uri();
my $server_proto=$gip->get_server_proto();

# Parameter check
my $lang = $daten{'lang'} || "";
$lang="" if $lang !~ /^\w{1,3}$/;
my ($lang_vars,$vars_file)=$gip->get_lang("","$lang");

my $client_id = $daten{'client_id'} || $gip->get_first_client_id();
my $id = $daten{'id'} || $gip->get_first_client_id();

my $error_message=$gip->check_parameters(
	vars_file=>"$vars_file",
	client_id=>"$client_id",
) || "";


$gip->CheckInput("$client_id",\%daten,"$$lang_vars{mal_signo_error_message}","$$lang_vars{job_info_message}","$vars_file");

my $job_hash = $gip->get_scheduled_job_hash("$client_id", "id");
my $job_result_hash = $gip->get_scheduled_job_last_status_hash("$client_id", "id");


#		push @{$values{$id}},"$name", "$start_date","$end_date", "$run_once", "$status", "$comment", "$arguments", "$cron_time", "$next_run", "$repeat_interval", "$type", "$client_id", "$end_date";


my $job_name = $job_hash->{$id}[0];
my $start_date = $job_hash->{$id}[1];
my $end_date = $job_hash->{$id}[2];
my $run_once = $job_hash->{$id}[3];
my $status_id = $job_hash->{$id}[4];
my $comment = $job_hash->{$id}[5];
my $arguments = $job_hash->{$id}[6];
my $cron_time = $job_hash->{$id}[7];
my $repeat_interval = $job_hash->{$id}[9];
my $job_type_id = $job_hash->{$id}[10];

if ( $arguments =~ /--aws_secret_access_key/ ) {
    $arguments =~ s/(--aws_secret_access_key=".+?")/--aws_secret_access_key="\*\*\*\*\*\*\*\*"/;
}
if ( $arguments =~ /--azure_secret_key_value/ ) {
    $arguments =~ s/(--azure_secret_key_value=".+?")/--azure_secret_key_value="\*\*\*\*\*\*\*\*"/;
}

my $next_run=$gip->get_next_run("$cron_time");

my %job_type_hash = (
    1 => $$lang_vars{combined_message},
    2 => $$lang_vars{networks_message},
    3 => $$lang_vars{host_dns_message},
    4 => $$lang_vars{host_snmp_message},
    5 => $$lang_vars{vlans_message},
	6 => $$lang_vars{dhcp_leases_message},
	7 => $$lang_vars{db_backup_message},
	8 => $$lang_vars{cloud_discovery_aws_message},
	9 => $$lang_vars{cloud_discovery_azure_message},
	10 => $$lang_vars{cloud_discovery_gcp_message},
    11 => $$lang_vars{cmm_job_message},
);

my %status_hash = (
    1 => $$lang_vars{enabled_message},
    2 => $$lang_vars{disabled_message},
);

my %result_hash = (
    1 => $$lang_vars{scheduled_message},
    2 => $$lang_vars{running_message},
    3 => $$lang_vars{completed_message},
    4 => $$lang_vars{failed_message},
    5 => $$lang_vars{completed_warning_message},
    6 => $$lang_vars{skipped_messge},
);

my %log_name_hash = (
    "discover_networks" => $$lang_vars{combined_message},
    "get_networks" => $$lang_vars{networks_message},
    "vlans" => $$lang_vars{vlans_message},
    "gestioip_dns" => $$lang_vars{host_dns_message},
    "gestioip_snmp" => $$lang_vars{host_snmp_message},
    "leases" => $$lang_vars{dhcp_leases_message},
    "backup_gip" => $$lang_vars{db_backup_message},
	"aws" => $$lang_vars{cloud_discovery_aws_message},
	"azure" => $$lang_vars{cloud_discovery_azure_message},
	"gcp" => $$lang_vars{cloud_discovery_gcp_message},
    "cmm" => $$lang_vars{cmm_job_message},
);



my $script = "";
if ( $job_type_id == 1 ) {
        $script = "discover_network.pl";
} elsif ( $job_type_id == 2 ) {
        $script = "get_networks_snmp.pl";
} elsif ( $job_type_id == 3 ) {
        $script = "ip_update_gestioip_dns.pl";
} elsif ( $job_type_id == 4 ) {
        $script = "ip_update_gestioip_snmp.pl";
} elsif ( $job_type_id == 5 ) {
        $script = "ip_import_vlans.pl";
} elsif ( $job_type_id == 6 ) {
        $script = "gip_lease_sync.pl";
} elsif ( $job_type_id == 7 ) {
        $script = "backup_gip.pl";
} elsif ( $job_type_id == 8 || $job_type_id == 9 || $job_type_id == 10 ) {
        $script = "gip_cloud_sync.pl";
} elsif ( $job_type_id == 11 ) {
        $script = "fetch_config.pl";
}        
my $command = $script . " " . $arguments;

my $job_type=$job_type_hash{$job_type_id};

$start_date =~ /^(\d+)\/(\d+)\/(\d+) (\d+):(\d+)/;
my $exe_day = $1;
my $exe_month = $2;
my $exe_year = $3;
my $exe_hour = $4;
my $exe_minute = $5;
my $exe_sec = "00";

my $now_epoch = time();
my $now_time = strftime "%d/%m/%Y %H:%M", localtime($now_epoch);

my $exe_epoch = timelocal($exe_sec,$exe_minute,$exe_hour,$exe_day,$exe_month-1,$exe_year);


print "<p><h4>$$lang_vars{job_message} $job_name</h4><br>\n";
print "<table class='table'>";
print "<tr><td style='width: 10%'>$$lang_vars{id_message}</td><td>$id</td></tr>";
print "<tr><td>$$lang_vars{job_type_message}</td><td>$job_type</td></tr>";
#print "<tr><td>$$lang_vars{status_message}</td><td>$status</td></tr>";
#if ( ! $run_once ) {
#    print "<tr><td>$$lang_vars{start_date_message}</td><td>$start_date</td></tr>";
#    print "<tr><td>$$lang_vars{end_message}</td><td>$end_date</td></tr>";
#}
print "<tr><td>$$lang_vars{comentario_message}</td><td>$comment</td></tr>";
print "<tr><td>$$lang_vars{command_message}</td><td>$command</td></tr>";
if ( $run_once ) {
	print "<tr><td>$$lang_vars{execution_date_message}</td><td>$next_run</td></tr>";
} else {
	print "<tr><td>$$lang_vars{next_run_message}</td><td>$next_run</td></tr>";
}
print "<tr><td>$$lang_vars{repeat_message}</td><td>$repeat_interval</td></tr>";
print "<tr></table><p><br>";

print "<h5>$$lang_vars{historia_message}</h5><p>\n";

print "<table class='table' style='width: 60%'>";
print "<tr><td><font size=\"2\"><b>$$lang_vars{execution_date_message}</font></td><td><font size=\"2\"><b>$$lang_vars{duration_message}</b></font></td><td><font size=\"2\"><b>$$lang_vars{result_message}</b></font><td><font size=\"2\"><b>$$lang_vars{last_log_message}</b></font></td></tr>";
foreach my $job_status_id ( sort { $b <=> $a } keys  %$job_result_hash ) {
    if ( $job_result_hash->{$job_status_id}[0] eq $id ) {

		my $last_result_id = $job_result_hash->{$job_status_id}[1] || 1;
		my $start_time_epoch = $job_result_hash->{$job_status_id}[2] || "";
		my $end_time_epoch = $job_result_hash->{$job_status_id}[3] || "";

		my $last_log = $job_result_hash->{$job_status_id}[5] || "";


		my $last_result = $result_hash{$last_result_id};
		my $status=$status_hash{$status_id};

		my $start_time = "";
		$start_time = strftime "%d/%m/%Y %H:%M", localtime($start_time_epoch) if $start_time_epoch;

		my $duration_string = "";
		if ( $start_time_epoch && $end_time_epoch ) {
			my $duration = $end_time_epoch - $start_time_epoch;
			my @parts = gmtime($duration);
			$duration_string = $parts[2] . "h, " if $parts[2] != "0";
			$duration_string = $duration_string . $parts[1] . "m";
			$duration_string = $duration_string . " and " . $parts[0] . "s";
			$duration_string = "<1s" if $duration_string eq "0m and 0s";
			if ( $duration_string =~ /^0m and/ ) {
				$duration_string =~ s/^0m and //;
			}
		}

		my @last_log = split(",",$last_log);
		my $log_link = "";
		foreach ( @last_log ) {
			$_ =~ s/\s//g;
			if ( $_ =~ /discover_network/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_'>$log_name_hash{discover_networks}</a>";
			} elsif ( $_ =~ /networks_snmp/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_'>$log_name_hash{get_networks}</a>";
			} elsif ( $_ =~ /vlans/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{vlans}</a>";
			} elsif ( $_ =~ /gestioip_dns/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{gestioip_dns}</a>";
			} elsif ( $_ =~ /gestioip_snmp/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{gestioip_snmp}</a>";
			} elsif ( $_ =~ /leases/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{leases}</a>";
			} elsif ( $_ =~ /backup_gip/ ) {
				$log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{backup_gip}</a>";
            } elsif ( $_ =~ /aws/ ) {
                $log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{aws}</a>";
            } elsif ( $_ =~ /azure/ ) {
                $log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{azure}</a>";
            } elsif ( $_ =~ /gcp/ ) {
                $log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{gcp}</a>";
            } elsif ( $_ =~ /fetch_config/ ) {
                $log_link .= "<br><a href='$server_proto://$base_uri/log/$_' class='nowrap'>$log_name_hash{cmm}</a>";
			}
		}
		$log_link =~ s/^<br>// if $log_link;

		print "<tr><td>$start_time</td><td>$duration_string</td><td>$last_result</td><td>$log_link</td></tr>";
	}
}

print "</table>\n";

$gip->print_end("$client_id","$vars_file","", "$daten");
