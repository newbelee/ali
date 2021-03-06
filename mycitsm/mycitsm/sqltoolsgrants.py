# -*- coding: utf-8 -*- 
from commonconfig import *


reload(sys)
sys.setdefaultencoding('UTF-8')

@login_required
def sqltoolsgrants(request):
    errors=[]
    # if not request.user.is_superuser:
    #     errors.append('Sorry,only superusers are allowed to do this!')
    if errors:
        return render_to_response('error.html',{
            'errors':errors,
            'user':request.user.username,
            'title':"Error"
        })

    upload_cur = connection.cursor()
    param = []
    if not request.user.is_superuser:
        sql = """ 
                select id, dbname, username, email, case when issupper = 1 then 'Y' else 'N' end as issupper,
                case when status = 0 then '未审批' when status = 1 then '正常' when status = 2 then '未通过' end as status
                from sqltools_user_db where username = %s
                order by status
            """
        param = [request.user.username]
    elif request.user.is_superuser:
        sql = """ 
                select id, dbname, username, email, case when issupper = 1 then 'Y' else 'N' end as issupper,
                case when status = 0 then '未审批' when status = 1 then '正常' when status = 2 then '未通过' end as status
                from sqltools_user_db
                order by status
            """
    
    upload_cur.execute(sql, param)
    rows = dictFetchall(upload_cur)
    upload_cur.close()

    context = {
        'title':'用户查询权限管理',
        'is_superuser':request.user.is_superuser,
        'rows':rows
    }

    return render(request, 'sqltoolsgrants.html',context)

@login_required
def sqltoolsgrants_edit(request):
    errors=[]

    if request.method == 'GET':
        username = request.GET.get("username", "")
        dbname = request.GET.get("dbname", "")
        issupper = request.GET.get("issupper", "")
        status = request.GET.get("status", "未审批")
        if issupper == "Y":
            issupper = 1
        else:
            issupper = 0

        if status == "未审批":
            status = 0
        elif status == "正常":
            status = 1
        elif status == "未通过":
            status = 2
        else:
            status = 0

        statuslist = []
        statuslist.append({"status":0, "statusname":"未审批"})
        statuslist.append({"status":1, "statusname":"正常"})
        statuslist.append({"status":2, "statusname":"未通过"})

        context = {
            'title':'用户查询权限管理',
            'username':username,
            'dbname':dbname,
            'isadd':0,
            'issupper':issupper,
            'status':str(status),
            'statuslist':statuslist
        }
        return render(request, 'sqltoolsgrants_edit.html',context)
    if request.method == 'POST':
        if not request.user.is_superuser:
            errors.append('Sorry,only superusers are allowed to do this!')
        if errors:
            return render_to_response('error.html',{
                'errors':errors,
                'user':request.user.username,
                'title':"Error"
            })

        username = request.POST.get("username", "")
        dbname = request.POST.get("dbname", "")
        issupper = request.POST.get("issupper", "")
        status = request.POST.get("status", "0")

        sql = """
                update sqltools_user_db set issupper = %s, status = %s
                where username = %s and dbname = %s
            """
        param=[issupper, status, username, dbname]
        upload_cur = connection.cursor()
        upload_cur.execute(sql, param)
        upload_cur.connection.commit()
        upload_cur.close()

        context = {
            'title':'用户查询权限管理',
            'username':username,
            'dbname':dbname,
            'issupper':issupper
        }
        errors.append("操作成功")

        return render_to_response('error.html',{
            'errors':errors,
            'user':request.user.username,
            'title':"提示信息"
        })

# 申请 db 查询权限
@login_required
def sqltoolsgrants_add(request):
    errors=[]
    maxSqlAmount = 10
    envId = 4
    cursor = connection.cursor()

    #取出可用数据库名和ID
    sql = """
            select id, Upload_DBName from  
                release_dbconfig
                where  Upload_DBName not in (
                    select dbname from sqltools_user_db
                    where username = %s and status = 1
                )  and envId = 4
            """     
    param = [request.user.username]
    cursor.execute(sql, param)
    dblist = dictFetchall(cursor)

    cursor.close()
                
    if request.method == "GET":        
        context = {
            'title':'申请 db 查询权限',
            'username':request.user.username,
            'dblist':dblist
        }

        return render(request, 'sqltoolsgrants_add.html',context)

    if request.method == 'POST':

        username = request.user.username
        email = request.user.email
        databaselist = request.POST.getlist("databaseId", "")

        databaselist_where =  ','.join(['"'+ item + '"' for item in databaselist]) 

        try:
            sql = """
                insert into sqltools_user_db(dbid, dbname, username, email, issupper, status)
                select id, Upload_DBName, '%s', '%s', 0, 0 
                from  release_dbconfig
                where id in (%s) and envId = 4;
            """ %(username, email, databaselist_where)

            upload_cur = connection.cursor()
            upload_cur.connection.autocommit(True)
            upload_cur.execute(sql)
            upload_cur.connection.commit()
            upload_cur.close()

            errors.append("操作成功")

        except Exception as e:
            upload_cur.close()
            errors.append("发生错误：%s" %(e))

        return render_to_response('error.html',{
            'errors':errors,
            'user':request.user.username,
            'title':"提示信息"
        })



@login_required
def sqltoolsgrants_del(request):
    errors=[]
    if request.method == 'POST':
        if not request.user.is_superuser:
            errors.append('Sorry,only superusers are allowed to do this!')
        if errors:
            return render_to_response('error.html',{
                'errors':errors,
                'user':request.user.username,
                'title':"Error"
            })
        
        id = request.POST.get("id", "")
        retno = 0
        retmsg = ""
        try:
            sql = """
                    delete from sqltools_user_db
                    where id = %s
                """
            param=[id]
            upload_cur = connection.cursor()
            upload_cur.execute(sql, param)
            upload_cur.connection.commit()
            upload_cur.close()
            retno = 0
            retmsg = "操作成功"
        except Exception as e:
            retno = -1
            retmsg = "操作失败： %s" %(e)

        # message = {
        #         'returnno':retno, 
        #         'content':retmsg
        #    }

        response = HttpResponse()
        response['Content-Type'] = "application/json"
        response.write(json.dumps(retmsg))

        return response






