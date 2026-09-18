"""Vertex AI adapter (dry-run). Credential env: GCP_PROJECT, GCP_LOCATION, VERTEX_MODEL.

Auth qua Application Default Credentials ở runtime (không lưu key trong repo).
"""
from .base import Adapter


class VertexAiAdapter(Adapter):
    name = "vertex_ai"
    required_env = ["GCP_PROJECT", "GCP_LOCATION", "VERTEX_MODEL"]
