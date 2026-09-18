"""PRD-002 §6: Login PASS + Login sai PASS."""
from _base import AuthTestCase, SECRET

from auth import service, jwt_util


class TestLogin(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.make_user("admin", "secret123", ["Admin"])

    def test_login_success(self):
        res = service.login(self.conn, "admin", "secret123", SECRET)
        self.assertIn("access_token", res)
        self.assertIn("refresh_token", res)
        self.assertEqual(res["token_type"], "Bearer")
        claims = jwt_util.decode(res["access_token"], SECRET)
        self.assertEqual(claims["username"], "admin")
        self.assertIn("Admin", claims["roles"])

    def test_login_wrong_password(self):
        with self.assertRaises(service.AuthError):
            service.login(self.conn, "admin", "WRONG", SECRET)

    def test_login_unknown_user(self):
        with self.assertRaises(service.AuthError):
            service.login(self.conn, "ghost", "x", SECRET)

    def test_password_is_bcrypt_hashed(self):
        row = self.conn.execute(
            "SELECT password_hash FROM users WHERE username='admin'"
        ).fetchone()
        self.assertTrue(row["password_hash"].startswith("$2"))  # bcrypt prefix
        self.assertNotIn("secret123", row["password_hash"])


if __name__ == "__main__":
    import unittest
    unittest.main()
