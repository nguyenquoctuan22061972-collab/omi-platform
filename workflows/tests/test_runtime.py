"""QA — n8n runtime validation (PRD-008 G)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "runtime"))
import validate  # noqa: E402


class TestRuntimeValidation(unittest.TestCase):
    def test_report_three_workflows(self):
        rep = validate.activation_report()
        self.assertEqual(len(rep), 3)

    def test_webhooks_detected(self):
        rep = {r["name"]: r for r in validate.activation_report()}
        # WF001 + WF002 có webhook.
        wf001 = next(r for n, r in rep.items() if "WF001" in n)
        self.assertIn("crm/lead", wf001["webhooks"])

    def test_disabled_nodes_detected(self):
        rep = validate.activation_report()
        # Mỗi workflow có ít nhất 1 node disabled (cần secret) từ PRD-003.
        self.assertTrue(all(r["needs_activation"] for r in rep))

    def test_credential_nodes_flagged(self):
        rep = {r["name"]: r for r in validate.activation_report()}
        wf002 = next(r for n, r in rep.items() if "WF002" in n)
        self.assertTrue(any("Slack" in c for c in wf002["credential_nodes"]))


if __name__ == "__main__":
    unittest.main()
