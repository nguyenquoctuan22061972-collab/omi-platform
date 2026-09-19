"""QA — Runtime env loader (PRD-011 A)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.runtime import require_env, load_runtime_env, env_report, MissingEnvError, RUNTIME_REQUIRED  # noqa: E402


class TestRuntimeEnv(unittest.TestCase):
    def test_required_keys(self):
        self.assertEqual(RUNTIME_REQUIRED, ["AUTH_SECRET", "CRM_BASE", "N8N_BASE_URL"])

    def test_fail_fast_missing(self):
        with self.assertRaises(MissingEnvError) as ctx:
            load_runtime_env({})
        # Thông báo nêu tên biến thiếu, không có giá trị secret
        self.assertIn("AUTH_SECRET", str(ctx.exception))

    def test_fail_fast_blank(self):
        with self.assertRaises(MissingEnvError):
            require_env({"AUTH_SECRET": "x", "CRM_BASE": "  ", "N8N_BASE_URL": "y"})

    def test_pass_when_all_present(self):
        env = {"AUTH_SECRET": "s", "CRM_BASE": "/api/crm", "N8N_BASE_URL": "http://n8n"}
        got = load_runtime_env(env)
        self.assertEqual(got["CRM_BASE"], "/api/crm")

    def test_report_no_values(self):
        rep = env_report({"AUTH_SECRET": "s"})
        by = {r["key"]: r["present"] for r in rep}
        self.assertTrue(by["AUTH_SECRET"])
        self.assertFalse(by["CRM_BASE"])
        # report chỉ có present bool, không chứa value
        self.assertNotIn("value", rep[0])


if __name__ == "__main__":
    unittest.main()
