from dotenv import load_dotenv
load_dotenv()

import smtplib
import random
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

print(f"DEBUG: EMAIL_ADDRESS={'SET' if EMAIL_ADDRESS else 'MISSING'}")
print(f"DEBUG: EMAIL_APP_PASSWORD={'SET (len=' + str(len(EMAIL_APP_PASSWORD)) + ')' if EMAIL_APP_PASSWORD else 'MISSING'}")

# Simple in-memory OTP store: {email: {"otp": "123456", "expires": datetime}}
otp_store = {}


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def send_otp_email(to_email: str) -> str:
    otp = generate_otp()
    otp_store[to_email] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=10),
    }

    msg = MIMEText(f"Your SmartEstate AI verification code is: {otp}\nThis code expires in 10 minutes.")
    msg["Subject"] = "Your SmartEstate AI verification code"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.ehlo()
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)

    return otp


def verify_otp(email: str, otp: str) -> bool:
    record = otp_store.get(email)
    if not record:
        return False
    if datetime.utcnow() > record["expires"]:
        del otp_store[email]
        return False
    if record["otp"] != otp:
        return False
    del otp_store[email]
    return True