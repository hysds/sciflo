#!/bin/bash
cd /tmp
python $SCIFLO_DIR/bin/gridServerCtl.py --key $SCIFLO_DIR/ssl/hostkey.pem \
--cert $SCIFLO_DIR/ssl/hostcert.pem  --type twisted --log > $SCIFLO_DIR/log/scifloServer.log 2>&1
ZOMBIE=`grep Zombie $SCIFLO_DIR/log/scifloServer.log`
if (test -n "$ZOMBIE") then
    echo $ZOMBIE
fi
