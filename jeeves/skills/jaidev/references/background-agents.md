# Background agents

Run each ticket through its own background agent when several tickets are in
flight, so each ticket keeps its own context. The coordinator (this session)
keeps the user's approvals, and the agents do the ticket work.

| Piece | Rule |
|---|---|
| Agents | One background agent per ticket, started with the shared brief and an explicit tier: Phase 1 prepare `model: sonnet`, `effort: medium`; Phase 2 run `model: sonnet`, `effort: high` |
| Waiting | Agents wait for the coordinator's wake-up, because their sandbox blocks `sleep`. The coordinator learns of events from two watchers (see "Poll events") and wakes an agent with `SendMessage` |
| Shared brief | One file in the scratchpad with the context, the briefing format, the plan-review checks, the stop conditions and the report format; each agent reads it and its own ticket. Copy every rule an agent needs into the brief, so agents work from the brief alone and leave `SKILL.md` and `references/jaidev-reference.md` (12 KB) to the coordinator |
| Phase 1: prepare | The agent reads the ticket and the code, settles the names with `jeeves:typescript-naming`, writes its briefing to a file, reports back and posts nothing |
| Phase 2: run | The coordinator sends "go" once the base is ready; the agent posts the briefing, answers questions, reviews the plan and the PR |
| State file | A JSON file in the scratchpad, one entry per ticket: agent id, branch, last Jaidev comment id, last PR head, last reported CI head, merged flag |
| Events | One `SendMessage` per agent, carrying every event for that agent (two events in one message cost one wake-up), then the state file updates (see "Poll events") |
| Reports | Fetch origin and check any disputed or surprising claim in an agent's report against the latest parent branch yourself before you approve a scope |
| Approvals | The agent approves and merges a PR only when the user authorized both for that flow; otherwise it reports and the user decides. A pre-approval to merge a named set of PRs once CI passes covers only those PRs: after the agent reports a clean review and the head still matches, send the agent "merge" yourself; ask the user when a finding, a failed check or a moved head appears |
| Stop | A third failed revision round, a Blocked run, a rejected merge or a missing approval stops the agent, and it reports to the coordinator |
| Next ticket | Start a fresh Phase 1 agent for the next unblocked ticket while a PR waits in review or CI (see "Preparing the next ticket"). Reuse a finished agent only under "Reuse or spawn" |
| Repo facts | Fill the brief template's "Repo facts" section from `references/repo-notes.md`; after each merge, append the agent's "Repo facts learned" to that file in the same turn |
| Cleanup | After the last merge, delete the cron job, stop the PR watcher and mark the tickets merged in the state file |

### Poll events

Two watchers split the work, and only the cron costs a model turn per tick.

| Watcher | Covers | Cost |
|---|---|---|
| PR watcher (`scripts/pr-watch.zsh`, run with `Monitor`) | New PR head, CI result, review decision, merge or close | One model turn per printed line |
| Linear cron | Jaidev's status comment and its Timeline: a question, a plan, a Blocked comment or a PR opened. List comments with `limit: 1`, because a full list costs 5k to 25k tokens | One model turn per tick |

When a PR opens, start a `Monitor` on the PR watcher (30-minute timeout, re-arm on expiry, one monitor per group of PRs). It prints one line per change and runs free of model turns between events. Run it from the PR's repo directory so `gh` picks the right account:

```bash
cd <repo-dir> && <skill-base-dir>/scripts/pr-watch.zsh 60 <pr-number> [<pr-number> ...]
```

Pace the Linear cron by the phase:

| Phase | Interval |
|---|---|
| Waiting for analysis or plan v1 or v2 | 2 minutes |
| Implementation running | 5 minutes |
| Every ticket in the batch has a PR | Delete the cron job; the PR watcher covers the rest, and a Jaidev revision shows as a new PR head |

Events: a new question, a plan, a Blocked comment, a PR, a finished revision, a completed CI run or a merge. Each wake-up makes the agent re-read its whole context, so wake an agent only for:
- the first question, a plan, or a Blocked comment;
- all checks complete on a PR head (a new PR or a finished revision waits for this, and the agent reviews the diff and the CI result together);
- a merge.

On each event:
- Compare it with the state file, read and updated with `scripts/poll-state.py`:

  ```bash
  scripts/poll-state.py <state-file> get <ticket>
  scripts/poll-state.py <state-file> set <ticket> <field> <value>
  ```
- Status and progress comments change nothing.
- Send the ticket's agent one `SendMessage` that names every pending event, then update the state file. Two events for the same agent go in one message, because every wake re-reads the agent's whole context.

### Preparing the next ticket

When the tickets form a chain, the next unblocked ticket gets its briefing ready while the current PR waits.

- Start one Phase 1 agent for the next ticket as soon as the current PR is in review or CI.
- Point the agent at the unmerged code on the PR's branch, and at the PR's briefing and names reply.
- Keep at most 2 agents running.
- Send "go" after the blocking PR merges.

### Reuse or spawn

A resumed agent re-reads its whole context on every turn, so a long-lived agent taxes every later message. Spawn a fresh agent per ticket and carry knowledge in `references/repo-notes.md`. Reuse a finished agent (`SendMessage` with the next ticket) only when all hold:
- its completion notice shows under about 50k tokens of context;
- the next ticket edits the same files or tests;
- the previous ticket is merged, so nothing runs in parallel;
- the agent re-fetches origin and treats its earlier notes as unverified.

Name the session after the batch (`/rename`) when it starts a poll.

#### Batch small tickets

Up to 3 one-point tickets with disjoint files may share one agent:
- Phase 1 writes the two files per ticket in one pass.
- The coordinator sends "go <ticket-id>" per ticket.
- PR reviews run one after another.

Such an agent reached about 220k tokens of context, so 3 is the cap.

### Agent run endings

An agent ends each run with "I cannot wait for wake-ups, resume me via SendMessage". That is expected; resume it by message.

### Coordinator cron prompt

Use this prompt for the Linear cron (every 3 minutes at first, one job per batch; fill `{{TICKETS}}` and `{{STATE_FILE}}`):

```text
Poll {{TICKETS}}. State file: {{STATE_FILE}}. For each ticket with mergedReported=false, run these two commands first (<t> is the ticket id in lowercase):

gh pr list --head jai-dev/<t> --state all --json number,headRefOid,state,mergedAt
git ls-remote --heads origin jai-dev/<t>

List Linear comments with limit 1 only when a pushed commit, a PR or every second tick says so. An event is a new Jaidev question, plan, Blocked comment, PR, finished revision, completed CI run on a new head, or merge; status and progress comments are not events. For each agent send ONE SendMessage naming every pending event, then update the state file with scripts/poll-state.py. When a PR opens, start a Monitor on scripts/pr-watch.zsh 60 <pr numbers> (30-minute timeout, re-arm on expiry, one monitor per group of PRs). When every ticket in the batch has a PR, CronDelete this job. When a PR is merged, set mergedReported=true and tell the user. Post nowhere; approve and merge only after the user's "merge" (or a pre-approval that covers that PR).
```
