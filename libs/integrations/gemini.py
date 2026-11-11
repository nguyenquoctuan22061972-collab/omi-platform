"""Google Gemini adapter. Credential env: GEMINI_API_KEY, GEMINI_MODEL.

`send()` vẫn dry-run như mọi adapter (giữ interface). Bổ sung `live_check()`
(opt-in, chỉ chạy khi gọi tường minh) để kiểm tra xác thực + kết nối thật:
- mặc định gọi models.list — miễn phí, không sinh nội dung;
- `probe=True` gửi thêm 1 generateContent tối đa 8 token đầu ra (chi phí rất nhỏ).
Khóa chỉ gửi qua header `x-goog-api-key`, không bao giờ nằm trong URL, log hay kết quả trả về.

CLI: python -m libs.integrations.gemini [--probe]
"""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Callable, Dict, Mapping, Optional

from .base import Adapter

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _classify(status: int, body: Dict) -> str:
    """Phân loại lỗi Gemini API thành auth / rate_limit / ... (không chứa khóa)."""
    err = (body or {}).get("error", {}) or {}
    reason = " ".join(str(d.get("reason", "")) for d in err.get("details", []) if isinstance(d, dict))
    if status in (401, 403) or "API_KEY_INVALID" in reason or err.get("status") == "UNAUTHENTICATED":
        return "auth"
    if status == 400 and "API key" in str(err.get("message", "")):
        return "auth"
    if status == 429 or err.get("status") == "RESOURCE_EXHAUSTED":
        return "rate_limit"
    if status == 404:
        return "not_found"
    if status >= 500:
        return "server"
    return "http_error"


class GeminiAdapter(Adapter):
    name = "gemini"
    required_env = ["GEMINI_API_KEY", "GEMINI_MODEL"]

    def _request(self, method: str, path: str, payload: Optional[Dict], timeout: float,
                 opener: Callable) -> Dict:
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(f"{API_BASE}/{path}", data=data, method=method, headers={
            "x-goog-api-key": self.config["GEMINI_API_KEY"],
            "Content-Type": "application/json",
        })
        try:
            with opener(req, timeout=timeout) as resp:
                return {"ok": True, "status": resp.status, "body": json.loads(resp.read() or b"{}")}
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read() or b"{}")
            except ValueError:
                body = {}
            err = body.get("error", {}) if isinstance(body, dict) else {}
            return {"ok": False, "status": e.code, "error": _classify(e.code, body),
                    "message": str(err.get("message", ""))[:200]}
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            reason = getattr(e, "reason", e)
            return {"ok": False, "status": 0, "error": "network", "message": type(reason).__name__}

    def live_check(self, probe: bool = False, timeout: float = 15.0,
                   opener: Callable = urllib.request.urlopen) -> Dict:
        """Kiểm tra thật (opt-in). Trả kết quả có cấu trúc; không bao giờ chứa khóa."""
        if not self.is_configured():
            return {"adapter": self.name, "status": "blocked", "missing_env":
                    [k for k in self.required_env if not self.config.get(k)]}
        model = self.config["GEMINI_MODEL"]
        out: Dict = {"adapter": self.name, "model": model}
        listed = self._request("GET", "models?pageSize=1000", None, timeout, opener)
        out["models_list"] = {k: v for k, v in listed.items() if k != "body"}
        if not listed["ok"]:
            out.update(status="fail", authentication="fail" if listed["error"] == "auth" else "unknown",
                       connectivity="pass" if listed["status"] else "fail")
            return out
        names = [m.get("name", "").split("/", 1)[-1] for m in listed["body"].get("models", [])]
        out.update(authentication="pass", connectivity="pass", models_available=len(names),
                   model_found=model in names,
                   gemini_models=sorted(n for n in names if n.startswith("gemini"))[:60])
        if probe:
            gen = self._request("POST", f"models/{model}:generateContent", {
                "contents": [{"parts": [{"text": "Reply with the single word: OK"}]}],
                "generationConfig": {"maxOutputTokens": 8, "temperature": 0},
            }, timeout, opener)
            if gen["ok"]:
                usage = gen["body"].get("usageMetadata", {})
                cand = (gen["body"].get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                out["generate"] = {"ok": True, "status": gen["status"], "reply": text.strip()[:40],
                                   "usage": {k: usage.get(k) for k in
                                             ("promptTokenCount", "candidatesTokenCount", "totalTokenCount")}}
            else:
                out["generate"] = gen
        ok = out["model_found"] and (not probe or out["generate"]["ok"])
        out["status"] = "pass" if ok else "fail"
        return out


def main(argv=None) -> int:
    import argparse
    import os
    ap = argparse.ArgumentParser(description="Gemini live check (không in khóa)")
    ap.add_argument("--probe", action="store_true", help="thêm 1 generateContent ≤8 token (chi phí rất nhỏ)")
    args = ap.parse_args(argv)
    res = GeminiAdapter(os.environ).live_check(probe=args.probe)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
