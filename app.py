from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import DictCursor
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dynamic_cells_123'

DATABASE_URL = "postgresql://postgres:DynamicCells1!@db.lwxbuotfkpdlqvsuslkx.supabase.co:5432/postgres"

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

init_db()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE username = %s AND password = %s", (username, password))
    doctor = cursor.fetchone()
    conn.close()
    if doctor:
        session['doctor_id'] = doctor['id']
        session['doctor_name'] = doctor['name']
        return redirect('/dashboard')
    return "Λάθος στοιχεία!"

@app.route('/dashboard')
def dashboard():
    if 'doctor_id' not in session: return redirect('/login')
    return render_template('dashboard.html', doctor_name=session.get('doctor_name'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
