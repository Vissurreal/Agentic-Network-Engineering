# Content-addressed review contract

Requests conform to `agentic.review-request/v1`; verdicts conform to
`agentic.review-verdict/v1`. Exact JSON Schemas are under `assets/schemas/`.

A request binds:

- task and round;
- producer and reviewer identities;
- original intent and executable acceptance criteria;
- ground-truth type, threshold, stop condition, and round cap;
- out-of-scope items;
- every reviewed path and SHA-256 digest;
- a canonical digest of the request.

A verdict binds the request digest, reviewer identity, disposition, findings,
clean checks, the exact checked file list and hashes, whether the stop condition
was met, and its own canonical digest.

Any subsequent file edit invalidates the verdict. The hook compares hashes, not
path substrings or free-form `PASS` text.

Local records under `.agentic/reviews/` are advisory because a workspace-write
agent can forge them. The hook still blocks stale, malformed, missing, or
failing local records, but documentation must not call that an independent
approval boundary.

An enforced gate requires an external authority endpoint outside the
workspace-write boundary. Verification fails closed when that authority is
absent or unreachable. The human override remains the parent-shell environment
variable `AGENTIC_SKIP_REVIEW=1`.

Mechanical findings require reproduction. Documentary findings require a
traceable primary source. Judgment-only review is advisory, single-round, and
unarbitrated.
