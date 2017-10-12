#!/bin/bash
EXPOSER_DIR=$SCIFLO_DIR/share/sciflo/data/exposer
EXPOSER_PORT=`$SCIFLO_DIR/bin/getConfigVal.py exposerPort`
rm -rf $EXPOSER_DIR; mkdir -p $EXPOSER_DIR; cd $EXPOSER_DIR
nohup python -u $SCIFLO_DIR/bin/exposer.py --port=$EXPOSER_PORT \
--xmlDir=$SCIFLO_DIR/etc/soap --addPath=$SCIFLO_DIR/scripts/soap \
--wsdlDir=$SCIFLO_DIR/etc/soap/wsdl --type forking \
--serveDir=$EXPOSER_DIR \
> $SCIFLO_DIR/log/exposer.log 2>&1 &
