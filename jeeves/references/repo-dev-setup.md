# Repo dev setup

How to build, test and commit in each JeevesInc repo from a ticket worktree. The `ticket-workflow` agents read this before running anything in a repo.

Check the repo's row first. When a repo has no row, or a value proves wrong, derive it from the repo (`.nvmrc`, `package.json` scripts, `.jest/`, `.husky/`) and add or fix the row in the same turn, following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.

## Ticket worktree

One worktree per ticket at `<repo>/.claude/worktrees/<ticket-lowercase>`, on branch `feat/<TICKET>` cut from the parent branch with no upstream, so every push names its target:

```bash
cd ~/github/JeevesInc/<repo>
grep -qx '.claude/worktrees/' .git/info/exclude || echo '.claude/worktrees/' >> .git/info/exclude
git fetch origin
git worktree add --no-track -b feat/<TICKET> .claude/worktrees/<ticket-lowercase> origin/<parent-branch>
```

When the worktree exists, reuse it if `git -C <worktree> branch --show-current` prints `feat/<TICKET>`; otherwise report the branch it holds. Then run the repo's "Worktree setup" from the table, inside the worktree.

## Repos

| Repo | Unit / e2e test | Type-check and lint | E2e database | Worktree setup | Known local failures |
|---|---|---|---|---|---|
| `accounting-service` (Node 22.23.4) | `NODE_ENV=test fnm exec --using 22.23.4 npx jest <path> --selectProjects unit` (or `e2e`) | `fnm exec --using 22.23.4 npx tsc --noEmit -p tsconfig.json`; `fnm exec --using 22.23.4 npx eslint <files>`; `fnm exec --using 22.23.4 npx prettier --check <files>` | `.jest/globalSetup.ts` starts a `mysql:8.0.35` testcontainer; start Docker first | `ln -s ~/github/JeevesInc/accounting-service/node_modules node_modules`; `cp -R ~/github/JeevesInc/accounting-service/.husky/_ .husky/` (the pre-commit hook sources `.husky/_/husky.sh`) | `server.test.ts` and 8 controller e2e suites fail with `Configuration property "auth.publicKeyBase64EncodedInput" is not defined`; count them as known failures |
