"""QA — Credential Activation & Go-Live kit (PRD-007 A/C/D/E). Tĩnh + bash -n."""
import os
import subprocess
import unittest

DEPLOY = os.path.join(os.path.dirname(__file__), "..")
ROOT = os.path.join(DEPLOY, "..")


def r(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def has_shebang(path):
    return r(path).startswith("#!")


def bash_ok(path):
    return subprocess.run(["bash", "-n", path]).returncode == 0


class TestActivationKit(unittest.TestCase):
    # Module A
    def test_secrets_files(self):
        for f in ("secrets/validate-env.sh", "secrets/secrets-manifest.md", "secrets/env-mapping.md"):
            self.assertTrue(os.path.isfile(os.path.join(DEPLOY, f)), f)

    def test_validate_env_covers_all_groups(self):
        s = r(os.path.join(DEPLOY, "secrets", "validate-env.sh"))
        for tok in ("TELEGRAM_", "SMTP_", "ZALO_OA_", "FB_PAGE_", "OPENAI_",
                    "GCP_PROJECT", "VERTEX_MODEL", "AUTH_SECRET", "CRM_BASE", "N8N_BASE_URL"):
            self.assertIn(tok, s, tok)

    def test_validate_env_shebang_and_syntax(self):
        p = os.path.join(DEPLOY, "secrets", "validate-env.sh")
        self.assertTrue(has_shebang(p))
        self.assertTrue(bash_ok(p))

    # Module C
    def test_n8n_kit(self):
        for f in ("enable-production.md", "rollback.md", "verify.md"):
            self.assertTrue(os.path.isfile(os.path.join(DEPLOY, "n8n", f)), f)

    # Module D
    def test_deploy_scripts(self):
        for f in ("go-live.sh", "rollback.sh", "post-deploy-check.sh"):
            p = os.path.join(DEPLOY, f)
            self.assertTrue(os.path.isfile(p), f)
            self.assertTrue(has_shebang(p), f)
            self.assertTrue(bash_ok(p), f)

    def test_go_live_has_stages(self):
        s = r(os.path.join(DEPLOY, "go-live.sh"))
        for stage in ("preflight", "backup", "deploy", "post-deploy-check", "rollback"):
            self.assertIn(stage, s, stage)

    # Module E
    def test_production_ready(self):
        p = os.path.join(ROOT, "scripts", "production-ready.sh")
        self.assertTrue(os.path.isfile(p))
        self.assertTrue(has_shebang(p))
        self.assertTrue(bash_ok(p))
        s = r(p)
        for chk in ("Docker", "Nginx", "SSL", "CI", "Secrets", "Adapters",
                    "n8n", "Dashboard KPI", "Contacts", "Inbox", "Pipeline", "Score"):
            self.assertIn(chk, s, chk)

    # An toàn: không secret literal
    def test_no_secret_literal(self):
        blob = (r(os.path.join(DEPLOY, "secrets", "validate-env.sh"))
                + r(os.path.join(DEPLOY, "secrets", "secrets-manifest.md"))
                + r(os.path.join(DEPLOY, "secrets", "env-mapping.md"))).lower()
        for bad in ("bearer ", "xoxb-", "-----begin", "sk-"):
            self.assertNotIn(bad, blob, bad)


if __name__ == "__main__":
    unittest.main()
