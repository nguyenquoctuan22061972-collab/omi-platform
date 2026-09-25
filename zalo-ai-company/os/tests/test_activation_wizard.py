"""QA — Zalo Production Activation Wizard (PR-005.1). Offline, reuse ZaloOaAdapter."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import activation_wizard as w  # noqa: E402

FULL = {"ZALO_OA_ID": "1234567890", "ZALO_OA_ACCESS_TOKEN": "tok_abc_1234567890"}


class TestWizard(unittest.TestCase):
    def test_oa_id_valid_invalid(self):
        self.assertTrue(w.validate_oa_id("1234567890")["ok"])
        self.assertFalse(w.validate_oa_id("abc")["ok"])
        self.assertFalse(w.validate_oa_id("")["ok"])

    def test_openapi_dry_run_masks_token(self):
        r = w.dry_run_openapi(FULL, "hi")
        self.assertTrue(r["ok"])
        self.assertEqual(r["request"]["headers"]["access_token"], "***set-in-credential***")
        self.assertNotIn("tok_abc_1234567890", str(r))

    def test_credential_health(self):
        self.assertTrue(w.credential_health(FULL)["ok"])
        self.assertFalse(w.credential_health({})["ok"])
        self.assertIn("ZALO_OA_ID", w.credential_health({})["missing_env"])

    def test_webhook_verify(self):
        ok = w.verify_webhook("https://ycdtuo.ezn8n.com")
        self.assertTrue(ok["ok"])
        self.assertTrue(ok["production_url"].endswith("/webhook/wf005-zalo-inbound"))
        self.assertFalse(w.verify_webhook("http://x")["ok"])   # không https

    def test_run_ready_with_two_secrets(self):
        r = w.run(FULL, "https://ycdtuo.ezn8n.com")
        self.assertTrue(r["ready_to_activate"])
        self.assertEqual(len(r["checklist"]), 6)
        self.assertTrue(len(r["recovery"]) >= 5)

    def test_run_not_ready_without_secrets(self):
        self.assertFalse(w.run({}, "")["ready_to_activate"])

    def test_no_secret_leak(self):
        self.assertNotIn("tok_abc_1234567890", str(w.run(FULL, "https://x.io")))


if __name__ == "__main__":
    unittest.main()
