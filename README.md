# Agentic Engineering

Agentic Engineering completes substantive tasks through bounded delegated
workers and independent QA. It also retains a specialized compiler for
designing project-specific Claude and Codex agent environments.

Explicit invocation is an execution request. The plugin must not answer by
describing its scope or silently omit delegation. Research, analysis, writing,
and implementation prompts route to `execute-delegated-task`; agent-network
configuration prompts route to `design-agent-network`.

## Install and develop

Claude Code:

```text
/plugin marketplace add C:\Users\upsca\Projects\Agentic Engineering
/plugin install agentic-engineering@agentic-engineering
```

To test the working tree without the Claude marketplace cache:

```text
claude --plugin-dir "C:\Users\upsca\Projects\Agentic Engineering"
```

Codex:

```text
codex plugin marketplace add "C:\Users\upsca\Projects\Agentic Engineering"
codex plugin add agentic-engineering@agentic-engineering
```

After changing an installed Codex plugin, run the plugin-creator cachebuster
and reinstall workflow so a new task loads the current files.

Codex treats plugin command hooks as untrusted after installation or whenever
their definition changes. Review and trust the current Agentic Engineering
hooks through `/hooks`; until then Codex skips the guard. This is a host
security boundary, not a setting the plugin can override.

## Use

For a general task:

```text
/agentic-engineering:execute-delegated-task Research this question, write the requested note, and verify the material claims.
```

In Codex, invoke the corresponding installed skill:

```text
$agentic-engineering:execute-delegated-task Implement this change and verify it.
```

The execution workflow:

1. classifies the task as research, implementation, analysis, writing, or
   general work;
2. dispatches at least one real worker before the final response;
3. gives concurrent workers non-overlapping ownership, with a default limit of
   three and a hard limit of four;
4. integrates worker outputs in the parent context;
5. uses an independent reviewer for substantive work; and
6. verifies the requested destination artifact before completion.

If the runtime cannot delegate, the response must say
`Delegation unavailable in this runtime`. A bounded direct fallback is allowed
only when the operator explicitly sets
`AGENTIC_ENGINEERING_ALLOW_DIRECT_FALLBACK=1`; the phrase alone cannot bypass
the guard. The response may not claim that delegation occurred.

For agent-network design:

```text
/agentic-engineering:design-agent-network
```

That specialized workflow probes runtime capabilities, derives the smallest
justified topology, validates it, and shows the exact preflight diff before
requesting approval. It does not write project files before approval.

## Invocation guard

`hooks/hooks.json` supplies a cross-runtime lifecycle guard:

- `UserPromptSubmit` detects explicit Agentic Engineering markers and injects
  the selected route and dispatch requirement.
- `SubagentStart` records an actual dispatch and gives the worker the
  material-contribution requirement.
- `SubagentStop` records completion of that worker lifecycle.
- `Stop` permits a completed lifecycle, permits an operator-enabled disclosed
  unavailable-runtime fallback, or blocks one silent completion attempt.
- A repeated silent stop terminates visibly instead of creating an infinite
  retry loop.

The state is stored outside the target workspace. The guard never treats a
written plan, a claim of delegation, a started-but-unfinished worker, or the
fallback phrase alone as satisfaction.

The guard mechanically establishes a worker lifecycle, not semantic usefulness
or correct integration. The execution skill, worker context, destination
checks, and reviewer contract govern those properties; the live smoke can
observe events and an artifact but cannot prove the quality of model judgment.

## Agent-network compiler

The version 2 `.agentic/network.yaml` format records independent dimensions for
workflow shape, scope, evidence, reversibility, consequence, delegation,
isolation, topology, role contracts, A2A behavior, and review gates. It has no
single complexity tier.

Native Anthropic roles compile to `.claude/agents/*.md`. Logical OpenAI roles
compile to Claude dispatcher roles that call the configured Codex MCP tools,
pass the remote model as an argument, and retain the returned thread
identifier. The compiler safely merges managed content, refuses unmanaged
conflicts, stages writes, rolls back failures, and records hashes.

Local review records are advisory because agents with workspace-write access
can alter them. Enforced review requires an authority outside that boundary and
fails closed when the authority is unavailable.

## Verification

```text
python tests\run.py
claude plugin validate . --strict
python C:\Users\upsca\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

The default suite is model-free. It covers the exact reported research prompt,
general routing, required dispatch, lifecycle enforcement, role safety,
network-design regression, strict schema validation, safe emission, hook
contracts, rollback, and end-to-end generation.

An authenticated smoke test is available but refuses to consume a model call
unless authorization is explicit:

```text
python scripts\live_invocation_smoke.py --host claude --allow-model-call
python scripts\live_invocation_smoke.py --host codex --allow-model-call
```

Run live checks in a disposable directory. A passing smoke test requires a
structurally parsed worker-start event and the requested output artifact. The
Codex variant uses an ephemeral workspace-write run and explicitly enables the
already-reviewed hook definition for that process; this does not establish
persistent hook trust for future interactive tasks.
