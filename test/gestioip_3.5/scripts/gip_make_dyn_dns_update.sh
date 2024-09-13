#!/bin/bash

# This script is executed by GestioIP to notify the master DNS server
# of changes in the GestioIP database

# version 3.5.7 20210812


LOG="/usr/share/gestioip/var/log/make_update.log"

UPDATE_TYPE=$1
KRB_USER=$2
KRB_PASS=$3
KRB_REALM=$4
ZONE_NAME=$5
DNS_SERVER=$6
UPDATE_ENTRY=$7
UPDATE_ENTRY_IP=$8
UPDATE_ENTRY_IP_ARPA=$9
ZONE_NAME_ARPA=${10}
TTL=${11}
UPDATE_ENTRY_DELETE=${12}
IP_VERSION=${13}
TSIG_KEY=${14}
TSIG_KEY_NAME=${15}
DEBUG=${16}

DATE=`date`

echo $DATE: $UPDATE_TYPE ${KRB_USER} XXXXXX ${KRB_REALM} $ZONE_NAME $DNS_SERVER $UPDATE_ENTRY $UPDATE_ENTRY_IP $UPDATE_ENTRY_IP_ARPA $ZONE_NAME_ARPA $TTL $UPDATE_ENTRY_DELETE $IP_VERSION XXXXX $TSIG_KEY_NAME $DEBUG >> $LOG

if [ "${DEBUG}" == 1 ]
then
    echo UPDATE_TYPE=$UPDATE_TYPE >> $LOG
    echo KRB_USER=$KRB_USER >> $LOG
    echo KRB_PASS=XXXXXXXX >> $LOG
    echo KRB_REALM=$KRB_REALM >> $LOG
    echo ZONE_NAME=$ZONE_NAME >> $LOG
    echo DNS_SERVER=$DNS_SERVER >> $LOG
    echo UPDATE_ENTRY=$UPDATE_ENTRY >> $LOG
    echo UPDATE_ENTRY_IP=$UPDATE_ENTRY_IP >> $LOG
    echo UPDATE_ENTRY_IP_ARPA=$UPDATE_ENTRY_IP_ARPA >> $LOG
    echo ZONE_NAME_ARPA=$ZONE_NAME_ARPA >> $LOG
    echo TTL=$TTL >> $LOG
    echo UPDATE_ENTRY_DELETE=$UPDATE_ENTRY_DELETE >> $LOG
    echo IP_VERSION=$IP_VERSION >> $LOG
    echo TSIG_KEY=$TSIG_KEY >> $LOG
    echo TSIG_KEY_NAME=$TSIG_KEY_NAME >> $LOG
    echo DEBUG=$DEBUG >> $LOG
fi


if [ -z "$IP_VERSION" ]
then
    echo "Argument missing"
    exit
fi

NSUPDATE_COMMANDS="/tmp/nsupdate_commands"
NSUPDATE="/usr/bin/nsupdate"
KLIST="/usr/bin/klist"
KINIT="/usr/bin/kinit"

ENTRY_TYPE="A"
if [ "${IP_VERSION}" == "v6" ]
then
    ENTRY_TYPE="AAAA"
fi

if [[ ${TSIG_KEY} =~ "DUMMY" ]]
then
    # NO TSIG KEY given
    export KRB_USER=${KRB_USER}
    export KRB_PASS=${KRB_PASS}
    export KRB_REALM=${KRB_REALM}


    #check if ticket already exists
    if [ ${DEBUG} -eq 1 ]
    then
        echo "$KLIST | grep \"${KRB_USER}@${KRB_REALM}\"" >> $LOG
        $KLIST | grep "${KRB_USER}@${KRB_REALM}" >>$LOG 2>&1
        RES=$?
    else
        $KLIST | grep "${KRB_USER}@${KRB_REALM}" >>/dev/null 2>&1
        RES=$?
    fi

    if [ ${RES} -ne 0 ]
    then
        # create KRB ticket if no ticket was found
        if [ ${DEBUG} -eq 1 ]
        then
            echo $DATE Creating Ticket: \"echo XXXXXX \| $KINIT ${KRB_USER}@${KRB_REALM}\" >> $LOG
            echo $KRB_PASS | $KINIT -V ${KRB_USER}@${KRB_REALM} >>$LOG 2>&1 
            $KLIST | grep "${KRB_USER}@${KRB_REALM}" >>$LOG 2>&1
            RES=$?
        else
            echo $KRB_PASS | $KINIT ${KRB_USER}@${KRB_REALM} >>/dev/null 2>&1 
            $KLIST | grep "${KRB_USER}@${KRB_REALM}" >>/dev/null 2>&1
            RES=$?
        fi
    fi    

    if [ ${RES} -ne 0 ]
    then
        # exit if no ticket was found
        echo "ERROR: Unable to create KRB ticket - DNS not updated"
        if [ ${DEBUG} -eq 1 ]
        then
            echo "ERROR: Unable to create KRB ticket - DNS not updated" >> $LOG
        fi
        exit 2
    fi

    echo server ${DNS_SERVER} > $NSUPDATE_COMMANDS
    echo realm ${KRB_REALM} >> $NSUPDATE_COMMANDS

else
    echo server ${DNS_SERVER} > $NSUPDATE_COMMANDS
    echo key $TSIG_KEY_NAME $TSIG_KEY >> $NSUPDATE_COMMANDS

fi

if [ ${UPDATE_TYPE} -eq 2 ]
then
    #add A and PTR entry
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY} ${TTL} ${ENTRY_TYPE} ${UPDATE_ENTRY_IP}" >> $NSUPDATE_COMMANDS
    echo >> $NSUPDATE_COMMANDS
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY_IP_ARPA} ${TTL} PTR ${UPDATE_ENTRY}." >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 3 ]
then
    #add A only
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY} ${TTL} ${ENTRY_TYPE} ${UPDATE_ENTRY_IP}" >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 4 ]
then
    #add PTR only
    if [ "${ZONE_NAME_ARPA}" == "DUMMY_NO_PTR_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_PTR_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY_IP_ARPA} ${TTL} PTR ${UPDATE_ENTRY}." >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 5 ]
then
    #delete A and PTR
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    if [ "${ZONE_NAME_ARPA}" == "DUMMY_NO_PTR_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_PTR_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY} ${ENTRY_TYPE}" >> $NSUPDATE_COMMANDS
    echo >> $NSUPDATE_COMMANDS
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_IP_ARPA} PTR" >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 6 ]
then
    #delete A only
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY} ${ENTRY_TYPE}" >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 7 ]
then
    #delete PTR only
    if [ "${ZONE_NAME_ARPA}" == "DUMMY_NO_PTR_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_PTR_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_IP_ARPA} PTR" >> $NSUPDATE_COMMANDS
elif [ ${UPDATE_TYPE} -eq 8 ]
then
    #update A and PTR
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    if [ "${ZONE_NAME_ARPA}" == "DUMMY_NO_PTR_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_PTR_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_DELETE} ${ENTRY_TYPE}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY} ${TTL} ${ENTRY_TYPE} ${UPDATE_ENTRY_IP}" >> $NSUPDATE_COMMANDS
    echo >> $NSUPDATE_COMMANDS
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_IP_ARPA} PTR" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY_IP_ARPA} ${TTL} PTR ${UPDATE_ENTRY}." >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 9 ]
then
    #update A only
    if [ "${ZONE_NAME}" == "DUMMY_NO_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_DELETE} ${ENTRY_TYPE}" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY} ${TTL} ${ENTRY_TYPE} ${UPDATE_ENTRY_IP}" >> $NSUPDATE_COMMANDS

elif [ ${UPDATE_TYPE} -eq 10 ]
then
    #update ptr only
    if [ "${ZONE_NAME_ARPA}" == "DUMMY_NO_PTR_ZONE_NAME" ]
    then
        echo "DNS update error: No Zone: DUMMY_NO_PTR_ZONE_NAME"
		exit 4
    fi
    echo "zone ${ZONE_NAME_ARPA}" >> $NSUPDATE_COMMANDS
    echo "update delete ${UPDATE_ENTRY_IP_ARPA} PTR" >> $NSUPDATE_COMMANDS
    echo "update add ${UPDATE_ENTRY_IP_ARPA} ${TTL} PTR ${UPDATE_ENTRY}." >> $NSUPDATE_COMMANDS

else
    echo
    echo "unsupported update type. Use \"add\" or \"delete\""
    exit 3
fi

if [ ${DEBUG} -eq 1 ]
then
    echo debug >> $NSUPDATE_COMMANDS
fi
echo send >> $NSUPDATE_COMMANDS

if [ ${DEBUG} -eq 1 ]
then
    # does not work for win2000. Delete the "-g" option to make it work with win2000.
    echo "executing $NSUPDATE -L 10 -g -t 10 < $NSUPDATE_COMMANDS" >> $LOG
    echo
    cat $NSUPDATE_COMMANDS >> $LOG
    $NSUPDATE -L 10 -g -t 10 < $NSUPDATE_COMMANDS >> $LOG 2>&1
    RES=$?
else
    $NSUPDATE -g -t 10 < $NSUPDATE_COMMANDS > /dev/null 2>&1
    RES=$?
fi

if [ ${RES} -ne 0 ]
then
    echo "DNS update error: ${RES}"
    exit 4
fi

exit 0

