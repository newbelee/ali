#!/usr/bin/env python

import ConfigParser
import endecrypt
config = ConfigParser.ConfigParser()
cfgfile = open('/var/www/site/mycitsm/mycitsm/login.cnf', 'r')
config.readfp(cfgfile)
admin_user = config.get('mysqllogin', 'admin_user')
admin_passwd = endecrypt.decrypt(config.get('mysqllogin', 'admin_passwd'))
product_user = config.get('mysqllogin', 'product_user')
product_passwd = endecrypt.decrypt(config.get('mysqllogin', 'product_passwd'))
mysqluploaddb_site_user = config.get('mysqllogin', 'mysqluploaddb_site_user')
mysql_aes_encrypt_key = endecrypt.decrypt(config.get('key', 'mysql_aes_encrypt_key'))


print admin_passwd
