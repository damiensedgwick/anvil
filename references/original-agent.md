# Original Agent Source

Source of truth for behavior:
`https://raw.githubusercontent.com/burkeholland/anvil/refs/heads/main/agents/anvil.agent.md`

Porting rule:
- Prefer matching upstream behavior first.
- Apply Codex-specific substitutions only when upstream depends on unavailable tools.
- If this skill drifts, treat upstream as canonical and update this port map and references.

Codex substitutions currently required:
- Replace `ask_user` with direct user clarification in chat.
- Replace internal `session_store` SQL tooling with `scripts/anvil_ledger.py` and `.anvil/anvil.db`.
- Replace model-pinned reviewer agents with Codex subagents while keeping reviewer-count and review gates.
