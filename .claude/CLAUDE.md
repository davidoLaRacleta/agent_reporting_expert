# Global Claude Code Instructions

## Working Style

- State assumptions before editing.
- If the task is ambiguous, ask one clarifying question.
- Turn each task into verifiable goals before coding.
- Prefer the smallest change that solves the problem.
- Touch only files needed for the requested change.
- Do not refactor unrelated code unless asked.
- Before finishing, verify with the narrowest relevant test.

## Context and Tool Use

- Narrow reads with deterministic CLI tools.
- Use `rg -n <pattern> <path>` for exact matches.
- Read only relevant symbols or line ranges.
- Review edits with `git diff -- <path>`.
- Prefer syntax-aware tools for bulk edits.
- Use `ast-grep` for structural rewrites.
- Use `fastmod` for safe string replacements.

## Python Defaults

- Use `uv` for dependency and environment commands.
- Use `logging` instead of `print()` for application code.
- Add type hints to public functions and return values.
- All exception paths should be handled explicitly.
- Ask before adding runtime dependencies.

## Code Quality

- Keep functions focused and small (< 50 lines if possible).
- Match the existing project style before introducing a new pattern.
- Remove imports, variables, or functions made unused by your own changes.
- Avoid speculative abstractions for single-use code.

## Communication

- Be concise.
- Call out trade-offs when multiple reasonable approaches exist.
- Push back if a safer or smaller approach would meet the goal.