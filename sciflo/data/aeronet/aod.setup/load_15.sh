#!/bin/sh

set -e

. /usr/sfldev/sciflo/etc/sciflo-env.sh

tool=/usr/sfldev/sciflo/bin/insertDataFromXml.py

date

db=aeronetdb
#port=8989
port=8979

level=1.5
dir=/data/df3/xing/aeronet-data/xml

table=level15_meta
metaXml=$dir/lev15.meta.xml
echo loading $metaXml
$tool \
    -l "mysql://root:sciflo@127.0.0.1:$port/$db" \
    --recordTag file --keyTag fname \
    -t $table -u $metaXml


table=level15_data
for x in $dir/lev15/*lev*.xml; do
date
echo loading $x
$tool \
    -l "mysql://root:sciflo@127.0.0.1:$port/$db" \
    --recordTag record --keyTag dt \
    -t $table -u $x
done

date
