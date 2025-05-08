#!/bin/bash

###############################
# reads all reservations and uses the current time to determine
# which reservations are active, then it updates the authorized
# users file on the target machines.
###############################
echo "Running on-rsvp-change.sh script"

# First define required environment variables if not set
: "${ADMIN_USER_ON_SWITCH:=admin}"
: "${SSH_RESERVATIONS_CONFIG_ON_SWITCH:=/etc/ssh/reservations.conf}"

# Get current timestamp
NOW=$(date +%s)

# Process reservations file
tail -n +2 ./.data/reservations.csv | while IFS=, read -r id user target from_date to_date rest; do
    # Convert dates to timestamps
    FROM=$(date -d "$from_date" +%s 2>/dev/null)
    TO=$(date -d "$to_date" +%s 2>/dev/null)
    
    # Skip invalid dates
    [ -z "$FROM" ] || [ -z "$TO" ] && continue
    
    # Check if reservation is active
    if [ "$NOW" -le "$TO" ] && [ "$NOW" -ge "$FROM" ]; then
        TARGET="${target}.polito.it"
        echo "Active reservation found: $user on $TARGET until $(date -d "@$TO")"
        
        # ----- Test ------
        # echo "Connecting to $TARGET with user $ADMIN_USER_ON_SWITCH..."
        
        # ssh -o ConnectTimeout=5 $ADMIN_USER_ON_SWITCH@$TARGET "echo 'Connection test successful'"
        
        # Uncomment to enable reservation updates on remote switch
        # You can check the logs of this by inspecting the container logs of the website 
        # docker compose logs <service name for the web dashboard>
        # -----------------
        echo "$user,$(date -d "@$TO")" | ssh -o ConnectTimeout=10 -o BatchMode=yes $ADMIN_USER_ON_SWITCH@$TARGET "
            sudo tee $SSH_RESERVATIONS_CONFIG_ON_SWITCH &&
            sudo $ENFORCE_SSH_ACCESS_RESERVATION_SCRIPT_ON_SWITCH
            echo 'SSH command completed successfully'
        "

    fi
done