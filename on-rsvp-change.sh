#!/bin/bash

###############################
# reads all reservations and uses the current time to determine
# which reservations are active, then it triggers the remote execution of the script
# to enforce the SSH access reservation on the target machine
###############################
echo "Running on-rsvp-change.sh script"

if [ -n $DEBUG ]; then
    echo "DEBUG: SSH command $ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH would be executed on remote"
else
    # below we run the command to enforce the SSH access reservation: it will play with SSH groups
    ssh -o ConnectTimeout=10 -o BatchMode=yes $ADMIN_USER_ON_SWITCH@$TARGET "
        sudo $ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH &&
        echo 'SSH command completed successfully'
    "
fi
