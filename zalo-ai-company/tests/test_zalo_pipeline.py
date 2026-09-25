"""QA — Zalo OA Pipeline (PR-001). Reuse ZaloOaAdapter + AIRouter, dry-run, no network."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from zalo_pipeline import handle_inbound, parse_event  # noqa: E402

EVENT = {"sender": {"id": "zalo_user_123"}, "message": {"text": "Giá gói Premium bao nhiêu?"}}


class TestZaloPipeline(unittest.TestCase):
    def test_parse_event(self):
        p = parse_event(EVENT)
        self.assertEqual(p["user_id"], "zalo_user_123")
        self.assertIn("Premium", p["text"])

    def test_full_pipeline_dry_run(self):
        r = handle_inbound(EVENT, env={})
        self.assertTrue(r["ok"])
        steps = [s["step"] for s in r["steps"]]
        self.assertEqual(steps, ["parse", "crm", "ai", "zalo_reply", "audit", "metrics"])

    def test_invalid_event(self):
        r = handle_inbound({"sender": {"id": "x"}}, env={})  # thiếu text
        self.assertFalse(r["ok"])

    def test_go_live_needs_two_secrets(self):
        # không secret → chưa go-live
        self.assertFalse(handle_inbound(EVENT, env={})["ready_to_go_live"])
        # đủ 2 secret → go-live ready + zalo configured, không rò secret ra reply
        env = {"ZALO_OA_ID": "oa_demo", "ZALO_OA_ACCESS_TOKEN": "tok_demo_value_1234"}
        r = handle_inbound(EVENT, env=env)
        self.assertTrue(r["ready_to_go_live"])
        self.assertEqual(r["zalo_missing_env"], [])
        zalo_step = [s for s in r["steps"] if s["step"] == "zalo_reply"][0]
        self.assertEqual(zalo_step["result"]["status"], "dry-run")  # KHÔNG gọi API thật
        self.assertNotIn("tok_demo_value_1234", str(r))             # token không lộ

    def test_ai_fallback_without_provider(self):
        r = handle_inbound(EVENT, env={})
        ai = [s for s in r["steps"] if s["step"] == "ai"][0]
        self.assertEqual(ai["provider"], "fallback")

    def test_ai_uses_provider_when_available(self):
        r = handle_inbound(EVENT, env={"OPENAI_API_KEY": "x"})
        ai = [s for s in r["steps"] if s["step"] == "ai"][0]
        self.assertEqual(ai["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
