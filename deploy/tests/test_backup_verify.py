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


class TestBackupVolumeMode(unittest.TestCase):
    """PG_VOLUME mode (Docker volume) — additive; filesystem mode giữ nguyên."""

    BK = os.path.join(DEPLOY, "scripts", "backup.sh")

    def test_syntax(self):
        self.assertEqual(subprocess.run(["bash", "-n", self.BK]).returncode, 0)

    def test_has_volume_branch_readonly(self):
        s = open(self.BK, encoding="utf-8").read()
        self.assertIn("PG_VOLUME", s)
        self.assertIn(":ro", s)  # volume phải mount read-only
        self.assertIn("docker volume inspect", s)

    def test_filesystem_fallback_unchanged(self):
        # PG_VOLUME rỗng → vẫn backup DATA_DIR như cũ.
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            os.makedirs(data)
            open(os.path.join(data, "crm_core.db"), "wb").write(b"SQLite format 3\x00x")
            bdir = os.path.join(tmp, "backups")
            env = dict(os.environ, DATA_DIR=data, BACKUP_DIR=bdir, BACKUP_KEEP="14")
            env.pop("PG_VOLUME", None)
            r = subprocess.run(["bash", self.BK], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue([f for f in os.listdir(bdir) if f.endswith(".tar.gz")])

    def test_wrapper_forwards_to_canonical(self):
        # deploy/backup/backup.sh chỉ là wrapper exec sang scripts/backup.sh (fallback mode chạy được).
        wrapper = os.path.join(DEPLOY, "backup", "backup.sh")
        self.assertTrue(os.path.isfile(wrapper))
        self.assertEqual(subprocess.run(["bash", "-n", wrapper]).returncode, 0)
        self.assertIn("scripts/backup.sh", open(wrapper, encoding="utf-8").read())
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "data")
            os.makedirs(data)
            open(os.path.join(data, "crm_core.db"), "wb").write(b"SQLite format 3\x00x")
            bdir = os.path.join(tmp, "backups")
            env = dict(os.environ, DATA_DIR=data, BACKUP_DIR=bdir, BACKUP_KEEP="14")
            env.pop("PG_VOLUME", None)
            r = subprocess.run(["bash", wrapper], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue([f for f in os.listdir(bdir) if f.endswith(".tar.gz")])

    def test_volume_missing_fails_clearly(self):
        # PG_VOLUME trỏ volume không tồn tại → lỗi rõ ràng, không im lặng.
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, BACKUP_DIR=os.path.join(tmp, "backups"),
                       PG_VOLUME="omi_no_such_volume_xyz")
            r = subprocess.run(["bash", self.BK], env=env, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            # không docker hoặc volume thiếu — cả hai đều báo ERROR
            self.assertIn("ERROR", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
