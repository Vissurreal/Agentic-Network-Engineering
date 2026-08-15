#!/usr/bin/env python3
"""Strict validation for the version 2 logical agent-network specification.

The validator is intentionally dependency-free.  It implements the safety
invariants directly rather than silently accepting fields that a runtime cannot
honour.  Unknown fields are rejected throughout the safety-relevant schema.

Usage:
    python validate_network.py network.yaml [--probe probe.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _yamlcompat as yamlc  # noqa: E402


IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]{0,47}$")
PROSE_WORD_CAP = 100

MUTATING_TOOLS = {"Write", "Edit", "NotebookEdit", "MultiEdit", "Bash"}
DELEGATION_TOOLS = {"Agent", "Task"}
CODEX_MCP_TOOLS = {"codex", "codex-reply"}
NATIVE_MODEL_ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit"}

ENUMS = {
    "path_predictability": {"known", "partially-known", "emergent"},
    "coupling": {"independent", "staged", "interdependent"},
    "information_volume": {"bounded", "large", "runtime-determined"},
    "search_breadth": {"bounded", "broad", "runtime-determined"},
    "ground_truth": {"mechanical", "documentary", "judgment"},
    "reversibility": {"reversible", "costly", "irreversible"},
    "consequence": {"low", "material", "high"},
    "context_isolation": {"shared", "clean-room", "cross-vendor"},
    "pattern": {
        "direct",
        "pipeline",
        "fan-out",
        "supervised-portfolio",
        "adaptive-harness",
        "custom",
    },
    "topology_mode": {"direct", "graph", "harness"},
    "rank": {"lead", "specialist", "worker", "reviewer", "arbiter", "scout"},
    "provider": {"anthropic", "openai"},
    "via": {"native", "codex-mcp"},
    "effort": {"low", "medium", "high", "xhigh", "max"},
    "memory": {"none", "project", "user", "local"},
    "isolation": {"shared", "worktree", "read-only", "cross-vendor"},
    "unit": {"task", "milestone"},
    "threshold": {"critical", "high", "medium"},
    "gate_authority": {"advisory", "enforced"},
    "deadlock": {"human", "none"},
    "authority_mode": {"advisory-local", "external"},
    "backoff": {"none", "linear", "exponential"},
    "cancellation": {"cooperative", "immediate"},
    "checkpoint": {"none", "per-task", "per-iteration"},
    "recovery": {"restart", "resume-latest"},
    "sandbox": {"read-only", "workspace-write", "danger-full-access"},
    "approval_policy": {"untrusted", "on-request", "never"},
}


class Report:
    def __init__(self) -> None:
        self.violations: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def fail(self, code: str, detail: str) -> None:
        self.violations.append((code, detail))

    def warn(self, detail: str) -> None:
        self.warnings.append(detail)

    @property
    def ok(self) -> bool:
        return not self.violations

    def render(self) -> str:
        if self.violations:
            lines = [f"BLOCKED - {len(self.violations)} violation(s)"]
            for code, detail in sorted(self.violations):
                lines.append(f"  [{code}] {detail}")
        else:
            lines = ["PASS - network specification is valid"]
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {warning}" for warning in self.warnings)
        return "\n".join(lines)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _mapping(value: Any, path: str, report: Report) -> dict[str, Any]:
    if not isinstance(value, dict):
        report.fail("schema.type", f"{path} must be a mapping.")
        return {}
    return value


def _sequence(value: Any, path: str, report: Report) -> list[Any]:
    if not isinstance(value, list):
        report.fail("schema.type", f"{path} must be a list.")
        return []
    return value


def _unknown(obj: dict[str, Any], allowed: Iterable[str], path: str, report: Report) -> None:
    extra = sorted(set(obj) - set(allowed))
    if extra:
        report.fail("schema.unknown", f"{path} contains unknown field(s): {', '.join(extra)}.")


def _required(obj: dict[str, Any], fields: Iterable[str], path: str, report: Report) -> None:
    missing = [field for field in fields if field not in obj]
    if missing:
        report.fail("schema.required", f"{path} is missing: {', '.join(missing)}.")


def _string(
    obj: dict[str, Any],
    field: str,
    path: str,
    report: Report,
    *,
    allow_empty: bool = False,
) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        report.fail("schema.type", f"{path}.{field} must be a non-empty string.")
        return ""
    return value


def _boolean(obj: dict[str, Any], field: str, path: str, report: Report) -> bool:
    value = obj.get(field)
    if not isinstance(value, bool):
        report.fail("schema.type", f"{path}.{field} must be a boolean.")
        return False
    return value


def _integer(
    obj: dict[str, Any],
    field: str,
    path: str,
    report: Report,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    value = obj.get(field)
    if not _is_int(value):
        report.fail("schema.type", f"{path}.{field} must be an integer.")
        return minimum
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and <= {maximum}" if maximum is not None else ""
        report.fail("schema.range", f"{path}.{field} must be >= {minimum}{upper}.")
    return value


def _enum(
    obj: dict[str, Any],
    field: str,
    values: set[str],
    path: str,
    report: Report,
) -> str:
    value = obj.get(field)
    if value not in values:
        report.fail(
            "schema.enum",
            f"{path}.{field} must be one of {sorted(values)}; got {value!r}.",
        )
        return ""
    return str(value)


def _string_list(
    obj: dict[str, Any],
    field: str,
    path: str,
    report: Report,
    *,
    allow_empty: bool = True,
) -> list[str]:
    value = obj.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        report.fail("schema.type", f"{path}.{field} must be a list of non-empty strings.")
        return []
    if not allow_empty and not value:
        report.fail("schema.range", f"{path}.{field} must not be empty.")
    if len(value) != len(set(value)):
        report.fail("schema.unique", f"{path}.{field} contains duplicate values.")
    return value


def _identifier(value: Any, path: str, report: Report) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        report.fail(
            "schema.identifier",
            f"{path} must match {IDENTIFIER.pattern}; got {value!r}.",
        )
        return ""
    return value


def _validate_project(net: dict[str, Any], report: Report) -> None:
    project = _mapping(net.get("project"), "project", report)
    _unknown(project, {"name", "domain", "guidance"}, "project", report)
    _required(project, {"name", "domain", "guidance"}, "project", report)
    _string(project, "name", "project", report)
    _string(project, "domain", "project", report)

    guidance = _mapping(project.get("guidance"), "project.guidance", report)
    _unknown(
        guidance,
        {"description", "completion_criteria", "conventions", "commands"},
        "project.guidance",
        report,
    )
    _required(
        guidance,
        {"description", "completion_criteria", "conventions", "commands"},
        "project.guidance",
        report,
    )
    _string(guidance, "description", "project.guidance", report)
    _string_list(guidance, "completion_criteria", "project.guidance", report, allow_empty=False)
    _string_list(guidance, "conventions", "project.guidance", report)
    commands = _sequence(guidance.get("commands"), "project.guidance.commands", report)
    purposes: set[str] = set()
    for index, raw in enumerate(commands):
        path = f"project.guidance.commands[{index}]"
        command = _mapping(raw, path, report)
        _unknown(command, {"purpose", "command"}, path, report)
        _required(command, {"purpose", "command"}, path, report)
        purpose = _string(command, "purpose", path, report)
        _string(command, "command", path, report)
        if purpose in purposes:
            report.fail("schema.unique", f"Duplicate command purpose {purpose!r}.")
        purposes.add(purpose)


def _validate_decision(net: dict[str, Any], report: Report) -> None:
    decision = _mapping(net.get("decision"), "decision", report)
    allowed = {
        "path_predictability",
        "workstreams",
        "coupling",
        "information_volume",
        "search_breadth",
        "external_retrieval",
        "ground_truth",
        "reversibility",
        "consequence",
        "delegation_depth",
        "human_gates",
        "context_isolation",
    }
    _unknown(decision, allowed, "decision", report)
    _required(decision, allowed, "decision", report)
    for field in (
        "path_predictability",
        "coupling",
        "information_volume",
        "search_breadth",
        "ground_truth",
        "reversibility",
        "consequence",
        "context_isolation",
    ):
        _enum(decision, field, ENUMS[field], "decision", report)
    workstreams = decision.get("workstreams")
    if workstreams != "runtime-determined" and (not _is_int(workstreams) or workstreams < 1):
        report.fail(
            "schema.type",
            "decision.workstreams must be a positive integer or 'runtime-determined'.",
        )
    _boolean(decision, "external_retrieval", "decision", report)
    _integer(decision, "delegation_depth", "decision", report, minimum=0, maximum=8)
    _string_list(decision, "human_gates", "decision", report)


def _validate_selection(net: dict[str, Any], report: Report) -> None:
    selection = _mapping(net.get("selection"), "selection", report)
    allowed = {"pattern", "rationale", "deviation_rationale", "alternatives_rejected", "assumptions"}
    _unknown(selection, allowed, "selection", report)
    _required(selection, {"pattern", "rationale", "alternatives_rejected", "assumptions"}, "selection", report)
    pattern = _enum(selection, "pattern", ENUMS["pattern"], "selection", report)
    _string(selection, "rationale", "selection", report)
    deviation = selection.get("deviation_rationale")
    if deviation is not None and not isinstance(deviation, str):
        report.fail("schema.type", "selection.deviation_rationale must be a string or null.")
    if pattern == "custom" and (not isinstance(deviation, str) or not deviation.strip()):
        report.fail(
            "selection.custom-rationale",
            "Custom topology selections require a non-empty deviation_rationale.",
        )
    alternatives = _sequence(selection.get("alternatives_rejected"), "selection.alternatives_rejected", report)
    for index, raw in enumerate(alternatives):
        path = f"selection.alternatives_rejected[{index}]"
        item = _mapping(raw, path, report)
        _unknown(item, {"pattern", "reason"}, path, report)
        _required(item, {"pattern", "reason"}, path, report)
        _enum(item, "pattern", ENUMS["pattern"], path, report)
        _string(item, "reason", path, report)
    _string_list(selection, "assumptions", "selection", report)


def _validate_environment(net: dict[str, Any], report: Report) -> None:
    env = _mapping(net.get("environment"), "environment", report)
    allowed = {"git", "python_command", "test_command", "languages", "claude", "codex"}
    _unknown(env, allowed, "environment", report)
    _required(env, allowed, "environment", report)
    _boolean(env, "git", "environment", report)
    _string(env, "python_command", "environment", report)
    test = env.get("test_command")
    if test is not None and not isinstance(test, str):
        report.fail("schema.type", "environment.test_command must be a string or null.")
    _string_list(env, "languages", "environment", report)

    claude = _mapping(env.get("claude"), "environment.claude", report)
    claude_fields = {"installed", "authenticated", "version", "models"}
    _unknown(claude, claude_fields, "environment.claude", report)
    _required(claude, claude_fields, "environment.claude", report)
    _boolean(claude, "installed", "environment.claude", report)
    _boolean(claude, "authenticated", "environment.claude", report)
    version = claude.get("version")
    if version is not None and not isinstance(version, str):
        report.fail("schema.type", "environment.claude.version must be a string or null.")
    _string_list(claude, "models", "environment.claude", report)

    codex = _mapping(env.get("codex"), "environment.codex", report)
    codex_fields = {
        "installed",
        "authenticated",
        "version",
        "mcp_available",
        "mcp_tools",
        "model_access",
        "models",
    }
    _unknown(codex, codex_fields, "environment.codex", report)
    _required(codex, codex_fields, "environment.codex", report)
    for field in ("installed", "authenticated", "mcp_available"):
        _boolean(codex, field, "environment.codex", report)
    version = codex.get("version")
    if version is not None and not isinstance(version, str):
        report.fail("schema.type", "environment.codex.version must be a string or null.")
    _enum(codex, "model_access", {"verified", "unverified", "unavailable"}, "environment.codex", report)
    tools = _string_list(codex, "mcp_tools", "environment.codex", report)
    _string_list(codex, "models", "environment.codex", report)
    if codex.get("mcp_available") and not CODEX_MCP_TOOLS.issubset(set(tools)):
        report.fail(
            "environment.codex-mcp",
            "Codex MCP readiness requires both 'codex' and 'codex-reply' tools.",
        )


def _validate_runtime(net: dict[str, Any], report: Report) -> None:
    runtime = _mapping(net.get("runtime"), "runtime", report)
    allowed = {
        "max_concurrency",
        "max_depth",
        "retry",
        "cancellation",
        "checkpoint",
        "recovery",
        "claude",
        "codex",
    }
    _unknown(runtime, allowed, "runtime", report)
    _required(runtime, allowed, "runtime", report)
    _integer(runtime, "max_concurrency", "runtime", report, minimum=1, maximum=64)
    _integer(runtime, "max_depth", "runtime", report, minimum=0, maximum=8)
    _enum(runtime, "cancellation", ENUMS["cancellation"], "runtime", report)
    _enum(runtime, "checkpoint", ENUMS["checkpoint"], "runtime", report)
    _enum(runtime, "recovery", ENUMS["recovery"], "runtime", report)

    retry = _mapping(runtime.get("retry"), "runtime.retry", report)
    _unknown(retry, {"max_attempts", "backoff"}, "runtime.retry", report)
    _required(retry, {"max_attempts", "backoff"}, "runtime.retry", report)
    _integer(retry, "max_attempts", "runtime.retry", report, minimum=0, maximum=5)
    _enum(retry, "backoff", ENUMS["backoff"], "runtime.retry", report)

    claude = _mapping(runtime.get("claude"), "runtime.claude", report)
    _unknown(claude, {"dispatcher_model", "dispatcher_effort"}, "runtime.claude", report)
    _required(claude, {"dispatcher_model", "dispatcher_effort"}, "runtime.claude", report)
    model = _string(claude, "dispatcher_model", "runtime.claude", report)
    if model and model not in NATIVE_MODEL_ALIASES and not model.startswith("claude-"):
        report.fail("runtime.model", f"Unknown Claude dispatcher model {model!r}.")
    _enum(claude, "dispatcher_effort", ENUMS["effort"], "runtime.claude", report)

    codex = _mapping(runtime.get("codex"), "runtime.codex", report)
    _unknown(codex, {"sandbox", "approval_policy"}, "runtime.codex", report)
    _required(codex, {"sandbox", "approval_policy"}, "runtime.codex", report)
    _enum(codex, "sandbox", ENUMS["sandbox"], "runtime.codex", report)
    _enum(codex, "approval_policy", ENUMS["approval_policy"], "runtime.codex", report)


def _validate_agents(
    net: dict[str, Any],
    probe: dict[str, Any] | None,
    report: Report,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    raw_agents = _sequence(net.get("agents"), "agents", report)
    agents: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    allowed = {
        "id",
        "role",
        "rank",
        "provider",
        "model",
        "via",
        "effort",
        "count",
        "default_active",
        "max_turns",
        "context_budget_tokens",
        "memory",
        "isolation",
        "tools",
        "invocable_by",
        "reports_to",
        "produces_changes",
        "accepts",
        "produces",
        "prevents",
        "prose",
    }
    for index, raw in enumerate(raw_agents):
        path = f"agents[{index}]"
        agent = _mapping(raw, path, report)
        agents.append(agent)
        _unknown(agent, allowed, path, report)
        _required(agent, allowed, path, report)
        agent_id = _identifier(agent.get("id"), f"{path}.id", report)
        if agent_id in by_id:
            report.fail("schema.unique", f"Duplicate agent id {agent_id!r}.")
        elif agent_id:
            by_id[agent_id] = agent
        for field in ("role", "model", "accepts", "produces", "prevents"):
            _string(agent, field, path, report)
        rank = _enum(agent, "rank", ENUMS["rank"], path, report)
        provider = _enum(agent, "provider", ENUMS["provider"], path, report)
        via = _enum(agent, "via", ENUMS["via"], path, report)
        _enum(agent, "effort", ENUMS["effort"], path, report)
        _integer(agent, "count", path, report, minimum=1, maximum=32)
        _boolean(agent, "default_active", path, report)
        _integer(agent, "max_turns", path, report, minimum=1, maximum=200)
        _integer(agent, "context_budget_tokens", path, report, minimum=1_000, maximum=2_000_000)
        _enum(agent, "memory", ENUMS["memory"], path, report)
        isolation = _enum(agent, "isolation", ENUMS["isolation"], path, report)
        tools = _string_list(agent, "tools", path, report)
        callers = _string_list(agent, "invocable_by", path, report, allow_empty=False)
        reports_to = agent.get("reports_to")
        if reports_to != "human":
            _identifier(reports_to, f"{path}.reports_to", report)
        _boolean(agent, "produces_changes", path, report)
        prose = agent.get("prose")
        if not isinstance(prose, str):
            report.fail("schema.type", f"{path}.prose must be a string.")
        elif len(prose.split()) > PROSE_WORD_CAP:
            report.fail(
                "agent.prose-cap",
                f"Agent {agent_id!r} prose is {len(prose.split())} words; cap is {PROSE_WORD_CAP}.",
            )
        if not str(agent.get("prevents", "")).strip() or str(agent.get("prevents", "")).strip().lower() in {
            "none",
            "nothing",
            "n/a",
        }:
            report.fail("agent.failure-mode", f"Agent {agent_id!r} must name a substantive failure mode.")

        model = str(agent.get("model") or "")
        if via == "native":
            if provider != "anthropic":
                report.fail("agent.adapter", f"Native agent {agent_id!r} must use provider 'anthropic'.")
            if model not in NATIVE_MODEL_ALIASES and not model.startswith("claude-"):
                report.fail("agent.model", f"Native agent {agent_id!r} uses unknown model {model!r}.")
        elif via == "codex-mcp":
            if provider != "openai":
                report.fail("agent.adapter", f"Codex MCP agent {agent_id!r} must use provider 'openai'.")
            if not model.startswith("gpt-"):
                report.fail("agent.model", f"Codex MCP agent {agent_id!r} must use a GPT model.")
            if tools:
                report.fail(
                    "agent.logical-role-tools",
                    f"Remote logical agent {agent_id!r} must declare no Claude tools; the dispatcher owns transport tools.",
                )
            if isolation != "cross-vendor":
                report.fail(
                    "agent.isolation",
                    f"Remote logical agent {agent_id!r} must use cross-vendor isolation.",
                )

        if rank == "scout":
            bad = set(tools) & (MUTATING_TOOLS | DELEGATION_TOOLS)
            if bad:
                report.fail(
                    "agent.scout-read-only",
                    f"Scout {agent_id!r} holds mutating or delegation tools: {sorted(bad)}.",
                )
            if isolation != "read-only":
                report.fail("agent.scout-read-only", f"Scout {agent_id!r} must use read-only isolation.")
            if agent.get("produces_changes") is not False:
                report.fail("agent.scout-read-only", f"Scout {agent_id!r} cannot produce project changes.")
            if model != "haiku" or via != "native":
                report.fail("agent.scout-model", f"Scout {agent_id!r} must be a native Haiku role.")

        if probe:
            if via == "native":
                available = probe.get("claude_models") or []
                if available and model not in available and not model.startswith("claude-"):
                    report.fail("agent.model-availability", f"Probe did not report Claude model {model!r}.")
            elif via == "codex-mcp":
                access = probe.get("codex_model_access")
                models = probe.get("codex_models") or []
                if access != "verified" or model not in models:
                    report.fail(
                        "agent.model-availability",
                        f"Probe did not verify access to Codex model {model!r}.",
                    )

    for agent in agents:
        agent_id = agent.get("id")
        for caller in agent.get("invocable_by") or []:
            if caller != "human" and caller not in by_id:
                report.fail("agent.dangling-caller", f"Agent {agent_id!r} has unknown caller {caller!r}.")
        reports_to = agent.get("reports_to")
        if reports_to != "human" and reports_to not in by_id:
            report.fail("agent.dangling-report", f"Agent {agent_id!r} reports to unknown {reports_to!r}.")
        if reports_to not in (agent.get("invocable_by") or []):
            report.fail(
                "agent.reporting",
                f"Agent {agent_id!r} reports_to must be one of its declared invocable_by entries.",
            )

    decision = net.get("decision") or {}
    scouting_needed = (
        decision.get("search_breadth") in {"broad", "runtime-determined"}
        or decision.get("external_retrieval") is True
        or decision.get("information_volume") in {"large", "runtime-determined"}
    )
    scouts = [agent for agent in agents if agent.get("rank") == "scout"]
    if scouting_needed and len(scouts) != 1:
        report.fail("agent.scout-count", f"Retrieval conditions require exactly one scout; found {len(scouts)}.")
    elif not scouting_needed and len(scouts) > 1:
        report.fail("agent.scout-count", f"At most one scout is permitted; found {len(scouts)}.")

    return agents, by_id


def _validate_topology(
    net: dict[str, Any],
    agents: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    topology = _mapping(net.get("topology"), "topology", report)
    allowed = {
        "mode",
        "invocation_policy",
        "entry_agent",
        "graph",
        "harness",
        "a2a",
    }
    _unknown(topology, allowed, "topology", report)
    _required(topology, {"mode", "invocation_policy", "entry_agent"}, "topology", report)
    mode = _enum(topology, "mode", ENUMS["topology_mode"], "topology", report)
    _enum(topology, "invocation_policy", {"descriptive", "runtime-enforced"}, "topology", report)
    if topology.get("invocation_policy") == "runtime-enforced":
        report.fail(
            "topology.invocation-policy",
            "Claude project subagents cannot enforce caller identity; use 'descriptive'.",
        )

    entry = topology.get("entry_agent")
    if mode == "direct":
        if entry is not None:
            report.fail("topology.direct", "Direct mode requires entry_agent: null.")
        if agents:
            report.fail("topology.direct", "Direct mode must not define agents.")
        for forbidden in ("graph", "harness", "a2a"):
            if forbidden in topology:
                report.fail("topology.direct", f"Direct mode must not define topology.{forbidden}.")
        return

    _identifier(entry, "topology.entry_agent", report)
    if entry not in by_id:
        report.fail("topology.entry", f"Entry agent {entry!r} is not defined.")
    elif "human" not in (by_id[entry].get("invocable_by") or []):
        report.fail("topology.entry", f"Entry agent {entry!r} must be invocable by human.")

    if mode == "graph":
        if "harness" in topology:
            report.fail("topology.mode", "Graph mode must not define topology.harness.")
        graph = _mapping(topology.get("graph"), "topology.graph", report)
        _unknown(graph, {"edges"}, "topology.graph", report)
        _required(graph, {"edges"}, "topology.graph", report)
        edges = _sequence(graph.get("edges"), "topology.graph.edges", report)
        incoming: dict[str, set[str]] = {agent_id: set() for agent_id in by_id}
        reachable = {"human"}
        parsed_edges: list[tuple[str, str]] = []
        for index, raw in enumerate(edges):
            path = f"topology.graph.edges[{index}]"
            edge = _mapping(raw, path, report)
            _unknown(edge, {"from", "to", "message", "condition"}, path, report)
            _required(edge, {"from", "to", "message", "condition"}, path, report)
            source = edge.get("from")
            target = edge.get("to")
            if source != "human":
                _identifier(source, f"{path}.from", report)
            _identifier(target, f"{path}.to", report)
            _string(edge, "message", path, report)
            _string(edge, "condition", path, report)
            if source != "human" and source not in by_id:
                report.fail("topology.edge", f"{path}.from references unknown agent {source!r}.")
            if target not in by_id:
                report.fail("topology.edge", f"{path}.to references unknown agent {target!r}.")
            if target in incoming and isinstance(source, str):
                incoming[target].add(source)
            if isinstance(source, str) and isinstance(target, str):
                parsed_edges.append((source, target))

        changed = True
        while changed:
            changed = False
            for source, target in parsed_edges:
                if source in reachable and target not in reachable:
                    reachable.add(target)
                    changed = True
        for agent_id in sorted(set(by_id) - reachable):
            report.fail("topology.orphan", f"Agent {agent_id!r} is unreachable from human.")
        for agent in agents:
            agent_id = agent.get("id")
            declared = set(agent.get("invocable_by") or [])
            if incoming.get(agent_id, set()) != declared:
                report.fail(
                    "topology.caller-drift",
                    f"Agent {agent_id!r} callers {sorted(declared)} do not match graph incoming "
                    f"edges {sorted(incoming.get(agent_id, set()))}.",
                )
        for source, target in parsed_edges:
            if source == "human" or source not in by_id:
                continue
            if "Agent" not in (by_id[source].get("tools") or []) and "Task" not in (
                by_id[source].get("tools") or []
            ):
                report.fail(
                    "topology.unexecutable-edge",
                    f"Edge {source!r} -> {target!r} requires Agent or Task on {source!r}.",
                )

    elif mode == "harness":
        if "graph" in topology:
            report.fail("topology.mode", "Harness mode must not define topology.graph.")
        harness = _mapping(topology.get("harness"), "topology.harness", report)
        _unknown(
            harness,
            {"planner", "states", "termination", "max_iterations", "fan_out"},
            "topology.harness",
            report,
        )
        _required(
            harness,
            {"planner", "states", "termination", "max_iterations", "fan_out"},
            "topology.harness",
            report,
        )
        planner = _identifier(harness.get("planner"), "topology.harness.planner", report)
        states = _string_list(harness, "states", "topology.harness", report, allow_empty=False)
        if len(states) < 2:
            report.fail("topology.harness", "Harness requires at least two explicit states.")
        _string(harness, "termination", "topology.harness", report)
        _integer(harness, "max_iterations", "topology.harness", report, minimum=1, maximum=100)
        fan_out = _mapping(harness.get("fan_out"), "topology.harness.fan_out", report)
        _unknown(fan_out, {"mode", "max_parallel", "partition_by"}, "topology.harness.fan_out", report)
        _required(fan_out, {"mode", "max_parallel", "partition_by"}, "topology.harness.fan_out", report)
        _enum(fan_out, "mode", {"none", "fixed", "runtime"}, "topology.harness.fan_out", report)
        _integer(fan_out, "max_parallel", "topology.harness.fan_out", report, minimum=1, maximum=64)
        partition = fan_out.get("partition_by")
        if partition is not None and not isinstance(partition, str):
            report.fail("schema.type", "topology.harness.fan_out.partition_by must be a string or null.")
        if planner not in by_id:
            report.fail("topology.harness", f"Harness planner {planner!r} is not defined.")
        elif not set(by_id[planner].get("tools") or []) & DELEGATION_TOOLS:
            report.fail("topology.harness", f"Harness planner {planner!r} lacks Agent or Task.")
        # Harness calls remain dynamic, but every declared caller must still exist.
        reachable = {entry}
        changed = True
        while changed:
            changed = False
            for agent in agents:
                if any(caller in reachable for caller in agent.get("invocable_by") or []):
                    if agent.get("id") not in reachable:
                        reachable.add(agent.get("id"))
                        changed = True
        for agent_id in sorted(set(by_id) - reachable):
            report.fail("topology.orphan", f"Agent {agent_id!r} is unreachable in the harness.")

    remote = [agent for agent in agents if agent.get("via") == "codex-mcp"]
    a2a = topology.get("a2a")
    if remote:
        block = _mapping(a2a, "topology.a2a", report)
        _unknown(
            block,
            {"transport", "request_schema", "response_schema", "continuation", "timeout_seconds", "max_retries"},
            "topology.a2a",
            report,
        )
        _required(
            block,
            {"transport", "request_schema", "response_schema", "continuation", "timeout_seconds", "max_retries"},
            "topology.a2a",
            report,
        )
        if block.get("transport") != "codex-mcp":
            report.fail("topology.a2a", "Remote GPT roles require transport: codex-mcp.")
        if block.get("request_schema") != "agentic.review-request/v1":
            report.fail("topology.a2a", "Unsupported A2A request schema.")
        if block.get("response_schema") != "agentic.review-verdict/v1":
            report.fail("topology.a2a", "Unsupported A2A response schema.")
        _boolean(block, "continuation", "topology.a2a", report)
        _integer(block, "timeout_seconds", "topology.a2a", report, minimum=10, maximum=3600)
        _integer(block, "max_retries", "topology.a2a", report, minimum=0, maximum=3)
    elif a2a is not None:
        report.fail("topology.a2a", "A2A configuration is pure cost when no remote role exists.")


def _validate_review(
    net: dict[str, Any],
    agents: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    protocol = _mapping(net.get("review_protocol"), "review_protocol", report)
    _unknown(protocol, {"request_schema", "verdict_schema", "authority", "gates"}, "review_protocol", report)
    _required(protocol, {"request_schema", "verdict_schema", "authority", "gates"}, "review_protocol", report)
    if protocol.get("request_schema") != "agentic.review-request/v1":
        report.fail("review.schema", "review_protocol.request_schema is unsupported.")
    if protocol.get("verdict_schema") != "agentic.review-verdict/v1":
        report.fail("review.schema", "review_protocol.verdict_schema is unsupported.")

    authority = _mapping(protocol.get("authority"), "review_protocol.authority", report)
    _unknown(authority, {"mode", "endpoint", "project_id", "fail_closed", "human_override"}, "review_protocol.authority", report)
    _required(authority, {"mode", "endpoint", "project_id", "fail_closed", "human_override"}, "review_protocol.authority", report)
    mode = _enum(authority, "mode", ENUMS["authority_mode"], "review_protocol.authority", report)
    endpoint = authority.get("endpoint")
    if endpoint is not None and not isinstance(endpoint, str):
        report.fail("schema.type", "review_protocol.authority.endpoint must be a string or null.")
    _string(authority, "project_id", "review_protocol.authority", report)
    fail_closed = _boolean(authority, "fail_closed", "review_protocol.authority", report)
    if authority.get("human_override") != "AGENTIC_SKIP_REVIEW":
        report.fail("review.override", "human_override must be AGENTIC_SKIP_REVIEW.")
    if mode == "external":
        if not isinstance(endpoint, str) or not endpoint.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            report.fail("review.authority", "External authority requires an HTTPS or loopback endpoint.")
        if not fail_closed:
            report.fail("review.authority", "External authority must fail closed.")
    elif mode == "advisory-local":
        if endpoint is not None or fail_closed:
            report.fail("review.authority", "Advisory local authority requires endpoint: null and fail_closed: false.")
        report.warn(
            "Local review records are content-addressed but forgeable by workspace-write agents; "
            "they are advisory, not an independent approval boundary."
        )

    raw_gates = _sequence(protocol.get("gates"), "review_protocol.gates", report)
    gate_ids: set[str] = set()
    covered: set[str] = set()
    gate_allowed = {
        "id",
        "produced_by",
        "reviewed_by",
        "unit",
        "evidence",
        "risk_threshold",
        "stop_condition",
        "max_rounds",
        "arbiter",
        "on_deadlock",
        "authority",
    }
    for index, raw in enumerate(raw_gates):
        path = f"review_protocol.gates[{index}]"
        gate = _mapping(raw, path, report)
        _unknown(gate, gate_allowed, path, report)
        _required(gate, gate_allowed, path, report)
        gate_id = _identifier(gate.get("id"), f"{path}.id", report)
        if gate_id in gate_ids:
            report.fail("schema.unique", f"Duplicate gate id {gate_id!r}.")
        gate_ids.add(gate_id)
        producer = gate.get("produced_by")
        reviewer = gate.get("reviewed_by")
        for field, ref in (("produced_by", producer), ("reviewed_by", reviewer)):
            _identifier(ref, f"{path}.{field}", report)
            if ref not in by_id:
                report.fail("review.reference", f"{path}.{field} references unknown agent {ref!r}.")
        if producer == reviewer:
            report.fail("review.self-signing", f"Gate {gate_id!r} lets {producer!r} review its own work.")
        if isinstance(producer, str):
            covered.add(producer)
        _enum(gate, "unit", ENUMS["unit"], path, report)
        evidence = _enum(gate, "evidence", ENUMS["ground_truth"], path, report)
        _enum(gate, "risk_threshold", ENUMS["threshold"], path, report)
        _string(gate, "stop_condition", path, report)
        rounds = _integer(gate, "max_rounds", path, report, minimum=1, maximum=2)
        arbiter = gate.get("arbiter")
        if arbiter is not None:
            _identifier(arbiter, f"{path}.arbiter", report)
            if arbiter not in by_id:
                report.fail("review.reference", f"{path}.arbiter references unknown agent {arbiter!r}.")
            if arbiter in {producer, reviewer}:
                report.fail("review.self-signing", f"Gate {gate_id!r} uses a disputant as arbiter.")
        _enum(gate, "on_deadlock", ENUMS["deadlock"], path, report)
        gate_authority = _enum(gate, "authority", ENUMS["gate_authority"], path, report)
        if gate_authority == "enforced" and mode != "external":
            report.fail(
                "review.false-guarantee",
                f"Gate {gate_id!r} cannot claim enforced authority with an advisory local store.",
            )
        if evidence != (net.get("decision") or {}).get("ground_truth"):
            report.fail(
                "review.evidence",
                f"Gate {gate_id!r} evidence does not match decision.ground_truth.",
            )
        if evidence == "judgment":
            if gate_authority != "advisory" or rounds != 1 or arbiter is not None:
                report.fail(
                    "review.judgment",
                    f"Judgment-only gate {gate_id!r} must be advisory, single-round, and unarbitrated.",
                )

    producers = {agent.get("id") for agent in agents if agent.get("produces_changes") is True}
    missing = sorted(producers - covered)
    if missing:
        report.fail("review.coverage", f"Change-producing agents lack review gates: {', '.join(missing)}.")


def check(net: dict[str, Any], probe: dict[str, Any] | None, report: Report) -> None:
    if not isinstance(net, dict):
        report.fail("schema.type", "The document root must be a mapping.")
        return
    top = {
        "version",
        "project",
        "decision",
        "selection",
        "environment",
        "runtime",
        "topology",
        "agents",
        "review_protocol",
    }
    _unknown(net, top, "root", report)
    _required(net, top, "root", report)
    if net.get("version") != 2:
        report.fail("schema.version", "version must be the integer 2.")

    _validate_project(net, report)
    _validate_decision(net, report)
    _validate_selection(net, report)
    _validate_environment(net, report)
    _validate_runtime(net, report)
    agents, by_id = _validate_agents(net, probe, report)
    _validate_topology(net, agents, by_id, report)
    _validate_review(net, agents, by_id, report)

    pattern = (net.get("selection") or {}).get("pattern")
    mode = (net.get("topology") or {}).get("mode")
    runtime = net.get("runtime") or {}
    max_concurrency = runtime.get("max_concurrency")
    if _is_int(max_concurrency):
        for agent in agents:
            if _is_int(agent.get("count")) and agent["count"] > max_concurrency:
                report.fail(
                    "runtime.concurrency",
                    f"Agent {agent.get('id')!r} count {agent['count']} exceeds max_concurrency {max_concurrency}.",
                )
    delegation_depth = (net.get("decision") or {}).get("delegation_depth")
    if _is_int(delegation_depth) and _is_int(runtime.get("max_depth")):
        if delegation_depth > runtime["max_depth"]:
            report.fail(
                "runtime.depth",
                "decision.delegation_depth exceeds runtime.max_depth.",
            )
    if pattern == "direct" and mode != "direct":
        report.fail("selection.topology", "Direct selection requires direct topology mode.")
    if pattern != "direct" and mode == "direct":
        report.fail("selection.topology", "Non-direct selections require graph or harness topology.")
    if mode == "harness" and (net.get("decision") or {}).get("path_predictability") != "emergent":
        report.fail("decision.topology", "Harness mode is reserved for emergent paths.")
    if mode == "graph" and (net.get("decision") or {}).get("path_predictability") == "emergent":
        report.fail("decision.topology", "An emergent path cannot be encoded as a graph.")
    if pattern == "fan-out":
        workstreams = (net.get("decision") or {}).get("workstreams")
        coupling = (net.get("decision") or {}).get("coupling")
        if workstreams == 1 or coupling == "interdependent":
            report.fail(
                "decision.fan-out",
                "Fan-out requires multiple/runtime workstreams that are independent or staged.",
            )


def load_network(path: Path) -> dict[str, Any]:
    value = yamlc.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError("network.yaml must be a mapping")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("network", type=Path)
    parser.add_argument("--probe", type=Path)
    args = parser.parse_args()
    try:
        net = load_network(args.network)
    except FileNotFoundError:
        sys.stderr.write(f"not found: {args.network}\n")
        return 2
    except Exception as error:
        sys.stderr.write(f"malformed YAML: {error}\n")
        return 2

    probe = None
    if args.probe:
        try:
            probe = json.loads(args.probe.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            sys.stderr.write(f"could not read probe: {error}\n")
            return 2

    report = Report()
    check(net, probe, report)
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
