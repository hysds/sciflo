#!/bin/bash
source $SCIFLO_DIR/etc/sciflo-env.sh
SFLWORKDIR=`$SCIFLO_DIR/bin/getConfigVal.py sflWorkDir`
SFLEXECDIR=`$SCIFLO_DIR/bin/getConfigVal.py sflExecDir`
rm -rf  $SFLWORKDIR $SFLEXECDIR
python $SCIFLO_DIR/bin/flowcheck.py -o $1 -r $2
