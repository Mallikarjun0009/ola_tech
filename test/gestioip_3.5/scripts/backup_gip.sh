#!/bin/bash

# script to create a backup of the GestióIP database
# v0.4 20210206

BACKUP_DIR="/usr/share/gestioip/var/data"
GZIP="/bin/gzip"
MYSQLDUMP="/usr/bin/mysqldump"
RM="/bin/rm"
GREP="/bin/grep"
SED="/bin/sed"
DATE="/bin/date"

MYSQL_VERSION="5"
if [ ${MYSQL_VERSION} -eq 8 ]
then
    PARAM_COL_STAT='--column-statistics=0'
fi


if [ ! -x "$GZIP" ]
then
    echo "ERROR: gzip not found"
    exit 1
fi

if [ ! -x "$MYSQLDUMP" ]
then
    echo "ERROR: mysqldump not found"
    exit 1
fi

if [ ! -x "$RM" ]
then
    echo "ERROR: rm not found"
    exit 1
fi


DOCUMENT_ROOT=""
if [ -e "/var/www/gestioip" ]
then
    DOCUMENT_ROOT="/var/www/"
elif [ -e "/var/www/html/gestioip" ]
then
    DOCUMENT_ROOT="/var/www/html"
elif [ -e "/srv/www/htdocs/gestioip" ]
then
    DOCUMENT_ROOT="/srv/www/htdocs/"
fi

USER=`$GREP user ${DOCUMENT_ROOT}/gestioip/priv/ip_config | $GREP -v '#' | $SED 's/user=//'`
PASS=`$GREP password ${DOCUMENT_ROOT}/gestioip/priv/ip_config | $GREP -v '#' | $SED 's/password=//'`
DATE=`$DATE +%Y%m%d`

if [ -z "$USER" ]
then
    echo "ERROR: database user not found"
    exit 1
fi

if [ -z "$PASS" ]
then
    echo "ERROR: database password not found"
    exit 1
fi



BACKUP_FILE="${BACKUP_DIR}/${DATE}_gestioip_bck.sql"


MYSQL_PWD=${PASS} $MYSQLDUMP ${PARAM_COL_STAT} --no-tablespaces -u $USER gestioip > $BACKUP_FILE 2>/tmp/backup_gip.tmp
res=$?
if [ $res -ne 0 ]
then
    ERROR=$(</tmp/backup_gip.tmp)
    echo "ERROR: mysqldump: ${ERROR}"
    exit 1
fi

$GZIP -f $BACKUP_FILE 2>/tmp/backup_gip.error
res=$?
if [ $res -ne 0 ]
then
    ERROR=$(</tmp/backup_gip.tmp)
    echo "ERROR: gzip: ${ERROR}"
    exit 1
fi

echo "Backup successfully created (${BACKUP_FILE}.gz)"
exit 0

