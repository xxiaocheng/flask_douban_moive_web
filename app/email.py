import os
from flask import current_app
from sendgrid.helpers.mail import Email,Content,Mail
from sendgrid import SendGridAPIClient
from flask import render_template
from app.extensions import redis_store


def send_email(subject,to,html_body):
    """@param subject: 邮件主题
    @param to: 收件人邮箱地址
    @param body :邮件主体部分 
    @return ``response``
    """
    sg=SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
    from_email=Email(current_app.config['EMAIL_SENDER'])
    to_email=Email(to)
    html_content=Content('text/html',html_body)
    mail=Mail(from_email,subject,to_email,content=html_content)
    response=sg.client.mail.send.post(request_body=mail.get())
    return response


def send_confirm_email(token, to,username):
    url_to=current_app.config['WEB_BASE_URL']+'/activate?token='+token
    response= send_email(subject='确认邮箱', to=to , html_body=render_template('emails/confirm.html', username=username, url_to=url_to))
    return response.status_code


def send_reset_password_email(token,to,username):
    url_to=current_app.config['WEB_BASE_URL']+'/change-password?token='+token
    response=send_email(subject='请更改密码', to=to, html_body=render_template('emails/reset_password.html', username=username, url_to=url_to))
    return response.status_code

def send_change_email_email(token, to,username):
    url_to=current_app.config['WEB_BASE_URL']+'/change-email?token='+token
    response=send_email(subject='更改绑定邮箱', to=to, html_body=render_template('emails/change_email.html', username=username, url_to=url_to))
    return response.status_code


