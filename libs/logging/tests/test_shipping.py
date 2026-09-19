"""QA — Log shipping (PRD-012 C)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.logging.shipping import FileShipper, DBShipper, RemoteShipper, default_shipper  # noqa: E402


class TestShipping(unittest.TestCase):
    def test_file_shipper_writes(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "app.log")
            fs = FileShipper(p)
            res = fs.ship({"level": "INFO", "msg": "hi"})
            self.assertTrue(res["shipped"])
            with open(p, encoding="utf-8") as f:
                self.assertEqual(json.loads(f.readline())["msg"], "hi")

    def test_default_is_file(self):
        self.assertIsInstance(default_shipper(), FileShipper)
        self.assertEqual(default_shipper().name, "file")

    def test_db_dry_run(self):
        db = DBShipper()
        res = db.ship({"x": 1})
        self.assertFalse(res["shipped"])
        self.assertEqual(res["mode"], "dry-run")
        self.assertEqual(len(db.buffer), 1)

    def test_remote_configured_flag(self):
        self.assertFalse(RemoteShipper(env={}).ship({})["configured"])
        self.assertTrue(RemoteShipper(env={"LOG_SHIPPER_URL": "http://loki"}).ship({})["configured"])


if __name__ == "__main__":
    unittest.main()
