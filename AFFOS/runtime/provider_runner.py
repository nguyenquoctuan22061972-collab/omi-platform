"""AFFOS real provider-runner (Phase-0 COST-1) — the missing link for a REAL (billed) baseline.

It produces a `real_runner_factory(topic) -> runner(stage)` compatible with `baseline_runner.run_baseline`,
where a paid stage calls a real provider (model → script, canva → thumbnail, elevenlabs → video,
vidiq → publish). Free/cached stages (topic/research/qa) return a placeholder, no provider, no cost.

DRY-RUN-SAFE BY CONSTRUCTION — it is IMPOSSIBLE to spend by accident:
  * Paid stages are REFUSED (raise ProvidersDisabled) unless BOTH are true:
      - `live=True` (the deliberate switch; the MODE-B driver sets it from AFFOS_PROVIDERS_LIVE=1), AND
      - the stage's provider CREDENTIAL env var is present (value from the secret store; never read/logged here).
  * The actual provider HTTP call lives in a PLUGGABLE adapter injected by the caller — not in this module.
    So real API clients drop in and get credentialed without this committed code ever making a real/paid call.
  * With no adapter, or disabled, or missing credential -> it raises before any call. Default `live=False`.

Reconciliation: each adapter returns a ProviderResult(artifact, billed_usd, usage). Captured usage is recorded
into an optional `usage_sink`; `reconcile_billed(ledger, usage_sink, topics)` then calls confirm_stage so the
ledger's estimate is overridden by the provider's real billed cost. No secret is read or logged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# Paid stages -> provider name. Stages not here (topic/research/qa) are free/cached (no provider call).
STAGE_PROVIDER: Dict[str, str] = {"script": "model", "thumbnail": "canva", "video": "elevenlabs", "publish": "vidiq"}
# Credential env var NAMES per provider (values come from the secret store at run time — never committed/logged).
CREDENTIAL_ENV: Dict[str, str] = {"model": "AFFOS_MODEL_API_KEY", "canva": "AFFOS_CANVA_API_KEY",
                                  "elevenlabs": "AFFOS_ELEVENLABS_API_KEY", "vidiq": "AFFOS_VIDIQ_API_KEY"}


class ProvidersDisabled(RuntimeError):
    """A paid stage was requested but the runner is not live, is missing a credential, or has no adapter.
    Raised BEFORE any provider call — so a disabled/misconfigured runner can never spend."""


@dataclass
class ProviderResult:
    artifact: str
    billed_usd: Optional[float] = None      # provider-reported real cost, if known (feeds confirm_stage)
    usage: Dict = field(default_factory=dict)


# An adapter is: (topic, stage) -> ProviderResult. It is where a REAL API call would live. Injected by the caller.
Adapter = Callable[[str, str], ProviderResult]


class ProviderRunner:
    def __init__(self, adapters: Dict[str, Adapter], *, live: bool = False,
                 env: Optional[Dict[str, str]] = None, usage_sink: Optional[List[Dict]] = None,
                 free_artifact: Callable[[str], str] = lambda s: f"[free:{s}]"):
        self.adapters = adapters or {}
        self.live = bool(live)
        self.env = env if env is not None else os.environ
        self.usage_sink = usage_sink
        self.free_artifact = free_artifact

    def _runner(self, topic: str) -> Callable[[str], str]:
        def run(stage: str) -> str:
            provider = STAGE_PROVIDER.get(stage)
            if provider is None:
                return self.free_artifact(stage)                 # free/cached stage: no provider, no cost
            if not self.live:
                raise ProvidersDisabled(
                    f"providers not live (set AFFOS_PROVIDERS_LIVE=1 and pass live=True); "
                    f"stage '{stage}' -> provider '{provider}' refused")
            cred = CREDENTIAL_ENV.get(provider)
            if cred and not self.env.get(cred):
                raise ProvidersDisabled(f"missing credential env '{cred}' for provider '{provider}' (stage '{stage}')")
            adapter = self.adapters.get(provider)
            if adapter is None:
                raise ProvidersDisabled(f"no adapter wired for provider '{provider}' (stage '{stage}')")
            res = adapter(topic, stage)                          # <-- the ONLY place a real paid call happens
            if self.usage_sink is not None:
                self.usage_sink.append({"topic": topic, "stage": stage, "provider": provider,
                                        "billed_usd": res.billed_usd, "usage": res.usage})
            return res.artifact
        return run

    def factory(self) -> Callable[[str], Callable[[str], str]]:
        """Return a real_runner_factory(topic) for baseline_runner.run_baseline."""
        return self._runner


def live_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    """The deliberate switch: live only when AFFOS_PROVIDERS_LIVE == '1'."""
    return (env if env is not None else os.environ).get("AFFOS_PROVIDERS_LIVE") == "1"


def reconcile_billed(ledger, usage_sink: List[Dict], topics: List[str]) -> int:
    """After a run, override each stage's estimate with the provider's real billed cost (confirm_stage).
    Maps a sink entry's topic -> run_id 'r{i+1}' using the same ordering as baseline_runner. Returns the
    number of confirmations written. Entries with no billed_usd are skipped (left as estimates)."""
    from pilot_metering import confirm_stage
    n = 0
    for e in usage_sink:
        if e.get("billed_usd") is None:
            continue
        try:
            run_id = f"r{topics.index(e['topic']) + 1}"
        except ValueError:
            continue
        confirm_stage(ledger, run_id, e["stage"], float(e["billed_usd"]))
        n += 1
    return n


def mock_adapters(prices: Optional[Dict[str, float]] = None) -> Dict[str, Adapter]:
    """Offline test/dev adapters — NO network, NO cost. billed_usd comes from `prices` (per provider)."""
    prices = prices or {"model": 0.02, "canva": 0.05, "elevenlabs": 0.30, "vidiq": 0.00}

    def make(provider):
        def adapter(topic: str, stage: str) -> ProviderResult:
            return ProviderResult(artifact=f"[{provider}:{stage}:{topic}]",
                                  billed_usd=prices.get(provider), usage={"provider": provider, "mock": True})
        return adapter

    return {p: make(p) for p in STAGE_PROVIDER.values()}
