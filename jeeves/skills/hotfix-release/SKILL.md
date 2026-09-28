---
name: hotfix-release
description: Cut a hot-fix branch off a Jeeves service's production branch (main/master), cherry-pick one or more already-merged development commits onto it, and push it to origin. Trigger on hotfix, urgent release, or shipping a fix out-of-band from the normal development→release flow.
---

# Hotfix Release

Ship one or more already-merged fixes straight to production, bypassing the
normal release train. Run this from inside the target service's local repo.

## 1. Sync local branches with origin

Identify the production branch — `main` if it exists, else `master`:

```bash
git fetch origin
git rev-parse --verify --quiet origin/main >/dev/null 2>&1 && PROD_BRANCH=main || PROD_BRANCH=master
```

Reset both branches to exactly match origin:

```bash
for branch in development "$PROD_BRANCH"; do
  git checkout "$branch"
  git reset --hard "origin/$branch"
done
```

If either checkout hits uncommitted local changes unrelated to this hotfix,
stash them first, then restore after pushing the hotfix branch, the same way
as any other branch switch:

```bash
git stash push -u -m "<note>"
```

## 2. Get the commits to hotfix

Ask the user for every pull request (link or number) going into this hotfix,
then find each one's **actual** commit in `development`'s history:

```bash
git log --oneline origin/development -5
```

Each PR shows up tagged with `(#<pr-number>)` in that log. Cherry-pick that
SHA — it's the squashed commit that actually landed in `development`. Note
the order the commits appear in the log (newest first) — step 4 cherry-picks
them in the reverse order, oldest first.

Use `gh pr view` for context only (title, merge state): it lists the PR's
pre-squash commits, which stay on the PR's own branch and never land in
`development` as standalone commits.

```bash
gh pr view <pr-number> --json title,mergeCommit,commits,baseRefName,state
```

For an older or unusually-delayed hotfix, widen the search:

```bash
git log --oneline origin/development | grep "#<pr-number>"
```

## 3. Create the hot-fix branch

For a single PR, derive `<ticket-id>` and `<context>` from its commit's
subject line, which follows the repo's `<type>: [<TICKET-ID>] - <description>`
convention:

- `<ticket-id>` — the bracketed ticket reference, e.g. `ACC-1494`.
- `<context>` — a short kebab-case slug from `<description>`, e.g.
  `add-accounting-category-filters`. Keep it to 3-5 words.

For multiple PRs, ask the user for a combined `<ticket-id>` (e.g.
`ACC-1497_ACC-1494`) and a `<context>` slug covering all the fixes — the
branch name can't be derived automatically once more than one commit is
involved.

If a commit subject doesn't carry a bracketed ticket ID, ask the user for
the ticket ID and context slug directly.

Branch from the production branch:

```bash
git checkout -b hot-fix/<ticket-id>_<context> "$PROD_BRANCH"
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

Push the branch straight to origin:

```bash
git push -u origin hot-fix/<ticket-id>_<context>
```

## 5. Report the result

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

- **Lead with a verdict line** — icon, the pushed branch, and the commit count:
  `✅ pushed hot-fix/ACC-1494_add-category-filters · 2 commits`.
- **Table the cherry-picks** — columns `Commit` (short sha linked to
  `https://github.com/JeevesInc/<repo>/commit/<sha>`), `Subject`, and `Result`
  (✅ applied clean · ⚠️ conflict resolved), one row per commit in pick order.
- **Link the branch** so it opens in one click, using the PR-create URL against
  the production branch:
  `https://github.com/JeevesInc/<repo>/compare/<prod-branch>...hot-fix/<ticket-id>_<context>?expand=1`.

That hands the branch off to deployment. Answer with the verdict, the table and
the branch link, then stop — leave out the git commands run, diff stats, and
"want me to open the PR?" follow-ups.
