#!/usr/bin/env python3
"""Regression tests for explicit plugin invocation and delegated completion."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _harness import ROOT, SCRIPTS, Suite, py, run  # noqa: E402
sys.path.insert(0, str(SCRIPTS))
import invocation_guard as guard  # noqa: E402
import live_invocation_smoke as live_smoke  # noqa: E402


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, header, body = text.split("---\n", 2)
    values = {}
    for line in header.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values, body


def invoke_guard(payload: dict, state_dir: Path, extra_env: dict[str, str] | None = None):
    env = os.environ.copy()
    env["AGENTIC_ENGINEERING_STATE_DIR"] = str(state_dir)
    if extra_env:
        env.update(extra_env)
    result = run(
        [py(), SCRIPTS / "invocation_guard.py"],
        env=env,
        stdin=json.dumps(payload),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def main() -> int:
    suite = Suite("plugin invocation")
    exec_skill = ROOT / "skills/execute-delegated-task/SKILL.md"
    design_skill = ROOT / "skills/design-agent-network/SKILL.md"
    exec_meta, exec_body = frontmatter(exec_skill)
    design_meta, design_body = frontmatter(design_skill)

    suite.check("execution skill has stable name", exec_meta.get("name"), "execute-delegated-task")
    suite.ok(
        "execution trigger front-loads explicit plugin invocation",
        "explicitly invokes or mentions Agentic Engineering" in exec_meta.get("description", ""),
    )
    suite.ok(
        "execution trigger covers screenshot task classes",
        all(
            word in exec_meta.get("description", "")
            for word in ("research", "writing", "coding", "analysis")
        ),
    )
    suite.ok(
        "mandatory dispatch precedes final result",
        0 <= exec_body.find("## Mandatory invocation contract")
        < exec_body.find("## Execute")
        and "Before presenting a final result, dispatch at least one bounded worker"
        in exec_body,
    )
    suite.ok(
        "contract requires real dispatch not a plan",
        "A plan or a promise to\ndelegate is not a dispatch." in exec_body,
    )
    suite.ok(
        "contract requires integration and task completion",
        "Integrate the evidence and complete the actual requested artifact" in exec_body,
    )
    suite.ok(
        "contract requires independent QA",
        "dispatch an\n   independent reviewer" in exec_body,
    )
    suite.ok(
        "unavailable delegation is disclosed",
        "Delegation unavailable in this\nruntime" in exec_body,
    )
    suite.ok(
        "scope explanation is forbidden",
        "Never answer only that the plugin is irrelevant" in exec_body,
    )
    suite.ok(
        "same-file parallel writes are forbidden",
        "Never assign overlapping same-file\n   writes" in exec_body,
    )

    suite.check("design skill remains specialized", design_meta.get("name"), "design-agent-network")
    suite.ok(
        "design trigger excludes generic execution",
        "use execute-delegated-task instead" in design_meta.get("description", ""),
    )
    suite.ok(
        "wrong-route fallback executes sibling skill",
        "read\n`../execute-delegated-task/SKILL.md` completely" in design_body,
    )
    suite.ok(
        "network approval gate remains",
        "## Phase 6 - Approval gate" in design_body
        and "No project file may be\ncreated or modified before approval." in design_body,
    )

    codex_manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    claude_manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads(
        (ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    suite.check("Codex manifest exposes skills", codex_manifest.get("skills"), "./skills/")
    suite.check(
        "Codex uses the standard plugin hook location",
        "hooks" not in codex_manifest and (ROOT / "hooks/hooks.json").is_file(),
        True,
    )
    suite.ok(
        "Codex plugin purpose includes execution",
        "Executes substantive tasks" in codex_manifest.get("description", ""),
    )
    suite.ok(
        "Claude plugin purpose includes execution",
        "Executes substantive tasks" in claude_manifest.get("description", ""),
    )
    suite.ok(
        "marketplace purpose includes execution",
        "Completes research, coding, analysis, writing"
        in marketplace["plugins"][0]["description"],
    )

    contract = json.loads(
        (ROOT / "assets/contracts/invocation-v1.json").read_text(encoding="utf-8")
    )
    suite.check("invocation contract is versioned", contract.get("schema"), "agentic-engineering-invocation/v1")
    suite.check("minimum dispatch is mechanical", contract["routes"]["research"]["minimum_dispatches"], 1)
    suite.check("guard retry is bounded", contract["limits"]["stop_retries"], 1)
    suite.check("same-file writers are bounded", contract["limits"]["same_file_parallel_writers"], 1)
    suite.check(
        "contract markers equal runtime markers",
        contract["explicit_markers"],
        list(guard.EXPLICIT_MARKERS),
    )
    runtime_routes = {
        name: {
            "skill": route["skill"],
            "minimum_dispatches": 1,
            "primary_roles": route["primary_roles"],
        }
        for name, route in guard.ROUTES.items()
    }
    suite.check("contract routes equal runtime routes", contract["routes"], runtime_routes)
    suite.check(
        "contract fallback environment equals runtime",
        contract["completion"]["unavailable_fallback_operator_env"],
        guard.DIRECT_FALLBACK_ENV,
    )
    suite.check(
        "contract stop retry equals runtime",
        contract["limits"]["stop_retries"],
        guard.MAX_STOP_RETRIES,
    )

    for role in ("task-worker", "task-researcher", "task-implementer", "task-reviewer"):
        suite.ok(f"custom role exists: {role}", (ROOT / f"agents/{role}.md").is_file())
    _, researcher = frontmatter(ROOT / "agents/task-researcher.md")
    researcher_header, _ = frontmatter(ROOT / "agents/task-researcher.md")
    reviewer_header, reviewer = frontmatter(ROOT / "agents/task-reviewer.md")
    suite.ok(
        "researcher is read-only",
        all(tool not in researcher_header.get("tools", "") for tool in ("Bash", "Edit", "Write")),
    )
    suite.ok(
        "reviewer cannot edit",
        all(tool not in reviewer_header.get("tools", "") for tool in ("Edit", "Write")),
    )
    suite.ok("reviewer checks source trace", "failed source trace" in reviewer.casefold())

    cases = json.loads(
        (HERE / "fixtures/invocation_cases.json").read_text(encoding="utf-8")
    )
    for case in cases:
        result = run([py(), SCRIPTS / "invocation_guard.py", "--classify", case["prompt"]])
        suite.check(f"{case['name']}: classifier exits", result.returncode, 0)
        route = json.loads(result.stdout)
        suite.check(f"{case['name']}: explicit", route["explicit_invocation"], case["explicit"])
        suite.check(f"{case['name']}: kind", route["task_kind"], case["task_kind"])
        suite.check(f"{case['name']}: skill", route["skill"], case["skill"])
        suite.check(f"{case['name']}: roles", route["primary_roles"], case["roles"])

    hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    suite.ok(
        "guard covers routing, dispatch, and completion",
        all(
            event in hooks
            for event in ("UserPromptSubmit", "SubagentStart", "SubagentStop", "Stop")
        ),
    )
    # Neither Claude Code nor Codex reads an "args" key on a command hook: the
    # script path has to live inside the command string, or the harness runs a
    # bare `python` that reads the hook payload as source and exits 1.
    suite.ok(
        "hook commands carry the guard path in the command string",
        all(
            "args" not in event["hooks"][0]
            and event["hooks"][0]["command"]
            == 'python "${CLAUDE_PLUGIN_ROOT}/scripts/invocation_guard.py"'
            and event["hooks"][0]["commandWindows"]
            == 'python "$env:CLAUDE_PLUGIN_ROOT\\scripts\\invocation_guard.py"'
            for groups in hooks.values()
            for event in groups
        ),
    )
    live_command = live_smoke.command("codex", Path("C:/disposable"))
    suite.ok("Codex live smoke enables workspace writes", "workspace-write" in live_command)
    suite.ok(
        "Codex live smoke explicitly activates reviewed hooks",
        "--dangerously-bypass-hook-trust" in live_command,
    )
    suite.ok(
        "live smoke structurally recognizes a Claude Agent event",
        live_smoke._contains_worker_start(
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent"}]}}
        ),
    )
    suite.ok(
        "live smoke structurally recognizes a Codex spawn event",
        live_smoke._contains_worker_start(
            {"type": "item.started", "item": {"tool_name": "spawn_agent"}}
        ),
    )
    refused = run([py(), SCRIPTS / "live_invocation_smoke.py", "--host", "claude"])
    suite.check("live smoke refuses an unauthorized model call", refused.returncode, 2)

    with tempfile.TemporaryDirectory() as temporary:
        state_dir = Path(temporary)
        base = {
            "session_id": "session-a",
            "turn_id": "turn-1",
            "permission_mode": "default",
        }
        prompt = cases[0]["prompt"]
        result = invoke_guard(
            {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt},
            state_dir,
        )
        context = result["hookSpecificOutput"]["additionalContext"]
        suite.ok("screenshot prompt injects execution route", "execute-delegated-task" in context)
        suite.ok("screenshot prompt injects mandatory dispatch", "start at least one useful" in context)

        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": "The plugin is not relevant.",
            },
            state_dir,
        )
        suite.check("first silent stop is blocked", result.get("decision"), "block")

        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": True,
                "last_assistant_message": "The plugin is not relevant.",
            },
            state_dir,
        )
        suite.check("repeated silent stop terminates visibly", result.get("continue"), False)
        suite.ok("visible termination explains missing dispatch", "without a verified subagent" in result["stopReason"])

        base["turn_id"] = "turn-2"
        invoke_guard(
            {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt},
            state_dir,
        )
        start_result = invoke_guard(
            {
                **base,
                "hook_event_name": "SubagentStart",
                "agent_id": "worker-1",
                "agent_type": "agentic-engineering:task-researcher",
            },
            state_dir,
        )
        suite.ok(
            "worker receives material-contribution context",
            "material, evidence-backed result"
            in start_result["hookSpecificOutput"]["additionalContext"],
        )
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": "Research note completed.",
            },
            state_dir,
        )
        suite.check("started but unfinished worker cannot satisfy guard", result.get("decision"), "block")
        invoke_guard(
            {
                **base,
                "hook_event_name": "SubagentStop",
                "agent_id": "worker-1",
                "agent_type": "agentic-engineering:task-researcher",
                "last_assistant_message": "Evidence returned.",
            },
            state_dir,
        )
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": True,
                "last_assistant_message": "Research note completed.",
            },
            state_dir,
        )
        suite.check("completed worker lifecycle permits completion", result, {})

        base["turn_id"] = "turn-3"
        invoke_guard(
            {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt},
            state_dir,
        )
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Delegation unavailable in this runtime. I completed the bounded task directly."
                ),
            },
            state_dir,
        )
        suite.check(
            "disclosure alone cannot bypass dispatch",
            result.get("decision"),
            "block",
        )

        base["turn_id"] = "turn-3-opt-in"
        invoke_guard(
            {**base, "hook_event_name": "UserPromptSubmit", "prompt": prompt},
            state_dir,
        )
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": (
                    "Delegation unavailable in this runtime. I completed the bounded task directly."
                ),
            },
            state_dir,
            {"AGENTIC_ENGINEERING_ALLOW_DIRECT_FALLBACK": "1"},
        )
        suite.ok("operator-enabled fallback is visible", "systemMessage" in result)
        suite.ok("operator-enabled fallback is not blocked", "decision" not in result)

        base["turn_id"] = "turn-4"
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Research this without invoking the plugin.",
            },
            state_dir,
        )
        suite.check("untagged prompt is untouched", result, {})
        result = invoke_guard(
            {
                **base,
                "hook_event_name": "Stop",
                "stop_hook_active": False,
                "last_assistant_message": "Done.",
            },
            state_dir,
        )
        suite.check("untagged stop is untouched", result, {})

    return suite.report()


if __name__ == "__main__":
    raise SystemExit(main())
