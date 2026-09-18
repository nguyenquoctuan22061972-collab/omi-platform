"""Tiện ích test — nạp package từ src/, DB in-memory, seed user."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from auth import db as _db, tokens as _tokens, service as _service  # noqa: E402

SECRET = "test-secret"


class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = _db.connect(":memory:")
        _db.init_db(self.conn)
        _tokens.init_store(self.conn)

    def tearDown(self):
        self.conn.close()

    def make_user(self, username, password, roles):
        return _service.register(self.conn, username, password, roles)
