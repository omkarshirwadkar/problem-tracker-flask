# Flask Problem Tracker

A Flask-based problem tracking and revision platform for competitive programming.

Users can:

- sign up and log in with OTP-based verification
- track solved problems
- categorize solved problems with custom tags
- search, edit, delete, and clear solved problems
- solve random problems from their solved list by category
- browse other users and view their solved problems
- keep a local master database of LeetCode problems synced from an external API

This project is built as a monolithic Flask application with a normalized SQL database and a background sync workflow.

---

## Table of contents

- [Features](#features)
- [How the system works](#how-the-system-works)
- [Architecture](#architecture)
- [Database design](#database-design)
- [Routes](#routes)
- [Security](#security)
- [Trade-offs and design choices](#trade-offs-and-design-choices)
- [Local setup](#local-setup)
- [Deployment notes](#deployment-notes)
- [Environment variables](#environment-variables)
- [Project structure](#project-structure)

---

## Features

### Authentication
- Signup with username, email, password, and confirm password
- OTP-based signup verification
- Login with username/email + password
- OTP-based login verification
- Forgot-password flow using email reset link
- Logout

### Problem tracking
- Import LeetCode problems into a local database
- Add solved problems by problem number
- Add one or more custom categories to each solved problem
- Leave a problem uncategorized if no category is selected
- Search solved problems by title, number, or category
- Edit tags for a solved problem
- Delete a single solved problem
- Clear all solved problems
- Clear all categories

### Revision workflow
- Pick one or more categories and get a random solved problem from each
- If no category is selected, get a random solved problem from the full solved list

### Community / social view
- View other registered users
- Open a user profile and see their solved problem list

### Admin / maintenance
- One-time bulk load of LeetCode problems from the external API
- Weekly incremental problem sync job
- Protected admin sync endpoints

---

## How the system works

### 1. New user flow
A visitor lands on `/home`.

Guests can only access public pages such as:
- `/home`
- `/signup`
- `/login`
- OTP verification pages
- forgot/reset password pages

They cannot access protected pages like:
- `/add-problems`
- `/solve-problems`
- `/manage-problems`
- `/users`

### 2. Signup flow
1. User enters username, email, password, and confirm password.
2. The backend checks uniqueness for username and email.
3. A `User` row is created.
4. An OTP record is created.
5. In the current deployment setup, OTP delivery can be disabled or replaced with a static development code.
6. The user verifies the OTP.
7. The account becomes active and verified.

### 3. Login flow
1. User enters username/email and password.
2. Credentials are checked.
3. A login OTP record is created.
4. The user verifies the OTP.
5. Session login begins through Flask-Login.

### 4. Forgot password flow
1. User submits email.
2. If the user exists, a password reset token is generated.
3. A reset link is sent by email.
4. User sets a new password.

### 5. Problem ingestion flow
There are two ways the LeetCode problem database is populated:

- **One-time bulk load** from `https://leetcode-api-pied.vercel.app/problems`
- **Incremental weekly sync** that starts from the current max local problem ID and queries the next IDs until failure

This keeps the local problem database searchable and fast.

### 6. Add solved problem flow
1. User enters a problem number.
2. The backend looks up the problem in the local `problems` table.
3. The app shows the problem name and link.
4. The user confirms the action and selects categories or adds a custom category.
5. The solved problem is stored in `user_problems`.
6. The selected categories are linked through `problem_categories`.

### 7. Solve by category flow
1. User selects one or more categories.
2. The backend returns one random solved problem per category.
3. If no category is selected, one random solved problem is returned from all solved problems.

### 8. Manage solved problems flow
The user can:
- search solved problems
- edit tags
- delete a single solved problem
- clear the full solved list
- clear all categories

### 9. Community flow
Registered users can browse other users and view their solved problem lists.

---

## Architecture

This project uses a layered monolithic architecture.

### Presentation layer
HTML templates rendered by Flask:
- `home.html`
- `login.html`
- `signup.html`
- `verify_otp.html`
- `forgot_password.html`
- `reset_password.html`
- `add_problems.html`
- `manage_problems.html`
- `edit_solved_problem.html`
- `solve_problems.html`
- `users_list.html`
- `user_profile.html`

### Application layer
Flask routes handle:
- auth
- authorization
- solved-problem management
- category management
- random problem selection
- admin sync behavior
- community browsing

### Data layer
SQLAlchemy models store:
- users
- OTPs
- password reset tokens
- master problems
- solved problems
- categories
- problem-category mappings

### Background job layer
A scheduled job can sync new problems every Sunday at 10:00 AM IST.

---

## Database design

### `users`
Stores user accounts.

Fields:
- `id`
- `username`
- `email`
- `password_hash`
- `is_verified`
- `is_admin`
- `created_at`

### `email_otps`
Stores OTP records for signup and login.

Fields:
- `id`
- `email`
- `user_id`
- `otp_hash`
- `purpose`
- `expires_at`
- `verified_at`
- `attempts`
- `created_at`

### `password_resets`
Stores password reset token hashes.

Fields:
- `id`
- `user_id`
- `token_hash`
- `expires_at`
- `used_at`
- `created_at`

### `problems`
Stores the master problem catalog.

Fields:
- `id`
- `leetcode_problem_id`
- `title`
- `link`
- `created_at`

### `user_problems`
Represents a user having solved a problem.

Fields:
- `id`
- `user_id`
- `problem_id`
- `created_at`

This is the timestamp you can use to show when a problem was added to the solved list.

### `categories`
Stores user-defined categories.

Fields:
- `id`
- `user_id`
- `name`
- `created_at`

### `problem_categories`
Many-to-many join table between solved problems and categories.

Fields:
- `id`
- `user_problem_id`
- `category_id`

---

## Routes

## Public routes

| Route | Method | Purpose |
|---|---:|---|
| `/home` | GET | Public landing page |
| `/` | GET | Redirects to `/home` |
| `/signup` | GET, POST | Register a user |
| `/verify-signup-otp` | GET, POST | Verify signup OTP |
| `/login` | GET, POST | Log in a user |
| `/verify-login-otp` | GET, POST | Verify login OTP |
| `/forgot-password` | GET, POST | Start password reset |
| `/reset-password/<token>` | GET, POST | Set a new password |
| `/logout` | GET | Log out current user |

## Protected routes

| Route | Method | Purpose |
|---|---:|---|
| `/add-problems` | GET, POST | Add a solved problem |
| `/solve-problems` | GET, POST | Get random solved problems by category |
| `/manage-problems` | GET | Search, edit, delete solved problems |
| `/edit-solved-problem/<id>` | GET, POST | Edit tags for one solved problem |
| `/delete-solved-problem/<id>` | POST | Delete one solved problem |
| `/clear-solved-problems` | POST | Clear solved problem list |
| `/clear-all-categories` | POST | Clear all categories |
| `/users` | GET | List other users |
| `/users/<user_id>` | GET | View a user’s solved problems |

## Admin / maintenance routes

| Route | Method | Purpose |
|---|---:|---|
| `/admin/load-problems-once` | POST | Bulk load all problems |
| `/admin/sync-problems` | POST | Incrementally sync new problems |

---

## Security

### Password security
Passwords are hashed before storage. Plain passwords are never stored.

### OTP security
OTP records are stored separately from users, and can expire or be replaced. For development, OTP delivery can be disabled or replaced with a static code.

### Reset token security
Password reset tokens are stored as hashes and used only once.

### Authorization
- Guests cannot access protected routes
- Admin sync routes are protected
- Flask-Login manages authenticated sessions

### Input validation
The app validates:
- unique username/email
- matching passwords
- valid problem number
- category inputs

### CSRF protection
Forms are designed to use CSRF tokens on POST requests.

### Rate limiting
Sensitive routes are rate limited to reduce abuse:
- signup
- login
- OTP verification
- forgot/reset password
- admin sync actions
- destructive problem-management actions

---

## Trade-offs and design choices

### 1. SQLite for local development, Postgres for deployment
**Why:** SQLite is simple and easy to start with.  
**Trade-off:** SQLite is not ideal for production or hosted ephemeral filesystems.  
**Choice:** Use SQLite locally and Postgres in deployment.

### 2. SQLAlchemy instead of raw SQL
**Why:** Easier schema management, portability, and cleaner code.  
**Trade-off:** Slight abstraction overhead.  
**Choice:** Use SQLAlchemy for maintainability.

### 3. Separate master problem catalog from solved-problem history
**Why:** The same problem should not be duplicated for every user.  
**Trade-off:** Requires joins when displaying solved problems.  
**Choice:** Keep `problems` and `user_problems` separate.

### 4. User-scoped categories
**Why:** Different users can use the same category name with different meanings.  
**Trade-off:** More tables and constraints.  
**Choice:** Scope categories to each user.

### 5. Many-to-many mapping for categories
**Why:** A problem can belong to multiple categories.  
**Trade-off:** Requires an extra join table.  
**Choice:** Use `problem_categories` for flexibility.

### 6. Background sync instead of live API calls everywhere
**Why:** Faster and more reliable during normal usage.  
**Trade-off:** Data may lag until the next sync.  
**Choice:** Cache problem metadata locally.

### 7. OTP-based auth
**Why:** Adds an email verification layer.  
**Trade-off:** Adds more steps and requires mail setup.  
**Choice:** Useful for a secure demo, but can be temporarily disabled during development.

### 8. Static OTP / disabled mail for deployment testing
**Why:** Email services can be slow or unreliable during early deployment.  
**Trade-off:** Not secure for public production use.  
**Choice:** Use only for testing and private demos.

### 9. Flask monolith instead of microservices
**Why:** Simpler to build, debug, and deploy for a solo project.  
**Trade-off:** Harder to scale into independently deployed services later.  
**Choice:** Keep the architecture straightforward.

---

## Local setup

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Create and activate a virtual environment
Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env`
Copy `.env.example` to `.env` and fill in the values.

### 5. Apply database migrations
```bash
flask --app main.py db upgrade
```

### 6. Run the app
```bash
python run.py
```

---

## Deployment notes

### Recommended deployment stack
- **GitHub** for source control
- **Render** for hosting the Flask app
- **Neon** for hosted Postgres

### Important deployment note
Do not rely on SQLite for a hosted deployment that needs persistent data. Use a managed database instead.

### Production start command
```bash
gunicorn main:app
```

### Environment variables on host
Set:
- `SECRET_KEY`
- `DATABASE_URL`
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USE_TLS`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`
- `MAIL_TIMEOUT`

---

## Environment variables

Example `.env`:

```env
SECRET_KEY=change-me
DATABASE_URL=sqlite:///problem-leetcode.db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=your_email@gmail.com
MAIL_TIMEOUT=10

STATIC_OTP=123123
OTP_MODE=static
```

---

## Project structure

```text
flask_problem_tracker/
├── auth/
│   ├── routes.py
│   └── utils.py
├── problems/
│   ├── routes.py
│   └── sync.py
├── community/
│   └── routes.py
├── tasks/
│   └── scheduler.py
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── signup.html
│   ├── verify_otp.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── add_problems.html
│   ├── edit_solved_problem.html
│   ├── manage_problems.html
│   ├── solve_problems.html
│   ├── users_list.html
│   └── user_profile.html
├── config.py
├── extensions.py
├── main.py
├── models.py
├── requirements.txt
└── run.py
```

---

## Resume-ready summary

This project demonstrates:
- Flask backend development
- SQLAlchemy relational schema design
- authentication and authorization
- email OTP and password reset flows
- external API ingestion
- background sync jobs
- category-based retrieval logic
- route protection and rate limiting
- production deployment fundamentals

---

## License

Add your preferred license before publishing publicly.
