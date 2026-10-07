# OpenClaw → Claude handoff

OpenClaw plans; Claude builds. The handoff is a GitHub issue, and the reply is
a draft PR plus a status comment. Everything goes through this repo, so every
task has a written spec, a branch, and a reviewable diff.

```
OpenClaw ──(gh issue create, label claude-build)──▶ GitHub issue
                                                       │
                                     claude-builder.yml workflow runs Claude
                                                       │
OpenClaw ◀──(reads STATUS comment / PR)──── draft PR + STATUS comment on issue
```

## One-time setup

1. Install the Claude GitHub App on this repo:
   https://github.com/apps/claude
2. In a terminal with Claude Code, run `claude setup-token` and save the token
   as the repo secret `CLAUDE_CODE_OAUTH_TOKEN`
   (Settings → Secrets and variables → Actions). Or use an Anthropic API key as
   `ANTHROPIC_API_KEY` and swap the line in `.github/workflows/claude-builder.yml`.
3. Create the label once: `gh label create claude-build --color 5319e7`.
4. Give OpenClaw a GitHub token that can create issues in this repo. If that
   token belongs to a bot account rather than you, add the bot's login to
   `allowed_bots` in the workflow.

## Dispatching a task (what OpenClaw runs)

```sh
gh issue create --repo jahadhasan-max/jh2026 \
  --label claude-build \
  --title "[build] invoice-parser: extract totals from PDF invoices" \
  --body "$(cat <<'SPEC'
### App name
invoice-parser

### Goal
CLI that reads a PDF invoice and prints vendor, date and total as JSON.

### Acceptance criteria
- `python -m invoice_parser samples/a.pdf` prints {"vendor","date","total"}
- `pytest` passes

### Stack and constraints
Python 3.12, no paid APIs.
SPEC
)"
```

The section headings match the issue form, so issues filed by hand and by
OpenClaw look the same to Claude.

## Reading the result

Claude ends each task with a comment on the issue:

```
STATUS: done | blocked | needs-input
PR: <url or none>
SUMMARY: ...
VERIFIED: ...
NEXT: ...
```

OpenClaw can poll for it with
`gh issue view <N> --repo jahadhasan-max/jh2026 --comments --json comments`
and branch on the `STATUS:` line. On `needs-input`, answer by commenting on the
issue with `@claude` and the answer; that re-runs Claude on the same task.

## Follow-ups

- Change requests on a PR: comment `@claude <what to change>` on the PR.
- Merging stays with you (or OpenClaw, if you give it that permission).
