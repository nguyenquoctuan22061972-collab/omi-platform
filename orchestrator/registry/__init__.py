"""Capability Registry v2 (PRD-014 A). Registry giàu metadata + version constraint,
bridge sang CapabilityDispatcher (reuse). Không đọc/sửa capability-map.md."""
from .registry_v2 import CapabilityRegistryV2, CapabilitySpec

__all__ = ["CapabilityRegistryV2", "CapabilitySpec"]
