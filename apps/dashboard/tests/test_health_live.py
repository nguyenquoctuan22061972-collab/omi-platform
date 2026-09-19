"""QA — Dashboard health wiring (PRD-011 D). Kiểm tra tĩnh; không đụng operations.js."""
import os
import unittest

OPS = os.path.join(os.path.dirname(__file__), "..", "operations")


def r(name):
    with open(os.path.join(OPS, name), encoding="utf-8") as f:
        return f.read()


class TestHealthLive(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(OPS, "health-live.js")))

    def test_uses_runtime_health_gateway(self):
        js = r("health-live.js")
        self.assertIn("/health/gateway", js)

    def test_uses_config_no_hardcode_host(self):
        js = r("health-live.js")
        self.assertIn("HEALTH_BASE", js)
        self.assertNotIn("http://localhost", js)

    def test_does_not_touch_kpi(self):
        # File health-live không render KPI cards / không import module KPI cũ
        js = r("health-live.js")
        self.assertNotIn("kpiCards", js)
        self.assertNotIn("overview.js", js)

    def test_operations_js_unchanged_ref(self):
        # operations.js không import health-live (giữ nguyên file cũ)
        self.assertNotIn("health-live", r("operations.js"))


if __name__ == "__main__":
    unittest.main()
