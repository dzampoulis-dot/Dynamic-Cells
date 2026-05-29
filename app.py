import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Η εφαρμογή ξεκίνησε επιτυχώς!"

if __name__ == '__main__':
    # Το Render θέλει να χρησιμοποιήσει τη δική του θύρα, 
    # αν δεν υπάρχει, χρησιμοποιούμε την 10000.
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
