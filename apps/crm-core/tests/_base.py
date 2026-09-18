"""Tiện ích chung cho test — nạp package crm từ src/ và tạo DB in-memory."""
import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src")
)

from crm import db as _db  # noqa: E402


class CrmTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = _db.connect(":memory:")
        _db.init_db(self.conn)

    def tearDown(self):
        self.conn.close()
