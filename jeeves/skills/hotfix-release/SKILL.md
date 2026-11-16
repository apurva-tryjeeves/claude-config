---
name: hotfix-release
description: Cut a hot-fix branch off a Jeeves service's production branch (main/master), cherry-pick already-merged development commits onto it, and push it to origin. Trigger when asked to cut, cherry-pick or push a hot-fix branch; for the full hotfix release (branch, Notion release page, Slack drafts) use the hotfix-captain agent.
---

# Hotfix Release

Ship one or more already-merged fixes straight to production, bypassing the
normal release train. Run this from inside the target service's local repo
(`${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/<repo>`); a hotfix spanning
several repos gets one branch per repo.
The pushed `hot-fix/…` branch is the finished hotfix: deployment ships it as it
stands, with no pull request into `main`/`master`, so the flow stops at the push.

For the full release-captain process — branch, Notion release page and Slack
drafts — run the `hotfix-captain` agent; it calls this skill for the branch.

## 1. Find the production branch

Record the current branch as `PREV_BRANCH`, so step 4 can return to it, and
list any local changes:

```bash
PREV_BRANCH=$(git branch --show-current)
```

```bash
git status --short
```

Start from a clean working tree. When `git status --short` lists changes, show
the user that list, then wait for the user's yes before stashing them; step 4
restores the stash:

```bash
git stash push -u -m "before hot-fix <ticket-id>"
```

Fetch, then take the production branch from whichever of `origin/main` and
`origin/master` has the newer tip — some repos keep a years-old `main` beside a
live `master` (wallet-service, billpay-service):

```bash
git fetch origin
for b in main master; do
  git rev-parse --verify --quiet "origin/$b" >/dev/null && \
    printf '%s %s %s\n' "$(git log -1 --format=%ct "origin/$b")" "$b" "$(git log -1 --format='%cs %h %s' "origin/$b")"
done | sort -rn | head -1
```

Show the user the chosen branch with its last commit date and subject, and
confirm it before going further. Set `PROD_BRANCH` to the confirmed name.

## 2. Get the commits to hotfix

Ask the user for every pull request (link or number) going into this hotfix,
then read each one's squashed commit — the `mergeCommit` is the exact commit
that landed in `development`:

```bash
gh pr view <pr-number> --json number,title,state,baseRefName,mergeCommit,mergedAt
```

Confirm each PR is `MERGED` with `baseRefName` `development`. A sub-ticket PR
merged into a parent integration branch (`feat/<PARENT>`) has not reached
`development` — hotfix the parent PR's commit instead. Check the commit is on
`development`:

```bash
git merge-base --is-ancestor <mergeCommit-oid> origin/development && echo on-development
```

To cross-check by subject, match the PR number in parentheses so `#54` does not
also match `#540`:

```bash
git log --oneline origin/development | grep "(#<pr-number>)"
```

Order the commits by `mergedAt`, oldest first — step 4 cherry-picks them in
that order.

## 3. Create the hot-fix branch

For a single PR, derive `<ticket-id>` and `<context>` from its commit's
subject line, which follows the repo's `<type>: [<TICKET-ID>] - <description>`
convention:

- `<ticket-id>` — the bracketed ticket reference, e.g. `ACC-1494`.
- `<context>` — a short kebab-case slug from `<description>`, e.g.
  `add-accounting-category-filters`. Keep it to 3-5 words.

For multiple PRs, derive a default and confirm it with the user:

- `<ticket-id>` — each commit's ticket id joined with `_` in merge order, e.g.
  `ACC-1497_ACC-1494`.
- `<context>` — a 3-5 word slug from the first commit's subject.

Show the resulting branch name, then wait for the user's yes or a
replacement before creating it.

If a commit subject doesn't carry a bracketed ticket ID, ask the user for
the ticket ID and context slug directly.

Branch from the fetched production branch, leaving your local branches as
they are:

```bash
git switch -c hot-fix/<ticket-id>_<context> --no-track "origin/$PROD_BRANCH"
```

## 4. Cherry-pick and push

Cherry-pick each commit in the order it landed in `development` — oldest
first — to keep conflicts to a minimum:

```bash
git cherry-pick <commit-sha-1>
git cherry-pick <commit-sha-2>
```

On a conflict, resolve it the same way as any rebase conflict: read both
sides in full and combine the intent of each — most hotfix conflicts are the
production branch missing later refactors that development already has.
Stage the resolved files and continue before moving to the next commit:

```bash
git add <resolved-files>
git cherry-pick --continue
```

Show the user the branch name, its base (`origin/$PROD_BRANCH` and its tip),
and the picked commits, and push once they confirm:

```bash
git push -u origin hot-fix/<ticket-id>_<context>
```

After the push, switch back to `PREV_BRANCH`, and restore the stash when
step 1 made one:

```bash
git switch "$PREV_BRANCH"
```

```bash
git stash pop
```

When the user declines the push, return the repo to where it started: switch
back to `PREV_BRANCH`, delete the local hot-fix branch, and restore the stash
when step 1 made one:

```bash
git switch "$PREV_BRANCH"
```

```bash
git branch -D hot-fix/<ticket-id>_<context>
```

```bash
git stash pop
```

## 5. Reporting results

Icons, linking and value-rendering vocabulary live in the shared
`${CLAUDE_PLUGIN_ROOT}/references/output-style.md` — follow it rather than inventing a format.

- **Lead with a verdict line** — icon, the pushed branch, and the commit count:
  `✅ pushed hot-fix/ACC-1494_add-category-filters · 2 commits`.
- **Table the cherry-picks** — columns `Commit` (short sha linked to
  `https://github.com/JeevesInc/<repo>/commit/<sha>`), `Subject`, and `Result`
  (✅ applied clean · ⚠️ conflict resolved), one row per commit in pick order.
- **Link the branch** so it opens in one click:
  `https://github.com/JeevesInc/<repo>/tree/hot-fix/<ticket-id>_<context>`.

Answer with the verdict, the table and
the branch link, then stop — leave out the git commands run, diff stats, and
"want me to open the PR?" follow-ups.
