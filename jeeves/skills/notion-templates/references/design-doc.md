# Design doc template

## Canonical source

| Team | Parent page | Canonical example |
|---|---|---|
| Customer Accounting Team | Engineering > Customer Accounting Team (`7410dd2edd2241e0bf6ce26cad8ba1c7`), under its "Technical documentation" heading | [Accounting Service — ERP Provider Abstraction](https://app.notion.com/p/3e51edd5ce8c817c995ee839360ce23f) (`3e51edd5ce8c817c995ee839360ce23f`) |

When the doc's team has no row, ask the user for the parent page and an
example design doc, fetch both with `notion-fetch`, then add the team's row in
the same turn, following `${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.

## Page naming

| Doc | Title format | Example |
|---|---|---|
| Design doc | `<Service or area> — <Topic>` | `Accounting Service — ERP Provider Abstraction` |

## Fill guide

| Section | What goes in it |
|---|---|
| Purpose callout | One line: the decision this doc asks for, and the ticket it serves |
| `❗ Problem` | Bold-lead bullets, one per fact or cause, with the evidence (query, log line, ticket) |
| `🎯 Goal` | One or two sentences of what success looks like |
| `📐 Scope` | In-scope bullets, and an `**Out:**` line for what this phase leaves alone |
| `🛠️ Solution` | One bold-lead bullet per decision, then a `###` sub-section per part of the design: flow (a `mermaid` diagram), data model, API, failure modes. Long code or before/after sketches go in toggles |
| `⚖️ Alternatives considered` | A `### ⚖️ Alternatives considered` sub-section of Solution: one bold-lead bullet per option weighed, with why it lost |
| `✅ Acceptance criteria` | `- [ ]` checks the PRs must meet; they become each PR's manual test steps |
| `🚦 Rollout` | Gates, flags, migrations, what to watch after deploy, rollback |
| `❓ Open questions` | Numbered, each with an owner; resolved ones move into the section they settled |
| `🔗 References` | Ticket, parent ticket, related docs and PRs |

## Defaults

- Formatting follows `references/page-formatting.md`: page icon, gray purpose callout,
  table of contents, one emoji per heading, toggles for long code.
- Section headers and order follow `${CLAUDE_PLUGIN_ROOT}/references/doc-spine.md`.
- Keep sections that have content; a small change can be Problem, Solution and
  Acceptance criteria alone.

## Fallback body

````markdown
<callout icon="🎯" color="gray_bg">
<one line: the decision this doc asks for> — [<TICKET>](https://linear.app/jeeves/issue/<TICKET>)
</callout>

<table-of-contents />

## ❗ Problem
- **<Lead>:** <fact or cause, with its evidence>

## 🎯 Goal
<what success looks like>

## 📐 Scope
- **<Area>:** <in scope>

**Out:** <what this phase leaves alone>

## 🛠️ Solution
- **<Decision>:** <behaviour it gives>

### 🔀 Flow
```mermaid
sequenceDiagram
    <participant> ->> <participant>: <call>
```

### ⚖️ Alternatives considered
- **<Option>:** <why it lost>

## ✅ Acceptance criteria
- [ ] **<Check>:** <observable result>

## 🚦 Rollout
- **<Step>:** <gate, flag or migration>

## ❓ Open questions
1. <question> — owner: <name>

## 🔗 References
- **Ticket:** [<TICKET>](https://linear.app/jeeves/issue/<TICKET>)
````
