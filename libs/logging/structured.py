"""JSON structured logging helpers (PRD-008 B). Stdlib only; không đụng logging gốc."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict


def new_request_id() -> str:
    return "req_" + uuid.uuid4().hex[:16]


def new_correlation_id() -> str:
    return "cor_" + uuid.uuid4().hex[:16]


class JsonFormatter(logging.Formatter):
    """Format log record thành 1 dòng JSON; kèm request_id/correlation_id nếu có."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in ("request_id", "correlation_id", "event", "actor", "target"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = "omi", level: int = logging.INFO) -> logging.Logger:
    """Logger riêng có JSON handler. KHÔNG chạm root logger (không sửa logger cũ)."""
    logger = logging.getLogger(f"omi.{name}")
    logger.setLevel(level)
    logger.propagate = False  # không lan sang root/logger cũ
    if not any(isinstance(h.formatter, JsonFormatter) for h in logger.handlers):
        h = logging.StreamHandler()
        h.setFormatter(JsonFormatter())
        logger.addHandler(h)
    return logger


def audit_event(logger: logging.Logger, event: str, actor: str = "", target: str = "", **extra) -> None:
    """Ghi 1 audit event ở mức INFO (không log secret — caller tự tránh)."""
    logger.info(event, extra={"event": event, "actor": actor, "target": target, **{
        "request_id": extra.get("request_id"),
        "correlation_id": extra.get("correlation_id"),
    }})


def rotation_config(path: str = "/var/log/omi/app.log", max_bytes: int = 10_485_760, backups: int = 7) -> Dict:
    """Cấu hình RotatingFileHandler đề xuất (dùng ở runtime, không bắt buộc)."""
    return {"class": "logging.handlers.RotatingFileHandler", "filename": path,
            "maxBytes": max_bytes, "backupCount": backups, "formatter": "json"}
