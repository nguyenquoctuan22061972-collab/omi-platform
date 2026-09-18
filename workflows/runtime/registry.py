"""n8n Workflow Registry (PRD-009 D): version, dependency, activation status, rollback mapping.

Chỉ metadata — KHÔNG sửa workflow business. Đối chiếu file workflow.json thực tế nếu có.
"""
from __future__ import annotations

import glob
import os
from typing import Dict, List

WF_DIR = os.path.join(os.path.dirname(__file__), "..")

# Đăng ký workflow (metadata). WF003 & future = 'planned'.
REGISTRY: Dict[str, Dict] = {
    "WF001": {"name": "Lead Ingestion", "version": "1.0", "depends_on": ["CRM Core"],
              "rollback_to": None, "planned": False},
    "WF002": {"name": "AI Auto-Tag & Routing", "version": "1.0", "depends_on": ["WF001", "CRM Core"],
              "rollback_to": None, "planned": False},
    "WF003": {"name": "Content Publish (future)", "version": "0.0", "depends_on": ["content-factory"],
              "rollback_to": None, "planned": True},
    "WF050": {"name": "Dashboard KPI Sync", "version": "1.0", "depends_on": ["CRM Core (CR-001)"],
              "rollback_to": None, "planned": False},
}


def _existing_files() -> Dict[str, str]:
    out = {}
    for f in glob.glob(os.path.join(WF_DIR, "WF*", "workflow.json")):
        wf_id = os.path.basename(os.path.dirname(f))
        out[wf_id] = f
    return out


def status() -> List[Dict]:
    """Kết hợp registry metadata + sự hiện diện file thực tế → activation status."""
    files = _existing_files()
    out = []
    for wf_id, meta in REGISTRY.items():
        has_file = wf_id in files
        out.append({
            "id": wf_id,
            "name": meta["name"],
            "version": meta["version"],
            "depends_on": meta["depends_on"],
            "planned": meta["planned"],
            "has_file": has_file,
            "activation": "planned" if meta["planned"] else ("importable" if has_file else "missing"),
            "rollback_to": meta["rollback_to"],
        })
    return out


def rollback_mapping() -> Dict[str, str]:
    return {wf: (m["rollback_to"] or "re-import bản Git trước") for wf, m in REGISTRY.items()}


if __name__ == "__main__":
    import json
    print(json.dumps(status(), ensure_ascii=False, indent=2))
