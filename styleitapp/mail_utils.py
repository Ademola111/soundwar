from datetime import datetime, timedelta, timezone
from flask import current_app
from flask_mail import Message
from styleitapp import mail
from styleitapp.models import Designer, Customer
from styleitapp.mytoken import generate_password_reset_token

"""email alert for activation of account"""
def send_email(to, subject, template):
    
    msg = Message(
        subject, 
        recipients=[to], 
        html=template, 
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        )
    mail.send(msg)

"""email alert for every action on the web"""
def send_email_alert(subject, body, recipients):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)


"""
send reset email for users who forgot their password
"""
def send_password_reset_email(user):
    token = generate_password_reset_token(user.desi_email)
    reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password/{token}"
    subject = "Password Reset Request"
    body = f"Hi {user.desi_fname},\n\n You requested a password reset. Click the link below to reset your password:\n\n{reset_url}\n\n If you did not request this, please ignore this email.\n\n Best regards,\n Styleit Africa Team"
    send_email_alert(subject, body, [user.desi_email])

def send_customer_password_reset_email(user):
    token = generate_password_reset_token(user.cust_email)
    reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password/{token}"
    subject = "Password Reset Request"
    body = f"Hi {user.cust_fname},\n\n You requested a password reset. Click the link below to reset your password:\n\n{reset_url}\n\n If you did not request this, please ignore this email.\n\n Best regards,\n Styleit Africa Team"
    send_email_alert(subject, body, [user.cust_email])

def send_admin_password_reset_email(user):
    token = generate_password_reset_token(user.admin_email)
    reset_url = f"{current_app.config['FRONTEND_URL']}/admin/reset-password/{token}"
    subject = "Password Reset Request"
    body = f"Hi {user.admin_fname},\n\n You requested a password reset. Click the link below to reset your password:\n\n{reset_url}\n\n If you did not request this, please ignore this email.\n\n Best regards,\n Styleit Africa Team"
    send_email_alert(subject, body, [user.admin_email])

def send_superadmin_password_reset_email(user):
    token = generate_password_reset_token(user.spadmin_email)
    reset_url = f"{current_app.config['FRONTEND_URL']}/admin/reset-password/{token}"
    subject = "Password Reset Request"
    body = f"Hi {user.spadmin_fname},\n\n You requested a password reset. Click the link below to reset your password:\n\n{reset_url}\n\n If you did not request this, please ignore this email.\n\n Best regards,\n Styleit Africa Team"
    send_email_alert(subject, body, [user.spadmin_email])