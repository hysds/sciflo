#!/bin/bash

#export PYTHONPATH=/home/mlissa1/xing/pymodule:$PYTHONPATH
#echo $PYTHONPATH

source $SCIFLO_DIR/etc/sciflo-env.sh
#source /usr/sfldev/sciflo/etc/sciflo-env.sh

datasetName="aeronet"
level="2.0"
version="ignored"

#dt0="2007-05-01T00:00:00Z"
#dt1="2007-05-01T23:59:59Z"
dt0="2008-05-19T18:00:00Z"
dt1="2008-05-20T23:59:59Z"

#dt1="2007-05-31 23:59:59"
#dt0="2000-01-01 00:00:00"
#dt1="2000-01-07 23:59:59"

lon0=-180; lon1=180
#lat0=-5; lat1=5
lat0=-90; lat1=90

#responseGroups="Small"
#responseGroups="Small,Particles"
level="1.5"
responseGroups="Small,MAN"
#responseGroups="Medium,Particles"
responseGroups="Medium,MAN"
#responseGroups="Large"
#responseGroups="Large,Particles"
#responseGroups="Large,MAN"

dburi="root:sciflo@127.0.0.1:8989/aeronetdb"

outDir="/tmp/xing"
outDirUrl="http://sciflo.jpl.nasa.gov/data/"

date
time python /home/mlissa1/xing/aeronet/service.py $datasetName $level $version "$dt0" "$dt1" $lat0 $lat1 $lon0 $lon1 $responseGroups $dburi $outDir $outDirUrl
#time python /home/mlissa1/xing/pymodule/sciflo/data/aeronet/rdb/service.py $datasetName $level $version "$dt0" "$dt1" $lat0 $lat1 $lon0 $lon1 $responseGroups $dburi
#time service.py $datasetName $level $version "$dt0" "$dt1" $lat0 $lat1 $lon0 $lon1 $responseGroups $dburi
date
