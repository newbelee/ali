# -*- coding: utf-8 -*- 
from commonconfig import *
import sqlparse
from threading import Timer
from django import forms

import time
import signal


reload(sys)
sys.setdefaultencoding('UTF-8')

class sqlreviewForm(forms.Form):
    tips='Your SQl goes here...(Editor Tips: Start searching: Ctrl-F, Find next: Ctrl-G, Find previous: Shift-Ctrl-G, Replace: Shift-Ctrl-F, Replace all:Shift-Ctrl-R)'
    sql = forms.CharField(widget=forms.Textarea(attrs={'cols':140,'rows':20,'placeholder':tips}), label='您的SQL语句:',required=True)
    required_css_class = 'required'


@login_required
def executesql(request):
    maxSqlAmount = 10
    envId = 4
    cursor = connection.cursor()

    param = []
    #取出可用数据库名和ID
    if request.user.is_superuser:
        sql = """
                select id,  Upload_DBName from  
                    release_dbconfig 
                """
    else:
        sql = """
            select dbid as id, dbname as Upload_DBName from  
                sqltools_user_db 
                where username = %s and status = 1
            """
        param = [request.user.username]
    cursor.execute(sql, param)
    dblist = dictFetchall(cursor)
    cursor.close()
                
    if request.method == "GET":
        databaseName = request.GET.get('databaseName','')
        if dblist:
            databaseId = str(dblist[0]['id'])
        else:
            databaseId = 0

        if databaseName:
            for item in dblist:             
                if str(databaseName).lower() == str(item['Upload_DBName']).lower():
                    databaseId = str(item['id'])
                    break
    elif request.method == 'POST':
        retno = None
        retmsg = None
        sqlErrorDict={}
        exec_errors=[]
        field_desc=[]
        sqlResultDict=[]

        db_conn_exe_id = 0

        form = sqlreviewForm(request.POST)

        databaseId = request.POST.get('databaseId','')
        sql = request.POST.get('sql','')

        if sql == "":
            sqlErrorDict={}
            sqlErrorDict['sql']=""
            sqlErrorDict['error']="get sql failed: 请输入 sql"
            exec_errors.append(sqlErrorDict)
            sqlResultDict=[]
            field_desc.append("error")

            context={'form':form,
                     'title':'在线查询',
                     'errorSqlList':exec_errors,
                     'sqlResultDict':sqlResultDict,
                     'field_desc':field_desc,
                     'width':str(100/len(field_desc)) +'%',
                     'dblist':dblist,
                     'databaseId': databaseId
            }
            return render(request, 'executesql.html',context)     

        
        
        if request.POST.get('formatsql'):
            format_sql = ""
            unformattedSqlList = []
            (format_sql, unformattedSqlList) = get_formatsql(request)

            form = sqlreviewForm({'sql':format_sql})

            context={'form':form,
                     'title':'在线查询',
                     'unformattedSqlList':unformattedSqlList,
                     'dblist':dblist,
                     'databaseId': databaseId
            }
            return render(request, 'executesql.html',context)

        elif request.POST.get('getExecutePlan'):
            chk_errors = []
            field_desc = []
            chk_errors = chk_sql_select(request)
            if chk_errors:
                context={'form':form,
                         'title':'在线查询',
                         'errorSqlList':chk_errors,
                         'dblist':dblist,
                         'databaseId': databaseId
                }
                return render(request, 'executesql.html',context)                
            
            (desc_errors,sqlResultDict,field_desc)=get_desc(request)

            context={'form':form,
                     'title':'在线查询',
                     'errorSqlList':desc_errors,
                     'sqlResultDict':sqlResultDict,
                     'field_desc':field_desc,
                     'width':str(100/len(field_desc)) +'%',
                     'dblist':dblist,
                     'databaseId': databaseId
            }

            return render(request, 'executesql.html',context)                
        
        elif request.POST.get('executesql'):

            errors=[]

            if not request.POST.get('databaseId',''):
                errors.append('请选择数据库')
                return render_to_response('error.html',{
                    'errors':errors,
                    'user':request.user.username,
                    'title':"Error"
                })

            chk_errors = chk_sql_select(request)
            if chk_errors:
                context={'form':form,
                         'title':'在线查询',
                         'errorSqlList':chk_errors,
                         'dblist':dblist,
                         'databaseId': databaseId
                }
                return render(request, 'executesql.html',context)
                    

            sql = """select host,port,dbname
                from  sqltools_db_conninfo
                where dbid = %s and type = 'R';"""
            cursor = connection.cursor()
            param = [request.POST.get('databaseId')]
            cursor.execute(sql, param)
            db_connstr = dictFetchall(cursor)
            cursor.close()
            if len(db_connstr) > 0:
                db_host = db_connstr[0]["host"]
                db_port = db_connstr[0]["port"]
                db_name = db_connstr[0]["dbname"]
            else:
                sqlErrorDict={}
                sqlErrorDict['sql']=""
                sqlErrorDict['error']="get dbconect failed: 未找到 db 连接串"
                exec_errors.append(sqlErrorDict)
                sqlResultDict=[]
                field_desc.append("error")

                context={'form':form,
                         'title':'在线查询',
                         'errorSqlList':exec_errors,
                         'sqlResultDict':sqlResultDict,
                         'field_desc':field_desc,
                         'width':str(100/len(field_desc)) +'%',
                         'dblist':dblist,
                         'databaseId': databaseId
                }
                return render(request, 'executesql.html',context)                

            # check top table privileges
            (retno, retmsg, tblist) = check_table_priv(request, db_name)
            if retno == -1:
                sqlErrorDict={}
                sqlErrorDict['sql']=""
                sqlErrorDict['error']="没有对象的查询权限: %s" %(tblist)

                exec_errors.append(sqlErrorDict)
                sqlResultDict=[]
                field_desc.append("error")

                context={'form':form,
                         'title':'在线查询',
                         'errorSqlList':exec_errors,
                         'sqlResultDict':sqlResultDict,
                         'field_desc':field_desc,
                         'width':str(100/len(field_desc)) +'%',
                         'dblist':dblist,
                         'databaseId': databaseId
                }
                return render(request, 'executesql.html',context)

            (retno, retmsg, db_conn_exe) = getdbconnection(db_name,db_host, db_port, "0")
            db_conn_exe_id = db_conn_exe.thread_id()
            if retno == -1:
                sqlErrorDict={}
                sqlErrorDict['sql']=""
                sqlErrorDict['error']="get dbconect failed: %s" %(retmsg)
                exec_errors.append(sqlErrorDict)
                sqlResultDict=[]
                field_desc.append("error")

                context={'form':form,
                         'title':'在线查询',
                         'errorSqlList':exec_errors,
                         'sqlResultDict':sqlResultDict,
                         'field_desc':field_desc,
                         'width':str(100/len(field_desc)) +'%',
                         'dblist':dblist,
                         'databaseId': databaseId
                }
                return render(request, 'executesql.html',context)    

            db_conn_kill = getConn(db_host, db_port,db_name)

            exec_errors = []
            field_desc = []
            sqlResultDict=[]           

            __result=None

            timer = ExecutionTime()

            execThd = execThread(1,request,db_conn_exe, db_name)
            execThd.setDaemon(True)
            execThd.start()            
            execThd.join(60)

            __result = execThd.getResult()

            if len(__result["field_desc"]) > 0:
                exec_errors=__result["exec_errors"]
                sqlResultDict=__result["sqlResultDict"]
                field_desc=__result["field_desc"]
            else:
                exec_errors.append({"sql":"","error":"TIMEOUT: max execute time is : 60s"})
                field_desc.append("error")
                if db_conn_exe_id > 0:
                    kill_dbconnection(db_conn_exe_id, db_conn_kill)

            if not db_conn_exe:              
                db_conn_exe.close()
            if not db_conn_kill:
                db_conn_kill.close()

            if len(sqlResultDict) == 0 and len(exec_errors) == 0:
               exec_errors.append({"sql":"","error":"没有满足条件的记录"})
               field_desc.append("info")

            context={'form':form,
                     'title':'在线查询',
                     'errorSqlList':exec_errors,
                     'sqlResultDict':sqlResultDict,
                     'field_desc':field_desc,
                     'width':str(100/len(field_desc)) +'%',
                     'dblist':dblist,
                     'databaseId': databaseId,
                     'time': '{}'.format(round(timer.duration(), 2)),
                     'rowcount':len(sqlResultDict)
            }

            return render(request, 'executesql.html',context)    

    form = sqlreviewForm()
    
    context = {
        'form':form, 
        'title':'在线查询',
        'dblist':dblist,
        'databaseId':databaseId
    }

    return render(request, 'executesql.html',context)

@login_required
def get_formatsql(request):
    try:
        unformattedSqlList = []
        sql = request.POST.get('sql','')
        format_sql = sqlparse.format(sql, reindent=True, keyword_case='upper');            
    except Exception as e:
        format_sql = ""
        unformattedSqlList.append(["sql format failed:%s" %(e)])

    return (format_sql, unformattedSqlList)

@login_required
def chk_sql_select(request):
    sql_item=""
    try:
        sqlErrorDict={}
        chk_errors = []
        sql = request.POST.get('sql','')
        sql_parse = sqlparse.parse(str(sql).strip())

        if len(sql_parse) > 1:
            sqlErrorDict={}
            sqlErrorDict['sql']=""
            sqlErrorDict['error']="一次只能查询一个 sql"
            chk_errors.append(sqlErrorDict)
            return (chk_errors)

        ispass = 1
        for sql_item in sql_parse:
            if sql_item.get_type() != "SELECT":
                if sql_item.get_type() == "UNKNOWN":
                    sqlstr=str(sql_item).strip().replace(" ", "")
                    if len(sqlstr) > 15:
                        if sqlstr[0:15].lower() == "showcreatetable" or sqlstr[0:13].lower() == "showindexfrom" or sqlstr[0:8].lower() == "describe" or sqlstr[0:4].lower() == "desc" or sqlstr[0:10].lower() == "showtables":
                            pass
                        else:
                            ispass = 0
                    elif len(sqlstr) > 13:
                        if sqlstr[0:13].lower() == "showindexfrom" or sqlstr[0:8].lower() == "describe" or sqlstr[0:4].lower() == "desc" or sqlstr[0:10].lower() == "showtables":
                            pass
                        else:
                            ispass = 0
                    elif len(sqlstr) > 10:
                        if sqlstr[0:8].lower() == "describe" or sqlstr[0:4].lower() == "desc" or sqlstr[0:10].lower() == "showtables":
                            pass
                        else:
                            ispass = 0
                    elif len(sqlstr) > 8:
                        if sqlstr[0:8].lower() == "describe" or sqlstr[0:4].lower() == "desc":
                            pass
                        else:
                            ispass = 0
                    elif len(sqlstr) > 4:
                        if sqlstr[0:4].lower() == "desc":
                            pass
                        else:
                            ispass = 0
                    if ispass == 0:
                        sqlErrorDict={}
                        sqlErrorDict['sql']=str(sql_item)
                        sqlErrorDict['error']="SQL must be in [ select / desc / describe / show index from / show create table / show tables]"
                        chk_errors.append(sqlErrorDict)                          
                else:
                    sqlErrorDict={}
                    sqlErrorDict['sql']=str(sql_item)
                    sqlErrorDict['error']="SQL must be in [ select / desc / describe / show index from / show create table / show tables]"
                    chk_errors.append(sqlErrorDict)
                    
    except Exception as e:
        sqlErrorDict={}
        sqlErrorDict['sql']=str(sql_item)
        sqlErrorDict['error']="sql format failed: %s" %(e)
        chk_errors.append(sqlErrorDict)

    return (chk_errors)

@login_required
def get_desc(request):
    try:
        sqlErrorDict={}
        sqlResultDict=[]

        desc_errors = []
        desc_result = []

        field_desc=[]

        sql = request.POST.get('sql','')
        sql_parse = sqlparse.parse(sql)
        
        sql_item=""
        field_desc=["id","select_type","table","type","possible_keys","key","key_len","ref","rows","Extra"]

        if not request.POST.get('databaseId',''):
            sqlErrorDict={}
            sqlErrorDict['sql']=""
            sqlErrorDict['error']="DB do not exists"
            desc_errors.append(sqlErrorDict)

            return (desc_errors,sqlResultDict,field_desc)

        sql = """select host,port,dbname
            from  sqltools_db_conninfo
            where dbid = %s and type = 'R';"""

        cursor = connection.cursor()
        param = [request.POST.get('databaseId')]
        cursor.execute(sql, param)
        db_connstr = dictFetchall(cursor)
        cursor.close()
        
        db_host = db_connstr[0]["host"]
        db_port = db_connstr[0]["port"]
        db_name = db_connstr[0]["dbname"]

        retno = None
        retmsg = None

        (retno, retmsg, db_conn) = getdbconnection(db_name, db_host, db_port, "0")
        if retno == -1:
            sqlErrorDict={}
            sqlErrorDict['sql']=str(sql_item)
            sqlErrorDict['error']="get desc failed: %s" %(retmsg)
            desc_errors.append(sqlErrorDict)
            return (desc_errors,sqlResultDict,field_desc)

        db_cur = db_conn.cursor()
        db_cur.connection.autocommit(0)

        sql_item = sql_parse[0]
        sql = "explain " + str(sql_item)
        db_cur.execute(sql)
        result_item = db_cur.fetchall()
        sqlResultDict = result_item

        db_conn.rollback()

        db_cur.close()
        db_conn.close()

    except Exception as e:
        sqlErrorDict={}
        sqlErrorDict['sql']=str(sql_item)
        sqlErrorDict['error']="get desc failed: %s" %(e)
        desc_errors.append(sqlErrorDict)
    return (desc_errors,sqlResultDict,field_desc)


@login_required
def do_execute(request, db_conn, db_name):
    try:
        returncount = 0

        __result = {}
        __result['exec_errors'] = []
        __result['sqlResultDict'] = []
        __result['field_desc'] = []

        result_item = []
        sqlErrorDict={}
        sqlResultDict=[]
        exec_errors = []
        field_desc=[]

        db_conn.autocommit(0)
        db_cur = db_conn.cursor()
        db_cur.connection.autocommit(0)

        sql_parse = sqlparse.parse(request.POST.get('sql',''))        
        sql_item=""
        sql_item = sql_parse[0]
        sql = str(sql_item)

        # 处理 sql 的 limit
        isExistsLimit = 0
        dosql= ""
        islimit = 0
        limit_begin = 0
        limit_end = 0
        idx = 0
        num = ""
        for item in sql_item:     
            if str(item).lower() == "limit":
                islimit = 1
                idx = idx + 1
                continue
            if islimit == 1 and str(item).strip() != ";":
                if str(item).strip() == "":
                    continue
                else:
                    num = str(item).strip().replace(" ", "")
            else:
                dosql = dosql + str(item)        

        if num != "":
            if len(num.split(",")) == 2:
                limit_begin = int(num.split(",")[0])
                limit_end = int(num.split(",")[1])
            else:
                limit_begin = 0
                limit_end = int(num.split(",")[0])

            if int(limit_end) > 100:
                limit_end = 100            
        else:
            limit_begin = 0
            limit_end = 100

        # 去掉结尾的 ; 
        if dosql[-1] == ";":
            dosql = dosql[:-1]

        if sql_item.get_type() == "SELECT":
            dosql = dosql + " limit " + str(limit_begin) + "," + str(limit_end)

        returncount = db_cur.execute(dosql)

        for desc in db_cur.description:
            field_desc.append(desc[0])

        rows = db_cur.fetchall()
        for row in rows:
            line = []
            for i in range(0, len(row)):
                if row[i] ==None:
                    line.append("NULL")
                else:
                    line.append(str(row[i]))
            result_item.append(line)

        # 处理敏感字段
        topFiled = None
        topFiledIndex = []
        retno = None
        retmsg = None
        (retno, retmsg, topFiled) = getTopField(request,db_name)

        if retno == -2: # 发生错误
            field_desc.append("error")
            sqlErrorDict={}
            sqlErrorDict['sql']=str(dosql)
            sqlErrorDict['error']=retmsg
            exec_errors.append(sqlErrorDict)
        
            __result['exec_errors'] = exec_errors
            __result['sqlResultDict'] = sqlResultDict
            __result['field_desc'] = field_desc

            return __result
        elif retno == -1:# 没有权限 
            field_desc.append("error")
            sqlErrorDict={}
            sqlErrorDict['sql']=str(dosql)
            sqlErrorDict['error']="没有该 db 访问权限"
            exec_errors.append(sqlErrorDict)
        
            __result['exec_errors'] = exec_errors
            __result['sqlResultDict'] = sqlResultDict
            __result['field_desc'] = field_desc

            return __result            
        elif retno == 0: # 限制访问敏感字段
            idx = 0
            for desc in field_desc:
                for col in topFiled:
                    if str(desc).lower() == str(col[0]).lower():
                        topFiledIndex.append(idx)
                idx = idx + 1
            if topFiledIndex:
                for rowindex in range(0, len(result_item)):
                    for colindex in range(0,len(result_item[rowindex]) - 1):
                        if colindex in topFiledIndex:
                            result_item[rowindex][colindex] = 'Top Secret'

        elif retno == 2: # 超级权限
            pass

        sqlResultDict = result_item

        db_conn.rollback()
        db_cur.close()

    except Exception as e:
        field_desc.append("error")
        sqlErrorDict={}
        sqlErrorDict['sql']=str(sql_item)
        sqlErrorDict['error']="execute failed: %s" %(e)
        exec_errors.append(sqlErrorDict)

    
    __result['exec_errors'] = exec_errors
    __result['sqlResultDict'] = sqlResultDict
    __result['field_desc'] = field_desc

    # log
    try:
        upload_cur = connection.cursor()
        sqlstr = """
            insert into sqltools_sqlqry_log(dbid, dbname, username, `sql`, returncount) 
                values(%s, %s, %s, %s, %s)
        """
        param = [request.POST.get('databaseId',''), db_name, request.user.username, str(sql_item), returncount ]
        upload_cur.execute(sqlstr, param)
        upload_cur.connection.commit()
        upload_cur.close()
    except Exception as e:
        upload_cur.close()

    return __result

#执行线程
class execThread(threading.Thread):
    __result = {}
    __result['exec_errors'] = []
    __result['sqlResultDict'] = []
    __result['field_desc'] = []
    
    def __init__(self, thread_id,request, db_conn, db_name):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.request=request
        self.db_conn = db_conn
        self.db_name = db_name

    def run(self):
        self.__result =  do_execute(self.request,self.db_conn, self.db_name)
    def getResult(self):
        return self.__result

#kill 数据库连接
def kill_dbconnection(db_conn_exe_id, db_conn_kill):
    try:
        cursor=db_conn_kill.cursor()
        kill = "kill %d " % db_conn_exe_id

        cursor.execute(kill)
        cursor.fetchall()
        cursor.close()
    except Exception as e:
        return -1
    
    return 0

def getTbName(request, sqlstr):
    try:
        filename = "/tmp/sql.%s" %(time.time())
        isget = 0
        tblist = []
        dblist = []
        dbtbinfo = [] # eg: db.tb
        retno = 0
        retmsg = 0


        sqlReviewFile=open(filename,'w+')
        sqlReviewFile.write(sqlstr)
        sqlReviewFile.close()
        (retno,tbinfo) = commands.getstatusoutput("./gettbinfo -d mysql -f %s" %(filename))        

        if retno != 0:
            return [], []
        else:
            tbinfolist = tbinfo.split("\n")
            for line in tbinfolist:
                line = line.strip()

                if line.strip() == "Tables:":
                    isget = 1
                    continue
                if line.strip() == "Columns:":
                    break

                if isget == 1:
                    if line.strip() != "":
                        '''
                            如果返回的表名里有 `  符号，就以 ` 符号为分隔
                            如果没有, 就以 .  为分隔  来查找  dbname
                        '''
                        if line.find("`") > -1:  # 以 ` 分隔
                            dbtbinfo = line.split("`")
                            if len(dbtbinfo) > 3: # eg.  `testdb`.`tb`
                                dblist.append(dbtbinfo[1])
                                tblist.append(dbtbinfo[3])
                            else:                 # eg. `tb`  不包含 db 信息
                                tblist.append(dbtbinfo[1])
                        else:
                            if line.find(".") > -1:  # 以 . 分隔
                                dbtbinfo = line.split(".")
                                dblist.append(dbtbinfo[0])
                                tblist.append(dbtbinfo[1])
                            else:                    # 不包含 db 信息
                                tblist.append(line.strip().replace("`", ""))
        (retno,retmsg) = commands.getstatusoutput("rm %s" %(filename))
    except Exception as e:
        tbinfo = []

    return dblist, tblist  

# retno: 0: 有权限; -1: 无权限
# retmsg: ok / errmsg
def check_table_priv(request, dbname):
    retno = 0
    retmsg = "ok"
    tblist = []
    dblist = []
    grants_dblist = []

    try:
        if request.user.is_superuser:
            return (0, "ok", tblist)

        cursor = connection.cursor()

        sql = """
                select dbname from sqltools_user_db where username = %s and status = 1
            """
        param = [request.user.username]
        cursor.execute(sql, param)
        rows = cursor.fetchall() 
        for row in rows:
            grants_dblist.append(str(row[0]))

        sql_parse = sqlparse.parse(request.POST.get('sql',''))        
        sql_item=""
        sql_item = sql_parse[0]
        sql = str(sql_item)

        dblist, tblist = getTbName(request, sql)
        dblist.append(str(dbname))

        strwhere = '(' + ','.join(['"'+ item + '"' for item in dblist]) + ')'
        # 检查 db 权限
        for item in dblist:
            if str(item) not in grants_dblist:
                return (-1, "no privileges on ", item)

        sql = "select tablename from sqltools_top_fields where dbname in " + strwhere
        sql = sql +" and dbname not in (select dbname from sqltools_user_db \
                where status = 1 and issupper = 1 and username = %s)"
        param = [request.user.username]
        cursor.execute(sql, param)
        rows = cursor.fetchall()
        
        for tbitem in rows:
            if str(tbitem[0]) in tblist:
                retno = -1
                retmsg = "no privileges"
                tblist = []
                tblist.append(str(tbitem[0]))
                break

        cursor.close()
    except Exception as e:
        retno = -1
        retmsg = "error: %s" %(e)
        cursor.close()
        print retmsg

    return (retno, retmsg, tblist)


# 限敏感字段, 对于有特殊 db 权限有用户, 可以查询敏感数据
# return: 
# retno: -1: 没有 db 访问权限; 0: 正常; 1: 超级权限
# retmsg: 返回信息
# fileds: 敏感字段列表 
# !!!!!!!!!!!!!!!!!!!!!! 暂时敏感控制只到 表级别, 字段级的判断不准,                         !!!!!!!!!!!!!!!!!!!!!!
# !!!!!!!!!!!!!!!!!!!!!! 通过配置 sqltools_top_fields.fieldname = '' 来忽略字段级的判断    !!!!!!!!!!!!!!!!!!!!!!
def getTopField(request,dbname):
    try:
        issupper = "0"
        param = []
        if request.user.is_superuser:
            sql = """
                    select id,  Upload_DBName, '1' as issupper from  
                        release_dbconfig 
                    """        
        else:
            sql = """
                select dbid as id, dbname as Upload_DBName, issupper from  
                    sqltools_user_db 
                    where username = %s and status = 1
                """
            param = [request.user.username]

        cursor = connection.cursor()
        
        cursor.execute(sql, param)
        rows = dictFetchall(cursor)
        
        if len(rows) > 0:
            issupper = rows[0]["issupper"]
        else:
            cursor.close()
            return (-1, 'ok', [])

        if issupper == '1':
            cursor.close()
            return(1, 'ok', [])

        sql = """
                select fieldname from sqltools_top_fields where dbname = %s
            """
        param = [dbname]
        cursor.execute(sql, param)
        rows = cursor.fetchall()    
        cursor.close()
        return (0, 'ok', rows)
    except Exception as e:
        return(-2, e, [])


config=ConfigParser.ConfigParser()
cfgfile=open('/var/www/site/mycitsm/mycitsm/login.cnf','r')

config.readfp(cfgfile)

product_user=config.get('mysqllogin','product_user').encode('utf-8')
product_passwd=endecrypt.endeCrypt.decrypt(config.get('mysqllogin','product_passwd').encode('utf-8'))
# 取连接串, readonly = 0 时, 从 slave 取
# 返回
# retno: 0: 正常, -1: 出错
# retmsg 
# dbconnection
def getdbconnection(dbname, mhost, mport, readonly):
    try:
        # upload_cur = connection.cursor()
        # if readonly == 0:
        #     sql = """
        #             select b.host, b.port, a.dbuser,
        #               cast(aes_decrypt(`password`,'yo9lf9UrsypjnriseLnzvqghdmpbky') as char(50)) as pwd
        #             from db_conninfo a 
        #             left join sqltools_db_conninfo b on a.dbname = b.dbname and envt = "生产" and a.dbuser = b.dbuser and type = 'W'
        #             where b.dbname = %s 
        #         """
        # else:
        #     sql = """
        #             select b.host, b.port, a.dbuser,
        #               cast(aes_decrypt(`password`,'yo9lf9UrsypjnriseLnzvqghdmpbky') as char(50)) as pwd
        #             from db_conninfo a 
        #             left join sqltools_db_conninfo b on a.dbname = b.dbname and envt = "生产" and a.dbuser = b.dbuser and type = 'R'
        #             where b.dbname = %s 
        #         """
        # param = [dbname]
        # upload_cur.execute(sql, param)
        # dbconn = dictfetchall(upload_cur)
        # upload_cur.close()

        # con=MySQLdb.connect(user=dbconn[0]["dbuser"], db=dbname,passwd=dbconn[0]["pwd"],
        #     host=dbconn[0]["host"], port=dbconn[0]["port"])

        con=MySQLdb.connect(user=product_user, db=dbname,passwd=product_passwd,
            host=mhost, port=mport, charset="utf8")
        return (0, "ok", con)
    except Exception as e:
        return (-1, e, None)

