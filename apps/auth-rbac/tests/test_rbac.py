"""PRD-002 §6: RBAC PASS."""
from _base import AuthTestCase, SECRET

from auth import service
from rbac import middleware, matrix


class TestRBAC(AuthTestCase):
    def _token_for(self, username, password, roles):
        self.make_user(username, password, roles)
        return service.login(self.conn, username, password, SECRET)["access_token"]

    def test_admin_has_user_manage(self):
        tok = self._token_for("admin", "p", ["Admin"])
        claims = middleware.require_permission(tok, SECRET, "user:manage")
        self.assertIn("Admin", claims["roles"])

    def test_viewer_denied_write(self):
        tok = self._token_for("viewer", "p", ["Viewer"])
        with self.assertRaises(middleware.Forbidden):
            middleware.require_permission(tok, SECRET, "contact:write")

    def test_viewer_allowed_read(self):
        tok = self._token_for("viewer2", "p", ["Viewer"])
        self.assertTrue(middleware.check_permission(
            middleware.authenticate(tok, SECRET), "contact:read"))

    def test_operator_cannot_manage_users(self):
        tok = self._token_for("op", "p", ["Operator"])
        with self.assertRaises(middleware.Forbidden):
            middleware.require_permission(tok, SECRET, "user:manage")

    def test_missing_token_unauthorized(self):
        with self.assertRaises(middleware.Unauthorized):
            middleware.require_permission("", SECRET, "contact:read")

    def test_matrix_hierarchy(self):
        self.assertTrue(matrix.has_permission(["Manager"], "audit:read"))
        self.assertFalse(matrix.has_permission(["Operator"], "audit:read"))


if __name__ == "__main__":
    import unittest
    unittest.main()
