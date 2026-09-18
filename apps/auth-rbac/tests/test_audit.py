"""PRD-002 §6: Audit Log PASS."""
from _base import AuthTestCase, SECRET

from auth import service, audit


class TestAudit(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.u = self.make_user("admin", "secret123", ["Admin"])

    def test_login_success_audited(self):
        service.login(self.conn, "admin", "secret123", SECRET)
        actions = [r["action"] for r in audit.list_logs(self.conn)]
        self.assertIn("login_success", actions)

    def test_login_failed_audited(self):
        with self.assertRaises(service.AuthError):
            service.login(self.conn, "admin", "WRONG", SECRET)
        actions = [r["action"] for r in audit.list_logs(self.conn)]
        self.assertIn("login_failed", actions)

    def test_logout_and_refresh_audited(self):
        res = service.login(self.conn, "admin", "secret123", SECRET)
        service.refresh(self.conn, res["refresh_token"], SECRET)
        service.logout(self.conn, res["refresh_token"], user_id=self.u["id"])
        actions = [r["action"] for r in audit.list_logs(self.conn)]
        self.assertIn("refresh", actions)
        self.assertIn("logout", actions)

    def test_audit_has_timestamp_and_action(self):
        service.login(self.conn, "admin", "secret123", SECRET)
        row = audit.list_logs(self.conn)[0]
        self.assertTrue(row["timestamp"])
        self.assertTrue(row["action"])


if __name__ == "__main__":
    import unittest
    unittest.main()
