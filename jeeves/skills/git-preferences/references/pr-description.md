# PR description

Write the PR title and body to this structure. It follows accounting-service
PR #584 (ACC-1587), the reference for a parent-ticket PR.
`${CLAUDE_PLUGIN_ROOT}/references/output-style.md` ("Posted markdown style")
holds the style rules: emoji headers, bold lead terms, code formatting, tables;
`SKILL.md` ("PR body format") adds the GitHub-only elements.

Section headers and order follow ${CLAUDE_PLUGIN_ROOT}/references/doc-spine.md;
the PR-only sections (Code review, Related PRs, Deployed to) sit where this file places
them.

## Title

```text
<type>: [<TICKET>] - <imperative outcome>
```

- **Type:** one from the Type row of the `SKILL.md` "Create a PR" table.
- **Scope:** write the title without one, so every PR title reads the same.
- **Ticket:** the PR's own ticket; a parent-ticket PR uses the parent id.
- **Outcome:** a sentence-case verb phrase saying what the change achieves.
  Join two outcomes with "and".

### Write the outcome

The title becomes the squash commit subject on the base branch, so write the
outcome as the line a reader of `git log` needs:

- **Lead with the behaviour change:** what the system does differently after
  the merge (`Import ERP bills through provider ports`), rather than the
  mechanism or file touched.
- **Keep it to one idea in about 60 characters:** move routes, class names,
  conditions ("once …") and caller paths into the body.
- **Use the domain's words:** the names a reviewer knows from the ticket and
  the product (bills import, dead-letter page, provider).
- **Offer three or four meaningful options:** each a different angle on the
  change (the behaviour, the end state, the user-facing surface), with its
  character count and the recommended one first. Before `gh pr create`, or
  when tidying open PRs, show the current title and the options for one PR at
  a time, and apply the one the user picks.
- **Share one verb across sibling PRs:** an API and its page read as one
  feature in `git log` (`Add an admin API to triage accounting dead letters`,
  `Show and triage accounting dead letters in the CMS`).

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
   - Open with one line that names and links the design doc, when there is
     one.
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
4. `## 🚦 Rollout` (parent PR, or any PR that needs deploy steps or waits on
   another PR)
   - A gated PR opens the section with a `> [!IMPORTANT]` or `> [!WARNING]`
     alert naming the gate and what breaks if it ships early.
   - `### 📋 Before merge` (gated PR) or `### 📋 Before deploy`: `- [ ]`
     items that must hold first (sibling PR live, queues, secrets, build env,
     migrations, flags); tick an item once it is confirmed.
   - `### 🚀 On deploy`, `### 👀 First 48 hours` (what to watch and where)
     and `### ↩️ Rollback`.
5. `## 🧷 Related PRs` (when sibling PRs exist)
   - A table: `| PR | Covers | State |`, full GitHub URL per row, State as
     `🟢 open` or `✅ merged`.
6. `## 🔗 References`
   - Bold-lead bullets: the PR's own ticket, parent ticket, related tickets,
     design doc (Notion link), next phases.
   - Link tickets inline: `[ACC-1558](https://linear.app/jeeves/issue/ACC-1558)`.
7. `## 🧪 How to test`
   - `### 🤖 Automated`: `- [x]` items for what passed, e.g. CI on the head
     commit and local lint commands in backticks.
   - `### 🧑‍🔬 Manual`, when a person tests: `- [ ]` steps, one per ticket
     acceptance criterion, each with its expected result.
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
