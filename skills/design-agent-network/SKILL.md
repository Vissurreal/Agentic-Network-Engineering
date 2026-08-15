---
name: design-agent-network
description: Use specifically to design, review, or resize a project agent environment, orchestration topology, graph or harness, cross-vendor review path, or project-level Claude and Codex instructions. For an explicit Agentic Engineering invocation that asks to execute research, writing, coding, analysis, or another task, use execute-delegated-task instead.
---

# Design an agent network

If this skill was loaded for a generic Agentic Engineering invocation rather
than an agent-environment design request, read
`../execute-delegated-task/SKILL.md` completely and follow it immediately. Do
not return a scope explanation.

For an actual network-design request, generate configuration and exit. Do not
build a supervisor service or execute the user's project. Read
`references/topology-doctrine.md` and `references/archetypes.md` before
classification.

Every role, edge, loop, transport, and gate must remove a named failure mode.
Delete structure whose marginal benefit does not exceed its coordination,
latency, context, and reliability cost.

## Phase 1 - Probe capabilities

Run:

```text
python ${CLAUDE_PLUGIN_ROOT}/scripts/probe_environment.py .
```

Use the interpreter fallback order `python3`, `python`, then `py`. Installation,
authentication, MCP transport readiness, and model access are separate facts.
Do not infer authentication from a config file. Codex model access remains
unverified unless the user authorizes the bounded live check:

```text
python ${CLAUDE_PLUGIN_ROOT}/scripts/probe_environment.py . --verify-codex-model <model>
```

Never emit a remote role for an unverified model. Degrade to a native reviewer
or stop before approval and state why.

## Phase 2 - Decide whether retrieval should be delegated

Use search breadth, relevant context volume, large artifacts, external
retrieval, and whether provenance extraction can proceed independently. File
count alone is not a criterion.

When delegation pays for itself, dispatch one native Haiku scout using
`references/scout-contract.md`. Its tools are `Read, Glob, Grep, WebSearch,
WebFetch`; it never receives Bash. It returns excerpts and provenance, not
conclusions. When retrieval is bounded, read the relevant material directly and
do not add a scout merely to satisfy a template.

## Phase 3 - Classify and question

Delegate the architectural reasoning to `network-architect`. Supply the probe,
retrieval evidence, and the user's request verbatim. The architect returns:

1. the complete orthogonal decision vector;
2. a graph, harness, or direct-execution verdict;
3. the selected structural pattern and rejected alternatives;
4. at most three questions.

Ask all qualifying questions together. A question qualifies only if different
answers change the decision vector, topology, model, tool permission, evidence
standard, or human gate. Record all other uncertainty as explicit assumptions.

## Phase 4 - Draft outside the project

Return the answers to the same architect. It returns version 2 YAML conforming
to `assets/templates/network.yaml.template`. Store the draft under
`${CLAUDE_PLUGIN_DATA}/drafts/`, not in the project. No project file may be
created or modified before approval.

The specification must include typed project guidance, decision dimensions,
selection rationale, runtime policies, topology-specific state, logical roles,
and content-addressed review contracts. Remote GPT roles remain logical roles.
They are never rendered as Claude agents with GPT model identifiers.

## Phase 5 - Validate and preflight

Validate the external draft:

```text
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_network.py <draft.yaml> --probe <probe.json>
```

Route failures back to the architect. Then obtain the exact project diff:

```text
python ${CLAUDE_PLUGIN_ROOT}/scripts/emit_network.py <draft.yaml> \
  --root . --probe <probe.json> --preflight --install-spec
```

Validation rejects unknown safety fields, invalid model/runtime combinations,
unexecutable edges, uncovered producers, and false claims of enforced review.

## Phase 6 - Approval gate

Present:

1. the generated Mermaid network;
2. the decision vector and structural rationale;
3. roles with rank, runtime, model, effort, count, active default, tools,
   isolation, reporting line, and failure mode;
4. every review gate and whether it is advisory or externally enforced;
5. rejected alternatives and assumptions;
6. the preflight classification and exact diff for every file.

Ask for approval, revision, or rejection. Rejection leaves the project
byte-for-byte unchanged. Revision returns to phase 4. Conflicting unmanaged
files require separate, explicit approval of the displayed diff.

## Phase 7 - Emit transactionally

After approval:

```text
python ${CLAUDE_PLUGIN_ROOT}/scripts/emit_network.py <draft.yaml> \
  --root . --probe <probe.json> --install-spec
```

Add `--approve-conflicts` only when the user approved the exact conflicting
diff from phase 6. The compiler validates again, merges supported structured
configuration, stages all artifacts, atomically replaces targets, and restores
the previous state if a write fails.

Native roles compile to valid Claude project agents. Each remote Codex role
compiles to a native Claude dispatcher with `mcp__codex__codex` and
`mcp__codex__codex-reply`, a valid Claude model, the remote model argument, and
thread continuation instructions.

## Phase 8 - Smoke test

Run `emit_network.py --check`. Then dispatch a trivial content-addressed review
through the emitted adapter. Confirm:

- a real Codex response and thread identifier when cross-vendor access was
  verified;
- response-schema validation;
- a current file hash passes and a subsequent edit invalidates it;
- an unavailable external authority fails closed;
- advisory-local mode is reported as advisory, never as structural approval.

Report any unexecuted live check as unverified rather than passed.

## References

| File | Purpose |
|---|---|
| `references/topology-doctrine.md` | Graph, harness, and loop selection |
| `references/archetypes.md` | Decision rubric and structural patterns |
| `references/model-assignment.md` | Logical role and runtime adapter models |
| `references/scout-contract.md` | Retrieval-only scout |
| `references/review-contract.md` | Content-addressed review protocol |
| `references/emitted-artifacts.md` | Transactional output contract |
