"""QA — WF004 AI Call Intelligence (WO-015 / WO-015C). Kiểm tra tĩnh, không cần n8n.

v2: bỏ $env (n8n chặn access to env vars) → dùng node 'Config' (Set) chứa base URL,
downstream tham chiếu $('Config'). Token vẫn ở credential (node disabled). Secret env-only.
Không đụng test_workflows.py (vẫn đúng 3 WF*/workflow.json). File phẳng WF004.n8n.json.
"""
import json
import os
import unittest

WF = os.path.join(os.path.dirname(__file__), "..", "WF004.n8n.json")
EXPECTED_CHAIN = ["Webhook", "Config", "Validation", "Vertex STT", "AI Summary",
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
        for a, b in zip(EXPECTED_CHAIN, EXPECTED_CHAIN[1:]):
            targets = [l["node"] for outs in self.wf["connections"][a]["main"] for l in outs]
            self.assertIn(b, targets, f"{a} phải nối {b}")

    def test_config_node_provides_bases(self):
        cfg = self.nodes["Config"]
        self.assertEqual(cfg["type"], "n8n-nodes-base.set")
        names = {a["name"] for a in cfg["parameters"]["assignments"]["assignments"]}
        self.assertEqual(names, {"crm_base", "vertex_stt_url", "vertex_summary_url", "telegram_chat_id"})

    def test_no_env_access(self):
        # $env bị n8n chặn → không được dùng ở bất kỳ đâu
        self.assertNotIn("$env", json.dumps(self.wf))

    def test_http_urls_from_config(self):
        for n in self.wf["nodes"]:
            if n["type"] == "n8n-nodes-base.httpRequest":
                url = n["parameters"].get("url", "")
                self.assertIn("$('Config')", url, f"{n['name']}: URL phải lấy từ node Config")

    def test_credential_nodes_disabled(self):
        for n in self.wf["nodes"]:
            if n.get("credentials"):
                self.assertTrue(n.get("disabled") is True,
                                f"{n['name']} có credential nhưng chưa disabled")

    def test_no_secret_value(self):
        # Không có GIÁ TRỊ secret (không chỉ là tên biến). crm_base nội bộ không phải secret.
        import re
        blob = json.dumps(self.wf)
        self.assertIsNone(re.search(r'(?i)(secret|token|password|api[_-]?key|bearer)"?\s*[:=]\s*"[A-Za-z0-9/_+\-]{12,}"', blob))
        for bad in ("xoxb-", "AIza", "sk-"):
            self.assertNotIn(bad, blob, f"nghi secret literal: {bad}")


if __name__ == "__main__":
    unittest.main()
