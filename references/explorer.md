# Explorer Prompt

Use this reference when spawning the Anvil survey subagent.

Spawn an `explorer` agent and give it:

- The task description
- The likely target area
- This repository boundary: stay inside the current working directory

Use these instructions in the prompt:

1. Find existing similar code by grepping for related names, patterns, routes, schema objects, and helper functions.
2. Map the blast radius by finding importing files and call sites for the modules being changed.
3. Identify available verification infrastructure for the target area.
4. Document surrounding conventions: naming, error handling, data flow, state handling, validation, and migration patterns.
5. Stay read-only. Do not suggest patches.

Require this output format:

```text
**Existing similar code**: [file:line] - [what it does] - [reuse potential: high/medium/low]
**Blast radius**: [list of importing files]
**Test infra**: [framework or "none"] - [relevant files/helpers]
**Patterns**: [key conventions observed]
**Recommendation**: Extend [X] vs write new - estimated [N] lines either way
```

Keep it concise and factual.
