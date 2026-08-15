#!/usr/bin/env python3
"""Probe, validate, preflight, emit, and drift-check a real git project."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _harness import ROOT, SCRIPTS, Suite, py, run  # noqa: E402


def git(project, *args):
    subprocess.run(["git", *args], cwd=project, capture_output=True, text=True)


def main() -> int:
    suite = Suite("end to end")
    project = Path(tempfile.mkdtemp())
    git(project, "init", "-q")
    git(project, "config", "user.email", "test@example.com")
    git(project, "config", "user.name", "Test")
    (project / "main.py").write_text("print('ok')\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "base")

    result = run([py(), SCRIPTS / "probe_environment.py", project])
    suite.check("probe succeeds", result.returncode, 0)
    probe = json.loads(result.stdout)
    suite.ok("auth is explicit", "authenticated" in probe["codex"])
    suite.ok("MCP tools are explicit", isinstance(probe["codex"]["mcp_tools"], list))
    suite.ok("search breadth is not a file-count trigger", probe["search_breadth"] in {"bounded", "broad"})

    template = ROOT / "assets/templates/network.yaml.template"
    before = sorted(path.relative_to(project).as_posix() for path in project.rglob("*"))
    result = run(
        [py(), SCRIPTS / "emit_network.py", template, "--root", project, "--preflight", "--install-spec"]
    )
    suite.check("preflight succeeds", result.returncode, 0)
    after = sorted(path.relative_to(project).as_posix() for path in project.rglob("*"))
    suite.ok("preflight leaves project structurally unchanged", before == after)

    result = run(
        [py(), SCRIPTS / "emit_network.py", template, "--root", project, "--install-spec"]
    )
    suite.check("emit succeeds", result.returncode, 0)
    result = run(
        [
            py(),
            SCRIPTS / "validate_network.py",
            project / ".agentic/network.yaml",
        ]
    )
    suite.check("installed source validates", result.returncode, 0)
    result = run(
        [
            py(),
            SCRIPTS / "emit_network.py",
            project / ".agentic/network.yaml",
            "--root",
            project,
            "--check",
        ]
    )
    suite.check("installed artifacts are drift-free", result.returncode, 0)
    suite.ok(
        "manifest binds approved source",
        bool(json.loads((project / ".agentic/manifest.json").read_text())["approved_spec_sha256"]),
    )
    return suite.report()


if __name__ == "__main__":
    raise SystemExit(main())
