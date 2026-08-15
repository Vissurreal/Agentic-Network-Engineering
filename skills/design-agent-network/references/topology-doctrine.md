# Topology doctrine

A graph encodes a prior about valid execution paths. It is useful when that
prior is correct and harmful when it is not.

Use a graph when the valid stages, handoffs, retry routes, and prohibited
deviations are known before execution. Represent revision and approval as
bounded cycles rather than pretending the graph is acyclic.

Use a harness when the path is emergent. Define a small state machine around
plan, act, observe, revise, and terminate. Every loop needs an explicit
termination condition, iteration cap, checkpoint policy, cancellation policy,
and recovery behavior.

Fan-out is independent of graph versus harness. Add it only when work can be
partitioned without duplicated context or conflicting writes. Runtime-sized
inputs require runtime fan-out bounded by explicit concurrency.

A2A is a transport choice, not a topology rank. Add it only when a remote role
removes a specific failure mode and its authentication, model access, tools,
request schema, response schema, continuation, timeout, and cancellation
behavior are verified.

Ground truth determines what a gate can claim. Mechanical evidence comes from
tests, compilers, schemas, or reproducible checks. Documentary evidence comes
from traceable primary sources. Judgment has no falsifying mechanism and
therefore supports advisory review only.

Consequence and reversibility modify evidence thresholds, isolation, human
gates, permissions, retries, and rollback. They do not determine agent count.

The marginal-cost test applies to every role and edge:

1. Name the concrete failure mode.
2. Explain why the existing roles cannot remove it.
3. Estimate the added coordination, context, latency, and reliability cost.
4. Add the structure only when the expected reduction in failure exceeds that
   cost.
