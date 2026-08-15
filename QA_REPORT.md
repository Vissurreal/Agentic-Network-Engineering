# Agentic Engineering Plugin — QA Remediation Report

**Date:** 2026-07-28  
**Scope:** Agent-network decisions, schema validation, emission, review
contracts, Claude/Codex interoperability, Relay integration, and automated QA.  
**Current status:** The original network-design remediation and the version 3
general-task invocation remediation are implemented and pass model-free
validation. Live hosted-model dispatch, externally enforced approval, and live
cross-vendor review remain explicit integration gates.

## Executive conclusion

The original QA report correctly found that the plugin's implementation did not
support several of its central claims. The implementation now:

- routes explicit Agentic Engineering task invocations to a general execution
  workflow instead of dismissing prompts outside agent-network design;
- requires an observed completed worker lifecycle, bounded non-overlapping
  ownership, integration, destination verification, and independent QA;
- uses a lifecycle guard to block one silent completion attempt and then
  terminate visibly rather than loop;
- derives architecture from an orthogonal decision vector rather than a
  complexity tier;
- strictly validates logical roles, topology, runtime compatibility, review
  coverage, and safety-sensitive fields;
- compiles GPT roles into valid Claude-to-Codex dispatcher adapters instead of
  invalid Claude subagents;
- preflights, merges, stages, and transactionally emits project artifacts;
- binds review requests and verdicts to exact content hashes;
- identifies the local review ledger as advisory and fails closed when an
  external authority is configured but unavailable;
- treats `.agentic/network.yaml` as Relay's editable source of truth;
- exposes session activation, role specifications, and structured dispatch
  lifecycle state in Relay.

Three guarantees are intentionally not claimed:

1. Static routing and hook tests do not prove that every hosted model build
   will select the execution skill, assign useful work, or integrate the
   result. Codex also skips new or changed plugin hooks until the user reviews
   and trusts them. The opt-in authenticated smoke test observes a worker event
   and artifact but is not proof of semantic quality or persistent hook trust.
2. The repository does not include or deploy an external verdict authority.
   The workspace-local ledger cannot provide an unforgeable independence
   guarantee against an agent with project write access.
3. No paid or model-consuming Claude-to-Codex review was invoked during this
   remediation. Installation, authentication, and MCP transport are verified,
   but access to the selected Codex model and a live returned verdict remain
   unverified.

The plugin is suitable for continued development and advisory use. A release
that advertises structurally enforced independent approval or functional
cross-vendor review remains blocked.

## Remediation status

| Original finding | Status | Implemented change and evidence |
|---|---|---|
| P0: explicit plugin invocation ignored delegation | Statically resolved; trusted live host check pending | [`execute-delegated-task`](skills/execute-delegated-task/SKILL.md) claims general task invocations and requires a material worker result. [`invocation_guard.py`](scripts/invocation_guard.py) honors direct-skill precedence, records a complete `SubagentStart`/`SubagentStop` lifecycle, rejects a phrase-only fallback, blocks one silent stop, and then fails visibly. [`test_invocation.py`](tests/test_invocation.py) includes the exact reported research prompt plus conflicting direct-skill markers, implementation, writing, untagged, and network-design regression cases. Codex enforcement requires user trust of the current hook definition. |
| P0: forgeable review records | Partially resolved by design | [`assets/hooks/review_contract.py`](assets/hooks/review_contract.py), [`create_review_request.py`](assets/hooks/create_review_request.py), and [`record_verdict.py`](assets/hooks/record_verdict.py) use strict versioned contracts, canonical digests, safe relative paths, exact file hashes, reviewer identity, bounded rounds, and non-overwriting records. [`verify_review_coverage.py`](assets/hooks/verify_review_coverage.py) rejects stale, missing, malformed, failing, deleted-file, and hash-mismatched coverage. Local mode is explicitly advisory. External mode fails closed, but the authority service itself is a remaining release gate. |
| P0: non-executable Claude-to-Codex reviewer | Statically resolved; live check pending | [`scripts/emit_network.py`](scripts/emit_network.py) emits a valid native Claude dispatcher with `mcp__codex__codex` and `mcp__codex__codex-reply`, passes the logical GPT model, preserves the returned thread identifier in its protocol, and never emits a GPT model as Claude frontmatter. The local Codex MCP server initialized successfully and exposed both required tools. |
| P1: complexity-tier topology | Resolved | [`network.yaml.template`](assets/templates/network.yaml.template), [`SKILL.md`](skills/design-agent-network/SKILL.md), [`network-architect.md`](agents/network-architect.md), [`archetypes.md`](skills/design-agent-network/references/archetypes.md), and [`DESIGN.md`](DESIGN.md) now use independent workflow, scope, evidence, risk, reversibility, and isolation dimensions. |
| P1: unsound validator | Resolved for declared version 2 schema | [`scripts/validate_network.py`](scripts/validate_network.py) rejects unknown safety fields, invalid types and enums, duplicate identifiers, dangling references, invented models, provider/transport mismatches, uncovered producers, self-review, unsafe scouts, invalid arbitration, unverified remote models, unexecutable edges, and topology contradictions. All seven original adversarial cases are regression fixtures. |
| P1: descriptive read-only/reporting restrictions | Resolved or relabeled | Bash is treated as mutating and is prohibited for a read-only scout. Reporting lines remain editable logical metadata and are documented as descriptive when a runtime cannot enforce caller identity. |
| P1: contradictory approval and destructive emission | Resolved | The skill keeps the draft outside the project until approval. The emitter supports read-only preflight with exact diffs, structured merges, unmanaged-conflict refusal, explicit conflict approval, staged writes, rollback, manifest hashes, and drift checks. Direct mode emits no agents, hooks, MCP server, or Codex agent configuration. |
| P1: missing agent and harness specification | Resolved at the logical/compiler layer | Version 2 records rank, provider, model, effort, count, default activation, maximum turns, context budget, memory, isolation, tools, contracts, reporting, cancellation/retry policy, graph edges, harness loop behavior, A2A schemas, and review gates. The validator also checks declared concurrency and delegation limits. |
| P1: incomplete project guidance | Resolved | Typed project guidance is part of the approved network and is deterministically rendered into managed `CLAUDE.md` and `AGENTS.md` sections. Unused templates were removed. |
| P1: Relay drift and missing state | Resolved, subject to live lifecycle test | [`bridge/agent-store.mjs`](../AI%20GUI/bridge/agent-store.mjs) reads and updates version 2 `network.yaml`, invokes the shared validator/compiler, and preserves comments and unrelated data. Relay exposes managed role fields and session-only activation. [`bridge/server.mjs`](../AI%20GUI/bridge/server.mjs) and [`dispatch-tracker.mjs`](../AI%20GUI/bridge/dispatch-tracker.mjs) track queued, running, blocked, completed, failed, and cancelled states from structured CLI events. |
| P2: false Codex readiness | Resolved | [`scripts/probe_environment.py`](scripts/probe_environment.py) distinguishes installation, authentication, MCP initialization/tool discovery, and selected-model access. Model access remains `unverified` unless the user explicitly authorizes the bounded live check. |
| P2: file-count scouting proxy | Resolved | Scouting is based on search breadth, relevant bytes, large artifacts, external retrieval, and provenance needs rather than a fixed file-count threshold. |

## Verified behavior

### Plugin

`python tests\run.py`

- Plugin invocation: 89 passed.
- Invariants: 17 passed.
- Emitter: 27 passed.
- Review hooks: 17 passed.
- End to end: 10 passed.
- Default aggregate: 160 passed, 0 failed.

The dependency-free run skipped the parser cross-check because PyYAML is not
globally installed. PyYAML 6.0.3 was supplied from an isolated temporary
directory for the compatibility gate:

- YAML parser compatibility: 15 fixtures passed, 0 failed.
- The stricter run found and prompted correction of doubled-apostrophe decoding
  in the restricted parser.

The tests cover the exact reported plugin prompt, explicit and implicit routing,
required worker dispatch, bounded stop handling, unavailable-runtime
disclosure, role permissions, network-design regression, the original
adversarial validator cases, unverified remote models, malformed input, direct
execution, exact preflight diffs, safe merges, dispatcher output, drift,
unmanaged conflicts, rollback, stale verdicts, reviewed deletions, malicious
paths and hashes, human override, and external-authority failure.

Plugin validation:

- `claude plugin validate . --strict`: passed with Claude Code 2.1.220.
- Native Codex plugin-creator validation: passed.
- Codex installed and enabled
  `agentic-engineering@agentic-engineering` version
  `0.3.1+codex.20260728194349`.
- Claude updated and enabled the same plugin at version `0.3.1`.
- Installed copies contain both skills, the invocation guard, the hook
  declaration, and the invocation contract. SHA-256 comparisons for the
  execution skill, guard, hooks, and contract match the source tree.

`python scripts\doctor.py`

- Python 3.14.6 detected.
- Claude installed and authenticated.
- Codex installed and authenticated.
- Codex MCP initialized and exposed `codex` and `codex-reply`.
- Selected Codex model access remains unverified because no live call was
  authorized.

### Relay

From `C:\Users\upsca\Projects\AI GUI`:

- `npm test`: 27 passed, 0 failed.
- `npm run typecheck`: passed.
- `npm run lint`: passed.
- `npm run desktop:build`: passed.
- `npm run desktop:test`: renderer, bridge connection, both terminal sessions,
  metrics, and agent manager checks passed.
- `npm audit --omit=dev`: 0 production vulnerabilities.

The desktop test emitted two `AttachConsole failed` errors from the Node PTY
cleanup helper after reporting success. The command exited zero and the tested
UI state was correct, but the cleanup noise should be fixed before treating the
desktop test as fully clean.

The full development dependency audit reports 25 advisories: 1 low and 24 high.
They are confined to development/build dependencies, including Electron
Builder, ESLint, Vite, and their transitive trees. Production dependencies
report zero advisories. A forced audit fix currently proposes major-version
changes or an Electron Builder downgrade, so it was not applied without a
separate compatibility pass.

## Fresh QA assessment

### Resolved sources

Runtime adapter fields and MCP naming were checked against current official
Claude Code documentation:

- <https://code.claude.com/docs/en/sub-agents>
- <https://code.claude.com/docs/en/mcp>
- <https://code.claude.com/docs/en/hooks>
- <https://code.claude.com/docs/en/plugins-reference>

Codex plugin packaging, skill invocation policy, and plugin-bundled hook
behavior were checked against the current Codex manual and official plugin
documentation:

- <https://developers.openai.com/plugins/build/plugins>

Local runtime checks independently confirmed the installed CLI versions,
authentication states, MCP initialization, and discovered tool names.

### Acceptance criteria

The implementation now satisfies the code-verifiable acceptance criteria for:

- explicit general-task routing with no scope-only dismissal;
- at least one recorded completed worker lifecycle, or both operator opt-in and
  an explicit unavailable-runtime disclosure;
- bounded concurrency, exclusive writer ownership, parent integration,
  independent QA, and destination verification;
- one bounded stop retry with visible termination on repeated noncompliance;
- preservation of the specialized network-design route;
- scope-and-scale topology selection without complexity ranking;
- user-visible approval and exact preflight before project writes;
- editable role, rank, model, effort, count, permissions, reporting, and
  activation metadata;
- minimal-role and named-failure-mode checks;
- no declared self-review;
- runtime-valid Claude/Codex adapter generation;
- conditional graph, harness, fan-out, arbitration, and A2A declarations;
- Relay source-of-truth editing and lifecycle state;
- safe integration into existing configured projects.

It does not yet satisfy the acceptance criteria for a live observed hosted
plugin dispatch, an unforgeable external review authority, or a live observed
Claude-to-Codex verdict.

### Contradictions and unsupported claims

README and design documentation now distinguish verified compiler behavior
from unverified live behavior. The local ledger is not represented as
independent approval. Reporting lines are not represented as runtime access
control. Model installation and authentication are not represented as model
access.

No contradiction was found between the version 2 template, validator, emitter,
hook contracts, and Relay's managed-role representation in the exercised
fixtures.

## Remaining release gates and next steps

1. **Authorized live plugin invocation.** Run one bounded invocation through
   each installed host with
   `python scripts\live_invocation_smoke.py --host <claude|codex>
   --allow-model-call`. Require an observed worker tool event and the requested
   output artifact. Before an interactive Codex test, review and trust the
   current hook definition through `/hooks`; the smoke's process-local bypass
   does not establish persistent trust. This consumes model calls and is never
   part of the default test suite.
2. **External review authority.** Implement a verdict service outside the
   agent-writable workspace. It must authenticate mutation requests, bind
   approvals to project identity and exact file hashes, record reviewer
   identity independently of model-authored workspace files, survive or
   explicitly fail closed across process restarts, and expose only read-only
   verification to the Stop hook. Add hostile forgery, deletion, replay, and
   unavailable-service tests.
3. **Authorized live cross-vendor smoke.** Run
   `python scripts\doctor.py --verify-codex-model <approved-model>`, then execute
   one trivial Claude dispatcher request through Codex MCP. Verify the returned
   thread identifier, a stateful follow-up, schema-valid verdict, cancellation,
   and a failure case. This consumes a model call and therefore was not run
   implicitly.
4. **Relay live lifecycle test.** Dispatch a bounded non-destructive task
   through each CLI and verify that the UI receives actual queued/running/final
   events, not only reducer fixtures. Resolve the Windows PTY cleanup errors
   observed after the desktop smoke test.
5. **Dependency compatibility pass.** Upgrade Vite to a patched release and
   evaluate supported Electron Builder/ESLint upgrades without accepting
   npm's proposed forced downgrade. Re-run build, package, desktop, and audit
   checks.
6. **Coverage expansion.** Add golden prompt-to-decision cases for data,
   migration, incident response, policy, and high-consequence small-scope work.
   Add property tests for graph reachability and schema mutation.

## Final release boundary

The explicit-invocation routing defect and the original
architecture-selection, validation, safe-generation, review-contract, and
Relay source-of-truth defects have in-repository remediations and regression
tests. The project must still be described as using an advisory local review
ledger unless an external authority is configured. Hosted-model dispatch and
cross-vendor review are statically wired but not functionally verified until
their authorized live smoke tests pass.
