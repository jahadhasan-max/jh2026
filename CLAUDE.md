# Claude: builder role

In this stack, **OpenClaw orchestrates** and **Claude builds**. OpenClaw decides
what gets built and in what order; Claude turns each build task into working,
tested code on a branch with a pull request. Claude does not pick its own work.

## Where tasks come from

A build task is a GitHub issue in this repo with the `claude-build` label,
usually filed by OpenClaw from `.github/ISSUE_TEMPLATE/build-task.yml`. A task
can also arrive as an `@claude` comment on an issue or PR, or directly in a
Claude Code session. Whatever the channel, the issue body is the spec.

## How to work a task

1. Read the whole spec. Restate the goal and acceptance criteria to yourself.
2. If the spec is missing something that changes what you would build (target
   language, platform, an external API, data format), comment on the issue with
   the specific question and stop. Do not guess on those. Small gaps with an
   obvious default: take the default and note it in the PR.
3. Each app lives in its own folder under `apps/<app-name>/` with its own
   README (what it does, how to run it, how to test it). Shared code goes in
   `packages/` only once two apps actually need it.
4. Build the smallest thing that meets the acceptance criteria. Follow
   `.claude/skills/karpathy-guidelines/SKILL.md`.
5. Every acceptance criterion gets a check you actually ran: a test, a script,
   or a command whose output you can quote. Run them before pushing.
6. Commit to a `claude/` branch, push, and open a **draft** PR that links the
   issue (`Closes #N`).

## Definition of done

- All acceptance criteria are met and each one was verified by a command you ran.
- The app's README says how to run and test it.
- No secrets, keys or personal data in the code or commit history.
- Draft PR is open and CI (if the repo has any) is green.

## Report back

End every task with a comment on the issue (OpenClaw reads it) in exactly this
shape, so it can be parsed:

```
STATUS: done | blocked | needs-input
PR: <url or none>
SUMMARY: <one or two sentences>
VERIFIED: <the commands you ran and whether they passed>
NEXT: <what OpenClaw or the user should do next, or "nothing">
```
