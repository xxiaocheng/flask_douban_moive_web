import json
import threading

from app.email import (send_change_email_email, send_confirm_email,
                       send_reset_password_email)
from app.extensions import redis_store
from app.helpers.utils import generate_email_confirm_token
from app.settings import Operations
from flask import current_app

key = 'task:email'

def _send_async_email(app,task):

    task_str=str(task[1],encoding='utf-8')
    task_dict = eval(task_str)
    to, cate, username,timestamp = task_dict.values()
    with app.app_context():
        if cate == Operations.CHANGE_EMAIL:
            token = generate_email_confirm_token(
                username=username, operation=Operations.CHANGE_EMAIL)
            status_code = send_change_email_email(token, to, username)

        elif cate == Operations.CONFIRM:
            token = generate_email_confirm_token(
                username=username, operation=Operations.CONFIRM, email=to)
            status_code = send_confirm_email(token, to, username)

        elif cate == Operations.RESET_PASSWORD:
            token = generate_email_confirm_token(
                username=username, operation=Operations.RESET_PASSWORD)
            status_code = send_reset_password_email(token, to, username)
    print(cate)
    if status_code != 202:
        redis_store.rpush(key, json.dumps(task_dict))

def handle_email():
    app=current_app._get_current_object()
    while True:
        task = redis_store.blpop(key)
        print(task[1])
        t=threading.Thread(target=_send_async_email,args=(app,task))
        t.start()

    
        
        

        


