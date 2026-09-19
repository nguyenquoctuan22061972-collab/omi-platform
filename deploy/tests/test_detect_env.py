"""QA — detect-and-prepare-env.sh (Phase 10 continue). Chạy trong bản sao tạm; không đụng repo."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest

DEPLOY = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT_REL = "deploy/detect-and-prepare-env.sh"


class TestDetectEnv(unittest.TestCase):
    def test_syntax(self):
        self.assertEqual(subprocess.run(["bash", "-n", os.path.join(DEPLOY, "detect-and-prepare-env.sh")]).returncode, 0)

    def _run(self, root):
        return subprocess.run(["bash", SCRIPT_REL], cwd=root, capture_output=True, text=True)

    def test_generates_secret_and_crm_no_secret_leak(self):
        with tempfile.TemporaryDirectory() as root:
            shutil.copytree(DEPLOY, os.path.join(root, "deploy"))
            r = self._run(root)
            env_path = os.path.join(root, "deploy", ".env")
            self.assertTrue(os.path.isfile(env_path))
            content = open(env_path, encoding="utf-8").read()
            m = re.search(r"^AUTH_SECRET=([0-9a-f]+)$", content, re.M)
            self.assertIsNotNone(m, "AUTH_SECRET chưa sinh")
            secret = m.group(1)
            self.assertEqual(len(secret), 64, "AUTH_SECRET phải 64 hex chars")
            self.assertIn("CRM_BASE=", content)
            # Không rò secret ra stdout
            self.assertNotIn(secret, r.stdout)

    def test_idempotent_secret(self):
        with tempfile.TemporaryDirectory() as root:
            shutil.copytree(DEPLOY, os.path.join(root, "deploy"))
            self._run(root)
            env_path = os.path.join(root, "deploy", ".env")
            first = re.search(r"^AUTH_SECRET=(\S+)$", open(env_path, encoding="utf-8").read(), re.M).group(1)
            self._run(root)  # chạy lần 2
            second = re.search(r"^AUTH_SECRET=(\S+)$", open(env_path, encoding="utf-8").read(), re.M).group(1)
            self.assertEqual(first, second, "AUTH_SECRET không được đổi khi chạy lại")


if __name__ == "__main__":
    unittest.main()
