export MYSQL_PWD=sciflo
#port=8989
port=8979

db=aeronetdb

mysql -h 127.0.0.1 -P $port -u root $db -e "rename table level15_meta to level15_meta_old"
mysql -h 127.0.0.1 -P $port -u root $db -e "rename table level15_data to level15_data_old"

#mysql -h 127.0.0.1 -P $port -u root $db -e "rename table level20_meta to level20_meta_old"
#mysql -h 127.0.0.1 -P $port -u root $db -e "rename table level20_data to level20_data_old"
