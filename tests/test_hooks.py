#!/usr/bin/env python3
"""Content-hash invalidation and authority behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _harness import ROOT, SCRIPTS, Suite, py, run  # noqa: E402
sys.path.insert(0, str(ROOT / "assets/hooks"))
from review_contract import digest, validate_request  # noqa: E402

TEMPLATE = ROOT / "assets/templates/network.yaml.template"
ALLOW, BLOCK = 0, 2


def git(project: Path, *args: str):
    subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)


def hook(project: Path, **extra) -> int:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project), **extra}
    return run(
        [py(), project / ".claude/hooks/verify_review_coverage.py"],
        cwd=project,
        env=env,
    ).returncode


def main() -> int:
    suite = Suite("hooks")
    if subprocess.run(["git", "--version"], capture_output=True).returncode:
        print("git unavailable; skipping")
        return 0
    project = Path(tempfile.mkdtemp())
    git(project, "init", "-q")
    git(project, "config", "user.email", "test@example.com")
    git(project, "config", "user.name", "Test")
    (project / "app.py").write_text("print(1)\n", encoding="utf-8")
    (project / "delete-me.txt").write_text("remove me\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "base")
    result = run([py(), SCRIPTS / "emit_network.py", TEMPLATE, "--root", project, "--install-spec"])
    suite.check("test project emits", result.returncode, 0)
    git(project, "add", "-A")
    git(project, "commit", "-qm", "generated")
    suite.check("clean tree allows", hook(project), ALLOW)

    (project / "app.py").write_text("print(2)\n", encoding="utf-8")
    suite.check("changed file blocks", hook(project), BLOCK)

    intent = project / ".agentic/tasks/intent.txt"
    intent.write_text("Change the printed value to 2.", encoding="utf-8")
    create = project / ".claude/hooks/create_review_request.py"
    result = run(
        [
            py(),
            create,
            "T-1",
            "1",
            "--producer",
            "implementer",
            "--reviewer",
            "reviewer",
            "--intent-file",
            intent,
            "--criterion",
            "app.py prints 2",
            "--ground-truth",
            "mechanical",
            "--risk-threshold",
            "high",
            "--stop-condition",
            "one pass",
            "--max-rounds",
            "2",
            "--file",
            "app.py",
        ],
        cwd=project,
    )
    suite.check("request records current hash", result.returncode, 0)
    request_path = project / ".agentic/reviews/T-1/request-r1.json"
    request_value = json.loads(request_path.read_text(encoding="utf-8"))
    malformed = deepcopy(request_value)
    malformed["files"][0]["sha256"] = "not-a-hash"
    malformed["request_digest"] = digest(malformed, "request_digest")
    suite.ok(
        "malformed content hash is rejected",
        any("sha256" in error for error in validate_request(malformed)),
    )
    unsafe = deepcopy(request_value)
    unsafe["files"][0]["path"] = "../outside.py"
    unsafe["request_digest"] = digest(unsafe, "request_digest")
    suite.ok(
        "unsafe review path is rejected",
        any("project-relative" in error for error in validate_request(unsafe)),
    )
    body = json.dumps(
        {
            "findings": [],
            "checked_clean": ["app.py prints 2"],
            "stop_condition_met": True,
        }
    )
    result = run(
        [
            py(),
            project / ".claude/hooks/record_verdict.py",
            "T-1",
            "1",
            "reviewer",
            "PASS",
        ],
        cwd=project,
        stdin=body,
    )
    suite.check("schema-valid verdict records", result.returncode, 0)
    suite.check("current passing hash allows", hook(project), ALLOW)

    (project / "delete-me.txt").unlink()
    suite.check("unreviewed deletion blocks", hook(project), BLOCK)
    result = run(
        [
            py(),
            create,
            "T-2",
            "1",
            "--producer",
            "implementer",
            "--reviewer",
            "reviewer",
            "--intent-file",
            intent,
            "--criterion",
            "delete-me.txt is removed",
            "--ground-truth",
            "mechanical",
            "--risk-threshold",
            "high",
            "--stop-condition",
            "one pass",
            "--max-rounds",
            "2",
            "--deleted",
            "delete-me.txt",
        ],
        cwd=project,
    )
    suite.check("deletion request records null content hash", result.returncode, 0)
    result = run(
        [
            py(),
            project / ".claude/hooks/record_verdict.py",
            "T-2",
            "1",
            "reviewer",
            "PASS",
        ],
        cwd=project,
        stdin=body,
    )
    suite.check("reviewed deletion records", result.returncode, 0)
    suite.check("reviewed deletion allows", hook(project), ALLOW)

    (project / "app.py").write_text("print(3)\n", encoding="utf-8")
    suite.check("subsequent edit invalidates verdict", hook(project), BLOCK)

    verdict = project / ".agentic/reviews/T-1/verdict-r1.json"
    verdict.write_text("PASS\napp.py\n", encoding="utf-8")
    suite.check("free-form PASS cannot forge approval", hook(project), BLOCK)
    suite.check("human parent-shell override allows", hook(project, AGENTIC_SKIP_REVIEW="1"), ALLOW)

    generated = project / ".claude/agents/orchestrator.md"
    generated.write_text(generated.read_text() + "\nhand edit\n", encoding="utf-8")
    suite.check("hand-edited generated file loses exemption", hook(project), BLOCK)

    runtime = json.loads((project / ".agentic/runtime.json").read_text())
    runtime["review_authority"] = {
        "mode": "external",
        "endpoint": "http://127.0.0.1:9",
        "project_id": "test",
        "fail_closed": True,
        "human_override": "AGENTIC_SKIP_REVIEW",
    }
    (project / ".agentic/runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
    suite.check("unavailable external authority fails closed", hook(project), BLOCK)
    return suite.report()


if __name__ == "__main__":
    raise SystemExit(main())
