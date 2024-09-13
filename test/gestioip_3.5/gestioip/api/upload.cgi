#!/usr/bin/perl

use Cwd;
use CGI;

my $debug = 1;
        
my $q = new CGI;

my ($status, $message, $exit);
my $output_type_header = "text/xml";
$exit = 0;

my $filename = $q->param("file_name") || "";

print STDERR "FOUND FILENAME: $filename\n" if $debug;

if ( $filename !~ /^[A-Za-z0-9-_.]+$/ ){
	$message = "ERROR: only the following characters are allowed for file_name: A-Z,a-z,0-9,-,_,.";
	$status ="400 Bad Request";
	$exit = 1;
	printResponse(
		message   => "$message",
		status => "$status",
		exit => "$exit",
	);
}

$POST_MAX=1024 * 10000;  # 10MB max
my $content_length = defined $ENV{'CONTENT_LENGTH'} ? $ENV{'CONTENT_LENGTH'} : 0;
if (($POST_MAX > 0) && ($content_length > $POST_MAX)) {
		$message = "ERROR: Upload is limited to a file size of max. 10MB";	
		print STDERR "$message\n" if $debug;
		$status ="500 Internal Server Error";
		$exit = 1;
		printResponse(
			message   => "$message",
			status => "$status",
			exit => "$exit",
		);
}

my $lightweight_fh  = $q->upload('leases_file');



if (defined $lightweight_fh) {

	print STDERR "HANDLE DEFINED\n" if $debug;

	# Upgrade the handle to one compatible with IO::Handle:
	my $io_handle = $lightweight_fh->handle;

	my $file = '/usr/share/gestioip/var/data/' . $filename;
	open (OUTFILE,'>', "$filename") or $message = "ERROR: can not open file to write: $!";

	if ( $message ) {
		print STDERR "$message\n" if $debug;
		$status ="500 Internal Server Error";
		$exit = 1;
		printResponse(
			message   => "$message",
			status => "$status",
			exit => "$exit",
		);
	}

	while ($bytesread = $io_handle->read($buffer,1024)) {
		print OUTFILE $buffer;
	}

	close OUTFILE;

} else {
	print STDERR "NO HANDLE DEFINED\n" if $debug;
	$message = "ERROR: No leases file received";
	$status ="400 Bad Request";
	$exit = 1;
	printResponse(
		message   => "$message",
		status => "$status",
		exit => "$exit",
	);
}


$status ="200 OK";
printResponse(
	message   => "OK",
	status => "$status",
	exit => "$exit",
);



###################
#### Subroutines
###################

sub printResponse {
    my %args = @_;

    my $status = $args{status} || "";
    my $message = $args{message} || "";
    my $exit = $args{exit} || 0;

	my $output = "";
	$output .= "<?xml version='1.0' encoding='UTF-8'?>\n";
	$output .= "<Result>\n";
	$output .= "    <Message>$message</Message>\n";
	$output .= "</Result>\n";

	printHtmlHeader(
		type   => "$output_type_header",
		status => "200 OK",
	);

	print $output;

	exit $exit;
}

sub printHtmlHeader {
    my %args = @_;

    my $type = $args{type} || "";
    $type = "-type => \"$type\"" if $type;
    my $status = $args{status} || "";
    $status = "-status => \"$status\"" if $status;

    my $header_params = $type . "," . $allow . "," . $location . "," . $status;
    $header_params =~ s/^,//;
    $header_params =~ s/,$//;

    print $q->header( eval($header_params) );
}





#curl \
#  -F "userid=1" \
#  -F "filecomment=This is an image file" \
#  -F "image=@/home/user1/Desktop/test.jpg" \
#  localhost/uploader.php

