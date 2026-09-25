"""CRM SQLite → Supabase migration PLANNER (PR-003). DRY-RUN, không network.

REUSE (không fork): đọc schema/dữ liệu SQLite bằng apps/crm-core/src/crm/db.py.
Sinh kế hoạch: bảng đích, số hàng, và câu INSERT PostgREST-friendly để nạp qua service_role.
Không kết nối Supabase (cần SUPABASE_URL + service key — PR-003 permission).
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "apps", "crm-core", "src"))
from crm import db as crm_db  # noqa: E402  (reuse SQLite layer)

TABLES = {
    "contacts": ["id", "name", "phone", "email", "source", "tags", "created_at"],
    "conversations": ["id", "contact_id", "channel", "message", "timestamp"],
    "pipeline": ["contact_id", "stage"],
}


def plan(sqlite_path: str = ":memory:") -> Dict:
    """Trả kế hoạch migrate: mỗi bảng -> số hàng + hàng (để đẩy qua PostgREST)."""
    conn = crm_db.connect(sqlite_path)
    crm_db.init_db(conn)
    out: Dict[str, Dict] = {}
    for table, cols in TABLES.items():
        try:
            rows = conn.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
            out[table] = {"columns": cols, "row_count": len(rows),
                          "rows": [dict(r) for r in rows]}
        except Exception as e:
            out[table] = {"columns": cols, "row_count": 0, "error": str(e)}
    conn.close()
    return {"tables": out, "target": "supabase", "mode": "dry-run",
            "total_rows": sum(t["row_count"] for t in out.values())}


def postgrest_endpoints(supabase_url: str = "<SUPABASE_URL>") -> Dict[str, str]:
    """Endpoint PostgREST cho n8n (service_role key ở credential, không ở đây)."""
    base = supabase_url.rstrip("/") + "/rest/v1"
    return {t: f"{base}/{t}" for t in TABLES}
