"""QA — WF004 AI Call Intelligence (WO-015). Kiểm tra tĩnh, không cần n8n.

Không đụng test_workflows.py (vẫn đúng 3 WF*/workflow.json). WF004 là file phẳng
workflows/WF004.n8n.json → validate riêng ở đây.
"""
import json
import os
import unittest

WF = os.path.join(os.path.dirname(__file__), "..", "WF004.n8n.json")
EXPECTED_CHAIN = ["Webhook", "Validation", "Vertex STT", "AI Summary",
                  "CRM Update", "Telegram Notify", "Audit", "Metrics"]


class TestWF004(unittest.TestCase):
    def setUp(self):
        with open(WF, encoding="utf-8") as fh:
            self.wf = json.load(fh)
        self.nodes = {n["name"]: n for n in self.wf["nodes"]}

    def test_import_valid_structure(self):
        self.assertIn("name", self.wf)
        self.assertTrue(self.wf["nodes"])
        self.assertIn("connections", self.wf)

    def test_all_pipeline_nodes_present(self):
        for name in EXPECTED_CHAIN:
            self.assertIn(name, self.nodes, f"thiếu node {name}")

    def test_webhook_trigger_and_http(self):
        types = [n["type"] for n in self.wf["nodes"]]
        self.assertIn("n8n-nodes-base.webhook", types)
        self.assertIn("n8n-nodes-base.httpRequest", types)

    def test_connections_reference_existing(self):
        for src, conn in self.wf["connections"].items():
            self.assertIn(src, self.nodes, f"nguồn lạ: {src}")
            for outs in conn.get("main", []):
                for link in outs:
                    self.assertIn(link["node"], self.nodes, f"đích lạ: {link['node']}")

    def test_chain_order(self):
        # chuỗi Webhook -> ... -> Metrics đúng thứ tự
        for a, b in zip(EXPECTED_CHAIN, EXPECTED_CHAIN[1:]):
            targets = [l["node"] for outs in self.wf["connections"][a]["main"] for l in outs]
            self.assertIn(b, targets, f"{a} phải nối {b}")

    def test_env_only_urls(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.httpRequest":
                url = n["parameters"].get("url", "")
                self.assertIn("$env.", url, f"{n['name']}: URL phải dùng $env")
                self.assertNotIn("http://", url)
                self.assertNotIn("https://", url)

    def test_crm_nodes_use_crm_base(self):
        for name in ("CRM Update", "Audit", "Metrics"):
            self.assertIn("$env.CRM_BASE", self.nodes[name]["parameters"]["url"])

    def test_credential_nodes_disabled(self):
        for n in self.wf["nodes"]:
            if n.get("credentials"):
                self.assertTrue(n.get("disabled") is True,
                                f"{n['name']} có credential nhưng chưa disabled")

    def test_no_secret_literal(self):
        blob = json.dumps(self.wf).lower()
        for bad in ('password":', "token=", "bearer ", "api_key", "xoxb-", "secret_key"):
            self.assertNotIn(bad, blob, f"nghi secret literal: {bad}")


if __name__ == "__main__":
    unittest.main()
