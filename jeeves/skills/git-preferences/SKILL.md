---
name: git-preferences
description: JeevesInc git and PR conventions — branch strategy (including a parent-ticket integration branch), commit and PR titles, PR descriptions, PR comment and CI pollers. Invoke when doing git operations or creating or updating PRs in a JeevesInc repo, when asked to rebase or sync a feature branch onto its default branch, or when the user gives JeevesInc git guidance to remember.
---

# Git Preferences

JeevesInc git and PR conventions. When the user gives new guidance, add it to
this file, following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.

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

When a Linear parent ticket's sub-issues go live together, collect them on one
`feat/<PARENT>` integration branch and ship it to the default branch as one PR. Read
`references/parent-ticket-branches.md` before creating, rebasing or merging a parent or
sub-ticket branch.

## Conventional Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) spec with a Linear ticket reference:

```text
<type>: [<ticket-id>] - <description>

[optional body]

[optional footer(s)]
```

**Types:** the set in the **Create a PR** table, which the repos' `lint / Validate PR title` check accepts.

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

**Cherry-picks:** use plain `git cherry-pick` (no `-x`) for commits that land in a PR.

## Create a PR

Jeeves repos squash-merge, so the PR title becomes the commit subject on the base branch. Every repo runs `lint / Validate PR title` (`infra-reusable-workflows` → `pr-title.yml`), which accepts:

| Part | Allowed |
|---|---|
| Type | `fix`, `feat`, `chore`, `docs`, `refactor`, `perf`, `test` (the check also accepts a scope, e.g. `feat(ACC):`) |
| Subject | starts with the bracketed ticket id `[ABC-123]` (2–6 capitals, a dash, digits), then the description |

Write the title without a scope, so every PR title reads the same (`references/pr-description.md` → "Title").

1. Offer three or four meaningful titles per "Write the outcome" in `references/pr-description.md`, each with its character count, and use the one the user picks.
2. Show the whole description as raw markdown in a ` ````markdown ` fence, with the chosen title above it, and post only after the user approves it. Apply the same review to `gh pr edit --title` and `--body-file` on an existing PR.
3. Push the branch, then open the PR against the default branch (or the parent branch for a sub-ticket), with the approved title and body file:
   ```bash
   gh pr create --repo JeevesInc/<repo> --base <default-branch> --head <branch> \
     --title "<type>: [<TICKET>] - <outcome>" --body-file <body.md>
   ```
4. Add a `## 🔗 Related PRs` section when the change spans repos (below).
5. Offer the pollers (see `references/pr-pollers.md`).

### PR body format

Write the PR title and the description's sections to the structure in `references/pr-description.md` (sub-ticket and parent-ticket shapes, with a skeleton). Write every PR description, PR comment and review summary in the shared style (`${CLAUDE_PLUGIN_ROOT}/references/output-style.md`, "Posted markdown style"), with these GitHub specifics:

- Use the repo's PR template sections:
  `## ❗ Problem`, `## 🛠️ Solution`, `## 🔗 References`, `## 🧪 How to test`, `## 🚀 Deployed to`.
- Wrap long logs in `<details>`.
- Put a merge or deploy gate in a GitHub alert (`> [!IMPORTANT]` or `> [!WARNING]`) at the top of `## 🚦 Rollout`, followed by its checklist.
- Describe the change itself. Keep rebase and cherry-pick mechanics, stacking banners and commit SHAs in the branch graph.
- Point to PRs in other repos only through `## 🔗 Related PRs`. A parent-ticket PR lists its sub-ticket PRs in its Solution tables.

## Sync a feature branch onto the default branch

Show the plan first: per repo, the current branch, how far local `<default>` is behind origin,
the feature branch's own commit count, the default-branch commits it will pick up, and the
commands. Run nothing until the user approves it.

```bash
cd ~/github/JeevesInc/<repo>
git switch <default-branch>
git pull --ff-only origin <default-branch>
git switch <feature>            # git switch -c <feature> --track origin/<feature> when it isn't local
git rebase <default-branch>
git push --force-with-lease origin <feature>
```

- Start only from a clean working tree; report a dirty one and skip that repo.
- On a rebase conflict, stop, list the conflicted files, and wait for the user.
- Force-push only with `--force-with-lease`, and only after the user approves the plan.
- Report a table: PR link, new head, commits replayed, behind-default count (0 after a clean run).
- After the push, note that dev environments still run the old head until redeployed, and that an
  approval given before the new commits may need a fresh review.

## Cross-Repo Related PRs

When a change spans PRs in different repos, link each PR to the others in its description. Add a `## 🔗 Related PRs` table listing every sibling PR as a full link, what it covers, and its state:

```markdown
## 🔗 Related PRs

| PR | Covers | State |
|---|---|---|
| https://github.com/JeevesInc/jeeves-web/pull/3739 | Reads the renamed provider columns | 🟢 open |
```

Once the sibling PR exists, update the earlier PR's description too, so every PR links to all the others:

```bash
gh pr edit <n> --repo JeevesInc/<repo> --body-file <updated-body.md>
```

## PR Post-Create Polling

After creating a PR, or pushing to a branch with an open PR, ask before starting any
background poller, then follow `references/pr-pollers.md`: the comments and checks
pollers, their cadence, the CI timing rows in
`~/.claude/org-memory/jeevesinc/ci-check-timing.md`, and the poller report format.

## Reporting results

Icons, linking and value-rendering vocabulary live in the shared
`${CLAUDE_PLUGIN_ROOT}/references/output-style.md` — follow it for every report.

**PR status:**

- When the approving review's `commit_id` predates the head, say so: the approval was given on
  `<sha>` before the latest commits.

Answer with the verdict line and the table or bullets, then stop — leave out the
`gh` commands run, the diff summary, and "want me to keep polling?" follow-ups.
