---
name: git-preferences
description: Personal git/PR preferences for JeevesInc repos — commit style (Linear ticket refs), branch strategy (including a parent-ticket integration branch for sub-issues that ship together), PR creation, and post-create polling. Invoke when doing git operations or creating/updating PRs in a JeevesInc repo, or when the user gives JeevesInc git-related guidance to remember.
---

# Git Preferences

Personal git and PR preferences. This is a living list — add new guidance here as it's given.

## Branch Strategy

- Most Jeeves services use `development` as the main branch; some use `main`. Look up the repo's default branch:
  ```bash
  gh repo view JeevesInc/<repo> --json defaultBranchRef -q .defaultBranchRef.name
  ```
- Start every new branch from an up-to-date local copy of its base: switch to the base, fast-forward it from origin, then branch from it. `--ff-only` stops the pull when the local base has drifted from origin, so it never gains a merge commit:
  ```bash
  git switch <default-branch>
  git pull --ff-only origin <default-branch>
  git switch -c <type>/<TICKET>
  ```

### Parent ticket whose sub-issues ship together

When a Linear parent ticket's sub-issues go live together (e.g. `ACC-1555` with sub-issues `ACC-1557`, `ACC-1561`, …), collect them on one integration branch named after the parent, and ship that branch to the default branch as one PR. A ticket without such a parent branches off the default branch as above.

| Branch | Created from | PR base | Merge |
|---|---|---|---|
| `feat/<PARENT>` (e.g. `feat/ACC-1555`) | the default branch | the default branch, once every sub-issue is in | Squash |
| `feat/<SUB>` (e.g. `feat/ACC-1557`) | `feat/<PARENT>` | `feat/<PARENT>` | Squash |

1. Create and push the parent branch once, from the updated local default branch:
   ```bash
   git switch <default-branch>
   git pull --ff-only origin <default-branch>
   git switch -c feat/<PARENT>
   git push -u origin feat/<PARENT>
   ```
2. Start each sub-ticket from the updated local parent branch:
   ```bash
   git switch feat/<PARENT>
   git pull --ff-only origin feat/<PARENT>
   git switch -c feat/<SUB>
   ```
3. Open each sub-ticket PR against the parent branch, titled with the sub-ticket's id (see **Create a PR**):
   ```bash
   gh pr create --repo JeevesInc/<repo> --base feat/<PARENT> --head feat/<SUB> \
     --title "feat: [<SUB>] - <description>" --body-file <body.md>
   ```
4. Keep the parent branch current by rebasing it onto the default branch, then rebase every open sub-branch onto the new parent tip. Record the parent's tip before the rebase, so each sub-branch replays only its own commits:
   ```bash
   git switch <default-branch>
   git pull --ff-only origin <default-branch>

   git switch feat/<PARENT>
   OLD_PARENT=$(git rev-parse feat/<PARENT>)
   git rebase <default-branch>
   ```
   Confirm with the user before each force-push — the parent branch carries every merged sub-PR and is the base of every open one:
   ```bash
   git push --force-with-lease origin feat/<PARENT>
   ```
   Then, for each open sub-branch, rebase and (after confirming) force-push:
   ```bash
   git switch feat/<SUB>
   git rebase --onto feat/<PARENT> "$OLD_PARENT"
   git push --force-with-lease origin feat/<SUB>
   ```
5. Once every sub-issue PR is squashed into the parent branch, open the parent PR against the default branch, titled with the parent's id. List each sub-issue PR in its description, then squash-merge it.

**Stacked-branch gotchas:**
- Parallel sub-branches that each inject the same dependency into one service merge cleanly but break `tsc`. After each merge, rebase the remaining sub-branches and run `tsc` before merging the next.
- Retarget dependent PRs before deleting their base branch; deleting the base closes them:
  ```bash
  gh pr edit <n> --base <new-base>
  ```
- To reopen a closed PR whose branch was force-pushed: push the branch back to its SHA at close, reopen the PR, then push the new SHA.

## Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) spec with a Linear ticket reference:

```text
<type>: [<ticket-id>] - <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat:`, `fix:`, `docs:`, `refactor:`, `perf:`, `test:`, `chore:` — the set the repos' `lint / Validate PR title` check accepts.

**Examples:**
```bash
git commit -m "feat: [ENG-456] - Add Slack notification integration"
git commit -m "fix: [ENG-789] - Resolve transaction processing race condition"
```

**Co-authoring with Claude:** take the trailer verbatim from the session's own
attribution guidance, so it names the model that actually wrote the commit:
```text
feat: [ENG-123] - Implement feature

Co-Authored-By: <the session's own Claude model> <noreply@anthropic.com>
```

**Reasoning:** put the "why" of a small, self-contained change in the commit message or PR body, and keep the code free of explanatory comments. Reserve an inline comment for a workaround for a specific external bug or a non-obvious invariant.

## Create a PR

Jeeves repos squash-merge, so the PR title becomes the commit subject on the base branch. Every repo runs `lint / Validate PR title` (`infra-reusable-workflows` → `pr-title.yml`), which accepts:

| Part | Allowed |
|---|---|
| Type | `fix`, `feat`, `chore`, `docs`, `refactor`, `perf`, `test` (optional scope, e.g. `feat(ACC):`) |
| Subject | starts with the bracketed ticket id `[ABC-123]` (2–6 capitals, a dash, digits), then the description |

1. Push the branch, then open the PR against the default branch (or the parent branch for a sub-ticket), with the title in the commit format and a body file:
   ```bash
   gh pr create --repo JeevesInc/<repo> --base <default-branch> --head <branch> \
     --title "<type>: [<TICKET>] - <description>" --body-file <body.md>
   ```
2. Add a `## 🔗 Related PRs` section when the change spans repos (below).
3. Offer the pollers (see **PR Post-Create Polling**).

### PR body format

Write every PR description, PR comment and review summary in this style:

- Start each section with a `## <emoji> Header`, one emoji per header. Use the repo's PR template sections:
  `## ❗ Problem`, `## 🛠️ Solution`, `## 🔗 References`, `## 🧪 How to test`, `## 🚀 Deployed to`.
- Use `- [ ]` task lists for test steps and follow-ups.
- Bold each bullet's lead term.
- Put names, paths and commands in `code`.
- Use a table for anything with repeating columns.
- Wrap long logs in `<details>`.
- Describe the change itself. Keep rebase and cherry-pick mechanics, stacking banners and commit SHAs in the branch graph.
- Point to other work only through `## 🔗 Related PRs`.
- Cherry-pick with plain `git cherry-pick` (no `-x`) for commits that land in a PR.

## Cross-Repo Related PRs

When a change spans PRs in different repos, link each PR to the others in its description. Add a `## 🔗 Related PRs` section listing every sibling PR as a full link with a one-line note on what it covers:

```markdown
## 🔗 Related PRs
- https://github.com/JeevesInc/jeeves-web/pull/3739 — reads the renamed provider columns
```

Once the sibling PR exists, update the earlier PR's description too, so every PR links to all the others:

```bash
gh pr edit <n> --repo JeevesInc/<repo> --body-file <updated-body.md>
```

## PR Post-Create Polling

After creating a pull request, or pushing to a branch that already has an open PR, ask before starting any background poller. Each poller runs per-PR and stops itself.

### Ask which poller(s) to start

Call `AskUserQuestion` (multiSelect) offering **Comments poller** and **Checks poller**, and start only the one(s) picked.

### Comments poller

Watches for review/PR comments that need a response.

- Cadence: every 2 hours, 10:00–22:00 in the user's local time. Create it with `CronCreate` using `0 10-22/2 * * *` — cron fires in the machine's local timezone, so the window follows the user.
- On a new comment needing a response (review comment, requested change, question), notify with a summary.
- On-demand: when asked "any PR comments?", pull status immediately regardless of schedule.
- Stop when the PR is merged or closed.
- Detect new comments by diffing all three sources against the last check — conversation comments and review summaries:
  ```bash
  gh pr view <n> --repo JeevesInc/<repo> --json state,comments,reviews
  ```
  and inline code-review comments, which live on a separate endpoint paged at 30 — `--paginate` returns all of them:
  ```bash
  gh api --paginate repos/JeevesInc/<repo>/pulls/<n>/comments --jq '.[] | {id, user: .user.login, path, line, body, created_at}'
  ```

### Checks poller

Watches CI/check status until it settles.

- Cadence is per-repo. Check `references/ci-check-timing.md` (the source clone's copy first — see **Write back a timing row**) for a row matching the target repo; when one exists, use its `First check`/`Interval` columns directly.
- For a repo with no row yet, derive the cadence from that repo's own CI history with a background `Agent` instead of asking the user. Pull the last 10 successful PR runs of each PR-check workflow:
  ```bash
  gh run list --repo JeevesInc/<repo> --workflow <file> --status success --event pull_request --limit 10 --json createdAt,updatedAt \
    --jq '[.[] | ((.updatedAt|fromdateiso8601) - (.createdAt|fromdateiso8601)) | select(. < 7200)] | "n=\(length) min=\(min)s max=\(max)s mean=\(add/length|floor)s"'
  ```
  Set `First check` a little under the fastest duration and `Interval` from the spread between fastest and slowest, then add the row (repo, long-pole workflow, check name, min/max/mean, sample size, first check, interval) per **Write back a timing row** below, and start polling once the agent reports back.
- After checks settle, if the actual settle time differs noticeably from the remembered cadence, refine that repo's row in the same turn, per **Write back a timing row**.
- Use `/loop`'s dynamic mode (`ScheduleWakeup`) for the recurring execution, including when asked to "run in the background" or "move to background" — it re-invokes the session each interval, so every tick is a fresh check.
- Poll with `statusCheckRollup`, which exits 0 while checks are still running:
  ```bash
  gh pr view <n> --repo JeevesInc/<repo> --json statusCheckRollup --jq '.statusCheckRollup[] | {name, status, conclusion}'
  ```
- Stop once every check has `status: COMPLETED` **and** every check in the row's `Settles on` column is in the list — on repos using the shared unit-test workflow that is `test / Scan for secrets` and `SonarCloud Code Analysis`. The workflow creates `test / Code Analysis` and `test / Scan for secrets` only after the job before them finishes, so an all-COMPLETED list missing them is mid-handoff — keep polling. Then report per **Report findings** below.
- A failing check here often traces back to the SonarCloud quality gate — see the `jeeves:sonar-proactive-rules` skill for what triggers it, and `/jeeves:sonar-fix` to clear it.

### Write back a timing row

Edit the source clone of the plugin, not the installed skill copy:

```bash
${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}/jeeves/skills/git-preferences/references/ci-check-timing.md
```

Leave the edit uncommitted and tell the user it is ready to review and push. When that directory doesn't exist, report the new row and the proposed edit instead. Read the source clone's copy of the table when it exists, else this skill's own `references/ci-check-timing.md`.

## Report findings

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it for every report.

**Checks poller:**

- **Lead with the PR** — its number as a link, carrying the state icon:
  `✅ [#534](https://github.com/JeevesInc/<repo>/pull/534) merged`.
- **Table the checks** — columns `Check`, `Status` (icon + conclusion) and
  `Duration` (human-readable, `4m12s`), one row per check.
- **On a failure, list only the failing checks** and fence the handful of log
  lines naming the cause; the passing ones stay off the table.
- **While checks still run**, give elapsed against the expected settle time from
  `references/ci-check-timing.md`: `⏳ 2m10s elapsed · ~6m expected`.

**Comments poller:**

- **Lead with the PR** as a link and the count of new comments.
- **One bullet per new comment** — author, `file:line` for inline comments, and
  a one-line summary of what it asks for.

Answer with the verdict line and the table or bullets, then stop — leave out the
`gh` commands run, the diff summary, and "want me to keep polling?" follow-ups.
