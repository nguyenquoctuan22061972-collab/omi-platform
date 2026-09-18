"""PRD-001 §10: "Tin nhắn đúng contact"."""
from _base import CrmTestCase

from crm import contacts, conversations, ingestion


class TestConversations(CrmTestCase):
    def test_message_attached_to_correct_contact_by_id(self):
        c = contacts.create_contact(self.conn, name="An", phone="0900000001")
        conv = conversations.add_message(
            self.conn, channel="telegram", message="Xin chào", contact_id=c["id"]
        )
        self.assertEqual(conv["contact_id"], c["id"])
        timeline = conversations.list_conversations(self.conn, c["id"])
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["message"], "Xin chào")

    def test_message_resolved_by_phone_when_no_id(self):
        c = contacts.create_contact(self.conn, phone="0900000002")
        conv = conversations.add_message(
            self.conn, channel="zalo_oa", message="Giá bao nhiêu?", phone="0900000002"
        )
        self.assertEqual(conv["contact_id"], c["id"])

    def test_message_creates_contact_when_unknown(self):
        conv = conversations.add_message(
            self.conn, channel="email", message="Hi", email="new@example.com"
        )
        self.assertTrue(conv["contact_id"])
        self.assertEqual(len(contacts.list_contacts(self.conn)), 1)

    def test_missing_identity_raises(self):
        with self.assertRaises(ValueError):
            conversations.add_message(self.conn, channel="telegram", message="x")

    def test_two_contacts_do_not_cross_messages(self):
        a = ingestion.ingest(self.conn, channel="fb", message="A msg", phone="0900000010")
        b = ingestion.ingest(self.conn, channel="fb", message="B msg", phone="0900000011")
        ta = conversations.list_conversations(self.conn, a["contact"]["id"])
        tb = conversations.list_conversations(self.conn, b["contact"]["id"])
        self.assertEqual([m["message"] for m in ta], ["A msg"])
        self.assertEqual([m["message"] for m in tb], ["B msg"])


if __name__ == "__main__":
    import unittest

    unittest.main()
