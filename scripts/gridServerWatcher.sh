#!/bin/bash
source ~/sciflo/etc/sciflo-env.sh
running=0
uid=`id -u`
gridIds=`ps -C python | awk '{print $1}' | xargs -i -t grep gridServerCtl /proc/{}/cmdline 2>/dev/null | grep matches | awk 'BEGIN{FS="/"}{print $3}'`
for id in $gridIds; do
    found=`grep ^Uid /proc/$id/status | grep -c $uid`;
    if [ $found -eq 1 ]; then
       running=$found;
    fi
done
if [ $running -eq 0 ]; then
    $SCIFLO_DIR/bin/startGridServer.sh;
    date;
    echo "No grid server found running.  Started it up.";
fi
