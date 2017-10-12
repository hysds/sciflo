#!/bin/sh

set -e

. /usr/sfldev/sciflo/etc/sciflo-env.sh

tool=/usr/sfldev/sciflo/bin/insertDataFromXml.py

date

db=aeronetdb
#port=8989
port=8979

level=2.0
dir=/data/df3/xing/aeronet-data/xml

table=level20_meta
metaXml=$dir/lev20.meta.xml
echo loading $metaXml
$tool \
    -l "mysql://root:sciflo@127.0.0.1:$port/$db" \
    --recordTag file --keyTag fname \
    -t $table -u $metaXml


table=level20_data
for x in $dir/lev20/*lev*.xml; do
date
echo loading $x
$tool \
    -l "mysql://root:sciflo@127.0.0.1:$port/$db" \
    --recordTag record --keyTag dt \
    -t $table -u $x
done

date
