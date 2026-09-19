"""Runtime env loader (PRD-011 A). Fail-fast khi thiếu; không hardcode; không in secret.

Dùng bởi preflight/go-live để chặn khởi động khi thiếu env core. KHÔNG sửa app cũ
(auth-rbac giữ nguyên default dev của nó) — đây là lớp kiểm tra additive.
"""
from __future__ import annotations

from typing import Dict, List, Mapping

# Env core bắt buộc để go-live (đúng 3 biến go-live.sh dừng ở preflight).
RUNTIME_REQUIRED: List[str] = ["AUTH_SECRET", "CRM_BASE", "N8N_BASE_URL"]


class MissingEnvError(RuntimeError):
    """Ném khi thiếu env bắt buộc (fail-fast)."""


def require_env(env: Mapping[str, str], keys: List[str] | None = None) -> Dict[str, str]:
    """Trả dict các biến bắt buộc; thiếu bất kỳ biến nào → MissingEnvError (fail-fast).

    Không log/in giá trị. `env` truyền vào (vd os.environ) — không hardcode.
    """
    keys = keys or RUNTIME_REQUIRED
    missing = [k for k in keys if not (env.get(k) or "").strip()]
    if missing:
        raise MissingEnvError("Thiếu env bắt buộc: " + ", ".join(missing))
    return {k: env[k] for k in keys}


def load_runtime_env(env: Mapping[str, str]) -> Dict[str, str]:
    """Alias fail-fast cho toàn bộ RUNTIME_REQUIRED."""
    return require_env(env, RUNTIME_REQUIRED)


def env_report(env: Mapping[str, str], keys: List[str] | None = None) -> List[Dict]:
    """Báo cáo PASS/FAIL từng biến (KHÔNG in giá trị)."""
    keys = keys or RUNTIME_REQUIRED
    return [{"key": k, "present": bool((env.get(k) or "").strip())} for k in keys]
