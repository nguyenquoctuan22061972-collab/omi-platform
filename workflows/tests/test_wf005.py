"""QA — WF005 Zalo OA Assistant (PR-001). Config-based (no $env), credential nodes disabled."""
import json
import os
import unittest

WF = os.path.join(os.path.dirname(__file__), "..", "WF005.n8n.json")
CHAIN = ["Webhook", "Config", "Parse", "CRM Update", "AI Reply", "Zalo Reply", "Audit", "Metrics"]


class TestWF005(unittest.TestCase):
    def setUp(self):
        self.wf = json.load(open(WF, encoding="utf-8"))
        self.nodes = {n["name"]: n for n in self.wf["nodes"]}

    def test_valid_and_chain(self):
        self.assertIn("name", self.wf)
        for name in CHAIN:
            self.assertIn(name, self.nodes)
        for a, b in zip(CHAIN, CHAIN[1:]):
            targets = [l["node"] for outs in self.wf["connections"][a]["main"] for l in outs]
            self.assertIn(b, targets, f"{a} -> {b}")

    def test_no_env_access(self):
        self.assertNotIn("$env", json.dumps(self.wf))

    def test_http_urls_from_config(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.httpRequest":
                self.assertIn("$('Config')", n["parameters"].get("url", ""))

    def test_credential_nodes_disabled(self):
        for n in self.wf["nodes"]:
            if n.get("credentials"):
                self.assertTrue(n.get("disabled") is True, n["name"])

    def test_zalo_reply_uses_header_auth(self):
        z = self.nodes["Zalo Reply"]
        self.assertIn("httpHeaderAuth", z.get("credentials", {}))
        self.assertTrue(z.get("disabled"))

    def test_no_secret_value(self):
        import re
        blob = json.dumps(self.wf)
        self.assertIsNone(re.search(r'(?i)(secret|token|password|api[_-]?key|bearer)"?\s*[:=]\s*"[A-Za-z0-9/_+\-]{12,}"', blob))
        for bad in ("xoxb-", "AIza", "sk-"):
            self.assertNotIn(bad, blob)


if __name__ == "__main__":
    unittest.main()
