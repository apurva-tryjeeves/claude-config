# Background agents

Run each ticket through its own background agent when several tickets are in
flight, so each ticket keeps its own context. The coordinator (this session)
keeps the user's approvals, and the agents do the ticket work.

| Piece | Rule |
|---|---|
| Agents | One background agent per ticket, started with the shared brief and an explicit tier: Phase 1 prepare `model: sonnet`, `effort: medium`; Phase 2 run `model: sonnet`, `effort: high` |
| Waiting | Ticket agents wait for the coordinator's wake-up. The coordinator learns of events from the watcher (see "Poll events") and wakes an agent with `SendMessage` |
| Shared brief | One file in the scratchpad, filled from `assets/agent-brief-template.md`; each agent reads it and its own ticket. The template is self-contained, so agents load only `jeeves:typescript-naming` besides it |
| Phase 1: prepare | The agent reads the ticket and the code, settles the names with `jeeves:typescript-naming`, writes its briefing to a file, reports back and posts nothing |
| Phase 2: run | The coordinator sends "go" once the base is ready; the agent posts the briefing, answers questions, reviews the plan and the PR |
| State file | A JSON file in the scratchpad, one entry per ticket, created with `scripts/poll-state.py <state-file> init <ticket> <agent-id> <repo-dir>` |
| Events | Wake agents and update the state file as "Poll events" describes |
| Reports | Fetch origin and check any disputed or surprising claim in an agent's report against the latest parent branch yourself before you approve a scope |
| Approvals | The agent approves and merges a PR only when the user authorized both for that flow; otherwise it reports and the user decides. A pre-approval to merge a named set of PRs once CI passes covers only those PRs: after the agent reports a clean review and the head still matches, send the agent "merge" yourself; ask the user when a finding, a failed check or a moved head appears |
| Stop | A third failed revision round, a Blocked run, a rejected merge or a missing approval stops the agent, and it reports to the coordinator |
| Repo facts | Fill the brief template's "Repo facts" section from `references/repo-notes.md`; after each merge, append the agent's "Repo facts learned" to that file in the same turn |
| Cleanup | `poll.py` marks merged tickets and prints `ALL MERGED` at the end, and the watcher exits |

### Color coding

Give every agent an identity color and every message a status circle. The identity palette has eight hues: 🟦 indigo, 🟧 amber, 🟪 violet, 🩵 teal, 🩷 rose, 🟫 brown, ⬜ slate, ⬛ ink. Take them in this order, so neighbours differ strongly.

1. When you spawn an agent, pick the next unused emoji from the palette and record it:

   ```bash
   scripts/poll-state.py <state-file> set <ticket> color <emoji>
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

Name the session after the batch (`/rename`) when the wave starts. One shell
script watches the wave, so the coordinator wakes only when an event arrives.
Start it in the background from the scratchpad once the start comments are
posted, and start it again after handling each exit:

```bash
<skill-dir>/scripts/watch.sh <state-file>
```

| Every | It runs | Which prints |
|---|---|---|
| 5 min | `scripts/poll-linear.py`: one headless `claude -p --model haiku` call that reads each open ticket's Jaidev status comment | A Status or Timeline change that waits on the coordinator: a plan, a question, Blocked, PRs created, Complete |
| 3 min | `scripts/poll.py`: every GitHub check in one call | PR opened, CI finished on a new head, merged, closed |

The watcher exits on the first line printed. Headless Haiku runs as its own
process, so no agent of this session stops or wakes; a background agent that
paces itself instead wakes the coordinator on every pause. One Linear call
costs about $0.007 and takes about 10 s (measured 4 Nov 2026). Changes while
Jaidev works (Analyzing, Planning, Implementing, Addressing PR Feedback) and
Timeline entries the coordinator caused update the state file silently.

| Line | Action |
|---|---|
| `<ticket> STATUS "Awaiting Plan Approval"` or a plan in `TIMELINE` | Wake the ticket's agent to review the plan |
| `<ticket> STATUS "Gathering Info…"` or `"Blocked…"` | Wake the ticket's agent |
| `<ticket> STATUS` for any other change | Update the progress; it is no agent event |
| `<ticket> PR opened`, `CI …`, `MERGED`, `CLOSED` | From `poll.py`; wake the agent for CI finished and a merge, tell the user about MERGED and CLOSED |
| `LINEAR POLL ERROR …` | Run `scripts/poll-linear.py <state-file>` once by hand; when it fails again, read the status comments with `limit: 1` and tell the user |
| `ALL MERGED` | The wave is done; leave the watcher stopped |

Wake an agent only for:
- a first question, a plan, or a Blocked comment;
- CI finished on a PR head (the agent reviews the diff and the CI result
  together);
- a merge.

Send the ticket's agent one `SendMessage` naming every pending event. Status
and progress changes on their own are no event. Approve and merge only after
the user's "merge", or a pre-approval naming that PR.

#### Agent tools

Linear tools may be `mcp__claude_ai_Linear__*` or `mcp__linear__*`. Tell each agent which server is connected when you spawn it.

### Preparing the next ticket

When the tickets form a chain, the next unblocked ticket gets its briefing ready while the current PR waits.

- Start one Phase 1 agent for the next ticket as soon as the current PR is in review or CI.
- Point the agent at the unmerged code on the PR's branch, and at the PR's briefing and names reply.
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
- Phase 1 writes the two files per ticket in one pass.
- The coordinator sends "go <ticket-id>" per ticket.
- PR reviews run one after another.

Such an agent reached about 220k tokens of context, so 3 is the cap.

### Agent run endings

An agent ends each run with "I cannot wait for wake-ups, resume me via SendMessage". That is expected; resume it by message.

authoring-guide: v4
