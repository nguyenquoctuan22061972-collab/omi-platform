"""QA validator workflow n8n (PRD-003 §10, scope B). Kiểm tra tĩnh, không cần n8n.

Map acceptance:
  TC1 JSON hợp lệ/import được   TC2 có trigger + HTTP node
  TC3 connection trỏ node tồn tại  TC4 URL dùng $env.CRM_BASE
  TC5 không secret literal      TC6 node cần credential đều disabled
  TC7 có .env.example
"""
import glob
import json
import os
import unittest

WF_DIR = os.path.join(os.path.dirname(__file__), "..")
TRIGGERS = {
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.cron",
}


def _load_all():
    files = sorted(glob.glob(os.path.join(WF_DIR, "WF*", "workflow.json")))
    out = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            out.append((f, json.load(fh)))
    return out


class TestWorkflows(unittest.TestCase):
    def setUp(self):
        self.wfs = _load_all()
        self.assertEqual(len(self.wfs), 3, "TC1: cần đúng 3 workflow")

    def test_TC1_valid_structure(self):
        for path, wf in self.wfs:
            self.assertIn("name", wf, path)
            self.assertTrue(isinstance(wf.get("nodes"), list) and wf["nodes"], path)
            self.assertIn("connections", wf, path)

    def test_TC2_has_trigger_and_http(self):
        for path, wf in self.wfs:
            types = [n["type"] for n in wf["nodes"]]
            self.assertTrue(any(t in TRIGGERS for t in types), f"{path} thiếu trigger")
            self.assertIn("n8n-nodes-base.httpRequest", types, f"{path} thiếu HTTP")

    def test_TC3_connections_valid(self):
        for path, wf in self.wfs:
            names = {n["name"] for n in wf["nodes"]}
            for src, conn in wf["connections"].items():
                self.assertIn(src, names, f"{path}: nguồn '{src}' lạ")
                for outs in conn.get("main", []):
                    for link in outs:
                        self.assertIn(link["node"], names, f"{path}: đích '{link['node']}' lạ")

    def test_TC4_http_uses_env(self):
        for path, wf in self.wfs:
            for n in wf["nodes"]:
                if n["type"] == "n8n-nodes-base.httpRequest":
                    self.assertIn("$env.CRM_BASE", n["parameters"].get("url", ""),
                                  f"{path}: URL không dùng CRM_BASE")

    def test_TC5_no_secret_literal(self):
        for path, wf in self.wfs:
            blob = json.dumps(wf).lower()
            for bad in ('password":', "token=", "bearer ", "api_key", "xoxb-", "secret_key"):
                self.assertNotIn(bad, blob, f"{path}: nghi secret literal '{bad}'")

    def test_TC6_credential_nodes_disabled(self):
        """Mọi node có 'credentials' phải disabled (chờ gắn secret)."""
        for path, wf in self.wfs:
            for n in wf["nodes"]:
                if n.get("credentials"):
                    self.assertTrue(n.get("disabled") is True,
                                    f"{path}: node '{n['name']}' có credential nhưng chưa disabled")

    def test_TC7_env_example_exists(self):
        env = os.path.join(WF_DIR, ".env.example")
        self.assertTrue(os.path.isfile(env), "thiếu workflows/.env.example")
        content = open(env, encoding="utf-8").read()
        for key in ("N8N_BASE_URL", "CRM_BASE"):
            self.assertIn(key, content, f".env.example thiếu {key}")


if __name__ == "__main__":
    unittest.main()
