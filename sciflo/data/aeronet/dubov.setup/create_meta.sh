#in=./sample/txt
#outFile=./sample/xml/meta.xml

in=/data/df3/xing/aeronet-data/dubov/data/raw
outFile=/data/df3/xing/aeronet-data/dubov/xml/meta.xml

python ./tool/summarize.py $in > $outFile
