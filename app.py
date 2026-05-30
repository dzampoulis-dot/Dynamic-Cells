from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2
from psycopg2.extras import DictCursor
import os
import sys

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dynamic_cells_123')

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set! Check Render Environment")

print(f"=== USING DATABASE: {DATABASE_URL[:60]}... ===", file=sys.stderr)

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

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
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
        except Exception as e:
            print(f"Login error: {e}", file=sys.stderr)
            return f"Σφάλμα σύνδεσης: {e}"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO doctors (name, specialty, address, phone, username, password) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                           (request.form['name'], request.form['specialty'], request.form['address'], request.form['phone'], request.form['username'], request.form['password']))
            session['doctor_id'] = cursor.fetchone()['id']
            session['doctor_name'] = request.form['name']
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Register error: {e}", file=sys.stderr)
            return f"Σφάλμα εγγραφής: {e}"
        return redirect('/dashboard')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect('/login')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM doctors WHERE id = %s', (session['doctor_id'],))
        doctor = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('dashboard.html', doctor=doctor)
    except Exception as e:
        print(f"Dashboard error: {e}", file=sys.stderr)
        return f"Σφάλμα: {e}"

@app.route('/my_stats')
def my_stats():
    if 'doctor_id' not in session: return redirect('/login')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT 
                          COALESCE(SUM(d3_qty), 0) as total_d3, 
                          COALESCE(SUM(magnesium_qty), 0) as total_mg, 
                          COALESCE(SUM(CASE WHEN status = 'pending' THEN d3_qty ELSE 0 END), 0) as pending_d3, 
                          COALESCE(SUM(CASE WHEN status = 'pending' THEN magnesium_qty ELSE 0 END), 0) as pending_mg 
                          FROM recommendations WHERE doctor_id = %s''', (session['doctor_id'],))
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('stats.html', stats=stats)
    except Exception as e:
        print(f"Stats error: {e}", file=sys.stderr)
        return f"Σφάλμα: {e}"

# --- ΠΡΟΣΘΗΚΗ ΓΙΑ ΕΚΤΥΠΩΣΗ ---
@app.route('/issue_recommendation', methods=['POST'])
def issue_recommendation():
    if 'doctor_id' not in session: return redirect('/login')
    doctor_id = session['doctor_id']
    d3_qty = int(request.form.get('d3_qty', 0)) if request.form.get('d3_active') == '1' else 0
    magnesium_qty = int(request.form.get('magnesium_qty', 0)) if request.form.get('magnesium_active') == '1' else 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO recommendations (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, status) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id',
                       (doctor_id, request.form.get('diagnosis', ''), d3_qty, magnesium_qty, request.form.get('special_notes', ''), 'pending'))
        new_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('print_prescription', rec_id=new_id))
    except Exception as e:
        print(f"Issue rec error: {e}", file=sys.stderr)
        return f"Σφάλμα: {e}"

@app.route('/print_prescription/<int:rec_id>')
def print_prescription(rec_id):
    if 'doctor_id' not in session: return redirect('/login')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT r.*, d.name as doctor_name FROM recommendations r JOIN doctors d ON r.doctor_id = d.id WHERE r.id = %s', (rec_id,))
        rec = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('print.html', rec=rec)
    except Exception as e:
        return f"Σφάλμα εκτύπωσης: {e}"
# ------------------------------

@app.route('/admin')
def admin():
    if session.get('doctor_name') != 'Admin':
        return "Δεν έχετε δικαίωμα πρόσβασης!", 403
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT d.id, d.name, COALESCE(SUM(r.d3_qty), 0) as total_d3, COALESCE(SUM(r.magnesium_qty), 0) as total_mg FROM doctors d LEFT JOIN recommendations r ON d.id = r.doctor_id GROUP BY d.id, d.name')
        doctor_stats = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin.html', doctor_stats=doctor_stats)
    except Exception as e:
        print(f"Admin error: {e}", file=sys.stderr)
        return f"Σφάλμα: {e}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
