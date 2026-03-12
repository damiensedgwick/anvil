# Adversarial Review Matrix

Match upstream review intensity:

- Medium with no red-risk files: run one reviewer.
- Large task or any red-risk file: run three reviewers in parallel.

Codex execution mapping:

- Use `spawn_agent` with Codex-supported roles.
- Use separate reviewer runs and distinct ledger check names for each verdict.

Suggested check names:
- Single reviewer: `review-gpt-agent`
- Three reviewers: `review-gpt-agent-1`, `review-gpt-agent-2`, `review-gpt-agent-3`

Review gates:

1. Stage changes before review (`git add -A`).
2. Record every reviewer verdict with `phase=review`.
3. If real issues are found, fix them, re-run affected verification, then re-run review.
4. Cap review iterations at two rounds.
