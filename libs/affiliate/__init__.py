"""Affiliate Registry (PRD-010 B). Networks + UTM + deep-link; env-based, không hardcode."""
from .registry import AffiliateRegistry, NETWORKS, build_utm, deep_link

__all__ = ["AffiliateRegistry", "NETWORKS", "build_utm", "deep_link"]
