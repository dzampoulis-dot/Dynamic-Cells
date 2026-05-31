from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2
from psycopg2.extras import DictCursor
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-this')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL: return None
    conn_str = DATABASE_URL if 'sslmode' in DATABASE_URL else DATABASE_URL + "?sslmode=require"
    return psycopg2.connect(conn_str, cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id SERIAL PRIMARY KEY, name TEXT, specialty TEXT, address TEXT, 
        phone TEXT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS recommendations (
        id SERIAL PRIMARY KEY, doctor_id INTEGER REFERENCES doctors(id), 
        diagnosis TEXT, d3_qty INTEGER DEFAULT 0, magnesium_qty INTEGER DEFAULT 0, 
        special_notes TEXT, status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"DB init error: {e}")

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM doctors WHERE username = %s', (username,))
        doctor = cursor.fetchone()
        cursor.close()
        conn.close()
        if doctor and check_password_hash(doctor['password'], password):
            session['doctor_id'] = doctor['id']
            session['doctor_name'] = doctor['name']
            session['username'] = doctor['username']
            return redirect(url_for('dashboard'))
        return "Λάθος στοιχεία!"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO doctors (name, specialty, address, phone, username, password) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''', 
                (request.form['name'], request.form['specialty'], request.form['address'], 
                 request.form['phone'], request.form['username'].lower(), generate_password_hash(request.form['password'])))
            conn.commit()
            return redirect(url_for('login'))
        except:
            conn.rollback()
            return render_template('register.html', error="Το username υπάρχει ήδη!")
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM doctors WHERE id = %s', (session['doctor_id'],))
    doctor = cursor.fetchone()
    conn.close()
    return render_template('dashboard.html', doctor=doctor)

@app.route('/issue_recommendation', methods=['POST'])
def issue_recommendation():
    if 'doctor_id' not in session: return redirect(url_for('login'))
    d3 = int(request.form.get('d3_qty', 0)) if request.form.get('d3_active') else 0
    mg = int(request.form.get('magnesium_qty', 0)) if request.form.get('magnesium_active') else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO recommendations (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, status) 
        VALUES (%s, %s, %s, %s, %s, 'pending') RETURNING id''', 
        (session['doctor_id'], request.form.get('diagnosis'), d3, mg, request.form.get('special_notes')))
    rec_id = cursor.fetchone()['id']
    conn.commit()
    conn.close()
    return redirect(url_for('admin_print_rec', rec_id=rec_id))

@app.route('/admin/recommendations')
def admin_recommendations():
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    status_filter = request.args.get('status', 'all')
    doctor_filter = request.args.get('doctor_id', 'all')
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """SELECT r.*, d.name as doctor_name, d.specialty 
               FROM recommendations r JOIN doctors d ON r.doctor_id = d.id WHERE 1=1"""
    params = []
    if status_filter != 'all':
        query += ' AND r.status = %s'
        params.append(status_filter)
    if doctor_filter != 'all':
        query += ' AND r.doctor_id = %s'
        params.append(int(doctor_filter))
    query += ' ORDER BY r.created_at DESC'
    cursor.execute(query, tuple(params))
    recommendations = cursor.fetchall()
    cursor.execute('SELECT id, name FROM doctors WHERE username != %s', ('admin',))
    doctors = cursor.fetchall()
    conn.close()
    return render_template('admin_recs.html', recommendations=recommendations, doctors=doctors, status_filter=status_filter, doctor_filter=doctor_filter)

@app.route('/admin/update_status/<int:rec_id>/<status>', methods=['POST'])
def update_status(rec_id, status):
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE recommendations SET status = %s WHERE id = %s', (status, rec_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_recommendations'))

@app.route('/admin/print/<int:rec_id>')
def admin_print_rec(rec_id):
    if 'doctor_id' not in session and session.get('username') != 'admin': return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT r.*, d.name, d.specialty, d.address, d.phone FROM recommendations r JOIN doctors d ON r.doctor_id = d.id WHERE r.id = %s', (rec_id,))
    rec = cursor.fetchone()
    conn.close()
    if not rec: return "Δεν βρέθηκε", 404
    # Εδώ καλούμε το print.html όπως επιβεβαίωσες
    return render_template('print.html', serial=rec['id'], doctor=rec, diagnosis=rec['diagnosis'],
                           d3_qty=rec['d3_qty'], magnesium_qty=rec['magnesium_qty'],
                           d3_days=rec['d3_qty']*30, magnesium_days=rec['magnesium_qty']*30,
                           special_notes=rec['special_notes'], current_date=datetime.now().strftime('%d/%m/%Y'),
                           current_time=datetime.now().strftime('%H:%M'))

@app.route('/admin')
def admin():
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(d3_qty),0), COALESCE(SUM(magnesium_qty),0), COALESCE(SUM(CASE WHEN status='pending' THEN d3_qty END),0), COALESCE(SUM(CASE WHEN status='pending' THEN magnesium_qty END),0), COALESCE(SUM(CASE WHEN status='paid' THEN d3_qty END),0), COALESCE(SUM(CASE WHEN status='paid' THEN magnesium_qty END),0) FROM recommendations")
    totals = cursor.fetchone()
    cursor.execute("SELECT d.id, d.name, d.specialty, COUNT(r.id) as total_recs FROM doctors d LEFT JOIN recommendations r ON d.id = r.doctor_id WHERE d.username != 'admin' GROUP BY d.id, d.name, d.specialty")
    doctor_stats = cursor.fetchall()
    conn.close()
    return render_template('admin.html', doctor_stats=doctor_stats, totals=totals)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
