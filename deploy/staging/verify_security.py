#!/usr/bin/env python3
"""AFFOS STATIC SECURITY verifier (Milestone 2, TASK 3). Reads repo config only — no DB, no network.
Run anywhere. Prints PASS/FAIL per check; exit 0 iff all PASS. Complements the LIVE DB matrix in
deploy/staging/verify_db.py (which needs a running Postgres).

Checks: staging Postgres has no published host port; the runtime connects as affos_service (not
owner/superuser); n8n has no DB credentials; roles.sql keeps affos_service off service_role / BYPASSRLS /
schema-CREATE; and no non-placeholder secret value is committed under deploy/.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DEPLOY = os.path.join(REPO, "deploy")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def verify_compose():
    import yaml
    d = yaml.safe_load(read(os.path.join(DEPLOY, "docker-compose.staging.yml")))
    svcs = d.get("services", {})
    published = {s: v.get("ports") for s, v in svcs.items() if v.get("ports")}
    check("no published host ports in staging compose", not published, str(published or "none"))

    affos = svcs.get("affos-runtime", {})
    dburl = (affos.get("environment", {}) or {}).get("DATABASE_URL", "")
    # role = the userinfo between "://" and "@" (so the host "postgres:5432" is never mistaken for a role)
    m = re.search(r"://([^@/]+)@", dburl)
    role = (m.group(1).split(":")[0] if m else "")
    check("runtime DATABASE_URL uses affos_service", role == "affos_service", role or "missing")
    check("runtime DB role is NOT owner/superuser",
          role not in ("affos_owner", "affos_bootstrap", "postgres", "supabase_admin"), role or "missing")

    check("no n8n service in staging compose (no DB creds to n8n)", "n8n" not in svcs, ",".join(svcs))
    # defensive: no service other than affos-runtime carries a DATABASE_URL
    leaks = [s for s, v in svcs.items() if s != "affos-runtime" and "DATABASE_URL" in (v.get("environment", {}) or {})]
    check("only affos-runtime holds DATABASE_URL", not leaks, ",".join(leaks) or "none")


def verify_roles_sql():
    raw = read(os.path.join(DEPLOY, "postgres", "roles.sql"))
    # strip SQL line comments so a "-- intentionally NO grant ..." note can't trip a substring check
    sql = "\n".join(re.sub(r"--.*$", "", line) for line in raw.splitlines()).lower()
    check("affos_service NOT granted service_role (effective SQL)",
          "grant service_role to affos_service" not in sql, "")
    check("affos_service NOT given bypassrls (effective SQL)",
          not re.search(r"affos_service[^;]*bypassrls", sql), "")
    check("schema CREATE revoked from affos_service",
          re.search(r"revoke\s+create\s+on\s+schema\s+public\s+from[^;]*affos_service", sql) is not None, "")
    check("affos_service granted authenticated (read) only",
          "grant authenticated to affos_service" in sql, "")


def verify_no_committed_secret():
    # A committed secret is a LITERAL value: key = <contiguous high-entropy token>, no spaces, no shell
    # expansion. Placeholders (${VAR}, ${VAR:?msg}), blank example values, and prose (which has spaces)
    # are excluded by requiring the value to be a pure [A-Za-z0-9+/_-] token of 12+ chars to end-of-line.
    secret_kv = re.compile(
        r'(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*["\']?([A-Za-z0-9+/_\-]{12,})["\']?\s*$')
    offenders = []
    for root, _dirs, files in os.walk(DEPLOY):
        for fn in files:
            if not fn.endswith((".yml", ".yaml", ".env", ".example", ".sh")):   # skip .md docs (name secrets, not values)
                continue
            p = os.path.join(root, fn)
            for i, line in enumerate(read(p).splitlines(), 1):
                m = secret_kv.search(line.strip())
                if not m:
                    continue
                val = m.group(2)
                if any(tok in val.lower() for tok in ("example", "change", "placeholder", "your", "xxxx")):
                    continue
                offenders.append(f"{os.path.relpath(p, REPO)}:{i}")
    check("no literal secret value committed under deploy/", not offenders,
          "; ".join(offenders[:5]) or "clean")


def main():
    try:
        verify_compose()
        verify_roles_sql()
        verify_no_committed_secret()
    except Exception as exc:
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    width = max(len(n) for n, _, _ in results)
    passed = 0
    for name, ok, detail in results:
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name.ljust(width)}  {detail}")
    print(f"\n{passed}/{len(results)} checks PASSED")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
