# AFFOS production runtime (SPRINT 01). Minimal, additive — does NOT touch the omi or
# n8n compose stacks. Build context = the AFFOS/ directory.
FROM python:3.11-slim

WORKDIR /app/AFFOS
COPY . /app/AFFOS

# AFFOS core is stdlib-only. psycopg is needed ONLY for the LIVE Postgres path; installing
# it here is harmless in DRY-RUN (driver simply available but unused).
RUN pip install --no-cache-dir 'psycopg[binary]==3.*'

ENV AFFOS_RUNTIME_PORT=8099
EXPOSE 8099

# Health endpoint derives mode from env and does NOT open a DB connection.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8099/health',timeout=4).status==200 else 1)" || exit 1

CMD ["python3", "runtime/server.py"]
