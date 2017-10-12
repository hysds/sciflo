#!/bin/bash
DB_PORT=`$SCIFLO_DIR/bin/getConfigVal.py dbPort`
cd $SCIFLO_DIR
bin/mysqld_safe --no-defaults --socket=$SCIFLO_DIR/log/mysqld.sock --port=$DB_PORT --datadir=$SCIFLO_DIR/data --log-error=$SCIFLO_DIR/log/mysqld.log --max_allowed_packet=1G > $SCIFLO_DIR/log/mysqld.log 2>&1 &
