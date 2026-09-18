"""Zalo OA adapter (dry-run). Credential env: ZALO_OA_ID, ZALO_OA_ACCESS_TOKEN."""
from .base import Adapter


class ZaloOaAdapter(Adapter):
    name = "zalo_oa"
    required_env = ["ZALO_OA_ID", "ZALO_OA_ACCESS_TOKEN"]
