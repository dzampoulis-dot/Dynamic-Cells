from flask import Flask
import os
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)

# Το URL της βάσης σου
DATABASE_URL = "postgresql://postgres:DynamicCells1!@db.lwxbuotfkpdlqvsuslkx.supabase.co:6543/postgres"

@app.route('/')
def home():
    try:
        # Δοκιμάζουμε μια απλή σύνδεση
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
        conn.close()
        return "Η εφαρμογή είναι LIVE και συνδεδεμένη με τη βάση!"
    except Exception as e:
        return f"Η εφαρμογή είναι LIVE, αλλά η βάση έχει σφάλμα: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
