"""QA validator Frontend Dashboard (PRD-004 TC1-TC10). Tĩnh, chạy offline bằng python."""
import json
import os
import re
import unittest

APP = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as f:
        return f.read()


def _exists(*parts):
    return os.path.isfile(os.path.join(APP, *parts))


class TestDashboard(unittest.TestCase):
    def test_TC1_index_responsive(self):
        html = _read("index.html")
        self.assertIn("viewport", html)
        self.assertIn("width=device-width", html)

    def test_TC2_root_mount(self):
        self.assertIn('id="app"', _read("index.html"))

    def test_TC3_api_calls_kpi_endpoint(self):
        self.assertIn("/dashboard/kpi", _read("src", "api.js"))

    def test_TC4_uses_config_base_no_hardcode(self):
        api = _read("src", "api.js")
        self.assertIn("OMI_CONFIG", api)
        self.assertIn("CRM_BASE", api)
        # Không hardcode host http(s) trong api.js (chỉ path tương đối/biến).
        self.assertFalse(re.search(r"https?://(?!\{)", api), "api.js không được hardcode host")

    def test_TC5_mock_valid(self):
        data = json.loads(_read("mock", "kpi.json"))
        for k in ("total_contacts", "total_messages", "pipeline_by_stage", "win_rate"):
            self.assertIn(k, data)

    def test_TC6_store_state_mgmt(self):
        store = _read("src", "store.js")
        self.assertIn("subscribe", store)
        self.assertIn("set", store)

    def test_TC7_router_routes(self):
        router = _read("src", "router.js")
        self.assertIn("ROUTES", router)
        for r in ("overview", "contacts", "inbox", "pipeline"):
            self.assertIn(r, router)

    def test_TC8_component_map(self):
        for comp in ("nav", "kpiCards", "pipelineChart", "overview"):
            self.assertTrue(_exists("src", "components", f"{comp}.js"), comp)

    def test_TC9_no_secret(self):
        blob = " ".join(
            _read(*p) for p in [("src", "api.js"), ("index.html",), ("config.example.js",)]
        ).lower()
        for bad in ("password", "api_key", "bearer ", "secret_key", "xoxb-"):
            self.assertNotIn(bad, blob, f"nghi secret: {bad}")

    def test_TC10_config_example_and_media_query(self):
        self.assertTrue(_exists("config.example.js"))
        self.assertIn("CRM_BASE", _read("config.example.js"))
        self.assertIn("@media", _read("styles.css"))


if __name__ == "__main__":
    unittest.main()
