# vault.hcl — Configuratie Vault pentru productie
# (In dev-mode acest fisier e ignorat, dar e util ca referinta)

storage "raft" {
  path    = "/vault/data"
  node_id = "vault-node-1"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/tls/vault.crt"
  tls_key_file  = "/vault/tls/vault.key"
}

api_addr     = "https://vault.internal:8200"
cluster_addr = "https://vault.internal:8201"

# UI activata pentru demonstratie
ui = true

# Audit log (obligatoriu in productie)
# Se configureaza dupa unseal:
# vault audit enable file file_path=/vault/logs/audit.log

# Lease-uri implicite
default_lease_ttl = "1h"
max_lease_ttl     = "24h"
