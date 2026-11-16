# PR naming review workflow

## 1. Scope to the PR

```bash
git fetch origin
BASE_BRANCH=$(gh pr view --json baseRefName -q .baseRefName)
BASE=$(git merge-base HEAD "origin/$BASE_BRANCH")
git diff --name-only "$BASE"...HEAD
git diff "$BASE"...HEAD
```

- Work on identifiers this PR adds or modifies.
- Leave identifiers on unchanged lines as they are.
- On a fix request, rename an identifier introduced in this PR and update every reference, including call sites outside the diff.
- On a review request, list the proposed renames and leave the code unchanged.

## 2. Apply the conventions

Check each new or changed identifier against `SKILL.md`, in its order of precedence.

## 3. Update docs

On a fix request, bring every doc that mentions a renamed identifier in line with the new name: README, `docs/*.md`, `AGENTS.md`, JSDoc/TSDoc, OpenAPI descriptions, and comments on changed lines.

## 4. Verify

On a fix request, run the repo's typecheck, lint and tests (see `package.json` scripts) and confirm they pass.

## Reporting results

Follow the reporting rule in `SKILL.md`.
