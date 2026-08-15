#!/usr/bin/env python3
"""Route explicit plugin invocations and prevent silent non-delegated exits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

PLUGIN_NAME = "agentic-engineering"
UNAVAILABLE_DISCLOSURE = "Delegation unavailable in this runtime"
DIRECT_FALLBACK_ENV = "AGENTIC_ENGINEERING_ALLOW_DIRECT_FALLBACK"
MAX_STOP_RETRIES = 1

GENERAL_MARKERS = (
    "@agentic-engineering",
    "plugin://agentic-engineering",
)
EXECUTION_MARKERS = (
    "$execute-delegated-task",
    "$agentic-engineering:execute-delegated-task",
    "/execute-delegated-task",
    "/agentic-engineering:execute-delegated-task",
)
NETWORK_MARKERS = (
    "$design-agent-network",
    "$agentic-engineering:design-agent-network",
    "/design-agent-network",
    "/agentic-engineering:design-agent-network",
)
EXPLICIT_MARKERS = GENERAL_MARKERS + EXECUTION_MARKERS + NETWORK_MARKERS

NETWORK_PATTERNS = (
    r"\bagent(?:ic)? (?:environment|network|topology)\b",
    r"\bdesign (?:an? )?(?:agent|multi-agent|orchestration)\b",
    r"\b(?:review|resize|configure|generate) (?:the |my )?(?:agents|agent network)\b",
    r"\bgraph (?:engineering|orchestration)\b",
    r"\bharness (?:engineering|orchestration)\b",
    r"\bcross-vendor review (?:path|network|configuration)\b",
)
RESEARCH_PATTERNS = (
    r"\bresearch\b",
    r"\bsource[ds]?\b",
    r"\bliterature\b",
    r"\bevidence\b",
    r"\bprimary sources?\b",
    r"\bnotes?\b.*\b(?:vault|obsidian)\b",
)
IMPLEMENTATION_PATTERNS = (
    r"\b(?:implement|build|code|fix|refactor|patch|debug)\b",
    r"\b(?:test|lint|compile|typecheck)\b",
    r"\b(?:repository|codebase|plugin|script|function|class|api)\b",
)
ANALYSIS_PATTERNS = (
    r"\b(?:analy[sz]e|assess|compare|evaluate|audit|review)\b",
    r"\b(?:cost[- ]efficien|effectiv|trade-?off|risk)\w*\b",
)

ROUTES = {
    "network-design": {
        "skill": "design-agent-network",
        "primary_roles": ["network-architect"],
    },
    "research": {
        "skill": "execute-delegated-task",
        "primary_roles": ["task-researcher", "task-reviewer"],
    },
    "implementation": {
        "skill": "execute-delegated-task",
        "primary_roles": ["task-implementer", "task-reviewer"],
    },
    "analysis": {
        "skill": "execute-delegated-task",
        "primary_roles": ["task-researcher", "task-reviewer"],
    },
    "general": {
        "skill": "execute-delegated-task",
        "primary_roles": ["task-worker", "task-reviewer"],
    },
}


def _matches_any(prompt: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, prompt, flags=re.IGNORECASE) for pattern in patterns)


def is_explicit_invocation(prompt: str) -> bool:
    lowered = prompt.casefold()
    return any(marker in lowered for marker in EXPLICIT_MARKERS)


def _direct_skill(prompt: str) -> str | None:
    """Return the first explicitly named skill, preserving host semantics."""
    lowered = prompt.casefold()
    candidates = [
        (lowered.find(marker), "execute-delegated-task")
        for marker in EXECUTION_MARKERS
        if marker in lowered
    ]
    candidates.extend(
        (lowered.find(marker), "design-agent-network")
        for marker in NETWORK_MARKERS
        if marker in lowered
    )
    return min(candidates)[1] if candidates else None


def classify_prompt(prompt: str) -> dict[str, Any]:
    """Return a deterministic route for prompt-level guardrails and tests."""
    direct_skill = _direct_skill(prompt)
    if direct_skill == "design-agent-network":
        kind = "network-design"
    elif direct_skill == "execute-delegated-task":
        if _matches_any(prompt, RESEARCH_PATTERNS):
            kind = "research"
        elif _matches_any(prompt, IMPLEMENTATION_PATTERNS):
            kind = "implementation"
        elif _matches_any(prompt, ANALYSIS_PATTERNS):
            kind = "analysis"
        else:
            kind = "general"
    elif _matches_any(prompt, NETWORK_PATTERNS):
        kind = "network-design"
    elif _matches_any(prompt, RESEARCH_PATTERNS):
        kind = "research"
    elif _matches_any(prompt, IMPLEMENTATION_PATTERNS):
        kind = "implementation"
    elif _matches_any(prompt, ANALYSIS_PATTERNS):
        kind = "analysis"
    else:
        kind = "general"
    route = ROUTES[kind]
    return {
        "schema": "agentic-engineering-route/v1",
        "explicit_invocation": is_explicit_invocation(prompt),
        "task_kind": kind,
        "skill": route["skill"],
        "minimum_dispatches": 1,
        "primary_roles": list(route["primary_roles"]),
    }


def _event_name(payload: dict[str, Any]) -> str:
    return str(payload.get("hook_event_name") or payload.get("hookEventName") or "")


def _state_root() -> Path:
    configured = (
        os.environ.get("AGENTIC_ENGINEERING_STATE_DIR")
        or os.environ.get("PLUGIN_DATA")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
    )
    root = (
        Path(configured)
        if configured
        else Path(tempfile.gettempdir()) / "agentic-engineering-hook-state"
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def _state_key(payload: dict[str, Any]) -> str:
    session = str(payload.get("session_id") or "unknown-session")
    turn = str(payload.get("turn_id") or "current-turn")
    return hashlib.sha256(f"{session}\0{turn}".encode("utf-8")).hexdigest()


def _state_path(payload: dict[str, Any]) -> Path:
    return _state_root() / f"{_state_key(payload)}.json"


def _read_state(payload: dict[str, Any]) -> dict[str, Any] | None:
    path = _state_path(payload)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _write_state(payload: dict[str, Any], state: dict[str, Any]) -> None:
    path = _state_path(payload)
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=".invocation-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _delete_state(payload: dict[str, Any]) -> None:
    try:
        _state_path(payload).unlink(missing_ok=True)
    except OSError:
        pass


def _context_for(route: dict[str, Any]) -> str:
    roles = ", ".join(route["primary_roles"])
    if route["skill"] == "design-agent-network":
        task_instruction = (
            "Use the design-agent-network workflow and dispatch network-architect "
            "for the architectural decision."
        )
    else:
        task_instruction = (
            "Use execute-delegated-task and complete the user's actual task; "
            "do not substitute an explanation of the plugin's scope."
        )
    return (
        f"Agentic Engineering explicit invocation route: {route['task_kind']}. "
        f"{task_instruction} Before a final answer, start at least one useful "
        f"bounded subagent and integrate its returned result. Suggested roles: {roles}. "
        "If the host exposes no delegation primitive, state exactly "
        f"'{UNAVAILABLE_DISCLOSURE}'. A direct fallback is allowed only when the "
        f"operator set {DIRECT_FALLBACK_ENV}=1. "
        "Do not claim delegation without a real subagent start."
    )


def _on_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "")
    if not is_explicit_invocation(prompt):
        return {}
    route = classify_prompt(prompt)
    state = {
        "schema": "agentic-engineering-invocation-state/v1",
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "route": route,
        "dispatches": [],
        "stop_retries": 0,
    }
    _write_state(payload, state)
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _context_for(route),
        }
    }


def _on_subagent_start(payload: dict[str, Any]) -> dict[str, Any]:
    state = _read_state(payload)
    if state is None:
        return {}
    dispatches = state.setdefault("dispatches", [])
    agent_id = str(payload.get("agent_id") or "unknown-agent")
    if not any(item.get("agent_id") == agent_id for item in dispatches if isinstance(item, dict)):
        dispatches.append(
            {
                "agent_id": agent_id,
                "agent_type": str(payload.get("agent_type") or "unknown"),
                "completed": False,
            }
        )
    _write_state(payload, state)
    route = state.get("route") if isinstance(state.get("route"), dict) else {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": (
                "This worker is part of an explicit Agentic Engineering "
                f"{route.get('task_kind', 'general')} task. Produce a material, "
                "evidence-backed result for the assigned scope and return it to "
                "the coordinator; do not perform unrelated work."
            ),
        }
    }


def _on_subagent_stop(payload: dict[str, Any]) -> dict[str, Any]:
    state = _read_state(payload)
    if state is None:
        return {}
    agent_id = str(payload.get("agent_id") or "unknown-agent")
    for item in state.get("dispatches", []):
        if isinstance(item, dict) and item.get("agent_id") == agent_id:
            item["completed"] = True
    _write_state(payload, state)
    return {}


def _on_stop(payload: dict[str, Any]) -> dict[str, Any]:
    state = _read_state(payload)
    if state is None:
        return {}
    completed = [
        item
        for item in state.get("dispatches", [])
        if isinstance(item, dict) and item.get("completed") is True
    ]
    if completed:
        _delete_state(payload)
        return {}

    last_message = str(payload.get("last_assistant_message") or "")
    direct_fallback_enabled = os.environ.get(DIRECT_FALLBACK_ENV) == "1"
    if (
        direct_fallback_enabled
        and UNAVAILABLE_DISCLOSURE.casefold() in last_message.casefold()
    ):
        _delete_state(payload)
        return {
            "systemMessage": (
                "Agentic Engineering allowed a disclosed direct fallback because "
                "this runtime reported delegation unavailable; no subagent start "
                "was verified."
            )
        }

    retries = int(state.get("stop_retries", 0))
    if retries >= MAX_STOP_RETRIES:
        _delete_state(payload)
        return {
            "continue": False,
            "stopReason": (
                "Agentic Engineering blocked silent completion: the explicitly "
                "invoked task ended without a verified subagent dispatch."
            ),
        }

    state["stop_retries"] = retries + 1
    _write_state(payload, state)
    return {
        "decision": "block",
        "reason": (
            "The user explicitly invoked Agentic Engineering, but this turn has "
            "not completed a subagent lifecycle. Dispatch one useful bounded "
            "worker, wait for its result, and integrate it. A direct fallback "
            f"requires operator opt-in through {DIRECT_FALLBACK_ENV}=1 as well "
            f"as the exact disclosure '{UNAVAILABLE_DISCLOSURE}'."
        ),
    }


def handle_hook(payload: dict[str, Any]) -> dict[str, Any]:
    event = _event_name(payload)
    if event == "UserPromptSubmit":
        return _on_prompt(payload)
    if event == "SubagentStart":
        return _on_subagent_start(payload)
    if event == "SubagentStop":
        return _on_subagent_stop(payload)
    if event == "Stop":
        return _on_stop(payload)
    if event in {"StopFailure", "SessionEnd"}:
        _delete_state(payload)
    return {}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--classify",
        metavar="PROMPT",
        help="classify a prompt and print the versioned route without hook state",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.classify is not None:
        print(json.dumps(classify_prompt(args.classify), indent=2, sort_keys=True))
        return 0
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        result = handle_hook(payload)
    except Exception as exc:
        result = {
            "systemMessage": (
                "Agentic Engineering invocation guard could not verify delegation: "
                f"{type(exc).__name__}: {exc}"
            )
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
