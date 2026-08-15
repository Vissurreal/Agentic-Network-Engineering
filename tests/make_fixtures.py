#!/usr/bin/env python3
"""Generate valid and adversarial version 2 network fixtures."""

from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import _yamlcompat as yamlc  # noqa: E402


def scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = " ".join(str(value).split())
    if text == "" or any(char in text for char in ":#[]{}&*!|>'\"%@`"):
        return "'" + text.replace("'", "''") + "'"
    return text


def dump(obj, indent=0):
    pad = " " * indent
    output = []
    for key, value in obj.items():
        if isinstance(value, dict) and value:
            output.append(f"{pad}{key}:")
            output.append(dump(value, indent + 2))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            output.append(f"{pad}{key}:")
            for item in value:
                body = dump(item, indent + 4).lstrip()
                output.append(f"{pad}  - {body}")
        elif isinstance(value, list):
            output.append(f"{pad}{key}: [{', '.join(scalar(item) for item in value)}]")
        else:
            output.append(f"{pad}{key}: {scalar(value)}")
    return "\n".join(output)


def write(name, value):
    pathlib.Path(name).write_text(dump(value) + "\n", encoding="utf-8")


def clean_scout(identifier):
    return {
        "id": identifier,
        "role": "Retrieves bounded evidence with provenance.",
        "rank": "scout",
        "provider": "anthropic",
        "model": "haiku",
        "via": "native",
        "effort": "low",
        "count": 1,
        "default_active": True,
        "max_turns": 20,
        "context_budget_tokens": 40000,
        "memory": "none",
        "isolation": "read-only",
        "tools": ["Read", "Glob", "Grep"],
        "invocable_by": ["orchestrator"],
        "reports_to": "orchestrator",
        "produces_changes": False,
        "accepts": "A bounded retrieval question.",
        "produces": "Verbatim excerpts with provenance.",
        "prevents": "High-volume retrieval consuming the lead role's reasoning context.",
        "prose": "Return evidence and provenance without conclusions.",
    }


def add_graph_agent(network, agent):
    network["agents"].append(agent)
    network["topology"]["graph"]["edges"].append(
        {
            "from": "orchestrator",
            "to": agent["id"],
            "message": "Retrieval request.",
            "condition": "retrieval is required",
        }
    )


def build():
    base = yamlc.safe_load(
        (ROOT / "assets" / "templates" / "network.yaml.template").read_text(encoding="utf-8")
    )
    write("00-valid.yaml", base)

    direct = copy.deepcopy(base)
    direct["selection"]["pattern"] = "direct"
    direct["topology"] = {
        "mode": "direct",
        "invocation_policy": "descriptive",
        "entry_agent": None,
    }
    direct["agents"] = []
    direct["review_protocol"]["gates"] = []
    direct["decision"]["context_isolation"] = "shared"
    write("01-direct-valid.yaml", direct)

    cases = {}
    value = copy.deepcopy(base)
    value["review_protocol"]["gates"] = []
    cases["10-no-review-gate.yaml"] = value

    value = copy.deepcopy(base)
    value["decision"]["search_breadth"] = "broad"
    scout = clean_scout("scout")
    scout["tools"].append("Bash")
    add_graph_agent(value, scout)
    cases["11-scout-bash.yaml"] = value

    value = copy.deepcopy(base)
    value["decision"]["search_breadth"] = "broad"
    add_graph_agent(value, clean_scout("scout-one"))
    add_graph_agent(value, clean_scout("scout-two"))
    cases["12-two-scouts.yaml"] = value

    value = copy.deepcopy(base)
    value["agents"][0]["model"] = "invented-native-model"
    cases["13-invented-model.yaml"] = value

    value = copy.deepcopy(base)
    value["decision"]["ground_truth"] = "judgment"
    gate = value["review_protocol"]["gates"][0]
    gate["evidence"] = "judgment"
    gate["max_rounds"] = 2
    gate["arbiter"] = "arbiter"
    cases["14-judgment-arbitration.yaml"] = value

    value = copy.deepcopy(base)
    value["selection"]["pattern"] = "custom"
    value["selection"]["deviation_rationale"] = None
    cases["15-custom-no-rationale.yaml"] = value

    value = copy.deepcopy(base)
    value["review_protocol"]["gates"][0]["max_rounds"] = "two"
    cases["16-rounds-not-integer.yaml"] = value

    value = copy.deepcopy(base)
    value["agents"][0]["unsafe_extension"] = True
    cases["17-unknown-field.yaml"] = value

    value = copy.deepcopy(base)
    value["agents"][1]["id"] = "orchestrator"
    cases["18-duplicate-id.yaml"] = value

    value = copy.deepcopy(base)
    value["agents"][0]["tools"].remove("Agent")
    cases["19-unexecutable-edge.yaml"] = value

    value = copy.deepcopy(base)
    value["review_protocol"]["gates"][0]["reviewed_by"] = "implementer"
    cases["20-self-review.yaml"] = value

    value = copy.deepcopy(base)
    value["topology"]["mode"] = "harness"
    value["topology"].pop("graph")
    value["topology"].pop("a2a")
    value["agents"] = [agent for agent in value["agents"] if agent["via"] == "native"]
    value["review_protocol"]["gates"][0]["reviewed_by"] = "arbiter"
    value["review_protocol"]["gates"][0]["arbiter"] = None
    value["topology"]["harness"] = {
        "planner": "orchestrator",
        "states": ["plan", "act", "observe", "complete"],
        "termination": "Acceptance criteria hold or iteration cap is reached.",
        "max_iterations": 8,
        "fan_out": {"mode": "runtime", "max_parallel": 3, "partition_by": "workstream"},
    }
    cases["21-harness-for-known-path.yaml"] = value

    for name, value in cases.items():
        write(name, value)

    pathlib.Path("probe-ok.json").write_text(
        json.dumps(
            {
                "claude_models": ["haiku", "sonnet", "opus", "fable"],
                "codex_model_access": "verified",
                "codex_models": ["gpt-5.6-sol"],
            }
        ),
        encoding="utf-8",
    )
    pathlib.Path("probe-unverified.json").write_text(
        json.dumps(
            {
                "claude_models": ["haiku", "sonnet", "opus", "fable"],
                "codex_model_access": "unverified",
                "codex_models": [],
            }
        ),
        encoding="utf-8",
    )
    print("fixtures written")


if __name__ == "__main__":
    build()
