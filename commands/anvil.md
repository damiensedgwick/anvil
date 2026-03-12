---
name: anvil
description: Run the Anvil evidence-first coding workflow on a task
---

Execute the following task using the full Anvil methodology:

$ARGUMENTS

Follow the Anvil Loop exactly as defined in the anvil agent instructions:

1. Boost the prompt into a precise spec (silent unless intent changed)
2. Check git hygiene (dirty state, branch)
3. Survey codebase for existing patterns and reuse opportunities
4. Plan the changes with risk classification
5. Capture baseline into .claude/anvil.db BEFORE any edits
6. Implement with minimal, surgical changes following existing patterns
7. Run the full verification cascade (build, typecheck, lint, test) — INSERT every result
8. Delegate adversarial review to anvil-reviewer subagent
9. Present the Evidence Bundle generated from SQL
10. Auto-commit with rollback command

Size the task (Small/Medium/Large) and adjust accordingly. Small tasks skip the ledger and review.
