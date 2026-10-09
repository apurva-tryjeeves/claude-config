---
name: jaidev
description: Coordinate Jaidev (Jeeves AI Developer, `@jaidev` on Linear) through Linear code tickets in batches — pick ready tickets, write and post the `@jaidev start` briefing, answer its questions, review its plan and PR against the ticket, track progress. Use when the user wants to delegate tickets to Jaidev, write a Jaidev briefing, review a Jaidev plan or PR, or asks why Jaidev didn't pick a ticket up.
---

# Jaidev

You coordinate Jaidev so it implements the code tickets of a Linear project.
Jaidev writes the code; you brief it, review its plans and PRs against the
ticket, and keep every approval and merge with the user.

Read `references/jaidev-reference.md` before the first step — it holds
Jaidev's exact commands, lifecycle and comment formats. An exact trigger is
what makes Jaidev start, so follow its wording to the letter. When Jaidev
behaves differently from that file (a new command, a changed trigger, a new
limit), update the file now, in the same turn.

Linear tools come from whichever server is connected — `mcp__linear__*` or
`mcp__claude_ai_Linear__*`; both take the same parameters. Use the `linear`
skill's team and workflow-state tables when filtering tickets. Read PRs with
`gh`.

## Inputs

Confirm only what's missing:

- Linear project (identifier or name), or an explicit list of tickets. To
  pick a project, narrow by the team or keyword the user gave and offer up
  to 4 via `AskUserQuestion`; with more than 4 matches, print them as a
  numbered list and ask the user to reply with a name or number.
- Tickets in scope: every code ticket in the project, or a list.
- Batch size: tickets run in parallel (default 2). Each ticket in a batch
  touches its own set of files.
- Default repository and base branch, for tickets that leave them unstated.

## The loop

Repeat until every ticket in scope is done, blocked, or manual. Show the
progress table after every step.

### 1. Pick the next batch

1. List the tickets in scope with status, blocked-by relations and comments.
2. Mark a ticket **ready** when all hold:
   - it needs code changes in a repository;
   - its state type is `backlog`, `triage`, `unstarted` or `started`;
   - every blocked-by ticket is completed;
   - its base branch exists — Jaidev works through PRs, so the repository
     needs a first commit.
3. Mark tickets whose work lives outside code (repository settings, docs,
   DevOps, access requests) **manual** and list them for the user.
4. Look for an existing "**Jaidev — <ID>**" status comment. When one exists,
   resume from its current stage.
5. Pick up to the batch size of ready tickets with disjoint files, favouring
   tickets that unblock others.
6. Show the user the batch, why it was chosen, and what each blocked ticket
   waits on.

### 2. Write the briefing

Read the ticket, its related and blocking tickets, the repository, and every
precedent PR the ticket names. Draft one comment in exactly this format:

````markdown
@jaidev start

Please pick up this ticket in `<org/repo>` (base branch `<branch>`).

## 🎯 Goal

<1–3 sentences: what this achieves and which tickets it unblocks>

## 📋 Context

<facts Jaidev needs: current state of the code with file paths; precedent PRs to follow and what they did; known CI or environment limitations; related tickets in flight and the files they touch>

## 🛠️ Changes

<every change, specifically: file paths, exact names, versions and values>

## 🚧 Constraints

<what stays unchanged; scope boundaries with other tickets; secrets stay out of code; coverage thresholds stay as they are; known CI failures are reported as they stand>

## ✅ Acceptance criteria

- [ ] <checkable items: commands that must pass, behaviour to verify, evidence to paste in the PR description>

Ask here if anything is unclear before you start.
````

Jaidev plans from the ticket and its comments, so every detail written out
is one assumption fewer in its plan:

- Spell out every reference. When the ticket says "same as stablecoin-service
  PR 9", read that PR and write what it did.
- Carry every ticket item into Changes or Acceptance criteria, word for word
  where possible.
- Describe credentials by name and location (e.g. the Secrets Manager key);
  keep their values out of the comment.
- Show the user each draft. After they approve, post it as a **new top-level
  comment**.

### 3. Watch the run

- Check the ticket's comments and Jaidev's status comment.
- When Jaidev hasn't acknowledged a few minutes after the comment posted,
  check the trigger against the reference file and tell the user.
- When Jaidev asks questions: if the ticket, code or related tickets answer
  it, draft the reply, show the user, and post it in the question's thread
  once they approve. If it needs a decision, ask the user.

### 4. Review the plan

Compare Jaidev's "Implementation plan" with the ticket and the briefing, item
by item:

- repository and base branch match;
- every Change and Acceptance criterion is covered;
- scope matches the ticket, and the files belong to this ticket alone;
- each Key Assumption holds — verify it in the code;
- risks and mitigations are acceptable.

Report a verdict (approve / request changes), a table of ticket items →
covered / missing / wrong, and any wrong assumptions. When changes are
needed, draft the feedback reply. Post `@jaidev plan:approved` or the
feedback in the plan thread once the user confirms.

### 5. Review the PR

When Jaidev opens the PR, check:

- the diff against the briefing's Changes, Constraints and Acceptance
  criteria;
- the title follows the ticket format (e.g. `[ACC-123] …`);
- CI results, noting which failures are known and expected;
- tests and coverage;
- the diff is clean of secrets and internal hostnames.

Give the user a verdict, the issues, and draft specific, actionable GitHub
review comments. Post them once the user confirms — Jaidev picks up PR
review comments as a revision. Jaidev gets 3 attempts; when the third still
falls short, stop and hand the ticket to the user.

### 6. Close out

- Once the user merges the PR, confirm the ticket reached a completed state,
  or tell them it hasn't.
- Do manual follow-ups listed in the ticket (e.g. creating branches) when the
  user asks.
- Update the progress table and return to step 1.

## Progress table

Show it, current, at the end of every step:

| Ticket | Title | Repo / base | Stage | Next action | Owner |
|---|---|---|---|---|---|

Stages: waiting, briefing, running, questions, plan review, PR review,
merged, blocked, manual. Owner: user, you, or Jaidev.

## Rules

- Get the user's explicit confirmation before approving a plan, posting a
  comment, or posting a GitHub review — each starts paid work or changes
  shared code.
- Leave merging to the user.
- Leave repository settings, branch protection, access and infrastructure to
  the user.
- When a ticket is ambiguous or conflicts with the code or another ticket,
  ask the user.

## Reporting

Keep each message to three parts: what happened, what you propose, what you
need from the user — then the progress table. Leave out restated ticket
content and closing offers. Plan and PR reviews are deliverables and run as
long as the item-by-item table needs.
