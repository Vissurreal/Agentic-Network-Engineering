# Emitted artifacts

The approved `.agentic/network.yaml` is the logical source of truth.

The compiler emits:

- typed project guidance and the network map into managed sections of
  `CLAUDE.md` and `AGENTS.md`;
- native Claude roles under `.claude/agents/`;
- native dispatcher roles for logical Codex agents;
- merged hook configuration in `.claude/settings.json`;
- a merged Codex MCP entry in `.mcp.json`;
- a delimited `[agents]` block in `.codex/config.toml`;
- `.agentic/DECISIONS.md`, `runtime.json`, and `manifest.json`;
- content-addressed request and verdict helpers under `.claude/hooks/`.

Preflight classifies targets as absent, managed, mergeable, conflicting, or
stale-managed and prints exact diffs. Unmanaged conflicts block unless the user
approved that diff and the caller passes `--approve-conflicts`.

Emission stages every file, replaces targets only after planning succeeds, and
rolls back prior bytes on failure. Rejection before emission leaves the project
unchanged. `--check` derives the full plan again and reports drift.

Generated files are exempt from review only while their hashes match
`.agentic/manifest.json`. Hand edits lose that exemption.
