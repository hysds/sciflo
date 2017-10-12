export MYSQL_PWD=sciflo

#port=8989
port=8979

#db=dubovikdb
db=dubovdb

#mysqladmin -h 127.0.0.1 -P $port -u root drop $db
#mysqladmin -h 127.0.0.1 -P $port -u root create $db

#mysqlshow -h 127.0.0.1 -P $port -u root
mysqlshow -h 127.0.0.1 -P $port -u root $db
#mysqldump -h 127.0.0.1 -P $port -u root $db meta
#mysqldump -h 127.0.0.1 -P $port -u root $db data
