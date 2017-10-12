export MYSQL_PWD=sciflo
#port=8989
port=8979

db=aeronetdb

mysql -h 127.0.0.1 -P $port -u root $db -e "drop table level15_meta"
mysql -h 127.0.0.1 -P $port -u root $db -e "drop table level15_data"

#mysql -h 127.0.0.1 -P $port -u root $db -e "drop table level20_meta"
#mysql -h 127.0.0.1 -P $port -u root $db -e "drop table level20_data"
