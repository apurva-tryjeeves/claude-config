# Briefing format

The one format for every `@jaidev start` comment. `SKILL.md` step 2
(`references/briefing.md`) and `assets/agent-brief-template.md` both use it.

Fill this format; include Manual follow-up only when it has items, and then add "A human makes the items under Manual follow-up." to the workflows Constraint.

````markdown
@jaidev start

Please pick up this ticket in <org/repo>. Start your branch from <start-branch> and open the PR against <base-branch>.

## 🎯 Goal

<1–3 sentences: what this achieves and which tickets it unblocks>

## 📋 Context

- <current state of the code, in words>
- <precedent PRs to follow and what they did>
- <known CI or environment limitations>
- <related tickets in flight and the files they touch>

## 🛠️ Changes

- <every change in prose: what changes and why; the exact names, paths and values are in the names comment just above the start comment>

## 🚧 Constraints

- <what stays unchanged; scope boundaries with other tickets>
- Secrets stay out of code; coverage thresholds stay as they are.
- Report known CI failures as they stand.
- Your changes stay outside .github/workflows.

## 🧑‍🔧 Manual follow-up

- <changes a human makes on your branch, e.g. .github/workflows edits; they sit outside your definition of done>

## ✅ Acceptance criteria

- [ ] <checkable items your branch alone can satisfy: commands that must pass, behaviour to verify, evidence to paste in the PR description; the full test suite and coverage gate as the CI check that runs them, e.g. "CI test / Unit Test passes">

The exact names and code are in the comment just above this one; use them as written. Copy every acceptance criterion into your plan's Done when, word for word. Name any you fail to meet in the plan, before you start. Quote back at the top of your plan one key code signature (if this briefing gives code) and acceptance criterion #1. Write any code this briefing gives out in full in your plan's Implementation Sequence. Ask here if anything is unclear.
````
