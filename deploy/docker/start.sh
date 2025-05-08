#!/bin/bash

echo "Starting up the webapp from $(pwd)=$DEBUG..."

WORKDIR=$(pwd)


# Start the webapp in the background
cd ./web
if [ -n "$DEBUG" ]; then
    echo "Starting webapp in debug mode (DEBUG=$DEBUG)..."
    export FLASK_APP=server.py && flask run --debug --port 80 --host 0.0.0.0 &
else
    gunicorn -w 1 -b :80 server:app &
fi


# here we use the `entr` command to listen for changes to the database file
# and trigger the on-rsvp-change.sh script when it changes
# This is a simple way to watch for changes in the file and run a command
# to update the authorized users on the target machines

echo "Listening for changes to database: $WORKDIR/web/.data/reservations.csv"
cd $WORKDIR/web
ls ./.data/reservations.csv | entr -spn "../on-rsvp-change.sh"
