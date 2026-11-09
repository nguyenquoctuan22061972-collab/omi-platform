"""AFFOS real provider-adapter FRAMEWORK (COST-1). Turns a per-provider ProviderSpec into a
provider_runner `Adapter` ((topic, stage) -> ProviderResult): read the credential (name only, from env;
never logged), build the request, call an INJECTED transport, parse the response into artifact +
billed_usd + usage.

HONESTY / SAFETY:
  * The real HTTP call lives behind an INJECTED `transport`. Tests inject a fake transport -> ZERO network,
    ZERO cost. The real HTTPS transport (`https_transport`) is used only when the caller deliberately passes
    it AND provider_runner is live + credentialed (see provider_runner's gate). Nothing fires on import.
  * Per-provider endpoint/body/parse are NOT shipped as verified values. `reference_specs()` returns each
    provider UNCONFIGURED (empty endpoint); a call to an unconfigured adapter raises AdapterNotConfigured.
    The operator fills endpoint/build_body/parse and **VERIFIES each against the provider's real API docs**
    (auth header name, request body, response fields for the artifact and the billed cost) before going live.
  * Credentials are read by env-var NAME only (provider_runner.CREDENTIAL_ENV); values are never read into
    logs or returned. No secret appears in this module.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from provider_runner import ProviderResult, CREDENTIAL_ENV

# transport: (method, url, headers, body|None) -> (status:int, response_json:dict). Injected (fake in tests).
Transport = Callable[[str, str, Dict[str, str], Optional[dict]], Tuple[int, dict]]


class AdapterNotConfigured(RuntimeError):
    """A provider's ProviderSpec has no endpoint yet — fill + VERIFY it against the real API before live use."""


def https_transport(method: str, url: str, headers: Dict[str, str], body: Optional[dict]) -> Tuple[int, dict]:
    """Real HTTPS transport. Invoked ONLY when the caller deliberately wires it into a live, credentialed run."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:            # real network — never reached in tests/CI
        raw = r.read().decode() or "{}"
        return r.status, (json.loads(raw) if raw.strip() else {})


def _generic_parse(resp: dict) -> ProviderResult:
    """Best-effort response -> ProviderResult. VERIFY/replace per provider: map the real artifact field and the
    real billed-cost field. billed_usd stays None if the provider does not report a cost (reconcile later)."""
    artifact = resp.get("artifact") or resp.get("url") or resp.get("output") or ""
    cost = resp.get("cost_usd", resp.get("billed_usd"))
    return ProviderResult(artifact=str(artifact),
                          billed_usd=(None if cost is None else float(cost)),
                          usage=resp.get("usage") or {})


@dataclass
class ProviderSpec:
    """How to call ONE provider. Every field must be VERIFIED against the provider's API docs before live use."""
    endpoint: str = ""                                            # "" = UNCONFIGURED -> adapter refuses
    auth_header: str = "Authorization"                           # e.g. "Authorization" or "xi-api-key"
    auth_prefix: str = "Bearer "                                 # "" for a bare key header
    method: str = "POST"
    build_body: Callable[[str, str], Optional[dict]] = field(
        default=lambda topic, stage: {"input": topic, "stage": stage})
    parse: Callable[[dict], ProviderResult] = field(default=_generic_parse)


def make_adapter(provider: str, spec: ProviderSpec, *, transport: Transport,
                 env: Optional[Dict[str, str]] = None):
    """Build an Adapter((topic, stage) -> ProviderResult) for `provider`. The returned adapter reads the
    credential by NAME from env, builds the request, calls `transport`, and parses the response."""
    env = env if env is not None else os.environ
    cred_name = CREDENTIAL_ENV.get(provider, f"AFFOS_{provider.upper()}_API_KEY")

    def adapter(topic: str, stage: str) -> ProviderResult:
        if not spec.endpoint:
            raise AdapterNotConfigured(
                f"provider '{provider}' has no endpoint configured — fill its ProviderSpec and VERIFY "
                f"against the provider's API before enabling live")
        key = env.get(cred_name)
        if not key:
            raise RuntimeError(f"missing credential env '{cred_name}' for provider '{provider}'")  # value never logged
        headers = {"Content-Type": "application/json", spec.auth_header: f"{spec.auth_prefix}{key}"}
        status, resp = transport(spec.method, spec.endpoint, headers, spec.build_body(topic, stage))
        if status // 100 != 2:
            raise RuntimeError(f"provider '{provider}' API returned HTTP {status}")
        return spec.parse(resp)

    return adapter


def reference_specs() -> Dict[str, ProviderSpec]:
    """UNCONFIGURED reference specs for the paid providers (endpoint='' -> each adapter refuses until filled).
    The auth-header hints below are a STARTING POINT — VERIFY every one against the provider's real API docs,
    then set endpoint/build_body/parse accordingly."""
    return {
        "model": ProviderSpec(auth_header="Authorization", auth_prefix="Bearer "),      # LLM: script
        "canva": ProviderSpec(auth_header="Authorization", auth_prefix="Bearer "),      # thumbnail
        "elevenlabs": ProviderSpec(auth_header="xi-api-key", auth_prefix=""),           # video/voice
        "vidiq": ProviderSpec(auth_header="Authorization", auth_prefix="Bearer "),      # publish/metadata
    }


def build_adapters(specs: Optional[Dict[str, ProviderSpec]] = None, *, transport: Transport,
                   env: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Build {provider: adapter} for provider_runner. Pass configured `specs` (+ real `transport`) for live use;
    defaults to reference_specs() (unconfigured -> adapters refuse until the operator fills + verifies them)."""
    specs = specs if specs is not None else reference_specs()
    return {p: make_adapter(p, s, transport=transport, env=env) for p, s in specs.items()}
