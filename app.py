import os
from flask import Flask
from sqlalchemy import create_engine, text

app = Flask(__name__)

# Το URL της βάσης σου
DATABASE_URL = "postgresql://postgres.lwxbuotfkpdlqvsuslkx:DynamicCells1!2@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
engine = create_engine(DATABASE_URL)

@app.route('/')
def home():
    try:
        # Δοκιμή σύνδεσης
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        # Αυτό είναι το HTML που θα εμφανιστεί στην οθόνη σου
        return """
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1 style="color: #2c3e50;">Η εφαρμογή DynamicCells είναι έτοιμη!</h1>
                <p style="color: #27ae60; font-size: 1.2em;">Η σύνδεση με τη βάση δεδομένων λειτουργεί κανονικά.</p>
            </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Σφάλμα</h1><p>{str(e)}</p>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
