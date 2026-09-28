---
name: git-preferences
description: Personal git/PR preferences for JeevesInc repos — commit style (Linear ticket refs), branch strategy, PR creation, and post-create polling. Invoke when doing git operations or creating/updating PRs in a JeevesInc repo, or when the user gives JeevesInc git-related guidance to remember.
---

# Git Preferences

Personal git and PR preferences. This is a living list — add new guidance here as it's given.

## Branch Strategy

- Most Jeeves services use `development` as the main branch; some use `main`. Look up the repo's default branch:
  ```bash
  gh repo view JeevesInc/<repo> --json defaultBranchRef -q .defaultBranchRef.name
  ```
- Pull that branch before starting work:
  ```bash
  git pull origin <default-branch>
  ```

## Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) spec with a Linear ticket reference:

```text
<type>: [<ticket-id>] - <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, `chore:`

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

## Cross-Repo Related PRs

When a change spans PRs in different repos, link each PR to the others in its description. Add a `## Related PRs` section listing every sibling PR as a full link with a one-line note on what it covers:

```markdown
## Related PRs
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
  and inline code-review comments, which live on a separate endpoint:
  ```bash
  gh api repos/JeevesInc/<repo>/pulls/<n>/comments --jq '.[] | {id, user: .user.login, path, line, body, created_at}'
  ```

### Checks poller

Watches CI/check status until it settles.

- Cadence is per-repo. Check `references/ci-check-timing.md` for a row matching the target repo first; when one exists, use its `First check`/`Interval` columns directly.
- For a repo with no row yet, derive the cadence from that repo's own CI history with a background `Agent` instead of asking the user. Pull the last 10 completed runs of each PR-check workflow:
  ```bash
  gh run list --repo <repo> --workflow <file> --limit 10 --json createdAt,updatedAt,conclusion,event
  ```
  Compute each run's duration (`updatedAt - createdAt`), then set `First check` a little under the fastest observed duration and `Interval` from the spread between fastest and slowest. Have the agent add a new row to `references/ci-check-timing.md` (repo, long-pole workflow, check name, min/max/mean, sample size, first check, interval), then start polling once it reports back.
- After checks settle, if the actual settle time differs noticeably from the remembered cadence, update that repo's row in `references/ci-check-timing.md` with the refined value.
- Use `/loop`'s dynamic mode (`ScheduleWakeup`) for the recurring execution, including when asked to "run in the background" or "move to background" — it re-invokes the session each interval, so every tick is a fresh check.
- Poll with `statusCheckRollup`, which exits 0 while checks are still running:
  ```bash
  gh pr view <n> --json statusCheckRollup --jq '.statusCheckRollup[] | {name, status, conclusion}'
  ```
- Stop as soon as every check has `status: COMPLETED`, then report per **Report findings** below.
- A failing check here often traces back to the SonarCloud quality gate — see the `sonar-proactive-rules` skill for what triggers it, and `/jeeves:sonar-fix` to clear it.

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
