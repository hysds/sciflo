#!/bin/bash
PORT=`$SCIFLO_DIR/bin/getConfigVal.py gridPort`
python $SCIFLO_DIR/bin/gridServerCtl.py --kill
\ps x | grep [g]ridServerCtl | awk '{print $1}' | xargs kill -9 2>/dev/null
rm -rf /tmp/sciflo-${PORT}.lock
