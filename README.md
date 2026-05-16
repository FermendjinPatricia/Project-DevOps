# Secrets Management cu HashiCorp Vault
### Proiect DevOps Security & Compliance

---

## 📋 Cuprins

1. [Problema — Before](#problema--before)
2. [Solutia — After](#solutia--after)
3. [Arhitectura Before/After](#arhitectura-beforeafter)
4. [Imbunatatiri de Securitate](#imbunatatiri-de-securitate)
5. [Structura Proiectului](#structura-proiectului)
6. [Cum Rulezi](#cum-rulezi)
7. [Concepte Cheie Vault](#concepte-cheie-vault)
8. [Threat Model](#threat-model)

---

## Problema — Before

### Cod vulnerabil (`before/app.py`)

Aplicatia initiala stocheaza toate credentialele **direct in codul sursa**:

```python
# ⚠️ VULNERABILITATE CRITICA
DB_PASSWORD           = "SuperSecretP@ssw0rd123!"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_SECRET_KEY     = "sk_live_51HZn2KJK9..."
SENDGRID_API_KEY      = "SG.abc123xyz789..."
JWT_SECRET            = "my-super-secret-jwt-key-do-not-share"
```

### Riscuri identificate

| # | Vulnerabilitate | Severitate | Impact |
|---|----------------|------------|--------|
| 1 | Credentiale in Git history | 🔴 CRITICA | Oricine cu acces la repo le vede |
| 2 | Rotatia manuala a secretelor | 🔴 CRITICA | Credentiale expirate / compromise |
| 3 | Niciun audit trail | 🟠 INALTA | Imposibil de detectat accesul neautorizat |
| 4 | Aceleasi credentiale dev/prod | 🟠 INALTA | Breach in dev = breach in prod |
| 5 | Debug mode ON in productie | 🟠 INALTA | Expune stack traces cu detalii interne |
| 6 | Erori cu detalii tehnice | 🟡 MEDIE | Information disclosure |
| 7 | Niciun principiu least privilege | 🟡 MEDIE | Orice serviciu accesa orice |

---

## Solutia — After

### Arhitectura securizata (`after/app/app.py`)

```
Nicio credentiala in cod.
Nicio credentiala in variabile de mediu (cu exceptia AppRole IDs).
Toate secretele: preluate la runtime din HashiCorp Vault.
```

**Fluxul de autentificare AppRole:**

```
1. App porneste
2. App trimite role_id + secret_id catre Vault
3. Vault valideaza si returneaza un token cu TTL de 1h
4. App foloseste token-ul pentru a citi secretele
5. La expirare, token-ul se reinnoieste automat
```

---

## Arhitectura Before/After

### BEFORE — Arhitectura vulnerabila

```
┌─────────────────────────────────────────────┐
│                Git Repository               │
│                                             │
│  app.py                                     │
│  ├── DB_PASSWORD = "SuperSecret123!"   ⚠️   │
│  ├── AWS_SECRET  = "wJalrXUtn..."      ⚠️   │
│  └── JWT_SECRET  = "my-secret-key"     ⚠️   │
│                                             │
│  Vizibil pentru: devs, CI/CD, auditori,    │
│  atacatori cu acces la repo                │
└──────────────────┬──────────────────────────┘
                   │  deploy
                   ▼
┌─────────────────────────────────────────────┐
│            Flask Application                │
│                                             │
│  Credentiale in memorie (plain text)        │
│  Debug mode: ON  ⚠️                         │
│  Erori detaliate expuse  ⚠️                 │
└──────┬──────────────┬───────────────────────┘
       │              │
       ▼              ▼
  PostgreSQL      AWS / SendGrid
  (parola clara)  (chei expuse)
```

### AFTER — Arhitectura securizata

```
┌─────────────────────────────────────────────┐
│                Git Repository               │
│                                             │
│  app.py — ZERO secrete  ✅                  │
│  docker-compose.yml — ZERO secrete  ✅      │
│  .gitignore: .env.app, secrets/  ✅         │
└─────────────────────────────────────────────┘
                   │  deploy
                   ▼
┌─────────────────────────────────────────────┐
│            CI/CD Pipeline                   │
│                                             │
│  Injecteaza doar:                           │
│  - VAULT_ROLE_ID   (non-secret)             │
│  - VAULT_SECRET_ID (TTL scurt, rotit)       │
└──────────────────┬──────────────────────────┘
                   │  env vars
                   ▼
┌─────────────────────────────────────────────┐
│            Flask Application                │
│                                             │
│  1. Autentificare AppRole → Vault Token     │
│  2. Token TTL: 1h (auto-renew)             │
│  3. Citire secrete la runtime               │
│  Debug: OFF  ✅                             │
│  User: non-root  ✅                         │
└──────┬───────────────────────────────────────┘
       │  citeste secrete
       ▼
┌─────────────────────────────────────────────┐
│           HashiCorp Vault                   │
│                                             │
│  KV Secrets Engine v2                       │
│  ├── secret/database/postgres               │
│  ├── secret/aws/s3-credentials              │
│  ├── secret/integrations/sendgrid           │
│  └── secret/app/jwt                         │
│                                             │
│  AppRole Auth  ✅                           │
│  Policies (least privilege)  ✅             │
│  Audit Log  ✅                              │
│  TLS  ✅                                    │
└──────┬──────────────────────────────────────┘
       │
       ├──▶ PostgreSQL (parola rotita automat)
       ├──▶ AWS (chei cu TTL scurt)
       └──▶ SendGrid / Stripe (chei externe)
```

---

## Imbunatatiri de Securitate

### 1. Eliminarea credentialelor din cod

| Aspect | Before | After |
|--------|--------|-------|
| Credentiale in Git | ✅ (problema) | ❌ Eliminate |
| Credentiale in logs | ✅ (risc) | ❌ Nu apar niciodata |
| Credentiale in env vars | N/A | Doar IDs non-sensitive |

### 2. Rotatie automata a secretelor

```bash
# Rotire parola DB — un singur command, zero downtime
vault kv put secret/database/postgres password="$(openssl rand -base64 32)"

# Aplicatia preia noua parola la urmatorul apel
# Nu e necesar restart!
```

### 3. Audit Trail complet

```json
// /vault/logs/audit.log — fiecare acces este inregistrat
{
  "time": "2024-01-15T10:30:00Z",
  "type": "request",
  "auth": {
    "accessor": "hmac-sha256:...",
    "display_name": "approle:flask-app",
    "policies": ["app-policy"]
  },
  "request": {
    "operation": "read",
    "path": "secret/data/database/postgres"
  }
}
```

### 4. Principiul Least Privilege

```hcl
# Policy app-policy — acces MINIM necesar
path "secret/data/database/postgres" {
  capabilities = ["read"]           # Doar citire
}

path "secret/data/integrations/*" {
  capabilities = ["read"]           # Doar integrari specifice
}

path "*" {
  capabilities = ["deny"]           # Orice altceva: REFUZAT
}
```

### 5. Comparatie rezumat securitate

| Criteriu | Before | After | Imbunatatire |
|----------|--------|-------|--------------|
| Secrete in repo | DA ⚠️ | NU ✅ | Eliminat attack vector principal |
| Rotatie secrete | Manuala ⚠️ | Automata ✅ | MTTR redus de la ore la secunde |
| Audit access | Niciunul ⚠️ | Complet ✅ | Detectie intruziuni posibila |
| Least privilege | Niciunul ⚠️ | Enforced ✅ | Blast radius minimizat |
| Criptare in tranzit | Partial ⚠️ | TLS везде ✅ | Zero plaintext |
| Autentificare app | Implicita ⚠️ | AppRole ✅ | Identity-based access |
| Debug in prod | ON ⚠️ | OFF ✅ | Info disclosure eliminat |
| User container | root ⚠️ | non-root ✅ | Privilege escalation dificil |

---

## Structura Proiectului

```
secrets-management-project/
│
├── before/
│   └── app.py                    # ⚠️  Aplicatie vulnerabila (demo)
│
├── after/
│   ├── app/
│   │   ├── app.py                # ✅  Aplicatie securizata
│   │   ├── Dockerfile            # Multi-stage, non-root user
│   │   └── requirements.txt
│   └── vault-config/
│       └── vault.hcl             # Configuratie Vault productie
│
├── scripts/
│   ├── vault-init.sh             # Initializare Vault + secrete
│   └── init-db.sql               # Schema demo PostgreSQL
│
├── docker-compose.yml            # Stack complet
├── .gitignore                    # Exclude .env.app, secrets/
└── README.md                     # Aceasta documentatie
```

---

## Cum Rulezi

### Prerequisite
- Docker + Docker Compose
- `openssl` (pentru generarea secretelor)

### Pasii

```bash
# 1. Cloneaza / copiaza proiectul
cd secrets-management-project

# 2. Creeaza directorul pentru Docker secrets
mkdir -p secrets
openssl rand -base64 32 > secrets/db_password.txt

# 3. Porneste Vault si PostgreSQL
docker compose up vault postgres -d

# 4. Initializeaza Vault (ruleaza o singura data)
bash scripts/vault-init.sh
# Genereaza automat fisierul .env.app

# 5. Porneste aplicatia
docker compose up flask-app -d

# 6. Testeaza
curl http://localhost:5000/health
curl http://localhost:5000/users

# 7. Acceseaza Vault UI
open http://localhost:8200  # Token: root (doar dev!)
```

### Verificare audit log

```bash
docker exec vault cat /vault/logs/audit.log | python3 -m json.tool
```

---

## Concepte Cheie Vault

### KV Secrets Engine v2
Motor de stocare pentru perechi cheie-valoare. v2 adauga **versionare** — poti recupera versiuni anterioare ale unui secret.

### AppRole Authentication
Metoda de autentificare machine-to-machine:
- `role_id` — identifica aplicatia (public, ca un username)
- `secret_id` — valideaza identitatea (privat, ca o parola, cu TTL)

### Policies
Documente HCL care definesc **ce poate face** un token dupa autentificare. Principiu: deny implicit pe orice cale nedefinita.

### Lease & Renewal
Orice secret din Vault are un **lease** (TTL). La expirare, secretul poate fi reinnoit sau revocat. Permite rotatie automata fara downtime.

---

## Threat Model

### Scenarii acoperite

| Scenariu | Before | After |
|----------|--------|-------|
| Developer rau intenționat vede repo | Acces complet la toate credentialele | Nicio credentiala in repo |
| CI/CD pipeline compromis | Toate secretele expuse | Doar role_id/secret_id cu TTL scurt |
| Container spart | Secretele in env vars | Token Vault cu acces minim, TTL 1h |
| Laptop dev compromis | Credentiale prod expuse | Nicio credentiala pe laptopuri |
| Angajat paraseste compania | Trebuie rotit manual, risc uitat | Revocare token imediata din Vault |

### Limitari cunoscute ale solutiei

1. **Vault Single Point of Failure** — Solutie: Vault HA cu Raft sau cloud-managed (HCP Vault)
2. **Bootstrap problem** — `secret_id` trebuie injectat initial; solutie: Vault Agent sau Kubernetes Auth
3. **In-memory caching** — Token-ul e in memorie; solutie: memory encryption, seccomp profiles

---

*Proiect realizat pentru cursul DevOps Security & Compliance*
*Stack: HashiCorp Vault 1.17 · Flask 3.0 · PostgreSQL 16 · Docker Compose*
