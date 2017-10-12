#!/bin/bash
WORKDIR=`getConfigVal.py workUnitRootWorkDir`
rm -rf $WORKDIR output
count=0
while [ "$count" -le "5000" ]; do
    echo $count
    var2=$(($count+100))
    var3=$(($count+1000))
    var4=$(($count+2))
    var5=$(($count+1000000))
    if [ "$count" -eq "5" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "500" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "1000" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "1500" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "2000" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "2500" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "3000" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "3500" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "4000" ]; then rm -rf $WORKDIR output; mkdir output; fi
    if [ "$count" -eq "4500" ]; then rm -rf $WORKDIR output; mkdir output; fi
    time python -u $HOME/sciflo/bin/sflExec.py -f -o output/output_${count} --args var1=$count,var2=$var2,var3=$var3,var4=$var4,var5=$var5 mytest.sf.xml 2>&1 | tee run.log
    time python -u $HOME/sciflo/bin/sflExec.py -f -o output/output_${count}_cached --args var1=$count,var2=$var2,var3=$var3,var4=$var4,var5=$var5 mytest.sf.xml 2>&1 | tee run.log
    count=$(($count+1))
done
