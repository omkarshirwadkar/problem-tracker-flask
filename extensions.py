from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()

def rate_limit_key():
    try:
        if current_user.is_authenticated:
            return f"user:{current_user.get_id()}"
    except Exception:
        pass
    return get_remote_address()

limiter = Limiter(key_func=rate_limit_key)