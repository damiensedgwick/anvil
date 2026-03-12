# Original To Codex Port Map

This skill mirrors the upstream Anvil agent and adapts only runtime/tooling differences required by Codex.

Upstream source of truth:
`https://raw.githubusercontent.com/burkeholland/anvil/refs/heads/main/agents/anvil.agent.md`

| Original artifact/functionality | Codex port | Notes |
| --- | --- | --- |
| `agents/anvil.agent.md` | `SKILL.md` + [references/original-agent.md](references/original-agent.md) | Use upstream agent as primary behavioral reference |
| Explorer survey instructions | [references/explorer.md](references/explorer.md) + `spawn_agent(agent_type="explorer")` | Same survey loop; mapped to Codex explorer role |
| Adversarial review loop (1 or 3 reviewers) | [references/reviewer.md](references/reviewer.md) + [references/review-matrix.md](references/review-matrix.md) | Preserves reviewer-count behavior; uses Codex-supported agent roles |
| Dynamic verification cascade | [references/verification.md](references/verification.md) | Detect commands from repo files instead of project-specific hardcoding |
| SQL verification ledger | `.anvil/anvil.db` via `scripts/anvil_ledger.py` | Keeps SQL evidence model with deterministic helper commands |
| Model-specific reviewer pins | Codex subagent execution with equivalent count/flow | Preserve process semantics even when exact model pins differ |

## Intentional Adaptations

- Keep the workflow source-linked to upstream Anvil instead of a one-time static translation.
- Remove repository-specific command maps so the skill is copy/paste portable between projects.
- Preserve the ledger-evidence loop while using local helper scripts for deterministic DB writes and reporting.
- Preserve review intensity (single reviewer for Medium; three for Large/red) using available Codex agents.
