from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from extensions import db
from models import User, EmailOTP, PasswordReset
from auth.utils import create_email_otp, send_otp_email, hash_token, create_reset_token, send_reset_email
from extensions import limiter

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")

        existing = User.query.filter(
            (func.lower(User.username) == username.lower()) |
            (func.lower(User.email) == email.lower())
        ).first()

        if existing:
            flash("Username or email already exists.", "danger")
            return render_template("signup.html")

        user = User(username=username, email=email, is_verified=False)
        user.set_password(password)
        db.session.add(user)

        try:
            db.session.flush()  # get user.id without committing yet
            otp = create_email_otp(email=email, purpose="signup", user_id=user.id)
            send_otp_email(email, otp, "signup")
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not send OTP email. Please try again.", "danger")
            return render_template("signup.html")

        session["pending_signup_email"] = email
        # flash("OTP sent to your email. Verify to complete signup.", "info")
        flash("OTP generation is currently disabled. Account created for testing.", "info")
        return redirect(url_for("auth.verify_signup_otp"))

    return render_template("signup.html")

@auth_bp.route("/verify-signup-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def verify_signup_otp():
    email = session.get("pending_signup_email")
    if not email:
        return redirect(url_for("auth.signup"))
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        record = EmailOTP.query.filter_by(email=email, purpose="signup").order_by(EmailOTP.created_at.desc()).first()
        if not record or record.expires_at < datetime.utcnow() or record.verified_at is not None:
            flash("OTP expired or invalid.", "danger")
            return render_template("verify_otp.html", purpose="signup")
        if record.otp_hash != hash_token(otp):
            record.attempts += 1
            db.session.commit()
            flash("Incorrect OTP.", "danger")
            return render_template("verify_otp.html", purpose="signup")
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            record.verified_at = datetime.utcnow()
            db.session.commit()
            session.pop("pending_signup_email", None)
            flash("Signup verified. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("verify_otp.html", purpose="signup")

@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (func.lower(User.username) == identifier.lower()) |
            (func.lower(User.email) == identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            flash("Invalid credentials.", "danger")
            return render_template("login.html")

        if not user.is_verified:
            flash("Please verify your account first.", "danger")
            return render_template("login.html")

        try:
            otp = create_email_otp(email=user.email, purpose="login", user_id=user.id)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not create login OTP. Please try again.", "danger")
            return render_template("login.html")

        session["pending_login_email"] = user.email
        flash("OTP generated. Enter the code to login.", "info")
        return redirect(url_for("auth.verify_login_otp"))

    return render_template("login.html")

@auth_bp.route("/verify-login-otp", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def verify_login_otp():
    email = session.get("pending_login_email")
    if not email:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        otp = request.form.get("otp", "").strip()
        record = EmailOTP.query.filter_by(email=email, purpose="login").order_by(EmailOTP.created_at.desc()).first()
        if not record or record.expires_at < datetime.utcnow() or record.verified_at is not None:
            flash("OTP expired or invalid.", "danger")
            return render_template("verify_otp.html", purpose="login")
        if record.otp_hash != hash_token(otp):
            record.attempts += 1
            db.session.commit()
            flash("Incorrect OTP.", "danger")
            return render_template("verify_otp.html", purpose="login")
        user = User.query.filter_by(email=email).first()
        if user:
            record.verified_at = datetime.utcnow()
            db.session.commit()
            login_user(user)
            session.pop("pending_login_email", None)
            flash("Logged in successfully.", "success")
            return redirect(url_for("home"))
    return render_template("verify_otp.html", purpose="login")

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = create_reset_token(user.id)
            send_reset_email(user.email, token)
        flash("If the email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot_password.html")

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def reset_password(token):
    token_hash = hash_token(token)
    record = PasswordReset.query.filter_by(token_hash=token_hash).order_by(PasswordReset.created_at.desc()).first()
    if not record or record.used_at is not None or record.expires_at < datetime.utcnow():
        flash("Invalid or expired reset link.", "danger")
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not password or password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")
        user = db.session.get(User, record.user_id)
        user.set_password(password)
        record.used_at = datetime.utcnow()
        db.session.commit()
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("home"))
