"""PRD-002 §6: Token hết hạn PASS + Refresh PASS."""
from _base import AuthTestCase, SECRET

from auth import service, jwt_util


class TestToken(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.make_user("op", "pass123", ["Operator"])

    def test_expired_token_rejected(self):
        # Cấp access token đã hết hạn (ttl âm) → decode raise ExpiredToken.
        res = service.login(self.conn, "op", "pass123", SECRET, access_ttl=-1)
        with self.assertRaises(jwt_util.ExpiredToken):
            jwt_util.decode(res["access_token"], SECRET)

    def test_valid_token_accepted(self):
        res = service.login(self.conn, "op", "pass123", SECRET, access_ttl=900)
        claims = jwt_util.decode(res["access_token"], SECRET)
        self.assertEqual(claims["username"], "op")

    def test_tampered_token_rejected(self):
        res = service.login(self.conn, "op", "pass123", SECRET)
        bad = res["access_token"][:-2] + ("aa" if not res["access_token"].endswith("aa") else "bb")
        with self.assertRaises(jwt_util.JWTError):
            jwt_util.decode(bad, SECRET)

    def test_refresh_issues_new_access(self):
        res = service.login(self.conn, "op", "pass123", SECRET)
        out = service.refresh(self.conn, res["refresh_token"], SECRET)
        self.assertIn("access_token", out)
        claims = jwt_util.decode(out["access_token"], SECRET)
        self.assertEqual(claims["username"], "op")

    def test_refresh_after_logout_fails(self):
        res = service.login(self.conn, "op", "pass123", SECRET)
        service.logout(self.conn, res["refresh_token"], user_id=None)
        with self.assertRaises(service.AuthError):
            service.refresh(self.conn, res["refresh_token"], SECRET)


if __name__ == "__main__":
    import unittest
    unittest.main()
