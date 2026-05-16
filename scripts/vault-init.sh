#!/usr/bin/env bash
# =============================================================
# vault-init.sh — Initializare Vault pentru proiect
# Ruleaza o singura data dupa primul start al Vault-ului
# =============================================================
set -euo pipefail

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="root"   # token dev-mode; in productie foloseste unseal keys

echo "Vault Initialization — Secrets Management"


# ── 1. Activeaza KV Secrets Engine v2 ──────────────────────
echo "Activare KV Secrets Engine v2..."
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "  (deja activ)"

# ── 2. Scrie secretele aplicatiei ──────────────────────────
echo "Scriere secrete in Vault..."

vault kv put secret/database/postgres \
  host="prod-db.internal.company.com" \
  port="5432" \
  dbname="production_db" \
  username="app_user" \
  password="$(openssl rand -base64 32)"

vault kv put secret/aws/s3-credentials \
  access_key_id="AKIAIOSFODNN7EXAMPLE" \
  secret_access_key="$(openssl rand -base64 40)" \
  region="eu-west-1"

vault kv put secret/integrations/sendgrid \
  api_key="SG.$(openssl rand -hex 32)"

vault kv put secret/integrations/stripe \
  secret_key="sk_live_$(openssl rand -hex 24)"

vault kv put secret/app/jwt \
  secret="$(openssl rand -base64 64)"

echo "Secrete scrise cu succes"

# ── 3. Creeaza Policy pentru aplicatie ─────────────────────
echo ""
echo "Creare policy 'app-policy'..."

vault policy write app-policy - <<'EOF'
# Policy pentru aplicatia Flask
# Principiu: least privilege — acces DOAR la ce e necesar

# Citire credentiale DB
path "secret/data/database/postgres" {
  capabilities = ["read"]
}

# Citire credentiale AWS
path "secret/data/aws/s3-credentials" {
  capabilities = ["read"]
}

# Citire chei API externe
path "secret/data/integrations/*" {
  capabilities = ["read"]
}

# Citire JWT secret
path "secret/data/app/jwt" {
  capabilities = ["read"]
}

# Interzis orice altceva
path "*" {
  capabilities = ["deny"]
}
EOF

echo "Policy creata"

# ── 4. Configureaza AppRole Authentication ─────────────────
echo ""
echo "Configurare AppRole Auth..."

vault auth enable approle 2>/dev/null || echo "  (deja activ)"

vault write auth/approle/role/flask-app \
  token_policies="app-policy" \
  token_ttl="1h" \
  token_max_ttl="4h" \
  secret_id_ttl="24h" \
  secret_id_num_uses=0

# Extrage role_id si secret_id
ROLE_ID=$(vault read -field=role_id auth/approle/role/flask-app/role-id)
SECRET_ID=$(vault write -f -field=secret_id auth/approle/role/flask-app/secret-id)

echo "AppRole configurat"

echo "Credentiale AppRole (injecteaza in env):"
echo "VAULT_ROLE_ID   = ${ROLE_ID:0:8}..."
echo "VAULT_SECRET_ID = ${SECRET_ID:0:8}..."


# Salveaza pentru docker-compose
cat > .env.app <<EOF2
VAULT_ADDR=http://vault:8200
VAULT_ROLE_ID=${ROLE_ID}
VAULT_SECRET_ID=${SECRET_ID}
EOF2

echo ""
echo "Credentiale salvate in .env.app"

# ── 5. Audit Log ────────────────────────────────────────────
echo ""
echo "Activare Audit Logging..."
vault audit enable file file_path=/vault/logs/audit.log 2>/dev/null || echo "  (deja activ)"
echo "Audit log activ la /vault/logs/audit.log"

echo "Vault initializat cu succes!"
