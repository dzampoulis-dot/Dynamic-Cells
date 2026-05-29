from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import DictCursor
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dynamic_cells_123'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS doctors (id SERIAL PRIMARY KEY, name TEXT, specialty TEXT, address TEXT, phone TEXT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS recommendations (id SERIAL PRIMARY KEY, doctor_id INTEGER REFERENCES doctors(id), diagnosis TEXT, d3_qty INTEGER DEFAULT 0, magnesium_qty INTEGER DEFAULT 0, special_notes TEXT, status TEXT DEFAULT 'pending')''')
    conn.commit()
    cursor.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"Error initializing database: {e}")

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM doctors WHERE username = %s AND password = %s', (username, password))
        doctor = cursor.fetchone()
        cursor.close()
        conn.close()
        if doctor:
            session['doctor_id'] = doctor['id']
            session['doctor_name'] = doctor['name']
            return redirect('/dashboard')
        return "Λάθος στοιχεία!"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name, specialty, address = request.form['name'], request.form['specialty'], request.form['address']
        phone, username, password = request.form['phone'], request.form['username'], request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO doctors (name, specialty, address, phone, username, password) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                           (name, specialty, address, phone, username, password))
            session['doctor_id'] = cursor.fetchone()['id']
            session['doctor_name'] = name
            conn.commit()
        except Exception:
            conn.rollback()
        conn.close()
        return redirect('/dashboard')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM doctors WHERE id = %s', (session['doctor_id'],))
    doctor = cursor.fetchone()
    conn.close()
    return render_template('dashboard.html', doctor=doctor)

@app.route('/my_stats')
def my_stats():
    if 'doctor_id' not in session: return redirect('/login')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT SUM(d3_qty) as total_d3, SUM(magnesium_qty) as total_mg, 
                      SUM(CASE WHEN status = 'pending' THEN d3_qty ELSE 0 END) as pending_d3, 
                      SUM(CASE WHEN status = 'pending' THEN magnesium_qty ELSE 0 END) as pending_mg 
                      FROM recommendations WHERE doctor_id = %s''', (session['doctor_id'],))
    stats = cursor.fetchone()
    conn.close()
    return render_template('stats.html', stats=stats)

@app.route('/issue_recommendation', methods=['POST'])
def issue_recommendation():
    if 'doctor_id' not in session: return redirect('/login')
    doctor_id = session['doctor_id']
    d3_qty = int(request.form.get('d3_qty', 0)) if request.form.get('d3_active') == '1' else 0
    magnesium_qty = int(request.form.get('magnesium_qty', 0)) if request.form.get('magnesium_active') == '1' else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recommendations (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                   (doctor_id, request.form.get('diagnosis', ''), d3_qty, magnesium_qty, request.form.get('special_notes', ''), 'pending'))
    conn.commit()
    conn.close()
    return "Συνταγογράφηση επιτυχής!"

@app.route('/admin')
def admin():
    if session.get('doctor_name') != 'Admin':
        return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT d.id, d.name, SUM(r.d3_qty) as total_d3, SUM(r.magnesium_qty) as total_mg FROM doctors d LEFT JOIN recommendations r ON d.id = r.doctor_id GROUP BY d.id, d.name')
    doctor_stats = cursor.fetchall()
    conn.close()
    return render_template('admin.html', doctor_stats=doctor_stats)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
