#in=./sample/txt
#out=./sample/xml

in=/data/df3/xing/aeronet-data/dubov/data/raw
out=/data/df3/xing/aeronet-data/dubov/xml

python ./tool/txt2xml.py $out/meta.xml $in $out
