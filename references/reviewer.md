# Reviewer Prompt

Use this reference when spawning the Anvil adversarial reviewer.

Spawn a `default` subagent after staging changes and give it:

- The task description
- The changed file list
- The instruction to review the staged diff first
- This repository boundary: stay inside the current working directory

Use these instructions in the prompt:

1. Run `git --no-pager diff --staged`. If nothing is staged, run `git --no-pager diff`.
2. Read each changed file in full, not just the diff.
3. Grep for usages of changed exports, routes, schema objects, and helper functions.
4. Look for real defects only:
   - bugs and logic errors
   - security problems
   - race conditions or concurrency issues
   - null, undefined, empty-state, and bounds edge cases
   - missing error handling
   - type-safety holes
   - breaking changes to existing consumers
   - behavior that violates nearby repository patterns
5. Ignore style, formatting, naming preferences, and pre-existing issues outside the diff.

Require this output format for each real issue:

```text
### [critical | major | minor] - Brief title
**File**: path/to/file.ts:lineNumber
**Bug**: What's wrong
**Impact**: Why it matters
**Fix**: Concrete fix
```

If there are no real issues, require:

```text
No issues found. Code looks correct.
```
