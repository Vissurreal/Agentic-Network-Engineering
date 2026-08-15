# Agentic Engineering completion log

Last updated: 2026-07-28

## Objective

Make explicit invocation of the Agentic Engineering plugin execute the user's
prompt through an appropriate delegated agent workflow. An invocation must not
be dismissed merely because the prompt is not about designing an agent network.

## Evidence and current conclusion

- The supplied screenshot shows an explicit `@agentic-engineering` invocation
  for a research-and-writing task.
- The installed bundle exposes only `design-agent-network`.
- That skill's description is limited to creating or resizing agent
  environments, and its first instruction is to generate configuration and
  exit rather than execute the user's task.
- The plugin and marketplace descriptions repeat that narrow configuration
  scope.

The observed behavior was therefore consistent with a routing defect: no
installed skill claimed explicit plugin invocation for an arbitrary task, and
the only skill expressly refused to perform the prompted work. Version 3
resolves that defect with a broad execution skill and a lifecycle guard.

## Acceptance criteria

1. Explicit plugin invocation routes to an execution skill for research,
   coding, analysis, writing, and other substantive prompts.
2. The execution skill dispatches at least one useful worker before presenting
   a final result. It may report a runtime limitation, but may not silently
   ignore delegation or substitute an explanation of the plugin's scope.
3. Delegation is proportional to task shape, with bounded concurrency,
   non-overlapping ownership, an integration step, and independent QA for
   substantive work.
4. Network-design requests continue to route to the existing configuration
   skill rather than being conflated with task execution.
5. The Claude plugin and Codex-installed representation expose equivalent
   intent.
6. Automated tests cover the screenshot scenario, trigger metadata, mandatory
   dispatch language, execution completion, failure handling, and regression of
   the network-design workflow.
7. Plugin validation, the full existing test suite, and a fresh QA pass pass.

## Progress

- [x] Reproduced the routing explanation from the screenshot and installed
  metadata.
- [x] Read the mandatory plugin-maintenance and network-design instructions.
- [x] Defined a versioned cross-runtime invocation contract with bounded
  concurrency, exclusive ownership, integration, unavailable-runtime
  disclosure, and independent QA.
- [x] Added `execute-delegated-task` plus researcher, implementer, general
  worker, and reviewer roles.
- [x] Added native `.codex-plugin` metadata and skill UI metadata.
- [x] Added a deterministic invocation guard for `UserPromptSubmit`,
  `SubagentStart`, `SubagentStop`, and `Stop`. It injects the route, records a
  completed worker lifecycle, blocks one silent stop, and then terminates
  visibly rather than loop indefinitely. A direct fallback requires both an
  exact unavailable-runtime disclosure and explicit operator opt-in.
- [x] Added the broad invocation skill without weakening the specialized
  network-design skill.
- [x] Added adversarial routing and hook tests using the exact screenshot
  prompt, coding, writing, implicit research, and network-design cases. The
  strengthened suite passes 89 of 89 checks, including direct-skill precedence,
  contract/runtime equality, completed lifecycle enforcement, fallback
  authorization, structural live-event recognition, and live-call refusal.
- [x] Updated both plugin manifests to version 0.3.1 and added the native Codex
  manifest.
- [x] Updated README, design documentation, and the QA report.
- [x] Added an opt-in live-host smoke test that refuses to consume a model call
  without `--allow-model-call`.
- [x] Validated, cache-busted, reinstalled, and inspected both host copies.
- [x] Completed the final independent QA pass and corrected every actionable
  finding.

## Validation checkpoint

- Claude strict plugin validation passes.
- Native Codex plugin validation passes when PyYAML 6.0.3 is supplied from an
  isolated temporary directory.
- Both bundled skills pass the skill-creator metadata validator.
- The default suite passes 160 reported checks with no failures. The invocation
  suite accounts for 89 checks.
- The PyYAML compatibility run initially exposed a pre-existing restricted
  parser defect for doubled apostrophes in single-quoted YAML. The decoder and
  a direct regression assertion were added; all 15 fixture comparisons now
  pass.
- Codex installed and enabled version
  `0.3.1+codex.20260728194349`; Claude updated and enabled version `0.3.1`.
- Both installed copies contain the execution and network-design skills, guard,
  hook declaration, and invocation contract. SHA-256 checks of the execution
  skill, guard, hooks, and contract match the repository.
- No model-consuming live smoke was run because the user did not pass the
  script's explicit authorization flag.
- Codex requires the user to review and trust a new or changed plugin hook
  definition. Until that host trust step is completed, Codex skips the guard;
  the plugin cannot grant itself trust.

## Final QA outcome

The independent reviewer initially identified six issues: a text-only fallback
bypass, acceptance of unfinished workers, direct-skill precedence errors,
undocumented Codex hook trust, weak live-event detection, and contract/runtime
drift. The implementation and tests were revised for all six. The reviewer
then confirmed that the findings were resolved or accurately release-gated.

No unresolved in-repository P0 or P1 finding remains. Two external checks remain
deliberately unexecuted:

- review and trust the current hook definition in Codex through `/hooks`; and
- run the opt-in model-consuming smoke test in a new host task.

## Next steps

1. Restart Claude Code and start a new Claude or Codex task so the host loads
   version 0.3.1.
2. In Codex, open `/hooks`, review the Agentic Engineering hook definition, and
   trust it.
3. When model-call authorization is intended, run the opt-in live smoke once
   per host and record the observed worker event and artifact result.

## Architecture simplification assessment — 2026-07-28

### Conclusion

The plugin is not the simplest runtime architecture for the intended result.
Codex and Claude Code already provide project-scoped instructions, custom
subagents, model/tool restrictions, lifecycle hooks, and MCP integration. The
recommended design is therefore a thin project-local control plane:

- one Claude Code coordinator as the sole scheduler;
- Claude specialists in `.claude/agents/`;
- Codex workers reached through the official `codex mcp-server` tools;
- shared acceptance criteria and verification commands in project guidance;
- deterministic tests, linters, schemas, and file hashes before model review;
- one authoritative writer and one independent reviewer;
- one review-and-repair round by default, with explicit time, token, handoff,
  and iteration caps.

Subagents reduce main-thread context pollution but do not inherently reduce
aggregate token use. Every additional agent pays for task restatement, project
context, tool discovery, and result reconciliation. Fan-out is justified only
for independent partitions, and cross-vendor review is justified only when it
removes a named failure mode.

The existing plugin remains useful as an optional scaffold or installer across
many repositories. It should not be the primary scheduler, invocation router,
or permanent agent graph for a single project.

### Verified environment

- Claude Code 2.1.220 is installed and authenticated.
- Codex CLI 0.145.0 is installed and authenticated.
- `codex mcp-server` initializes and exposes `codex` and `codex-reply`.
- Selected Codex model access and a complete Claude-to-Codex task remain
  unverified because no authorized live model call was made.
- This repository currently has no `AGENTS.md`, `CLAUDE.md`, or
  `network.yaml`, and it is not a Git repository.

### Recommended next steps

1. Replace plugin-owned runtime routing with repository-owned guidance and
   native agent definitions.
2. Make Claude Code the single coordinator and configure Codex as a
   project-scoped stdio MCP server.
3. Define only three default logical roles: coordinator, worker, and verifier.
   Add specialists only for a named recurring failure mode.
4. Implement a bounded sequence:
   task contract → production → deterministic checks → independent review →
   one targeted repair → final acceptance.
5. Pass agents compact task contracts, relevant file paths, diffs, and test
   evidence rather than full conversation transcripts.
6. Verify one live Claude-to-Codex run before treating cross-vendor review as a
   dependable project capability.
7. Retain the plugin only if reusable cross-project installation and scaffolding
   justify its maintenance cost.

### Sources checked

- Current Codex manual sections on subagents, `AGENTS.md`, project
  `.codex/config.toml`, custom agents, hooks, plugins, non-interactive
  execution, and `codex mcp-server`.
- Claude Code documentation on custom subagents, parallel-agent choices,
  project hooks, and project-scoped stdio MCP servers.
