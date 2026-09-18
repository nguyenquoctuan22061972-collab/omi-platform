"""QA — structured logging (PRD-008 B)."""
import io
import json
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from libs.logging import (  # noqa: E402
    JsonFormatter, get_logger, new_request_id, new_correlation_id, rotation_config, audit_event,
)


class TestLogging(unittest.TestCase):
    def test_ids(self):
        self.assertTrue(new_request_id().startswith("req_"))
        self.assertTrue(new_correlation_id().startswith("cor_"))

    def test_json_format(self):
        rec = logging.LogRecord("omi.t", logging.INFO, __file__, 1, "hello", None, None)
        rec.request_id = "req_1"
        out = json.loads(JsonFormatter().format(rec))
        self.assertEqual(out["level"], "INFO")
        self.assertEqual(out["msg"], "hello")
        self.assertEqual(out["request_id"], "req_1")

    def test_logger_json_output_and_isolated(self):
        logger = get_logger("test")
        self.assertFalse(logger.propagate)  # không lan sang logger cũ
        buf = io.StringIO()
        logger.handlers[0].stream = buf
        audit_event(logger, "login", actor="admin", target="system")
        line = buf.getvalue().strip().splitlines()[-1]
        data = json.loads(line)
        self.assertEqual(data["event"], "login")
        self.assertEqual(data["actor"], "admin")

    def test_rotation_config(self):
        cfg = rotation_config()
        self.assertIn("RotatingFileHandler", cfg["class"])
        self.assertGreater(cfg["maxBytes"], 0)


if __name__ == "__main__":
    unittest.main()
