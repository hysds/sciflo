#!/bin/bash

set -e

source $SCIFLO_DIR/etc/sciflo-env.sh

#tool=/usr/sciflo/sciflo/bin/insertDataFromXml.py
tool=$SCIFLO_DIR/bin/insertDataFromXml.py

date

dir=/home/mlissa1/xing/data_aeronet_dubov/data/xml

#db=dubovikdb
db=dubovdb
table=meta
metaXml=$dir/meta.xml.all
#metaXml=./meta.xml
echo loading $metaXml
$tool \
    -l "mysql://root:sciflo@127.0.0.1:8989/$db" \
    --recordTag file --keyTag fname \
    -t $table -u $metaXml

date
