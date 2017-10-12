#!/bin/bash
source ~/sciflo/etc/sciflo-env.sh
running=0
exposerPort=`$SCIFLO_DIR/bin/getConfigVal.py exposerPort`
exposerIds=`ps -C python | awk '{print $1}' | xargs -i -t grep exposer /proc/{}/cmdline 2>/dev/null | grep matches | awk 'BEGIN{FS="/"}{print $3}'`
for id in $exposerIds; do
    found=`grep -c $exposerPort /proc/$id/cmdline`;
    if [ $found -eq 1 ]; then
       running=$found;
    fi
done
if [ $running -eq 0 ]; then
    $SCIFLO_DIR/bin/startExposer.sh;
    date;
    echo "No exposer found running.  Started it up.";
fi
