# HomePulse — Flask + SQLite

A local full-stack community reporting prototype with separate resident and administrator routes, SQLite persistence, hashed passwords, session-based login, report tracking, and admin status updates.

## Requirements
- Python 3.10 or newer
- pip

## Setup (Windows / VS Code)
1. Extract this folder and open `HomePulse` in VS Code.
2. Open **Terminal → New Terminal** in the project root (the folder containing `app.py`).
3. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and use `\.venv\Scripts\python.exe` for the remaining commands.
4. Install Flask:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Create an administrator account (new or promote an existing account):
   ```powershell
   python create_admin.py
   ```
   Use a unique password of at least 12 characters. Do not make public admin registration available.
6. Set a unique session secret for local development, then run the server. For PowerShell:
   ```powershell
   $env:HOMEPULSE_SECRET_KEY = [guid]::NewGuid().ToString() + [guid]::NewGuid().ToString()
   python app.py
   ```
7. Open `http://127.0.0.1:5000/`.
   - Resident sign up: `http://127.0.0.1:5000/register`
   - Resident login: `http://127.0.0.1:5000/login`
   - Admin login: `http://127.0.0.1:5000/admin/login`

The first launch creates `instance/homepulse.sqlite3` automatically. Keep the terminal open while using the site. Press Ctrl+C to stop the server.

## Included functions
- Resident signup/login/logout, profile name update
- Submit reports, list/search/filter personal reports, report detail and status timeline
- Notifications after an administrator changes a report status
- Admin-only dashboard, user listing, report search/filter, status/note updates
- Password hashes via Werkzeug; admin role checked server-side on each protected route

## Security and scope notes
This is intended for local development/coursework. Before deployment, set a long random `HOMEPULSE_SECRET_KEY` outside source control, run with debug disabled, use HTTPS, add CSRF protection/rate limiting/email verification/backups, and review privacy/data-retention requirements. Do not expose Flask's development server publicly. Admin account creation is a local CLI action; there is no public admin signup.

The original project's `images/` directory is retained. If a preferred logo asset differs, update the logo in `templates/base.html` and `templates/auth.html`.
