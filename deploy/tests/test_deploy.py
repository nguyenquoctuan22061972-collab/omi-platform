"""QA validator Production Deployment (PRD-005 TC1-TC15). Tĩnh, offline."""
import os
import unittest

DEPLOY = os.path.join(os.path.dirname(__file__), "..")
ROOT = os.path.join(DEPLOY, "..")


def r(*p, base=DEPLOY):
    with open(os.path.join(base, *p), encoding="utf-8") as f:
        return f.read()


def exists(*p, base=DEPLOY):
    return os.path.isfile(os.path.join(base, *p))


class TestDeploy(unittest.TestCase):
    def test_TC1_compose_services(self):
        c = r("docker-compose.prod.yml")
        for svc in ("crm-core:", "auth-rbac:", "nginx:", "certbot:"):
            self.assertIn(svc, c, svc)

    def test_TC2_dockerfiles_exist(self):
        self.assertTrue(exists("Dockerfile.crm-core"))
        self.assertTrue(exists("Dockerfile.auth-rbac"))

    def test_TC3_dockerfiles_non_root(self):
        for df in ("Dockerfile.crm-core", "Dockerfile.auth-rbac"):
            self.assertIn("USER omi", r(df), df)

    def test_TC4_rate_limit(self):
        self.assertIn("limit_req_zone", r("nginx", "nginx.conf"))
        self.assertIn("limit_req", r("nginx", "conf.d", "omi.conf"))

    def test_TC5_ssl(self):
        conf = r("nginx", "conf.d", "omi.conf")
        self.assertIn("listen 443", conf)
        self.assertIn("ssl_certificate", conf)

    def test_TC6_csp(self):
        self.assertIn("Content-Security-Policy", r("nginx", "conf.d", "omi.conf"))

    def test_TC7_security_headers(self):
        conf = r("nginx", "conf.d", "omi.conf")
        for h in ("Strict-Transport-Security", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy"):
            self.assertIn(h, conf, h)

    def test_TC8_cors(self):
        self.assertIn("Access-Control-Allow-Origin", r("nginx", "conf.d", "omi.conf"))

    def test_TC9_reverse_proxy(self):
        conf = r("nginx", "conf.d", "omi.conf")
        self.assertIn("/api/crm/", conf)
        self.assertIn("/api/auth/", conf)
        self.assertIn("proxy_pass", conf)

    def test_TC10_ci_runs_tests(self):
        ci = r(".github", "workflows", "ci.yml", base=ROOT)
        self.assertIn("unittest discover", ci)
        for wd in ("apps/crm-core", "apps/auth-rbac", "workflows", "apps/dashboard", "deploy"):
            self.assertIn(wd, ci, wd)

    def test_TC11_deploy_manual(self):
        dep = r(".github", "workflows", "deploy.yml", base=ROOT)
        self.assertIn("workflow_dispatch", dep)
        self.assertIn("environment: production", dep)

    def test_TC12_env_example_no_secret(self):
        env = r(".env.example")
        self.assertIn("AUTH_SECRET=", env)
        # AUTH_SECRET phải để trống (không secret thật)
        for line in env.splitlines():
            if line.strip().startswith("AUTH_SECRET="):
                self.assertEqual(line.strip(), "AUTH_SECRET=", "AUTH_SECRET không được chứa giá trị")

    def test_TC13_backup_restore_health(self):
        for s in ("backup.sh", "restore.sh", "healthcheck.sh"):
            self.assertTrue(exists("scripts", s), s)
            self.assertTrue(r("scripts", s).startswith("#!"), f"{s} thiếu shebang")

    def test_TC14_healthcheck_and_restart(self):
        c = r("docker-compose.prod.yml")
        self.assertIn("healthcheck:", c)
        self.assertIn("restart:", c)

    def test_TC15_no_hardcoded_secret(self):
        blob = (r("docker-compose.prod.yml") + r(".env.example")
                + r("nginx", "conf.d", "omi.conf")).lower()
        for bad in ("password=", "secret=", "api_key=", "token=", "bearer "):
            # cho phép "AUTH_SECRET=" (rỗng) trong .env.example
            self.assertNotIn(bad, blob.replace("auth_secret=", ""), bad)


if __name__ == "__main__":
    unittest.main()
