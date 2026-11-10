"""QA — AFFOS Impact Revenue Integrity Guard (CTO revenue-integrity task).

Pins the two risks the CTO flagged and the required guarantees. NO credentials, NO live call,
NO network, NO cost. AWIN is exercised only to prove it stays REAL (unaffected).

Covered (maps to the CTO's mandatory test list 1–9):
  1. AWIN production (verified) is recognized REAL.
  2. Impact fake-test can never be REAL.
  3. Impact dry-run (no production transport) can never be REAL.
  4. Impact production WITHOUT CEO approval can never be REAL.
  5. Impact becomes REAL only with full conditions AND the separate approval whitelist.
  6. AWIN conversion carries the AWIN label.
  7. Impact conversion carries the Impact label.
  8. No revenue write path (click/conversion/commission ingest) can emit a REAL Impact row.
  9. (Full regression suite runs separately.)
"""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "connectors"))
sys.path.insert(0, os.path.join(ROOT, "connectors", "impact"))

import provenance            # noqa: E402
import proof                 # noqa: E402
from impact_live import ImpactLiveClient, ProductionTransport, Transport  # noqa: E402

CREDS = {"IMPACT_ACCOUNT_SID": "SID123", "IMPACT_AUTH_TOKEN": "tok"}


class _FakeTestTransport(Transport):
    """Non-production transport (test data). is_production=False → records stamped TEST."""
    is_production = False
    def get(self, url, auth_header):
        if "Actions" in url:
            return {"Actions": [{"Id": 1, "CampaignId": 9, "Amount": 100, "Payout": 30,
                                 "Currency": "USD", "State": "APPROVED",
                                 "ClickDate": "2026-10-05", "EventDate": "2026-10-06"}]}
        return {}


class _ProdActions(ProductionTransport):
    """Production-FLAGGED transport (is_production=True) returning real-shaped Actions. No network."""
    def __init__(self, actions):
        self._actions = actions
    def get(self, url, auth_header):
        if not auth_header:
            from impact_live import ImpactAuthError
            raise ImpactAuthError("missing credentials")
        return {"Actions": self._actions}


class _MemLiveRepo:
    """Non-SQLite LIVE repo double so the production write-guard passes (no real DB)."""
    data_state = "LIVE"
    def __init__(self):
        self.rows = {}
    def insert(self, table, row):
        self.rows.setdefault(table, []).append(row)
    def count(self, table):
        return len(self.rows.get(table, []))
    def query(self, sql, params=()):
        # Answer proof.real_commerce_proof()'s unscoped conv/comm/link reads from stored rows.
        s = sql.lower()
        if "from conversion_events" in s and "as tl" not in s:
            return [{"data_state": r.get("data_state"), "is_verified": r.get("is_verified"),
                     "source": r.get("source")} for r in self.rows.get("conversion_events", [])]
        if "from commissions" in s:
            return [{"data_state": r.get("data_state"), "is_verified": r.get("is_verified"),
                     "source": r.get("source")} for r in self.rows.get("commissions", [])]
        if "as tl" in s:   # link rows: tracking_link_id of each conversion's click
            return [{"tl": r.get("tracking_link_id", "")} for r in self.rows.get("click_events", [])]
        return []


ACTION = {"Id": 9001, "CampaignId": 501, "Amount": 200, "Payout": 60, "Currency": "USD",
          "State": "APPROVED", "ClickDate": "2026-10-05", "EventDate": "2026-10-06"}


class TestImpactRevenueIntegrity(unittest.TestCase):

    # ---- 1. AWIN production stays REAL (unaffected) ----
    def test_awin_production_verified_is_real(self):
        rec = provenance.provenance("awin_production", "T-1", "PRODUCTION_VERIFIED", is_verified=True)
        self.assertTrue(provenance.is_real(rec))

    # ---- 2. Impact fake-test never REAL ----
    def test_impact_fake_test_never_real(self):
        c = ImpactLiveClient(CREDS, transport=_FakeTestTransport())
        self.assertEqual(c._state(), "TEST")
        self.assertEqual(c._source(), "impact_fake_test")
        self.assertFalse(provenance.is_real(c._prov("X", currency="USD")))

    # ---- 3. Impact dry-run (no production transport) never REAL ----
    def test_impact_dry_run_never_real(self):
        c = ImpactLiveClient(CREDS, transport=None)      # not ready → dry-run
        self.assertFalse(c._ready())
        self.assertEqual(c._state(), "TEST")
        self.assertFalse(provenance.is_real(c._prov("X", currency="USD")))

    # ---- 4. Impact production WITHOUT CEO approval never REAL ----
    def test_impact_production_unapproved_never_real(self):
        self.assertNotIn("impact_production", provenance.PRODUCTION_SOURCES)
        c = ImpactLiveClient(CREDS, transport=ProductionTransport())
        rec = c._prov("X", currency="USD")
        self.assertEqual(rec["data_state"], "PRODUCTION_VERIFIED")   # transport truth
        self.assertEqual(int(rec["is_verified"]), 1)
        self.assertFalse(provenance.is_real(rec))                    # but NOT real (not whitelisted)

    # ---- 5. Impact REAL only with full conditions AND the separate approval whitelist ----
    def test_impact_real_only_with_full_conditions_and_approval(self):
        c = ImpactLiveClient(CREDS, transport=ProductionTransport())
        rec = c._prov("X", currency="USD")
        self.assertFalse(provenance.is_real(rec))                    # before approval
        original = set(provenance.PRODUCTION_SOURCES)
        try:
            provenance.PRODUCTION_SOURCES.add("impact_production")   # simulate CEO approval ONLY in-test
            self.assertTrue(provenance.is_real(rec))                 # now real with full chain
            # even post-approval, a fake-test / unverified record stays non-real
            f = ImpactLiveClient(CREDS, transport=_FakeTestTransport())
            self.assertFalse(provenance.is_real(f._prov("Y", currency="USD")))
            seeded = provenance.provenance("impact_production", "Z", "SEEDED")
            self.assertFalse(provenance.is_real(seeded))
        finally:
            provenance.PRODUCTION_SOURCES.clear()
            provenance.PRODUCTION_SOURCES.update(original)           # restore (no leak)
        self.assertNotIn("impact_production", provenance.PRODUCTION_SOURCES)

    # ---- 6 & 7. Source-aware conversion labels ----
    def test_conversion_labels_are_source_specific(self):
        self.assertEqual(provenance.conversion_type("PRODUCTION_VERIFIED", "awin_production"),
                         "AWIN_PRODUCTION_CONVERSION")
        self.assertEqual(provenance.conversion_type("LIVE", "awin_production"),
                         "AWIN_PRODUCTION_CONVERSION")
        self.assertEqual(provenance.conversion_type("PRODUCTION_VERIFIED", "impact_production"),
                         "IMPACT_PRODUCTION_CONVERSION")
        self.assertEqual(provenance.conversion_type("LIVE", "impact_production"),
                         "IMPACT_PRODUCTION_CONVERSION")
        self.assertEqual(provenance.conversion_type("SEEDED", "impact_production"), "SEEDED_CONVERSION")
        # production state with unknown/empty source must NOT be mislabeled AWIN
        self.assertEqual(provenance.conversion_type("LIVE"), "SEEDED_CONVERSION")
        self.assertEqual(provenance.conversion_type("PRODUCTION_VERIFIED", "mystery"), "SEEDED_CONVERSION")

    # ---- 8. No revenue write path emits a REAL Impact row (end-to-end ingest) ----
    def test_ingest_write_paths_never_emit_real_impact(self):
        c = ImpactLiveClient(CREDS, transport=_ProdActions([ACTION]))
        self.assertEqual(c._state(), "PRODUCTION_VERIFIED")          # production transport
        repo = _MemLiveRepo()
        res = c.ingest_actions(repo, "2026-10-01", "2026-10-06")
        self.assertEqual(res["ingested"], 1)
        # every row written to EVERY revenue-bearing table is non-real
        for table in ("click_events", "conversion_events", "commissions"):
            self.assertTrue(repo.rows.get(table), f"{table} should have rows")
            for row in repo.rows[table]:
                self.assertEqual(row["source"], "impact_production")
                self.assertFalse(provenance.is_real(row), f"{table} row became REAL (guard bypass!)")
        # the conversion carries the Impact label (not AWIN)
        self.assertEqual(repo.rows["conversion_events"][0]["event_subtype"],
                         "IMPACT_PRODUCTION_CONVERSION")
        # and the aggregate proof refuses to call it REAL
        self.assertEqual(proof.real_commerce_proof(repo)["status"], "NOT YET VERIFIED")


if __name__ == "__main__":
    unittest.main()
