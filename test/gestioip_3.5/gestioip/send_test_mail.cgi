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
#use POSIX qw(ceil);
use POSIX qw(strftime);
use Net::SMTP;
use Math::BigInt;
use Time::Local;

my $daten=<STDIN> || "";
my $gip = GestioIP -> new();
my %daten=$gip->preparer("$daten");

my $base_uri = $gip->get_base_uri();
my ($lang_vars,$vars_file)=$gip->get_lang();
my $server_proto=$gip->get_server_proto();

my $client_id = $daten{'client_id'} || 1;
my $server_name = $daten{'server_name'} || "";
my $default_from = $daten{'default_from'} || "";
my $user_name = $daten{'user_name'} || "";
my $password = $daten{'password'} || "";
my $security = $daten{'security'} || "";
my $port = $daten{'port'} || "";
my $timeout = $daten{'timeout'} || 6;
my $mail_to = $daten{'mail_to'} || "";
my $send_mail = $daten{'send_mail'} || "";


print <<EOF;
Content-type: text/html\n
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
"http://www.w3.org/TR/html4/loose.dtd">
<HTML>
<head><title>Mail Server Check</title>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<meta http-equiv="Pragma" content="no-cache">
<link rel="stylesheet" type="text/css" href="./stylesheet.css">
<link rel="stylesheet" href="./css/bootstrap/bootstrap.min.css">
<script src="http://localhost/gestioip/js/bootstrap/bootstrap.min.js"></script>
<link rel="shortcut icon" href="/favicon.ico">
</head>

<body>
EOF

print "<p></p>\n";

if ( $send_mail ) {

	my $error = send_mail (
	    mail_from   =>  "$default_from",
	    mail_to     =>  $mail_to,
	    user     =>  $user_name,
	    pass     =>  $password,
	    security     =>  $security,
	    port     =>  $port,
	    timeout     =>  $timeout,
		subject     => "GestioIP test mail",
	    smtp_server => "$server_name",
		smtp_message    => "Mail test",
	) || "";

    if ( $error ) {
        print "<h4 class='pb-2 pl-2'>Error</h4><h5 class='pb-2 pl-2'>$error</h5>\n" if $error;
        print_end();
    }

	print "<h5 class='pb-2 pl-2'>$$lang_vars{test_mail_send_message}</h5><p>";
	print "<h5 class='pb-2 pl-2'>$$lang_vars{check_mail_box_message}</h5>\n";

	print_end();

} else {
	print "<h5 class='pb-2 pl-2'>$$lang_vars{send_test_mail_message}</h5>\n";
}

my ($form, $form_elements);

$form_elements .= GipTemplate::create_form_element_text(
    label => $$lang_vars{mail_recipient_message},
    id => "mail_to",
    type => "email",
    col_sm => "col-sm-4",
);


$form_elements .= GipTemplate::create_form_element_hidden(
    value => "send_mail",
    name => "send_mail",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$server_name",
    name => "server_name",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$user_name",
    name => "user_name",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$password",
    name => "password",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$port",
    name => "port",
);

$form_elements .= GipTemplate::create_form_element_hidden(
    value => "$default_from",
    name => "default_from",
);

$form_elements .= GipTemplate::create_form_element_button(
    value => $$lang_vars{submit_message},
    name => "B2",
);


## FORM

$form = GipTemplate::create_form(
    form_elements => $form_elements,
    form_id => "insert_smtp_server_form",
    link => "./send_test_mail.cgi",
    method => "POST",
);

print $form;

print_end();

sub print_end {
	print "</div>\n";
	print "</div>\n";
	print "</body>\n";
	print "</html>\n";
	exit 0;
}



sub send_mail {
    my %args = @_;

    my $mail_from=$args{mail_from};
    #"user\@domain.net";
    my $mail_to=$args{mail_to} || "";
    # mail_to array_ref;
    my $subject=$args{'subject'} || "";
    my $server=$args{'smtp_server'} || "";
    my $message=$args{'smtp_message'} || "";
    my $user=$args{'user'} || "";
    my $pass=$args{'pass'} || "";
    my $security=$args{'security'} || "";
    my $port=$args{'port'} || "";
    my $timeout=$args{'timeout'} || "6";
    my $debug=$args{'debug'} || 0;

    my $error = "";

    my @months = qw( Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec );
    my @days = qw(Sun Mon Tue Wed Thu Fri Sat Sun);
    my $zone_num = strftime("%z", localtime());
    my $zone_string = strftime("%Z", localtime());

    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime();
    $year = $year + 1900;
    my $mail_date = "$days[$wday], $mday $months[$mon] $year $hour:$min:$sec $zone_num ($zone_string)";

    $gip->debug("SENDING MAIL: $user - $pass - $server - $port - $mail_from - $timeout - $mail_to");

    my $mailer = new Net::SMTP(
        $server,
        Hello   =>      'localhost',
        Port    =>      $port,
        Timeout =>      $timeout,
#        Debug   =>      $debug,
    );
    
    return "Error connecting with mail server:<p></p><b>$!</b>" if ! $mailer;

    if ( $security eq "starttls" ) {
        $mailer->starttls();
    }
    if ( $user ) {
        $mailer->auth($user,$pass) or $error = $mailer->message();
    }

    return $error if $error;

    $mailer->mail($mail_from) or $error .= $mailer->message();
    $mailer->to($mail_to) or $error .= $mailer->message();
    $mailer->data() or $error .= $mailer->message();
    $mailer->datasend('Date: ' . $mail_date) or $error .= $mailer->message();
    $mailer->datasend("\n") or $error .= $mailer->message();
    $mailer->datasend('Subject: ' . $subject) or $error .= $mailer->message();
    $mailer->datasend("\n") or $error .= $mailer->message();
    $mailer->datasend('From: ' . $mail_from) or $error .= $mailer->message();
    $mailer->datasend("\n") or $error .= $mailer->message();
    $mailer->datasend('To: ' . $mail_to) or $error .= $mailer->message();
    $mailer->datasend("\n") or $error .= $mailer->message();
    $mailer->datasend($message) or $error .= $mailer->message();
    $mailer->dataend or $error .= $mailer->message();
    $mailer->quit or $error .= $mailer->message();

	$gip->debug("MAIL ERROR: $error") if $error;

    return $error;
}


