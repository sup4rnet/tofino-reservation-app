#!/bin/bash

###############################
# reads all reservations and uses the current time to determine
# which reservations are active, then it updates the authorized
# users file on the target machines. This script is triggered
# by the rest-db-watch.sh script whenever a change in the db
# is detected
###############################

tail -n +2 ./.data/reservations.csv | awk -F, '{
    
    "date +%s" | getline now
    "date -d \"" $4 "\" +%s" | getline to

    if (now <= to && now >= from) {
        target = $2 ".polito.it"
        print $1 "," $4 "," target
    }

}' | while read -r line; do

    # enter here only if active reservation    
    user=$(echo $line | cut -d, -f1)
    expire=$(echo $line | cut -d, -f2)
    target=$(echo $line | cut -d, -f3)

    # update the authorized users file on remotes
    echo "$user,$expire" | ssh p4-restart@$target "
            sudo tee /home/p4-restart/.restart-super/ssh_authorized_users > /dev/null
            sudo /home/p4-restart/.restart-super/user_accesses.sh
    "
    
done