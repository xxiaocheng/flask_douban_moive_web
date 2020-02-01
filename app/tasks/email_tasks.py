import json
import threading

from app.email import (send_change_email_email, send_confirm_email,
                       send_reset_password_email)
from app.extensions import redis_store,scheduler
from app.helpers.utils import generate_email_confirm_token
from app.settings import Operations

key = 'task:email'

def _send_async_email(task):

    task_str=str(task[1],encoding='utf-8')
    task_dict = eval(task_str)
    to, cate, username,timestamp = task_dict.values()
    app=redis_store.app
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
    # if status_code != 202:
    #     redis_store.rpush(key, json.dumps(task_dict))


def handle_email():
    if redis_store.llen(key):
        task = redis_store.blpop(key)
        t=threading.Thread(target=_send_async_email,args=(task,))
        t.start()
    