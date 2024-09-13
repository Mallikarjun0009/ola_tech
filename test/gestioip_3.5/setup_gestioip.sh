#!/bin/sh

# Installation script for GestioIP 3.5

# Copyright (C) 2020 Marc Uebel

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

# setup_gestioip.sh VERSION 3.5.7.1 20220424


# GestioIP Apache cgi directory
GESTIOIP_CGI_DIR="gestioip"

#Version
VERSION="3.5"
# scipt base directory
SCRIPT_BASE_DIR="/usr/share/$GESTIOIP_CGI_DIR"
# Apache DocumentRoot
DOCUMENT_ROOT=""
# Apache daemon binary
APACHE_BIN=""
# Apache configuration file
APACHE_CONFIG_FILE=""
# Apache includes directory
APACHE_INCLUDE_DIRECTORY=""
# Apache configuration directory
APACHE_CONFIG_DIRECTORY=""
# Which user is running Apache web server
APACHE_USER=""
# Which group is running Apache web server
APACHE_GROUP=""
# Apache document root directory
APACHE_ROOT_DOCUMENT=""
# GestioIP Apache configuration
GESTIOIP_APACHE_CONF="`echo $GESTIOIP_CGI_DIR | tr '/' '_'`"
# Where is perl interpreter located
PERL_BIN=`which perl 2>/dev/null`
# Install dir
INSTALL_DIR=`pwd`
# Installation log-file
INSTALL_DATE=`date +%Y%m%d%H%M%S`
# actual version of netdisco MIBs
NETDISCO_MIB_VERSION="2.6"
# Where is hostname command located
HOSTNAME_BIN=`which hostname 2>/dev/null`
# Installation mode
INSTALLATION_MODE_PARAM=$1

SCRIPT=`realpath $0`
EXE_DIR=`dirname $SCRIPT`
SETUP_CONF="${EXE_DIR}/conf/setup.conf"

SETUP_LOG=$EXE_DIR/${INSTALL_DATE}.setup.log


SCRIPT_BIN_DIR="${SCRIPT_BASE_DIR}/bin"
SCRIPT_BIN_WEB_DIR="${SCRIPT_BASE_DIR}/bin/web"
SCRIPT_BIN_WEB_INCLUDE_DIR="${SCRIPT_BASE_DIR}/bin/web/include"
SCRIPT_BIN_INCLUDE_DIR="${SCRIPT_BASE_DIR}/bin/include"
SCRIPT_CONF_DIR="${SCRIPT_BASE_DIR}/etc"
SCRIPT_LOG_DIR="${SCRIPT_BASE_DIR}/var/log"
SCRIPT_TMP_DIR="${SCRIPT_BASE_DIR}/tmp"
SCRIPT_RUN_DIR="${SCRIPT_BASE_DIR}/var/run"
CM_CONFIGS_DIR="${SCRIPT_BASE_DIR}/conf"
CM_DEVICES_DIR="${SCRIPT_BASE_DIR}/var/devices"
SCRIPT_DATA_DIR="${SCRIPT_BASE_DIR}/var/data"
SCRIPT_CONF_APACHE_DIR="${SCRIPT_BASE_DIR}/etc/apache"

# clean logfile
echo > $SETUP_LOG

# read values from configuration file
echo -n "Reading setup configuration file $SETUP_CONF... "
. $SETUP_CONF
res=$?
if [ "$res" -eq 0 ]
then
	echo "OK"
    echo "Using the following variables from $SETUP_CONF:"
    cat $SETUP_CONF | grep -v '^#' | grep -v "^$" | sed 's/^GESTIOIP_USER_PASSWORD=.*/GESTIOIP_USER_PASSWORD=XXXXXX/' >> $SETUP_LOG
else
	echo "ERROR reading $SETUP_CONF"
	echo
    echo "Installation aborted!" >> $SETUP_LOG 2>&1
    echo "Installation aborted!"
    exit 1
fi

# Starting Installation
if [ "$CONFIRM_EXECUTION" = "yes" ]
then
	echo
	echo "This script will install GestioIP $VERSION on this computer"
	echo
	echo -n "Do you wish to continue [y]/n? "
	read input
	if [ -z "$input" ] || [ "$input" = "y" ] || [ "$input" = "Y" ] || [ "$input" = "yes" ]
	then
		echo "Starting installation"
	else
		echo "Installation aborted!" >> $SETUP_LOG 2>&1
		echo "Installation aborted!"
		echo
		exit 1
	fi

	# Are you root?
	MY_EUID="`id -u 2>/dev/null`"
	if [ $MY_EUID -ne 0 ]
	then
		echo
		echo "You must be root to run this script"
		echo
		echo
		echo -n "Are you root [n]/y? "
		read input
		if [ "$input" = "y" ] || [ "$input" = "Y" ] || [ "$input" = "yes" ]
		then
			echo "OK - Assuming that you are root"
		else
			echo "Installation aborted!"
			echo "Not root - Installation aborted!" >> $SETUP_LOG 2>&1
			echo
			exit 1
		fi
	fi

	if [ $? -ne "0" ]
	then
		echo
		echo "Can't open $SETUP_LOG"
		echo "Installation aborted!"
		echo
		exit 1
	fi

	echo "Storing log in file $SETUP_LOG" >> $SETUP_LOG
	echo >> $SETUP_LOG

else
	MY_EUID="`id -u 2>/dev/null`"
	if [ $MY_EUID -ne 0 ]
	then
		echo "Not root - Installation aborted!"
		echo "Not root - Installation aborted!" >> $SETUP_LOG 2>&1
		echo
		exit 1
	fi
fi

echo >> $SETUP_LOG
DATE=`date +%Y-%m-%d-%H-%M-%S`
echo "$DATE - Starting GestioIP $VERSION setup" >> $SETUP_LOG
echo -n "from folder $INSTALL_DIR" >> $SETUP_LOG

echo SETUP_CONF: $SETUP_CONF >> $SETUP_LOG


if [ -z ${INSTALLATION_MODE} ]
then
	INSTALLATION_MODE="DEFAULT"
fi

if [ ! -z ${INSTALLATION_MODE_PARAM} ]
then
    if [ ${INSTALLATION_MODE_PARAM} = "-i" ] || [ ${INSTALLATION_MODE_PARAM} = "--interactive" ]
    then
        INSTALLATION_MODE="INTERACTIVE"
    fi
fi
echo "Installation mode: $INSTALLATION_MODE" >> $SETUP_LOG


# Where is wget executable
WGET=`which wget 2>/dev/null`
if [ $? -ne 0 ]
then
	echo "wget not found" >> $SETUP_LOG
	echo "wget not found"
	echo
	echo "Please install wget and execute this script again"
	echo "Installation aborted!"
	echo
	exit 1
fi
WGET_NOCERT="$WGET --no-check-certificate"

# OS
OS=""
LINUX_DIST=""
LINUX_DIST_DETAIL=""
DEBIAN_VERSION=1
SUSE_DETAIL="none"
uname -a | grep -i linux >> $SETUP_LOG 2>&1
if [ $? -eq 0 ]
then
    OS=linux
    echo "OS: linux" >> $SETUP_LOG
fi
if [ "$OS" = "linux" ]
then
    cat /etc/issue | egrep -i "ubuntu|debian" >> $SETUP_LOG 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST="ubuntu"
        cat /etc/issue | egrep -i "debian" >> $SETUP_LOG 2>&1
        if [ $? -eq 0 ]
        then
            LINUX_DIST_DETAIL="debian"
			cat /etc/issue | egrep -i "Linux 9" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=9
            fi
			cat /etc/issue | egrep -i "Linux 10" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=10
            fi
			cat /etc/issue | egrep -i "Linux 11" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=11
            fi
			cat /etc/issue | egrep -i "Linux 12" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=12
            fi


        else
			cat /etc/issue | egrep -i "Ubuntu 17" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=9
            fi
			cat /etc/issue | egrep -i "Ubuntu 18" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=10
            fi
			cat /etc/issue | egrep -i "Ubuntu 19" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=11
            fi
			cat /etc/issue | egrep -i "Ubuntu 20" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=12
            fi
			cat /etc/issue | egrep -i "Ubuntu 22" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                DEBIAN_VERSION=12
            fi


        fi
        echo "Debian version: $DEBIAN_VERSION" >> $SETUP_LOG

    fi
    cat /etc/issue | egrep -i "suse" >> $SETUP_LOG 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST="suse"
        cat /etc/os-release | egrep -i "opensuse leap" >> $SETUP_LOG 2>&1
        if [ $? -eq 0 ]
        then
            SUSE_DETAIL="leap"
            echo "suse leap" >> $SETUP_LOG
        fi
    fi
    cat /etc/issue | egrep -i "fedora|redhat|centos|red hat" >> $SETUP_LOG 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST="fedora"
    fi
    cat /etc/issue | egrep -i "fedora" >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST_DETAIL="fedora"
    fi
    cat /etc/issue | egrep -i "redhat|red hat" >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST_DETAIL="redhat"
    fi
    cat /etc/issue | egrep -i "centos" >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
        LINUX_DIST_DETAIL="centos"
    fi
    echo "ISSUE: `cat /etc/issue`" >> $SETUP_LOG



    # If /etc/issue was customized so that the distribution name does
    # not appear use alternative way to determine linux distibution

    if [ -z "$LINUX_DIST" ]
    then
        if [ -e "/etc/debian_version" ];
        then
            LINUX_DIST="ubuntu"
        elif [ -e "/etc/SuSE-release" ];
        then
            LINUX_DIST="suse"
        elif [ -e "/etc/sles-release" ];
        then
            LINUX_DIST="suse"
        elif [ -e "/etc/SUSE-brand" ];
        then
            LINUX_DIST="suse"
	        cat /etc/os-release | egrep -i "opensuse leap" >> $SETUP_LOG 2>&1
            if [ $? -eq 0 ]
            then
                SUSE_DETAIL="leap"
                echo "SUSE_DETAIL: suse leap" >> $SETUP_LOG
            fi
        elif [ -e "/etc/fedora-release" ];
        then
            LINUX_DIST="fedora"
            LINUX_DIST_DETAIL="fedora"
        elif [ -e "/etc/redhat-release" ];
        then
            cat /etc/redhat-release | grep -i centos >/dev/null
            if [ $? -eq 0 ]
            then
                LINUX_DIST="fedora"
                LINUX_DIST_DETAIL="centos"
            fi
            cat /etc/redhat-release | egrep -i "redhat|red hat" >/dev/null
            if [ $? -eq 0 ]
            then
                LINUX_DIST="fedora"
                LINUX_DIST_DETAIL="redhat"
            fi
        fi
    fi

    echo "Distribution: $LINUX_DIST - $LINUX_DIST_DETAIL" >> $SETUP_LOG

    if [ -z "$LINUX_DIST" ]
    then
        echo "Can not determine the Linux distribution - installation aborted"
        echo "Can not determine the Linux distribution - installation aborted" >> $SETUP_LOG
        exit 1
    fi
fi

if [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ]
then
    REDHAT_VERSION=`cat /etc/redhat-release | sed 's/^.*\([0-9]\+\.[0-9]\+\).*/\1/g'` >> $SETUP_LOG 2>&1
    if [ -z "$REDHAT_VERSION" ]
    then
        echo "Can not determine Redhat version - using default values" >> $SETUP_LOG
    else
        echo "Found Redhat version: $REDHAT_VERSION" >> $SETUP_LOG
        REDHAT_MAIN_VERSION=`echo $REDHAT_VERSION | sed 's/\.[0-9]*$//'`
    fi
fi



### Install available packages START
##### XX0

if [ "$LINUX_DIST" = "fedora" ] || [ "$LINUX_DIST" = "ubuntu" ] || [ "$LINUX_DIST" = "suse" ]
then
    if [ "$INSTALLATION_MODE" = "DEFAULT" ]
	then
		PM_INSTALL="y"
	else
		echo
		echo "##### There are required Perl Modules missing #####"
		echo
		echo "The Setup can install the missing modules"
		echo
		echo -n "Do you wish that the Setup installs the missing Perl Modules now [y]/n? "
		read PM_INSTALL
		echo
	fi

    if [ -z "$PM_INSTALL" ] || [ "$PM_INSTALL" = "y" ] || [ "$PM_INSTALL" = "Y" ] || [ "$PM_INSTALL" = "yes" ]
    then
	    echo "AUTOMATIC INSTALLATION OF PERL MODULES" >> $SETUP_LOG
        echo

	    SNMP_INFO_AUTO_INSTALL=0

	    if [ "$LINUX_DIST" = "fedora" ]
        then

            if [ "$LINUX_DIST_DETAIL" = "fedora" ] 
            then
                REQUIRED_PERL_MODULE_MISSING="0"

            elif [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ]
            then
                echo "Installing EPEL Release"
                echo "Installing EPEL Release" >> $SETUP_LOG
                echo
                sudo yum -y install epel-release | tee -a $SETUP_LOG

                echo
                echo "Executing \"yum update\""
                echo "Executing yum update" >> $SETUP_LOG
                echo
                sudo yum -y update | tee -a $SETUP_LOG
                echo

                echo "Enabling PowerTools" >> $SETUP_LOG
                sudo yum config-manager --set-enable powertools >> $SETUP_LOG 2>&1
                res=$?
                if [ "$res" -eq 0 ]
                then
                    echo "Enabling powertools" >> $SETUP_LOG
                    sudo yum config-manager --set-enabled powertools >> $SETUP_LOG 2>&1
                fi
            fi

            COMMON_PACKAGES="httpd mod_perl mod_session apr-util-openssl mariadb-server make gcc net-snmp net-snmp-utils wget perl-Net-IP perl-DBI perl-DBD-mysql perl-DateManip perl-Date-Calc perl-TimeDate perl-MailTools perl-Time-HiRes perl-CGI perl-Text-Diff perl-Expect perl-XML-Simple perl-XML-Parser perl-MIME-tools perl-Crypt-CBC perl-Text-CSV perl-Perl-OSType perl-Module-Metadata perl-NetAddr-IP perl-JSON perl-Authen-SASL perl-MIME-Base64 perl-LDAP mod_ldap unzip"

            DATABASE_PACKAGES="mariadb"
			if [ "$INSTALL_DB" = "no" ]
            then
                DATABASE_PACKAGES=""
            fi

            echo -n "Checking for available packages (that takes a while)... "
            VERSION_PACKAGES=""
            for i in cronie checkpolicy perl-IO-Tty perl-Devel-GloblalDestruction perl-Role-Tiny perl-Crypt-Blowfish net-snmp-perl perl-Parallel-ForkManager perl-Spreadsheet-ParseExcel perl-SNMP-Info perl-Net-SNMP perl-Net-DNS perl-Crypt-RC4 perl-Digest-Perl-MD5 perl-Module-Runtime semodule_package perl-ExtUtils-MakeMaker; do sudo yum list all | grep $i >/dev/null; if [ "$?" -eq 0 ]; then VERSION_PACKAGES="${VERSION_PACKAGES} $i"; fi; done

            sudo yum list policycoreutils-python | grep policycoreutils-python && VERSION_PACKAGES="${VERSION_PACKAGES} policycoreutils-python"
            sudo yum list policycoreutils-python-utils | grep policycoreutils-python-utils && VERSION_PACKAGES="${VERSION_PACKAGES} policycoreutils-python-utils"

            echo " OK"

            echo "Executing yum install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES"
            echo "Executing yum install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES" >> $SETUP_LOG
            echo
            sudo yum -y install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES | tee -a $SETUP_LOG
            echo

	    elif [ "$LINUX_DIST" = "suse" ]
	    then

            SUSE_VERSION=`cat /etc/os-release | grep "VERSION=" | sed 's/VERSION="//' | sed 's/"$//'` >> $SETUP_LOG 2>&1
            echo "SUSE VERSION: ${SUSE_VERSION}" >> $SETUP_LOG

            # Add Perl devel repository (https://es.opensuse.org/Repositorios_comunitarios)
            REPO_URL=""
            if [ ! -z ${SUSE_VERSION} ]
            then
                if [ "${SUSE_VERSION}" = "15.0" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/openSUSE_Leap_15.0"
                elif [ "${SUSE_VERSION}" = "15.1" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/openSUSE_Leap_15.1"
                elif [ "${SUSE_VERSION}" = "15.2" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/openSUSE_Leap_15.2"
                elif [ "${SUSE_VERSION}" = "15.3" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/openSUSE_Leap_15.3"
                elif [ "${SUSE_VERSION}" = "12-SP4" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/SEL_12_SP4"
                elif [ "${SUSE_VERSION}" = "15" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/SEL_15"
                elif [ "${SUSE_VERSION}" = "15-SP1" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/SEL_15_SP1"
                elif [ "${SUSE_VERSION}" = "15-SP2" ]
                then
                    REPO_URL="http://download.opensuse.org/repositories/devel:/languages:/perl/SEL_15_SP2"
                fi
            fi
            if [ ! -z ${REPO_URL} ]
            then
                echo "Adding devel:lang:perl repository"
                echo "Adding repository: $REPO_URL" >> $SETUP_LOG
                sudo zypper ar -f -g -n "perl" ${REPO_URL} perl >> $SETUP_LOG 2>&1
            else
                echo "Could not determine REPO_URL - devel:lang:perl repository not added" >> $SETUP_LOG
            fi

            COMMON_PACKAGES="apache2 apache2-mod_perl apache2-utils mariadb-client mariadb-errormessages make snmp-mibs net-snmp perl-SNMP perl-DBD-mysql perl-DBI perl-Net-IP perl-libwww-perl perl-MailTools perl-Time-modules perl-Date-Calc perl-Date-Manip perl-Net-DNS perl-Text-Diff perl-Expect perl-XML-Simple perl-XML-Parser perl-Crypt-CBC perl-Crypt-Blowfish perl-Text-CSV perl-Module-Metadata perl-NetAddr-IP perl-JSON perl-CGI perl-Authen-SASL cronie perl-ldap"

            DATABASE_PACKAGES="mariadb"
			if [ "$INSTALL_DB" = "no" ]
            then
                DATABASE_PACKAGES=""
            fi

            echo -n "Checking for available packages (that takes a while)... "
            VERSION_PACKAGES=""
            for i in perl-Crypt-RC4 perl-Spreadsheet-ParseExcel perl-MIME-Base64; do sudo zypper packages | grep $i >/dev/null; if [ "$?" -eq 0 ]; then VERSION_PACKAGES="${VERSION_PACKAGES} $i"; fi; done
            echo " OK"

            echo "Executing zypper install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES"
            echo "Executing zypper install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES" >> $SETUP_LOG
            echo
            sudo zypper --non-interactive install $COMMON_PACKAGES $VERSION_PACKAGES $DATABASE_PACKAGES | tee -a $SETUP_LOG


	    elif [ "$LINUX_DIST" = "ubuntu" ]
	    then

            export DEBIAN_FRONTEND=noninteractive

            if [ "$LINUX_DIST_DETAIL" != "debian" ]
            then
                echo "Enabling Multiverse and Universe repositories"
                echo "Enabling Multiverse and Universe repositories" >> $SETUP_LOG

                sudo apt-get -y install software-properties-common >> $SETUP_LOG
                sudo add-apt-repository universe | tee -a $SETUP_LOG
                sudo add-apt-repository multiverse | tee -a $SETUP_LOG
                echo
                echo "Executing \"sudo apt-get update\""
                sudo apt-get update | tee -a $SETUP_LOG
            fi

            dpkg -l | grep apt-utils >> $SETUP_LOG 2>&1
            res=$?
            if [ "$res" -ne 0 ]
            then
                sudo apt-get -y install apt-utils libterm-readline-perl-perl >> $SETUP_LOG
            fi
            
            echo -n "Checking for available packages (that takes a while)... "
            VERSION_PACKAGES=""
            for i in snmp-mibs-downloader; do sudo apt-cache search --names-only $i | grep $i >/dev/null; if [ "$?" -eq 0 ]; then VERSION_PACKAGES="${VERSION_PACKAGES} $i"; fi; done
            echo " OK"

            LIBTIME_PACKAGE="libtime-modules-perl"
            if [ "$LINUX_DIST_DETAIL" = "debian" ]
            then    
                if [ "$DEBIAN_VERSION" -eq 9 ]
                then
                    LIBTIME_PACKAGE=""
                    BASE_PACKAGES="make mysql-client apache2 apache2-utils libapache2-mod-perl2 snmp wget"
                    DATABASE_PACKAGES="mysql-server"
                fi
                if [ "$DEBIAN_VERSION" -ge 10 ]
                then
                    LIBTIME_PACKAGE=""
                    BASE_PACKAGES="make mariadb-server mariadb-client apache2 apache2-utils libapache2-mod-perl2 snmp wget"
                    DATABASE_PACKAGES="mariadb-server"
                fi

                SETCAP=`which setcap` >> $SETUP_LOG 2>&1
                res=$?
                if [ "$res" -eq 0 ]
                then
                    echo "SETTING cap_net_raw=ep for 'ping'"
                    echo "SETTING cap_net_raw=ep for 'ping'" >> $SETUP_LOG
                    $SETCAP cap_net_raw=ep $(which ping) >> $SETUP_LOG 2>&1
                fi

            else
                BASE_PACKAGES="make mysql-client apache2 apache2-utils libapache2-mod-perl2 snmp wget"
                DATABASE_PACKAGES="mysql-server"
            fi

			if [ "$DEBIAN_VERSION" -ge 11 ]
            then
                LIBTIME_PACKAGE="libtime-parsedate-perl"
            fi

            TOOL_PACKAGES=""
            if [ "$INSTALL_TOOLS" = "yes" ]
            then    
                TOOL_PACKAGES="net-tools iputils-ping dnsutils vim netcat"
            fi

            COMMON_PACKAGES="libdbi-perl libdbd-mysql-perl libparallel-forkmanager-perl libwww-perl libnet-ip-perl libspreadsheet-parseexcel-perl libsnmp-perl libdate-manip-perl libdate-calc-perl libmailtools-perl libnet-dns-perl libsnmp-info-perl libgd-graph-perl libtext-diff-perl libexpect-perl libxml-parser-perl libxml-simple-perl libcrypt-cbc-perl libmime-base64-urlsafe-perl libcrypt-blowfish-perl libtext-csv-perl libnetaddr-ip-perl libmoo-perl libjson-perl libmime-base64-urlsafe-perl libauthen-sasl-perl libnet-ldap-perl libcgi-pm-perl cron"

			if [ "$INSTALL_DB" = "no" ]
            then
                DATABASE_PACKAGES=""
            fi

           echo
           echo "Executing apt-get -y install $BASE_PACKAGES $COMMON_PACKAGES $DATABASE_PACKAGES $VERSION_PACKAGES $LIBTIME_PACKAGE $TOOL_PACKAGES"
           echo "Executing apt-get -y install $BASE_PACKAGES $COMMON_PACKAGES $DATABASE_PACKAGES $VERSION_PACKAGES $LIBTIME_PACKAGE $TOOL_PACKAGES" >> $SETUP_LOG
           echo
           sudo apt-get -y install $BASE_PACKAGES $COMMON_PACKAGES $DATABASE_PACKAGES $VERSION_PACKAGES $LIBTIME_PACKAGE $TOOL_PACKAGES | tee -a $SETUP_LOG

           REQUIRED_PERL_MODULE_MISSING="0"
	    fi


        # MODULE CHECK START

        INSTALL_MOD_EXCEL="yes"

        REQUIRED_PERL_MODULE_MISSING=0

        echo "Checking for DBI PERL module" >> $SETUP_LOG
        $PERL_BIN -mDBI -e 'print "PERL module DBI is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for DBD-mysql PERL module" >> $SETUP_LOG
        $PERL_BIN -mDBD::mysql -e 'print "PERL module DBD-mysql is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for Net::IP PERL module" >> $SETUP_LOG
        $PERL_BIN -mNet::IP -e 'print "PERL module Net::IP is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for Parallel::ForkManager PERL module" >> $SETUP_LOG
        PARALLEL_FORKMANAGER_MISSING="0"
        $PERL_BIN -mParallel::ForkManager -e 'print "PERL module Parallel::ForkManager is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
            PARALLEL_FORKMANAGER_MISSING=1
        fi

        echo "Checking for SNMP PERL module" >> $SETUP_LOG
        $PERL_BIN -mSNMP -e 'print "PERL module SNMP is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for SNMP::Info PERL module" >> $SETUP_LOG
        SNMP_INFO_MISSING="0"
        $PERL_BIN -mSNMP::Info -e 'print "PERL module SNMP::Info is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
            SNMP_INFO_MISSING="1"
            SNMP_INFO_AUTO_INSTALL="1"
        fi

        MAIL_MAILER_MISSING="0"
        echo "Checking for Mail::Mailer PERL module" >> $SETUP_LOG
        $PERL_BIN -mMail::Mailer -e 'print "PERL module Mail::Mailer is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
            MAIL_MAILER_MISSING="1"
        fi


        HI_RES_MISSING="0"
        echo "Checking for Time::HiRes PERL module" >> $SETUP_LOG
        $PERL_BIN -mTime::HiRes -e 'print "PERL module Time::HiRes is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
            HI_RES_MISSING="1"
        fi

        echo "Checking for Date::Calc PERL module" >> $SETUP_LOG
        $PERL_BIN -mDate::Calc -e 'print "PERL module Date::Calc is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for Date::Manip PERL module" >> $SETUP_LOG
        $PERL_BIN -mDate::Manip -e 'print "PERL module Date::Manip is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
        fi

        echo "Checking for Net::DNS PERL module" >> $SETUP_LOG
        NET_DNS_MISSING="0"
        $PERL_BIN -mNet::DNS -e 'print "PERL module Net::DNS is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            REQUIRED_PERL_MODULE_MISSING=1
            NET_DNS_MISSING="1"
        fi

        if [ "$INSTALL_MOD_EXCEL" = "yes" ]
        then
           PARSE_EXCEL_MISSING="0"
           echo "Checking for Spreadsheet::ParseExcel PERL module" >> $SETUP_LOG
           $PERL_BIN -mSpreadsheet::ParseExcel -e 'print "PERL module Spreadsheet::ParseExcel is available\n"' >> $SETUP_LOG 2>&1
           if [ $? -ne 0 ]
           then
              REQUIRED_PERL_MODULE_MISSING=1
              PARSE_EXCEL_MISSING=1
           fi

           echo "Checking for OLE::Storage_Lite PERL module" >> $SETUP_LOG
           OLE_STORAGE_LIGHT_MISSING="0"
           $PERL_BIN -mOLE::Storage_Lite -e 'print "PERL module OLE::Storage_Lite is available\n"' >> $SETUP_LOG 2>&1
           if [ $? -ne 0 ]
           then
              REQUIRED_PERL_MODULE_MISSING=1
              OLE_STORAGE_LIGHT_MISSING=1
           fi
        fi

        echo "Checking for Text::Diff PERL module" >> $SETUP_LOG
        Text_Diff_MISSING="0"
        $PERL_BIN -mText::Diff -e 'print "PERL module Text::Diff is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           Text_Diff_MISSING=1
        fi

        echo "Checking for Expect PERL module" >> $SETUP_LOG
        EXPECT_MISSING="0"
        $PERL_BIN -mExpect -e 'print "PERL module Expect is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           EXPECT_MISSING=1
        fi

        echo "Checking for XML::Simple PERL module" >> $SETUP_LOG
        XML_SIMPLE_MISSING="0"
        $PERL_BIN -mXML::Simple -e 'print "PERL module XML::Simple is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           XML_SIMPLE_MISSING=1
        fi

        echo "Checking for XML::Parser PERL module" >> $SETUP_LOG
        XML_PARSER_MISSING="0"
        $PERL_BIN -mXML::Parser -e 'print "PERL module XML::Parser is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           XML_PARSER_MISSING=1
        fi

        echo "Checking for Digest::MD5 PERL module" >> $SETUP_LOG
        DIGEST_MD5_MISSING="0"
        $PERL_BIN -mDigest::MD5 -e 'print "PERL module Digest::MD5 is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           DIGEST_MD5_MISSING=1
        fi

        echo "Checking for Crypt::CBC PERL module" >> $SETUP_LOG
        CRYPT_CBC_MISSING="0"
        $PERL_BIN -mCrypt::CBC -e 'print "PERL module Crypt::CBC is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           CRYPT_CBC_MISSING=1
        fi

        echo "Checking for Crypt::Blowfish PERL module" >> $SETUP_LOG
        CRYPT_BLOWFISH_MISSING="0"
        $PERL_BIN -mCrypt::Blowfish -e 'print "PERL module Crypt::Blowfish is available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           CRYPT_BLOWFISH_MISSING=1
        fi

        echo "Checking for MIME::Base64 module" >> $SETUP_LOG
        MIME_BASE64_MISSING="0"
        $PERL_BIN -mMIME::Base64 -e 'print "PERL module MIME::Base64 available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           MIME_BASE64_MISSING=1
        fi
        echo

        echo "Checking for Text::CSV module" >> $SETUP_LOG
        TEXT_CSV_MISSING="0"
        $PERL_BIN -mText::CSV -e 'print "PERL module Text::CSV available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
           REQUIRED_PERL_MODULE_MISSING=1
           TEXT_CSV_MISSING=1
        fi

        # MODULE CHECK END



		if [ "$REQUIRED_PERL_MODULE_MISSING" -ne 0 ]
		then

		echo "Checking for MAKE" >> $SETUP_LOG
		MAKE=`which make 2>/dev/null`

		if [ -z "$MAKE" ]
		then
		    echo
		    echo "MAKE not found!"
		    echo "MAKE not found" >> $SETUP_LOG
		else
		    echo
		    echo "Found MAKE at <$MAKE>" >> $SETUP_LOG
		fi

        if [ "$INSTALLATION_MODE" = "INTERACTIVE" ]
        then
            # Ask user's confirmation
            res=0
            while [ $res -eq 0 ]
            do
                echo -n "Where is MAKE binary [$MAKE]? "
                read input
                if [ -n "$input" ]
                then
                    MAKE_INPUT="$input"
                else
                    MAKE_INPUT=$MAKE
                fi
                # Ensure file exists and is executable
                if [ -x "$MAKE_INPUT" ]
                then
                    res=1
                else
                    echo "*** ERROR: $MAKE_INPUT is not executable!" >> $SETUP_LOG 2>&1
                    echo "*** ERROR: $MAKE_INPUT is not executable!"
                    res=0
                fi
                # Ensure file is not a directory
                if [ -d "$MAKE_INPUT" ]
                then
                    echo "*** ERROR: $MAKE_INPUT is a directory!" >> $SETUP_LOG 2>&1
                    echo "*** ERROR: $MAKE_INPUT is a directory!"
                    res=0
                fi
            done

            if [ -n "$MAKE_INPUT" ]
            then
                MAKE="$MAKE_INPUT"
            fi

            echo "OK, using MAKE $MAKE"
            echo "Using MAKE $MAKE" >> $SETUP_LOG
        fi

		if [ ! -x "$WGET" ]
		then
			echo
			echo "*** ERROR: wget not found" >> $SETUP_LOG
			echo "*** ERROR: wget not found"
			echo
			echo "Please install wget (or specify wget binary in \$WGET at the beginning of this script)"
			echo "and execute setup_gestioip.sh again"
			echo
			echo "Installation aborted" >> $SETUP_LOG
			echo "Installation aborted"
			echo
			exit 1
		fi

        for i in OLE-Storage_Lite Moo-Role Sub-Quote Module-Runtime Role-Tiny Parallel-ForkManager Perl-OSType Module-Build SNMP-Info Algorithm-Diff Text-Diff MailTools Net-DNS IO-Tty Expect HiRes Crypt-Blowfish ParseExcel
        do
			if [ $i = "ParseExcel" ] && [ "$PARSE_EXCEL_MISSING" -eq "1" ] && [ "$INSTALL_MOD_EXCEL" = "yes" ]
			then
				sudo rm -r Spreadsheet::ParseExcel* > /dev/null 2>&1
				echo "Installing Spreadsheet-ParseExcel" >> $SETUP_LOG
				echo "### Installing Spreadsheet-ParseExcel"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Spreadsheet::ParseExcel >> $SETUP_LOG 2>&1

			elif [ $i = "Crypt-Blowfish" ] && [ "$CRYPT_BLOWFISH_MISSING" -eq "1" ]
			then
				sudo rm -r Crypt::Blowfish* > /dev/null 2>&1
				echo "Installing Crypt-Blowfish" >> $SETUP_LOG
				echo "### Installing Crypt-Blowfish"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Crypt::Blowfish >> $SETUP_LOG 2>&1

			elif [ $i = "OLE-Storage_Lite" ] && [ "$OLE_STORAGE_LIGHT_MISSING" -eq "1" ] && [ "$INSTALL_MOD_EXCEL" = "yes" ]
			then
				sudo rm -r OLE::Storage_Lite* > /dev/null 2>&1
				echo "Installing OLE-Storage_Lite" >> $SETUP_LOG
				echo "### Installing OLE-Storage_Lite"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/OLE::Storage_Lite >> $SETUP_LOG 2>&1

			elif [ "$PARALLEL_FORKMANAGER_MISSING" -eq "1" ] && ( [ $i = "Parallel-ForkManager" ] || [ $i = "Moo-Role" ] || [ $i = "Sub-Quote" ] || [ $i = "Module-Runtime" ] || [ $i = "Role-Tiny" ] )
			then
				if [ $i = "Moo-Role" ]
				then
                    $PERL_BIN -mMoo::Role -e 'print "PERL module Moo::Role is available\n"' >> $SETUP_LOG 2>&1
                    res=$?
                    if [ "$res" -ne 0 ]
                    then
                        sudo rm -r Moo* > /dev/null 2>&1
                        echo "Installing Moo" >> $SETUP_LOG
                        echo "### Installing Moo"
                        $WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Moo::Role >> $SETUP_LOG 2>&1
                    fi


				elif [ $i = "Sub-Quote" ]
				then
                    $PERL_BIN -mSub::Quote -e 'print "PERL module Sub::Quote is available\n"' >> $SETUP_LOG 2>&1
                    res=$?
                    if [ "$res" -ne 0 ]
                    then
                        sudo rm -r Sub-Quote* > /dev/null 2>&1
                        echo "Installing Sub-Quote" >> $SETUP_LOG
                        echo "### Installing Sub-Quote"
                        $WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Sub::Quote >> $SETUP_LOG 2>&1
                    fi

			   elif [ $i = "Module-Runtime" ]
			   then
                    $PERL_BIN -mModule::Runtime -e 'print "PERL module Module::Runtime is available\n"' >> $SETUP_LOG 2>&1
                    res=$?
                    if [ "$res" -ne 0 ]
                    then
                        echo "RES Runtime: $res" >> $SETUP_LOG
						sudo rm -r Module::Runtime* > /dev/null 2>&1
						echo "Installing Module-Runtime" >> $SETUP_LOG
						echo "### Installing Module-Runtime"
						$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Module::Runtime >> $SETUP_LOG 2>&1
                    fi

				elif [ $i = "Role-Tiny" ]
				then
                    $PERL_BIN -mRole::Tiny -e 'print "PERL module Role::Tiny is available\n"' >> $SETUP_LOG 2>&1
                    res=$?
                    if [ "$res" -ne 0 ]
                    then
						sudo rm -r Role::Tiny* > /dev/null 2>&1
						echo "Installing Role-Tiny" >> $SETUP_LOG
						echo "### Installing Role-Tiny"
						$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Role::Tiny >> $SETUP_LOG 2>&1
                    fi


				elif [ $i = "Parallel-ForkManager" ]
				then
					sudo rm -r Parallel::ForkManager* > /dev/null 2>&1
					echo "Installing Parallel-ForkManager" >> $SETUP_LOG
					echo "### Installing Parallel-ForkManager"
					$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Parallel::ForkManager >> $SETUP_LOG 2>&1
				fi
			elif [ $i = "MailTools" ] && [ "$MAIL_MAILER_MISSING" -eq "1" ]
			then
				sudo rm -r MailTools* > /dev/null 2>&1

				echo "### Installing Mail-Mailer" >> $SETUP_LOG
				echo "### Installing Mail-Mailer"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/distribution/MailTools/lib/MailTools.pod >> $SETUP_LOG 2>&1

			elif [ $i = "Perl-OSType" ] && [ "$SNMP_INFO_MISSING" -eq "1" ]
			then
				sudo rm -r Perl::OSType* > /dev/null 2>&1
				echo "Installing Perl::OSType" >> $SETUP_LOG
				echo "### Installing Perl::OSType"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Perl::OSType >> $SETUP_LOG 2>&1
			elif [ $i = "Module-Build" ] && [ "$SNMP_INFO_MISSING" -eq "1" ]
			then
				sudo rm -r Module::Build* > /dev/null 2>&1
				echo "Installing Module-Build" >> $SETUP_LOG
				echo "### Installing Module-Build"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Module::Build >> $SETUP_LOG 2>&1
			elif [ $i = "SNMP-Info" ] && [ "$SNMP_INFO_MISSING" -eq "1" ]
			then
				if [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ]
				then
					$PERL_BIN -mSNMP -e 'print "PERL module SNMP is available\n"' >> $SETUP_LOG 2>&1
					if [ $? -ne 0 ]
					then
						# net-snmp is not available as package for RH8/Centos8.
						echo "### Installing net-snmp. This will take a while..."
						echo "### Installing net-snmp." >> $SETUP_LOG

#						sudo rm -r net-snmp-5.8* > /dev/null 2>&1
						$WGET_NOCERT -w 2 -T 8 -t 6 https://sourceforge.net/projects/net-snmp/files/net-snmp/5.8/net-snmp-5.8.zip >> $SETUP_LOG 2>&1
                        if [ -e ./net-snmp-5.8.zip ]
                        then
                            unzip net-snmp-5.8.zip
                            cd net-snmp-5.8
                            ./configure --with-perl-modules --with-defaults
                            make
                            sudo make install
                            cd ..
                        else
                            echo
                            echo "There was a problme downloading net-snmp-5.8.zip. Just run the script again. If this message appears again, download net-snmp-5.8.zip manually (wget https://sourceforge.net/projects/net-snmp/files/net-snmp/5.8/net-snmp-5.8.zip), copy it to $EXE_DIR and run setup_gestioip.sh again"
                            echo
                            echo "Installation aborded"
                            echo "Cound not download net-snmp-5.8" >> $SETUP_LOG
                            exit 1
                        fi
					fi
				fi

				sudo rm -r SNMP::Info* > /dev/null 2>&1
				echo "Installing SNMP-Info" >> $SETUP_LOG
				echo "### Installing SNMP-Info"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/SNMP::Info >> $SETUP_LOG 2>&1

			elif [ "$Text_Diff_MISSING" -eq "1" ] && ( [ $i = "Algorithm-Diff" ] || [ $i = "Text-Diff" ] )
			then
				if [ $i = "Algorithm-Diff" ]
				then
					sudo rm -r Algorithm::Diff* > /dev/null 2>&1
					echo "Installing Algorithm-Diff" >> $SETUP_LOG
					echo "### Installing Algorithm-Diff"
					$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Algorithm::Diff >> $SETUP_LOG 2>&1
			        elif [ $i = "Text-Diff" ]
			        then
					sudo rm -r Text::Diff* > /dev/null 2>&1
					echo "Installing Text-Diff" >> $SETUP_LOG
					echo "### Installing Text-Diff"
					$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Text::Diff >> $SETUP_LOG 2>&1
				fi

			elif [ $i = "Net-DNS" ] && [ "$NET_DNS_MISSING" -eq "1" ]
			then
				sudo rm -r Net-DNS* > /dev/null 2>&1
				echo "Installing Net-DNS" >> $SETUP_LOG
				echo "### Installing Net-DNS"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Net::DNS >> $SETUP_LOG 2>&1

			elif [ "$EXPECT_MISSING" -eq "1" ] && ( [ $i = "IO-Tty" ] || [ $i = "Expect" ] ) 
			then
				if [ $i = "IO-Tty" ]
				then
					sudo rm -r IO* > /dev/null 2>&1
					echo "Installing IO-Tty" >> $SETUP_LOG
					echo "### Installing IO-Tty"
					$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/IO::Tty >> $SETUP_LOG 2>&1
				elif [ $i = "Expect" ]
				then
					sudo rm -r Expect* > /dev/null 2>&1
					echo "Installing Expect" >> $SETUP_LOG
					echo "### Installing Expect"
					$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Expect >> $SETUP_LOG 2>&1
				fi
			elif [ $i = "HiRes" ] && [ "$HI_RES_MISSING" -eq "1" ]
			then
				sudo rm -r Time::HiRes* > /dev/null 2>&1
				echo "Installing Time-HiRes" >> $SETUP_LOG
				echo "### Installing Time-HiRes"
				$WGET_NOCERT -w 2 -T 8 -t 6 https://metacpan.org/pod/Time::HiRes >> $SETUP_LOG 2>&1

			else
				continue
			fi

            if [ $i = "ParseExcel" ]
            then
                    MOD_NAME="Spreadsheet::ParseExcel"
            elif [ $i = "MailTools" ]
            then
                    MOD_NAME="MailTools.pod"
            else
                    MOD_NAME=`echo $i | sed 's/-/::/g'`
            fi

            URL=`grep downloadUrl $MOD_NAME 2>>$SETUP_LOG | sed 's/.*href="//' | sed 's/">.*//'`
            echo "$MOD_NAME - $URL" >>$SETUP_LOG

            FILE=`echo $URL | sed 's/.*\///'`

			if [ -z "$URL" ]
			then
				echo "Can't fetch filename for $i - skipping installation of $i" >> $SETUP_LOG 
				echo "Can't fetch filename for $i - skipping installation of $i"
				echo 
				echo "##### Please install $i manually #####"
				echo
				continue
			fi

			URL_COMPL=${URL}


			echo -n "Downloading $FILE from CPAN..." >> $SETUP_LOG
			echo -n "Downloading $FILE from CPAN..."

			$WGET_NOCERT -w 2 -T 8 -t 6 $URL_COMPL >> $SETUP_LOG  2>&1

			if [ $? -ne 0 ]
			then
				echo " Failed" >> $SETUP_LOG
				echo " Failed"
				echo "Skipping installation of $FILE"
				echo 
				echo "##### Please install $FILE manually and execute setup_gestioip.sh again#####"
				echo
				continue
			else
				echo " OK" >> $SETUP_LOG
				echo " OK" 
			fi

			echo -n "Installation of $FILE"

			echo $URL | grep "tar.gz" >/dev/null 2>&1
			if [ $? -eq 0 ]
			then
				tar vzxf $FILE >> $SETUP_LOG 2>&1
				if [ $? -ne 0 ]
				then
					echo "FAILED"
					echo "Failed to unpack $FILE" >> $SETUP_LOG
					echo "Failed to unpack $FILE"
					echo "Skipping installation of $FILE"
					echo
					echo "##### Please install $FILE manually and execute setup_gestioip.sh again #####"
					echo
					continue
				fi
				DIR=`echo $FILE | sed 's/.tar.gz//'`
			fi

			echo $URL | grep ".zip" >/dev/null 2>&1
			if [ $? -eq 0 ]
			then
				unzip $FILE  >> $SETUP_LOG 2>&1
				if [ $? -ne 0 ]
				then
					echo "FAILED"
					echo "Failed to unpack $FILE" >> $SETUP_LOG
					echo "Failed to unpack $FILE"
					echo "Skipping installation of $FILE"
					echo "Please install $FILE manually and execute setup_gestioip.sh again"
					echo
					continue
				fi
				DIR=`echo $FILE | sed 's/.zip//'`
			fi

			if [ -d "$DIR" ]
			then
				cd $DIR
				if [ $? -eq 0 ]
				then
                    if [ $i = "Net-DNS" ]
                    then
                            echo "executing \"perl Makefile.PL --noxs --no-online-tests --no-IPv6-tests\"" >> $SETUP_LOG 2>&1
                            sudo perl Makefile.PL --noxs --no-online-tests --no-IPv6-tests >> $SETUP_LOG 2>&1
                    elif [ $i = "SNMP-Info" ]
                    then
                            echo "executing \"perl Build.PL\"" >> $SETUP_LOG 2>&1
                            sudo perl Build.PL >> $SETUP_LOG 2>&1
                    else
                            echo "executing \"perl Makefile.PL\"" >> $SETUP_LOG 2>&1
                            sudo perl Makefile.PL >> $SETUP_LOG 2>&1
                    fi

					if [ $? -ne 0 ]
					then
						echo "FAILED"
						echo "Failed to create Makefile for $DIR" >> $SETUP_LOG
						echo "Failed to create Makefile for $DIR"
						echo "Skipping installation of $DIR"
						echo 
						echo "##### Please install $DIR manually and execute setup_gestioip.sh again #####"
						echo
						cd ..
						continue
					fi

                    if [ $i != "SNMP-Info" ]
                    then
                        echo "executing \"$MAKE\"" >> $SETUP_LOG 2>&1
                        MAKE_OUT=`sudo $MAKE 2>&1`
                        if [ $? -ne 0 ]
                        then
                            echo $MAKE_OUT >> $SETUP_LOG
                        fi

                        echo "executing \"sudo $MAKE install\"" >> $SETUP_LOG 2>&1
                        MAKE_OUT=`sudo $MAKE install 2>&1`
                        if [ $? -ne 0 ]
                        then
                            echo $MAKE_OUT >> $SETUP_LOG

                            echo "FAILED"
                            echo "Failed to execute make install for $DIR" >> $SETUP_LOG
                            echo "Failed to execute make install for $DIR"
                            echo "Skipping installation of $FILE"
                            echo
                            echo "###### Please install $DIR manually and execute setup_gestioip.sh again ####"
                            echo
                            cd ..
                            continue
                        fi
                    else
                        # SNMP-Info

                        echo "executing \"sudo ./Build install\"" >> $SETUP_LOG 2>&1
                        MAKE_OUT=`sudo ./Build install 2>&1`
                        if [ $? -ne 0 ]
                        then
                            echo $MAKE_OUT >> $SETUP_LOG

                            echo "FAILED"
                            echo "Failed to execute ./Build install for $DIR" >> $SETUP_LOG
                            echo "Failed to execute ./Build install for $DIR"
                            echo "Skipping installation of $FILE"
                            echo
                            echo "###### Please install $DIR manually and execute setup_gestioip.sh again ####"
                            echo
                            cd ..
                            continue
                        fi
                    fi
				fi
			else
				echo "FAILED"
				echo "$DIR in not a directory" >> $SETUP_LOG
				echo "$DIR in not a directory"
				echo "Skipping installation of $FILE"
				echo "Please install $FILE manually"
				echo
				continue
			fi

			cd ..

			echo " SUCCESSFUL"
			if [ $i = "SNMP-Info" ] && [ "$SNMP_INFO_MISSING" -eq "1" ]
			then
                if [ "$INSTALLATION_MODE" = "DEFAULT" ]
				then
					PM_NETDISCO_MIBS="Y"
				else
					echo
					echo "SNMP::Info needs the Netdisco MIBs to be installed"
					echo "Setup can download MIB files (11MB) and install it under ${SCRIPT_BASE_DIR}/mibs"
					echo
					echo "If Netdisco MIBs are already installed on this server type \"no\" and"
					echo "specify path to MIBs via frontend Web (manage->GestioIP) after finishing"
					echo "the installation"
					echo
					echo -n "Do you wish that the Setup installs required MIBs now [y]/n? "
					read PM_NETDISCO_MIBS
					echo
				fi

				if [ -z "$PM_NETDISCO_MIBS" ] || [ "$PM_NETDISCO_MIBS" = "y" ] || [ "$PM_NETDISCO_MIBS" = "Y" ] || [ "$PM_NETDISCO_MIBS" = "yes" ]
				then
					rm -r ./netdisco-mibs-${NETDISCO_MIB_VERSION}* >> $SETUP_LOG 2>&1
					echo "Downloading Netdisco MIBs (this may take several minutes)... " >> $SETUP_LOG
					echo -n "Downloading Netdisco MIBs (this may take several minutes)... "
					$WGET_NOCERT -w 2 -T 15 -t 6 http://sourceforge.net/projects/netdisco/files/netdisco-mibs/${NETDISCO_MIB_VERSION}/netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz >> $SETUP_LOG 2>&1
					if [ $? -ne 0 ]
					then
						echo "FAILED"
						echo "Installation of Netdisco MIBs FAILED"
						echo "Consult setup.log for details"
						echo
						echo "Please install Netdisco-MIBs v${NETDISCO_MIB_VERSION} manually after installation has finished ***"
						echo "(Download netdisco-mibs from https://sourceforge.net/projects/netdisco/files/netdisco-mibs/)"
						echo "and copy the content of netdisco-mibs-${NETDISCO_MIB_VERSION}/ to ${SCRIPT_BASE_DIR}/mibs/"
						echo
						continue
						
					else
						if [ -e "./netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz" ]
						then
							echo "OK" >> $SETUP_LOG
							echo "OK"

							tar -vzxf netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz >> $SETUP_LOG 2>&1
							mkdir -p ${SCRIPT_BASE_DIR}/mibs  >> $SETUP_LOG 2>&1
							if [ -w "${SCRIPT_BASE_DIR}/mibs" ]
							then
								cp -r ./netdisco-mibs-${NETDISCO_MIB_VERSION}/* ${SCRIPT_BASE_DIR}/mibs/ >> $SETUP_LOG 2>&1
								echo "Installation of Netdisco MIBs SUCCESSFUL"
							else
								echo "${SCRIPT_BASE_DIR}/mibs not writable" >> $SETUP_LOG
								echo "Installation of Netdisco MIBs FAILED"
								echo
								echo "Please install Netdisco-MIBs v${NETDISCO_MIB_VERSION} manually after installation has finished ***"
								echo "(Download netdisco-mibs from https://sourceforge.net/projects/netdisco/files/netdisco-mibs/)"
								echo "and copy the content of netdisco-mibs-${NETDISCO_MIB_VERSION}/ to ${SCRIPT_BASE_DIR}/mibs/"
								echo
								continue
							fi
						fi
					fi
				else
					echo
					echo "user chose to install MIBs manually"  >> $SETUP_LOG
					echo "*** Required MIBs were not installed ***"
					echo
					echo "Please install Netdisco-MIBs v${NETDISCO_MIB_VERSION} manually after installation has finished ***"
					echo "(Download netdisco-mibs from https://sourceforge.net/projects/netdisco/files/netdisco-mibs/)"
					echo "and copy the content of netdisco-mibs-${NETDISCO_MIB_VERSION}/ to ${SCRIPT_BASE_DIR}/mibs/"
					echo
					
				fi
			fi
			echo
        done
    fi
fi
fi

# comment out the mib entry in /etc/snmp/snmp.conf
if [ "$LINUX_DIST" = "ubuntu" ]
then
    if [ -w "/etc/snmp/snmp.conf" ]
    then
        echo "Commenting out \"mibs :\" line (/etc/snmp/snmp.conf)"
        echo "Actual file content:"
        grep -v '^#' /etc/snmp/snmp.conf >> $SETUP_LOG 
        $PERL_BIN -pi -e "s/^mibs :/#mibs :/" /etc/snmp/snmp.conf >> $SETUP_LOG 2>&1
    fi
fi

#if [ ${GCC_INSTALLED} -eq "1" ]
#then
#	yum -y remove gcc >> $SETUP_LOG 2>&1
#fi

#### XX1

REQUIRED_PERL_MODULE_MISSING=0

echo "Checking if all dependencies are resolved..." >> $SETUP_LOG
echo -n "Checking if all dependencies are resolved... "

echo "Checking for DBI PERL module" >> $SETUP_LOG
$PERL_BIN -mDBI -e 'print "PERL module DBI is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module DBI is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for DBD-mysql PERL module" >> $SETUP_LOG
$PERL_BIN -mDBD::mysql -e 'print "PERL module DBD-mysql is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module DBD-mysql is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for Net::IP PERL module" >> $SETUP_LOG
$PERL_BIN -mNet::IP -e 'print "PERL module Net::IP is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Net::IP is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for Parallel::ForkManager PERL module" >> $SETUP_LOG
PARALLEL_FORKMANAGER_MISSING="0"
$PERL_BIN -mParallel::ForkManager -e 'print "PERL module Parallel::ForkManager is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Parallel::ForkManager is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
    PARALLEL_FORKMANAGER_MISSING=1
fi

echo "Checking for SNMP PERL module" >> $SETUP_LOG
$PERL_BIN -mSNMP -e 'print "PERL module SNMP is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module SNMP is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for SNMP::Info PERL module" >> $SETUP_LOG
SNMP_INFO_MISSING="0"
$PERL_BIN -mSNMP::Info -e 'print "PERL module SNMP::Info is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module SNMP::Info is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
    SNMP_INFO_MISSING="1"
    SNMP_INFO_AUTO_INSTALL="1"
else
    # check if MIBs are installed:

    if [ ! -e "${SCRIPT_BASE_DIR}/mibs" ]
    then
        rm -r ./netdisco-mibs-${NETDISCO_MIB_VERSION}* >> $SETUP_LOG 2>&1
        echo
        echo "Downloading Netdisco MIBs (this may take several minutes)... " >> $SETUP_LOG
        echo -n "Downloading Netdisco MIBs (this may take several minutes)... "
        $WGET_NOCERT -w 2 -T 15 -t 6 http://sourceforge.net/projects/netdisco/files/netdisco-mibs/${NETDISCO_MIB_VERSION}/netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
        then
            echo "FAILED"
            echo "Installation of Netdisco MIBs FAILED"
            echo "Consult setup.log for details"
            echo
            echo "Please install Netdisco-MIBs v${NETDISCO_MIB_VERSION} manually after installation has finished ***"
            echo "(Download netdisco-mibs from https://sourceforge.net/projects/netdisco/files/netdisco-mibs/)"
            echo "and copy the content of netdisco-mibs-${NETDISCO_MIB_VERSION}/ to ${SCRIPT_BASE_DIR}/mibs/"
            echo
            continue
            
        else
            if [ -e "./netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz" ]
            then
                echo "OK" >> $SETUP_LOG
                echo "OK"

                tar -vzxf netdisco-mibs-${NETDISCO_MIB_VERSION}.tar.gz >> $SETUP_LOG 2>&1
                mkdir -p ${SCRIPT_BASE_DIR}/mibs  >> $SETUP_LOG 2>&1
                if [ -w "${SCRIPT_BASE_DIR}/mibs" ]
                then
                    cp -r ./netdisco-mibs-${NETDISCO_MIB_VERSION}/* ${SCRIPT_BASE_DIR}/mibs/ >> $SETUP_LOG 2>&1
                    echo "Installation of Netdisco MIBs SUCCESSFUL"
                else
                    echo "${SCRIPT_BASE_DIR}/mibs not writable" >> $SETUP_LOG
                    echo "Installation of Netdisco MIBs FAILED"
                    echo
                    echo "Please install Netdisco-MIBs v${NETDISCO_MIB_VERSION} manually after installation has finished ***"
                    echo "(Download netdisco-mibs from https://sourceforge.net/projects/netdisco/files/netdisco-mibs/)"
                    echo "and copy the content of netdisco-mibs-${NETDISCO_MIB_VERSION}/ to ${SCRIPT_BASE_DIR}/mibs/"
                    echo
                    continue
                fi
            fi
        fi
    fi
fi

MAIL_MAILER_MISSING="0"
echo "Checking for Mail::Mailer PERL module" >> $SETUP_LOG
$PERL_BIN -mMail::Mailer -e 'print "PERL module Mail::Mailer is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Mail::Mailer is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
    MAIL_MAILER_MISSING="1"
fi

HI_RES_MISSING="0"
echo "Checking for Time::HiRes PERL module" >> $SETUP_LOG
$PERL_BIN -mTime::HiRes -e 'print "PERL module Time::HiRes is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Time::HiRes is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
    HI_RES_MISSING="1"
fi

echo "Checking for Date::Calc PERL module" >> $SETUP_LOG
$PERL_BIN -mDate::Calc -e 'print "PERL module Date::Calc is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Date::Calc is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for Date::Manip PERL module" >> $SETUP_LOG
$PERL_BIN -mDate::Manip -e 'print "PERL module Date::Manip is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo
    echo "*** ERROR ***: PERL module Date::Manip is not installed!"
    echo
    REQUIRED_PERL_MODULE_MISSING=1
fi

echo "Checking for Net::DNS PERL module" >> $SETUP_LOG
NET_DNS_MISSING="0"
$PERL_BIN -mNet::DNS -e 'print "PERL module Net::DNS is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
    echo "*** ERROR ***: PERL module Net::DNS is not installed!"
    REQUIRED_PERL_MODULE_MISSING=1
    NET_DNS_MISSING="1"
fi

if [ "$INSTALL_MOD_EXCEL" = "yes" ]
then
   PARSE_EXCEL_MISSING="0"
   echo "Checking for Spreadsheet::ParseExcel PERL module" >> $SETUP_LOG
   $PERL_BIN -mSpreadsheet::ParseExcel -e 'print "PERL module Spreadsheet::ParseExcel is available\n"' >> $SETUP_LOG 2>&1
   if [ $? -ne 0 ]
   then
      echo
      echo "*** ERROR ***: PERL module Spreadsheet::ParseExcel is not installed!"
      echo
      REQUIRED_PERL_MODULE_MISSING=1
      PARSE_EXCEL_MISSING=1
   fi

   echo "Checking for OLE::Storage_Lite PERL module" >> $SETUP_LOG
   OLE_STORAGE_LIGHT_MISSING="0"
   $PERL_BIN -mOLE::Storage_Lite -e 'print "PERL module OLE::Storage_Lite is available\n"' >> $SETUP_LOG 2>&1
   if [ $? -ne 0 ]
   then
      echo
      echo "*** ERROR ***: PERL module OLE::Storage_Lite is not installed!"
      echo
      REQUIRED_PERL_MODULE_MISSING=1
      OLE_STORAGE_LIGHT_MISSING=1
   fi
fi

echo "Checking for Text::Diff PERL module" >> $SETUP_LOG
Text_Diff_MISSING="0"
$PERL_BIN -mText::Diff -e 'print "PERL module Text::Diff is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Text::Diff is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   Text_Diff_MISSING=1
fi

echo "Checking for Expect PERL module" >> $SETUP_LOG
EXPECT_MISSING="0"
$PERL_BIN -mExpect -e 'print "PERL module Expect is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Expect is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   EXPECT_MISSING=1
fi

echo "Checking for XML::Simple PERL module" >> $SETUP_LOG
XML_SIMPLE_MISSING="0"
$PERL_BIN -mXML::Simple -e 'print "PERL module XML::Simple is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module XML::Simple is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   XML_SIMPLE_MISSING=1
fi

echo "Checking for XML::Parser PERL module" >> $SETUP_LOG
XML_PARSER_MISSING="0"
$PERL_BIN -mXML::Parser -e 'print "PERL module XML::Parser is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module XML::Parser is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   XML_PARSER_MISSING=1
fi

echo "Checking for Digest::MD5 PERL module" >> $SETUP_LOG
DIGEST_MD5_MISSING="0"
$PERL_BIN -mDigest::MD5 -e 'print "PERL module Digest::MD5 is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Digest::MD5 is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   DIGEST_MD5_MISSING=1
fi

echo "Checking for Crypt::CBC PERL module" >> $SETUP_LOG
CRYPT_CBC_MISSING="0"
$PERL_BIN -mCrypt::CBC -e 'print "PERL module Crypt::CBC is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Crypt::CBC is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   CRYPT_CBC_MISSING=1
fi

echo "Checking for Crypt::Blowfish PERL module" >> $SETUP_LOG
CRYPT_BLOWFISH_MISSING="0"
$PERL_BIN -mCrypt::Blowfish -e 'print "PERL module Crypt::Blowfish is available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Crypt::Blowfish is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   CRYPT_BLOWFISH_MISSING=1
fi

echo "Checking for MIME::Base64 module" >> $SETUP_LOG
MIME_BASE64_MISSING="0"
$PERL_BIN -mMIME::Base64 -e 'print "PERL module MIME::Base64 available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module MIME::Base64 is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   MIME_BASE64_MISSING=1
fi

echo "Checking for Text::CSV module" >> $SETUP_LOG
TEXT_CSV_MISSING="0"
$PERL_BIN -mText::CSV -e 'print "PERL module Text::CSV available\n"' >> $SETUP_LOG 2>&1
if [ $? -ne 0 ]
then
   echo
   echo "*** ERROR ***: PERL module Text::CSV is not installed!"
   echo
   REQUIRED_PERL_MODULE_MISSING=1
   TEXT_CSV_MISSING=1
fi


if [ "$REQUIRED_PERL_MODULE_MISSING" -ne 0 ]
then
	echo "##### Automatic installation of missing Perl Modules failed #####" >> $SETUP_LOG
	echo "##### Automatic installation of missing Perl Modules failed #####"
	echo
    echo "Check the log file $SETUP_LOG for errors"
    echo "Installation aborded"
    echo
    exit 1
else
    echo "OK"
fi


echo
echo "Checking for Apache web server daemon" >> $SETUP_LOG
# Try to find Apache daemon
if [ -z "$APACHE_BIN" ]
then
    APACHE_BIN_FOUND=`which httpd 2>/dev/null`
    if [ -z "$APACHE_BIN_FOUND" ]
    then
        APACHE_BIN_FOUND=`which apache 2>/dev/null`
        if [ -z "$APACHE_BIN_FOUND" ]
        then
            APACHE_BIN_FOUND=`which apache2 2>/dev/null`
            if [ -z "$APACHE_BIN_FOUND" ]
            then
                APACHE_BIN_FOUND=`which httpd2 2>/dev/null`
                if [ -z "$APACHE_BIN_FOUND" ]
                then
                    if [ "$LINUX_DIST" = "fedora" ]
                    then    
                        ls /usr/sbin/httpd 2>/dev/null | grep httpd >/dev/null 2>&1
                        if [ $? -eq 0 ]
                        then
                            APACHE_BIN_FOUND="/usr/sbin/httpd"
                        fi
                        which httpd >>$SETUP_LOG 2>&1
                        echo "Which httpd has not output. Found Apache binary in /usr/sbin/httpd" >> $SETUP_LOG
                    fi

                    if [ "$LINUX_DIST" = "ubuntu" ]
                    then    
                        ls /usr/sbin/apache2 2>/dev/null | grep apache2 >/dev/null 2>&1
                        if [ $? -eq 0 ]
                        then
                            APACHE_BIN_FOUND="/usr/sbin/apache2"
                        fi
                        which apache2 >>$SETUP_LOG 2>&1
                        echo "Which apache2 has not output. Found Apache binary in /usr/sbin/apache2" >> $SETUP_LOG
                    fi
                fi
            fi
        fi
    fi
fi

if [ ! -z ${APACHE_BIN_PARAM} ]
then
        APACHE_BIN_FOUND=$APACHE_BIN_PARAM
fi

if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    if [ ! -z "$APACHE_BIN_FOUND" ]
    then
        APACHE_BIN=$APACHE_BIN_FOUND

        # Ensure file exists and is executable
        if [ -x "$APACHE_BIN" ]
        then
            res=1
        else
            echo "*** ERROR: $APACHE_BIN is not executable!" >> $SETUP_LOG
            echo "*** ERROR: $APACHE_BIN is not executable!"
            res=0
        fi

        echo "Found Apache daemon $APACHE_BIN_FOUND" >> $SETUP_LOG
    else
        echo "No Apache binary found."
        echo "No Apache binary found." >> $SETUP_LOG
        exit 1
    fi
else
    # Ask user's confirmation 
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache web server daemon...                 |"
    echo "+----------------------------------------------------------+"
    echo
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Where is Apache daemon binary [$APACHE_BIN_FOUND]? "
        read input
        if [ -z "$input" ]
        then
            APACHE_BIN=$APACHE_BIN_FOUND
        else
            APACHE_BIN="$input"
        fi
        # Ensure file exists and is executable
        if [ -x "$APACHE_BIN" ]
        then
            res=1
        else
            echo "*** ERROR: $APACHE_BIN is not executable!" >> $SETUP_LOG
            echo "*** ERROR: $APACHE_BIN is not executable!"
            res=0
        fi
        # Ensure file is not a directory
        if [ -d "$APACHE_BIN" ]
        then 
            echo "*** ERROR: $APACHE_BIN is a directory!" >> $SETUP_LOG
            echo "*** ERROR: $APACHE_BIN is a directory!"
            res=0
        fi
    done
    echo "OK, using Apache daemon $APACHE_BIN"
    echo "Using Apache daemon $APACHE_BIN" >> $SETUP_LOG
    echo
fi

# Determine Apache Version
APACHE_VERSION_PRE=`$APACHE_BIN -v | grep -i "Server version"`
echo "apache version pre: $APACHE_VERSION_PRE" >> $SETUP_LOG

echo $APACHE_VERSION_PRE | egrep '2.0.|2.1.|2.2.' >/dev/null
if [ $? -eq 0 ]
then
    APACHE_VERSION="22"
fi
echo $APACHE_VERSION_PRE | egrep '2.3.|2.4.' >/dev/null
if [ $? -eq 0 ]
then
    APACHE_VERSION="24"
fi
echo "found Apache version \"$APACHE_VERSION\"" >> $SETUP_LOG

if [ -z "$APACHE_VERSION" ]
then
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "What is the Version of the Apache Webserver (please answer with \"22\" or \"24\")? "
        read input
        if [ "$input" = "22" ]
	then
            echo "OK, Using Apache configuration for Apache 2.2"
            APACHE_VERSION=22
            echo "user choose apache version: $APACHE_VERSION" >> $SETUP_LOG
            res=1
        elif [ "$input" = "24" ]
	then
            echo "OK, Using Apache configuration for Apache 2.4"
            APACHE_VERSION="24"
            echo "user choose apache version: $APACHE_VERSION" >> $SETUP_LOG
            res=1
        else
            echo "invalid input for APACHE_VERSION: $APACHE_VERSION" >> $SETUP_LOG
            echo -n "What is the Version of the Apache Webserver (please answer with \"22\" or \"24\")? "
            read input
        fi
    done
fi




if [ "$LINUX_DIST" = "ubuntu" ]
then    
    if [ -e "/etc/apache2/envvars" ]
    then
#        echo "Loading environment variables from /etc/apache2/envvars"
#        echo "Loading environment variables from /etc/apache2/envvars" >> $SETUP_LOG
        . /etc/apache2/envvars >> $SETUP_LOG 2>&1
    fi

    if ! [ -L "/etc/apache2/mods-enabled/cgi.load" ]
    then
        if [ "$INSTALLATION_MODE" = "DEFAULT" ]
        then
            CREATE_LINK_CHECK="y"
        else
            echo "/etc/apache2/mods-enabled/cgi.load not found. That means that the Apache CGI Module"
            echo "is not enabled. Should the setup create the symbolic link"
            echo "ln -s /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load"
            echo -n "to enable the Apache CGI Module permanently [y]/n? "
            read CREATE_LINK_CHECK
        fi

        if [ -z "$CREATE_LINK_CHECK" ] || [ "$CREATE_LINK_CHECK" = "y" ] || [ "$CREATE_LINK_CHECK" = "Y" ] || [ "$CREATE_LINK_CHECK" = "yes" ]
        then
            echo -n "Creating sym link /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load..." >> $SETUP_LOG
            ln -s /etc/apache2/mods-available/cgi.load /etc/apache2/mods-enabled/cgi.load >> $SETUP_LOG 2>&1
            if [ -L "/etc/apache2/mods-enabled/cgi.load" ]
            then
                echo "OK" >> $SETUP_LOG
            else
                echo "Could not create symbolic link" >> $SETUP_LOG
                echo "Could not create symbolic link - Check log file for further information"
                echo "Please enable CGI Module manually after finishing the installation."
            fi
        else
            echo "User choosed that setup should not create sym link cgi.load" >> $SETUP_LOG
            echo "Symbolic link not created - please enable CGI Module manually after finishing the installation."
        fi
    fi


    # Where is ubuntu a2enmod command located
    A2ENMOD=`which a2enmod` >/dev/null 2>&1

    if [ ! -z "$A2ENMOD" ]
    then
        sudo $A2ENMOD request >> $SETUP_LOG 2>&1
        sudo $A2ENMOD rewrite >> $SETUP_LOG 2>&1
        sudo $A2ENMOD session >> $SETUP_LOG 2>&1
        sudo $A2ENMOD session_crypto >> $SETUP_LOG 2>&1
        sudo $A2ENMOD session_cookie >> $SETUP_LOG 2>&1
        sudo $A2ENMOD auth_form >> $SETUP_LOG 2>&1
        sudo $A2ENMOD authz_groupfile >> $SETUP_LOG 2>&1
        sudo $A2ENMOD headers >> $SETUP_LOG 2>&1
        sudo $A2ENMOD ldap >> $SETUP_LOG 2>&1
        sudo $A2ENMOD authnz_ldap >> $SETUP_LOG 2>&1
    else
        echo "Waring - a2enmod not found"
        echo "a2enmod not found" >> $SETUP_LOG
        echo "Enable the following Apache modules manually:"
        echo "request, rewrite, session, session_crypto, session_cookie, auth_form, authz_groupfile, headers"
    fi
fi

# Try to find Apache main configuration file
echo "Checking for Apache main configuration file" >> $SETUP_LOG
if [ -z "$APACHE_CONFIG_FILE" ]
then
    APACHE_ROOT=`eval $APACHE_BIN -V 2>/dev/null | grep "HTTPD_ROOT" | cut -d'=' -f2 | tr -d '"'`
    echo "Found Apache HTTPD_ROOT $APACHE_ROOT" >> $SETUP_LOG
    APACHE_CONFIG=`eval $APACHE_BIN -V 2>/dev/null | grep "SERVER_CONFIG_FILE" | cut -d'=' -f2 | tr -d '"'`
    echo "Found Apache SERVER_CONFIG_FILE $APACHE_CONFIG" >> $SETUP_LOG
    if [ -e "$APACHE_CONFIG" ]
    then
        APACHE_CONFIG_FILE_FOUND="$APACHE_CONFIG"
    else
        APACHE_CONFIG_FILE_FOUND="$APACHE_ROOT/$APACHE_CONFIG"
    fi
fi
echo "Found Apache main configuration file $APACHE_CONFIG_FILE_FOUND" >> $SETUP_LOG


if [ ! -z ${APACHE_CONF_PARAM} ]
then
	APACHE_CONFIG_FILE_FOUND=$APACHE_CONF_PARAM
fi

if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    APACHE_CONFIG_FILE=$APACHE_CONFIG_FILE_FOUND
    echo "Using Apache main configuration file $APACHE_CONFIG_FILE" >> $SETUP_LOG
    if [ -z "$APACHE_CONFIG_FILE" ]
    then
        echo "Apache main configuration file not found."
        echo "Apache main configuration file not found." >> $SETUP_LOG
        exit 1
    fi
else

    echo
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache main configuration file...           |"
    echo "+----------------------------------------------------------+"
    echo

    # Ask user's confirmation 
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Where is Apache main configuration file [$APACHE_CONFIG_FILE_FOUND]? "
        read input
        if [ -z "$input" ]
        then
            APACHE_CONFIG_FILE=$APACHE_CONFIG_FILE_FOUND
        else
            APACHE_CONFIG_FILE="$input"
        fi
        # Ensure file is not a directory
        if [ -d "$APACHE_CONFIG_FILE" ]
        then 
            echo "*** ERROR: $APACHE_CONFIG_FILE is a directory!" >> $SETUP_LOG
            echo "*** ERROR: $APACHE_CONFIG_FILE is a directory!"
            res=0
        fi
        # Ensure file exists and is readable
        if [ -r "$APACHE_CONFIG_FILE" ]
        then
            res=1
        else
            echo "*** ERROR: $APACHE_CONFIG_FILE is not readable!" >> $SETUP_LOG
            echo "*** ERROR: $APACHE_CONFIG_FILE is not readable!"
            res=0
        fi
    done
    echo "OK, using Apache main configuration file $APACHE_CONFIG_FILE"
    echo "Using Apache main configuration file $APACHE_CONFIG_FILE" >> $SETUP_LOG
    echo
fi

# Try to find apache user account
echo "Checking for Apache user account" >> $SETUP_LOG
if [ -z "$APACHE_USER" ]
then
    APACHE_USER_FOUND=`cat $APACHE_CONFIG_FILE | grep "User " | tail -1 | cut -d' ' -f2`
fi
echo "Found Apache user account $APACHE_USER_FOUND" >> $SETUP_LOG
#echo "Found Apache user account \"$APACHE_USER_FOUND\""

# Check if APACHE_USER_FOUND is a variable
echo $APACHE_USER_FOUND | grep "\\$" >/dev/null 2>&1
if [ $? -eq 0 ]
then
    APACHE_USER_FOUND=""
fi
if [ -z "$APACHE_USER_FOUND" ]
then
    if [ "$LINUX_DIST" = "suse" ]
    then
        APACHE_USER_FOUND=wwwrun
        APACHE_GROUP=www
    elif [ "$LINUX_DIST" = "ubuntu" ]
    then 
        APACHE_USER_FOUND=www-data
    fi
fi

if [ ! -z ${APACHE_USER_PARAM} ]
then
	APACHE_USER_FOUND=$APACHE_USER_PARAM
fi
        
if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    APACHE_USER=$APACHE_USER_FOUND
    echo "Using Apache user account $APACHE_USER" >> $SETUP_LOG
    if [ -z "$APACHE_USER" ]
    then
        echo "No Apache user found."
        echo "No Apache user found." >> $SETUP_LOG
        exit 1
    fi

	if [ `getent passwd | grep $APACHE_USER | wc -l` -eq 0 ]
	then
		echo "*** ERROR: account $APACHE_USER not found in system table /etc/passwd!" >> $SETUP_LOG
		echo "*** ERROR: account $APACHE_USER not found in system table /etc/passwd!"
		exit 1
	fi
else

    echo
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache user account...                      |"
    echo "+----------------------------------------------------------+"
    echo

    # Ask user's confirmation 
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Which user account is running Apache web server [$APACHE_USER_FOUND]? "
        read input
        if [ -z "$input" ]
        then
            APACHE_USER=$APACHE_USER_FOUND
        else
            APACHE_USER="$input"
        fi
        if ! [ -z "$APACHE_USER" ]
        then
            # Ensure user exist in /etc/passwd
            if [ `getent passwd | grep $APACHE_USER | wc -l` -eq 0 ]
            then
				echo "*** ERROR: account $APACHE_USER not found in system table /etc/passwd!" >> $SETUP_LOG
				echo "*** ERROR: account $APACHE_USER not found in system table /etc/passwd!"
				else
				res=1
            fi
        fi
    done
    echo "OK, Apache is running under user account $APACHE_USER"
    echo "Using Apache user account $APACHE_USER" >> $SETUP_LOG
    echo
fi


# Try apache group
echo "Checking for Apache group" >> $SETUP_LOG
if [ -z "$APACHE_GROUP" ]
then
    APACHE_GROUP_FOUND=`cat $APACHE_CONFIG_FILE | grep "Group" | tail -1 | cut -d' ' -f2`
    # Check if APACHE_GROUP_FOUND is a variable
    echo $APACHE_GROUP_FOUND | grep "\\$" >/dev/null 2>&1
    if [ $? -eq 0 ]
    then
        APACHE_GROUP_FOUND=""
    fi
    if [ -z "$APACHE_GROUP_FOUND" ]
    then
        # No group found, assume group name is the same as account
        echo "No Apache user group found, assuming group name is the same as user account" >> $SETUP_LOG
        APACHE_GROUP_FOUND=$APACHE_USER
    fi
else
    APACHE_GROUP_FOUND="$APACHE_GROUP"
fi

if [ ! -z ${APACHE_GROUP_PARAM} ]
then
	APACHE_GROUP_FOUND=$APACHE_GROUP_PARAM
fi

echo "Found Apache user group $APACHE_GROUP_FOUND" >> $SETUP_LOG
if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    APACHE_GROUP=$APACHE_GROUP_FOUND
    echo "Using Apache user group $APACHE_GROUP" >> $SETUP_LOG
    if [ -z "$APACHE_GROUP" ]
    then
        echo "Apache group not found."
        echo "Apache group not found." >> $SETUP_LOG
        exit 1
    fi
	# Ensure group exist in /etc/group
	if [ `getent group | grep $APACHE_GROUP | wc -l` -eq 0 ]
	then
		echo "*** ERROR: group $APACHE_GROUP not found in system table /etc/group!" >> $SETUP_LOG
		echo "*** ERROR: group $APACHE_GROUP not found in system table /etc/group!"
		exit 1
	fi
else

    echo
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache group...                             |"
    echo "+----------------------------------------------------------+"
    echo
    # Ask user's confirmation 
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Which user group is running Apache web server [$APACHE_GROUP_FOUND]? "
        read input
        if [ -z "$input" ]
        then
            APACHE_GROUP=$APACHE_GROUP_FOUND
        else
            APACHE_GROUP="$input"
        fi
        # Ensure group exist in /etc/group
        if [ `getent group | grep $APACHE_GROUP | wc -l` -eq 0 ]
        then
            echo "*** ERROR: group $APACHE_GROUP not found in system table /etc/group!" >> $SETUP_LOG
            echo "*** ERROR: group $APACHE_GROUP not found in system table /etc/group!"
        else
            res=1
        fi
    done
    echo "OK, Apache is running under users group $APACHE_GROUP"
    echo "Using Apache user group $APACHE_GROUP" >> $SETUP_LOG
    echo
fi


# Try to find Apache includes configuration directory
echo "Checking for Apache Include configuration directory" >> $SETUP_LOG
if [ -z "$APACHE_INCLUDE_DIRECTORY" ]
then
    # Works on RH/Fedora/CentOS
    INCLUDE_DIRECTORY_FOUND=`eval cat $APACHE_CONFIG_FILE | grep Include | grep conf.d |head -1 | cut -d' ' -f2 | cut -d'*' -f1`
    if [ -n "$INCLUDE_DIRECTORY_FOUND" ]
    then
        if [ -e "$INCLUDE_DIRECTORY_FOUND" ]
        then
            APACHE_INCLUDE_DIRECTORY_FOUND="$INCLUDE_DIRECTORY_FOUND"
        else
            APACHE_INCLUDE_DIRECTORY_FOUND="$APACHE_ROOT/$INCLUDE_DIRECTORY_FOUND"
        fi
        echo "Redhat compliant Apache Include configuration directory $INCLUDE_DIRECTORY_FOUND" >> $SETUP_LOG
    else
        APACHE_INCLUDE_DIRECTORY_FOUND=""
        echo "Not found Redhat compliant Apache Include configuration directory" >> $SETUP_LOG
    fi
    if ! [ -d "$APACHE_INCLUDE_DIRECTORY_FOUND" ]
    then
        # Works on Debian/Ubuntu
        INCLUDE_DIRECTORY_FOUND=`eval cat $APACHE_CONFIG_FILE | grep Include | grep conf.d |head -1 | cut -d' ' -f2 | cut -d'[' -f1`
        if [ -n "$INCLUDE_DIRECTORY_FOUND" ]
        then
            if [ -e "$INCLUDE_DIRECTORY_FOUND" ]
            then
                APACHE_INCLUDE_DIRECTORY_FOUND="$INCLUDE_DIRECTORY_FOUND"
            else
                APACHE_INCLUDE_DIRECTORY_FOUND="$APACHE_ROOT/$INCLUDE_DIRECTORY_FOUND"
            fi
            echo "Debian compliant Apache Include configuration directory $INCLUDE_DIRECTORY_FOUND" >> $SETUP_LOG
        else
            APACHE_INCLUDE_DIRECTORY_FOUND=""
            echo "Not found Debian compliant Apache Include configuration directory" >> $SETUP_LOG
        fi
    fi
    # Ubuntu up from 13.10 does not have a conf.d directory
    if ! [ -d "$APACHE_INCLUDE_DIRECTORY_FOUND" ] && [ "$LINUX_DIST" = "ubuntu" ]
    then
        if [ -d "/etc/apache2/sites-available" ] && [ -d "/etc/apache2/sites-enabled" ]
        then
            grep sites-enabled $APACHE_CONFIG_FILE > /dev/null 2>&1
            if [ $? -eq 0 ]
            then
                APACHE_INCLUDE_DIRECTORY_FOUND="/etc/apache2/sites-enabled"
            fi
        fi
    fi
fi
APACHE_CONFIG_DIRECTORY="`echo "$APACHE_CONFIG_FILE" | sed 's/\(.*\)\/.*/\1/'`"
if [ -e "$APACHE_CONFIG_DIRECTORY/conf.d" ] && [ -z "$APACHE_INCLUDE_DIRECTORY_FOUND" ]
then
    APACHE_INCLUDE_DIRECTORY_FOUND="$APACHE_CONFIG_DIRECTORY/conf.d"
fi
if [ -z "$APACHE_INCLUDE_DIRECTORY_FOUND" ]
then
   APACHE_INCLUDE_DIRECTORY_FOUND="`eval cat $APACHE_CONFIG_FILE | grep Include | grep -v "#" | grep "\*.conf" | sed -n 's/Include *\(\/.*\)/\1/p'| sed 's/\/\*\.conf//' 2>/dev/null`"
fi
echo "Found Apache Include configuration directory $APACHE_INCLUDE_DIRECTORY_FOUND" >> $SETUP_LOG


if [ ! -z ${APACHE_INCLUDE_DIRECTORY_PARAM} ]
then
	APACHE_INCLUDE_DIRECTORY_FOUND=$APACHE_INCLUDE_DIRECTORY_PARAM
fi

if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    APACHE_INCLUDE_DIRECTORY=$APACHE_INCLUDE_DIRECTORY_FOUND
    echo "Using Apache Include configuration directory $APACHE_INCLUDE_DIRECTORY" >> $SETUP_LOG
    if [ -z "$APACHE_INCLUDE_DIRECTORY" ]
    then
        echo "Apache include directory not found."
        echo "Apache include directory not found." >> $SETUP_LOG
        exit 1
    fi
	# Ensure directory exists and is writable
	if [ ! -w "$APACHE_INCLUDE_DIRECTORY" ]
	then
		echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not writable!" >> $SETUP_LOG 2>&1
		echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not writable! (are you root?)"
		exit 1
	fi
else

    echo
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache Include configuration directory...   |"
    echo "+----------------------------------------------------------+"
    echo

    if [ -z "$APACHE_INCLUDE_DIRECTORY_FOUND" ]
    then
        echo
        echo "+++++++++++++++++++++++++++++++++++++++++++++++++++"
        echo "HINT:"
        echo
        echo "If your apache installation doesn't have a"
        echo "Include directory answer with"
        echo "\"$APACHE_CONFIG_DIRECTORY\"."
        echo "and add manually the following line at the end of"
        echo "\"$APACHE_CONFIG_FILE:\""
        echo
        echo "\"Include $APACHE_CONFIG_DIRECTORY/$GESTIOIP_APACHE_CONF.conf\""
        echo "+++++++++++++++++++++++++++++++++++++++++++++++++++"
        echo
        echo
    fi

    # Ask user's confirmation 
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Where is Apache Include configuration directory [$APACHE_INCLUDE_DIRECTORY_FOUND]? "
        read input
        if [ -z "$input" ]
        then
            APACHE_INCLUDE_DIRECTORY=$APACHE_INCLUDE_DIRECTORY_FOUND
        else
            APACHE_INCLUDE_DIRECTORY="$input"
        fi
        # Ensure file is a directory
        if [ -d "$APACHE_INCLUDE_DIRECTORY" ]
        then
            res=1
            # Ensure directory exists and is writable
            if [ -w "$APACHE_INCLUDE_DIRECTORY" ]
            then
                res=1
            else
                echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not writable!" >> $SETUP_LOG 2>&1
                echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not writable! (are you root?)"
                res=0
            fi
        else
            echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not a directory!" >> $SETUP_LOG 2>&1
            echo "*** ERROR: $APACHE_INCLUDE_DIRECTORY is not a directory!"
            res=0
        fi
        if [ -z "$APACHE_INCLUDE_DIRECTORY" ]
        then
            res=0
        fi 
    done
    APACHE_INCLUDE_DIRECTORY=`echo "$APACHE_INCLUDE_DIRECTORY" | sed 's/\/$//'`
    echo "OK, using Apache Include configuration directory $APACHE_INCLUDE_DIRECTORY"
    echo "Using Apache Include configuration directory $APACHE_INCLUDE_DIRECTORY" >> $SETUP_LOG
    echo
fi


#checking for hostname binary
HOSTNAME_PATH=""
if [ -z "$HOSTNAME_BIN" ]
then
    echo "hostname command not found!"
    echo "hostname command not found" >> $SETUP_LOG
    $HOSTNAME_BIN="/bin/hostname"
    $HOSTNAME_PATH="/bin"
else
    echo "Found hostname command at <$HOSTNAME_BIN>" >> $SETUP_LOG
    HOSTNAME_PATH=`echo $HOSTNAME_BIN | sed 's/\/hostname//'`
    echo "HOSTNAME_PATH: $HOSTNAME_PATH" >> $SETUP_LOG
fi
HOSTNAME=`$HOSTNAME_BIN`

echo "Checking for PERL Interpreter" >> $SETUP_LOG
if [ -z "$PERL_BIN" ]
then
    echo "PERL Interpreter not found!"
    echo "PERL Interpreter not found" >> $SETUP_LOG
else
    echo "Found PERL Intrepreter at <$PERL_BIN>" >> $SETUP_LOG
fi

if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    if [ -z "$PERL_BIN" ]
    then
        exit 1
    fi
else
    echo
    echo "+----------------------------------------------------------+"
    echo "| Checking for PERL Interpreter...                         |"
    echo "+----------------------------------------------------------+"
    echo

    # Ask user's confirmation 
    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Where is PERL Intrepreter binary [$PERL_BIN]? "
        read input
        if [ -n "$input" ]
        then
            PERL_BIN_INPUT="$input"
        else
            PERL_BIN_INPUT=$PERL_BIN
        fi
        # Ensure file exists and is executable
        if [ -x "$PERL_BIN_INPUT" ]
        then
            res=1
        else
            echo "*** ERROR: $PERL_BIN_INPUT is not executable!" >> $SETUP_LOG 2>&1
            echo "*** ERROR: $PERL_BIN_INPUT is not executable!"
            res=0
        fi
        # Ensure file is not a directory
        if [ -d "$PERL_BIN_INPUT" ]
        then 
            echo "*** ERROR: $PERL_BIN_INPUT is a directory!" >> $SETUP_LOG 2>&1
            echo "*** ERROR: $PERL_BIN_INPUT is a directory!"
            res=0
        fi
    done
    if [ -n "$PERL_BIN_INPUT" ]
    then
        PERL_BIN=$PERL_BIN_INPUT
    fi
    echo "OK, using PERL Intrepreter $PERL_BIN"
    echo "Using PERL Intrepreter $PERL_BIN" >> $SETUP_LOG
    echo
fi









if [ "$INSTALLATION_MODE" = "INTERACTIVE" ]
then
    echo "+----------------------------------------------------------+"
    echo "| Checking for Apache mod_perl version...                  |"
    echo "+----------------------------------------------------------+"
    echo
    echo "Checking for Apache mod_perl"
    echo "Checking for Apache mod_perl" >> $SETUP_LOG
    $PERL_BIN -mmod_perl2 -e 'print "mod_perl > 1.99_21 available\n"' >> $SETUP_LOG 2>&1
    if [ $? -ne 0 ]
    # mod_perl 2 not found !
    then
        $PERL_BIN -mmod_perl -e 'print "mod_perl < 1.99_21 available\n"' >> $SETUP_LOG 2>&1
        if [ $? -ne 0 ]
            # mod_perl 2 not found !
        then
            echo "Apache mod_perl is not availabel" >> $SETUP_LOG 2>&1
            echo "Apache mod_perl is not availabel"
            echo
        echo "Please install Apache mod_perl"
            echo
            if [ "$LINUX_DIST" = "fedora" ]
            then
                echo
                echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                echo
                echo "Hint for Fedora (verified with Fedora 11/12/15/17/19)"
                echo
                echo "mod_perl is available from the Fedora repository."
                echo "You can install it with the following command:"
                echo
                echo "sudo yum install mod_perl"
                echo
                echo
            fi
            if [ "$LINUX_DIST" = "suse" ]
            then
                echo
                echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                echo
                echo "Hint for SUSE (verified with openSUSE 11/12)"
                echo
                echo "mod_perl is available from the SUSE repository."
                echo "You can install it with the following command:"
                echo
                echo "sudo zypper install apache2-mod_perl"
                echo
                echo
            fi
            if [ "$LINUX_DIST" = "ubuntu" ]
            then
                echo
                echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                echo
                echo "Hint for ubuntu"
                echo
                echo "mod_perl is available from the Ubuntu repository."
                echo "You can install it with the following command:"
                echo
                echo "sudo apt-get install libapache2-mod-perl2"
                echo
                echo
            fi
            echo
        echo "Installation aborded" >> $SETUP_LOG 2>&1
        echo "Installation aborded"
        exit 1;
        fi
    else
        echo "Apache mod_perl available - Good!"
    fi
fi


#echo
#echo "+----------------------------------------------------------+"
#echo "| Configuration of Apache Web Server...                    |"
#echo "+----------------------------------------------------------+"
#echo

if [ -z "$DOCUMENT_ROOT" ]
then
    if [ "$OS" = "linux" ]
    then
        if [ "$LINUX_DIST" = "ubuntu" ]
        then
            if [ "$DEBIAN_VERSION" -ge 10 ]
            then
                DOCUMENT_ROOT="/var/www/html"
            else
                DOCUMENT_ROOT="/var/www"
            fi
        fi
        if [ "$LINUX_DIST" = "suse" ]
        then
            DOCUMENT_ROOT="/srv/www/htdocs"
        fi
        if [ "$LINUX_DIST" = "fedora" ]
        then
            DOCUMENT_ROOT="/var/www/html"
        fi
    fi    
fi

if [ -z "$DOCUMENT_ROOT" ]
then
    DOCUMENT_ROOT=`grep -r DocumentRoot $APACHE_CONFIG_FILE | grep -v '#' 2>&1 | grep DocumentRoot | head -1 | sed 's/.*DocumentRoot *\(\/.*\)/\1/'`
fi

DOCUMENT_ROOT=`echo $DOCUMENT_ROOT | sed 's/"//'`

if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    echo "Using Apache DocumentRoot $DOCUMENT_ROOT"
    echo "Using Apache DocumentRoot $DOCUMENT_ROOT" >> $SETUP_LOG
    if ! [ -d "$DOCUMENT_ROOT" ]
    then
        echo "Apache DocumentRoot not found."
        echo "Apache DocumentRoot not found." >> $SETUP_LOG
        exit 1
    fi
else
    res=0
    while [ $res -eq 0 ]
    do
        if [ -z "$DOCUMENT_ROOT" ]
        then
            echo -n "Please enter the DocumentRoot of your Apache Web Server: "
            read input
            if [ -n "$input" ]
            then
                DOCUMENT_ROOT="$input"
                res=0
            fi
        else 
            echo -n "Which is the Apache DocumentRoot directory [$DOCUMENT_ROOT]? "
            read input
            if [ -n "$input" ]
            then
                DOCUMENT_ROOT="$input"
                res=0
            fi
        fi
        # Ensure file is a directory
        if [ ! -d "$DOCUMENT_ROOT" ]
        then
            echo "*** ERROR: $DOCUMENT_ROOT is not a directory!"
            res=0
        else
            res=1
        fi
        # Ensure directory exists and is writable
        if [ -w "$DOCUMENT_ROOT" ]
        then
            res=1
        else
            echo "*** ERROR: $DOCUMENT_ROOT is not writable! (are you root?)"
            res=0
        fi
    done
    echo "OK, using Apache DocumentRoot $DOCUMENT_ROOT"
    echo "OK, using Apache DocumentRoot $DOCUMENT_ROOT" >> $SETUP_LOG
    echo
fi

if [ -d "${DOCUMENT_ROOT}/${GESTIOIP_CGI_DIR}" ]
then
    echo "#### WARNING ####"
    echo
    echo "Directory ${DOCUMENT_ROOT}/gestioip already exists."
    echo "This script is only thought for a fresh installation."
    echo "If you want to UPDATE/UPGRADE GestioIP use the"
    echo "actualization tar-ball from"
    echo "http://www.gestioip.net/actualizations_gestioip_en.html"
    echo

    res=0
    while [ $res -eq 0 ]
    do
        echo -n "Do you want to continue with the installation [y]/n? "
        read input
	if [ -z "$input" ] || [ "$input" = "y" ] || [ "$input" = "Y" ] || [ "$input" = "yes" ]
        then
            echo
            res=1
        else 
            echo "Installation aborded "
            exit 1
        fi
    done
fi


# Try to find htpasswd
HTPASSWD=`which htpasswd 2>/dev/null`

if [ -z "$HTPASSWD" ]
then
    HTPASSWD=`which htpasswd2 2>/dev/null`
fi
if [ "$INSTALLATION_MODE" = "DEFAULT" ]
then
    echo "Using htpasswd $HTPASSWD" >> $SETUP_LOG 2>&1
    if [ -z "$HTPASSWD" ]
    then
        echo "htpasswd not found."
        echo "htpasswd not found." >> $SETUP_LOG
        exit 1
    fi
else
    res=0
    while [ $res -eq 0 ]
    do
        if [ -z "$HTPASSWD" ]
        then
            echo -n "Where is htpasswd? "
            read input
            if [ -n "$input" ]
            then
                HTPASSWD="$input"
                res=0
            fi
        else
            echo -n "Where is htpasswd [$HTPASSWD]? "
            read input
            if [ -n "$input" ]
            then
                HTPASSWD="$input"
                res=0
            fi
        fi
        # Ensure file is exectuabel
        if ! [ -x "$HTPASSWD" ]
        then
            echo "*** ERROR: $HTPASSWD is not executable!" >> $SETUP_LOG 2>&1
            echo "*** ERROR: $HTPASSWD is not executable!"
            res=0
        else
            res=1
        fi
        if [ -z "$HTPASSWD" ]
        then
            res=0
        fi
    done
    echo "Using htpasswd $HTPASSWD" >> $SETUP_LOG 2>&1
    echo "OK, using htpasswd $HTPASSWD"
    echo
fi


if [ "$PROMPT_FOR_USER" != "no" ]
then
    echo -n "Which should be the user to access to GestioIP [$GESTIOIP_USER]? "
    read input
    if [ -n "$input" ]
    then
        RW_USER="$input"
    else
        RW_USER="$GESTIOIP_USER" 
    fi
    echo "using rw user $RW_USER" >> $SETUP_LOG 2>&1
    echo "OK, using rw user $RW_USER"
    echo
else
    RW_USER="$GESTIOIP_USER" 
fi

RW_USER_PASS=""
if [ "$GENERATE_GESTIOIP_USER_PASSWORD" = "yes" ]
then
    # create random string as passphrase
    GENERATED_PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1) 2>>$SETUP_LOG
    if [ "$WRITE_GENERATED_PASSWORD_TO_LOG" = "yes" ]
    then
        echo "Generated password for user $RW_USER: $GENERATED_PASS" >> $SETUP_LOG
    fi

    RW_USER_PASS="$GENERATED_PASS"

    if [ ! -z "$GESTIOIP_USER_PASSWORD" ]
    then
        echo "WARNING: parameter GENERATE_GESTIOIP_USER_PASSWORD is set to \"yes\". Parameter GESTIOIP_USER_PASSWORD will be ignored"
        echo "WARNING: parameter GENERATE_GESTIOIP_USER_PASSWORD is set to \"yes\". Parameter GESTIOIP_USER_PASSWORD will be ignored" >> $SETUP_LOG
    fi
elif [ ! -z "$GESTIOIP_USER_PASSWORD" ]
then
    RW_USER_PASS="$GESTIOIP_USER_PASSWORD"
fi


APACHE_CONFIG_DIRECTORY="`echo "$APACHE_INCLUDE_DIRECTORY" | sed -n 's/\(.*\)\/.*/\1/p'`"
echo "Using Apache configuration Directory $APACHE_CONFIG_DIRECTORY" >> $SETUP_LOG 2>&1


#creating script directory

if [ ! -e "$SCRIPT_BASE_DIR" ]
then 
	echo "mkdir -p $SCRIPT_BASE_DIR" >> $SETUP_LOG 2>&1
	mkdir -p $SCRIPT_BASE_DIR 2>> $SETUP_LOG
	if [ $? -ne 0 ]
	then
	    echo "Something went wrong: Can't exectue \"mkdir -p $SCRIPT_BASE_DIR/\"" >> $SETUP_LOG 2>&1
	    echo "Something went wrong: Can't exectue \"mkdir -p $SCRIPT_BASE_DIR/\""
	    echo
	    echo "Installation aborted!"
	    exit 1
	fi
	echo "mkdir -p $SCRIPT_BIN_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_BIN_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_BIN_WEB_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_BIN_WEB_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_BIN_WEB_INCLUDE_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_BIN_WEB_INCLUDE_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_CONF_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_CONF_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_CONF_APACHE_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_CONF_APACHE_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_BIN_INCLUDE_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_BIN_INCLUDE_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_LOG_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_LOG_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_TMP_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_TMP_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_RUN_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_RUN_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $CM_CONFIGS_DIR" >> $SETUP_LOG
	mkdir -p $CM_CONFIGS_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $CM_DEVICES_DIR" >> $SETUP_LOG
	mkdir -p $CM_DEVICES_DIR >> $SETUP_LOG 2>&1
	echo "mkdir -p $SCRIPT_DATA_DIR" >> $SETUP_LOG
	mkdir -p $SCRIPT_DATA_DIR >> $SETUP_LOG 2>&1
else
	if [ ! -e "$SCRIPT_BIN_DIR" ]
	then
		echo "mkdir -p $SCRIPT_BIN_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_BIN_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_BIN_WEB_DIR" ]
	then
		echo "mkdir -p $SCRIPT_BIN_BIN_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_BIN_WEB_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_BIN_WEB_INCLUDE_DIR" ]
	then
		echo "mkdir -p $SCRIPT_BIN_WEB_INCLUDE_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_BIN_WEB_INCLUDE_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_BIN_INCLUDE_DIR" ]
	then
		echo "mkdir -p $SCRIPT_BIN_INCLUDE_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_BIN_INCLUDE_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_CONF_DIR" ]
	then
		echo "mkdir -p $SCRIPT_CONF_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_CONF_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_CONF_APACHE_DIR" ]
	then
		echo "mkdir -p $SCRIPT_CONF_APACHE_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_CONF_APACHE_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_LOG_DIR" ]
	then
		echo "mkdir -p $SCRIPT_LOG_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_LOG_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_TMP_DIR" ]
	then
		echo "mkdir -p $SCRIPT_TMP_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_TMP_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_RUN_DIR" ]
	then
		echo "mkdir -p $SCRIPT_RUN_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_RUN_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$CM_CONFIGS_DIR" ]
	then
		echo "mkdir -p $CM_CONFIGS_DIR" >> $SETUP_LOG
		mkdir -p $CM_CONFIGS_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$SCRIPT_DATA_DIR" ]
	then
		echo "mkdir -p $SCRIPT_DATA_DIR" >> $SETUP_LOG
		mkdir -p $SCRIPT_DATA_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$CM_DEVICES_DIR" ]
	then
		echo "mkdir -p $CM_DEVICES_DIR" >> $SETUP_LOG
		mkdir -p $CM_DEVICES_DIR >> $SETUP_LOG 2>&1
	fi
	if [ ! -e "$CM_DEVICES_DIR" ]
	then
	    echo "Something went wrong creating SCRIPT direcories" >> $SETUP_LOG 2>&1
	    echo "Something went wrong creating SCRIPT direcories"
	    echo
	    echo "Installation aborted!"
	    exit 1
	fi
fi



#### Create User
echo "Creating user $RW_USER"
echo "Creating user $RW_USER" >> $SETUP_LOG

USERCHECK=1
COUNTER_USER_CHECK=0
while [ $USERCHECK = 1 ]
do
    if [ $OS = "linux" ]
    then
#        if ([ "$PROMPT_FOR_PASSWORD" != "no" ] || [ ! -z "$GESTIOIP_USER_PASSWORD" ]) && [ ! -z "$RW_USER_PASS" ]
        if [ ! -z "$RW_USER_PASS" ]
        then
            sudo $HTPASSWD -b -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER $RW_USER_PASS 2>>$SETUP_LOG
            echo "executing: sudo $HTPASSWD -b -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER xxxxxxx" >> $SETUP_LOG
        else
            sudo $HTPASSWD -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER 2>>$SETUP_LOG
            echo "executing: sudo $HTPASSWD -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER" >> $SETUP_LOG
        fi
    else
        $HTPASSWD -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER 2>>$SETUP_LOG
        echo "executing: $HTPASSWD -c $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} $RW_USER" >> $SETUP_LOG
    fi

    grep $RW_USER $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} >/dev/null 2>&1
    if [ $? -ne 0 ]
    then
        echo "*** ERROR - rw user ($RW_USER) was NOT created" >> $SETUP_LOG
        echo "*** ERROR - rw user ($RW_USER) was NOT created"

    else
        echo "rw user ($RW_USER) successfully created" >> $SETUP_LOG
        echo "rw user ($RW_USER) successfully created"
        USERCHECK=2
        echo
    fi

    COUNTER_USER_CHECK=`expr $COUNTER_USER_CHECK + 1`
    if [ $COUNTER_USER_CHECK = 3 ]
    then
        USERCHECK=2
    fi
done

grep $RW_USER $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} >/dev/null 2>&1
if [ $? -ne 0 ]
then
    echo "Skipping installation"
    exit 1
fi
echo "chown $APACHE_USER:$APACHE_GROUP $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF}" >> $SETUP_LOG
chown $APACHE_USER:$APACHE_GROUP $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} >> $SETUP_LOG 2>&1

echo "chown $APACHE_USER:$APACHE_GROUP $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF}" >> $SETUP_LOG 2>&1
chown $APACHE_USER:$APACHE_GROUP $SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF} >> $SETUP_LOG 2>&1


# Where to install scripts?

if [ "$INSTALLATION_MODE" = "INTERACTIVE" ]
then
	res=0
	while [ $res -eq 0 ]
	do
		 echo -n "Under which directory should GestioIP's script files be installed [$SCRIPT_BASE_DIR]?"
		 read input
		 if [ -n "$input" ]
		 then
			 SCRIPT_BASE_DIR="$input"
			 res=1
		 else
		 res=1
		fi
	done
fi

echo "Using script base directory $SCRIPT_BASE_DIR"
echo "using script base directory $SCRIPT_BASE_DIR" >>$SETUP_LOG
echo "using script directory $SCRIPT_BIN_DIR" >>$SETUP_LOG
echo "using web script directory $SCRIPT_BIN_WEB_DIR" >>$SETUP_LOG
echo "using web include script directory $SCRIPT_BIN_WEB_INCLUDE_DIR" >>$SETUP_LOG
echo "using include script directory $SCRIPT_BIN_INCLUDE_DIR" >>$SETUP_LOG
echo "using script configuration directory $SCRIPT_BIN_DIR" >>$SETUP_LOG
echo "using script log directory $SCRIPT_LOG_DIR" >>$SETUP_LOG
echo "using script run directory $SCRIPT_RUN_DIR" >>$SETUP_LOG
echo "using cm conf directory $CM_CONFIGS_DIR" >>$SETUP_LOG
echo "using cm devices directory $CM_DEVICES_DIR" >>$SETUP_LOG
echo "using data directory $SCRIPT_DATA_DIR" >>$SETUP_LOG
echo


## Customize GestioIP Apache configuration
if [ ${LINUX_DIST} = "fedora" ]
then
    cp $EXE_DIR/apache/gestioip_default_${APACHE_VERSION}_rh $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
else
    if [ "$LINUX_DIST" = "ubuntu" ] && [ "${APACHE_VIRTUAL_HOST}" = "yes" ]
	then
#        if [ "${INSTALL_SSL}" = "yes" ]
#        then
#            cp $EXE_DIR/apache/gestioip_default_${APACHE_VERSION}_virtual_host_ssl $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
#            mkdir -p /etc/apache2/ssl/certs /etc/apache2/ssl/keys
#            chmod 700 /etc/apache2/ssl/keys
#            sudo $A2ENMOD ssl >> $SETUP_LOG 2>&1
#        else
            cp $EXE_DIR/apache/gestioip_default_${APACHE_VERSION}_virtual_host $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
#        fi
    else
        cp $EXE_DIR/apache/gestioip_default_${APACHE_VERSION} $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
    fi
fi

# create random string as passphrase
SECRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 24 | head -n 1) 2>>$SETUP_LOG


echo "GestioIPGroup: $RW_USER" > $EXE_DIR/apache/conf/apache-groups 2>>$SETUP_LOG
#$PERL_BIN -pi -e "s#Require user gipadmin#Require user $RW_USER#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#APACHE_LDAP_CONF#$SCRIPT_CONF_APACHE_DIR/apache_ldap.conf#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#AUTH_GROUP_FILE#$SCRIPT_CONF_APACHE_DIR/apache-groups#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#APACHE_LDAP_REQUIRE#$SCRIPT_CONF_APACHE_DIR/apache_ldap_require.conf#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#/var/www/gestioip#$DOCUMENT_ROOT/$GESTIOIP_CGI_DIR#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s# /errors/# /$GESTIOIP_CGI_DIR/errors/#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s# /login/# /$GESTIOIP_CGI_DIR/login/#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s# /logout/# /$GESTIOIP_CGI_DIR/login/#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
#$PERL_BIN -pi -e "s#AUTH_USER_FILE#$APACHE_CONFIG_DIRECTORY/users-${GESTIOIP_APACHE_CONF}#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#AUTH_USER_FILE#$SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF}#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#\#Alias#Alias /$GESTIOIP_CGI_DIR \"$DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\"#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG
$PERL_BIN -pi -e "s#CHANGE_ME_SECRET#${SECRET}#g" $EXE_DIR/apache/$GESTIOIP_APACHE_CONF 2>>$SETUP_LOG


if [ "$INSTALL_CM_PLUGIN" = "ask" ] || [ "$INSTALL_CM_PLUGIN" = "yes" ]
then
    if [ "$INSTALL_CM_PLUGIN" = "yes" ]
	then
		INSTALL_CMM="yes"
	else
		# download CM files
		echo "GestioIP offers an additional, commercial plugin which allows to backup"
		echo "configurations of network devices (CMM plugin). The plugin is not required"
		echo "to run GestioIP and is not part of the main release."
		echo "You can download the plugin now and activate it later in any moment."
		echo "See https://http://www.gestioip.net/configuration_backup_and_management.html"
		echo "for further informations"
		echo -n "Do you wish to download the CMM plugin [y]/n? "
		read INSTALL_CMM
	fi

	if [ -z "$INSTALL_CMM" ] || [ "$INSTALL_CMM" = "y" ] || [ "$INSTALL_CMM" = "Y" ] || [ "$INSTALL_CMM" = "yes" ]
	then
		echo -n "Downloading files for the Configuration Management Module..."
		$WGET -w 2 -T 8 -t 6 http://www.gestioip.net/files/gip_cm_files.tar.gz >> $SETUP_LOG 2>&1
		if [ $? -ne 0 ]
		then
			echo "FAILED to download gip_cm_files.tar.gz" >> $SETUP_LOG
			echo "FAILED - Check logfile for further information"
		else
			echo "Successfully downloaded gip_cm_files.tar.gz" >> $SETUP_LOG
			echo "OK"

			if [ ! -e $EXE_DIR/gestioip/res/cm ]
			then
				mkdir $EXE_DIR/gestioip/res/cm >> $SETUP_LOG 2>&1
				if [ $? -ne 0 ]
				then
					echo "FAILED: mkdir $EXE_DIR/gestioip/res/cm" >> $SETUP_LOG
				fi
			fi

			mv gip_cm_files.tar.gz $EXE_DIR/gestioip/res/cm >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED: mv gip_cm_files.tar.gz $EXE_DIR/gestioip/res/cm" >> $SETUP_LOG
			fi

			cd $EXE_DIR/gestioip/res/cm/ >> $SETUP_LOG 2>&1
#			tar zxf $EXE_DIR/gestioip/res/cm/gip_cm_files.tar.gz >> $SETUP_LOG 2>&1
			tar zxf gip_cm_files.tar.gz >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED: tar zxf gip_cm_files.tar.gz" >> $SETUP_LOG
			else
				echo "Successfully installed gip_cm_files.tar.gz" >> $SETUP_LOG
			fi
			rm $EXE_DIR/gestioip/res/cm/gip_cm_files.tar.gz >> $SETUP_LOG 2>&1
			cd $EXE_DIR >> $SETUP_LOG 2>&1

		fi
	fi
else
	echo "Not installing CMM Plugin" >> $SETUP_LOG
fi


# And copy all to the right places

# Move fetch_config.pl from res/cm dir to script dir
echo "executing \"mv $EXE_DIR/gestioip/res/cm/fetch_config.pl $EXE_DIR/scripts/\"" >> $SETUP_LOG
mv $EXE_DIR/gestioip/res/cm/fetch_config.pl $EXE_DIR/scripts/ >> $SETUP_LOG 2>&1;


echo "mkdir -p $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/" >> $SETUP_LOG 2>&1
mkdir -p $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"mkdir -p $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"mkdir -p $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp -r $EXE_DIR/gestioip/* $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/" >> $SETUP_LOG 2>&1
cp -r $EXE_DIR/gestioip/* $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp -r $EXE_DIR/gestioip/* $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp -r $EXE_DIR/gestioip/* $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\""
    echo
    echo "Installation aborted!"
    exit 1
fi

# remove installation directory for automatic installation
if [ "${INSTALL_INSTALL}" = "no" ]
then
    rm -r $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/install >> $SETUP_LOG 2>&1
fi

echo "chmod -R 750 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR" >> $SETUP_LOG 2>&1
chmod -R 750 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"chmod -R 750 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"chmod -R 750 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\""
    echo
    echo "Installation aborted!"
    exit 1
fi

# for an automated installation change values in priv_conf
if [ ! -z ${DB_HOST} ]
then
    $PERL_BIN -pi -e "s#bbdd_host=127.0.0.1#bbdd_host=${DB_HOST}#" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config >> $SETUP_LOG 2>&1
fi
if [ ! -z ${DB_PORT} ]
then
    $PERL_BIN -pi -e "s#bbdd_port=3306#bbdd_port=${DB_PORT}#" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config >> $SETUP_LOG 2>&1
fi
if [ ! -z ${DB_SSID} ]
then
    $PERL_BIN -pi -e "s#ssid=gestioip#ssid=$DB_SSID#" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config >> $SETUP_LOG 2>&1
fi
if [ ! -z ${DB_USER} ]
then
    $PERL_BIN -pi -e "s#user=gestioip#user=$DB_USER#" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config >> $SETUP_LOG 2>&1
fi
if [ ! -z ${DB_PASSWORD} ]
then
    $PERL_BIN -pi -e "s#password=xxxxxxxx#password=$DB_PASSWORD#" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config >> $SETUP_LOG 2>&1
fi


echo "chmod -R 640 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config" >> $SETUP_LOG 2>&1
chmod -R 750 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"chmod -R 640 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"chmod -R 640 $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/priv/ip_config\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "chown -R $APACHE_USER:$APACHE_GROUP $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR" >> $SETUP_LOG 2>&1
chown -R $APACHE_USER:$APACHE_GROUP $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"chown -R $APACHE_USER:$APACHE_GROUP $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"chown -R $APACHE_USER:$APACHE_GROUP $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR\""
    echo
    echo "Installation aborted!"
    exit 1
fi

if [ "$PERL_BIN" != "/usr/bin/perl" ]
then
	for i in $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/*
	do
            if ! [ -d $i ]
            then
	        $PERL_BIN -pi -e "s#/usr/bin/perl#$PERL_BIN#g" $i
            fi
        done 
        
	for i in $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/*
	do
            if ! [ -d $i ]
            then
	        $PERL_BIN -pi -e "s#/usr/bin/perl#$PERL_BIN#g" $i
            fi
	done 

	for i in $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/install/*
	do
            if ! [ -d $i ]
            then
	        $PERL_BIN -pi -e "s#/usr/bin/perl#$PERL_BIN#g" $i
            fi
	done 
fi

echo "cp ${EXE_DIR}/scripts/web/*.pl ${SCRIPT_BIN_WEB_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/web/*.pl ${SCRIPT_BIN_WEB_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/web/*.pl ${SCRIPT_BIN_WEB_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/web/*.pl ${SCRIPT_BIN_WEB_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/web/include/Usage.pm ${SCRIPT_BIN_WEB_INCLUDE_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/web/include/Usage.pm ${SCRIPT_BIN_WEB_INCLUDE_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/web/include/Usage.pm ${SCRIPT_BIN_WEB_INCLUDE_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/web/include/Usage.pm ${SCRIPT_BIN_WEB_INCLUDE_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/*.pl ${SCRIPT_BIN_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/*.pl ${SCRIPT_BIN_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/*.pl ${SCRIPT_BIN_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/*.pl ${SCRIPT_BIN_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/include/*.pm ${SCRIPT_BIN_INCLUDE_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/include/*.pm ${SCRIPT_BIN_INCLUDE_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/include/*.pm ${SCRIPT_BIN_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/include/*.pm ${SCRIPT_BIN_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/*.sh ${SCRIPT_BIN_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/*.sh ${SCRIPT_BIN_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/*.sh ${SCRIPT_BIN_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/*.sh ${SCRIPT_BIN_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/ip_update_gestioip.conf ${SCRIPT_CONF_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/ip_update_gestioip.conf ${SCRIPT_CONF_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/ip_update_gestioip.conf ${SCRIPT_CONF_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/ip_update_gestioip.conf ${SCRIPT_CONF_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/apache/conf/* ${SCRIPT_CONF_APACHE_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/apache/conf/* ${SCRIPT_CONF_APACHE_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/apache/conf/* ${SCRIPT_CONF_APACHE_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/apache/conf/* ${SCRIPT_CONF_APACHE_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/snmp_targets ${SCRIPT_CONF_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/snmp_targets ${SCRIPT_CONF_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/snmp_targets ${SCRIPT_CONF_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/snmp_targets ${SCRIPT_CONF_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/check_targets ${SCRIPT_CONF_DIR}/" >> $SETUP_LOG 2>&1
cp ${EXE_DIR}/scripts/check_targets ${SCRIPT_CONF_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/check_targets ${SCRIPT_CONF_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp ${EXE_DIR}/scripts/check_targets ${SCRIPT_CONF_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp -r ${EXE_DIR}/scripts/vars ${SCRIPT_CONF_DIR}/" >> $SETUP_LOG 2>&1
cp -r ${EXE_DIR}/scripts/vars ${SCRIPT_CONF_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp -r ${EXE_DIR}/scripts/vars ${SCRIPT_CONF_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp -r ${EXE_DIR}/scripts/vars ${SCRIPT_CONF_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi

echo "cp ${EXE_DIR}/scripts/devices/* ${CM_DEVICES_DIR}/" >> $SETUP_LOG 2>&1
cp -r ${EXE_DIR}/scripts/devices/* ${CM_DEVICES_DIR}/ 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"cp -r ${EXE_DIR}/scripts/devices/* ${SCRIPT_CONF_DIR}/\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"cp -r ${EXE_DIR}/scripts/devices/* ${SCRIPT_CONF_DIR}/\""
    echo
    echo "Installation aborted!"
    exit 1
fi



# Create symbolic link to $SCRIPT_CONFIGS_DIR
if [ ! -L $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/conf ]
then
    echo -n "ln -s $CM_CONFIGS_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/" >> $SETUP_LOG 2>&1
    ln -s $CM_CONFIGS_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ >> $SETUP_LOG 2>&1
    if [ $? -ne 0 ]
    then
        echo "ERROR" >> $SETUP_LOG
        echo "Symbolic link for config dir not created: $!" >> $SETUP_LOG
        echo "ERROR"
        echo "Symbolic link $CM_CONFIGS_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ not created: Please create the symbolic link manually after finishing the installation"
        echo
    else
        echo "OK" >> $SETUP_LOG
    fi
fi


# Create symbolic link to scheduled job logdir
if [ ! -L $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/log ]
then
    echo -n "ln -s $SCRIPT_LOG_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/" >> $SETUP_LOG 2>&1
    ln -s $SCRIPT_LOG_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ >> $SETUP_LOG 2>&1
    if [ $? -ne 0 ]
    then
        echo "ERROR" >> $SETUP_LOG
        echo "Symbolic link for log dir not created: $!" >> $SETUP_LOG
        echo "ERROR"
        echo "Symbolic link $SCRIPT_LOG_DIR $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/ not created: Please create the symbolic link manually after finishing the installation"
        echo
    else
        echo "OK" >> $SETUP_LOG
    fi
fi


#Customize web_scripts

$PERL_BIN -pi -e "s#/var/www/gestioip#$DOCUMENT_ROOT/$GESTIOIP_CGI_DIR#g" $SCRIPT_BIN_WEB_DIR/*.pl 2>> $SETUP_LOG


#changing script dir permissions

echo "chmod -R 775 $SCRIPT_BASE_DIR" >> $SETUP_LOG 2>&1
chmod -R 775 $SCRIPT_BASE_DIR 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"chmod -R 775 $SCRIPT_BASE_DIR\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"chmod -R 775 $SCRIPT_BASE_DIR\""
    echo
    echo "Installation aborted!"
    exit 1
fi

#changing script dir owner

echo "chown -R $APACHE_USER:$APACHE_GROUP $SCRIPT_BASE_DIR" >> $SETUP_LOG 2>&1
chown -R $APACHE_USER:$APACHE_GROUP $SCRIPT_BASE_DIR 2>> $SETUP_LOG
if [ $? -ne 0 ]
then
    echo "Something went wrong: Can't exectue \"chown -R $APACHE_USER:$APACHE_GROUP $SCRIPT_BASE_DIR\"" >> $SETUP_LOG 2>&1
    echo "Something went wrong: Can't exectue \"chown -R $APACHE_USER:$APACHE_GROUP $SCRIPT_BASE_DIR\""
    echo
    echo "Installation aborted!"
    exit 1
fi


#Customize initialize_gestioip.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_initialize.cgi 2>> $SETUP_LOG

#Customize ip_import_spreadsheet.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_import_spreadsheet.cgi 2>> $SETUP_LOG

#Customize ip_stop_discovery.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_stop_discovery.cgi 2>> $SETUP_LOG

#Customize ip_do_job.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/cm/ip_do_job.cgi 2>> $SETUP_LOG

#Customize install1.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/install/install1.cgi 2>> $SETUP_LOG

#Customize ip_deleteip.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_deleteip.cgi 2>> $SETUP_LOG

#Customize ip_modip.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_modip.cgi 2>> $SETUP_LOG

#Customize ip_modip_form.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_modip_form.cgi 2>> $SETUP_LOG

#Customize ip_modip_mass_update_form.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_modip_mass_update_form.cgi 2>> $SETUP_LOG

#Customize intapi.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/intapi.cgi 2>> $SETUP_LOG

#Customize upload.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/api/upload.cgi 2>> $SETUP_LOG

#Customize ip_manage_gestioip.cgi
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_manage_gestioip.cgi 2>> $SETUP_LOG

#Customize netblock_list_view_tree.js
$PERL_BIN -pi -e "s#/gestioip#/$GESTIOIP_CGI_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/js/netblock_list_view_tree.js 2>> $SETUP_LOG


#Customize GestioIP.pm
PING=`which ping`
CRONTAB=`which crontab`
ECHO=`which echo`
APACHE_RELOAD_COMMAND=""
if [ "$LINUX_DIST" = "fedora" ]
then
    APACHE_RELOAD_COMMAND="/usr/bin/systemctl reload httpd"
elif [ "$LINUX_DIST" = "ubuntu" ]
then
    APACHE_RELOAD_COMMAND="/etc/init.d/apache2 reload"
elif [ "$LINUX_DIST" = "suse" ]
then
    APACHE_RELOAD_COMMAND="/sbin/service apache2 reload"
fi
$PERL_BIN -pi -e "s#ENV_PATH_REPLACE_INSTALL#$HOSTNAME_PATH#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#HOSTNAME_BIN_REPLACE_INSTALL#$HOSTNAME_BIN#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#www-data#$APACHE_USER#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/etc/init.d/apache2 reload#$APACHE_RELOAD_COMMAND#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/etc/apache2/users-gestioip#$SCRIPT_CONF_APACHE_DIR/users-${GESTIOIP_APACHE_CONF}#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/modules/GestioIP.pm 2>> $SETUP_LOG

#Customise ip_insert_scheduled_jobs y ip_mod_scheduled_jobs
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_insert_scheduled_job.cgi 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/share/gestioip#$SCRIPT_BASE_DIR#g" $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/res/ip_mod_scheduled_job.cgi 2>> $SETUP_LOG

#Customize scripts in bin
$PERL_BIN -pi -e "s#/var/www/gestioip#$DOCUMENT_ROOT/$GESTIOIP_CGI_DIR#g" $SCRIPT_BIN_DIR/ip_import_vlans.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/var/www/gestioip#$DOCUMENT_ROOT/$GESTIOIP_CGI_DIR#g" $SCRIPT_BIN_DIR/fetch_config.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $SCRIPT_BIN_DIR/ip_import_vlans.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $SCRIPT_BIN_DIR/discover_network.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $SCRIPT_BIN_DIR/get_networks_snmp.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $SCRIPT_BIN_DIR/ip_update_gestioip_dns.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/usr/bin/crontab#$CRONTAB#g" $SCRIPT_BIN_DIR/ip_update_gestioip_snmp.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $SCRIPT_BIN_DIR/ip_import_vlans.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $SCRIPT_BIN_DIR/discover_network.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $SCRIPT_BIN_DIR/get_networks_snmp.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $SCRIPT_BIN_DIR/ip_update_gestioip_dns.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/ping#$PING#g" $SCRIPT_BIN_DIR/ip_update_gestioip_snmp.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $SCRIPT_BIN_DIR/ip_import_vlans.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $SCRIPT_BIN_DIR/discover_network.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $SCRIPT_BIN_DIR/get_networks_snmp.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $SCRIPT_BIN_DIR/ip_update_gestioip_dns.pl 2>> $SETUP_LOG
$PERL_BIN -pi -e "s#/bin/echo#$ECHO#g" $SCRIPT_BIN_DIR/ip_update_gestioip_snmp.pl 2>> $SETUP_LOG


# Customize error pages
for i in $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR/errors/*
do
    $PERL_BIN -pi -e "s#=\"/#=\"/$GESTIOIP_CGI_DIR/#g" $i
done 

        
if [ "$APACHE_INCLUDE_DIRECTORY" = "/etc/apache2/sites-enabled" ]
then
    if ! [ -L "/etc/apache2/sites-enabled/$GESTIOIP_APACHE_CONF.conf" ]
    then
        echo "cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf" >> $SETUP_LOG
        cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf >> $SETUP_LOG 2>&1
        echo "ln -s /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf /etc/apache2/sites-enabled/$GESTIOIP_APACHE_CONF.conf" >> $SETUP_LOG
        ln -s /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf /etc/apache2/sites-enabled/$GESTIOIP_APACHE_CONF.conf

        if [ $? -ne 0 ]
        then
            echo "Something went wrong: Can't create symbolic link \"ln -s /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf /etc/apache2/sites-enabled/$GESTIOIP_APACHE_CONF.conf\"" >> $SETUP_LOG
            echo "Something went wrong: Can't create symbolic link \"ln -s /etc/apache2/sites-available/$GESTIOIP_APACHE_CONF.conf /etc/apache2/sites-enabled/$GESTIOIP_APACHE_CONF.conf\""
            echo
            echo "Installation aborted!" >> $SETUP_LOG
            echo "Installation aborted!"
            exit 1
        fi
    fi
else
    echo "cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF $APACHE_INCLUDE_DIRECTORY/$GESTIOIP_APACHE_CONF.conf" >> $SETUP_LOG
    cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF $APACHE_INCLUDE_DIRECTORY/$GESTIOIP_APACHE_CONF.conf 2>> $SETUP_LOG

    if [ $? -ne 0 ]
    then
        echo "Something went wrong: Can't exectue \"cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF $APACHE_INCLUDE_DIRECTORY/$GESTIOIP_APACHE_CONF\"" >> $SETUP_LOG
        echo "Something went wrong: Can't exectue \"cp $EXE_DIR/apache/$GESTIOIP_APACHE_CONF $APACHE_INCLUDE_DIRECTORY/$GESTIOIP_APACHE_CONF\""
        echo
        echo "Installation aborted!" >> $SETUP_LOG
        echo "Installation aborted!"
        exit 1
    fi
fi

# Enable Apache modules
if [ "$LINUX_DIST_DETAIL" = "fedora" ] || [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ]
then
	echo "Enabeling Apache Modules" >> $SETUP_LOG
	$PERL_BIN -pi -e "s/^#LoadModule request_module/LoadModule request_module/" /etc/httpd/conf.modules.d/00-base.conf >> $SETUP_LOG 2>&1
	$PERL_BIN -pi -e "s/^#LoadModule auth_form_module/LoadModule auth_form_module/" /etc/httpd/conf.modules.d/01-session.conf >> $SETUP_LOG 2>&1
	$PERL_BIN -pi -e "s/^#LoadModule session_crypto_module/LoadModule session_crypto_module/" /etc/httpd/conf.modules.d/01-session.conf >> $SETUP_LOG 2>&1
fi

# check crontab
echo crontab-check >> $SETUP_LOG
sudo $CRONTAB -u $APACHE_USER -l >> $SETUP_LOG 2>&1

# add apache user to cron.allow if exists
if [ -e /etc/cron.allow ]
then
    echo -n "Adding $APACHE_USER to /etc/cron.allow" >> $SETUP_LOG
    sudo echo "${APACHE_USER}" >> /etc/cron.allow
    res=$?
    if [ $res -ne 0 ]
    then
        echo FAIILED >> $SETUP_LOG
    else
        echo OK >> $SETUP_LOG
    fi
fi

# creating sudoers entry 

echo -n "creating file \"/etc/sudoers.d/${APACHE_USER}\" to allow the apache user to reload the apache daemon - " >> $SETUP_LOG
sudo echo "${APACHE_USER} ALL=NOPASSWD:${APACHE_RELOAD_COMMAND}" >> /etc/sudoers.d/${APACHE_USER}
res=$?
if [ $res -ne 0 ]
then
    echo FAIILED >> $SETUP_LOG
else
    echo OK >> $SETUP_LOG
fi


SE_UPDATE=0
SE_ENABLED=0

# Check if SE_LINUX is enabled

if [ "$LINUX_DIST_DETAIL" = "fedora" ] || [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ]
then
	ENFORCE=`getenforce 2>/dev/null`

	if [ "$ENFORCE" = "Enforcing" ]
	then
		SE_ENABLED=1
	fi

	if [ "$SE_ENABLED" -eq "0" ]
	then
		echo "SE_LINUX disabled - skipping update of SE_LINUX policy"
	fi
fi

if [ "$SE_ENABLED" -eq "1" ] && ( [ "$LINUX_DIST_DETAIL" = "fedora" ] || [ "$LINUX_DIST_DETAIL" = "redhat" ] || [ "$LINUX_DIST_DETAIL" = "centos" ] ) 
then
	SE_UPDATE=1

	if [ ! -z ${UPDATE_SE_POLICY_PARAM} ]
	then
		UPDATE_POLICY_CHECK=$UPDATE_SE_POLICY_PARAM
	else
		UPDATE_POLICY_CHECK="y"
	fi

    if [ "$INSTALLATION_MODE" = "DEFAULT" ]
	then
		echo "Updatind SELinux policy"
		echo "Updatind SELinux policy" >> $SETUP_LOG
	else
		echo "Updating SELinux policy..." >> $SETUP_LOG
		echo
		echo "Note for Fedora/Redhat/CentOS Linux:"
		echo
		echo "Some functions of GestioIP require an update of SELinux policy"
		echo "Setup can update SELinux policy automatically"
		echo -n "Do you wish that the Setup updates SELinux policy now [y]/n? "
		read UPDATE_POLICY_CHECK
		echo
	fi

	if [ -z "$UPDATE_POLICY_CHECK" ] || [ "$UPDATE_POLICY_CHECK" = "y" ] || [ "$UPDATE_POLICY_CHECK" = "Y" ] || [ "$UPDATE_POLICY_CHECK" = "yes" ]
	then
		if [ ! -x "$WGET" ]
		then
			echo
			echo "*** error: wget not found" >> $SETUP_LOG
			echo "*** error: wget not found"
			echo
			echo "Skipping update of SELinux policy"
			echo
			echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
			echo "and update SELinux policy manually"
			echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
			echo "how to do that"
			echo
			SE_UPDATE=0
			echo -n "[continue] "
			read input
			echo
		fi

		## Check if "checkpolicy" package is installed
		echo -n "executing \"yum list installed checkpolicy\":" >> $SETUP_LOG
		yum list installed checkpolicy >> $SETUP_LOG 2>&1

		## Check if SELinux is enaled:
		echo -n "executing \"sestatus\":" >> $SETUP_LOG
		sestatus >> $SETUP_LOG 2>&1


		# remove .te files from old installations
		rm *.te >> $SETUP_LOG 2>&1

		if [ "$LINUX_DIST_DETAIL" = "centos" ]
		then
#			TE_FILE=gestioip_centos5.te
			TE_FILE=gestioip_centos.te
		elif [ "$LINUX_DIST_DETAIL" = "redhat" ]
		then
			if [ "$REDHAT_MAIN_VERSION" = "5" ]
			then
				TE_FILE=gestioip_redhat5.te
			else
				TE_FILE=gestioip_fedora_redhat.te
			fi
		elif [ "$LINUX_DIST_DETAIL" = "fedora" ]
		then
			TE_FILE=gestioip_fedora_redhat.te
		fi

		CHECKMODULE=`which checkmodule 2>/dev/null`
		if [ $? -ne 0 ] && [ "$SE_UPDATE" -eq "1" ]
		then
			echo "Can't find \"checkmodule\""  >> $SETUP_LOG
			echo "Can't find \"checkmodule\""
			echo "\"checkmodule\" is required for policy update"
			echo
			echo "\"checkmodule\" is part of the checkpolicy rpm"
			echo -n "Do you wish that the Setup installs checkpolicy rpm now [y]/n? "
			read input
			echo
			if [ -z "$input" ] || [ "$input" = "y" ] || [ "$input" = "Y" ] || [ "$input" = "yes" ]
			then
				echo "User choose to install checkpolicy rmp" >> $SETUP_LOG
				sudo yum install checkpolicy | tee -a $SETUP_LOG

				CHECKMODULE=`which checkmodule 2>/dev/null`
				if [ $? -ne 0 ]
				then
					echo "Can't find \"checkmodule\" - Skipping SELinux policy update"  >> $SETUP_LOG
					echo "Can't find \"checkmodule\""
					echo
					echo "Skipping update of SELinux policy"
					echo
					echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
					echo "and update SELinux policy manually"
					echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
					echo "how to do that"
					echo
					SE_UPDATE=0
				fi

				
			else
				echo "Skipping update of SELinux policy"
				echo
				echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
				echo "and update SELinux policy manually"
				echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
				echo "how to do that"
				echo
				SE_UPDATE=0
			fi

		fi

		SEMODULE_PACKAGE=`which semodule_package` 2>/dev/null
		if [ ! -x "$SEMODULE_PACKAGE" ] && [ "$SE_UPDATE" -eq "1" ]
		then
			echo "Can't find \"semodule_package\" - Skipping SELinux policy update"  >> $SETUP_LOG
			echo "Can't find \"semodule_package\""
			echo "\"semodule_package\" is required for policy update"
			echo "Skipping update of SELinux policy"
			echo
			echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
			echo "and update SELinux policy manually"
			echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
			echo "how to do that"
			echo
			SE_UPDATE=0
		fi
		
		SEMODULE="/usr/sbin/semodule"
		if [ ! -x "$SEMODULE" ] && [ "$SE_UPDATE" -eq "1" ]
		then
			echo "Can't find \"semodule\"  - Skipping SELinux policy update"  >> $SETUP_LOG
			echo "Can't find \"semodule\""
			echo "\"semodule\" is required for policy update"
			echo "Skipping update of SELinux policy"
			echo
			echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
			echo "and update SELinux policy manually"
			echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
			echo "how to do that"
			echo
			SE_UPDATE=0
		fi
		if [ $SE_UPDATE -eq "1" ]
		then
			echo
			echo -n "Downloading Type Enforcement File from www.gestioip.net..." >> $SETUP_LOG
			echo -n "Downloading Type Enforcement File from www.gestioip.net..."
			$WGET -w 2 -T 8 -t 6 http://www.gestioip.net/docu/${TE_FILE} >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED"
				echo "FAILED - skipping SELinux policy update" >> $SETUP_LOG
				echo "Update of SELinux policy FAILED"
				echo
				echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
				echo "and update SELinux policy manually"
				echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
				echo "how to do that"
				echo
				SE_UPDATE=0
			else
				echo "OK" >> $SETUP_LOG
				echo "OK"
			fi
		fi
		if [ $SE_UPDATE -eq "1" ]
		then
			echo -n "Executing $CHECKMODULE -M -m -o gestioip.mod $TE_FILE ..." >> $SETUP_LOG
			echo -n "Executing \"check_module\"..."
			$CHECKMODULE -M -m -o gestioip.mod $TE_FILE >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED - skipping SELinux policy update" >> $SETUP_LOG
				echo "FAILED"
				echo "Update of SELinux policy FAILED"
				echo
				echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
				echo "and update SELinux policy manually"
				echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
				echo "how to do that"
				echo
				SE_UPDATE=0
			else
				echo "OK" >> $SETUP_LOG
				echo "OK"
			fi
		fi
		if [ $SE_UPDATE -eq "1" ]
		then
			echo -n "Executing \"semodule_package\"..."
			echo -n "Executing $SEMODULE_PACKAGE -o gestioip.pp -m gestioip.mod ..." >> $SETUP_LOG
			$SEMODULE_PACKAGE -o gestioip.pp -m gestioip.mod >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED - skipping SELinux policy update" >> $SETUP_LOG
				echo "FAILED"
				echo "Update of SELinux policy FAILED"
				echo
				echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
				echo "and update SELinux policy manually"
				echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
				echo "how to do that"
				echo
				SE_UPDATE=0
			else
				echo "OK" >> $SETUP_LOG
				echo "OK"
			fi
		fi
		if [ $SE_UPDATE -eq "1" ]
		then
			echo -n "Executing \"semodule\"..."
			echo -n "Executing $SEMODULE -i gestioip.pp ..." >> $SETUP_LOG
			sudo $SEMODULE -i gestioip.pp >> $SETUP_LOG 2>&1
			if [ $? -ne 0 ]
			then
				echo "FAILED - skipping SELinux policy update" >> $SETUP_LOG
				echo "FAILED"
				echo "Update of SELinux policy FAILED"
				echo
				echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
				echo "and update SELinux policy manually"
				echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
				echo "how to do that"
				echo
				SE_UPDATE=0
			else
				echo "OK" >> $SETUP_LOG
				echo "OK"
			fi
		fi
		if [ $SE_UPDATE -eq "1" ]
		then
			echo
			echo "Update of SELinux policy SUCCESSFUL" >> $SETUP_LOG
			echo "Update of SELinux policy SUCCESSFUL"
			echo
			### update permissions DocumentRoot: sudo chcon -R -t httpd_sys_script_exec_t /var/www/html/gestioip
			echo -n "Updating permissions of GestioIP's cgi-dir..."
			echo -n "Updating permissions: sudo chcon -R -t httpd_sys_script_exec_t $DOCUMENT_ROOT/${GESTIOIP_CGI_DIR}..." >> $SETUP_LOG
			sudo chcon -R -t httpd_sys_script_exec_t $DOCUMENT_ROOT/$GESTIOIP_CGI_DIR >> $SETUP_LOG 2>&1
			if [ $? -eq 0 ]
			then
				echo "SUCCESSFUL" >> $SETUP_LOG
				echo "SUCCESSFUL"
				echo
			else
				echo "Failed" >> $SETUP_LOG
				echo "Failed"
				echo
				echo "If you get an \"Internal Server Error\" with the notification \"Permission denied\" in Apaches error log"
				echo "while accessing to GestioIP, you need to update cgi permissions manually. Consult distributions"
				echo "SELinux documentation for details"
				echo 
			fi

			### update permissions Script directory: sudo chcon -R -t httpd_sys_script_exec_t /usr/share/gestioip
			echo -n "Updating permissions of GestioIP's script directory..."
			echo -n "Updating permissions: sudo chcon -R -t httpd_sys_script_exec_t ${SCRIPT_BASE_DIR}..." >> $SETUP_LOG
			sudo chcon -R -t httpd_sys_script_exec_t ${SCRIPT_BASE_DIR} >> $SETUP_LOG 2>&1
			if [ $? -eq 0 ]
			then
				echo "SUCCESSFUL" >> $SETUP_LOG
				echo "SUCCESSFUL"
				echo
			else
				echo "Failed" >> $SETUP_LOG
				echo "Failed"
				echo
				echo "If you get an \"Internal Server Error\" with the notification \"Permission denied\" in Apaches error log"
				echo "while accessing to GestioIP, you need to update cgi permissions manually. Consult distributions"
				echo "SELinux documentation for details"
				echo 
			fi
		fi
	else
		echo "Not updating SELinux policy" >> $SETUP_LOG
		echo "Not updating SELinux policy"
		echo 
		echo "Please download Type Enforcement File from http://www.gestioip.net/docu/gestioip.te"
		echo "and update SELinux policy manually"
		echo "Please see http://www.gestioip.net/docu/README.fedora.redhat.CentOS for instructions"
		echo "how to do that"
		echo
	fi
fi

echo
echo "+-------------------------------------------------------+"
echo "|                                                       |"
echo "|    Installation of GestioIP successfully finished!    |"
echo "|                                                       |"
echo "|   Please, review $APACHE_INCLUDE_DIRECTORY/$GESTIOIP_APACHE_CONF.conf"
echo "|          to ensure that all is good and               |"
echo "|                                                       |"
echo "|            RESTART the Apache daemon!                 |"
echo "|                                                       |"
echo "|            Then, point your browser to                |"
echo "|                                                       |"
echo "|           http://server/$GESTIOIP_CGI_DIR/install"
echo "|                                                       |"
echo "|          to configure the database server.            |"
echo "|                                                       |"
echo "|         Access with user \"$RW_USER\" and the"
if [ "$GENERATE_GESTIOIP_USER_PASSWORD" = "yes" ] && [ "$WRITE_GENERATED_PASSWORD_TO_CONSOLE" = "yes" ]
then
    echo "|        auto generated password \"$RW_USER_PASS\"             |"
elif [ "$GENERATE_GESTIOIP_USER_PASSWORD" = "yes" ]
then
    echo "|        auto generated password               |"
else
    echo "|        the password which you created before          |"
fi
echo "|                                                       |"
echo "+-------------------------------------------------------+"
echo
#if [ "$LINUX_DIST" = "fedora" ]
#then
#    echo "Hint for Fedora/RH/CentOS"
#    echo "Enable the Apache modules 'request', 'auth_form' and 'session_crypto'"
#    echo "before you restart the Apache web server"
#    echo "You find instructions how to do this in the Installation Guide"
#    echo
#fi
if [ "$LINUX_DIST" = "suse" ]
then
    echo "Hint for Suse Linux"
    echo "Enable the Apache modules 'request', 'auth_form' and 'session_crypto'"
    echo "before you restart the Apache web server"
    echo "You find instructions how to do this in the Installation Guide"
    echo
fi
echo "GestioIP installation successful" >> $SETUP_LOG

