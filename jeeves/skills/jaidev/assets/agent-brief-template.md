# Shared brief for the Jaidev agents ({{BATCH_NAME}}: {{TICKETS}})

Copy this file to the scratchpad, fill every `{{...}}`, and delete the lines that do not apply. Agents work from the filled brief alone.

You run one Jaidev ticket end to end for the user, {{USER_NAME}}. {{N}} agents run in parallel, one per ticket, so keep to your own ticket.

## Context

- Repo: {{ORG/REPO}}. Parent branch: {{PARENT_BRANCH}} (pushed, at {{PARENT_SHA}}). Jaidev works on a branch jai-dev/<ticket-id-lowercase> cut from {{PARENT_BRANCH}}, and its PR targets {{PARENT_BRANCH}}.
- Route: {{HOW_PRS_REACH_THE_DEFAULT_BRANCH, e.g. the user merges each PR into the parent; the parent is squash-merged into <branch> at the end}}. The user is the only one who deploys and tests.
- Scope source: the Linear ticket and its comments. Decisions in force: {{ONE_LINE_PER_TICKET}}. Tickets outside this batch edit nearby files later; pull none of their scope into yours.
- Code to read first: {{FILES_AND_TESTS}}. Golden tests pin today's behaviour; a ticket that changes behaviour updates them and the PR calls the change out.
- Linear: use the mcp__claude_ai_Linear__* tools, or mcp__linear__* when that server is connected (load them with ToolSearch). Read the ticket, its comments and its relations. List comments with `limit: 1` (the status comment's timeline) and `limit: 2` only to read a new plan; a full list costs 5k to 25k tokens.
- Load the skill jeeves:jaidev and follow it: Ticket patterns, Write the briefing, Review the plan, Review the PR. Where this brief and the skill differ, this brief wins.
- Treat {{MAIN_CHECKOUT}} and every other worktree as read-only. Read code with:

  ```bash
  git -C {{MAIN_CHECKOUT}} fetch -q origin
  git -C {{MAIN_CHECKOUT}} show origin/{{PARENT_BRANCH}}:<path>
  ```
- In your prepare report, list every file your ticket changes, so the coordinator can confirm there is no overlap.

## Repo facts

{{PASTE_THE_REPO_SECTION_FROM_references/repo-notes.md}}

## Phase 1: prepare (do now, post nothing)

1. Read your ticket, its comments and the code on origin/{{PARENT_BRANCH}}.
2. Check every claim in the ticket against the code (paths, function names, helpers, repository methods, logger usage, test patterns). Run any command you put in an acceptance criterion in a scratch copy only (git worktree add in your scratchpad directory, then remove it), single test files with the command under "Repo facts".
3. Plan the names with the skill jeeves:typescript-naming, following its "During planning" steps: read the repo rules and the surrounding code, then settle a Names section (kind, name, file, purpose) and list renames separately, flagging any public contract. A ticket that adds no cross-file identifier says so.
4. Write TWO files to {{SCRATCHPAD}}:
   - <ticket-id>-briefing.md: the start comment in the jeeves:jaidev skill format, as prose and short lists. Write it as prose; identifiers, branch names, file paths, PR titles, code and inline backticks go in the names reply, because they arrive blank in a start comment. First line exactly: @jaidev start. State the start branch and the PR base as {{PARENT_BRANCH}} in the opening paragraph and again under Constraints. Keep every .github/workflows change out of Jaidev's scope and in the user's manual follow-up. Acceptance criteria are commands Jaidev can run (ts-lint, lint, named single test files with --coverage=false) plus the CI check names: test / Unit Test, test / Code Analysis, SonarCloud Code Analysis. Jaidev's sandbox has no Docker, so brief tests that mock the DB layer. Ask Jaidev to quote back one key signature and acceptance criterion 1, and to write the definitions from the names reply out in full in its Implementation Sequence.
   - <ticket-id>-names-reply.md: the thread reply after Jaidev's first question, and the plan feedback when Jaidev plans without asking. It holds a Names table, every code snippet, the exact acceptance-criteria commands, the base branch, the start branch and the PR title, all inside plain fenced blocks. PR title format: {{PR_TITLE_FORMAT, e.g. fix(ACC): [<ticket-id>] - <ticket title in the imperative>}}. Start the file with a ## section header per section.
5. Reply to the coordinator, then stop and wait: the two file paths, the Names table, the renames list, every place the briefing differs from the ticket text (with the reason), the files your ticket changes, the golden tests that change, and anything that depends on another ticket. Post nothing to Linear in this phase.

## Phase 2: run (when the coordinator sends "go")

1. Fetch origin, re-read origin/{{PARENT_BRANCH}} for changes since Phase 1, and update both files where they differ.
2. Post the briefing as a new top-level comment on your ticket (mcp__linear__save_comment). The user approved posting directly.
3. Your sandbox blocks sleep: wait for the coordinator's wake-up messages. When you wake, list the ticket's comments with `limit: 1` (the status comment's timeline), and with `limit: 2` only to read a new plan. When Jaidev asks its first question, answer in that question's thread with the names reply. Answer other questions from the ticket, the code and the user's rules; ask the coordinator when a decision is needed.
4. Plan review: when Jaidev posts "Implementation plan", compare it with your briefing and names reply item by item: base and PR target, quote-back, every Change and acceptance criterion word for word, the Done-when criteria, scope limited to your ticket, and each Key Assumption verified on origin/{{PARENT_BRANCH}}. Plan v1 usually needs one correction round (wrong base branch, invented names, reworded or missing Done-when, blank acceptance criteria): reply in the latest plan's thread with one correction listing the base branch, the Names table, every Done-when criterion word for word and the PR title in plain fenced blocks. Report the verdict to the coordinator; post exactly @jaidev plan:approved in the plan thread only after the coordinator confirms the user approved.
5. Run watch: tell the coordinator at once about a blocker or a "Blocked — Needs Human Help" comment, with the options. Post @jaidev resume in the Blocked thread only after the coordinator confirms.
6. PR review: the coordinator wakes you once all checks on the PR head are complete. From inside {{MAIN_CHECKOUT}}, read the result with the command below, then read .github/CODEOWNERS (if present) and the merge box. 

   ```bash
   gh pr view <n> --json headRefOid,mergeStateStatus,reviewDecision,statusCheckRollup --jq '{head: .headRefOid, merge: .mergeStateStatus, review: .reviewDecision, checks: [.statusCheckRollup[] | {n: (.name // .context), s: .status, c: (.conclusion // .state)}]}'
   ```

   Review the diff against the briefing's Changes, Constraints and acceptance criteria, using the PR's own file list: title format, identifiers against the Names table, tests and coverage, a diff clean of secrets and internal hostnames, a change inside your scope, the behaviour changes called out in the PR description, and that the branch merges cleanly into {{PARENT_BRANCH}}. Trace each finding through the code before reporting it. Keep the PR description to the change: behaviour, files and tests.
7. Corrections: post all findings as one GitHub review that opens each section with a ## <emoji> header. Jaidev gets 3 revision rounds in total; each review round uses one, SonarCloud findings included, and a rebase request counts as a round. After each push wait for CI and re-review. When the third round still falls short, stop and report.
8. Behind the parent: when another PR merges first and yours falls behind {{PARENT_BRANCH}}, ask Jaidev to rebase in a PR comment (## 🔁 header). A merge refused with "Base branch was modified" clears with one retry when the files differ.
9. When satisfied: confirm the head SHA still matches the one you reviewed and every check passed, then report "ready to merge". After the coordinator's "merge" message, run these (the squash commit title is the PR title):

   ```bash
   gh pr review <n> --approve
   gh pr merge <n> --squash
   ```

   When the merge needs approvals beyond the user's, or branch protection refuses, stop and report which.
10. After the merge: confirm the Linear ticket reached a completed state and report: PR link, merge commit, review rounds, Jaidev's cost from its status comment, timings (start comment to plan v1, plan approval to PR opened, PR opened to merged), and "Repo facts learned" (up to 5 bullets: commands, gotchas, patterns). Leave every other ticket's state as it is.

## Rules

- Post only in your own ticket's threads and PR. The user deploys; Jaidev's "Deploy this ticket" comment stays unanswered.
- Leave repository settings, branch protection, access and infrastructure to the user. Debug pods through Jenkins logs and OpenSearch.
- Run gh from inside {{MAIN_CHECKOUT}} (read-only gh commands; its branch stays as it is).
- Name scratch worktrees `wt-<ticket-id>-r<N>` with a new N each run, and remove them when you finish; earlier runs leave `wt-*` directories in the scratchpad.
- Run single test files. Before deleting a git lock, confirm that no git process is running.
- Write every commit message, PR comment and Linear comment per the user's authoring guide (load the authoring-guide skill once): short bullets, each fact its own line, commands in fenced blocks.
- Start every report with the status circle (🟢 progressing, 🟡 waiting for the user, 🔴 blocked or failing, ⚪ done or idle), then the verdict, then only what the coordinator needs to act on. Keep each report short.
