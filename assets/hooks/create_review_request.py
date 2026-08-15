#!/usr/bin/env python3
"""Create a content-addressed agentic.review-request/v1 document."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
from review_contract import REQUEST_SCHEMA, digest, file_digest, validate_request

TASK_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("round", type=int)
    parser.add_argument("--producer", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--intent-file", type=Path, required=True)
    parser.add_argument("--criterion", action="append", required=True)
    parser.add_argument("--ground-truth", choices=["mechanical", "documentary", "judgment"], required=True)
    parser.add_argument("--risk-threshold", choices=["critical", "high", "medium"], required=True)
    parser.add_argument("--stop-condition", required=True)
    parser.add_argument("--max-rounds", type=int, required=True)
    parser.add_argument("--out-of-scope", action="append", default=[])
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--deleted", action="append", default=[])
    args = parser.parse_args()
    if not TASK_RE.fullmatch(args.task) or args.round < 1:
        sys.stderr.write("invalid task id or round\n")
        return 64
    project = root().resolve()
    files = []
    for raw_path in sorted(set(args.file)):
        path = (project / raw_path).resolve()
        try:
            relative = path.relative_to(project).as_posix()
        except ValueError:
            sys.stderr.write(f"file is outside the project: {raw_path}\n")
            return 64
        if not path.is_file():
            sys.stderr.write(f"file does not exist: {raw_path}\n")
            return 66
        files.append({"path": relative, "sha256": file_digest(path)})
    for raw_path in sorted(set(args.deleted)):
        path = (project / raw_path).resolve()
        try:
            relative = path.relative_to(project).as_posix()
        except ValueError:
            sys.stderr.write(f"deleted path is outside the project: {raw_path}\n")
            return 64
        if path.exists():
            sys.stderr.write(f"--deleted path still exists: {raw_path}\n")
            return 64
        files.append({"path": relative, "sha256": None})
    files.sort(key=lambda item: item["path"])
    if not files:
        sys.stderr.write("at least one --file or --deleted path is required\n")
        return 64
    request = {
        "schema": REQUEST_SCHEMA,
        "task_id": args.task,
        "round": args.round,
        "producer_id": args.producer,
        "reviewer_id": args.reviewer,
        "original_intent": args.intent_file.read_text(encoding="utf-8"),
        "acceptance_criteria": args.criterion,
        "ground_truth": args.ground_truth,
        "risk_threshold": args.risk_threshold,
        "stop_condition": args.stop_condition,
        "max_rounds": args.max_rounds,
        "out_of_scope": args.out_of_scope,
        "files": files,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request_digest": "",
    }
    request["request_digest"] = digest(request, "request_digest")
    errors = validate_request(request)
    if errors:
        sys.stderr.write("invalid request: " + "; ".join(errors) + "\n")
        return 1
    output = project / ".agentic" / "reviews" / args.task / f"request-r{args.round}.json"
    if output.exists():
        sys.stderr.write(f"refusing to overwrite {output}\n")
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
