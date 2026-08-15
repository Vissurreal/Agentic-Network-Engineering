#!/usr/bin/env python3
"""Stop hook for content-addressed review coverage.

Local mode is an advisory backstop.  External mode delegates verification to a
separate authority and fails closed when it cannot obtain a binding answer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
from review_contract import file_digest, validate_request, validate_verdict

ALLOW, BLOCK = 0, 2


def git(args: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0, result.stdout
    except (OSError, subprocess.SubprocessError):
        return False, ""


def reject(message: str) -> int:
    sys.stderr.write(f"agentic: {message}\n")
    return BLOCK


def changed_files(root: Path) -> list[str] | None:
    changed: set[str] = set()
    for args in (
        ["diff", "--name-only", "HEAD"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        ok, output = git(args, root)
        if not ok:
            return None
        changed.update(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())
    return sorted(changed)


def generated_and_clean(path: str, root: Path, manifest: dict) -> bool:
    if path in {".agentic/manifest.json"} or path.startswith((".agentic/reviews/", ".agentic/tasks/")):
        return True
    expected = (manifest.get("files") or {}).get(path)
    target = root / path
    return bool(expected and target.is_file() and file_digest(target) == expected)


def external_verify(root: Path, files: list[dict], authority: dict) -> bool:
    endpoint = str(authority.get("endpoint") or "").rstrip("/") + "/verify"
    payload = json.dumps(
        {
            "project_id": authority.get("project_id"),
            "files": files,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False
    return result.get("approved") is True and result.get("files") == files


def local_coverage(root: Path, changed: list[str]) -> set[str]:
    reviews = root / ".agentic" / "reviews"
    if not reviews.is_dir():
        return set()
    covered: set[str] = set()
    for task_dir in sorted(path for path in reviews.iterdir() if path.is_dir()):
        for verdict_path in sorted(task_dir.glob("verdict-r*.json")):
            suffix = verdict_path.stem.replace("verdict-r", "")
            request_path = task_dir / f"request-r{suffix}.json"
            try:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if validate_request(request) or validate_verdict(verdict, request):
                continue
            if verdict.get("disposition") != "PASS" or verdict.get("stop_condition_met") is not True:
                continue
            for item in request.get("files") or []:
                path = item.get("path")
                target = root / str(path)
                if (
                    path in changed
                    and (
                        (target.is_file() and file_digest(target) == item.get("sha256"))
                        or (not target.exists() and item.get("sha256") is None)
                    )
                ):
                    covered.add(path)
    return covered


def main() -> int:
    if os.environ.get("AGENTIC_SKIP_REVIEW") == "1":
        return ALLOW
    if not shutil.which("git"):
        return reject("git is unavailable; review coverage cannot be established")
    cwd = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    ok, top = git(["rev-parse", "--show-toplevel"], cwd)
    if not ok or not top.strip():
        return reject("the project is not a git repository; review coverage cannot be established")
    root = Path(top.strip())
    try:
        runtime = json.loads((root / ".agentic" / "runtime.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / ".agentic" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return reject(f"generated authority metadata is absent or invalid: {error}")
    changed = changed_files(root)
    if changed is None:
        return reject("git could not enumerate the changed files")
    changed = [path for path in changed if not generated_and_clean(path, root, manifest)]
    if not changed:
        return ALLOW
    hashed = [
        {
            "path": path,
            "sha256": file_digest(root / path) if (root / path).is_file() else None,
        }
        for path in changed
    ]
    authority = runtime.get("review_authority") or {}
    if authority.get("mode") == "external":
        if external_verify(root, hashed, authority):
            return ALLOW
        return reject("external review authority did not approve the current file hashes")
    covered = local_coverage(root, changed)
    uncovered = sorted(set(changed) - covered)
    if uncovered:
        return reject(
            "the advisory local ledger has no current passing verdict for: "
            + ", ".join(uncovered)
        )
    return ALLOW


if __name__ == "__main__":
    raise SystemExit(main())
