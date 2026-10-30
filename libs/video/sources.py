"""Stock asset sources — probe accessibility + download with fallback.

Chỉ dùng CDN công khai (không cần API key) của ba nguồn ảnh miễn phí. Mỗi nguồn khai
báo một URL "probe" (một asset thật, nhỏ) để kiểm tra khả năng tải. Khi một nguồn bị
chặn (proxy/WAF/network), ta chuyển sang nguồn kế tiếp còn truy cập được — đúng yêu cầu
vận hành: báo domain bị chặn và fallback.

Lưu ý: trang gốc (vd pixabay.com) có thể trả 403 do WAF, nhưng CDN asset
(cdn.pixabay.com/...) vẫn 200. Vì thế probe luôn nhắm vào asset thật, không nhắm root.
"""
from __future__ import annotations

import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_TIMEOUT = 25


class AssetUnavailable(RuntimeError):
    """Không nguồn nào tải được asset yêu cầu."""


def _looks_like_image(data: bytes) -> bool:
    """Nhận diện JPEG/PNG/WebP/GIF qua magic bytes (Pexels có thể trả WebP)."""
    if len(data) < 64:
        return False
    if data[:3] == b"\xff\xd8\xff":          # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":     # PNG
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WebP
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):   # GIF
        return True
    return False


@dataclass(frozen=True)
class AssetSource:
    """Một nguồn ảnh miễn phí qua CDN công khai."""

    key: str
    domain: str              # domain CDN dùng để tải asset
    probe_url: str           # URL asset thật, nhỏ, để test khả năng tải
    license: str
    attribution: str

    def __repr__(self) -> str:  # gọn log
        return f"<AssetSource {self.key} {self.domain}>"


# Thứ tự là thứ tự ưu tiên fallback.
SOURCES: Sequence[AssetSource] = (
    AssetSource(
        key="pexels",
        domain="images.pexels.com",
        probe_url=(
            "https://images.pexels.com/photos/355747/"
            "pexels-photo-355747.jpeg?auto=compress&cs=tinysrgb&w=640"
        ),
        license="Pexels License (free, no attribution required)",
        attribution="Pexels.com",
    ),
    AssetSource(
        key="unsplash",
        domain="images.unsplash.com",
        probe_url="https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=640&q=70",
        license="Unsplash License (free)",
        attribution="Unsplash.com",
    ),
    AssetSource(
        key="pixabay",
        domain="cdn.pixabay.com",
        probe_url="https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885_640.jpg",
        license="Pixabay Content License (free)",
        attribution="Pixabay.com",
    ),
)

SOURCE_BY_KEY: Dict[str, AssetSource] = {s.key: s for s in SOURCES}


def _request(url: str, method: str = "GET") -> urllib.request.Request:
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", _UA)
    req.add_header("Accept", "image/avif,image/webp,image/*,*/*;q=0.8")
    return req


def _http_fetch(url: str, timeout: int = _TIMEOUT) -> bytes:
    ctx = ssl.create_default_context()
    ca = os.environ.get("CCR_CA_BUNDLE") or "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):
        try:
            ctx.load_verify_locations(ca)
        except Exception:
            pass
    with urllib.request.urlopen(_request(url), timeout=timeout, context=ctx) as resp:
        return resp.read()


@dataclass
class ProbeResult:
    source: AssetSource
    ok: bool
    status: str
    bytes_read: int = 0

    def as_dict(self) -> Dict:
        return {
            "source": self.source.key,
            "domain": self.source.domain,
            "ok": self.ok,
            "status": self.status,
            "bytes": self.bytes_read,
        }


def probe_sources(sources: Sequence[AssetSource] = SOURCES) -> List[ProbeResult]:
    """Tải thử asset nhỏ từ mỗi nguồn; trả trạng thái từng domain."""
    results: List[ProbeResult] = []
    for src in sources:
        try:
            data = _http_fetch(src.probe_url, timeout=_TIMEOUT)
            # asset ảnh thật phải > vài KB và có magic hợp lệ (JPEG/PNG/WebP/GIF)
            ok = len(data) > 2048 and _looks_like_image(data)
            results.append(
                ProbeResult(src, ok, "200-ok" if ok else "unexpected-body", len(data))
            )
        except urllib.error.HTTPError as e:
            results.append(ProbeResult(src, False, f"http-{e.code}"))
        except urllib.error.URLError as e:
            results.append(ProbeResult(src, False, f"urlerror-{e.reason}"))
        except Exception as e:  # pragma: no cover - mạng bất định
            results.append(ProbeResult(src, False, f"error-{type(e).__name__}"))
    return results


def pick_source(sources: Sequence[AssetSource] = SOURCES) -> Optional[AssetSource]:
    """Nguồn đầu tiên còn tải được, theo thứ tự ưu tiên."""
    for r in probe_sources(sources):
        if r.ok:
            return r.source
    return None


def download_asset(url: str, dest_path: str, retries: int = 3) -> str:
    """Tải một URL cụ thể về file, có retry backoff. Trả path."""
    last = None
    for attempt in range(retries):
        try:
            data = _http_fetch(url)
            if not _looks_like_image(data):
                raise AssetUnavailable(
                    f"không phải ảnh ({len(data)}B) từ {url}")
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(data)
            return dest_path
        except Exception as e:  # pragma: no cover - phụ thuộc mạng
            last = e
            time.sleep(2 ** attempt)
    raise AssetUnavailable(f"không tải được {url}: {last}")


def download_first(urls: Sequence[str], dest_path: str) -> str:
    """Thử lần lượt danh sách URL (các nguồn khác nhau), lấy cái đầu tiên tải được."""
    errors = []
    for url in urls:
        try:
            return download_asset(url, dest_path, retries=2)
        except Exception as e:  # pragma: no cover
            errors.append(f"{url}: {e}")
    raise AssetUnavailable("tất cả nguồn đều lỗi:\n" + "\n".join(errors))
