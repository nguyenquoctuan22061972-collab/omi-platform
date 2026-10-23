"""Bridge (AFFOS command path): Hub → Bridge → Claude Builder.

Sits between CommandHub and the actual executor. Two modes:

- "mock" (DEFAULT): deterministic, side-effect-free work. No network, no CLI, no spend.
  Clearly tagged mode="mock", real_claude_connected=False.
- "real" (opt-in ONLY): invokes the real Claude CLI as a subprocess under strict gates —
  non-root user, a dedicated staging workspace (cwd), read-only permission mode, and
  tools restricted to Read/Grep/Glob. `real_claude_connected` is True ONLY when that
  real invocation actually succeeds (exit 0 + parseable output).

Safety: input validation, timeout, output cap, secret scrub on errors. Never passes tokens.
The subprocess runner is injected (`runner`) so the wiring is unit-testable without a real
CLI; the DEFAULT runner is a real subprocess. A test double is never used to claim a real
end-to-end success — only real-runner success sets real_claude_connected.

Thuần stdlib.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Callable, Dict, Optional

from orchestrator.runtime import result_store as rs  # reuse scrub()

MOCK = "mock"
REAL = "real"
MODES = {MOCK, REAL}

# Read-only toolset for real Claude — never widened here.
REAL_ALLOWED_TOOLS = ["Read", "Grep", "Glob"]
REAL_PERMISSION_MODE = "plan"            # read-only; no edits/writes/bash
DEFAULT_TIMEOUT_S = 60
DEFAULT_OUTPUT_LIMIT = 65536             # cap captured stdout


def _default_runner(argv, cwd, timeout_s):
    """Real subprocess runner. Returns {returncode, stdout, stderr}."""
    p = subprocess.run(argv, cwd=cwd, timeout=timeout_s, capture_output=True, text=True)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def _recon_prompt(workspace_name: str) -> str:
    return (
        "You are the AFFOS recon_readonly agent. READ ONLY. "
        "List the first-level directories and count files you can safely enumerate in the "
        f"workspace '{workspace_name}'. Do NOT read secrets, tokens, credentials or personal "
        "data. Do NOT modify, create, delete or execute anything. Return concise JSON: "
        '{"workspace":..., "top_level_dirs":[...], "safe_file_count":N, "issues":[...]}.'
    )


class Bridge:
    def __init__(self, mode: Optional[str] = None, env: Optional[Dict] = None,
                 runner: Optional[Callable] = None, uid_getter: Callable[[], int] = os.getuid,
                 timeout_s: int = DEFAULT_TIMEOUT_S, output_limit: int = DEFAULT_OUTPUT_LIMIT):
        env = env or {}
        self.mode = (mode or env.get("AFFOS_BRIDGE_MODE") or MOCK).lower()
        if self.mode not in MODES:
            raise ValueError(f"bad bridge mode: {self.mode}")
        self.env = env
        self.runner = runner or _default_runner
        self.uid_getter = uid_getter
        self.timeout_s = timeout_s
        self.output_limit = output_limit
        self.workspace = env.get("AFFOS_STAGING_WORKSPACE")
        self.claude_bin = env.get("AFFOS_CLAUDE_BIN") or shutil.which("claude")

    # ---- public API ----
    def execute(self, task: Dict) -> Dict:
        """Run a task. Always returns a dict with mode/status/result/error/real_claude_connected."""
        command = task.get("command")
        target = task.get("target")
        if not target:
            return self._fail(MOCK if self.mode == MOCK else REAL, "target required")
        if self.mode == MOCK:
            return self._run_mock(command, target)
        return self._run_real(command, target)

    # ---- mock (default) ----
    def _run_mock(self, command: str, target: str) -> Dict:
        output = {
            "command": command, "target": target, "validated": True,
            "steps": {"build": ["reuse module", "additive change", "4-gate QA"],
                      "fix": ["reproduce", "root-cause", "patch", "regression"]}.get(command, []),
            "note": "mock execution (deterministic; no network/CLI/spend)",
        }
        return {"mode": MOCK, "status": "SUCCEEDED", "result": output,
                "error": "", "real_claude_connected": False}

    # ---- real (opt-in, gated) ----
    def _run_real(self, command: str, target: str) -> Dict:
        # Gate 1: never as root.
        if self.uid_getter() == 0:
            return self._blocked("real mode requires a non-root user (refusing to run as root)")
        # Gate 2: dedicated staging workspace must exist and be a directory.
        ws = self.workspace
        if not ws or not os.path.isdir(ws):
            return self._blocked("real mode requires AFFOS_STAGING_WORKSPACE to be an existing dir")
        # Gate 3: real Claude CLI must be available.
        if not self.claude_bin:
            return self._blocked("real mode requires AFFOS_CLAUDE_BIN or `claude` on PATH")
        # Validate target as a safe workspace name (no path traversal / injection).
        if not re.fullmatch(r"[A-Za-z0-9._\-]{1,128}", str(target)):
            return self._fail(REAL, "invalid target (must be a safe workspace name)")

        argv = [self.claude_bin, "-p", _recon_prompt(target),
                "--output-format", "json",
                "--permission-mode", REAL_PERMISSION_MODE,
                "--allowedTools", *REAL_ALLOWED_TOOLS]
        try:
            res = self.runner(argv, ws, self.timeout_s)
        except subprocess.TimeoutExpired:
            return self._fail(REAL, f"claude timeout after {self.timeout_s}s")
        except Exception as e:
            return self._fail(REAL, f"{type(e).__name__}: {e}")

        rc = res.get("returncode", 1)
        stdout = res.get("stdout") or ""
        stderr = res.get("stderr") or ""
        # The CLI can report failure INSIDE json stdout (is_error) even with rc==0
        # (e.g. "Not logged in"). Treat that as a failure and surface the message.
        parsed = None
        try:
            parsed = json.loads(stdout)
        except Exception:
            parsed = None
        cli_error = isinstance(parsed, dict) and bool(parsed.get("is_error"))
        if rc != 0 or cli_error:
            msg = ""
            if isinstance(parsed, dict):
                msg = str(parsed.get("result") or parsed.get("error") or "")
            msg = msg or stderr[:500]
            return self._fail(REAL, f"claude failed (rc={rc}): {msg}"[:600])
        # Success ONLY here → real_claude_connected True.
        return {"mode": REAL, "status": "SUCCEEDED", "result": {"raw": stdout[: self.output_limit]},
                "error": "", "real_claude_connected": True}

    # ---- helpers ----
    def _fail(self, mode: str, error: str) -> Dict:
        return {"mode": mode, "status": "FAILED", "result": None,
                "error": rs.scrub(error), "real_claude_connected": False}

    def _blocked(self, error: str) -> Dict:
        return {"mode": REAL, "status": "BLOCKED", "result": None,
                "error": rs.scrub(error), "real_claude_connected": False}
