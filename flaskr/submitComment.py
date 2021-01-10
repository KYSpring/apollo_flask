from flaskr.dataAccess import insert_comment

from flask import (
    Blueprint, flash, g, redirect, request, session, url_for
)

bp = Blueprint('submitComment', __name__, url_prefix='/privatelending')

@bp.route('/submitComment', methods=(['POST']))
def submit_comment():
    if request.method=='POST' and request.form['comment_data']:
        print(request.form)
        comment_data = request.form['comment_data']
        # print('66666666',comment_data)
        try:
            insert_comment(comment_data)
            res = {
                'state': True,
                'info': '提交数据库成功'
            }
        except Exception:
            print(Exception)
            res = {
                'state': False,
                'info': '提交数据库失败'
            }
    else:
        res = {
            'state': False,
            'info': '请使用Post请求'
        }
    return res
