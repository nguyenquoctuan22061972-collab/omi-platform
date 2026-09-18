"""QA — Runtime Health (PRD-008 A). Unit + HTTP smoke."""
import json
import os
import sys
import threading
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from health.service import HealthService  # noqa: E402
from health.api import create_server  # noqa: E402


class TestHealthService(unittest.TestCase):
    def test_ready_when_all_env(self):
        svc = HealthService(env={"CRM_BASE": "x", "AUTH_SECRET": "y", "N8N_BASE_URL": "z"})
        self.assertEqual(svc.readiness()["status"], "ready")
        self.assertEqual(svc.health()["status"], "healthy")

    def test_not_ready_when_missing(self):
        svc = HealthService(env={"CRM_BASE": "x"})
        self.assertEqual(svc.readiness()["status"], "not_ready")
        self.assertEqual(svc.health()["status"], "degraded")

    def test_liveness_independent_of_deps(self):
        svc = HealthService(env={})
        self.assertEqual(svc.liveness()["status"], "live")

    def test_version_build(self):
        svc = HealthService(env={"APP_VERSION": "1.2.3", "GIT_SHA": "abc"})
        self.assertEqual(svc.version()["version"], "1.2.3")
        self.assertIn("python", svc.build_info())


class TestHealthApi(unittest.TestCase):
    def setUp(self):
        self.srv = create_server(host="127.0.0.1", port=8095,
                                 env={"CRM_BASE": "x", "AUTH_SECRET": "y", "N8N_BASE_URL": "z"})
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()

    def _get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8095{path}") as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_endpoints(self):
        self.assertEqual(self._get("/health")[0], 200)
        self.assertEqual(self._get("/health/live")[1]["status"], "live")
        self.assertEqual(self._get("/health/ready")[0], 200)
        self.assertEqual(self._get("/version")[0], 200)
        self.assertEqual(self._get("/build-info")[0], 200)
        self.assertEqual(self._get("/nope")[0], 404)


if __name__ == "__main__":
    unittest.main()
