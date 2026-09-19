"""Lead Engine (PRD-010 C). Capture + email queue + notify + webhook + CRM mapping. Mock."""
from .engine import LeadEngine, EmailQueue, crm_mapping

__all__ = ["LeadEngine", "EmailQueue", "crm_mapping"]
