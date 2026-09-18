"""QA — Operations Dashboard (PRD-006 E)."""
import json
import os
import unittest

D = os.path.join(os.path.dirname(__file__), "..", "operations")


def r(*p):
    with open(os.path.join(D, *p), encoding="utf-8") as f:
        return f.read()


class TestOperations(unittest.TestCase):
    def test_files_exist(self):
        for f in ("index.html", "operations.js", os.path.join("mock", "ops.json")):
            self.assertTrue(os.path.isfile(os.path.join(D, f)), f)

    def test_ops_mock_has_sections(self):
        data = json.loads(r("mock", "ops.json"))
        for k in ("containers", "workflows", "backup", "ci", "deploys", "alerts"):
            self.assertIn(k, data)

    def test_does_not_touch_kpi_dashboard(self):
        # Operations là standalone; không import src/app.js hay overview KPI.
        js = r("operations.js")
        self.assertNotIn("../src/app.js", js)
        self.assertNotIn("kpiCards", js)

    def test_responsive(self):
        self.assertIn("width=device-width", r("index.html"))


if __name__ == "__main__":
    unittest.main()
