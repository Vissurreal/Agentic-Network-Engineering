# Structural patterns derived from the decision vector

These patterns are priors, not ranks. Do not call them tiers and do not choose
one from perceived difficulty.

## Deterministic rubric

1. Select `direct` when delegation or independent review removes no failure
   mode worth its coordination cost.
2. Select a `graph` when the valid path and prohibited deviations are known or
   partially known.
3. Select an `adaptive-harness` when the path is emergent. Define loop state,
   termination, iteration cap, checkpoints, and recovery.
4. Add fan-out only when workstreams are independent or can be partitioned
   without duplicated context.
5. Add a supervisor only when runtime evidence must reallocate workstreams.
6. Add review when mechanical or documentary evidence can falsify the work.
   Judgment-only review is explicitly advisory.
7. Add arbitration only when the declared evidence can decide disagreement.
8. Add A2A only when a remote role removes a cross-vendor or context-isolation
   failure mode and model plus transport access are verified.

## Pattern library

`direct` has no generated role. Project guidance and commands are sufficient.

`pipeline` uses a known staged path. Typical roles are an intent-holding lead,
one producer, and an independent reviewer.

`fan-out` partitions independent work and joins results under a bounded
aggregator. Width may be fixed or runtime-determined.

`supervised-portfolio` adds a supervisor only because parallel workstreams need
runtime reassignment or cancellation.

`adaptive-harness` defines a planner-act-observe-revise loop for emergent work.
Static edges must not pretend to know the runtime path.

`custom` is permitted only with a non-empty deviation rationale that identifies
the failure mode no listed pattern removes.

Consequences and reversibility modify human gates, isolation, evidence,
permissions, and retries. They do not increase role count by themselves.
