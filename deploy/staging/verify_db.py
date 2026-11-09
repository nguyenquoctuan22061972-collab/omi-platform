#!/usr/bin/env python3
"""AFFOS staging DATABASE verifier (Milestone 2, TASK 3). READ-MOSTLY — the one write it does (a
cost.call INSERT as affos_service) is wrapped in a transaction and ROLLED BACK, so it leaves no trace.

Run ON the staging host after migrations 0001–0005 are applied. Connects with two URLs from the env:
  * AFFOS_OWNER_URL   — postgresql://affos_owner:...@host:5432/<db>   (schema/role/grant reads)
  * AFFOS_SERVICE_URL — postgresql://affos_service:...@host:5432/<db> (live least-privilege matrix)
It NEVER prints a URL or password. Each check prints PASS/FAIL; exit code 0 iff every check PASSed.

Verifies (maps to the Milestone-2 acceptance criteria):
  - PostgreSQL 16; 23 tables; RLS enabled on all; ux_*_src unique indexes; audit_logs policies.
  - affos_service: NOT superuser, NOT BYPASSRLS, member of `authenticated` but NOT `service_role`;
    grants = SELECT+INSERT on audit_logs, SELECT-only on financial tables.
  - LIVE matrix as affos_service: INSERT audit_logs ALLOW; UPDATE/DELETE audit_logs DENY (42501);
    INSERT financial DENY (42501); CREATE TABLE (DDL) DENY (42501).
"""
import os
import sys

try:
    import psycopg
except ImportError:
    print("FAIL: psycopg (v3) not installed on the operator host", file=sys.stderr)
    sys.exit(2)

FINANCIAL = ("revenue", "commissions", "conversion_events", "expenses", "click_events")
EXPECT_TABLES = 23
results = []  # (name, ok, detail)


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def _sqlstate(exc):
    return getattr(exc, "sqlstate", None)


def verify_reads(owner_url):
    with psycopg.connect(owner_url) as c:
        cur = c.cursor()
        cur.execute("SHOW server_version")
        ver = cur.fetchone()[0]
        check("PostgreSQL 16", ver.split(".")[0] == "16", f"server_version={ver}")

        cur.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
        n = cur.fetchone()[0]
        check(f"{EXPECT_TABLES} tables in public", n == EXPECT_TABLES, f"found={n}")

        cur.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace ns ON ns.oid=c.relnamespace "
                    "WHERE ns.nspname='public' AND c.relkind='r' AND c.relrowsecurity")
        rls = cur.fetchone()[0]
        check("RLS enabled on all tables", rls == n, f"rls_enabled={rls}/{n}")

        cur.execute("SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'ux_%_src'")
        ux = cur.fetchone()[0]
        check("ux_*_src unique indexes (dedupe)", ux == 3, f"found={ux}/3")

        cur.execute("SELECT string_agg(polname,',' ORDER BY polname) FROM pg_policy p "
                    "JOIN pg_class c ON c.oid=p.polrelid WHERE c.relname='audit_logs'")
        pols = cur.fetchone()[0] or ""
        check("audit_logs policies (read_auth + ins_service)",
              "audit_logs_ins_service" in pols and "audit_logs_read_auth" in pols, pols)

        cur.execute("SELECT rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname='affos_service'")
        row = cur.fetchone()
        check("affos_service not super / not bypassrls",
              row is not None and not row[0] and not row[1], f"super={row[0]} bypassrls={row[1]}" if row else "missing")

        cur.execute("SELECT string_agg(r.rolname,',') FROM pg_auth_members m "
                    "JOIN pg_roles r ON r.oid=m.roleid JOIN pg_roles s ON s.oid=m.member "
                    "WHERE s.rolname='affos_service'")
        members = cur.fetchone()[0] or ""
        check("affos_service in authenticated, NOT service_role",
              "authenticated" in members and "service_role" not in members, members)

        cur.execute("SELECT privilege_type FROM information_schema.role_table_grants "
                    "WHERE grantee='affos_service' AND table_name='audit_logs' ORDER BY 1")
        al = sorted(r[0] for r in cur.fetchall())
        check("affos_service audit_logs grants = SELECT,INSERT", al == ["INSERT", "SELECT"], ",".join(al))

        bad = []
        for t in FINANCIAL:
            cur.execute("SELECT string_agg(privilege_type,',' ORDER BY privilege_type) "
                        "FROM information_schema.role_table_grants "
                        "WHERE grantee='affos_service' AND table_name=%s", (t,))
            p = cur.fetchone()[0] or ""
            if p != "SELECT":
                bad.append(f"{t}={p or 'none'}")
        check("financial tables SELECT-only for affos_service", not bad, "; ".join(bad) or "all SELECT")


def _expect_deny(cur, conn, label, sql):
    """Run a statement that MUST be denied; PASS iff it raises insufficient_privilege (42501)."""
    try:
        cur.execute(sql)
        conn.rollback()
        check(label + " DENY", False, "UNEXPECTEDLY ALLOWED")
    except psycopg.errors.InsufficientPrivilege as exc:
        conn.rollback()
        check(label + " DENY", True, f"SQLSTATE={_sqlstate(exc)}")
    except Exception as exc:                       # any other error: report, do not pass silently
        conn.rollback()
        check(label + " DENY", False, f"unexpected {type(exc).__name__} SQLSTATE={_sqlstate(exc)}")


def verify_live_matrix(service_url):
    with psycopg.connect(service_url) as c:
        cur = c.cursor()
        cur.execute("SELECT current_user, (SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user)")
        who, bypass = cur.fetchone()
        check("runtime connects as affos_service (no bypassrls)",
              who == "affos_service" and not bypass, f"user={who} bypassrls={bypass}")

        # ALLOW: INSERT a cost.call row, then ROLLBACK (verification leaves no data behind).
        try:
            cur.execute("INSERT INTO audit_logs(event,actor,target,meta) "
                        "VALUES ('cost.call','verify','V0','{}'::jsonb)")
            c.rollback()
            check("INSERT audit_logs (cost.call) ALLOW", True, "ok (rolled back)")
        except Exception as exc:
            c.rollback()
            check("INSERT audit_logs (cost.call) ALLOW", False, f"{type(exc).__name__} SQLSTATE={_sqlstate(exc)}")

        _expect_deny(cur, c, "UPDATE audit_logs", "UPDATE audit_logs SET actor='x'")
        _expect_deny(cur, c, "DELETE audit_logs", "DELETE FROM audit_logs")
        _expect_deny(cur, c, "INSERT revenue (financial)", "INSERT INTO revenue(source,amount) VALUES ('x',1)")
        _expect_deny(cur, c, "CREATE TABLE (DDL)", "CREATE TABLE _verify_ddl(x int)")


def main():
    owner = os.environ.get("AFFOS_OWNER_URL")
    svc = os.environ.get("AFFOS_SERVICE_URL")
    if not owner or not svc:
        print("FAIL: set AFFOS_OWNER_URL and AFFOS_SERVICE_URL (never printed)", file=sys.stderr)
        return 2
    try:
        verify_reads(owner)
        verify_live_matrix(svc)
    except Exception as exc:                        # connection/other fatal error (URL never printed)
        print(f"FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    width = max(len(n) for n, _, _ in results)
    passed = 0
    for name, ok, detail in results:
        tag = "PASS" if ok else "FAIL"
        passed += ok
        print(f"[{tag}] {name.ljust(width)}  {detail}")
    print(f"\n{passed}/{len(results)} checks PASSED")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
