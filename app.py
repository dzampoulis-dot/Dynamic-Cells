from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import psycopg2
from psycopg2.extras import DictCursor
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-this')

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if 'sslmode' not in DATABASE_URL:
        conn_str = DATABASE_URL + "?sslmode=require"
    else:
        conn_str = DATABASE_URL
    return psycopg2.connect(conn_str, cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id SERIAL PRIMARY KEY, name TEXT, specialty TEXT, address TEXT, 
        phone TEXT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS recommendations (
        id SERIAL PRIMARY KEY, doctor_id INTEGER REFERENCES doctors(id), 
        diagnosis TEXT, d3_qty INTEGER DEFAULT 0, magnesium_qty INTEGER DEFAULT 0, 
        special_notes TEXT, status TEXT DEFAULT 'pending')''')
    cursor.execute('''ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP''')
    cursor.execute('''UPDATE recommendations SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL''')
    cursor.execute('''DELETE FROM recommendations WHERE status = 'draft' ''')
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
                Values (%s, %s, %s, %s, %s, %s) RETURNING id''',
                (request.form['name'], request.form['specialty'], request.form['address'], 
                 request.form['phone'], request.form['username'].lower(), generate_password_hash(request.form['password'])))
            session['doctor_id'] = cursor.fetchone()['id']
            session['doctor_name'] = request.form['name']
            session['username'] = request.form['username'].lower()
            conn.commit()
            return redirect(url_for('dashboard'))
        except psycopg2.IntegrityError:
            conn.rollback()
            return render_template('register.html', error="Το username υπάρχει ήδη!")
        finally:
            cursor.close(); conn.close()
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
    doctor_id = session['doctor_id']
    d3_qty = int(request.form.get('d3_qty', 0)) if request.form.get('d3_active') == '1' else 0
    magnesium_qty = int(request.form.get('magnesium_qty', 0)) if request.form.get('magnesium_active') == '1' else 0
    
    if d3_qty == 0 and magnesium_qty == 0:
        return redirect(url_for('dashboard'))
    
    diagnosis = request.form.get('diagnosis', '')
    special_notes = request.form.get('special_notes', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO recommendations (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, status) 
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
        (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, 'draft'))
    rec_id = cursor.fetchone()['id']
    cursor.execute('SELECT * FROM doctors WHERE id = %s', (doctor_id,))
    doctor = cursor.fetchone()
    conn.commit(); conn.close()
    
    return render_template('print.html', serial=rec_id, doctor=doctor, diagnosis=diagnosis, 
                           d3_qty=d3_qty, magnesium_qty=magnesium_qty, d3_days=d3_qty*30, 
                           magnesium_days=magnesium_qty*30, special_notes=special_notes, 
                           current_date=datetime.now().strftime('%d/%m/%Y'), 
                           current_time=datetime.now().strftime('%H:%M'))

@app.route('/confirm_print/<int:rec_id>', methods=['POST'])
def confirm_print(rec_id):
    if 'doctor_id' not in session: return jsonify({'ok': False}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE recommendations SET status = 'pending' WHERE id = %s AND doctor_id = %s", 
                   (rec_id, session['doctor_id']))
    conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/my_stats')
def my_stats():
    if 'doctor_id' not in session: return redirect(url_for('login'))
    doctor_id = session['doctor_id']
    status_filter = request.args.get('status', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Stats query με φίλτρα
    stats_query = '''SELECT 
        COUNT(*) as total_recs,
        COALESCE(SUM(d3_qty), 0) as total_d3,
        COALESCE(SUM(magnesium_qty), 0) as total_mg,
        COALESCE(SUM(CASE WHEN status = 'pending' THEN d3_qty ELSE 0 END), 0) as pending_d3,
        COALESCE(SUM(CASE WHEN status = 'pending' THEN magnesium_qty ELSE 0 END), 0) as pending_mg,
        COALESCE(SUM(CASE WHEN status = 'paid' THEN d3_qty ELSE 0 END), 0) as paid_d3,
        COALESCE(SUM(CASE WHEN status = 'paid' THEN magnesium_qty ELSE 0 END), 0) as paid_mg,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_recs,
        COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_recs
        FROM recommendations WHERE doctor_id = %s AND status != 'draft' '''
    stats_params = [doctor_id]
    if status_filter != 'all': stats_query += ' AND status = %s'; stats_params.append(status_filter)
    if date_from: stats_query += ' AND created_at >= %s'; stats_params.append(date_from)
    if date_to: stats_query += ' AND created_at <= %s'; stats_params.append(date_to + ' 23:59:59')
    cursor.execute(stats_query, tuple(stats_params))
    stats = cursor.fetchone()

    # Recs query με φίλτρα
    recs_query = '''SELECT id, diagnosis, d3_qty, magnesium_qty, status, created_at 
        FROM recommendations WHERE doctor_id = %s AND status != 'draft' '''
    recs_params = [doctor_id]
    if status_filter != 'all': recs_query += ' AND status = %s'; recs_params.append(status_filter)
    if date_from: recs_query += ' AND created_at >= %s'; recs_params.append(date_from)
    if date_to: recs_query += ' AND created_at <= %s'; recs_params.append(date_to + ' 23:59:59')
    recs_query += ' ORDER BY id DESC LIMIT 200'
    cursor.execute(recs_query, tuple(recs_params))
    recs = cursor.fetchall()
    conn.close()
    return render_template('my_stats.html', stats=stats, recs=recs, 
                           status_filter=status_filter, date_from=date_from, date_to=date_to)

@app.route('/admin')
def admin():
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) as total_recs, COALESCE(SUM(d3_qty), 0) as total_d3, COALESCE(SUM(magnesium_qty), 0) as total_mg,
                      COALESCE(SUM(CASE WHEN status = 'pending' THEN d3_qty ELSE 0 END), 0) as pending_d3,
                      COALESCE(SUM(CASE WHEN status = 'pending' THEN magnesium_qty ELSE 0 END), 0) as pending_mg,
                      COALESCE(SUM(CASE WHEN status = 'paid' THEN d3_qty ELSE 0 END), 0) as paid_d3,
                      COALESCE(SUM(CASE WHEN status = 'paid' THEN magnesium_qty ELSE 0 END), 0) as paid_mg
                      FROM recommendations WHERE status != 'draft' ''')
    totals = cursor.fetchone()
    cursor.execute('''SELECT d.id, d.name, d.specialty, COUNT(r.id) as total_recs,
                      COALESCE(SUM(r.d3_qty), 0) as total_d3,
                      COALESCE(SUM(r.magnesium_qty), 0) as total_mg,
                      COALESCE(SUM(CASE WHEN r.status = 'pending' THEN r.d3_qty ELSE 0 END), 0) as pending_d3,
                      COALESCE(SUM(CASE WHEN r.status = 'pending' THEN r.magnesium_qty ELSE 0 END), 0) as pending_mg,
                      COALESCE(SUM(CASE WHEN r.status = 'paid' THEN r.d3_qty ELSE 0 END), 0) as paid_d3,
                      COALESCE(SUM(CASE WHEN r.status = 'paid' THEN r.magnesium_qty ELSE 0 END), 0) as paid_mg
                      FROM doctors d LEFT JOIN recommendations r ON d.id = r.doctor_id AND r.status != 'draft'
                      WHERE d.username != 'admin' GROUP BY d.id, d.name, d.specialty ORDER BY total_recs DESC''')
    doctor_stats = cursor.fetchall()
    conn.close()
    return render_template('admin.html', doctor_stats=doctor_stats, totals=totals)

@app.route('/admin/recommendations')
def admin_recommendations():
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    status_filter = request.args.get('status', 'all')
    doctor_filter = request.args.get('doctor_id', 'all')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''SELECT r.id, r.diagnosis, r.d3_qty, r.magnesium_qty, r.status, r.special_notes,
                      r.created_at, d.name as doctor_name, d.specialty 
               FROM recommendations r JOIN doctors d ON r.doctor_id = d.id 
               WHERE r.status != 'draft' '''
    params = []
    if status_filter != 'all': query += ' AND r.status = %s'; params.append(status_filter)
    if doctor_filter != 'all': query += ' AND r.doctor_id = %s'; params.append(int(doctor_filter))
    if date_from: query += ' AND r.created_at >= %s'; params.append(date_from)
    if date_to: query += ' AND r.created_at <= %s'; params.append(date_to + ' 23:59:59')
    query += ' ORDER BY r.id DESC LIMIT 500'
    cursor.execute(query, tuple(params))
    recommendations = cursor.fetchall()
    cursor.execute('SELECT id, name FROM doctors WHERE username != %s ORDER BY name', ('admin',))
    doctors = cursor.fetchall()
    conn.close()
    return render_template('admin_recs.html', recommendations=recommendations, doctors=doctors,
                           status_filter=status_filter, doctor_filter=doctor_filter,
                           date_from=date_from, date_to=date_to)

@app.route('/admin/update_status/<int:rec_id>/<status>', methods=['POST'])
def update_status(rec_id, status):
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE recommendations SET status = %s WHERE id = %s', (status, rec_id))
    conn.commit(); conn.close()
    return redirect(request.referrer or url_for('admin_recommendations'))

@app.route('/admin/print/<int:rec_id>')
def admin_print_rec(rec_id):
    if session.get('username') != 'admin': return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT r.id, r.diagnosis, r.d3_qty, r.magnesium_qty, r.special_notes, d.name, d.specialty, d.address, d.phone FROM recommendations r JOIN doctors d ON r.doctor_id = d.id WHERE r.id = %s', (rec_id,))
    rec = cursor.fetchone(); conn.close()
    if not rec: return "Η συνταγή δεν βρέθηκε", 404
    doctor = {'name': rec['name'], 'specialty': rec['specialty'], 'address': rec['address'], 'phone': rec['phone']}
    return render_template('print.html', serial=rec['id'], doctor=doctor, diagnosis=rec['diagnosis'], 
                           d3_qty=rec['d3_qty'], magnesium_qty=rec['magnesium_qty'], d3_days=rec['d3_qty']*30, 
                           magnesium_days=rec['magnesium_qty']*30, special_notes=rec['special_notes'], 
                           current_date=datetime.now().strftime('%d/%m/%Y'), current_time=datetime.now().strftime('%H:%M'),
                           is_admin=True)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
