#!/bin/sh

set -e

source $SCIFLO_DIR/etc/sciflo-env.sh

#tool=/usr/sciflo/sciflo/bin/insertDataFromXml.py
tool=$SCIFLO_DIR/bin/insertDataFromXml.py

date

#db=dubovikdb
db=dubovdb
table=data
#dir=./sample/xml
dir=/home/mlissa1/xing/data_aeronet_dubov/data/xml

for x in $dir/*.xml; do
date
echo loading $x
$tool \
    -l "mysql://root:sciflo@127.0.0.1:8989/$db" \
    --recordTag record --keyTag dt \
    -t $table -u $x
done

date
