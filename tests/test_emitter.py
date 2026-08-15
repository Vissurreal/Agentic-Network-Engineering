#!/usr/bin/env python3
"""Runtime adapters, safe merge, conflicts, drift, and rollback."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))
from _harness import ROOT, SCRIPTS, Suite, make_fixtures, py, run  # noqa: E402
import emit_network as emitter  # noqa: E402

TEMPLATE = ROOT / "assets" / "templates" / "network.yaml.template"
EMIT = SCRIPTS / "emit_network.py"


def main() -> int:
    suite = Suite("emitter")
    project = Path(tempfile.mkdtemp())
    (project / "CLAUDE.md").write_text("# User\n\nUSER-CLAUDE\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("# User rules\n\nUSER-AGENTS\n", encoding="utf-8")
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "permissions": {"allow": ["Read"]},
                "hooks": {
                    "Stop": [
                        {"hooks": [{"type": "command", "command": "user-hook"}]}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (project / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"github": {"command": "github-mcp"}}}),
        encoding="utf-8",
    )

    result = run([py(), EMIT, TEMPLATE, "--root", project, "--preflight", "--install-spec"])
    suite.check("preflight succeeds without writes", result.returncode, 0)
    suite.ok("preflight is read-only", not (project / ".agentic/network.yaml").exists())
    suite.ok("preflight contains exact diff", "--- a/CLAUDE.md" in result.stdout)

    result = run([py(), EMIT, TEMPLATE, "--root", project, "--install-spec"])
    suite.check("transactional emit succeeds", result.returncode, 0)
    suite.ok("user CLAUDE content preserved", "USER-CLAUDE" in (project / "CLAUDE.md").read_text())
    suite.ok("user AGENTS content preserved", "USER-AGENTS" in (project / "AGENTS.md").read_text())
    settings = json.loads((project / ".claude/settings.json").read_text())
    suite.ok("unrelated settings preserved", settings["permissions"]["allow"] == ["Read"])
    suite.ok(
        "unrelated Stop hook preserved",
        any("user-hook" in json.dumps(entry) for entry in settings["hooks"]["Stop"]),
    )
    mcp = json.loads((project / ".mcp.json").read_text())
    suite.ok("unrelated MCP server preserved", "github" in mcp["mcpServers"])
    suite.ok("Codex MCP server merged", mcp["mcpServers"]["codex"]["args"] == ["mcp-server"])

    suite.ok("logical GPT role is not a Claude agent", not (project / ".claude/agents/reviewer.md").exists())
    dispatcher = (project / ".claude/agents/reviewer-dispatcher.md").read_text()
    suite.ok("dispatcher uses a valid Claude model", "model: opus" in dispatcher)
    suite.ok("dispatcher gets Codex MCP tools", "mcp__codex__codex-reply" in dispatcher)
    suite.ok("dispatcher passes the GPT model", "`gpt-5.6-sol`" in dispatcher)
    suite.ok("typed guidance rendered", "Completion criteria" in (project / "CLAUDE.md").read_text())

    result = run(
        [py(), EMIT, project / ".agentic/network.yaml", "--root", project, "--check"]
    )
    suite.check("check is clean after emit", result.returncode, 0)

    with (project / ".claude/agents/orchestrator.md").open("a", encoding="utf-8") as stream:
        stream.write("\nhand edit\n")
    result = run(
        [py(), EMIT, project / ".agentic/network.yaml", "--root", project, "--check"]
    )
    suite.check("hand edit is drift", result.returncode, 1)

    collision_project = Path(tempfile.mkdtemp())
    collision = collision_project / ".claude/agents/orchestrator.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n", encoding="utf-8")
    result = run([py(), EMIT, TEMPLATE, "--root", collision_project, "--install-spec"])
    suite.check("unmanaged collision blocks", result.returncode, 1)
    suite.ok("collision remains unchanged", collision.read_text() == "user-owned\n")
    result = run(
        [
            py(),
            EMIT,
            TEMPLATE,
            "--root",
            collision_project,
            "--install-spec",
            "--approve-conflicts",
        ]
    )
    suite.check("approved exact conflict can be replaced", result.returncode, 0)

    fixtures = Path(tempfile.mkdtemp())
    make_fixtures(fixtures)
    direct_project = Path(tempfile.mkdtemp())
    result = run(
        [
            py(),
            EMIT,
            fixtures / "01-direct-valid.yaml",
            "--root",
            direct_project,
            "--install-spec",
        ]
    )
    suite.check("direct execution emits without an agent runtime", result.returncode, 0)
    suite.ok("direct execution emits no agents", not (direct_project / ".claude/agents").exists())
    suite.ok("direct execution emits no Stop hook", not (direct_project / ".claude/settings.json").exists())
    suite.ok("direct execution emits no MCP config", not (direct_project / ".mcp.json").exists())
    suite.ok("direct execution emits no Codex agent config", not (direct_project / ".codex/config.toml").exists())

    rollback = Path(tempfile.mkdtemp())
    first = rollback / "one.txt"
    second = rollback / "two.txt"
    first.write_text("before-one", encoding="utf-8")
    second.write_text("before-two", encoding="utf-8")
    real_replace = emitter.os.replace
    calls = {"count": 0}

    def fail_second(source, target):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected replacement failure")
        return real_replace(source, target)

    with mock.patch.object(emitter.os, "replace", side_effect=fail_second):
        try:
            emitter.transactional_write(
                rollback,
                {first: "after-one", second: "after-two"},
                set(),
            )
        except OSError:
            pass
    suite.ok("rollback restores first file", first.read_text() == "before-one")
    suite.ok("rollback preserves second file", second.read_text() == "before-two")
    return suite.report()


if __name__ == "__main__":
    raise SystemExit(main())
