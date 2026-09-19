"""Log shipping providers (PRD-012 C). Additive — không sửa structured.py.

Interface thống nhất: file (mặc định), DB (stub), remote shipper (stub). Không gửi thật
ở stub; DB/remote chỉ buffer + đánh dấu dry-run tới khi có credential/driver.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Protocol


class LogShipper(Protocol):
    name: str
    def ship(self, record: Dict) -> Dict: ...


class FileShipper:
    """Mặc định: ghi 1 dòng JSON/record ra file (append)."""
    name = "file"

    def __init__(self, path: str = "logs/app.log"):
        self.path = path

    def ship(self, record: Dict) -> Dict:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return {"shipped": True, "provider": self.name, "path": self.path}


class DBShipper:
    """Stub DB shipper — buffer trong bộ nhớ; cắm driver thật sau (dry-run)."""
    name = "db"

    def __init__(self):
        self.buffer: List[Dict] = []

    def ship(self, record: Dict) -> Dict:
        self.buffer.append(record)
        return {"shipped": False, "provider": self.name, "mode": "dry-run", "buffered": len(self.buffer)}


class RemoteShipper:
    """Stub remote shipper (Loki/ELK...) — chỉ đọc endpoint env, KHÔNG gửi thật."""
    name = "remote"

    def __init__(self, env=None):
        env = env or {}
        self.endpoint_configured = bool(env.get("LOG_SHIPPER_URL"))
        self.buffer: List[Dict] = []

    def ship(self, record: Dict) -> Dict:
        self.buffer.append(record)
        return {"shipped": False, "provider": self.name, "mode": "dry-run",
                "configured": self.endpoint_configured}


def default_shipper(path: str = "logs/app.log") -> FileShipper:
    return FileShipper(path)
