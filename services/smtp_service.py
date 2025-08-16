import smtplib
import random
from email.mime.text import MIMEText

from keys.gitignorfile import SMTP_CONFIG

# SMTP
SMTP_HOST = SMTP_CONFIG['host']
SMTP_PORT = SMTP_CONFIG["port"]
SMTP_USER = SMTP_CONFIG['user']
SMTP_PASS = SMTP_CONFIG['password']

def send_otp_email(to_email, otp_code):
    subject = "YOUR OTP CODE HERE"
    body = f"Your code: {otp_code}"
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())

