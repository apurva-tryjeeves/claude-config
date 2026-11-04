# PR description

Write the PR title and body to this structure. It follows accounting-service
PR #584 (`feat(ACC): [ACC-1587] - …`), the reference for a parent-ticket PR.
`SKILL.md` ("PR body format") holds the style rules: emoji headers, bold lead
terms, code formatting, tables.

## Title

```text
<type>(<SCOPE>): [<TICKET>] - <imperative outcome>
```

- **Type:** `feat`, `fix`, `chore`, `docs`, `refactor`, `perf` or `test`.
- **Scope:** the team key, e.g. `(ACC)`. Optional.
- **Ticket:** the PR's own ticket; a parent-ticket PR uses the parent id.
- **Outcome:** a sentence-case verb phrase saying what the change achieves.
  Join two outcomes with "and".

## Pick the shape

| PR | Sections |
|---|---|
| Single ticket, or a sub-ticket into a parent branch | Problem, Solution, References, How to test, Deployed to |
| Parent ticket into the default branch | All sections below, in order |

## Sections, in order

1. `## ❗ Problem`
   - One bold-lead bullet per distinct problem, 2–4 bullets.
   - A parent PR adds one `### <emoji> <Phase> · [<TICKET>](<url>): <title>`
     sub-heading per phase or sub-ticket, each with its own bullets.
2. `## 🛠️ Solution`
   - Open with one line naming the design doc, when there is one.
   - One bold-lead bullet per design decision, stated as the behaviour it
     gives (`- **Ports in, Codat out:** each service asks …`).
   - Name key paths in backticks; describe changes by behaviour, not as a
     file list.
   - A parent PR adds a table per phase:
     `| Step | Ticket | PR | State |`, with `✅ merged`, `✅ done` or
     `⏳ to do` in State.
3. `## 🔍 Code review` (parent PR)
   - One intro line, then `### 🧱 Design`, `### ⚠️ Behaviour changes made in
     review` and `### 🧹 Hygiene`, 3–5 bold-lead bullets each.
4. `## 🚦 Rollout` (parent PR, or any PR that needs deploy steps)
   - `### 📋 Before deploy`: `- [ ]` items that must hold first (queues,
     secrets, migrations, flags).
   - `### 🚀 On deploy`, `### 👀 First 48 hours` (what to watch and where)
     and `### ↩️ Rollback`.
5. `## 🔗 Related PRs` (when sibling PRs exist)
   - A table: `| PR | Covers | State |`, full GitHub URL per row, State as
     `🟢 open` or `✅ merged`.
6. `## 🔗 References`
   - Bold-lead bullets: parent ticket, related tickets, design doc (Notion
     link), next phases.
   - Link tickets inline: `[ACC-1558](https://linear.app/jeeves/issue/ACC-1558)`.
7. `## 🧪 How to test`
   - `### 🤖 Automated`: `- [x]` items for what passed, e.g. CI on the head
     commit and local lint commands in backticks.
   - `### 🧑‍🔬 Manual`, when a person tests: `- [ ]` steps with the expected
     result.
8. `## 🚀 Deployed to`
   - One bullet per environment, e.g. `` - `develop-07` ``; `- Not deployed`
     before deploy.

End the body with the session's attribution line.

## Skeleton: sub-ticket PR

```markdown
## ❗ Problem

- **<Lead>:** <what is wrong or missing today>

## 🛠️ Solution

- **<Decision>:** <behaviour it gives>, in `<key/path>`.

## 🔗 References

- **Ticket:** [<TICKET>](https://linear.app/jeeves/issue/<TICKET>)
- **Parent:** [<PARENT>](https://linear.app/jeeves/issue/<PARENT>)

## 🧪 How to test

### 🤖 Automated

- [x] `npx tsc --noEmit -p .` and `npm run lint` pass
- [x] CI: unit tests, Code Analysis and SonarCloud pass

## 🚀 Deployed to

- Not deployed
```
