---
name: anvil
description: Evidence-first coding workflow for verified code changes. Use when the user explicitly asks for Anvil, wants a cautious end-to-end implementation loop, asks for baseline/after/review proof in a SQLite ledger, or wants surgical edits with adversarial review, an evidence bundle, and rollback guidance.
---

# Anvil

Use this skill to run the Anvil workflow inside Codex. It stays as close as possible to the original Anvil agent while adapting only Codex-incompatible mechanics.

## Load Order

1. Read `AGENTS.md`.
2. Read [references/original-agent.md](references/original-agent.md) for the upstream source and mirroring rules.
3. Read [references/port-map.md](references/port-map.md) only when you need to confirm how upstream artifacts map to this Codex port.
4. Read [references/verification.md](references/verification.md) for dynamic verification command discovery.
5. Read [references/review-matrix.md](references/review-matrix.md) before running adversarial review.
6. Use [scripts/anvil_ledger.py](scripts/anvil_ledger.py) for every ledger write or query. Do not hand-edit SQLite rows.
7. When the task touches a Codex skill, use [scripts/validate_skill.py](scripts/validate_skill.py) as the local validator before relying on any external validator tooling.

## Core Rules

- Stay inside the current project root.
- Reuse existing code before introducing new abstractions.
- Do not present broken code. Verification is tool output, not assertion.
- For Medium and Large tasks, do not skip baseline capture, post-change verification, or review logging.
- If a verification tier is infeasible, record that explicitly in the ledger instead of silently skipping it.
- When you are stuck after two attempts, explain what failed and ask for help instead of spinning.
- Use the active `gpt-codex` model and Codex subagents. Do not assume Claude model pins or Context7 exist.

## Task Sizing

- Small: typo, copy tweak, one-liner, or isolated mechanical edit. Run diagnostics plus build. Skip ledger and review.
- Medium: most bug fixes, UI changes, feature work, or local refactors. Run the full loop with ledger and one reviewer.
- Large: cross-cutting changes, schema changes, auth/payments, concurrency, public API changes, or any task with a red-risk file. Show the plan and wait for confirmation before implementing.

## Risk Bands

- Green: additive files, tests, docs, or local config.
- Yellow: business logic, UI state, queries, signatures, or data transforms.
- Red: auth, payments, schema/migration work, destructive data changes, concurrency, public API changes.

Any red-risk file makes the task Large.

## Pushback

Before executing, evaluate the request itself. If the user is aiming at the wrong fix, adding unnecessary complexity, or introducing dangerous edge cases, stop and say:

`⚠️ Anvil pushback: [concern]`

Then ask the user to choose one of these exact options:

- `Proceed as requested`
- `Do it your way`
- `Let me rethink`

Do not implement until they answer.

## Ledger Setup

For Medium and Large tasks, initialize the ledger before edits:

```bash
python3 .agents/skills/anvil/scripts/anvil_ledger.py init
task_id="$(python3 .agents/skills/anvil/scripts/anvil_ledger.py task-id --text "$SPEC")"
```

- Default DB path: `.anvil/anvil.db`
- `init` recreates the repo-local `.anvil/` directory automatically when it is missing.
- Schema: identical to the Claude version
- Override path with `--db <path>` only when the user asks

Use these commands to interact with the ledger:

```bash
python3 .agents/skills/anvil/scripts/anvil_ledger.py run --task-id "$task_id" --phase baseline --check-name build --command "npm run build"
python3 .agents/skills/anvil/scripts/validate_skill.py .agents/skills/anvil
python3 .agents/skills/anvil/scripts/anvil_ledger.py record --task-id "$task_id" --phase review --check-name review-gpt-agent --tool agent --command "spawn_agent default reviewer" --exit-code 0 --passed 1 --output "$REVIEW_TEXT"
python3 .agents/skills/anvil/scripts/anvil_ledger.py record --task-id "$task_id" --phase after --check-name manual-smoke --tool manual --command "feature smoke check" --exit-code 0 --passed 1 --output "Exercised the changed path and confirmed expected behavior."
python3 .agents/skills/anvil/scripts/anvil_ledger.py count --task-id "$task_id" --phase after --passed-only
python3 .agents/skills/anvil/scripts/anvil_ledger.py bundle --task-id "$task_id"
```

## The Anvil Loop

### 0. Boost

Rewrite the request into a precise spec. Infer target files and implied constraints. Stay silent unless the intent materially changes, then show:

`📐 Boosted prompt: [spec]`

### 0b. Git Hygiene

1. Run `git status --porcelain`.
2. If dirty, warn and ask whether to commit, stash, or ignore.
3. Run `git rev-parse --abbrev-ref HEAD`.
4. If the branch is `main` or `master` for a Medium or Large task, warn and offer an `anvil/{task_id}` branch.

### 1. Understand

Parse the goal, acceptance criteria, and assumptions. Ask only if the ambiguity is material.

### 2. Survey

For Medium and Large tasks:

1. Read [references/explorer.md](references/explorer.md).
2. Spawn an `explorer` subagent with the task description and target area.
3. Continue local work while it runs. Wait only when the findings block the next step.
4. If reusable code is found, surface only the useful conclusion:

`🔍 Found existing code: [file] already handles [X]. Recommending extension.`

### 3. Plan

- Medium: plan silently.
- Large: show the plan with files and risk levels, then wait for confirmation before editing.

### 3b. Baseline Capture

Medium and Large tasks must have baseline rows before edits.

1. Initialize the ledger.
2. Record baseline checks with `phase=baseline`.
3. Capture at minimum:
   - build
   - file-level diagnostics for the target files
   - changed-file lint or typecheck
   - tests when real tests exist
4. If a baseline check is expected to fail and should not block progress, still run it and append `|| true` so the row exists.
5. If the task changes a Codex skill, include the local validator in baseline and after checks.

Discover commands from the repository itself. Use [references/verification.md](references/verification.md) and record what you ran. Examples:

```bash
python3 .agents/skills/anvil/scripts/anvil_ledger.py run --task-id "$task_id" --phase baseline --check-name build --command "npm run build" || true
python3 .agents/skills/anvil/scripts/anvil_ledger.py run --task-id "$task_id" --phase baseline --check-name typecheck --command "npm run typecheck" || true
python3 .agents/skills/anvil/scripts/anvil_ledger.py run --task-id "$task_id" --phase baseline --check-name lint-changed --command "npm run lint -- src/example.ts" || true
python3 .agents/skills/anvil/scripts/anvil_ledger.py run --task-id "$task_id" --phase baseline --check-name skill-validate --command "python3 .agents/skills/anvil/scripts/validate_skill.py .agents/skills/anvil" || true
```

If baseline is already broken, note it and continue. Do not make it worse.

### 4. Implement

- Read neighboring code first.
- Follow local patterns.
- Prefer extending existing abstractions.
- Add tests alongside the change when real test infrastructure exists.
- Keep changes minimal and surgical.

### 5. Verify

Insert every result with `phase=after`.

#### 5a. Diagnostics

Make every changed file parse and compile. Fix immediately if it does not.

#### 5b. Verification Cascade

Run every applicable tier. Do not stop at the first pass or first failure.

Tier 1, always:

1. Syntax or parse confidence for every changed file
2. File-level diagnostics

Tier 2, detect from the repository:

3. Build
4. Type check
5. Lint on changed files
6. Tests when real tests exist
7. For Codex skill changes, run the local skill validator

Tier 3, required when Tiers 1 and 2 provide no runtime signal:

8. Import or load test
9. Smoke execution, or a manual verification note when the change can only be exercised through the app

If Tier 3 is infeasible, insert `check_name=tier3-infeasible` with the reason.

If any post-change check fails:

1. Fix the issue.
2. Re-run the failed check.
3. Re-run any dependent checks.
4. Stop after two failed repair attempts and ask for help rather than spinning.

Minimum successful `after` signals:

- Medium: 2
- Large: 3

### 5c. Adversarial Review

Medium and Large tasks require review rows before presentation.

1. Stage changes with `git add -A`.
2. Read [references/reviewer.md](references/reviewer.md).
3. Apply [references/review-matrix.md](references/review-matrix.md):
   - Medium (no red files): run one reviewer.
   - Large or red-risk: run three reviewers in parallel.
4. Record each verdict in the ledger with `phase=review` using distinct check names.

Reviewer output is evidence, not decoration. If it finds real issues:

1. Fix them.
2. Re-run the affected verification checks.
3. Re-run review.
4. Cap at two review rounds.
5. If issues remain after round two, record the open findings and lower confidence to Low.

If subagents are unavailable, run the same checklist locally and record `check_name=review-local`.

### 6. Evidence Bundle

Before presenting:

```bash
python3 .agents/skills/anvil/scripts/anvil_ledger.py count --task-id "$task_id" --phase after --passed-only
python3 .agents/skills/anvil/scripts/anvil_ledger.py bundle --task-id "$task_id"
```

Do not present until the count meets the minimum signal threshold for task size.

Present:

1. Task id, size, and highest risk
2. SQL-backed baseline table
3. SQL-backed verification table
4. Regressions section
5. Adversarial review section
6. Files changed, blast radius, confidence, and rollback command

Confidence:

- High: all checks pass, reviewer is clean or only found issues you fixed
- Medium: verification is mostly good but runtime coverage is partial
- Low: a check remains unresolved, a reviewer issue remains open, or the path is materially unverifiable

### 7. Present

Keep output tight. Show only the items that matter:

1. Pushback, if any
2. Boosted prompt, if intent changed
3. Reuse signal, if present
4. Plan, for Large tasks only
5. Change summary
6. Evidence bundle, for Medium and Large tasks

For Small tasks, show the change and the verification result, then stop.

### 8. Commit

For Medium and Large tasks invoked through Anvil, preserve the original auto-commit behavior unless the user explicitly says not to commit.

1. Run `git rev-parse HEAD` and keep the pre-commit SHA.
2. Stage all changes.
3. Create a concise imperative commit message.
4. Commit.
5. Tell the user the branch, commit message, and rollback command:

`git revert HEAD`

For Small tasks, ask whether they want a commit.
