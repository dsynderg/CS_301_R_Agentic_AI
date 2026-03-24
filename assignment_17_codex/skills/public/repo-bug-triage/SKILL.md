---
name: repo-bug-triage
description: Identify likely bugs by scanning files in the current repository and produce a markdown task list with file paths and line numbers. Use when users report errors, ask why something isn't working, or request help finding bugs without running tests (e.g., "this isn't working why not", "here is an error, what is causing it", "there is a bug, help me find it").
---

# Repo Bug Triage

## Overview

Scan the current repository to find likely bugs and compile them into a markdown task list. Do not run tests; rely on static inspection and error context only.

## Workflow

1. Gather context
- If the user provides an error message or stack trace, extract file paths, function names, and line numbers to prioritize.
- If no error context exists, proceed with a broad scan of the repo.

2. Enumerate files (repo only)
- Use `rg --files` and skip common generated/vendor directories: `node_modules`, `dist`, `build`, `coverage`, `vendor`, `.git`.
- Keep scope to the current working directory only.

3. Inspect high-signal files
- Start with entry points (`index`, `main`, server/app bootstrap), routing, configuration, and files referenced by errors.
- Look for obvious correctness issues: undefined variables, incorrect imports, null/undefined usage, off-by-one loops, incorrect conditionals, missing returns, async/await misuse, unhandled promise rejections, resource leaks, incorrect API usage, or malformed data flow.

4. Record each likely bug as a task
- Include file path and 1-based line number. If line is approximate, note that explicitly.
- Provide a short justification and suggested fix.
- Assign `Severity` (Blocker/High/Medium/Low) and `Confidence` (High/Medium/Low).

5. Output only the task list
- Do not apply fixes unless the user explicitly asks to.

## Output Format

Write results to `BUG_TASKS.md` in the repo root. Use this template:

```markdown
# Bug Triage Tasks

## Summary
- Total: N
- Severity: Blocker X, High Y, Medium Z, Low W

## Tasks
### BUG-001
- File: `path/to/file.ext`
- Line: 123
- Severity: High
- Confidence: Medium
- Problem: One-sentence description of the likely bug.
- Evidence: Brief rationale referencing the code or error.
- Suggested fix: Short, concrete fix direction.
```

## Heuristics

- Prefer concrete evidence over speculation; avoid inventing issues without code cues.
- If an issue depends on runtime data you can’t see, mark `Confidence: Low`.
- If multiple bugs are related (cascade), still list individually with cross-references in `Evidence`.
