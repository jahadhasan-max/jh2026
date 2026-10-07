# jh2026

Build workspace where OpenClaw orchestrates and Claude does the coding.

- `CLAUDE.md`: Claude's builder role, definition of done, and report-back format
- `docs/openclaw-handoff.md`: how OpenClaw files a task and reads the result
- `.github/ISSUE_TEMPLATE/build-task.yml`: the task spec form
- `.github/workflows/claude-builder.yml`: runs Claude on `claude-build` issues and `@claude` mentions
- `apps/`: one folder per app Claude builds (created with the first task)
