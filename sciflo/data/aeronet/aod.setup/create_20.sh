#!/bin/bash

set -e

level=2.0
dataDir=/home/mlissa1/xing/a/aeronet-data/expanded/lev20/AOT/LEV20/ALL_POINTS
metaXML=/data/df3/xing/aeronet-data/xml/lev20.meta.xml
./txt/summarize.py $dataDir $level > $metaXML

inDir=$dataDir
outDir=/data/df3/xing/aeronet-data/xml/lev20
python ./txt/txt2xml.py $level $metaXML $inDir $outDir
