# Model and runtime assignment

Assign models from the role's reasoning demand, evidence volume, and runtime
capabilities. Record the resolved model and effort in the approved
specification.

Retrieval-only scouting uses native Haiku. Intent retention, decomposition, and
evidence-resolvable arbitration use Fable or Opus at high effort. Artifact
production uses the strongest verified native model justified by the task.

Cross-vendor review uses a logical OpenAI role only after the probe verifies:

- Codex installation;
- current authentication through `codex login status`;
- MCP advertisement of `codex` and `codex-reply`;
- access to the selected GPT model through an explicitly authorized bounded
  live check.

The compiler renders that logical role as a native Claude dispatcher. The
dispatcher uses a valid Claude model and explicitly receives
`mcp__codex__codex` and `mcp__codex__codex-reply`. It passes the GPT model as an
MCP argument and retains the returned thread identifier.

When any remote capability is unverified, choose a distinct native reviewer and
record the degradation. Do not emit a broken remote role or describe
configuration-file existence as authentication.
