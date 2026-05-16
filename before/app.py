"""
BEFORE: Aplicatie cu credentiale hard-codate
=============================================
PROBLEMA: Toate secretele sunt vizibile direct in cod.
Oricine acces la repo/cod sursa poate vedea credentialele.
"""

from flask import Flask, jsonify
import psycopg2
import boto3
import requests

app = Flask(__name__)

# VULNERABILITATE CRITICA: Credentiale hard-codate
DB_HOST     = "prod-db.internal.company.com"
DB_PORT     = 5432
DB_NAME     = "production_db"
DB_USER     = "admin"
DB_PASSWORD = "SuperSecretP@ssw0rd123!"   # <- vizibil in git history!

AWS_ACCESS_KEY_ID     = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_REGION            = "eu-west-1"

STRIPE_SECRET_KEY  = "sk_live_51HZn2KJK9..."
SENDGRID_API_KEY   = "SG.abc123xyz789..."
JWT_SECRET         = "my-super-secret-jwt-key-do-not-share"
INTERNAL_API_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."


def get_db_connection():
    """Conexiune DB cu credentiale expuse direct."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD   # <- trimis in clar
    )


def get_s3_client():
    """Client S3 cu chei AWS hard-codate."""
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "1.0-INSECURE"})


@app.route("/users")
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users LIMIT 10")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"users": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/send-email")
def send_email():
    """Trimite email folosind SendGrid cu API key expus."""
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "personalizations": [{"to": [{"email": "user@example.com"}]}],
        "from": {"email": "noreply@company.com"},
        "subject": "Test",
        "content": [{"type": "text/plain", "value": "Hello!"}],
    }
    r = requests.post("https://api.sendgrid.com/v3/mail/send",
                      json=payload, headers=headers)
    return jsonify({"status": r.status_code})


if __name__ == "__main__":
    #Debug mode ON in productie - alta vulnerabilitate
    app.run(host="0.0.0.0", port=5000, debug=True)
