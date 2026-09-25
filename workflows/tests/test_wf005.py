"""QA — WF005 Zalo OA Assistant (hardened). Config-based, retry/idempotency/rate-limit, no $env."""
import json
import os
import unittest

WF = os.path.join(os.path.dirname(__file__), "..", "WF005.n8n.json")
CHAIN = ["Webhook", "Config", "Parse", "CRM Update", "AI Reply", "Zalo Reply", "Audit", "Metrics"]


class TestWF005(unittest.TestCase):
    def setUp(self):
        self.wf = json.load(open(WF, encoding="utf-8"))
        self.nodes = {n["name"]: n for n in self.wf["nodes"]}

    def test_chain(self):
        for a, b in zip(CHAIN, CHAIN[1:]):
            targets = [l["node"] for outs in self.wf["connections"][a]["main"] for l in outs]
            self.assertIn(b, targets)

    def test_no_env(self):
        self.assertNotIn("$env", json.dumps(self.wf))

    def test_http_urls_from_config(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.httpRequest":
                self.assertIn("$('Config')", n["parameters"].get("url", ""))

    def test_retry_on_all_http(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.httpRequest":
                self.assertTrue(n.get("retryOnFail"), f"{n['name']} thiếu retry")
                self.assertGreaterEqual(n.get("maxTries", 0), 2)

    def test_idempotency_key(self):
        self.assertIn("event_id", self.nodes["Parse"]["parameters"]["functionCode"])
        crm = self.nodes["CRM Update"]["parameters"]
        hdrs = [h["name"] for h in crm["headerParameters"]["parameters"]]
        self.assertIn("Idempotency-Key", hdrs)
        self.assertIn("Prefer", hdrs)

    def test_rate_limit_config(self):
        names = {a["name"] for a in self.nodes["Config"]["parameters"]["assignments"]["assignments"]}
        self.assertIn("rate_limit_per_min", names)

    def test_credential_disabled(self):
        for n in self.wf["nodes"]:
            if n.get("credentials"):
                self.assertTrue(n.get("disabled") is True)

    def test_no_secret_value(self):
        import re
        self.assertIsNone(re.search(r'(?i)(token|secret|password|api_key)"?\s*[:=]\s*"[A-Za-z0-9/_+\-]{12,}"', json.dumps(self.wf)))
