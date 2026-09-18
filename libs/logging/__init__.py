"""Structured logging (PRD-008 B). Additive — không sửa logger cũ.

JSON log + request_id/correlation_id + level + audit event + rotation config.
"""
from .structured import (
    JsonFormatter,
    get_logger,
    new_request_id,
    new_correlation_id,
    audit_event,
    rotation_config,
)

__all__ = [
    "JsonFormatter",
    "get_logger",
    "new_request_id",
    "new_correlation_id",
    "audit_event",
    "rotation_config",
]
