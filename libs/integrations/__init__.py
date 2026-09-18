"""OMI integration adapters (PRD-006 Module D).

Interface thống nhất, credential từ env, DRY-RUN (không gọi API thật).
"""
from .base import Adapter, DryRunResult
from .registry import ADAPTERS, get_adapter, list_adapters

__all__ = ["Adapter", "DryRunResult", "ADAPTERS", "get_adapter", "list_adapters"]
