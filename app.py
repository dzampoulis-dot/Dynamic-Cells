from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import DictCursor
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dynamic_cells_123'

DATABASE_URL = "postgresql://postgres:DynamicCells1!@db.lwxbuotfkpdlqvsuslkx.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM doctors WHERE username = %s AND password = %s", (username, password))
    doctor = cur.fetchone()
    conn.close()
    if doctor:
        session['doctor_id'] = doctor['id']
        session['doctor_name'] = doctor['name']
        return redirect('/dashboard')
    return "Λάθος στοιχεία!"

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect('/login')
    return render_template('dashboard.html', doctor_name=session.get('doctor_name'))

# ISSUE RECOMMENDATION
@app.route('/issue_recommendation', methods=['POST'])
def issue_recommendation():
    if 'doctor_id' not in session: return redirect('/login')
    # Εδώ μπαίνει η λογική της συνταγογράφησης που είχες
    return "Συνταγογράφηση επιτυχής!"

# ADMIN
@app.route('/admin')
def admin():
    if session.get('doctor_name') != 'Admin': return "Όχι πρόσβαση!", 403
    return render_template('admin.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
