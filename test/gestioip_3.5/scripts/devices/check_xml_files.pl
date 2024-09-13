#!/usr/bin/perl

#version 1.3, 20160510

use strict;
use warnings;
use XML::Parser;
use XML::Simple;
use Data::Dumper;

my $verbose=0;

my ($xmlfiles,$xmlfiles_hash)=read_xml_files();
my @xmlfiles=@$xmlfiles;
my %xmlfiles=%$xmlfiles_hash;
if ( ! @xmlfiles ) {
	print "No XML files found\n";
}

if ( $ARGV[0] && ( $ARGV[0] eq "--help" || $ARGV[0] eq "-h" )) {
	print_help();
}

if ( $ARGV[0] ) {
	@xmlfiles=();
	my $i=0;
	foreach ( @ARGV ) {
		if ( $_ =~ /.xml$/ ) {
			$xmlfiles[$i]=$ARGV[$i];
			$i++;
		}
	}
}
if ( ! $xmlfiles[0] ) {
	print_help();
}

@xmlfiles=sort(@xmlfiles);


my $valid_global_parameters='passwordExpr|models|enableCommand|enablePrompt|pagerDisableCmd|deviceGroupName|jobs|usernameExpr|deviceGroupID|logoutCommand|pagerExpr|loginPrompt|unsavedChangesMessage|loginConfirmationExpr|showHostnameCommand';
my $required_global_parameters='enablePrompt|deviceGroupName|deviceGroupID|logoutCommand';
my $valid_job_parameter='comment|command|return|destConfigName|diffConfigIgnore|commandTimeout|jobType|localSourceFile|configExtension|dateFormat|localSourceCommand|localSourceCommandPort';
my $valid_job_types='copy_file|fetch_command_output|task|copy_local';
my %device_type_group_ids;

foreach my $xmlfile ( @xmlfiles) {

	if ( ! exists($xmlfiles{$xmlfile}) ) {
		print "ERROR: $xmlfile not found\n";
		next;
	}

	print "Checking $xmlfile...\n";
	# initialize parser object and parse the string
	my $parser = XML::Parser->new( ErrorContext => 2 );
	eval { $parser->parsefile( $xmlfile ); };

	# report any error that stopped parsing, or announce success
	if( $@ ) {
	    $@ =~ s/at \/.*?$//s;               # remove module line number
	    print STDERR ">>>>>>ERROR in '$xmlfile':\n$@\n";
		next;
	}


	# create object
	my $xml = new XML::Simple;

	# read XML file
	my $data = $xml->XMLin("$xmlfile");

#	print Dumper($data);

	my $xml_invalid=0;

	# check for required global parameters;
	foreach my $vals( keys %{$data} ) {
		if ( $vals !~ /^($valid_global_parameters)$/ ) {
			print ">>>>>>ERROR: unknown paramter: $vals - Parameter IGNORED\n";
		}
	}


	my @valid_global_parameters=split('\|',$valid_global_parameters);

	
	foreach my $param(@valid_global_parameters) {
		my $param_value=$data->{$param} || "";
		if ( $param =~ /^${required_global_parameters}$/ ) {
			if (ref $param eq 'HASH' || ! $param_value ) {
				print ">>>>>>ERROR: $param: no value - XML FILE INVALID\n";
				print "$xmlfile: IGNORED\n";
				$xml_invalid=1;
				last;
			} else {
				print "$param: $param_value\n" if $verbose;
			}
		} else {
			if (ref $param eq 'HASH') {
				print " $param: \n" if $verbose;
			} else {
				print " $param: $param_value\n" if $verbose;
			}
		}
	}

	next if $xml_invalid == 1;

	my $device_group_name = $data->{deviceGroupName} || "";
	my $device_group_id = $data->{deviceGroupID} || "";
	my $enable_prompt = $data->{enablePrompt} || "";
	$enable_prompt = "" if ref $enable_prompt eq 'HASH';
	my $logout_command = $data->{logoutCommand} || "";

	my $models = $data->{models} || "";
	my $login_prompt = $data->{loginPrompt} || "";
	my $login_prompt_empty=0;
	$login_prompt_empty=1 if ref $login_prompt eq 'HASH';
	my $enable_command = $data->{enableCommand} || "";
	my $username_expr = $data->{usernameExpr} || "";
	my $password_expr = $data->{passwordExpr} || "";
	my $pager_expr = $data->{pagerExpr} || "";
	my $pager_disable_command = $data->{pagerDisableCmd} || "";

	my $showHostnameCommand = $data->{showHostnameCommand} || "";
	$showHostnameCommand = "" if ref $showHostnameCommand eq 'HASH';


	$xmlfile =~ /^(\d+)_/;
	my $xmlfile_serial=$1 || "";
	if ( ! $xmlfile_serial ) {
		print ">>>>>>ERROR: Can not determine XML file's serial - XML FILE INVALID\n";
		print "$xmlfile: IGNORED\n";
		next;
	}
	if ( $xmlfile_serial ne $device_group_id ) {
		print ">>>>>>ERROR: Device Group ID and XML file's serial number are not identical - Please rename XML file or change the Device Group ID - XML FILE INVALID\n";
		print "$xmlfile: IGNORED\n";
		next;
	}

	if ( exists($device_type_group_ids{$device_group_id}) ) {
		print ">>>>>>ERROR: Dupicated Device Group ID $device_group_id. ID is already used by $device_type_group_ids{$device_group_id}\n";
		print "$xmlfile: IGNORED\n";
		next;
	}

	$device_type_group_ids{$device_group_id}=$xmlfile;

	if ( $login_prompt && ! $enable_prompt ) {

		print ">>>>>>ERROR: Mandatory attribute \"enablePrompt\" has no value. Please define an enable prompt (did you defined the optional login prompt instead?)\n";
		print "$xmlfile: IGNORED\n";
		next;
		
	} elsif ( ! $enable_prompt ) {
		print ">>>>>>ERROR: Mandatory attribute \"enablePrompt\" must have a value \n";
		print "$xmlfile: IGNORED\n";
		next;
	}

#	if ( $login_prompt_empty == 1 ) {
#		print ">>>>>>ERROR: Optional attribute \"loginPrompt\" without value. If this attribut is present it needs a value.\n";
#		print "$xmlfile: IGNORED\n";
#		next;
#	}

	## JOBS CHECK

	my @jobs=();
	while ( my ($key, $value) = each(%{ $data->{jobs}}) ) {
		push @jobs,"$key";
	}

#	my ($commands,$comment,$returns,$commands_count);
	my ($commands,$comment,$returns);


	foreach my $job_name ( @jobs ) {

		my @commands=();
		my @returns=();

		if ( $data->{jobs}{$job_name} =~ /^ARRAY/ ) {
			print ">>>>>>ERROR: Job: $job_name: duplicate Job name - job will be IGNORED\n";
			next;
		}
			
		my $invalid_job=0;

		next if $job_name eq "comment";

		if ( $data->{jobs}{$job_name}{jobType} && $data->{jobs}{$job_name}{jobType} eq "copy_local" ) {
			# "copy_local" must not have other parameter than comment, jobType and localSourceFile
			foreach my $vals( keys %{$data->{jobs}{$job_name}} ) {
				if ( $vals !~ /^(comment|jobType|localSourceFile|localSourceCommand|localSourceCommandPort)$/ ) {
					print ">>>>>>ERROR: Job: $job_name: Wrong parameter: $vals. Job type \"copy_local\" only allows the parameter jobType, comment, localSourceFile, localSourceCommand, localSourceCommandPort - Job will be ignored\n";
					$invalid_job=1;
					last;
				}
			}
            print "  $job_name: OK\n";
            next;
		}


		foreach my $vals( keys %{$data->{jobs}{$job_name}} ) {
			if ( $vals !~ /^($valid_job_parameter)$/ ) {
				print ">>>>>>ERROR: Job: $job_name: unknown paramter: $vals - Job will be ignored\n";
				$invalid_job=1;
			}
		}
		next if $invalid_job==1;

		$comment = $data->{jobs}{$job_name}{comment} || "";
		if ( ref $data->{jobs}{$job_name}{comment} eq 'ARRAY' ) {
			print ">>>>>>ERROR: Job: $job_name: only one comment per Job allowed - Job will be ignored\n";
			next;
		} elsif ( ref $data->{jobs}{$job_name}{comment} eq 'HASH' || ! $comment ) {
			print ">>>>>>ERROR: Job: $job_name: no comment for this job defined - Job will be ignored\n";
			next;
		}

		if ( ! exists($data->{jobs}{$job_name}{jobType}) || ref $data->{jobs}{$job_name}{jobType} eq 'HASH' ) {
			print ">>>>>>ERROR: Job: $job_name: no jobType defined - Job will be ignored\n";
			next;
		} else {
			if ( ref $data->{jobs}{$job_name}{jobType} eq 'ARRAY' ) {
				print ">>>>>>ERROR: Job: $job_name: only one jobType per Job allowed - Job will be ignored\n";
			} elsif ( $data->{jobs}{$job_name}{jobType} !~ /^($valid_job_types)$/ ) {
				print ">>>>>>ERROR: Job: $job_name: invalid jobType: $data->{jobs}{$job_name}{jobType} - Job will be ignored\n";
				next;
			}
		}

		if ( ! exists($data->{jobs}{$job_name}{command}) ) {
			print ">>>>>>ERROR: Job: $job_name: no commands defined - Job will be ignored\n";
			next;
		}
		if ( ! exists($data->{jobs}{$job_name}{return}) ) {
			print ">>>>>>ERROR: Job: $job_name: no return prompts defined - Job will be ignored\n";
			next;
		}

		my $commands_count=0;
		my $returns_count=0;
		my $command_array=0;
		my $returns_array=0;
		$commands=$data->{jobs}{$job_name}{command} || "";
		if (ref $data->{jobs}{$job_name}{command} eq 'ARRAY') {
			@commands=@$commands;
			$commands_count=scalar @$commands;
			$command_array=1;
		}
		

		$returns=$data->{jobs}{$job_name}{return} || "";
		if (ref $data->{jobs}{$job_name}{return} eq 'ARRAY') {
			@returns=@$returns;
			$returns_count=scalar @$returns;
			$returns_array=1;
		}

		if ( $command_array == 1 && $returns_array == 0 || $command_array == 0 && $returns_array == 1 ) {
			print ">>>>>>ERROR: Job: $job_name: there must be the same number of commands and returns - Job will be ignored\n";
			next;
		}

#		if ( $command_array == 1 ) {
#			print ">>>>>>ERROR: Job: $job_name: there must be the same number of commands and returns - Job will be ignored\n" if $commands_count ne $returns_count;
#		}

		if (ref $data->{jobs}{$job_name}{command} ne 'ARRAY') {
			push @commands,"$commands";
		}


		my $dest_config_name_found=0;
		foreach ( @commands ) {
			if ( $_ =~ /\[\[DEST_CONFIG_NAME\]\]/ ) {
				$dest_config_name_found=1;
			}
		}
		if ( $dest_config_name_found == 1 && ! $data->{jobs}{$job_name}{destConfigName} ) {
			print ">>>>>>ERROR: Job: $job_name: use of variable [[DEST_CONFIG_NAME]] but no attribute <destConfigName> found - Job will be ignored\n";
			next;
		}


		my $date_found=0;
		foreach ( @commands ) {
			if ( $_ =~ /\[\[DATE\]\]/ ) {
				$date_found=1;
			}
		}
		if ( $data->{jobs}{$job_name}{destConfigName} && $data->{jobs}{$job_name}{destConfigName} =~ /\[\[DATE\]\]/ ) {
			$date_found=1;
		}
		if ( $date_found == 1 && ! $data->{jobs}{$job_name}{dateFormat} ) {
			print ">>>>>>ERROR: Job: $job_name: use of variable [[DATE]] but no attribute <dateFormat> found - Job will be ignored\n";
			next;
		}

		
		my $hostname_found=0;
		foreach ( @commands ) {
			if ( $_ =~ /\[\[HOSTNAME\]\]/ ) {
				$hostname_found=1;
			}
		}
		if ( $data->{jobs}{$job_name}{destConfigName} && $data->{jobs}{$job_name}{destConfigName} =~ /\[\[HOSTNAME\]\]/ ) {
			$hostname_found=1;
		}
		if ( $hostname_found == 1 && ! $showHostnameCommand ) {
			print ">>>>>>ERROR: Job: $job_name: use of variable [[HOSTNAME]] but no global attribute <showHostnameCommand> found - Job will be ignored\n";
			next;
		}

		print "  $job_name: OK\n";
	}

	print "$xmlfile OK\n";
}



sub read_xml_files {
	my $xml_dir=".";

	my @files=();
	my %files=();

        opendir DIR, "$xml_dir" or die "Can't open vars dir \"$xml_dir\": $!\n";
        rewinddir DIR;
        while ( my $file = readdir(DIR) ) {
                if ( $file =~ /.xml$/ ) {
			push @files,"$file";
			$files{$file}=1;
                }
        }
        closedir DIR;

	return (\@files,\%files);
}

sub print_help {
	print "Usage: ./check_xml_files.pl [xml_file_list]\n";
	exit;
}

