# Task routing

Choose roles from task shape, not from a perceived complexity tier.

## Research, analysis, and writing

Dispatch `task-researcher` to retrieve evidence and provenance. Partition by
source family or question when parallel retrieval avoids duplication. The
coordinator owns synthesis and the destination artifact. Dispatch
`task-reviewer` after the draft exists when the task is multi-source,
high-stakes, or writes a durable artifact.

Research workers return claims, direct source locations, dates, short
supporting excerpts, unresolved conflicts, and confidence limits. They do not
write conclusions into the final destination. Prefer primary and current
sources; label inference and unsupported claims.

## Code, configuration, and technical changes

Dispatch `task-implementer` for one bounded component or a read-only diagnosis.
Give only one agent ownership of any file. The coordinator integrates shared
surfaces and runs the primary verification. Dispatch `task-reviewer` against
the resulting diff, tests, acceptance criteria, and regression risks.

## Documents, data, and operational work

Use a researcher for source extraction, an implementer for a non-overlapping
artifact component, or a reviewer for formula, citation, layout, or policy
verification. The coordinator retains external writes, publication, sending,
deletion, and irreversible actions unless the user explicitly delegated them.

## Default

For an unfamiliar substantive task, dispatch one read-only general worker to
identify the strongest execution route and return evidence or a bounded draft.
Do not ask a worker merely to restate the prompt or propose generic steps.

## Worker brief

Every brief states:

1. the user outcome and the worker's specific contribution;
2. in-scope and out-of-scope material;
3. allowed tools and whether writes are prohibited;
4. required evidence or tests;
5. the exact return structure;
6. the termination condition.
