from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime
from flask_mail import Mail, Message
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
CORS(app)

# Secret Key
app.secret_key = "secret123"
# ---------- EMAIL CONFIG ----------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
mail = Mail(app)

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect('complaint.db')
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        roll TEXT,
        email TEXT,
        branch TEXT,
        year TEXT,
        category TEXT,
        description TEXT,
        status TEXT DEFAULT 'Pending',
        date TEXT
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS admin(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )''')

    # Default admin (only one)
    cur.execute("INSERT OR IGNORE INTO admin (id, username, password) VALUES (1, 'admin', '123')")
    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route('/')
def home():
    return render_template('index.html')

# ---------- SUBMIT COMPLAINT ----------
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    roll = request.form['roll']
    email = request.form['email']
    branch = request.form['branch']
    year = request.form['year']
    category = request.form['category']
    description = request.form['description']
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect('complaint.db')
    cur = conn.cursor()
    cur.execute("""INSERT INTO complaints 
        (name, roll, email, branch, year, category, description, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, roll, email, branch, year, category, description, date))
    conn.commit()
    conn.close()

    # Send email to admin
    try:
        msg = Message("New Complaint Submitted",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['yashika9569597936@gmail.com'])
        msg.body = f"""
A new complaint has been submitted:

Name: {name}
Roll No: {roll}
Email: {email}
Branch: {branch}
Year: {year}
Category: {category}
Description: {description}
Date: {date}
"""
        mail.send(msg)
    except Exception as e:
        print("Mail Error:", e)

    return "<h2>Complaint submitted successfully! Admin has been notified.<br><a href='/'>Back</a></h2>"

# ---------- STATUS CHECK ----------
@app.route('/status', methods=['GET', 'POST'])
def status():
    data = None
    if request.method == 'POST':
        roll = request.form['roll']
        conn = sqlite3.connect('complaint.db')
        cur = conn.cursor()
        cur.execute("SELECT category, description, status, date FROM complaints WHERE roll=?", (roll,))
        data = cur.fetchall()
        conn.close()
        return render_template('status.html', data=data, roll=roll)
    return render_template('status.html', data=data)

# ---------- ADMIN LOGIN ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('complaint.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
        admin = cur.fetchone()
        conn.close()

        if admin:
            session['admin'] = username
            return redirect(url_for('dashboard'))
        else:
            return "<h3>Invalid credentials. Try again.</h3>"

    return render_template('admin_login.html')

# ---------- ADMIN DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('complaint.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()

    return render_template('dashboard.html', data=data)

# ---------- UPDATE STATUS ----------
@app.route('/update_status/<int:id>/<status>')
def update_status(id, status):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('complaint.db')
    cur = conn.cursor()

    # Fetch complaint info
    cur.execute("SELECT email, name, category FROM complaints WHERE id=?", (id,))
    row = cur.fetchone()

    # Automatically remove resolved complaints from the system
    if status == "Resolved":
        cur.execute("DELETE FROM complaints WHERE id=?", (id,))
    else:
        cur.execute("UPDATE complaints SET status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()

    # Send email to student
    if row:
        email, name, category = row
        try:
            msg = Message("Complaint Status Updated",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"""
Hello {name},

Your complaint '{category}' status has been updated to: {status}.

Regards,
College Complaint Portal Admin
"""
            mail.send(msg)
        except Exception as e:
            print("Mail Error:", e)

    return redirect(url_for('dashboard'))

# ---------- ABOUT ----------
@app.route('/about')
def about():
    return render_template('about.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# ---------- RUN APP ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
