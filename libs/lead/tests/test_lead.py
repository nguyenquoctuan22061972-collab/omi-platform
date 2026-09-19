"""QA — Lead Engine (PRD-010 C)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.lead import LeadEngine, EmailQueue, crm_mapping  # noqa: E402


class TestLead(unittest.TestCase):
    def test_capture(self):
        e = LeadEngine()
        lead = e.capture(name="An", phone="0900", source="facebook")
        self.assertTrue(lead["id"].startswith("led_"))
        self.assertEqual(len(e.leads), 1)

    def test_crm_mapping_matches_prd001(self):
        lead = {"name": "An", "phone": "0900", "email": "a@x.com", "source": "form", "tags": ["vip"]}
        payload = crm_mapping(lead)
        self.assertEqual(set(payload), {"name", "phone", "email", "source", "tags"})
        self.assertEqual(payload["phone"], "0900")

    def test_email_queue_dry_run(self):
        q = EmailQueue()
        q.enqueue("a@x.com", "Hi", "body")
        sent = q.flush_dry_run()
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["status"], "sent-dry-run")
        self.assertEqual(len(q.queue), 0)

    def test_notify_dry_run(self):
        e = LeadEngine()
        lead = e.capture(phone="0900")
        n = e.notify_telegram(lead)
        self.assertEqual(n["status"], "dry-run")

    def test_webhook_no_secret(self):
        e = LeadEngine()
        wh = e.register_webhook("LEAD_WEBHOOK_URL")
        self.assertEqual(wh["env_key"], "LEAD_WEBHOOK_URL")
        self.assertNotIn("http", str(wh))


if __name__ == "__main__":
    unittest.main()
