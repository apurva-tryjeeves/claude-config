---
name: jaidev
description: "Coordinate Jaidev (`@jaidev` on Linear) through code tickets: brief it, answer its questions, review its plans and PRs, unblock runs, track batches with background agents. Use to delegate tickets to Jaidev, write a Jaidev briefing, review a Jaidev plan or PR, or when Jaidev didn't start or got blocked. Every `@jaidev` comment on a ticket follows this skill."
---

# Jaidev

You coordinate Jaidev so it implements the code tickets of a Linear project.
Jaidev writes the code; you brief it, review its plans and PRs against the
ticket, and keep every approval and merge with the user.

Read `references/jaidev-reference.md` before the first step — it holds
Jaidev's exact commands, lifecycle, comment formats and limits. An exact
trigger is what makes Jaidev start, so follow its wording to the letter.

Check the reference file first whenever Jaidev acts. When Jaidev shows
something new — a command, a trigger, a comment format, a limit, a timing —
write it back in this same turn to the clone's copy of
`references/jaidev-reference.md`, and read every jaidev reference
(`references/*.md`) from the clone's copy when it exists. The rule
(clone path, read order, uncommitted edit, absent clone) is in
`${CLAUDE_PLUGIN_ROOT}/references/write-back.md`; every "write back" in this
skill's references follows it.

Linear tools come from whichever server is connected — `mcp__linear__*` or
`mcp__claude_ai_Linear__*`; both take the same parameters. Filter tickets by
state type: `backlog`, `triage`, `unstarted`, `started`, `completed`,
`canceled`. Read PRs with `gh`.

## Sessions

Run one session per wave: the batch picked in step 1, through its last merge.

1. Start the wave by reading the previous wave's handoff file, when one exists.
2. Close the wave by writing `<scratchpad>/<wave>-handoff.md`: tickets
   merged, follow-up tickets, open items, the state file path.
3. Stop the wave's watcher, then ask the user to run `/clear` and
   start the next wave from the handoff.

Each call re-reads the whole session, so a fresh session per wave keeps every
event and review cheap.

## Inputs

Confirm only what's missing:

- Linear project or list of tickets.
- Tickets in scope: every code ticket in the project, or a list.
- Default repository and base branch, for tickets that leave them unstated.
- The project's design doc (e.g. a Notion plan), when it has one.

## Ticket patterns

Pick the pattern from the ticket's shape; both run the loop below.

| | Single-task ticket | Parent feature with sub-tickets |
|---|---|---|
| Jaidev's start branch | the repository's default branch | the parent branch `feat/<PARENT-ID>` |
| PR base | the default branch | the parent branch |
| Jaidev's branch | `jai-dev/<ticket-id>` | `jai-dev/<sub-ticket-id>`, cut from the parent branch |
| Merge | the PR merges after the user's "merge" (see Rules) | each sub-ticket PR merges into the parent after the user's "merge"; the parent's own PR to the default branch comes last |
| Order | blocked-by relations | blocked-by relations, then file overlap |

For a parent feature:

- Cut the parent branch from the default branch and push it before the
  first briefing, so Jaidev has a base with a commit.
- Merge tickets that edit the same files one at a time (for example a
  worker start file, or one block of the config files). Merge the first,
  then ask the next ticket's PR to catch up with the parent.
- When parallel sibling tickets would each delete entries from one shared
  block (a placeholder list, a registry, an enum), give the deletions to the
  last ticket or the parent PR, so every sibling PR adds lines only and
  merges cleanly.
- When a sub-ticket PR falls behind the parent, ask Jaidev to rebase onto
  the parent. Jaidev's default is to merge the base into its branch, and the
  rebase keeps the PR history linear. Post the request as a PR comment:

  ```text
  ## 🔁 Rebase onto the parent branch

  This branch is behind <parent-branch>. Rebase it onto <parent-branch> and push.
  ```

  Jaidev rebases and force-pushes its own branch (ACC-1591, 2026-10-22). It
  counts the request as a revision round, so a ticket with two earlier rounds
  leaves 0 attempts afterwards. Ask for the rebase when the PR has a round to
  spare, or when it is the last change expected.
- Every sub-ticket PR title carries its own ticket id, so Linear moves that
  ticket when the PR merges.

## The loop

Repeat until every ticket in scope is merged, blocked, or manual. Show the
progress after every step.

### 1. Pick the next batch

1. List the tickets in scope with status, blocked-by relations and comments.
   Delegating a ticket to Jaidev leaves it unassigned to the user; the
   `linear` skill's "Start work on a ticket" assignment applies to the user's
   own work.
2. Mark a ticket **ready** when all hold:
   - it needs code changes in a repository;
   - its state type is `backlog`, `triage`, `unstarted` or `started`;
   - every blocked-by ticket is completed;
   - its base branch exists — Jaidev works through PRs, so the repository
     needs a first commit.
3. Mark tickets whose work lives outside code (repository settings, docs,
   DevOps, access requests) **manual** and list them for the user.
4. Read an existing "**Jaidev — <ID>**" status comment and resume from its stage.
5. Pick the ready tickets with disjoint files, favouring tickets that unblock others.
6. Show the user the batch, why it was chosen, and what each blocked ticket
   waits on.

### 2. Start the run

Draft a bare start by default, show it to the user, and post it after the
user's yes. For a ticket that spans repositories, contradicts the code or
names a precedent outside the repository, research the ticket and write a
briefing in the format in `assets/briefing-format.md`. Read
`references/briefing.md` before the first start of a session: it holds the
choice, the research list, the drafting rules and the posting order.

### 3. Watch the run

- Watch the wave, one ticket or many, as `references/background-agents.md`
  ("Poll events") describes. The coordinator wakes only when the watcher
  prints an event:

  ```bash
  cd "${CLAUDE_SKILL_DIR}/scripts" && python3 -m jaidev_watch watch <state-file>
  ```

- Read expected stage times from
  `~/.claude/org-memory/jeevesinc/jaidev-run-timings.md` when it exists.
- Stamp each post in the state file right after it goes up: `startedAt`,
  `feedbackAt`, `approvedAt`, `reviewAt`, with their inputs ("Stamp each
  post"). The watcher reads only where the stage expects an answer, so an
  unstamped post goes unwatched.
- Act on each watcher event, deadline events included, as the "Event lines"
  table in `references/background-agents.md` says.
- When an event needs context, read Jaidev's status comment with
  `list_comments` and `limit: 1`; its Timeline shows "Plan v1 posted", "Plan feedback received" and "Revised plan
  v2 posted". Open a full plan with `limit: 2` only when the timeline shows a
  new plan. A full list costs 5k to 25k tokens.
- When Jaidev asks a question that the ticket, code or related tickets
  answer, draft the reply, show the user, and post it in the question's
  thread once they approve. Point to the names comment above the start
  comment when it holds the answer. When the question needs a decision, ask
  the user.
- When Jaidev posts "🚫 Blocked — Needs Human Help": read "What Failed" and
  "What I Tried", inspect the pushed branch, and give the user the options.
  Once they choose, make any approved manual change, then post
  `@jaidev resume` as a reply in the Blocked thread, saying what changed.

### 4. Review the plan

Compare Jaidev's latest plan with the ticket, the briefing and the design
doc item by item, then post one correction or `@jaidev plan:approved` after
the user's yes. Read `references/plan-review.md` when a plan lands: it holds
plan v1's expected gaps, the checklist, the correction contents and the
report shape.

### 5. Review the PR

Wait for every check on the PR head, review it against the one checklist,
and post the review or the approval after the user's yes. Read
`references/pr-review.md` when Jaidev opens a PR: it holds the steps, the
review checklist the `jeeves:jaidev-pr-reviewer` agent also uses, the `gh`
commands and the revision-round limit.

### 6. Close out

- After the merge, confirm the ticket reached a completed state,
  or tell them it hasn't.
- Do manual follow-ups listed in the ticket or the briefing when the user
  asks.
- Add the run's row to the cost table in `~/.claude/org-memory/jeevesinc/jaidev-run-timings.md`, creating the file with this first row when it doesn't exist yet, and widen a typical range or edit a pattern when the run falls outside it.
- Update the progress and return to step 1.

## Background agents

With two or more tickets in flight, run each in its own background agent. Read
`references/background-agents.md` first: it holds the agent types, the
shared-brief rules, the state file and the watcher.

- Run the ticket work in a `jeeves:jaidev-ticket` agent, started from
  `assets/agent-brief-template.md`. Fill its "Repo facts" from
  `references/repo-notes.md`, the per-repo facts agents found on earlier
  tickets.
- Run each PR review in a fresh `jeeves:jaidev-pr-reviewer` agent.
- Model and effort come from the agent definition, as do the skills the
  agent loads besides the brief.
- Change the watcher scripts in `scripts/` through the
  `jeeves:jeeves-python-engineer` agent.

## Progress

Show it, current, at the start of every report to the user; a watcher wake
for a `LINEAR POLL ERROR` line alone skips it.

Show the current state of each ticket with the color coding: identity emoji, ticket id, status circle, stage, next action. `references/background-agents.md` ("Color coding") holds the rule. Collapse tickets still waiting into one line: "Waiting (N): WAL-1, WAL-2".

Stages: waiting, briefing, running, questions, plan review, blocked,
PR review, awaiting merge, merged, manual.

List follow-up tickets created during the run with their blocked-by ticket,
so the progress shows what each merge unblocks.

## Rules

- Get the user's explicit approval — "post it", "yes" or "approved" for that
  specific item — before posting a comment, approving a plan, posting a
  GitHub review, or pushing a commit. Each starts paid work or changes
  shared code.
- Push to Jaidev's branch only the Manual follow-up changes the user
  approved, commit by commit; every other fix reaches Jaidev as a review
  comment.
- Merging: the agent runs the merge, and only after the user's "merge" or a
  pre-approval that names the PRs.
- Leave repository settings, branch protection, access and infrastructure
  to the user.
- Open every approval review, and every Linear comment addressed to someone
  other than Jaidev, with `## <emoji>` section headers. Comments addressed to
  `@jaidev` follow the briefing format.
- When a ticket is ambiguous or conflicts with the code or another ticket,
  ask the user.
- Ask the user one decision at a time with `AskUserQuestion` (two or three
  options, the recommended one first), and explain any term the user asks about
  before asking again.

## Reporting results

- Start the first colored report with the legend line
  (`references/background-agents.md`, "Color coding").
- Start each message with the progress, then three parts: what happened,
  what you propose, what you need from the user.
- Report new facts only, and end on the request to the user; leave out
  restated context and closing offers.
- A watcher wake for a `LINEAR POLL ERROR` line alone gets one line naming
  the retry.
- Plan and PR reviews are deliverables and run as long as the item-by-item
  table needs.
- Start every line you relay about an agent or its ticket with the identity
  emoji and ticket id, and put the status circle before the verdict.
