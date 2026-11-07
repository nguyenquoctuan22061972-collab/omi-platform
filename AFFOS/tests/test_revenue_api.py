"""QA — AFFOS Revenue Ingestion API (S2/S3). Offline, no DB, no network, no creds.

Covers: authN/authZ (401/403), provider validation (400), Impact OFF (403), live-without-approval
(424), dry-run stop path (200), request-level idempotency (409), and audit recording. Reuses the
real apps/auth-rbac JWT + RBAC matrix (so `revenue:ingest`/`revenue:read` are exercised end-to-end).
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "..", "apps", "auth-rbac", "src"))

import revenue_api  # noqa: E402
from auth import jwt_util  # noqa: E402

SECRET = "test-secret"
ENV = {"AUTH_SECRET": SECRET}                       # DRY-RUN (no DATABASE_URL)
WINDOW = {"start": "2026-10-01", "end": "2026-10-06"}


def _tok(roles):
    return "Bearer " + jwt_util.encode({"sub": "svc-1", "roles": roles}, SECRET)


def _body(**kw):
    import json
    base = {"provider": "awin", "mode": "dry-run", "window": WINDOW}
    base.update(kw)
    return json.dumps(base).encode()


class TestRevenueIngest(unittest.TestCase):
    def setUp(self):
        self.idem = {}
        self.audit = []

    def _ingest(self, headers, body):
        return revenue_api.handle_ingest(body, headers, ENV,
                                         idem_store=self.idem, audit_sink=self.audit)

    def test_missing_token_401(self):
        code, r = self._ingest({}, _body())
        self.assertEqual(code, 401)

    def test_insufficient_permission_403(self):
        code, r = self._ingest({"Authorization": _tok(["Viewer"])}, _body())
        self.assertEqual(code, 403)
        self.assertIn("revenue:ingest", r["error"])

    def test_admin_dry_run_stops_not_verified(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body())
        self.assertEqual(code, 200)
        self.assertEqual(r["status"], "stopped")             # approved=false -> run_ingestion STOPs
        self.assertEqual(r["repository_mode"], "DRY-RUN")
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")
        self.assertEqual(len(self.audit), 1)                 # attempt audited

    def test_impact_disabled_403(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body(provider="impact"))
        self.assertEqual(code, 403)
        self.assertIn("Impact OFF", r["error"])

    def test_bad_provider_400(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body(provider="nope"))
        self.assertEqual(code, 400)

    def test_live_without_approval_424(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])},
                               _body(mode="live", approved=False))
        self.assertEqual(code, 424)

    def test_bad_window_400(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])},
                               _body(window={"start": "", "end": ""}))
        self.assertEqual(code, 400)

    def test_idempotency_replay_409(self):
        hdr = {"Authorization": _tok(["Admin"]), "Idempotency-Key": "abc-123"}
        c1, _ = self._ingest(hdr, _body())
        c2, r2 = self._ingest(hdr, _body())
        self.assertEqual(c1, 200)
        self.assertEqual(c2, 409)
        self.assertEqual(r2["idempotency_key"], "abc-123")


class TestRevenueReport(unittest.TestCase):
    def test_report_requires_auth(self):
        code, _ = revenue_api.handle_report({}, {}, ENV)
        self.assertEqual(code, 401)

    def test_report_dry_run_stub(self):
        code, r = revenue_api.handle_report(
            {"provider": "awin"}, {"Authorization": _tok(["Manager"])}, ENV)
        self.assertEqual(code, 200)
        self.assertEqual(r["repository_mode"], "DRY-RUN")
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")
        self.assertIsNone(r["revenue"])                      # no fabricated numbers in dry-run


if __name__ == "__main__":
    unittest.main()
