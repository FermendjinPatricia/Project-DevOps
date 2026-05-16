"""
AFTER: Aplicatie securizata cu HashiCorp Vault
===============================================
Nicio credentiala hard-codata. Toate secretele sunt
preluate la runtime din Vault cu autentificare AppRole.
"""

import os
import logging
from functools import lru_cache

import hvac
import psycopg2
import boto3
import requests
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ──────────────────────────────────────────────
# Vault Client - singura configuratie necesara
# vine din variabile de mediu NON-sensitive
# ──────────────────────────────────────────────

VAULT_ADDR    = os.environ["VAULT_ADDR"]          # ex: https://vault.internal:8200
VAULT_ROLE_ID = os.environ["VAULT_ROLE_ID"]       # AppRole role_id (non-secret)
# secret_id vine dintr-un secret Kubernetes / variabila injectata de CI
VAULT_SECRET_ID = os.environ["VAULT_SECRET_ID"]


@lru_cache(maxsize=1)
def get_vault_client() -> hvac.Client:
    """
    Autentificare prin AppRole.
    Token-ul este cache-uit in memorie si reinnoit automat.
    """
    client = hvac.Client(url=VAULT_ADDR, verify=True)
    auth = client.auth.approle.login(
        role_id=VAULT_ROLE_ID,
        secret_id=VAULT_SECRET_ID,
    )
    client.token = auth["auth"]["client_token"]
    logger.info("Autentificat in Vault cu AppRole")
    return client


def read_secret(path: str, key: str) -> str:
    """Citeste o valoare dintr-un secret KV-v2."""
    vault = get_vault_client()
    secret = vault.secrets.kv.v2.read_secret_version(path=path, raise_on_deleted_version=True)
    return secret["data"]["data"][key]


# ──────────────────────────────────────────────
# Conexiuni - secretele sunt preluate la runtime
# ──────────────────────────────────────────────

def get_db_connection():
    """Credentiale DB preluate din Vault la fiecare apel (sau pot fi cache-uite)."""
    creds = get_vault_client().secrets.kv.v2.read_secret_version(
        path="database/postgres"
    )["data"]["data"]

    return psycopg2.connect(
        host=creds["host"],
        port=int(creds["port"]),
        dbname=creds["dbname"],
        user=creds["username"],
        password=creds["password"],
        sslmode="require",         # TLS obligatoriu
        connect_timeout=5,
    )


def get_s3_client():
    """
    Optiune 1: credentiale AWS din Vault (KV).
    Optiune 2 (recomandata): IAM Role / IRSA - fara chei deloc.
    """
    creds = get_vault_client().secrets.kv.v2.read_secret_version(
        path="aws/s3-credentials"
    )["data"]["data"]

    return boto3.client(
        "s3",
        aws_access_key_id=creds["access_key_id"],
        aws_secret_access_key=creds["secret_access_key"],
        region_name=creds["region"],
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.route("/health")
def health():
    vault_ok = get_vault_client().is_authenticated()
    return jsonify({
        "status": "ok",
        "version": "2.0-SECURE",
        "vault_connected": vault_ok,
    })


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
        logger.error("DB error: %s", e)
        return jsonify({"error": "Database unavailable"}), 503  # nu expunam detalii


@app.route("/send-email")
def send_email():
    """Cheie SendGrid preluata din Vault."""
    api_key = read_secret("integrations/sendgrid", "api_key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "personalizations": [{"to": [{"email": "user@example.com"}]}],
        "from": {"email": "noreply@company.com"},
        "subject": "Test",
        "content": [{"type": "text/plain", "value": "Hello!"}],
    }
    r = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        json=payload,
        headers=headers,
        timeout=10,
    )
    return jsonify({"status": r.status_code})


if __name__ == "__main__":
    # Debug OFF in productie
    app.run(host="0.0.0.0", port=5000, debug=False)
