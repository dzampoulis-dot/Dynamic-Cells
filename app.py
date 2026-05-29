from flask import Flask, render_template, request, redirect, session
import psycopg2
from psycopg2.extras import DictCursor
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = 'dynamic_cells_123'

DATABASE_URL = "postgresql://postgres:DynamicCells1!@db.lwxbuotfkpdlqvsuslkx.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)

# ΠΡΟΣΘΗΚΗ ΑΥΤΟΥ ΤΟΥ ΚΟΜΜΑΤΙΟΥ ΓΙΑ ΝΑ ΜΗΝ ΚΡΑΣΑΡΕΙ
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS doctors 
                   (id SERIAL PRIMARY KEY, name TEXT, specialty TEXT, address TEXT, phone TEXT, username TEXT UNIQUE, password TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS recommendations 
                   (id SERIAL PRIMARY KEY, doctor_id INTEGER REFERENCES doctors(id), diagnosis TEXT, d3_qty INTEGER, magnesium_qty INTEGER, special_notes TEXT, status TEXT)''')
    conn.commit()
    cur.close()
    conn.close()

# Τρέχει μια φορά κατά την εκκίνηση
init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    # ... (ο υπόλοιπος κώδικας σου)
