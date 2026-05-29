import os
from flask import Flask
from sqlalchemy import create_engine, text

app = Flask(__name__)

DATABASE_URL = "postgresql://postgres.lwxbuotfkpdlqvsuslkx:DynamicCells1!2@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)

@app.route('/')
def home():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # Εδώ προσθέτουμε λίγη HTML για να μην είναι λευκή η οθόνη
        return "<h1>Καλώς ήρθες στο DynamicCells!</h1><p style='color:green;'>Η βάση συνδέθηκε επιτυχώς.</p>"
    except Exception as e:
        return f"<h1>Σφάλμα</h1><p style='color:red;'>{str(e)}</p>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
