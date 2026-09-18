"""QA — AI Provider Router (PRD-009 C)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.ai_router import AIRouter, PROVIDERS, RoutingPolicy  # noqa: E402


class TestRouter(unittest.TestCase):
    def test_four_providers(self):
        self.assertEqual(set(PROVIDERS), {"openai", "vertex", "claude", "gemini"})

    def test_none_available_empty_env(self):
        r = AIRouter(env={})
        self.assertIsNone(r.select())
        self.assertFalse(r.route("hi")["ready"])

    def test_select_by_order(self):
        r = AIRouter(env={"ANTHROPIC_API_KEY": "k", "GEMINI_API_KEY": "g"})
        # order mặc định: openai, claude, gemini, vertex → claude được chọn
        self.assertEqual(r.select(), "claude")

    def test_fallback_chain(self):
        r = AIRouter(env={"OPENAI_API_KEY": "k", "GEMINI_API_KEY": "g"})
        chain = r.route("hi")
        self.assertEqual(chain["primary"], "openai")
        self.assertIn("gemini", chain["fallback"])

    def test_custom_policy(self):
        r = AIRouter(env={"GCP_PROJECT": "p", "VERTEX_MODEL": "m"},
                     policy=RoutingPolicy(order=["vertex"], retries=5, timeout_s=10))
        out = r.route("hi")
        self.assertEqual(out["primary"], "vertex")
        self.assertEqual(out["retries"], 5)

    def test_dry_run(self):
        r = AIRouter(env={"OPENAI_API_KEY": "k"})
        self.assertEqual(r.route("hi")["status"], "dry-run")


if __name__ == "__main__":
    unittest.main()
