# Background agents

Run each ticket through its own background agent when several tickets are in
flight, so each ticket keeps its own context. The coordinator (this session)
keeps the user's approvals, and the agents do the ticket work.

| Piece | Rule |
|---|---|
| Agents | The coordinator runs bare-start tickets itself; one `jeeves:jaidev-ticket` agent per briefed ticket, started with the shared brief; a fresh `jeeves:jaidev-pr-reviewer` agent for each PR review round that changed code, started with the prompt in "Starting a PR reviewer". Model and effort come from the agent definition |
| Waiting | Ticket agents wait for the coordinator's wake-up. The coordinator learns of events from the watcher (see "Poll events") and wakes an agent with `SendMessage` |
| Shared brief | One file in the scratchpad, filled from `assets/agent-brief-template.md`; each agent reads it and its own ticket. The template is self-contained, so agents load only the skills their agent type names besides it |
| Phase 1: prepare | The agent reads the ticket and the code, settles the names with `jeeves:typescript-naming`, writes its briefing to a file, reports back and posts nothing |
| Phase 2: run | The coordinator sends "go" once the base is ready; the ticket agent posts the names comment and the briefing, answers questions and reviews the plan; the ticket agent reads CODEOWNERS and waits for the checks to settle; the coordinator then starts a fresh `jeeves:jaidev-pr-reviewer` on that head, which writes the draft review to the scratchpad; the ticket agent relays the draft for the user's approval, posts it, and runs Jaidev's revision rounds |
| State file | A JSON file in the scratchpad, one entry per ticket, created with `state init` (see "Poll events") |
| Events | Wake agents and update the state file as "Poll events" describes |
| Reports | Fetch origin and check any disputed or surprising claim in an agent's report against the latest parent branch yourself before you approve a scope |
| Approvals | The agent approves and merges a PR only when the user authorized both for that flow; otherwise it reports and the user decides. A pre-approval to merge a named set of PRs once CI passes covers only those PRs: after the agent reports a clean review and the head still matches, send the agent "merge" yourself; ask the user when a finding, a failed check or a moved head appears |
| Stop | A third failed revision round, a Blocked run, a rejected merge or a missing approval stops the agent, and it reports to the coordinator |
| Repo facts | Fill the brief template's "Repo facts" section from `references/repo-notes.md`; after each merge, append the agent's "Repo facts learned" to that file in the same turn (`references/write-back.md` at the plugin root) |
| Cleanup | After each merge, run `state set <state-file> <ticket> merged true`; the watcher prints `ALL MERGED` once every ticket is done, and exits |

### Color coding

Give every agent an identity color and every message a status circle. The identity palette has eight hues: 🟦 indigo, 🟧 amber, 🟪 violet, 🩵 teal, 🩷 rose, 🟫 brown, ⬜ slate, ⬛ ink. Take them in this order, so neighbours differ strongly.

1. When you spawn an agent, pick the next unused emoji from the palette and record it:

   ```bash
   cd "${CLAUDE_SKILL_DIR}/scripts" && python3 -m jaidev_watch state set <state-file> <ticket> color <emoji>
   ```
2. Start every message you relay about that agent or its ticket with the identity emoji and the ticket id. Tickets batched under one agent share its emoji.
3. Mark the status with one circle:

   | Circle | Status |
   |---|---|
   | 🟢 | progressing: Jaidev working, CI running, an agent running |
   | 🟡 | waiting for the user: a plan, briefing, decision or merge needs an answer |
   | 🔴 | blocked or failing: Blocked comment, failed check, third revision round, a stopped agent |
   | ⚪ | done or idle: merged, finished agent |

4. Print this legend as one line the first time the colors appear in a session, again whenever the user asks what a symbol means, and in every report that covers 3 or more agents:

   ```text
   🟦 🟧 🟪 🩵 🩷 🟫 ⬜ ⬛ = one agent each (its ticket) · 🟢 progressing · 🟡 waiting for you · 🔴 blocked or failing · ⚪ done or idle
   ```

The terminal draws these emoji in the emoji font's own colors, so the palette is fixed. In an HTML artifact or a document the skill produces, use the same hues as hex tokens: indigo #4F46E5, amber #F59E0B, violet #7C3AED, teal #14B8A6, rose #F43F5E, brown #92400E, slate #94A3B8, ink #0F172A.

Example line:

```text
🟦 ACC-1644 🟡 Plan v1 is ready for your review.
```

### Poll events

Name the session after the batch (`/rename`) when the wave starts. One
watcher follows the wave and reads Linear and GitHub only where the ticket's
stage expects an answer, so the coordinator wakes only for an event. Run every
command from the skill's `scripts` directory, with an absolute state-file path:

```bash
cd "${CLAUDE_SKILL_DIR}/scripts"
python3 -m jaidev_watch state init <state-file> <ticket> <agent-id> <repo-dir>
python3 -m jaidev_watch watch <state-file>
```

- Start `watch` in the background once the start comments are posted, and again after handling each exit.
- It ticks every 30 s and exits on the first tick with events, with exit code 0.
- It prints `IDLE` and exits with code 3 when no ticket has a check or a deadline left; every ticket then waits on you.
- It exits with code 4 on `TaskStop` (SIGTERM) or Ctrl-C, and prints nothing.
- It prints each tick's events before it saves the state, so an interrupted print repeats on the next run.
- `state init` on an existing ticket exits 2; add `--force` to replace it.
- One Linear read is one headless `claude -p --model haiku` call for every ticket due on that tick, $0.0057 and 7 to 10 s each (wave 2 usage log, 5 Nov 2026); its cost goes to `<state-file stem>.usage.log`.
- The Haiku call runs from `scripts/`, where the claude.ai Linear connector is set up, so run `watch` with its default `--tool` (`mcp__claude_ai_Linear__list_comments`) even when the session itself uses `mcp__linear__*`. A `LINEAR POLL ERROR` that says the call was refused means `--tool` names a server `scripts/` lacks (ACC-1642, 10 Nov 2026).
- GitHub reads (`gh pr list`, from the ticket's `repoDir`) cost nothing.
- `explain <state-file>` prints each ticket's stage, next checks and deadline; `due <state-file>` prints the checks due now. Both poll nothing.
- `--merge-watch` adds a 15-min GitHub check for merges made in the GitHub UI.

#### Stamp each post

The watcher's stage clock starts from your stamps. Stamp each post right after it goes up (`now` is the current time):

```bash
python3 -m jaidev_watch state set <state-file> <ticket> startedAt now
```

| After you post | Stamp | Also set |
|---|---|---|
| The `@jaidev start` comment | `startedAt` | `preEstimate` (Linear estimate), `namesBytes` (names comment size), `repoCount` when over 1 |
| Plan feedback, an answer to a question, or the `NO ACK` nudge | `feedbackAt` | `feedbackBytes` |
| `@jaidev plan:approved`, or `@jaidev resume` on a Blocked run | `approvedAt` | `estimate` (from the plan header "Estimate: N pts") |
| A GitHub review that asks for changes | `reviewAt` | `reviewComments` |
| The merge | `merged` = `true` | — |

#### Stages

| Stage | Linear | GitHub | Deadline → event |
|---|---|---|---|
| `starting` | +30 s; every 2 min while "Queued" | off | `NO START` at 2 min |
| `planning` | from `startedAt`: +2 min (1 pt), +3 min (2–3 pt), +4 min (5+); then every 1 min | off | `PLAN LATE` at 10 min, +1 min per 10 KB of names comment over 10 KB and per extra repo |
| `questions`, `plan-ready`, `blocked` | off | off | the `STATUS` line on entry |
| `plan-feedback` | +30 s; after the ack, +1 min then every 30 s | off | `NO ACK` at 1 min; after the ack, `PLAN LATE` at 4 min +1 min per 5 KB of feedback |
| `approved` | +30 s | off | `NO START` at 1 min |
| `implementing` | every 3 min from PR due | from PR due: every 1 min, every 2 min after 2× PR due | `PR LATE` at 3× PR due, +1× per attempt after the first, and only after 5 min without a status-comment update |
| `pr-ci` | off | the repo's `First check`, then its `Interval` | `CI LATE` at 1.5× the repo's `Max` |
| `pr-ready` | off | off, or every 15 min with `--merge-watch` | none |
| `pr-review-sent` | +30 s, then every 1 min | off | `NO ACK` at 2 min |
| `pr-revising` | every 3 min | every 1 min until a new head | `FIX LATE` at 2 min +1 min per review comment, capped at 10 min, and only after 5 min without a status-comment update |

- A head that settles with a failed check outside the repo's `Known failures` enters `pr-revising`: Jaidev fixes CI and SonarCloud failures on its own.
- PR due after `plan:approved`: 4 min for 1 or 2 points, 6 min for 3, 8 min for 5 or more.
- CI cadence comes from `~/.claude/org-memory/jeevesinc/ci-check-timing.md` (`$JEEVES_CI_TIMING` overrides the path); a new head restarts the CI clock. The repo is the one `git remote get-url origin` names in the ticket's `repoDir`.
- A repo without a row gets one derived the git-preferences way when its first ticket reaches a CI stage; the watcher adds it to that table, creating the file on its first row, and prints `CI ROW ADDED <repo>`.
- CI counts as settled once every check completed and every `Settles on` check is present.
- While Jaidev's timeline shows "Queued" or "API provider overloaded — retrying", every deadline pauses.
- A deadline fires after one last read at the deadline, once per stage.
- After a Linear deadline (`NO START`, `PLAN LATE`, `NO ACK`), the ticket idles: no more Linear reads until you act on the event and stamp again. GitHub reads go on after `PR LATE`, `CI LATE` and `FIX LATE`.
- In `starting`, a first read that shows the previous run's status comment (anything but Queued, Analyzing, Planning, Gathering Info, Blocked or a "Started by" entry) is kept as the baseline; the stage moves on the next change.
- A failed read waits 2 min before its retry.
- The numbers live in `scripts/jaidev_watch/policy.py`. Move a stage to measured values once `jaidev-run-timings.md` holds 3 runs of it.

#### Event lines

| Line | Action |
|---|---|
| `<ticket> STATUS "Awaiting Plan Approval"` or a plan in `TIMELINE` | Wake the ticket's agent to review the plan |
| `<ticket> STATUS "Gathering Info…"` or `"Blocked…"` | Wake the ticket's agent |
| `<ticket> STATUS` for any other change | Update the progress; it is no agent event |
| `<ticket> CI passed #<n> head=<sha>`, with `(known: <checks>)` when known failures ran | Start the PR review on that head |
| `<ticket> CI failed #<n> head=<sha>` | Read `gh pr checks`; Jaidev starts a revision on its own, and the ticket waits in `pr-revising` |
| `<ticket> MERGED #<n>`, `<ticket> CLOSED unmerged #<n>` | Tell the user |
| `<ticket> NO ACK stage=plan-feedback …` | Post `@jaidev please revise the plan per the feedback reply above` in the same thread, after the user's OK; stamp `feedbackAt` |
| `<ticket> NO ACK stage=pr-review-sent …` | Check the PR's review threads and Jaidev's status comment; tell the user |
| `<ticket> NO START …` | Read the status comment with `limit: 1`; check the trigger against `references/jaidev-reference.md` §3 and tell the user |
| `<ticket> PLAN LATE …`, `PR LATE …`, `FIX LATE …` | Read the status comment with `limit: 1` and tell the user what it shows |
| `<ticket> CI LATE …` | Read the PR's checks with `gh pr view`; tell the user which check is stuck |
| `LINEAR POLL ERROR …`, `GITHUB POLL ERROR <ticket> …` | Restart the watcher once; when it fails again, read the status comment with `limit: 1` and tell the user |
| `LINEAR POLL ERROR <ticket> missing from the reply` | Restart the watcher; the ticket counts as unread, so no deadline fires from it |
| `CI ROW ADDED <repo> …` | Tell the user the repo's new `ci-check-timing.md` row; when the file was just created, index it in `~/.claude/org-memory/jeevesinc/MEMORY.md`; restart the watcher |
| `CI ROW MISSING <repo> <reason>` | That ticket's CI polling stays off; derive the row with git-preferences' `references/pr-pollers.md` → "Checks poller", add it, and restart the watcher. The watcher retries the derivation 2 min after a failure (`<state-file stem>.ci-hold.json`) |
| `IDLE` | Every ticket waits on you; restart the watcher after your next stamp |
| `ALL MERGED` | The wave is done; leave the watcher stopped |

Wake an agent only for:
- a first question, a plan, or a Blocked comment;
- CI finished on a PR head (the ticket agent reports the settled head, and
  you start a fresh `jeeves:jaidev-pr-reviewer` on it);
- a merge.

Send the ticket's agent one `SendMessage` naming every pending event. Status
and progress changes on their own are no event. Approve and merge only after
the user's "merge", or a pre-approval naming that PR.

#### Agent tools

Linear tools may be `mcp__claude_ai_Linear__*` or `mcp__linear__*`. Tell each agent which server is connected when you spawn it.

### Starting a PR reviewer

Start a fresh `jeeves:jaidev-pr-reviewer` for each review round once the
ticket agent reports the settled head. Fill this prompt; the agent's "Inputs"
list names each field. Point the checklist at `references/pr-review.md`, read per `references/write-back.md` at the plugin root:

```text
Review Jaidev PR <org/repo>#<n> for <ticket-id>, review round <N>.
- Head SHA: <sha the ticket agent reported>
- Repo checkout: <main checkout; run gh from inside it>
- Briefing: <scratchpad>/<ticket-id>-briefing.md
- Names comment: <scratchpad>/<ticket-id>-names-comment.md
- Plan feedback: <scratchpad>/<ticket-id>-plan-feedback.md, or "none"
- Design doc: <URL>, or "none"
- Checklist: <absolute path of skills/jaidev/references/pr-review.md>
- Tests: rely on the CI result when it is green, and review by reading the code.
- Linear server: <mcp__claude_ai_Linear__* or mcp__linear__*>
- Scratchpad: <directory>; write <ticket-id>-review-r<N>.md there.
```

### Preparing the next ticket

When the tickets form a chain, the next unblocked ticket gets its briefing ready while the current PR waits.

- Start one Phase 1 agent for the next ticket as soon as the current PR is in review or CI.
- Point the agent at the unmerged code on the PR's branch, and at the PR's briefing and names comment.
- Run the agents the batch needs; two to five ran together without trouble, and an idle agent costs nothing until woken.
- Send "go" after the blocking PR merges.

### Reuse or spawn

A resumed agent re-reads its whole context on every turn, so a long-lived agent taxes every later message. Spawn a fresh agent per ticket and carry knowledge in `references/repo-notes.md`. Reuse a finished agent (`SendMessage` with the next ticket) only when all hold:
- its completion notice shows under about 50k tokens of context;
- the next ticket edits the same files or tests;
- the previous ticket is merged, so nothing runs in parallel;
- the agent re-fetches origin and treats its earlier notes as unverified.

#### Batch small tickets

Up to 3 one-point tickets with disjoint files may share one agent:
- Phase 1 writes each ticket's files in one pass.
- The coordinator sends "go <ticket-id>" per ticket.
- PR reviews run one after another.

Such an agent reached about 220k tokens of context, so 3 is the cap.

### Agent run endings

An agent ends each run with "I cannot wait for wake-ups, resume me via SendMessage". That is expected; resume it by message.
