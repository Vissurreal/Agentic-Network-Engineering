#!/usr/bin/env python3
"""Record a schema-valid, content-addressed local advisory verdict.

This recorder is intentionally disabled when the approved network claims an
external authority.  It cannot turn a workspace file into a trusted signature.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
from review_contract import VERDICT_SCHEMA, digest, validate_request, validate_verdict

TASK_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("round", type=int)
    parser.add_argument("reviewer")
    parser.add_argument("disposition", choices=["PASS", "FAIL", "BLOCKED"])
    parser.add_argument("body_file", nargs="?")
    args = parser.parse_args()
    if not TASK_RE.fullmatch(args.task) or args.round < 1:
        sys.stderr.write("invalid task id or round\n")
        return 64
    root = repo_root()
    runtime_path = root / ".agentic" / "runtime.json"
    try:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        sys.stderr.write(f"cannot read runtime authority: {error}\n")
        return 2
    if (runtime.get("review_authority") or {}).get("mode") != "advisory-local":
        sys.stderr.write("local verdict recording is disabled for external authority mode\n")
        return 1

    task_dir = root / ".agentic" / "reviews" / args.task
    request_path = task_dir / f"request-r{args.round}.json"
    output_path = task_dir / f"verdict-r{args.round}.json"
    if output_path.exists():
        sys.stderr.write(f"refusing to overwrite {output_path}\n")
        return 1
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        sys.stderr.write(f"cannot read request: {error}\n")
        return 2
    request_errors = validate_request(request)
    if request_errors:
        sys.stderr.write("invalid request: " + "; ".join(request_errors) + "\n")
        return 1
    if args.reviewer != request.get("reviewer_id"):
        sys.stderr.write("reviewer identity does not match request\n")
        return 1
    try:
        body_text = (
            Path(args.body_file).read_text(encoding="utf-8")
            if args.body_file
            else sys.stdin.read()
        )
        body = json.loads(body_text or "{}")
    except (OSError, json.JSONDecodeError) as error:
        sys.stderr.write(f"body must be valid JSON: {error}\n")
        return 64
    if not isinstance(body, dict) or set(body) - {"findings", "checked_clean", "stop_condition_met"}:
        sys.stderr.write("body may contain only findings, checked_clean, and stop_condition_met\n")
        return 64
    verdict = {
        "schema": VERDICT_SCHEMA,
        "task_id": args.task,
        "round": args.round,
        "request_digest": request["request_digest"],
        "reviewer_id": args.reviewer,
        "disposition": args.disposition,
        "findings": body.get("findings", []),
        "checked_clean": body.get("checked_clean", []),
        "checked_files": request["files"],
        "stop_condition_met": body.get("stop_condition_met", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "verdict_digest": "",
    }
    verdict["verdict_digest"] = digest(verdict, "verdict_digest")
    errors = validate_verdict(verdict, request)
    if errors:
        sys.stderr.write("invalid verdict: " + "; ".join(errors) + "\n")
        return 1
    task_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
