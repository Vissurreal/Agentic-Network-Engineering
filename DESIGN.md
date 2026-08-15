# Agentic Engineering - version 3 design

Status: implemented and under final verification  
Date: 2026-07-28

## Purpose

The plugin has two explicit routes:

- task execution, which completes research, implementation, analysis, writing,
  and other work through bounded delegated workers; and
- agent-network design, which derives and emits the smallest justified project
  agent environment.

The network designer remains a compiler. The execution route is a runtime
workflow and must not substitute a scope explanation for the requested task.

## Invocation and execution

Explicit Agentic Engineering invocation routes to
`skills/execute-delegated-task/SKILL.md` unless the prompt is specifically
about designing or resizing an agent network. At least one actual worker must
start before a general task can complete. A plan or prose claim is not a
dispatch.

The parent owns decomposition, integration, destination verification, and the
final answer. Direct named-skill markers take precedence over keyword
classification. Workers receive exclusive ownership. Concurrency defaults to
three and cannot exceed four; concurrent writers never share a file. A
separate reviewer checks substantive results against sources, acceptance
criteria, user instructions, stakes, constraints, contradictions, and
unsupported claims.

The invocation contract is versioned in
`assets/contracts/invocation-v1.json`. The lifecycle guard records explicit
invocations and actual `SubagentStart` and `SubagentStop` events outside the
project workspace. It blocks one silent stop, then terminates visibly. If
delegation is genuinely unavailable, the fallback must disclose that fact,
must have explicit operator opt-in, and must not claim a worker ran.

The guard verifies lifecycle facts only. It injects a material-contribution
instruction into the worker but cannot mechanically prove that the worker was
useful or that the parent integrated its result. Those are model-mediated
contract requirements and remain part of live qualitative review.

Codex skips new or changed plugin command hooks until the user reviews and
trusts their exact definition. Enforcement is therefore conditional on host
hook trust; the plugin cannot silently grant that trust to itself.

## Decision model

Topology is derived from independent dimensions:

```yaml
decision:
  path_predictability: known | partially-known | emergent
  workstreams: positive-integer | runtime-determined
  coupling: independent | staged | interdependent
  information_volume: bounded | large | runtime-determined
  search_breadth: bounded | broad | runtime-determined
  external_retrieval: boolean
  ground_truth: mechanical | documentary | judgment
  reversibility: reversible | costly | irreversible
  consequence: low | material | high
  delegation_depth: integer
  human_gates: [string]
  context_isolation: shared | clean-room | cross-vendor
```

The compiler contains no complexity tier. Graph, harness, fan-out, supervision,
review, arbitration, and A2A are separate decisions.

## Logical and runtime layers

The logical schema records intent, topology, roles, gates, and policies without
pretending every runtime supports every field. Runtime adapters compile only
supported fields.

Native Anthropic roles compile to Claude project agents. Remote OpenAI roles
compile to native Claude dispatcher agents. Dispatchers use Codex MCP tool
names discovered from the installed server, pass the logical GPT model as an
argument, preserve the returned thread identifier, and validate the response
contract.

Reporting lines remain visible and editable but are labeled descriptive because
Claude project agents do not enforce caller identity.

## Validation

`scripts/validate_network.py` rejects:

- unknown safety-relevant fields and invalid types or enums;
- duplicate identifiers and dangling references;
- invented native model aliases and unverified remote models;
- remote roles rendered as native roles or granted Claude tools;
- unsafe scouts, unnecessary duplicate scouts, and file-count-based scouting;
- unreachable or unexecutable graph edges;
- graph selection for emergent paths and harness selection for non-emergent
  paths;
- uncovered producers, self-review, disputant arbiters, and unbounded loops;
- mechanical claims for judgment-only review;
- enforced review without an external fail-closed authority.

## Approval and emission

The draft lives under `${CLAUDE_PLUGIN_DATA}` until approval. Preflight derives
the complete target state and prints exact diffs. Targets are absent, managed,
mergeable, conflicting, or stale-managed. Unmanaged conflicts block without a
dedicated approval flag.

Emission stages all bytes before replacement and keeps backups for rollback.
Structured JSON is merged; Markdown and TOML use delimited managed sections.
Derived artifact hashes are recorded in `.agentic/manifest.json`.

## Review contract

Requests and verdicts use canonical, versioned JSON schemas. Both bind file
hashes and identities. The Stop hook exempts generated files only while they
match the manifest.

The local ledger is advisory because it shares the workspace-write boundary.
External mode delegates hash verification to an authority endpoint and fails
closed. No local file is represented as an unforgeable approval.

## Relay contract

Relay reads and edits version 2 `network.yaml`, uses the emitted generator
metadata to call the same validator and compiler, and does not directly edit
derived managed Markdown. Activation overlays are session-local. Dispatches
use structured CLI streams and expose explicit lifecycle states.

## Release criteria

Release requires both plugin validators, the complete Python suite, invocation
and hook-lifecycle regressions, Relay tests, Relay typecheck, and Relay lint to
pass. Installation tests must confirm that the cached plugin contains both
skills and the guard.

Static tests establish routing, lifecycle enforcement, and host-command
contracts. They cannot prove that a particular hosted model will select a
skill, assign useful work, or integrate a returned result correctly. The
opt-in live smoke test parses host JSONL for a worker-start event and checks the
requested artifact, but remains a smoke assertion rather than a proof of
semantic quality. It requires explicit authorization because it consumes a
model call.
