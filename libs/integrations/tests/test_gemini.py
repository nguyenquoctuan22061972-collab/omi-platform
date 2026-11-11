"""QA — Gemini adapter. Không network: HTTP được giả lập qua `opener`."""
import io
import json
import os
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from libs.integrations import get_adapter  # noqa: E402
from libs.integrations.activation import connection_test  # noqa: E402

KEY = "test-key-should-never-leak"
ENV = {"GEMINI_API_KEY": KEY, "GEMINI_MODEL": "gemini-test-flash"}
MODELS = {"models": [{"name": "models/gemini-test-flash"}, {"name": "models/gemini-test-tts"}]}


class FakeResp(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(json.dumps(body).encode())
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def http_error(code, body):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(json.dumps(body).encode()))


class Opener:
    """Trả lần lượt các phản hồi; ghi lại request để kiểm tra header/URL."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        r = self.responses.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


class TestGeminiAdapter(unittest.TestCase):
    def test_registered_with_uniform_interface(self):
        a = get_adapter("gemini", env={})
        self.assertEqual(a.required_env, ["GEMINI_API_KEY", "GEMINI_MODEL"])
        self.assertFalse(a.is_configured())
        self.assertEqual(a.send({"prompt": "hi"})["status"], "dry-run")

    def test_activation_needs_enable_flag(self):
        a = get_adapter("gemini", env=ENV)
        self.assertFalse(connection_test(a, ENV)["ok"])
        self.assertTrue(connection_test(a, {**ENV, "GEMINI_ENABLED": "true"})["ok"])

    def test_blocked_without_env(self):
        res = get_adapter("gemini", env={}).live_check(opener=Opener())
        self.assertEqual(res["status"], "blocked")
        self.assertEqual(res["missing_env"], ["GEMINI_API_KEY", "GEMINI_MODEL"])

    def test_models_list_pass_and_key_only_in_header(self):
        op = Opener(FakeResp(200, MODELS))
        res = get_adapter("gemini", env=ENV).live_check(opener=op)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["authentication"], "pass")
        self.assertTrue(res["model_found"])
        req = op.requests[0]
        self.assertEqual(req.get_header("X-goog-api-key"), KEY)
        self.assertNotIn(KEY, req.full_url)
        self.assertNotIn(KEY, json.dumps(res))

    def test_model_missing_fails(self):
        env = {**ENV, "GEMINI_MODEL": "no-such-model"}
        res = get_adapter("gemini", env=env).live_check(opener=Opener(FakeResp(200, MODELS)))
        self.assertEqual(res["status"], "fail")
        self.assertEqual(res["authentication"], "pass")
        self.assertFalse(res["model_found"])

    def test_invalid_key_is_auth_error(self):
        body = {"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.",
                          "status": "INVALID_ARGUMENT", "details": [{"reason": "API_KEY_INVALID"}]}}
        res = get_adapter("gemini", env=ENV).live_check(opener=Opener(http_error(400, body)))
        self.assertEqual(res["status"], "fail")
        self.assertEqual(res["authentication"], "fail")
        self.assertEqual(res["models_list"]["error"], "auth")
        self.assertNotIn(KEY, json.dumps(res))

    def test_permission_denied_is_auth_error(self):
        body = {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "denied"}}
        res = get_adapter("gemini", env=ENV).live_check(opener=Opener(http_error(403, body)))
        self.assertEqual(res["models_list"]["error"], "auth")

    def test_rate_limit(self):
        body = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}}
        res = get_adapter("gemini", env=ENV).live_check(opener=Opener(http_error(429, body)))
        self.assertEqual(res["models_list"]["error"], "rate_limit")
        self.assertEqual(res["connectivity"], "pass")

    def test_network_failure(self):
        res = get_adapter("gemini", env=ENV).live_check(
            opener=Opener(urllib.error.URLError(ConnectionRefusedError())))
        self.assertEqual(res["models_list"]["error"], "network")
        self.assertEqual(res["connectivity"], "fail")

    def test_probe_generate(self):
        gen = {"candidates": [{"content": {"parts": [{"text": "OK"}]}}],
               "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 1, "totalTokenCount": 8}}
        op = Opener(FakeResp(200, MODELS), FakeResp(200, gen))
        res = get_adapter("gemini", env=ENV).live_check(probe=True, opener=op)
        self.assertEqual(res["status"], "pass")
        self.assertEqual(res["generate"]["reply"], "OK")
        self.assertEqual(res["generate"]["usage"]["totalTokenCount"], 8)
        sent = json.loads(op.requests[1].data)
        self.assertEqual(sent["generationConfig"]["maxOutputTokens"], 8)
        self.assertTrue(op.requests[1].full_url.endswith("models/gemini-test-flash:generateContent"))

    def test_probe_rate_limited_fails(self):
        body = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}}
        op = Opener(FakeResp(200, MODELS), http_error(429, body))
        res = get_adapter("gemini", env=ENV).live_check(probe=True, opener=op)
        self.assertEqual(res["status"], "fail")
        self.assertEqual(res["generate"]["error"], "rate_limit")


if __name__ == "__main__":
    unittest.main()
