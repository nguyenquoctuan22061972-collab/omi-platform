"""PRD-001 §10: "KPI thay đổi theo thời gian thực"."""
from _base import CrmTestCase

from crm import contacts, conversations, pipeline, dashboard


class TestDashboardKpi(CrmTestCase):
    def test_kpi_reflects_changes_in_realtime(self):
        # Ban đầu rỗng.
        k0 = dashboard.kpi(self.conn)
        self.assertEqual(k0["total_contacts"], 0)
        self.assertEqual(k0["total_messages"], 0)
        self.assertEqual(k0["win_rate"], 0.0)

        # Thêm contact + message → KPI đổi ngay.
        c = contacts.create_contact(self.conn, phone="0900000001")
        conversations.add_message(
            self.conn, channel="telegram", message="hi", contact_id=c["id"]
        )
        k1 = dashboard.kpi(self.conn)
        self.assertEqual(k1["total_contacts"], 1)
        self.assertEqual(k1["total_messages"], 1)

        # Pipeline won → win_rate cập nhật realtime.
        pipeline.update_stage(self.conn, c["id"], "won")
        k2 = dashboard.kpi(self.conn)
        self.assertEqual(k2["pipeline_by_stage"]["won"], 1)
        self.assertEqual(k2["win_rate"], 1.0)

        # Thêm 1 contact lost → win_rate = 1/2.
        c2 = contacts.create_contact(self.conn, phone="0900000002")
        pipeline.update_stage(self.conn, c2["id"], "lost")
        k3 = dashboard.kpi(self.conn)
        self.assertEqual(k3["win_rate"], 0.5)


if __name__ == "__main__":
    import unittest

    unittest.main()
