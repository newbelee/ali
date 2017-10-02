#!/usr/bin/env python

import ConfigParser
import endecrypt
config = ConfigParser.ConfigParser()
cfgfile = open('/var/www/site/mycitsm/mycitsm/login.cnf', 'r')
config.readfp(cfgfile)
admin_user = config.get('mysqllogin', 'admin_user')
admin_passwd = endecrypt.decrypt(config.get('mysqllogin', 'admin_passwd'))
dev_user = config.get('mysqllogin', 'dev_user')
dev_passwd = endecrypt.decrypt(config.get('mysqllogin', 'dev_passwd'))
test_user = config.get('mysqllogin', 'test_user')
test_passwd = endecrypt.decrypt(config.get('mysqllogin', 'test_passwd'))
uat_user = config.get('mysqllogin', 'uat_user')
uat_passwd = endecrypt.decrypt(config.get('mysqllogin', 'uat_passwd'))
product_user = config.get('mysqllogin', 'product_user')
product_passwd = endecrypt.decrypt(config.get('mysqllogin', 'product_passwd'))
mysqluploaddb_site_user = config.get('mysqllogin', 'mysqluploaddb_site_user')
mysqluploaddb_site_passwd = endecrypt.decrypt(config.get('mysqllogin', 'mysqluploaddb_site_passwd'))
sqlmonitordb_user = config.get('mysqllogin', 'sqlmonitordb_user')
sqlmonitordb_passwd = endecrypt.decrypt(config.get('mysqllogin', 'sqlmonitordb_passwd'))
mysql_aes_encrypt_key = endecrypt.decrypt(config.get('key', 'mysql_aes_encrypt_key'))


print admin_passwd
