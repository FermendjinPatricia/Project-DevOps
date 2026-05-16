<div align="center">

# Secrets Management with HashiCorp Vault

**DevOps Security & Compliance Project**

![Vault](https://img.shields.io/badge/HashiCorp_Vault-1.17-black?style=for-the-badge&logo=vault)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask)

*Replacing hard-coded credentials with a production-grade secrets manager*

</div>

---

## Overview

This project demonstrates how to eliminate one of the most common and dangerous security anti-patterns in software development: **hard-coded credentials in source code**.

The solution replaces all hard-coded secrets in a sample Flask application with **HashiCorp Vault** — the industry-standard secrets management tool used by companies like GitHub, Netflix, and Shopify. The result is a fully documented before/after architecture with measurable security improvements.

---

## The Problem — Before

### What the code looked like

```python
# before/app.py — everything exposed in plain text

DB_HOST               = "prod-db.internal.company.com"
DB_PASSWORD           = "SuperSecretP@ssw0rd123!"
AWS_ACCESS_KEY_ID     = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_SECRET_KEY     = "sk_live_51HZn2KJK9..."
SENDGRID_API_KEY      = "SG.abc123xyz789..."
JWT_SECRET            = "my-super-secret-jwt-key-do-not-share"
```

Any developer with read access to the repository could see production credentials. These also end up in Git history permanently — even after deletion.

### Vulnerabilities identified

| Vulnerability | Severity | Impact |
|--------------|----------|--------|
| Credentials visible in Git history | CRITICAL | Anyone with repo access owns production |
| No secret rotation | CRITICAL | A leaked credential is compromised forever |
| No audit trail | HIGH | Impossible to detect unauthorized access |
| Shared dev/prod credentials | HIGH | Dev environment breach = prod breach |
| Debug mode enabled in production | HIGH | Internal stack traces exposed to users |
| Detailed error messages | MEDIUM | Information disclosure to attackers |
| No least privilege enforcement | MEDIUM | Every service can access everything |

---

## The Solution — After

### What the code looks like now

```python
# after/app/app.py — zero secrets in code

VAULT_ADDR      = os.environ["VAULT_ADDR"]       # non-sensitive, just an address
VAULT_ROLE_ID   = os.environ["VAULT_ROLE_ID"]    # AppRole identity (not a secret)
VAULT_SECRET_ID = os.environ["VAULT_SECRET_ID"]  # injected by CI/CD, TTL-limited

def get_db_connection():
    # credentials fetched at runtime — never stored anywhere in code
    creds = vault.secrets.kv.v2.read_secret_version(path="database/postgres")
    return psycopg2.connect(
        host=creds["host"],
        user=creds["username"],
        password=creds["password"],
        sslmode="require"
    )
```

No passwords. No API keys. No secrets of any kind in the codebase.

---

## Architecture

### Before

```
┌──────────────────────────────────────────┐
│             Git Repository               │
│                                          │
│   app.py                                 │
│   ├── DB_PASSWORD  = "SuperSecret..."    │
│   ├── AWS_SECRET   = "wJalrXUtn..."      │
│   └── JWT_SECRET   = "my-secret-key"     │
│                                          │
│   Visible to: all developers, CI/CD,     │
│   anyone who ever cloned the repo        │
└──────────────────┬───────────────────────┘
                   │
                   v
         Flask App (debug: ON)
         ├── PostgreSQL (plaintext password)
         └── AWS / SendGrid (keys exposed)
```

### After

```
┌──────────────────────────────────────────┐
│             Git Repository               │
│                                          │
│   app.py  ──  zero secrets               │
│   .gitignore  ──  .env.app, secrets/     │
└──────────────────┬───────────────────────┘
                   │ deploy
                   v
┌──────────────────────────────────────────┐
│            CI/CD Pipeline                │
│                                          │
│   Injects only:                          │
│   - VAULT_ROLE_ID   (non-secret)         │
│   - VAULT_SECRET_ID (short TTL)          │
└──────────────────┬───────────────────────┘
                   │ AppRole authentication
                   v
┌──────────────────────────────────────────┐
│           HashiCorp Vault                │
│                                          │
│   secret/database/postgres               │
│   secret/aws/s3-credentials              │
│   secret/integrations/sendgrid           │
│   secret/app/jwt                         │
│                                          │
│   - AppRole Auth  (machine identity)     │
│   - Policies      (least privilege)      │
│   - Audit Log     (every access logged)  │
│   - Token TTL     (1h, auto-expires)     │
└──────────────────┬───────────────────────┘
                   │ secrets at runtime
                   v
         Flask App (debug: OFF, non-root)
         ├── PostgreSQL (TLS required)
         └── AWS / SendGrid (keys never touch disk)
```

---

## Running the Project

### Prerequisites

- Docker Desktop

### Step 1 — Start the infrastructure

```bash
docker compose up vault postgres -d
```

### Step 2 — Store secrets in Vault

```bash
docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root vault \
  vault kv put secret/database/postgres \
  host="prod-db.internal" port="5432" \
  dbname="production_db" username="app_user" password="SecurePass123!"

docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=root vault \
  vault auth enable approle
```

### Step 3 — Start the application

```bash
docker compose up flask-app -d
```

All containers healthy:

![Docker containers running](screenshots/docker-containers.png)

### Step 4 — Verify the Vault connection

```bash
curl http://localhost:5000/health
```

```json
{
  "status": "ok",
  "vault_connected": true,
  "version": "2.0-SECURE"
}
```

![Health check response](screenshots/health-check.png)

### Step 5 — Explore the Vault UI

Open `http://localhost:8200` in your browser (token: `root`) to browse the secrets engine, policies, and access logs.

![Vault dashboard](screenshots/vault-dashboard.png)

---

## Security Improvements Summary

| Criteria | Before | After |
|----------|--------|-------|
| Secrets in source code | Yes | No |
| Secrets in Git history | Yes | No |
| Secret rotation | Manual, error-prone | Single command, instant |
| Audit trail | None | Every read/write logged |
| Least privilege | Not enforced | Policy-based, deny by default |
| Encryption in transit | Partial | TLS on all connections |
| Application identity | None | AppRole with expiring tokens |
| Debug mode in production | Enabled | Disabled |
| Container privileges | Running as root | Dedicated non-root user |

---

## Key Concepts

**KV Secrets Engine v2** — Vault's key-value store with full versioning. Previous versions of secrets are retained and recoverable, enabling safe rotation without data loss.

**AppRole Authentication** — The standard method for machine-to-machine authentication in Vault. A `role_id` identifies the application (like a username), while a `secret_id` proves its identity (like a password). Secret IDs have a configurable TTL, so even if one is compromised, it expires automatically.

**Policies and Least Privilege** — Every Vault token is bound to a policy that defines exactly which paths it can read or write. Anything not explicitly allowed is denied. The Flask app can only read its own secrets — nothing else.

**Token TTL** — Application tokens expire after one hour. This limits the damage window of any credential theft: a stolen token becomes useless within the hour without any manual intervention.

---

*HashiCorp Vault 1.17 · Flask 3.0 · PostgreSQL 16 · Docker Compose · Python 3.12*
