from flask import Flask, render_template, request, redirect, session, url_for
import psycopg2
from psycopg2.extras import DictCursor
import os
import sys

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'dynamic_cells_123')

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

# --- ROUTES ---

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
            return redirect('/dashboard')
        except Exception as e:
            return f"Σφάλμα εγγραφής: {e}"
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect('/login')
    return render_template('dashboard.html')

@app.route('/issue_recommendation', methods=['POST'])
def issue_recommendation():
    if 'doctor_id' not in session: return redirect('/login')
    doctor_id = session['doctor_id']
    d3_qty = int(request.form.get('d3_qty', 0)) if request.form.get('d3_active') == '1' else 0
    magnesium_qty = int(request.form.get('magnesium_qty', 0)) if request.form.get('magnesium_active') == '1' else 0
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO recommendations (doctor_id, diagnosis, d3_qty, magnesium_qty, special_notes, status) 
                          VALUES (%s,%s,%s,%s,%s,'pending') RETURNING id''',
                       (doctor_id, request.form.get('diagnosis', ''), d3_qty, magnesium_qty, request.form.get('special_notes', '')))
        new_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        # Μεταφορά στη σελίδα εκτύπωσης
        return redirect(url_for('print_prescription', rec_id=new_id))
    except Exception as e:
        return f"Σφάλμα: {e}"

@app.route('/print_prescription/<int:rec_id>')
def print_prescription(rec_id):
    if 'doctor_id' not in session: return redirect('/login')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''SELECT r.*, d.name as doctor_name, d.specialty, d.address 
                          FROM recommendations r JOIN doctors d ON r.doctor_id = d.id WHERE r.id = %s''', (rec_id,))
        rec = cursor.fetchone()
        cursor.close()
        conn.close()
        if not rec: return "Η συνταγή δεν βρέθηκε."
        return render_template('print.html', rec=rec)
    except Exception as e:
        return f"Σφάλμα εκτύπωσης: {e}"

@app.route('/admin')
def admin():
    if session.get('doctor_name') != 'Admin': return "Δεν έχετε δικαίωμα!", 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT d.id, d.name, COALESCE(SUM(r.d3_qty), 0) as total_d3 FROM doctors d LEFT JOIN recommendations r ON d.id = r.doctor_id GROUP BY d.id, d.name')
    stats = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', doctor_stats=stats)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
