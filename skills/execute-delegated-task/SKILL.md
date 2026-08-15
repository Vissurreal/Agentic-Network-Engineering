---
name: execute-delegated-task
description: Use whenever the user explicitly invokes or mentions Agentic Engineering for a substantive task, including research, analysis, writing, coding, review, data, document, or operational work, or explicitly requests useful subagent delegation. Execute and finish the prompted task through bounded workers; do not design an agent network unless the user asks for one.
---

# Execute a delegated task

Treat the text accompanying the plugin invocation as the task. Complete that
task. Never answer only that the plugin is irrelevant, limited to agent-network
design, or unable to help.

## Mandatory invocation contract

Before presenting a final result, dispatch at least one bounded worker whose
output materially contributes to the requested result. Do this before
performing all substantive work in the coordinator. A plan or a promise to
delegate is not a dispatch.

Use the host's native subagent primitive:

- Codex: a collaboration subagent such as `spawn_agent`;
- Claude Code: the `Agent` tool with the plugin's scoped researcher,
  implementer, or reviewer agent;
- another host: its equivalent isolated worker mechanism.

If no delegation primitive is callable, state `Delegation unavailable in this
runtime`. A direct fallback is permitted only when the operator has explicitly
set `AGENTIC_ENGINEERING_ALLOW_DIRECT_FALLBACK=1`; otherwise report the
capability blocker without claiming completion. Never conceal the limitation,
claim that delegation occurred, or replace task execution with a scope
explanation.

## Execute

1. Parse the requested outcome, destination, evidence standard, constraints,
   and write authority. Preserve the user's prompt verbatim in worker briefs
   when nuance matters.
2. Choose the smallest useful decomposition from
   `references/task-routing.md`. Default to at most three concurrent workers
   and never exceed four.
3. Give every worker a concrete objective, exclusive scope, permitted actions,
   evidence requirements, and an output contract. Workers must not ask the
   user questions or make external commitments.
4. Keep user communication, integration, consequential decisions, and shared
   file ownership in the coordinator. Never assign overlapping same-file
   writes. Prefer read-only worker outputs and apply integrated changes once.
5. Continue useful coordinator work while independent workers run. Collect
   every dispatched result; do not finish while useful workers are still
   running.
6. Integrate the evidence and complete the actual requested artifact or
   action. A task requested in an Obsidian vault, repository, document, or
   other supplied destination is not complete until the deliverable exists
   there or a precise access blocker is reported.
7. Apply `references/qa-contract.md`. For substantive work, dispatch an
   independent reviewer after an inspectable draft or change exists. Route a
   failed source trace or acceptance criterion back to implementation, not to
   cosmetic rewriting.
8. Return the outcome, material verification, and any genuinely unexecuted
   check. Mention worker mechanics only when they affect confidence or when the
   user asks.

## Boundaries

- A request to create, review, or resize an agent environment belongs to the
  sibling `design-agent-network` skill.
- Delegation does not broaden permissions. Workers inherit the task's safety,
  privacy, approval, and external-action limits.
- Do not delegate trivial coordination overhead that exceeds the value of the
  worker, but explicit plugin invocation still requires one useful bounded
  dispatch.
- Workers may not recursively delegate unless the coordinator explicitly
  authorizes one additional level for a named failure mode.
