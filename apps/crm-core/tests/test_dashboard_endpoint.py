"""CR-001: GET /dashboard/kpi endpoint (backward compatible)."""
import json
import threading
import urllib.request
import unittest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from crm.api import create_server  # noqa: E402


class TestDashboardEndpoint(unittest.TestCase):
    def setUp(self):
        self.srv = create_server(host="127.0.0.1", port=8090, db_path=":memory:")
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()

    def tearDown(self):
        self.srv.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:8090{path}") as r:
            return r.status, json.loads(r.read())

    def _post(self, path, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:8090{path}", data=json.dumps(body).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())

    def test_kpi_endpoint_shape(self):
        s, k = self._get("/dashboard/kpi")
        self.assertEqual(s, 200)
        for key in ("total_contacts", "total_messages", "pipeline_by_stage", "win_rate"):
            self.assertIn(key, k)

    def test_kpi_reflects_data(self):
        s, c = self._post("/contacts", {"phone": "0900000001"})
        self._post("/pipeline/update", {"contact_id": c["id"], "stage": "won"})
        s, k = self._get("/dashboard/kpi")
        self.assertEqual(k["total_contacts"], 1)
        self.assertEqual(k["pipeline_by_stage"]["won"], 1)
        self.assertEqual(k["win_rate"], 1.0)

    def test_existing_endpoints_still_work(self):
        # Backward compatible: 5 endpoint cũ vẫn hoạt động.
        s, c = self._post("/contacts", {"phone": "0900000002"})
        self.assertEqual(s, 201)
        s, g = self._get(f"/contacts/{c['id']}")
        self.assertEqual(s, 200)


if __name__ == "__main__":
    unittest.main()
