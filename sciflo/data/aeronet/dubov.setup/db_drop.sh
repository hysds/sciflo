export MYSQL_PWD=sciflo
#port=8989
port=8979

db=dubovdb

mysql -h 127.0.0.1 -P $port -u root $db -e "drop table meta"
mysql -h 127.0.0.1 -P $port -u root $db -e "drop table data"
