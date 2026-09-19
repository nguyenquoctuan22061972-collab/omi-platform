"""QA — /metrics endpoint (PRD-012 A)."""
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from health.api import create_server  # noqa: E402


class TestMetricsEndpoint(unittest.TestCase):
    def setUp(self):
        self.srv = create_server(host="127.0.0.1", port=8097,
                                 env={"CRM_BASE": "x", "AUTH_SECRET": "y", "N8N_BASE_URL": "z"})
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def test_metrics_text(self):
        with urllib.request.urlopen("http://127.0.0.1:8097/metrics") as r:
            self.assertEqual(r.status, 200)
            self.assertIn("text/plain", r.headers.get("Content-Type", ""))
            body = r.read().decode()
            self.assertIn("omi_health_summary", body)
            self.assertIn("omi_uptime_seconds", body)


if __name__ == "__main__":
    unittest.main()
