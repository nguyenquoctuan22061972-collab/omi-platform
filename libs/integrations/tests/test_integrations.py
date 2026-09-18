"""QA — adapter architecture (PRD-006 Module D). Không network; kiểm tra dry-run + env."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from libs.integrations import get_adapter, list_adapters, ADAPTERS  # noqa: E402


class TestIntegrations(unittest.TestCase):
    def test_six_providers(self):
        self.assertEqual(
            set(list_adapters()),
            {"telegram", "gmail_smtp", "zalo_oa", "facebook_messenger", "openai", "vertex_ai"},
        )

    def test_uniform_interface(self):
        for name in ADAPTERS:
            a = get_adapter(name, env={})
            self.assertTrue(hasattr(a, "required_env"))
            for m in ("is_configured", "health", "send"):
                self.assertTrue(callable(getattr(a, m)), f"{name}.{m}")

    def test_unconfigured_when_env_empty(self):
        a = get_adapter("telegram", env={})
        self.assertFalse(a.is_configured())
        self.assertEqual(a.health()["mode"], "dry-run")
        self.assertTrue(a.health()["missing_env"])

    def test_configured_from_env(self):
        a = get_adapter("telegram", env={"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "1"})
        self.assertTrue(a.is_configured())

    def test_send_is_dry_run(self):
        a = get_adapter("openai", env={"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"})
        res = a.send({"prompt": "hi"})
        self.assertEqual(res["status"], "dry-run")
        self.assertIn("would_send", res)

    def test_unknown_adapter_raises(self):
        with self.assertRaises(KeyError):
            get_adapter("nope", env={})

    def test_no_hardcoded_secret_in_config(self):
        # config chỉ đọc từ env; env rỗng -> giá trị rỗng, không có secret literal.
        a = get_adapter("gmail_smtp", env={})
        self.assertTrue(all(v == "" for v in a.config.values()))


if __name__ == "__main__":
    unittest.main()
