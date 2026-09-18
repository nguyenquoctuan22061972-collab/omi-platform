"""PRD-001 §10: "Trùng số điện thoại phải merge"."""
from _base import CrmTestCase

from crm import contacts


class TestContactsMerge(CrmTestCase):
    def test_duplicate_phone_merges(self):
        a = contacts.create_contact(
            self.conn, name="An", phone="0900000001", source="facebook_messenger"
        )
        b = contacts.create_contact(
            self.conn, phone="0900000001", email="an@example.com", source="email"
        )
        # Cùng 1 contact (không tạo bản ghi mới).
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(len(contacts.list_contacts(self.conn)), 1)
        # Trường trống được điền, giữ trường cũ.
        self.assertEqual(b["name"], "An")
        self.assertEqual(b["email"], "an@example.com")
        self.assertEqual(b["source"], "facebook_messenger")

    def test_duplicate_email_merges(self):
        a = contacts.create_contact(self.conn, email="x@example.com")
        b = contacts.create_contact(self.conn, email="x@example.com", phone="0900000002")
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(len(contacts.list_contacts(self.conn)), 1)

    def test_distinct_contacts_not_merged(self):
        contacts.create_contact(self.conn, phone="0900000003")
        contacts.create_contact(self.conn, phone="0900000004")
        self.assertEqual(len(contacts.list_contacts(self.conn)), 2)

    def test_tags_are_merged_not_duplicated(self):
        contacts.create_contact(self.conn, phone="0900000005", tags=["vip"])
        c = contacts.create_contact(
            self.conn, phone="0900000005", tags=["vip", "pricing"]
        )
        self.assertEqual(sorted(c["tags"]), ["pricing", "vip"])


if __name__ == "__main__":
    import unittest

    unittest.main()
