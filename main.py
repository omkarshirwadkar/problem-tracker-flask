from flask import Flask, render_template, redirect, url_for, request
from flask_login import current_user
from config import Config
from extensions import db, migrate, login_manager, mail, csrf, limiter
from auth.routes import auth_bp
from problems.routes import problems_bp
from community.routes import community_bp
from problems.sync import incremental_sync_from_current_size
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

scheduler = BackgroundScheduler(timezone=ZoneInfo("Asia/Kolkata"))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.login_view = "auth.login"

    app.register_blueprint(auth_bp)
    app.register_blueprint(problems_bp)
    app.register_blueprint(community_bp)

    @app.before_request
    def restrict_guest_access():
        public_endpoints = {
            "home", "auth.login", "auth.signup",
            "auth.verify_signup_otp", "auth.verify_login_otp",
            "auth.forgot_password", "auth.reset_password",
            "static", "problems.health"
        }
        if current_user.is_authenticated:
            return
        endpoint = request.endpoint
        if endpoint and endpoint not in public_endpoints:
            return redirect(url_for("home"))

    @app.route("/home")
    def home():
        return render_template("home.html")

    @app.route("/")
    def index():
        return redirect(url_for("home"))

    return app

def start_scheduler(app):
    if scheduler.running:
        return

    def job():
        with app.app_context():
            incremental_sync_from_current_size()

    scheduler.add_job(
        job,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=ZoneInfo("Asia/Kolkata")),
        id="weekly_problem_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

app = create_app()

with app.app_context():
    from models import User, EmailOTP, PasswordReset, Problem, UserProblem, Category, ProblemCategory
    db.create_all()
    try:
        start_scheduler(app)
    except Exception:
        pass

if __name__ == "__main__":
    app.run(debug=True)
