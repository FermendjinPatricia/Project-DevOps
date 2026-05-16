# ── Build stage ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage (imagine minimala) ─────────────────────────
FROM python:3.12-slim

# Utilizator non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copiaza dependintele din builder
COPY --from=builder /install /usr/local

# Copiaza codul aplicatiei
COPY app.py .

# Permisiuni
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Gunicorn in productie (nu Flask dev server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", \
     "--timeout", "30", "--access-logfile", "-", "app:app"]
