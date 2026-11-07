"""QA — AFFOS Revenue Ingestion API (S2/S3 + Phase-3 v2). Offline, no DB, no network, no creds.

Covers: authN/authZ (401/403), validation (400), Impact OFF (403), request size (413), rate limit
(429), server-side approval gate (424 / 200), two-layer idempotency (same body 200 cached / diff 409),
the /approve grant (201 / 403), audit recording, and the report stub. Reuses the real apps/auth-rbac
JWT + RBAC matrix (so revenue:ingest / revenue:read / revenue:approve are exercised end-to-end).
"""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "runtime"))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "..", "apps", "auth-rbac", "src"))

import revenue_api  # noqa: E402
import revenue_store  # noqa: E402
from data_access import Repo  # noqa: E402
from auth import jwt_util  # noqa: E402

SECRET = "test-secret"
ENV = {"AUTH_SECRET": SECRET, "AFFOS_ENVIRONMENT": "production"}   # DRY-RUN (no DATABASE_URL)
WINDOW = {"start": "2026-10-01", "end": "2026-10-06"}
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def _tok(roles):
    return "Bearer " + jwt_util.encode({"sub": "svc-1", "roles": roles}, SECRET)


def _body(**kw):
    base = {"provider": "awin", "mode": "dry-run", "window": WINDOW}
    base.update(kw)
    return json.dumps(base).encode()


def _active_approval(provider="awin"):
    return [{"provider": provider, "environment": "production", "status": "active",
             "window_start": (NOW - timedelta(hours=1)).isoformat(),
             "window_end": (NOW + timedelta(hours=1)).isoformat(),
             "expires_at": (NOW + timedelta(hours=1)).isoformat()}]


class TestRevenueIngest(unittest.TestCase):
    def setUp(self):
        self.idem, self.audit, self.appr, self.rate = {}, [], [], {}

    def _ingest(self, headers, body, **kw):
        return revenue_api.handle_ingest(body, headers, ENV, idem_store=self.idem,
                                         audit_sink=self.audit, approvals=self.appr,
                                         rate_store=self.rate, clock=lambda: 1000.0, now=NOW, **kw)

    def test_missing_token_401(self):
        self.assertEqual(self._ingest({}, _body())[0], 401)

    def test_insufficient_permission_403(self):
        code, r = self._ingest({"Authorization": _tok(["Viewer"])}, _body())
        self.assertEqual(code, 403)
        self.assertIn("revenue:ingest", r["error"])

    def test_admin_dry_run_stops_not_verified(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body())
        self.assertEqual(code, 200)
        self.assertEqual(r["status"], "stopped")
        self.assertEqual(r["real_commerce_proof"], "NOT YET VERIFIED")
        self.assertEqual(len(self.audit), 1)

    def test_no_approved_field_in_body_is_fine(self):
        # body never carries `approved`; dry-run still works.
        code, _ = self._ingest({"Authorization": _tok(["Admin"])},
                               json.dumps({"provider": "awin", "mode": "dry-run", "window": WINDOW}).encode())
        self.assertEqual(code, 200)

    def test_impact_disabled_403(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body(provider="impact"))
        self.assertEqual(code, 403)
        self.assertIn("Impact OFF", r["error"])

    def test_bad_provider_400(self):
        self.assertEqual(self._ingest({"Authorization": _tok(["Admin"])}, _body(provider="nope"))[0], 400)

    def test_bad_window_400(self):
        self.assertEqual(self._ingest({"Authorization": _tok(["Admin"])},
                                      _body(window={"start": "", "end": ""}))[0], 400)

    def test_live_without_approval_424(self):
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body(mode="live"))
        self.assertEqual(code, 424)
        self.assertIn("approval", r["error"])

    def test_live_with_approval_passes_gate_then_stops(self):
        self.appr.extend(_active_approval("awin"))
        code, r = self._ingest({"Authorization": _tok(["Admin"])}, _body(mode="live"))
        self.assertEqual(code, 200)             # gate passed; run stops at transport (no live call)
        self.assertEqual(r["status"], "stopped")

    def test_approval_is_provider_scoped(self):
        self.appr.extend(_active_approval("awin"))   # AWIN approval must not cover anything else
        # impact is blocked earlier anyway; assert AWIN approval alone does not authorize a 2nd provider
        self.assertFalse(revenue_api.is_approved("impact", "production", NOW, self.appr))

    def test_idempotency_same_body_cached_200(self):
        hdr = {"Authorization": _tok(["Admin"]), "Idempotency-Key": "k1"}
        c1, r1 = self._ingest(hdr, _body())
        c2, r2 = self._ingest(hdr, _body())
        self.assertEqual((c1, c2), (200, 200))
        self.assertEqual(r1, r2)                # cached replay, not re-run
        self.assertEqual(len(self.audit), 1)    # second call did not audit a new run

    def test_idempotency_different_body_409(self):
        hdr = {"Authorization": _tok(["Admin"]), "Idempotency-Key": "k1"}
        self._ingest(hdr, _body())
        code, r = self._ingest(hdr, _body(window={"start": "2026-11-01", "end": "2026-11-02"}))
        self.assertEqual(code, 409)

    def test_request_too_large_413(self):
        big = json.dumps({"provider": "awin", "mode": "dry-run", "window": WINDOW,
                          "junk": "x" * (revenue_api.MAX_BODY_BYTES + 10)}).encode()
        self.assertEqual(self._ingest({"Authorization": _tok(["Admin"])}, big)[0], 413)

    def test_rate_limit_429(self):
        hdr = {"Authorization": _tok(["Admin"])}
        codes = [self._ingest(hdr, _body())[0] for _ in range(revenue_api.RATE_LIMIT_PER_MIN + 1)]
        self.assertTrue(all(c == 200 for c in codes[:revenue_api.RATE_LIMIT_PER_MIN]))
        self.assertEqual(codes[-1], 429)


class TestRevenueApprove(unittest.TestCase):
    def _grant(self, headers, body):
        return revenue_api.handle_grant(body, headers, ENV, approvals=[], audit_sink=[], now=NOW)

    def test_grant_requires_approve_permission(self):
        body = json.dumps({"provider": "awin", "window_start": NOW.isoformat(),
                           "window_end": (NOW + timedelta(hours=1)).isoformat(),
                           "expires_at": (NOW + timedelta(hours=1)).isoformat()}).encode()
        self.assertEqual(self._grant({"Authorization": _tok(["Manager"])}, body)[0], 403)

    def test_grant_admin_201(self):
        body = json.dumps({"provider": "awin", "window_start": NOW.isoformat(),
                           "window_end": (NOW + timedelta(hours=1)).isoformat(),
                           "expires_at": (NOW + timedelta(hours=1)).isoformat()}).encode()
        code, r = self._grant({"Authorization": _tok(["Admin"])}, body)
        self.assertEqual(code, 201)
        self.assertEqual(r["provider"], "awin")
        self.assertEqual(r["status"], "active")

    def test_grant_impact_refused_403(self):
        body = json.dumps({"provider": "impact", "window_start": NOW.isoformat(),
                           "window_end": (NOW + timedelta(hours=1)).isoformat(),
                           "expires_at": (NOW + timedelta(hours=1)).isoformat()}).encode()
        self.assertEqual(self._grant({"Authorization": _tok(["Admin"])}, body)[0], 403)


class TestJWTHardening(unittest.TestCase):
    ENV2 = {"AUTH_SECRET": SECRET, "AFFOS_ENVIRONMENT": "production",
            "AFFOS_JWT_ISS": "affos-auth", "AFFOS_JWT_AUD": "revenue"}

    def _tok(self, **extra):
        payload = {"sub": "svc-1", "roles": ["Admin"]}
        payload.update(extra)
        return "Bearer " + jwt_util.encode(payload, SECRET)

    def _ingest(self, hdr):
        return revenue_api.handle_ingest(_body(), hdr, self.ENV2, idem_store={}, audit_sink=[],
                                         approvals=[], rate_store={}, clock=lambda: 1.0, now=NOW)

    def test_valid_issuer_audience_ok(self):
        code, _ = self._ingest({"Authorization": self._tok(iss="affos-auth", aud="revenue")})
        self.assertEqual(code, 200)

    def test_invalid_issuer_401(self):
        code, r = self._ingest({"Authorization": self._tok(iss="evil", aud="revenue")})
        self.assertEqual(code, 401)
        self.assertIn("issuer", r["error"])

    def test_invalid_audience_401(self):
        code, r = self._ingest({"Authorization": self._tok(iss="affos-auth", aud="other")})
        self.assertEqual(code, 401)
        self.assertIn("audience", r["error"])


class TestStoreBacked(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(data_state="DRY_RUN")
        self.store = revenue_store.RevenueStore(self.repo.conn, "?")
        self.store.init_schema(with_commission_unique=False)
        self.rate = {}

    def _ingest(self, body, hdr):
        return revenue_api.handle_ingest(body, hdr, ENV, store=self.store, rate_store=self.rate,
                                         clock=lambda: 1.0, now=NOW)

    def _grant(self):
        body = json.dumps({"provider": "awin", "environment": "production",
                           "window_start": (NOW - timedelta(hours=1)).isoformat(),
                           "window_end": (NOW + timedelta(hours=1)).isoformat(),
                           "expires_at": (NOW + timedelta(hours=1)).isoformat()}).encode()
        return revenue_api.handle_grant(body, {"Authorization": _tok(["Admin"])}, ENV, store=self.store)

    def test_live_requires_store_approval(self):
        code, _ = self._ingest(_body(mode="live"), {"Authorization": _tok(["Admin"])})
        self.assertEqual(code, 424)
        self.assertEqual(self._grant()[0], 201)
        code2, _ = self._ingest(_body(mode="live"), {"Authorization": _tok(["Admin"])})
        self.assertEqual(code2, 200)                 # approval now active in the durable store

    def test_revoke_blocks_live(self):
        code, rec = self._grant()
        self.assertEqual(self._ingest(_body(mode="live"), {"Authorization": _tok(["Admin"])})[0], 200)
        rv = revenue_api.handle_revoke(json.dumps({"approval_id": rec["id"]}).encode(),
                                       {"Authorization": _tok(["Admin"])}, ENV, store=self.store)
        self.assertEqual(rv[0], 200)
        self.assertEqual(self._ingest(_body(mode="live"), {"Authorization": _tok(["Admin"])})[0], 424)

    def test_durable_idempotency(self):
        hdr = {"Authorization": _tok(["Admin"]), "Idempotency-Key": "dk1"}
        c1, r1 = self._ingest(_body(), hdr)
        c2, r2 = self._ingest(_body(), hdr)
        self.assertEqual((c1, c2), (200, 200))
        self.assertEqual(r1, r2)                     # replay from the durable store
        c3, _ = self._ingest(_body(window={"start": "2026-11-01", "end": "2026-11-02"}),
                             {"Authorization": _tok(["Admin"]), "Idempotency-Key": "dk1"})
        self.assertEqual(c3, 409)


class TestRevenueReport(unittest.TestCase):
    def test_report_requires_auth(self):
        self.assertEqual(revenue_api.handle_report({}, {}, ENV)[0], 401)

    def test_report_dry_run_stub(self):
        code, r = revenue_api.handle_report({"provider": "awin"}, {"Authorization": _tok(["Manager"])}, ENV)
        self.assertEqual(code, 200)
        self.assertEqual(r["repository_mode"], "DRY-RUN")
        self.assertIsNone(r["revenue"])


if __name__ == "__main__":
    unittest.main()
