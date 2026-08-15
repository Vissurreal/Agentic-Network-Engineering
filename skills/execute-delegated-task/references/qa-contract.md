# Independent QA contract

QA evaluates the work; it does not defend the coordinator's conclusion.

For substantive work, give `task-reviewer` the inspectable draft, diff, or
artifact plus:

- the user's instructions and acceptance criteria;
- resolved sources and their provenance;
- task stakes and permission constraints;
- known tests, validators, or reproducible checks;
- known uncertainties and unexecuted checks.

The reviewer returns:

1. `verdict`: pass or revise;
2. findings ordered by consequence;
3. failed or missing source traces;
4. unmet acceptance criteria;
5. contradictions and unsupported claims;
6. the minimum corrective action;
7. checks performed and checks still unverified.

A failed source trace or acceptance criterion returns to evidence gathering or
implementation. The coordinator must correct material findings and rerun the
affected check before finalizing. Judgment-only review remains advisory.
