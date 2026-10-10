"""AFFOS Experiment Lifecycle + Policy/Budget Gate + Result Contract (MONEY-03/06/08).

Pure domain layer (stdlib only). REUSE: economics, attribution, proof, provenance, money_status.
Does NOT create a new orchestrator, does NOT duplicate proof/attribution/cost math, does NOT
touch the network. A persisted experiment row lives in the `experiments` table; this module is
the in-memory state machine + gates a caller drives and then writes through the repository.

Lifecycle:
    DRAFT → NEEDS_APPROVAL → APPROVED → RUNNING → MEASURED → WIN | ITERATE | KILL
  - Invalid transitions are blocked.
  - KILL is always reachable from a non-terminal state (kill switch).
  - ITERATE loops back to DRAFT for a new round. WIN and KILL are terminal.
  - Every transition records an audit event (event, actor, target, reason, from, to, ts).
  - Idempotency: a transition carrying an already-seen event_id is a no-op.
Experiment STATE is never revenue proof — only proof.real_commerce_proof over verified
production data proves revenue.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "attribution"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "economics"))
import attribution     # noqa: E402
import proof           # noqa: E402

TERMINAL = {"WIN", "KILL"}
ALLOWED = {
    "DRAFT": {"NEEDS_APPROVAL", "KILL"},
    "NEEDS_APPROVAL": {"APPROVED", "DRAFT", "KILL"},
    "APPROVED": {"RUNNING", "KILL"},
    "RUNNING": {"MEASURED", "KILL"},
    "MEASURED": {"WIN", "ITERATE", "KILL"},
    "WIN": set(),
    "ITERATE": {"DRAFT"},
    "KILL": set(),
}
POLICY_REQUIRED = ["max_budget", "max_loss", "currency", "traffic_source",
                   "measurement_window", "attribution_method", "success_criteria", "stop_criteria"]


class InvalidTransition(Exception):
    pass


class PolicyViolation(Exception):
    pass


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def policy_gate(policy: Dict) -> Dict:
    """Budget/policy readiness. Must pass before RUNNING. Paid spend defaults to 0."""
    policy = policy or {}
    blocked: List[str] = []
    for k in POLICY_REQUIRED:
        v = policy.get(k)
        if v is None or v == "" or v == []:
            blocked.append(f"missing:{k}")
    mb = policy.get("max_budget")
    if isinstance(mb, (int, float)) and mb <= 0:
        blocked.append("max_budget_must_be_positive")
    ml = policy.get("max_loss")
    if isinstance(ml, (int, float)) and ml < 0:
        blocked.append("max_loss_negative")
    paid = policy.get("paid_spend", 0) or 0
    if paid > 0 and not policy.get("ceo_approved"):
        blocked.append("paid_spend_requires_ceo_approval")
    return {"ok": not blocked, "blocked": blocked}


class Experiment:
    def __init__(self, exp_id: str, hypothesis: str = "", campaign_id: str = "",
                 policy: Optional[Dict] = None, status: str = "DRAFT"):
        self.id = exp_id
        self.hypothesis = hypothesis
        self.campaign_id = campaign_id
        self.policy = dict(policy or {})
        self.status = status
        self.audit: List[Dict] = []
        self._seen = set()           # processed event ids (idempotency)
        self.created_at = _ts()

    # ---- core transition with guards + audit + idempotency ----
    def transition(self, to: str, actor: str, reason: str = "", event_id: Optional[str] = None) -> Dict:
        if event_id is not None and event_id in self._seen:
            return {"status": self.status, "idempotent": True}
        # Fail CLOSED and record the rejection in the audit trail before raising.
        try:
            if self.status in TERMINAL:
                raise InvalidTransition(f"{self.status} là trạng thái cuối, không thể chuyển sang {to}")
            if to not in ALLOWED.get(self.status, set()):
                raise InvalidTransition(f"không hợp lệ: {self.status} → {to}")
            if to == "APPROVED" and not self.policy.get("ceo_approved"):
                raise PolicyViolation("APPROVED yêu cầu ceo_approved=True")
            if to == "RUNNING":
                g = policy_gate(self.policy)
                if not g["ok"]:
                    raise PolicyViolation(f"budget/policy chưa đạt: {g['blocked']}")
        except (InvalidTransition, PolicyViolation) as e:
            self.audit.append({"event": "blocked", "actor": actor, "target": self.id,
                               "reason": (reason + " :: " + str(e)).strip(" :"),
                               "from": self.status, "to": to, "ts": _ts()})
            raise
        frm = self.status
        self.status = to
        if event_id is not None:
            self._seen.add(event_id)
        self.audit.append({"event": "transition", "actor": actor, "target": self.id,
                           "reason": reason, "from": frm, "to": to, "ts": _ts()})
        return {"status": self.status, "idempotent": False}

    # ---- convenience wrappers ----
    def submit(self, actor, reason="", event_id=None):   return self.transition("NEEDS_APPROVAL", actor, reason, event_id)
    def approve(self, actor, reason="", event_id=None):  return self.transition("APPROVED", actor, reason, event_id)
    def start(self, actor, reason="", event_id=None):    return self.transition("RUNNING", actor, reason, event_id)
    def measure(self, actor, reason="", event_id=None):  return self.transition("MEASURED", actor, reason, event_id)
    def decide(self, outcome, actor, reason="", event_id=None):
        if outcome not in ("WIN", "ITERATE", "KILL"):
            raise InvalidTransition(f"outcome không hợp lệ: {outcome}")
        return self.transition(outcome, actor, reason, event_id)
    def kill(self, actor, reason="", event_id=None):     return self.transition("KILL", actor, reason, event_id)

    # ---- persistence (reuses repository + experiments/audit_logs tables; no new store) ----
    def save(self, repo) -> None:
        """Persist status + a durable JSON state snapshot + append-only audit rows. Idempotent."""
        repo.insert("experiments", {"id": self.id, "campaign_id": self.campaign_id,
                                    "hypothesis": self.hypothesis, "variant": "", "metric": "",
                                    "status": self.status, "created_at": self.created_at})
        repo.insert("audit_logs", {"id": f"EXPSTATE-{self.id}", "event": "experiment.state",
                                   "actor": "system", "target": self.id, "ts": _ts(),
                                   "meta": json.dumps({"status": self.status, "policy": self.policy,
                                                       "seen": sorted(self._seen), "audit": self.audit})})
        for i, a in enumerate(self.audit):   # append-only trail as individual rows (idempotent by id)
            repo.insert("audit_logs", {"id": f"EXPAUD-{self.id}-{i}", "event": "experiment." + a["event"],
                                       "actor": a.get("actor", ""), "target": self.id, "ts": a.get("ts", ""),
                                       "meta": json.dumps(a)})

    @classmethod
    def load(cls, repo, exp_id: str) -> "Experiment":
        """Rebuild an experiment from persisted state (survives process restart)."""
        erows = repo.query("SELECT * FROM experiments WHERE id = ?", (exp_id,))
        if not erows:
            raise KeyError(f"experiment không tồn tại: {exp_id}")
        er = erows[0]
        snap = repo.query("SELECT meta FROM audit_logs WHERE id = ?", (f"EXPSTATE-{exp_id}",))
        state = json.loads(snap[0]["meta"]) if snap else {}
        e = cls(exp_id, hypothesis=er.get("hypothesis") or "", campaign_id=er.get("campaign_id") or "",
                policy=state.get("policy") or {}, status=state.get("status") or er.get("status") or "DRAFT")
        e._seen = set(state.get("seen") or [])
        e.audit = state.get("audit") or []
        e.created_at = er.get("created_at") or e.created_at
        return e


def experiment_result(repo, experiment: Experiment, costs: Optional[Dict] = None) -> Dict:
    """Per-experiment result contract. Single currency (from policy); never mixes currencies.

    Distinguishes FORECAST/SEED vs LIVE-unverified vs PRODUCTION-verified. revenue_proven is
    True only with verified production data AND end-to-end attribution linkage.
    """
    costs = costs or {}
    cur = experiment.policy.get("currency", "USD")
    per = attribution.per_campaign(repo).get(
        experiment.campaign_id, {"clicks": 0, "conversions": 0, "revenue": 0.0, "epc": 0.0, "cr": 0.0})
    tot = attribution.totals(repo, currency=cur,
                             ai_cost=costs.get("ai_cost", 0), content_cost=costs.get("content_cost", 0),
                             infrastructure_cost=costs.get("infrastructure_cost", 0),
                             advertising_cost=costs.get("advertising_cost", 0))
    pr = proof.real_commerce_proof(repo, campaign_id=experiment.campaign_id)
    data_state = tot.get("data_state", "DRY_RUN")
    revenue_proven = bool(pr["status"] == "VERIFIED" and pr.get("attribution_linked")
                          and tot.get("is_verified"))
    if revenue_proven and data_state == "PRODUCTION_VERIFIED":
        evidence = "PRODUCTION_VERIFIED"
    elif data_state == "LIVE":
        evidence = "LIVE_UNVERIFIED"
    else:
        evidence = "FORECAST_OR_SEED"
    return {
        "experiment_id": experiment.id, "campaign_id": experiment.campaign_id,
        "status": experiment.status, "currency": cur,
        "attributable_clicks": per.get("clicks", 0),
        "attributable_conversions": per.get("conversions", 0),
        "gross_revenue": tot.get("gross_revenue", tot.get("revenue")),
        "refunds": tot.get("refunds", 0.0),
        "net_revenue": tot.get("revenue"),
        "net_contribution_profit": tot.get("contribution_profit"),
        "revenue_label": tot.get("revenue_label"),
        "data_state": data_state, "evidence_class": evidence,
        "attribution_linked": pr.get("attribution_linked", False),
        "revenue_proven": revenue_proven,
        "proof": pr,
        "note": "experiment status ≠ revenue proof; revenue_proven requires verified production "
                "transaction + attribution linkage",
    }
