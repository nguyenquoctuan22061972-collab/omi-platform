"""QA — ZALO AI COMPANY Command Center (PRD-015)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from command_center import CommandCenter  # noqa: E402


class TestCommandCenter(unittest.TestCase):
    def setUp(self):
        self.cc = CommandCenter()

    def test_manifest_valid(self):
        self.assertEqual(self.cc.validate(), [], "manifest phải hợp lệ")

    def test_nine_departments(self):
        self.assertEqual(len(self.cc.departments()), 9)

    def test_expected_departments_present(self):
        ids = {d["id"] for d in self.cc.departments()}
        for x in ("engineering", "zalo", "crm", "vault", "sales",
                  "content", "security", "qa", "monitoring"):
            self.assertIn(x, ids)

    def test_runtime_bindings_exist(self):
        # mỗi phòng ban trỏ tới module/dir ĐÃ TỒN TẠI → reuse, không tạo mới
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        for d in self.cc.departments():
            b = d.get("runtime_binding")
            self.assertTrue(b, d["id"])
            self.assertTrue(os.path.exists(os.path.join(root, b)),
                            f"{d['id']}: binding không tồn tại: {b}")

    def test_permission_requests_prioritized(self):
        p0 = self.cc.permission_requests("P0")
        self.assertTrue(any(p["dept"] == "zalo" for p in p0))
        self.assertTrue(all(p["priority"] == "P0" for p in p0))

    def test_readiness_summary(self):
        r = self.cc.readiness()
        self.assertEqual(r["total"], 9)
        self.assertEqual(r["active"] + r["degraded"] + r["blocked"], 9)
        self.assertIn("P0", r["open_permissions"])


if __name__ == "__main__":
    unittest.main()
