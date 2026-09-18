"""QA — Contacts Domain (PRD-006 A)."""
import json
import os
import unittest

D = os.path.join(os.path.dirname(__file__), "..", "contacts")


def r(*p):
    with open(os.path.join(D, *p), encoding="utf-8") as f:
        return f.read()


class TestContacts(unittest.TestCase):
    def test_files_exist(self):
        for f in ("index.html", "contacts.js", "api.js", os.path.join("mock", "contacts.json")):
            self.assertTrue(os.path.isfile(os.path.join(D, f)), f)

    def test_mock_valid(self):
        data = json.loads(r("mock", "contacts.json"))
        self.assertTrue(isinstance(data, list) and data)
        for c in data:
            for k in ("id", "name", "phone", "source"):
                self.assertIn(k, c)

    def test_api_has_search_filter_paginate(self):
        api = r("api.js")
        for fn in ("applySearchFilter", "paginate", "getContacts"):
            self.assertIn(fn, api)

    def test_no_hardcoded_host_or_secret(self):
        api = r("api.js").lower()
        self.assertIn("crm_base", api)
        for bad in ("password", "api_key", "bearer "):
            self.assertNotIn(bad, api)

    def test_responsive(self):
        self.assertIn("width=device-width", r("index.html"))


if __name__ == "__main__":
    unittest.main()
