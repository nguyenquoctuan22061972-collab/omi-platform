"""QA — Health Gateway (PRD-011 C). Checker inject → không network."""
import json
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from health.gateway import HealthGateway  # noqa: E402
from health.api import create_server  # noqa: E402

ENV = {"CRM_BASE": "http://crm", "N8N_BASE_URL": "http://n8n"}


class TestGateway(unittest.TestCase):
    def test_reachable_all(self):
        gw = HealthGateway(env=ENV, checker=lambda url: True)
        out = gw.gateway()
        self.assertEqual(out["status"], "ready")
        self.assertEqual(out["crm"]["status"], "reachable")
        self.assertEqual(out["n8n"]["status"], "reachable")

    def test_degraded_when_unreachable(self):
        gw = HealthGateway(env=ENV, checker=lambda url: False)
        self.assertEqual(gw.gateway()["status"], "degraded")

    def test_not_configured(self):
        gw = HealthGateway(env={}, checker=lambda url: True)
        self.assertEqual(gw.crm()["status"], "not_configured")

    def test_adapter_and_queue_defaults(self):
        gw = HealthGateway(env=ENV, checker=lambda url: True)
        self.assertIn("mode", gw.adapters())
        self.assertEqual(gw.queue()["status"], "not_wired")

    def test_injected_status(self):
        gw = HealthGateway(env=ENV, checker=lambda url: True,
                           adapter_status={"enabled": 2}, queue_status={"status": "ok", "pending": 3})
        out = gw.gateway()
        self.assertEqual(out["adapters"]["enabled"], 2)
        self.assertEqual(out["queue"]["pending"], 3)


class TestGatewayEndpoint(unittest.TestCase):
    def setUp(self):
        gw = HealthGateway(env=ENV, checker=lambda url: True)
        self.srv = create_server(host="127.0.0.1", port=8096, env=ENV, gateway=gw)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def test_endpoint(self):
        with urllib.request.urlopen("http://127.0.0.1:8096/health/gateway") as r:
            self.assertEqual(r.status, 200)
            data = json.loads(r.read())
            self.assertEqual(data["status"], "ready")


if __name__ == "__main__":
    unittest.main()
