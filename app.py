import os
from flask import Flask
from sqlalchemy import create_engine, text

app = Flask(__name__)

# Το σωστό URL με το Transaction Pooler
DATABASE_URL = "postgresql://postgres.lwxbuotfkpdlqvsuslkx:DynamicCells1!2@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

engine = create_engine(DATABASE_URL)

@app.route('/')
def home():
    try:
        # Δοκιμή σύνδεσης
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "Η βάση συνδέθηκε επιτυχώς!"
    except Exception as e:
        return f"Σφάλμα σύνδεσης: {str(e)}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
