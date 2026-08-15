#!/usr/bin/env python3
"""Opt-in live check that requires a worker dispatch and a written artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TASK = (
    "Research whether directed-energy lasers can cost-effectively replace "
    "missile interceptors. Use current primary sources, distinguish facts "
    "from inference, dispatch at least one worker, and save a concise sourced "
    "assessment to smoke-result.md."
)
AGENT_TOOL_NAMES = {
    "agent",
    "spawn_agent",
    "collaboration.spawn_agent",
    "collaboration_spawn_agent",
}
AGENT_EVENT_TYPES = {
    "subagentstart",
    "subagent_start",
    "subagent.started",
    "subagent_started",
    "agent_spawn",
    "agent_spawned",
    "multi_agent.spawn",
}


def _contains_worker_start(value: Any) -> bool:
    if isinstance(value, list):
        return any(_contains_worker_start(item) for item in value)
    if not isinstance(value, dict):
        return False
    for key in ("name", "tool", "tool_name", "toolName"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.casefold() in AGENT_TOOL_NAMES:
            return True
    for key in ("type", "event", "event_type", "hook_event_name"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.casefold() in AGENT_EVENT_TYPES:
            return True
    return any(_contains_worker_start(item) for item in value.values())


def _parse_jsonl(transcript: str) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    invalid = 0
    for line in transcript.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, invalid


def command(host: str, workspace: Path) -> list[str]:
    if host == "claude":
        return [
            "claude",
            "-p",
            "--plugin-dir",
            str(ROOT),
            "--verbose",
            "--output-format",
            "stream-json",
            "--permission-mode",
            "bypassPermissions",
            f"/agentic-engineering:execute-delegated-task {TASK}",
        ]
    return [
        "codex",
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--dangerously-bypass-hook-trust",
        "-C",
        str(workspace),
        f"$agentic-engineering:execute-delegated-task {TASK}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=("claude", "codex"), required=True)
    parser.add_argument(
        "--allow-model-call",
        action="store_true",
        help="Acknowledge that this test consumes an authenticated model call.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Persistent disposable workspace for the artifact and JSONL evidence.",
    )
    args = parser.parse_args()

    if not args.allow_model_call:
        print("REFUSED: pass --allow-model-call to authorize a live model call.")
        return 2

    workspace = (
        args.workspace.resolve()
        if args.workspace
        else Path(tempfile.mkdtemp(prefix="agentic-engineering-live-"))
    )
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command(args.host, workspace),
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout_seconds,
            check=False,
        )
    except FileNotFoundError:
        print(f"FAIL: {args.host} CLI is not installed or not on PATH.")
        return 1
    except subprocess.TimeoutExpired:
        print(f"FAIL: {args.host} did not finish within the timeout.")
        return 1

    transcript = result.stdout + "\n" + result.stderr
    log_path = workspace / "host-events.jsonl"
    log_path.write_text(transcript, encoding="utf-8")
    events, invalid_lines = _parse_jsonl(transcript)
    artifact = workspace / "smoke-result.md"
    dispatched = any(_contains_worker_start(event) for event in events)
    artifact_ok = artifact.is_file() and bool(artifact.read_text(encoding="utf-8").strip())

    summary = {
        "host": args.host,
        "host_exit_code": result.returncode,
        "parsed_json_events": len(events),
        "non_json_lines": invalid_lines,
        "worker_dispatch_observed": dispatched,
        "artifact_created": artifact_ok,
        "evidence_workspace": str(workspace),
    }
    print(json.dumps(summary, indent=2))
    if result.returncode or not dispatched or not artifact_ok:
        print("FAIL: live invocation did not satisfy the dispatch-and-output contract.")
        return 1
    print("PASS: live invocation dispatched a worker and produced the artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
