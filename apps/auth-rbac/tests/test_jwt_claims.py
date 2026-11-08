"""QA — JWT issuer/audience stamping (staging hardening). Positive + negative."""
import os
import unittest
from unittest import mock

from _base import AuthTestCase, SECRET
from auth import service as _service, jwt_util


class TestJWTClaims(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.make_user("alice", "pw", ["Admin"])

    def _login_claims(self):
        res = _service.login(self.conn, "alice", "pw", SECRET)
        return jwt_util.decode(res["access_token"], SECRET)

    def test_no_env_no_iss_aud(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTH_JWT_ISS", None)
            os.environ.pop("AUTH_JWT_AUD", None)
            claims = self._login_claims()
        self.assertNotIn("iss", claims)
        self.assertNotIn("aud", claims)

    def test_env_stamps_iss_aud(self):
        with mock.patch.dict(os.environ, {"AUTH_JWT_ISS": "affos-auth", "AUTH_JWT_AUD": "revenue"}):
            claims = self._login_claims()
        self.assertEqual(claims["iss"], "affos-auth")
        self.assertEqual(claims["aud"], "revenue")


if __name__ == "__main__":
    unittest.main()
