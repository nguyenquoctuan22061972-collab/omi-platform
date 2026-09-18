"""QA — Backup verification (PRD-008 F). Gồm backup dry-run thực tế."""
import os
import subprocess
import tarfile
import tempfile
import unittest

DEPLOY = os.path.join(os.path.dirname(__file__), "..")
BV = os.path.join(DEPLOY, "backup", "backup-verify.sh")
RV = os.path.join(DEPLOY, "backup", "restore-verify.sh")


def _make_backup(tmp):
    data = os.path.join(tmp, "data")
    os.makedirs(data)
    with open(os.path.join(data, "crm_core.db"), "wb") as f:
        f.write(b"SQLite format 3\x00fake")
    archive = os.path.join(tmp, "omi-backup-test.tar.gz")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(data, arcname="data")
    return archive


class TestBackupVerify(unittest.TestCase):
    def test_files_and_syntax(self):
        for p in (BV, RV, os.path.join(DEPLOY, "backup", "retention-policy.md")):
            self.assertTrue(os.path.isfile(p), p)
        for s in (BV, RV):
            self.assertTrue(open(s, encoding="utf-8").read().startswith("#!"))
            self.assertEqual(subprocess.run(["bash", "-n", s]).returncode, 0, s)

    def test_backup_verify_and_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = _make_backup(tmp)
            r = subprocess.run(["bash", BV, archive], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.isfile(archive + ".sha256"))
            # chạy lại → checksum khớp
            r2 = subprocess.run(["bash", BV, archive], capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0)
            self.assertIn("khớp", r2.stdout)

    def test_restore_verify_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = _make_backup(tmp)
            r = subprocess.run(["bash", RV, archive], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PASS", r.stdout)

    def test_corrupt_backup_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.tar.gz")
            open(bad, "wb").write(b"not a gzip")
            r = subprocess.run(["bash", BV, bad], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
