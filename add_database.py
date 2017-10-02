#!/usr/bin/env python
#coding: utf8

from contextlib import contextmanager
import MySQLdb


@contextmanager
def get_conn(**kwargs):
    conn = MySQLdb.connect(**kwargs)
    try:
        yield conn
    finally:
        conn.close()


def add_into_mysql(conn, db_name, db_host_w, db_port_w, db_host_r, db_port_r, db_user_r = 'read_user', db_pass_r = 'xx' ,env='生产', db_user_w = 'write_user', b_pass_w='xx'):
    add_db_info = "insert into db_baseinfo(DBName, Description, Owner, Department, importance) values('{0}', '{0}', '', '', 0)"
    add_db_env_config = "insert into release_dbconfig(dbname, host, port, upload_dbname, active, EnvID) VALUES('{0}', '{1}', {2}, '{0}', 1, 4)"
    add_db_conninfo = """insert into db_conninfo(dbname, envt, host, port, dbuser, password)
		select '{0}', '{1}', '{2}', {3}, '{4}', '{5}'"""
    add_sqltool_conn = """insert into sqltools_db_conninfo(dbid, dbname, host, port, dbuser, type) select id, dbname, '{0}', {1}, '{2}','{3}' from release_dbconfig where dbname  ='{4}'"""
    add_db_info_format = add_db_info.format(db_name, db_name)
    add_db_env_config_format = add_db_env_config.format(db_name, db_host_w, db_port_w)
    add_db_conninfo_format = add_db_conninfo.format(db_name, env, db_host_w, db_port_w, db_user_w, b_pass_w)
    add_sqltool_conn_read = add_sqltool_conn.format(db_host_r, db_port_r, db_user_r, 'R', db_name)
    add_sqltool_conn_write = add_sqltool_conn.format(db_host_w, db_port_w, db_user_w, 'W', db_name)
    with conn as cur:
        cur.execute(add_db_info_format)
        cur.execute(add_db_env_config_format)
        cur.execute(add_db_conninfo_format)
        cur.execute(add_sqltool_conn_read)
	cur.execute(add_sqltool_conn_write)


def main():
    conn_args = dict(host='127.0.0.1', user='root', passwd='123', db = 'mysqluploaddb', port=3306, charset="utf8")
    db_name = raw_input('input the database name:').strip()
    db_host_w = raw_input('input the database host for write instance:').strip()
    db_port_w = raw_input('input the database port for write instance:').strip()
    while True:
    	choice = raw_input("is the host and user same for read instance? y|n?").strip()
        choice = str(choice)
        if choice == 'y':
            db_host_r = db_host_w
            db_port_r = db_port_w
            break
        elif choice == 'n':
            db_host_r = raw_input('input the database host for read instance:').strip()
            db_port_r = raw_input('input the database port for read instance:').strip()
            break
        else:
            continue

    if not ( db_name and db_host_w and db_port_w and db_host_r and db_port_r):
        print "check your input"

    with get_conn(**conn_args) as conn:    
        add_into_mysql(conn, db_name, db_host_w, db_port_w, db_host_r, db_port_r)    


if __name__ == '__main__':
    main()
