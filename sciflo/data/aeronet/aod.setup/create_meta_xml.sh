#!/bin/bash

set -e

for level in 1.5 2.0; do
dataDir=./sample/$level/txt/
metaXML=./sample/$level/xml/meta.xml
./txt/summarize.py $dataDir $level > $metaXML
done
