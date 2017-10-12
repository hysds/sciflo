#!/bin/bash
#rm -f runflows.log
for i in `ls *.sf.xml`; do ./runFlow.sh $i ; done
