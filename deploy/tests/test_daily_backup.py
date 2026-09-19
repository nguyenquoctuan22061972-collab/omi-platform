"""QA — Daily backup runtime (PRD-012 D). Chạy thật trên data giả (dry, không đụng ./data)."""
import os
import subprocess
import tempfile
import unittest

DEPLOY = os.path.join(os.path.dirname(__file__), "..")
ROOT = os.path.abspath(os.path.join(DEPLOY, ".."))
DB = os.path.join(DEPLOY, "backup", "daily-backup.sh")


class TestDailyBackup(unittest.TestCase):
    def test_file_and_syntax(self):
        self.assertTrue(os.path.isfile(DB))
        self.assertTrue(open(DB, encoding="utf-8").read().startswith("#!"))
        self.assertEqual(subprocess.run(["bash", "-n", DB]).returncode, 0)

    def test_does_not_overwrite_old_scripts(self):
        # daily-backup gọi lại script cũ, không thay thế
        s = open(DB, encoding="utf-8").read()
        self.assertIn("deploy/scripts/backup.sh", s)
        self.assertIn("deploy/backup/backup-verify.sh", s)

    def test_end_to_end_dry(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            os.makedirs(data)
            with open(os.path.join(data, "crm_core.db"), "wb") as f:
                f.write(b"SQLite format 3\x00x")
            bdir = os.path.join(tmp, "backups")
            env = dict(os.environ, DATA_DIR=data, BACKUP_DIR=bdir, BACKUP_KEEP="14")
            r = subprocess.run(["bash", DB], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            archives = [f for f in os.listdir(bdir) if f.endswith(".tar.gz")]
            self.assertTrue(archives)
            self.assertTrue(any(f.endswith(".sha256") for f in os.listdir(bdir)))


if __name__ == "__main__":
    unittest.main()
