# Jaidev reference

Observed behaviour of Jaidev ("Jeeves AI Developer", `@jaidev` on Linear),
from real tickets. Check here first; when Jaidev shows something new, write it
back to this file in the same turn (`references/write-back.md` at the plugin root).

Sections 1–5 hold stable behaviour and are safe to reuse across runs.
Section 6 points to the local file that holds timings and costs, which vary
by ticket.

## At a glance

| Fact | Value |
|---|---|
| Linear handle | `@jaidev` |
| Start trigger | New top-level comment, first line exactly `@jaidev start` |
| Status comment title | **Jaidev — <TICKET-ID>** |
| PR author | `jaidev-jeeves` |
| Branch | `jai-dev/<ticket-id-lowercase>` (e.g. `jai-dev/wal-6298`) |
| Implementation attempts | Up to 5 per run, before it posts Blocked |
| PR revision attempts | Each review comment, rebase request, CI failure or SonarCloud finding starts a numbered revision; ACC-1701 reached Revision #4 (21 Nov 2026), so a PR takes more than 3. Jaidev's code caps CI-failure revisions at 2 per PR |
| GitHub token scope | Pushes code; `.github/workflows/*` goes through a human |

Develop environments per team, from Jaidev's deploy comment. For a team with
no row, read its deploy comment, then add a row.

| Team | Shared develop environments |
|---|---|
| Wallet | develop-11, develop-12, develop-13, develop-20 |
| Accounting & ERP | develop-07 |

## Contents

1. Lifecycle
2. Commands
3. Triggering a run
4. What its comments look like
5. Limits
6. Timings and costs
7. Run patterns

## 1. Lifecycle

1. **Start**: a user posts `@jaidev start` as a new top-level comment, after
   a names comment when the start is briefed (§5).
2. **Analysis**: Jaidev reads the ticket, its comments and its knowledge base
   (`PRODUCT.md`, `PLATFORM.md`, `SERVICE.md`, one file per repository) and
   explores the repositories.
3. **Questions** (optional): it posts questions and waits; it can also plan
   without asking. Status shows
   "Gathering Info (Waiting for Answers)".
4. **Plan**: it posts an "Implementation plan" comment and waits for
   approval. Feedback in the plan thread gets an in-thread ack within ~10 s;
   Jaidev then resolves that thread and posts "Implementation plan (v2)" as a
   new top-level comment.
5. **Implementation**: after approval it posts a live progress comment per
   repository and keeps it updated. When the base branch moves, it merges the
   base into its branch. It then opens one PR per repository, cc'ing the user
   who started it.
6. **Blocked** (optional): when it can't meet a definition-of-done item, it
   uses up its attempts (up to 5), then posts "## 🚫 Blocked — Needs Human
   Help" and waits for `@jaidev resume`.
7. **Review**: GitHub PR review comments trigger a revision ("Revision #1 —
   addressing N new comment(s) — Attempt 2/3"). SonarCloud bot findings
   trigger one too, with no human comment. It explains each fix in a PR
   comment.
8. **Deploy** (optional): on request it deploys to a shared develop
   environment or a short-lived one.
9. **Complete**: after the merge, the status comment shows "Complete ✅".

Throughout, the status comment shows the status, who started it, cost per
phase, repositories, PR links and a timeline.

## 2. Commands

| Command | Where | Effect |
|---|---|---|
| `@jaidev start` | New top-level comment | Starts analysis |
| Reply text | In the question's thread | Answers a question |
| `@jaidev skip` | Ticket comment | Skips open questions |
| `@jaidev abort` | Ticket comment | Stops the run |
| `@jaidev plan:approved` | Reply in the latest plan's thread | Approves the plan, starts implementation |
| `@jaidev plan:approved, auto-deploy` | Reply in the latest plan's thread | Approves and provisions a dev environment |
| Feedback text | Reply in the latest plan's thread | Requests plan changes; Jaidev acks in ~10 s, resolves the thread, posts the revised plan as a new top-level comment |
| `@jaidev plan:drop <repo-name>` | Reply in the latest plan's thread | Removes a repository from the plan |
| `@jaidev resume` | Reply in the Blocked thread | Resumes a blocked run; it reads the context text after the command |
| `@jaidev deploy on develop-NN` | Ticket comment | Deploys the ticket's modules to a shared develop environment (`to` and `on` both work) |
| `@jaidev deploy` | Ticket comment | Provisions a short-lived environment `dev-jaidev-<linear-id>`; re-run after pushing changes |

## 3. Triggering a run

- Start every run with a **new top-level comment** whose first line is
  exactly `@jaidev start`. The full briefing follows in the same comment. A
  fresh comment starts the run within seconds (3 s on WAL-6298).
- Jaidev responds to that exact wording. These variants left it idle:
  `start @jaidev`, `@jaidev get started`, `@jaidev please pick up this
  ticket…`.
- To retrigger, post a fresh comment. Jaidev reads new comments only; a
  comment edited to begin `@jaidev start .` stayed idle for 85 min.
- Start runs by comment: on assignment alone Jaidev stays idle and replies
  "I don't pick up tickets via assignment anymore. Reply `@jaidev start`".
- "Started by" in the status comment names the Linear account that posted
  the start comment.

## 4. What its comments look like

**Status comment** values seen: "Analyzing... (Queued — waiting for
available worker)" (first value when every worker is busy), "Awaiting Plan Approval", "Implementing...
(<repo> · verifying)", "Blocked 🚫 (Needs Human Help)", "PRs Created
(Awaiting Merge)", "Addressing PR Feedback..." (repo phase `revising`), "Complete ✅". The cost line is split by phase ("Analysis
· Planning · Impl · PR Rev") and refreshes after implementation ends. Earlier
phase figures can rise later (WAL-6300: analysis $0.15 → $0.27 by the time
implementation started), so read final costs from the last status.

**Implementation plan** sections:

- Header: Complexity, Estimate (points), Repos, Confidence, Delegating User
- Summary
- Key Assumptions, each with the evidence it checked (omitted from v1 on
  WAL-6300, a briefing that listed every file and line)
- Affected Services table: service, base branch, changes
- Implementation Sequence per repository, with "Done when" criteria
- Feature Flags
- Risk Assessment: risk and mitigation pairs
- Cross-Cutting Invariants it verifies before opening a PR
- Context Sources: knowledge-base files and repositories explored
- Footer with the approval commands

When reviewing, focus on Key Assumptions (they carry the most risk), whether
Affected Services lists the right repository and base branch, and whether the
"Done when" items match the ticket's acceptance criteria.

**Revised plan**: titled "Implementation plan (v2)". It lists the changes
either as a "Changes in this revision" list or as numbered items inside the
Summary (WAL-6300). It may omit Key Assumptions and shorten Context Sources.

**Live progress comment** (during implementation): it opens as
"**<repo>** • `jai-dev/<id>` ↗ / ⏳ Cloning `<base>`…", then shows "**<repo>** •
`jai-dev/<id>` ↗", a phase bar "Setup → Implementing → **Verify** → PR",
three rolling notes, and "🔄 N files • N edits • N min • attempt x/5". The
rolling notes surface blockers before the Blocked comment does.

**Blocked comment**: "## 🚫 Blocked — Needs Human Help" with What Failed,
What I Tried (per attempt), Root Cause Assessment, What I Need From You, and
To Resume. Read the cause from What Failed and What I Tried; the root-cause
line can read "Unknown (low confidence)" when the cause is stated above it.

**PR result comment**: "**<repo>** • ✅ Complete, PR #N • N files • $ • N
min", with revision entries appended. The file count covers the last
session only; read the PR for the full list.

**Deploy comment** after the PR: lists the module to deploy and the team's
allocated develop environments (see At a glance).

## 5. Limits

- It needs an existing base branch with at least one commit; the first commit
  of a new repository is a manual step.
- Deploys need the service to exist in the develop environments (Helm chart,
  HelmRelease).
- Knowledge-base files cover existing repositories. For a new repository
  Jaidev explores the code directly, so give the briefing extra context.
- Jaidev strips backticks, fenced code and `>` lines from the start comment
  before reading it (`stripBlockquotesAndCode` in jai-dev-agent-service;
  WAL-6301, ACC-1588, ACC-1638). Thread replies and plan feedback arrive
  intact. Jaidev plans v1 as soon as the start comment lands, without
  waiting for a thread reply. Split a briefed start across three posts, in
  this order, and ask Jaidev to quote key lines back:

  | Post | Holds | Where and when |
  |---|---|---|
  | Names comment | The Names table and code blocks up to ~20 lines | Top-level comment, posted first |
  | Start comment | The briefing, as prose and short lists | Second top-level comment, straight after the names comment |
  | Plan feedback | Every code block over ~20 lines, the base branch restated, and the names again when plan v1 still misses them | Reply in plan v1's thread |

- Put code in plain fenced blocks and keep every section expanded: a
  briefing in a `+++` collapsible reached Jaidev with its identifiers blanked.
- The "Evidence" section below holds the runs behind the three-post split.
- Implementation works from the plan's text (WAL-6301): code that must land verbatim
  goes in the plan in full, so ask Jaidev to include it.
- With `collectCoverage: true` and a global threshold in `jest.config.js`, a
  single-file `npx jest <file>` run fails the threshold even when its tests
  pass. Brief single-file runs with this command; a bare path under
  `--selectProjects unit` runs the whole suite (2,241 tests on accounting-service):

  ```bash
  npx jest --ci --coverage=false --runTestsByPath <file>
  ```

- Its GitHub token pushes code only; `.github/workflows/*` changes reach the
  branch through a human. A briefing that puts a workflow change in its
  definition of done ends Blocked.
- It runs one bounded single-file test process at a time and leaves the full
  suite and coverage thresholds to CI. It reports a briefed "run the full
  `npm test` and paste its summary" item as not done, even in an approved
  plan. Brief the full-suite result as "CI `test / Unit Test` passes" instead.
- A blocked run retries up to 5 times before reporting, and each attempt
  costs money whether or not anything changed.
- Each phase costs money (shown in the status comment). Clear briefings avoid
  question rounds, plan revisions and blocks.
- Its sandbox has no Docker. A unit-test project whose `globalSetup` starts a
  database container needs Docker; brief tests that mock the DB layer
  and leave the full run to CI.
- On a parent feature, Jaidev merges a moved base into its branch by default
  (ACC-1637, ACC-1638). A PR comment asking it to rebase onto the parent works:
  on ACC-1591 it replied in about 2 minutes, rebased with no conflicts,
  force-pushed and ran ts-lint and build. The request counts as a revision round
  (ACC-1591, ACC-1699, ACC-1701).
- A second PR into the parent can be refused with "Base branch was modified"
  right after a sibling PR merges (ACC-1630 and ACC-1633). One retry works when the
  files differ.
- It marks DB-backed tests it cannot run as environment-blocked (no Docker or
  database in its sandbox); CI `test / Unit Test` settles them.
- Its plan can raise the estimate (ACC-1633: 1 to 2 points) and the new value
  overwrites the Linear estimate.
- After the PR it posts a "Deploy this ticket" comment. The user deploys; agents
  leave the comment unanswered and leave `@jaidev deploy` to the user.
- ACC-1670: a plan feedback reply without `@jaidev` (20:56 UTC) drew no ack for 5.5 h; a one-line reply in the same thread starting `@jaidev please revise the plan per the feedback reply above` (02:31:17 UTC) drew "Plan feedback received" 23 s later, and plan v2 used the earlier reply in full. When a feedback reply gets no ack within 1 min, post that `@jaidev` line in the same thread.
- A correction posted while Jaidev is already writing the next plan version can be missed: on ACC-1636 plan v2 was posted before it read the correction in the v1 thread. Repeat the correction in the v2 thread (the next plan then carries it).
- Plan code blocks can carry literal `\n` text (ACC-1645 plan v2). Check the opened PR's source for stray `\n` sequences.
- Open GitHub approval bodies and Linear comments with `## <emoji>` section
  headers; comments starting with `@jaidev` follow the briefing format.
- A failed CI check starts a revision with no human comment, like SonarCloud findings do: on ACC-1697 a Unit Test coverage failure (99.99% of a 100% gate) drew a fix 38 min later as "Revision #3"; ACC-1701 did the same for coverage and SonarCloud. Jaidev's code caps CI-failure revisions at 2 per PR, so fix a third CI failure manually, with the user's approval.
- During a revision it can push a "WIP checkpoint" commit before the final push (ACC-1697); the PR is squash-merged, so review the final head only.
- After a GitHub review, the status comment changes to "Addressing PR Feedback..." within ~10 s, while the watcher's `pr-review-sent` stage can still fire `NO ACK` (ACC-1697). Read the status comment before acting on that event.

### Evidence

Runs behind the three-post split (Nov 2026):

- ACC-1666 and ACC-1667: a names thread reply held back for a first
  question never reached it; plan v1 on ACC-1667 said "I don't have the
  thread reply… the names in this plan are my own design".
- ACC-1668: planning began at 16:42:31 IST and the thread reply landed at
  16:43:26; plan v1 invented names and wrote the code as prose; planning
  cost $4.10.
- ACC-1669 (names comment, then 10 s later a start comment whose closing
  paragraph pointed to the comment above it): plan v1 used every name
  exactly, quoted the signature and reused the test-setup notes; planning
  cost $0.90. It still showed `development` as the base in the Affected
  Services table, cut Done-when to 4 of 8 criteria and described a class
  in prose; plan review checks all three.
- ACC-1669 plan v2 reported the names comment's long service-code section
  as outside its context, and rebuilt the class from the plan. The Names
  table and short code blocks reached it intact.
- ACC-1670 (names comment 22 s before the start comment): plan v1 reported
  the 45-line config block as "empty in the prompt" while the prose around
  it arrived. It also read `development` instead of the briefed parent
  branch, so its hit list named files the parent had already deleted.

## 6. Timings and costs

Kept outside the plugin, in `${JEEVES_MEMORY_DIR:-$HOME/.claude/memory}/jaidev-run-timings.md`. When it
exists, read it to estimate a run; otherwise skip the estimate. Add the new run's row to its cost
table when the run closes out, creating the file with that first row when it doesn't exist yet.

## 7. Run patterns

What past runs showed about revisions, start comments, merges and costs. Add or edit a pattern when a run shows something new; the per-run numbers stay in `jaidev-run-timings.md` (§6).

- **Plan revisions:** every run needed one plan revision ($0.33 to $0.69; v2 lands about 1.5 min after the feedback). WAL-6301 needed 3 (lost briefing, our code defect, our forward-compat change).
- **Blocks:** WAL-6298 only, on the workflow scope ($6.25 of its implementation cost).
- **Bare start (ACC-1700, ACC-1701, 21 Nov 2026):** a start comment holding only the trigger and the base-branch sentence gave no question round and one plan revision each, the same as briefed runs; plan v1 found the sibling tickets' names in the code on its own.
- **More than 3 PR revisions:** ACC-1701 ran Revision #4 (coverage CI fix, our rebase request, SonarCloud fix, then a no-op after approval), so the per-PR limit is not 3 rounds.
- **PR revisions:** 0 on ACC-1588, ACC-1594, ACC-1595, ACC-1633, ACC-1630, ACC-1637, ACC-1667, ACC-1669 and ACC-1670 (code given in full in the names reply, copied byte for byte). One each on ACC-1666 (built from the briefing prose without the names reply), WAL-6298 (SonarCloud), WAL-6300, WAL-6301, ACC-1638, ACC-1589 and ACC-1593 (SonarCloud duplication). Three on ACC-1591 (CI failure reply, our review of a circular import, our rebase request).
- **Prose-only start comment:** no question round (ACC-1589, ACC-1591, ACC-1594 and the follow-up wave); the names reply goes out as plan feedback. A briefing whose identifiers arrive blank costs one question round (ACC-1588).
- **Merges:** agents merged 14 to 58 min after the PR opened; most of that is CI and waiting for the user's "merge".
- **Estimates:** Jaidev can raise the estimate (ACC-1633, 1 to 2 points) and overwrite the Linear value.
- **Reading costs:** read final costs from the last status comment; earlier phase figures can rise later (WAL-6300 analysis $0.15 → $0.27).
- **Parent-branch race:** a second PR can be refused with "Base branch was modified" right after a sibling merges; one retry works when the files differ.
- **Test commands:** a bare test path under `--selectProjects unit` runs the whole suite, so briefings use `--runTestsByPath`.
