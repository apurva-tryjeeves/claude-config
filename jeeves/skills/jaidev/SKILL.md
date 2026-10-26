---
name: jaidev
description: Coordinate Jaidev (`@jaidev` on Linear) through code tickets: brief it, answer its questions, review its plans and PRs, unblock runs, track batches with background agents. Use to delegate tickets to Jaidev, write a Jaidev briefing, review a Jaidev plan or PR, or when Jaidev didn't start or got blocked.
---

# Jaidev

You coordinate Jaidev so it implements the code tickets of a Linear project.
Jaidev writes the code; you brief it, review its plans and PRs against the
ticket, and keep every approval and merge with the user.

Read `references/jaidev-reference.md` before the first step — it holds
Jaidev's exact commands, lifecycle, comment formats and limits. An exact trigger is what makes Jaidev start, so
follow its wording to the letter.

Check the reference file first whenever Jaidev acts. When Jaidev shows
something new — a command, a trigger, a comment format, a limit, a timing —
update the file now, in this same turn.

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

## Ticket patterns

Pick the pattern from the ticket's shape; both run the loop below.

| | Single-task ticket | Parent feature with sub-tickets |
|---|---|---|
| Jaidev's start branch | the repository's default branch | the parent branch `feat/<PARENT-ID>` |
| PR base | the default branch | the parent branch |
| Jaidev's branch | `jai-dev/<ticket-id>` | `jai-dev/<sub-ticket-id>`, cut from the parent branch |
| Merge | the user merges the PR | the user merges each sub-ticket PR into the parent; the parent's own PR to the default branch comes last |
| Order | blocked-by relations | blocked-by relations, then file overlap |

For a parent feature:

- Cut the parent branch from the default branch and push it before the
  first briefing, so Jaidev has a base with a commit.
- State the start branch and the PR base in the briefing's opening
  paragraph and again under Constraints.
- Merge tickets that edit the same files one at a time (for example a
  worker start file, or one block of the config files). Merge the first,
  then ask the next ticket's PR to catch up with the parent.
- When a sub-ticket PR falls behind the parent, ask Jaidev to rebase onto
  the parent. Jaidev's default is to merge the base into its branch, and the
  rebase keeps the PR history linear. Post the request as a PR comment:

  ```text
  ## 🔁 Rebase onto the parent branch

  This branch is behind <parent-branch>. Rebase it onto <parent-branch> and push.
  ```

  Jaidev rebases and force-pushes its own branch (ACC-1591, 2026-10-22). It
  counts the request as a revision round, so a ticket with two earlier rounds
  has no attempt left afterwards. Ask for the rebase when the PR has a round to
  spare, or when no further fix is expected.
- Every sub-ticket PR title carries its own ticket id, so Linear moves that
  ticket when the PR merges.

## The loop

Repeat until every ticket in scope is merged, blocked, or manual. Show the
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
   resume from its current stage. When none exists, treat the ticket as not
   started by Jaidev, whatever its Linear state — a project can have every
   ticket bulk-moved to In Progress.
5. List every `@jaidev` comment that has no status comment after it — a
   leftover that never triggered — so the user can delete it.
6. Pick up to the batch size of ready tickets with disjoint files, favouring
   tickets that unblock others.
7. Show the user the batch, why it was chosen, and what each blocked ticket
   waits on.

### 2. Write the briefing

Research first. Jaidev plans from the ticket and its comments, so every
verified fact in the briefing becomes a correct assumption in its plan:

- Read the ticket, its related and blocking tickets, the repository, and
  every precedent PR the ticket names. Spell out every reference: when the
  ticket says "same as stablecoin-service PR 9", read that PR and write what
  it did.
- Check every factual claim in the ticket against the code — current config,
  versions, file layout, what CI runs. Brief Jaidev on what is true, and
  tell the user each correction.
- Read how one or two sibling services do the same thing, and follow the
  setting the team already uses.
- When the ticket touches build, lint or CI, read `.github/workflows/*`, the
  inputs it passes to any reusable workflow, and the npm scripts those
  inputs run, including `pre*` hooks (e.g. `prebuild` running lint).
- Run every acceptance-criterion command in the repository before
  briefing, and adjust any that can't pass in Jaidev's sandbox (e.g. single
  test files need `--coverage=false` when `jest.config.js` enforces a global
  threshold). Run any code the briefing gives the same way: compile it,
  lint it under the rules it will meet (including open PRs that tighten
  them), and test it with coverage on, under the strictest compiler flags
  the team's guidelines require.
- Settle every identifier the briefing introduces with the
  `jeeves:typescript-naming` skill, following its "During planning" steps.
  Read the repo rules and the surrounding code first, then write the Names
  table (kind, name, file, purpose) and the renames list. The names reply
  carries the table, and Jaidev uses the names as written.

Then draft one comment in exactly this format:

````markdown
@jaidev start

Please pick up this ticket in <org/repo>. Start your branch from <start-branch> and open the PR against <base-branch>.

## 🎯 Goal

<1–3 sentences: what this achieves and which tickets it unblocks>

## 📋 Context

- <current state of the code, in words>
- <precedent PRs to follow and what they did>
- <known CI or environment limitations>
- <related tickets in flight and the files they touch>

## 🛠️ Changes

- <every change in prose: what changes and why; the exact names, paths and values follow in the thread reply>

## 🚧 Constraints

- <what stays unchanged; scope boundaries with other tickets>
- Secrets stay out of code; coverage thresholds stay as they are.
- Report known CI failures as they stand.
- Your changes stay outside .github/workflows.

## 🧑‍🔧 Manual follow-up

- <changes a human makes on your branch, e.g. .github/workflows edits; they sit outside your definition of done>

## ✅ Acceptance criteria

- [ ] <checkable items your branch alone can satisfy: commands that must pass, behaviour to verify, evidence to paste in the PR description; the full test suite and coverage gate as the CI check that runs them, e.g. "CI test / Unit Test passes">

A reply in this thread follows with the exact names and code. Copy every acceptance criterion into your plan's Done when, word for word. Name any you can't meet in the plan, before you start. Quote back at the top of your plan one key code signature (if this briefing gives code) and acceptance criterion #1. Write any code this briefing gives out in full in your plan's Implementation Sequence. Ask here if anything is unclear.
````

Write the briefing to these rules:

- Carry every ticket item into Changes, Acceptance criteria or Manual
  follow-up, word for word where possible.
- Put every change to `.github/workflows/*` under Manual follow-up. Jaidev's
  GitHub token has no `workflow` scope, so those changes reach the branch
  through the user (see Rules).
- Keep lists one level deep, with each item's detail on its own line.
- Ask Jaidev to quote back, at the top of its plan, one key code signature
  (when the briefing gives code) and one acceptance criterion. Check both
  against the briefing before reviewing the rest of the plan.
- Write the start comment as prose and short lists. Identifiers, paths, backticks and
  code go in the names reply, because they arrive blank in a start comment (reference
  §5): send the Names table and the code in plain fenced blocks as the answer to
  Jaidev's first question, or as plan feedback when it plans without asking.
- Open every other body you post (an approval review, a Linear comment not
  addressed to Jaidev) with `## <emoji>` section headers, as the doc-format
  hook requires. Comments addressed to `@jaidev` follow the briefing
  format.
- Describe credentials by name and location (e.g. the Secrets Manager key);
  keep their values out of the comment.
- Show the user each draft and wait for explicit approval of that draft:
  "post it", "yes" or "approved". A general go-ahead ("coordinate with
  Jaidev per the skill") starts the drafting; posting waits for approval of
  the draft itself. Then post it as a **new top-level comment**.
- Omit the Manual follow-up section when it has no items. When it has
  items, add "A human makes the items under Manual follow-up." to the
  workflows Constraint.
- Write acceptance criteria Jaidev can meet in its sandbox: commands that
  exist in the base branch's `package.json` and single test files. Name the
  full suite and coverage gate by their CI check (reference §5).

### 3. Watch the run

- Poll with `list_comments` and `limit: 1`: Jaidev's status comment is the newest
  by update, and its Timeline shows "Plan v1 posted", "Plan feedback received" and
  "Revised plan v2 posted". Open a full plan with `limit: 2` only when the timeline
  shows a new plan, and read the status line for Blocked. A full list costs 5k to
  25k tokens.
  `~/.claude/memory/jaidev-run-timings.md` shows how long each phase usually takes.
- In your first report on a ticket, tell the user that Jaidev's status, plan
  and progress comments are the items you review, so a new Jaidev comment
  means a review from you is on its way.
- When no status comment appears within a few minutes of posting, check the
  trigger against the reference file and tell the user.
- When Jaidev asks questions: if the ticket, code or related tickets answer
  it, draft the reply, show the user, and post it in the question's thread
  once they approve. If it needs a decision, ask the user.
- During implementation, read the rolling notes in the live progress
  comment. When a note signals a blocker — a rejected push, missing access,
  a failing check outside the ticket — tell the user at once with the
  options; Jaidev spends its remaining attempts before posting Blocked.
- When Jaidev posts "🚫 Blocked — Needs Human Help": read "What Failed" and
  "What I Tried", inspect the pushed branch, and give the user the options.
  Once they choose, make any approved manual change, then post
  `@jaidev resume` as a reply in the Blocked thread, saying what changed.

### 4. Review the plan

Plan v1 usually needs one correction round. Expect these gaps and check each
first:

- the base branch is the default branch instead of the briefed one;
- names are invented where the briefing's names arrived blank;
- Done-when criteria are reworded or missing;
- acceptance criteria arrive blank.

Compare Jaidev's latest "Implementation plan" with the ticket and the
briefing, item by item:

- repository and base branch match;
- the quote-back matches the briefing, and any code the briefing gave
  appears in the Implementation Sequence exactly as briefed;
- every Change and Acceptance criterion is covered, value by value — rule
  names, options, versions and file names exactly as briefed. An item is
  covered when the plan names its value; a preset that "includes most of
  it" counts as missing;
- scope matches the ticket, and the files belong to this ticket alone;
- each Key Assumption holds — verify it in the code. A revised plan may omit
  the section; verify the assumptions it now relies on;
- risks and mitigations are acceptable.

Send the correction as one feedback reply that lists the base branch, the
Names table, every Done-when criterion word for word and the PR title, in
plain fenced blocks. Approve v2 when it matches.

Report a verdict (approve / request changes), a table of ticket items →
covered / missing / wrong, and any wrong assumptions. When changes are
needed, draft the feedback reply. Post `@jaidev plan:approved` or the
feedback as a reply in the thread of the **latest** plan once the user
confirms. A revised plan arrives as a new top-level comment ("Implementation
plan (v2)"), and Jaidev resolves the previous plan's thread.

### 5. Review the PR

When Jaidev opens the PR:

1. Read `.github/CODEOWNERS` and the merge box, and tell the user now which
   approvals the merge needs besides theirs: the code-owner teams for the
   PR's files, whether the user belongs to them
   (`gh api orgs/<org>/teams/<team>/memberships/<login>`), and two members
   who can approve. When the membership lookup is denied, name the
   code-owner teams and ask the user whether they belong to them.
2. Wait until every check has completed, SonarCloud included. Jaidev pushes
   fixes for bot findings on its own, so review the head that remains after
   that fix.
3. Review the PR and record the head SHA you reviewed:
   - the diff against the briefing's Changes, Constraints and Acceptance
     criteria, using the PR's own file list (the result comment counts only
     the last session's files);
   - the title follows the ticket format (e.g. `feat: [WAL-123] - …`);
   - CI results, noting which failures are known and expected;
   - tests and coverage;
   - generated files regenerate with no diff, and the lockfile adds or
     removes only what the change needs;
   - the effect beyond the PR: the deploy build (e.g. the Dockerfile's
     `npm run build`) and other open PRs against the same base;
   - the diff is clean of secrets and internal hostnames.
4. Trace each finding through the code path and its call sites. Report
   verified findings as issues and the rest as questions.
5. Give the user a verdict, the issues, and draft specific, actionable
   GitHub review comments, all in one review. Post them once the user
   confirms — Jaidev picks up PR review comments as a revision.
6. When nothing needs changing, confirm the head still matches the SHA you
   reviewed, propose an Approve review, and submit it once the user
   confirms. The approval goes out under the user's account.
7. Read the merge box and tell the user any requirement still missing, such
   as another required reviewer.
8. Draft follow-ups that belong outside the PR as new tickets for the user,
   each blocked by this ticket.

Read the head SHA, review state and checks:

```bash
gh pr view <number> --json headRefOid,reviewDecision,mergeStateStatus,statusCheckRollup --jq '{head: .headRefOid, merge: .mergeStateStatus, review: .reviewDecision, checks: [.statusCheckRollup[] | {n: (.name // .context), s: .status, c: (.conclusion // .state)}]}'
```

Submit the approval:

```bash
gh pr review <number> --approve
```

Jaidev gets 3 attempts per PR, and each review round uses one — a SonarCloud
finding counts as a round. When the third still falls short, stop and hand
the ticket to the user.

### 6. Close out

- Once the user merges the PR, confirm the ticket reached a completed state,
  or tell them it hasn't.
- Do manual follow-ups listed in the ticket or the briefing when the user
  asks.
- Add the run's row to the cost table in `~/.claude/memory/jaidev-run-timings.md`, and widen a typical range or edit a pattern when the run falls outside it.
- Update the progress table and return to step 1.

## Background agents

With two or more tickets in flight, run each in its own background agent. Read
`references/background-agents.md` first: it holds the agent tiers, the shared-brief
rules, the state file, the PR watcher and the Linear poll cadence. Start from
`assets/agent-brief-template.md` and keep the state file with `scripts/poll-state.py`.

## Progress table

Show it, current, at the start of every report:

| Ticket | Title | Repo / base | Stage | Next action | Owner |
|---|---|---|---|---|---|

Stages: waiting, briefing, running, questions, plan review, blocked,
PR review, awaiting merge, merged, manual. Owner: user, you, or Jaidev.

Collapse tickets in stage `waiting` with owner `you` into one line under the
table: "Waiting (N): WAL-1, WAL-2". Give every other ticket its own row.

List follow-up tickets created during the run as their own rows, with their
blocked-by ticket, so the table shows what each merge unblocks.

## Rules

- Get the user's explicit approval — "post it", "yes" or "approved" for that
  specific item — before posting a comment, approving a plan, posting a
  GitHub review, or pushing a commit. Each starts paid work or changes
  shared code.
- Push to Jaidev's branch only the Manual follow-up changes the user
  approved, commit by commit; every other fix reaches Jaidev as a review
  comment.
- Leave merging to the user.
- Leave repository settings, branch protection, access and infrastructure
  to the user.
- When a ticket is ambiguous or conflicts with the code or another ticket,
  ask the user.
- Ask the user one decision at a time with `AskUserQuestion` (two or three
  options, the recommended one first), and explain any term the user asks about
  before asking again.
- A user pre-approval to merge a named set of PRs once CI passes (for example
  "merge both once CI passes") covers only those PRs: after the agent reports a
  clean review and the head still matches, send the agent "merge" yourself; ask
  the user when a finding, a failed check or a moved head appears.

## Reporting results

Start each message with the progress table, then three parts: what
happened, what you propose, what you need from the user. Leave out restated ticket
content and closing offers. Plan and PR reviews are deliverables and run as
long as the item-by-item table needs.
