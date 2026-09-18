"""QA validator cho workflow n8n (PRD-003 §9, scope B).

Kiểm tra tĩnh — không cần n8n chạy:
- JSON hợp lệ, có name/nodes/connections.
- Có ít nhất 1 trigger + 1 HTTP Request node.
- Mọi connection trỏ tới node tồn tại.
- URL HTTP dùng {{$env.CRM_BASE}} (không hardcode host/secret).
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
    return [(f, json.load(open(f, encoding="utf-8"))) for f in files]


class TestWorkflows(unittest.TestCase):
    def setUp(self):
        self.wfs = _load_all()
        self.assertEqual(len(self.wfs), 3, "phải có đúng 3 workflow WF001/WF002/WF050")

    def test_valid_structure(self):
        for path, wf in self.wfs:
            self.assertIn("name", wf, path)
            self.assertIsInstance(wf.get("nodes"), list, path)
            self.assertTrue(wf["nodes"], f"{path} không có node")
            self.assertIn("connections", wf, path)

    def test_has_trigger_and_http(self):
        for path, wf in self.wfs:
            types = [n["type"] for n in wf["nodes"]]
            self.assertTrue(any(t in TRIGGERS for t in types), f"{path} thiếu trigger")
            self.assertIn("n8n-nodes-base.httpRequest", types, f"{path} thiếu HTTP node")

    def test_connections_point_to_existing_nodes(self):
        for path, wf in self.wfs:
            names = {n["name"] for n in wf["nodes"]}
            for src, conn in wf["connections"].items():
                self.assertIn(src, names, f"{path}: nguồn '{src}' không tồn tại")
                for outputs in conn.get("main", []):
                    for link in outputs:
                        self.assertIn(link["node"], names,
                                      f"{path}: đích '{link['node']}' không tồn tại")

    def test_http_urls_use_env_no_secret(self):
        for path, wf in self.wfs:
            for n in wf["nodes"]:
                if n["type"] == "n8n-nodes-base.httpRequest":
                    url = n["parameters"].get("url", "")
                    self.assertIn("$env.CRM_BASE", url,
                                  f"{path}: URL '{url}' không dùng env CRM_BASE")

    def test_no_hardcoded_secret_markers(self):
        for path, wf in self.wfs:
            blob = json.dumps(wf).lower()
            for bad in ("password", "token=", "bearer ", "api_key", "secret\""):
                self.assertNotIn(bad, blob, f"{path}: có dấu hiệu secret hardcode: {bad}")


if __name__ == "__main__":
    unittest.main()
