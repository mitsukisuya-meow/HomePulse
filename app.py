from functools import wraps
from pathlib import Path
import os, sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / 'instance' / 'homepulse.sqlite3'
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('HOMEPULSE_SECRET_KEY', 'change-this-development-secret-before-deployment'), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'resident' CHECK(role IN ('resident','admin')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, category TEXT NOT NULL, location TEXT NOT NULL, description TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','In Progress','Resolved','Rejected')),
          admin_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, read_at TEXT
        );
        ''')


def current_user():
    uid = session.get('user_id')
    if not uid: return None
    with db() as con:
        row = con.execute('SELECT id,name,email,role,created_at FROM users WHERE id=?', (uid,)).fetchone()
    if row is None: session.clear()
    return row


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login', next=request.path))
        return fn(*args, **kwargs)
    return wrapped


def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash('Please log in with your administrator account.', 'info')
            return redirect(url_for('admin_login'))
        if user['role'] != 'admin': abort(403)
        return fn(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user(): return {'user': current_user()}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if current_user(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        confirm = request.form.get('confirm_password','')
        if len(name) < 2: flash('Please enter your full name.', 'error')
        elif '@' not in email or '.' not in email.rsplit('@',1)[-1]: flash('Enter a valid email address.', 'error')
        elif len(password) < 8: flash('Password must be at least 8 characters.', 'error')
        elif password != confirm: flash('Passwords do not match.', 'error')
        else:
            try:
                with db() as con:
                    cur = con.execute('INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)', (name,email,generate_password_hash(password),'resident'))
                    uid = cur.lastrowid
                session.clear(); session['user_id'] = uid
                flash('Your resident account is ready.', 'success')
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError: flash('An account with that email already exists.', 'error')
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user(): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        with db() as con: account=con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if account and check_password_hash(account['password_hash'], password):
            session.clear(); session['user_id']=account['id']
            dest = request.args.get('next')
            if account['role']=='admin': return redirect(url_for('admin_dashboard'))
            return redirect(dest if dest and dest.startswith('/') and not dest.startswith('//') else url_for('dashboard'))
        flash('Email or password is incorrect.', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear(); flash('You have been logged out.', 'success'); return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    u=current_user()
    with db() as con:
        reports=con.execute('SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC LIMIT 5',(u['id'],)).fetchall()
        counts=con.execute("SELECT COUNT(*) total, SUM(status='Pending') pending, SUM(status='In Progress') progress, SUM(status='Resolved') resolved FROM reports WHERE user_id=?",(u['id'],)).fetchone()
    return render_template('dashboard.html', reports=reports, counts=counts)

@app.route('/reports', methods=['GET','POST'])
@login_required
def reports():
    u=current_user()
    if request.method=='POST':
        title=request.form.get('title','').strip(); category=request.form.get('category','').strip(); location=request.form.get('location','').strip(); description=request.form.get('description','').strip()
        if not all([title,category,location,description]): flash('Please complete all required fields.', 'error')
        elif len(description)<10: flash('Please add a little more detail (at least 10 characters).', 'error')
        else:
            with db() as con:
                con.execute('INSERT INTO reports(user_id,title,category,location,description) VALUES(?,?,?,?,?)',(u['id'],title,category,location,description))
            flash('Your concern has been submitted successfully.', 'success'); return redirect(url_for('my_reports'))
    return render_template('report_form.html')

@app.route('/my-reports')
@login_required
def my_reports():
    q=request.args.get('q','').strip(); status=request.args.get('status','')
    sql='SELECT * FROM reports WHERE user_id=?'; args=[current_user()['id']]
    if q: sql+=' AND (title LIKE ? OR location LIKE ? OR CAST(id AS TEXT)=?)'; args += [f'%{q}%',f'%{q}%',q]
    if status in ['Pending','In Progress','Resolved','Rejected']: sql+=' AND status=?'; args.append(status)
    sql+=' ORDER BY created_at DESC'
    with db() as con: rows=con.execute(sql,args).fetchall()
    return render_template('my_reports.html', reports=rows, q=q, selected_status=status)

@app.route('/reports/<int:report_id>')
@login_required
def report_detail(report_id):
    with db() as con: r=con.execute('SELECT r.*,u.name reporter FROM reports r JOIN users u ON u.id=r.user_id WHERE r.id=? AND r.user_id=?',(report_id,current_user()['id'])).fetchone()
    if not r: abort(404)
    return render_template('report_detail.html', report=r)

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    u=current_user()
    if request.method=='POST':
        name=request.form.get('name','').strip()
        if len(name)<2: flash('Name must be at least 2 characters.', 'error')
        else:
            with db() as con: con.execute('UPDATE users SET name=? WHERE id=?',(name,u['id']))
            flash('Profile updated.', 'success'); return redirect(url_for('profile'))
    return render_template('profile.html')

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    u=current_user()
    if u and u['role']=='admin': return redirect(url_for('admin_dashboard'))
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        with db() as con: account=con.execute('SELECT * FROM users WHERE email=? AND role=\'admin\'',(email,)).fetchone()
        if account and check_password_hash(account['password_hash'],password):
            session.clear(); session['user_id']=account['id']; return redirect(url_for('admin_dashboard'))
        flash('Administrator credentials are incorrect.', 'error')
    return render_template('admin_login.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    with db() as con:
        stats=con.execute("SELECT COUNT(*) total, SUM(status='Pending') pending, SUM(status='In Progress') progress, SUM(status='Resolved') resolved FROM reports").fetchone()
        rows=con.execute('SELECT r.*,u.name reporter,u.email FROM reports r JOIN users u ON u.id=r.user_id ORDER BY r.created_at DESC LIMIT 8').fetchall()
    return render_template('admin_dashboard.html', stats=stats, reports=rows)

@app.route('/admin/reports')
@admin_required
def admin_reports():
    q=request.args.get('q','').strip(); status=request.args.get('status','')
    sql='SELECT r.*,u.name reporter,u.email FROM reports r JOIN users u ON u.id=r.user_id WHERE 1=1'; args=[]
    if q: sql+=' AND (r.title LIKE ? OR u.name LIKE ? OR r.location LIKE ? OR CAST(r.id AS TEXT)=?)'; args += [f'%{q}%',f'%{q}%',f'%{q}%',q]
    if status in ['Pending','In Progress','Resolved','Rejected']: sql+=' AND r.status=?'; args.append(status)
    sql+=' ORDER BY r.created_at DESC'
    with db() as con: rows=con.execute(sql,args).fetchall()
    return render_template('admin_reports.html', reports=rows, q=q, selected_status=status)

@app.route('/admin/reports/<int:report_id>/update', methods=['POST'])
@admin_required
def update_report(report_id):
    status=request.form.get('status',''); note=request.form.get('admin_note','').strip()
    if status not in ['Pending','In Progress','Resolved','Rejected']:
        flash('Invalid report status.', 'error'); return redirect(url_for('admin_reports'))
    with db() as con:
        r=con.execute('SELECT user_id,title FROM reports WHERE id=?',(report_id,)).fetchone()
        if not r: abort(404)
        con.execute('UPDATE reports SET status=?,admin_note=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,note,report_id))
        con.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(r['user_id'],f"Your report #{report_id} ({r['title']}) status changed to {status}."))
    flash(f'Report #{report_id} updated.', 'success'); return redirect(url_for('admin_reports'))

@app.route('/admin/users')
@admin_required
def admin_users():
    with db() as con: users=con.execute('SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC').fetchall()
    return render_template('admin_users.html', users=users)

@app.route('/notifications')
@login_required
def notifications():
    with db() as con:
        rows=con.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC',(current_user()['id'],)).fetchall()
        con.execute('UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE user_id=? AND read_at IS NULL',(current_user()['id'],))
    return render_template('notifications.html', notifications=rows)

@app.errorhandler(403)
def forbidden(e): return render_template('error.html', code=403, message='You do not have permission to access this page.'),403
@app.errorhandler(404)
def not_found(e): return render_template('error.html', code=404, message='We could not find that page.'),404

init_db()
if __name__=='__main__': app.run(debug=True, port=5000)
