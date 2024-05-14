#!/bin/bash

# this is scheduled as cronjob running on boot, it listens
# to filechanges to the db, whenever a change is detected it runs
# a dedicated script to notify the target machines

echo $PATH
WORDKDIR=$(dirname $0)

cd $WORDKDIR
echo "Listening for changes to database: $(pwd)/.data/reservations.csv"
ls ./.data/reservations.csv | /usr/local/bin/entr -spn './on-rsvp-change.sh'