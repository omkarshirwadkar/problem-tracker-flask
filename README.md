# Flask Problem Tracker

A Flask + SQLAlchemy backend for:
- signup/login with OTP verification
- forgot password by email link
- solved problem tracking with categories
- random problem selection by category
- LeetCode problem database sync
- weekly incremental sync job

## Setup

1. Create a virtualenv.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in values.
4. Initialize database:
   ```bash
   flask --app main.py db init
   flask --app main.py db migrate -m "init"
   flask --app main.py db upgrade
   ```
5. Run:
   ```bash
   python run.py
   ```

## Notes
- Default DB is SQLite.
- Set `DATABASE_URL` to MySQL if needed.
- Use app-specific password for Gmail SMTP.
- `/admin/load-problems-once` and `/admin/sync-problems` are included for convenience; secure them before production use.
