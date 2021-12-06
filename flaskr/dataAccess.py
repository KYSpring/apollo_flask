import pymysql

def select_db(select_sql):
    """查询"""
    # 建立数据库连接
    db = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="KYSpring",
        passwd="KYSpring",
        db="privatelending"
    )
    # 通过 cursor() 创建游标对象，并让查询结果以字典格式输出
    cur = db.cursor(cursor=pymysql.cursors.DictCursor)
    # 使用 execute() 执行sql
    cur.execute(select_sql)
    # 使用 fetchall() 获取所有查询结果
    data = cur.fetchall()
    # 关闭游标
    cur.close()
    # 关闭数据库连接
    db.close()
    return data

def insert_comment(comment_data,contact,workplace):
    insertSQL = "INSERT INTO `privatelending`.privatelendingcomment (content,contact,workplace) VALUES('"+comment_data+"','"+contact+"','"+workplace+"');"
    # print(insertSQL)
    # 建立数据库连接
    db = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="KYSpring",
        passwd="KYSpring",
        db="privatelending"
    )
    try:
        # 通过 cursor() 创建游标对象，并让查询结果以字典格式输出
        cur = db.cursor(cursor=pymysql.cursors.DictCursor)
        # 使用 execute() 执行sql
        cur.execute(insertSQL)
        # 使用 fetchall() 获取所有查询结果
        db.commit()
        res = 'success'
    except Exception:
        # print('插入数据异常：'+Exception)
        db.rollback()
        res = '插入数据异常：'+Exception
    finally:
        # 关闭游标
        cur.close()
        # 关闭数据库连接
        db.close()
    return res

# select_sql = 'SELECT * FROM privatelendingcomment'
# print(insert_comment('222'))