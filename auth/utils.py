from datetime import datetime, timedelta
import secrets
import hashlib
from flask import url_for
from flask_mail import Message
from extensions import db, mail
from models import EmailOTP, PasswordReset

def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def generate_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"

def create_email_otp(email: str, purpose: str, user_id=None, minutes: int = 10) -> str:
    otp = generate_otp()
    record = EmailOTP(
        email=email,
        user_id=user_id,
        otp_hash=hash_token(otp),
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=minutes),
    )
    db.session.add(record)
    db.session.flush()
    return otp

def send_otp_email(email: str, otp: str, purpose: str):
    # msg = Message(
    #     subject=f"{purpose.title()} OTP Verification",
    #     recipients=[email],
    #     body=f"Your OTP for {purpose} is: {otp}\nIt expires in 10 minutes."
    # )
    # mail.send(msg)
    return

def create_reset_token(user_id: int, minutes: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    record = PasswordReset(
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(minutes=minutes),
    )
    db.session.add(record)
    db.session.commit()
    return token

def send_reset_email(email: str, token: str):
    # reset_link = url_for("auth.reset_password", token=token, _external=True)
    # msg = Message(
    #     subject="Password Reset",
    #     recipients=[email],
    #     body=f"Use this link to reset your password:\n{reset_link}\nThis link expires in 30 minutes."
    # )
    # mail.send(msg)
    return