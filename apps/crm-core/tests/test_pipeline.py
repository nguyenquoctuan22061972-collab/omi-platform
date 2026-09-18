"""PRD-001 §10: "Pipeline cập nhật"."""
from _base import CrmTestCase

from crm import contacts, pipeline


class TestPipeline(CrmTestCase):
    def setUp(self):
        super().setUp()
        self.c = contacts.create_contact(self.conn, phone="0900000001")

    def test_update_sets_stage(self):
        res = pipeline.update_stage(self.conn, self.c["id"], "qualified")
        self.assertEqual(res["stage"], "qualified")
        self.assertEqual(pipeline.get_stage(self.conn, self.c["id"]), "qualified")

    def test_update_transitions_stage(self):
        pipeline.update_stage(self.conn, self.c["id"], "lead")
        pipeline.update_stage(self.conn, self.c["id"], "won")
        self.assertEqual(pipeline.get_stage(self.conn, self.c["id"]), "won")

    def test_invalid_stage_rejected(self):
        with self.assertRaises(pipeline.InvalidStage):
            pipeline.update_stage(self.conn, self.c["id"], "archived")

    def test_unknown_contact_rejected(self):
        with self.assertRaises(ValueError):
            pipeline.update_stage(self.conn, "no-such-id", "lead")


if __name__ == "__main__":
    import unittest

    unittest.main()
