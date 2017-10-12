#!/bin/bash

set -e

for level in 1.5 2.0; do
metaXML=./sample/$level/xml/meta.xml
inDir=./sample/$level/txt/
outDir=./sample/$level/xml/
python ./txt/txt2xml.py $level $metaXML $inDir $outDir
done
