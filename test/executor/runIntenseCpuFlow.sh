#!/bin/bash
rm -f runflows.log
count=0
while [ "$count" -le "100" ]; do
    echo $count
    time ./runFlowNoBg.sh test_manysciflos.sf.xml
    count=$(($count+1))
done
