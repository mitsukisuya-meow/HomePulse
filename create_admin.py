"""Create or promote a HomePulse administrator account interactively."""
from getpass import getpass
import re
from app import db, init_db
from werkzeug.security import generate_password_hash

init_db()
name = input('Administrator full name: ').strip()
email = input('Administrator email: ').strip().lower()
if len(name) < 2 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
    raise SystemExit('Please enter a valid name and email.')
password = getpass('Password (minimum 12 characters): ')
confirm = getpass('Confirm password: ')
if len(password) < 12: raise SystemExit('Password must be at least 12 characters.')
if password != confirm: raise SystemExit('Passwords do not match.')
with db() as con:
    row = con.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
    if row:
        con.execute("UPDATE users SET name=?, password_hash=?, role='admin' WHERE id=?", (name, generate_password_hash(password), row['id']))
        print(f'Promoted existing account {email} to administrator.')
    else:
        con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,'admin')", (name,email,generate_password_hash(password)))
        print(f'Administrator account created for {email}.')
print('Open http://127.0.0.1:5000/admin/login to sign in.')
