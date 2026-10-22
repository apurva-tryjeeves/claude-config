# PR naming review workflow

## 1. Scope to the PR

```bash
git fetch origin
BASE=$(git merge-base HEAD origin/main)   # use the PR's actual base branch
git diff --name-only "$BASE"...HEAD
git diff "$BASE"...HEAD
```

- Work on identifiers this PR adds or modifies.
- Leave identifiers on unchanged lines as they are.
- When renaming an identifier introduced in this PR, update every reference, including call sites outside the diff.

## 2. Apply the conventions

Check each new or changed identifier against `SKILL.md`, in its order of precedence.

## 3. Update docs

Bring every doc that mentions a renamed identifier in line with the new name: README, `docs/*.md`, `AGENTS.md`, JSDoc/TSDoc, OpenAPI descriptions, and comments on changed lines.

## 4. Verify

Run the repo's typecheck, lint and tests (see `package.json` scripts) and confirm they pass.

## Reporting results

Reply with exactly:

1. Table: `File | Old name | New name | Rule applied`
2. Recommendations for public-contract names kept unchanged
3. Verification commands run and their pass status

When nothing needed renaming, reply with one line saying so plus the verification status.

Keep the reply to these items; usage examples, restated conventions and closing questions stay out. Add one line when a check fails for a reason outside this PR, naming the failing check and its cause.

authoring-guide: v4
