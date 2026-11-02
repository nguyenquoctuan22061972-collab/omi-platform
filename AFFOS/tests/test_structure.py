"""QA — AFFOS skeleton structure + manifest reuse pointers tồn tại."""
import json
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(ROOT, ".."))
REQUIRED = [
    "apps/dashboard", "apps/api", "apps/worker",
    "core/identity", "core/commerce", "core/attribution", "core/intelligence", "core/economics",
    "connectors/youtube", "connectors/amazon", "connectors/tiktok", "connectors/shopee", "connectors/affiliate-network",
    "agents/registry", "agents/research", "agents/commerce", "agents/content", "agents/analytics", "agents/qa", "agents/security",
    "skills/registry", "skills/definitions", "workflows/n8n",
    "infrastructure/docker", "infrastructure/backup", "infrastructure/monitoring",
    "tests", "docs", "constitution",
]


class TestAFFOS(unittest.TestCase):
    def test_all_dirs_exist(self):
        for d in REQUIRED:
            self.assertTrue(os.path.isdir(os.path.join(ROOT, d)), f"thiếu dir {d}")

    def test_constitution_present(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "constitution", "PRINCIPLES.md")))

    def test_manifest_reuse_pointers_exist(self):
        with open(os.path.join(ROOT, "affos.manifest.json")) as f:
            m = json.load(f)["modules"]
        for path, reuse in m.items():
            self.assertTrue(os.path.exists(os.path.join(REPO, reuse)),
                            f"reuse pointer không tồn tại: {path} -> {reuse}")

    def test_every_module_dir_has_readme(self):
        with open(os.path.join(ROOT, "affos.manifest.json")) as f:
            m = json.load(f)["modules"]
        for path in m:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path, "README.md")), path)


if __name__ == "__main__":
    unittest.main()
