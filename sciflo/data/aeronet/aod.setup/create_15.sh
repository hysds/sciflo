#!/bin/bash

set -e

level=1.5
dataDir=/data/df3/xing/aeronet-data/expanded/lev15
metaXML=/data/df3/xing/aeronet-data/xml/lev15.meta.xml
./txt/summarize.py $dataDir $level > $metaXML

inDir=$dataDir
outDir=/data/df3/xing/aeronet-data/xml/lev15
python ./txt/txt2xml.py $level $metaXML $inDir $outDir
