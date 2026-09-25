"""Docker/n8n/Nginx compatibility checker (PRD-016). Static, offline.
Xác minh workflow dùng node built-in n8n, không $env, và tham chiếu hạ tầng hợp lệ."""
from __future__ import annotations

import json
import os
from typing import Dict, List

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUILTIN = {"n8n-nodes-base.webhook", "n8n-nodes-base.set", "n8n-nodes-base.function",
           "n8n-nodes-base.httpRequest", "n8n-nodes-base.telegram"}


def check_workflow(path: str) -> Dict:
    wf = json.load(open(path, encoding="utf-8"))
    types = [n["type"] for n in wf["nodes"]]
    non_builtin = [t for t in types if t not in BUILTIN]
    return {
        "workflow": os.path.basename(path),
        "nodes": len(wf["nodes"]),
        "all_builtin": not non_builtin,      # community node = cần cài thêm trên n8n
        "non_builtin": non_builtin,
        "uses_env": "$env" in json.dumps(wf),
        "has_retry": any(n.get("retryOnFail") for n in wf["nodes"]),
    }


def check_infra() -> Dict:
    compose = os.path.join(_ROOT, "deploy", "docker-compose.prod.yml")
    nginx = os.path.join(_ROOT, "deploy", "nginx", "conf.d", "omi.conf")
    return {
        "compose_present": os.path.isfile(compose),
        "nginx_conf_present": os.path.isfile(nginx),
    }


def report(workflows: List[str]) -> Dict:
    wfs = [check_workflow(os.path.join(_ROOT, "workflows", w)) for w in workflows]
    infra = check_infra()
    compatible = (all(w["all_builtin"] and not w["uses_env"] for w in wfs)
                  and infra["compose_present"] and infra["nginx_conf_present"])
    return {"compatible": compatible, "workflows": wfs, "infra": infra}
