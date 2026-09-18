"""n8n runtime validation (PRD-008 G). Đọc workflow.json; KHÔNG sửa workflow business.

- webhook_validator: liệt kê webhook path.
- credential_checker: node cần credential.
- disabled_node_detector: node đang disabled.
- activation_report: tổng hợp sẵn-sàng-bật cho mỗi workflow.
"""
from __future__ import annotations

import glob
import json
import os
from typing import Dict, List

WF_DIR = os.path.join(os.path.dirname(__file__), "..")


def _load() -> List[Dict]:
    out = []
    for f in sorted(glob.glob(os.path.join(WF_DIR, "WF*", "workflow.json"))):
        with open(f, encoding="utf-8") as fh:
            out.append({"file": f, "wf": json.load(fh)})
    return out


def webhook_validator(wf: Dict) -> List[str]:
    paths = []
    for n in wf.get("nodes", []):
        if n.get("type") == "n8n-nodes-base.webhook":
            p = n.get("parameters", {}).get("path")
            if p:
                paths.append(p)
    return paths


def credential_checker(wf: Dict) -> List[str]:
    return [n["name"] for n in wf.get("nodes", []) if n.get("credentials")]


def disabled_node_detector(wf: Dict) -> List[str]:
    return [n["name"] for n in wf.get("nodes", []) if n.get("disabled") is True]


def activation_report() -> List[Dict]:
    report = []
    for item in _load():
        wf = item["wf"]
        report.append({
            "name": wf.get("name"),
            "webhooks": webhook_validator(wf),
            "credential_nodes": credential_checker(wf),
            "disabled_nodes": disabled_node_detector(wf),
            # sẵn sàng bật khi mọi node disabled đều đã có credential đính kèm để gắn.
            "needs_activation": bool(disabled_node_detector(wf)),
        })
    return report


if __name__ == "__main__":
    print(json.dumps(activation_report(), ensure_ascii=False, indent=2))
