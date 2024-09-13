#!/bin/sh

# Fetch configuration from a pfsense device >=v2.2.6
# https://doc.pfsense.org/index.php/Remote_Config_Backup

# This script will habitually be called by fetch_config.pl
# see /usr/share/gestioip/var/devices/35_pfsense.xml

# version 0.1

# usage: $0 deviceIP backupfilename username loginpass

IP="$1"
OUTFILE_NAME="$2"
USERNAME="$3"
PASS="$4"

if [ ! "$PASS" ]
then
    echo "ERROR: parameter missing"
    exit 1;
fi

#WGET=`which wget`
WGET="/usr/bin/wget"

if [ ! -x "$WGET" ]
then
    echo "ERROR: Wget not found"
    exit 1;
fi

COOKIE_FILE="/tmp/fetch_pfsenese.cookie"
OUTFILE="/tmp/${OUTFILE_NAME}"
CSRF_FILE1="/tmp/csrf1_$$.txt"
CSRF_FILE2="/tmp/csrf2_$$.txt"

$WGET -T 30 --tries=3 --connect-timeout=10 -qO- --keep-session-cookies --save-cookies ${COOKIE_FILE} \
  --no-check-certificate https://${IP}/diag_backup.php \
    | grep "name='__csrf_magic'" | sed 's/.*value="\(.*\)".*/\1/' > $CSRF_FILE1

if [ ! -s "$CSRF_FILE1" ]
then
    echo "ERROR: could not fetch csrf token 1"
    exit 1
fi

$WGET -T 30 --tries=3 --connect-timeout=10 -qO- --keep-session-cookies --load-cookies ${COOKIE_FILE} \ 
  --save-cookies ${COOKIE_FILE} --no-check-certificate \
  --post-data "login=Login&usernamefld=${USERNAME}&passwordfld=${PASS}&__csrf_magic=`cat $CSRF_FILE1`" \
  https://${IP}/diag_backup.php  | grep "name='__csrf_magic'" \
  | sed 's/.*value="\(.*\)".*/\1/' > $CSRF_FILE2

if [ ! -s "$CSRF_FILE2" ]
then
    rm $CSRF_FILE1 >/dev/null 2>&1
    echo "ERROR: could not fetch csrf token 2"
    exit 1
fi

$WGET -T 60 --tries=3 --connect-timeout=10 --keep-session-cookies --load-cookies ${COOKIE_FILE} --no-check-certificate \
  --post-data "Submit=download&donotbackuprrd=yes&__csrf_magic=$(head -n 1 CSRC_FILE2)" \
    https://${IP}/diag_backup.php -O $OUTFILE

if [ ! -s "${OUTFILE}" ]
then
    rm $CSRF_FILE1 >/dev/null 2>&1
    rm $CSRF_FILE2 >/dev/null 2>&1
    echo "ERROR: Failed to fetch configuration (CSRF token successfully fetched)"
    exit 1
fi


rm $CSRF_FILE1 >/dev/null 2>&1
rm $CSRF_FILE2 >/dev/null 2>&1
rm $COOKIE_FILE >/dev/null 2>&1

echo -n $OUTFILE
exit 0
