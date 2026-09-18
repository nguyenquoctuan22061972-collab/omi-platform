"""QA — Inbox Domain (PRD-006 B)."""
import json
import os
import unittest

D = os.path.join(os.path.dirname(__file__), "..", "inbox")


def r(*p):
    with open(os.path.join(D, *p), encoding="utf-8") as f:
        return f.read()


class TestInbox(unittest.TestCase):
    def test_files_exist(self):
        for f in ("index.html", "inbox.js", "adapters.js", os.path.join("mock", "messages.json")):
            self.assertTrue(os.path.isfile(os.path.join(D, f)), f)

    def test_four_channel_adapters(self):
        a = r("adapters.js")
        for ch in ("telegram", "email", "zalo_oa", "facebook_messenger"):
            self.assertIn(ch, a)

    def test_adapter_interface(self):
        a = r("adapters.js")
        for member in ("key", "label", "configured", "fetchMessages"):
            self.assertIn(member, a)

    def test_no_hardcoded_credential(self):
        a = r("adapters.js").lower()
        for bad in ("password", "api_key", "bearer ", "token:"):
            self.assertNotIn(bad, a)

    def test_mock_valid(self):
        data = json.loads(r("mock", "messages.json"))
        self.assertTrue(isinstance(data, list) and data)


if __name__ == "__main__":
    unittest.main()
