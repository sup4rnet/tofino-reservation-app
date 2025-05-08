#!/bin/bash

echo "Starting up the webapp from $(pwd)=$DEBUG..."

WORKDIR=$(pwd)

# Start the webapp in the background
cd ./web
if [ -n "$DEBUG" ]; then
    echo "Starting webapp in debug mode (DEBUG=$DEBUG)..."
    export FLASK_APP=server.py && flask run --debug --port 80 --host 0.0.0.0
else
    gunicorn -w 1 -b :80 server:app --log-level debug --access-logfile - --error-logfile - &
fi






echo "Listening for changes to database: $WORKDIR/web/.data/reservations.csv"
cd $WORKDIR/web
ls ./.data/reservations.csv | entr -spn "../deploy/docker/on-rsvp-change.sh > $WORKDIR/deploy/docker/rsvp-change.log 2>&1"
