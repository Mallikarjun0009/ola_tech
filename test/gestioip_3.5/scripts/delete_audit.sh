#!/bin/sh

# delete old GestióIP audit events from MySQL DB

####### edit from here .... #######

# delete events older than...
NUMBER_MONTH=3

GIP_PASS='XXXXXXX';
DATABASE='gestioip'
USER='gestioip'

####### to here .... #######




NOW=`date +%s`
SM1=2629800 # seconds of one month

SM=`expr ${SM1} \* ${NUMBER_MONTH}` 

SINCE=`expr ${NOW} \- ${SM1}`

COMMAND_AUDIT="DELETE FROM audit WHERE id IN ( SELECT id FROM ( select * from audit ) AS audit WHERE date < ${SINCE})";
COMMAND_AUDIT_AUTO="DELETE FROM audit_auto WHERE id IN ( SELECT id FROM ( select * from audit_auto ) AS audit_auto WHERE date < ${SINCE})";

mysql -u ${USER} -p${GIP_PASS} --database ${DATABASE} --execute="${COMMAND_AUDIT}; ${COMMAND_AUDIT_AUTO}"
