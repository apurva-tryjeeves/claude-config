---
name: fullstack-typescript
description: Principal-level engineering standards for Node, React and TypeScript — scalable and secure system design, low-level design and patterns, codebase structure, and advanced language features weighed against readability. Use when designing or implementing a non-trivial feature, module, service or API in a TypeScript codebase, or when reviewing a design or pull request at that level.
---

# Full-stack TypeScript

Work the way a principal engineer does: choose the simplest design that
survives production, and leave code the next engineer can change safely.

## Order of precedence

1. The target repo's own rules (`AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, lint and `tsconfig`).
2. Patterns the surrounding code already uses.
3. This skill.

## Workflow

1. **Size the work.** A change inside one function with a known cause is
   small: go to step 5. Anything that adds a module, an endpoint, a table, a
   queue, a shared type or a cross-service call is non-trivial: run every step.
2. **State the requirements with numbers** — load, latency, data volume,
   consistency, who may call it. Ask the user for a number that changes the
   design; assume and label the rest.
3. **System design.** Read `${CLAUDE_SKILL_DIR}/references/system-design.md`
   and `${CLAUDE_SKILL_DIR}/references/security.md`. Write a short Design
   section: components, data model, contracts, failure modes, security
   notes, rollout.
4. **Low-level design.** Read `${CLAUDE_SKILL_DIR}/references/design-patterns.md`
   and `${CLAUDE_SKILL_DIR}/references/codebase-structure.md`. List the
   modules, their public types and functions, and each pattern chosen with
   the problem it removes.
5. **Code.** Read the reference for the layer you touch (table below) and
   apply the judgement test to every advanced construct.
6. **Self-review** with `${CLAUDE_SKILL_DIR}/references/review-checklist.md`
   before reporting; fix what it finds.
7. **Independent review** for non-trivial work: offer the
   `principal-engineer` agent (see "Delegate").

Show the Design and Low-level design sections to the user and wait for
their yes before step 5.

## The judgement test

Use an advanced type, language feature or pattern when it does at least one
of these and a mid-level teammate can still read the call site:

- turns a runtime bug into a compile error;
- removes duplicated logic that would otherwise drift apart;
- makes a wrong use of an API impossible or obvious.

When it only shortens the code or shows skill, write the plain version.
Keep type-level machinery in library-style modules, behind a simple
signature; keep feature code plain. State the reason in one line when you
choose the advanced form.

## References

| File | Holds | Read when |
|---|---|---|
| `references/system-design.md` | Requirements, data, consistency, scaling, failure, evolution | Designing a service, feature or data flow |
| `references/security.md` | Threat model, validation, authorization, secrets, Node and browser risks | Designing, or touching a trust boundary |
| `references/design-patterns.md` | Boundaries, patterns with use-when and skip-when, error modelling | Low-level design |
| `references/codebase-structure.md` | Backend layering, React feature folders, module rules | Adding modules or files |
| `references/typescript-advanced.md` | Type modelling, generics, `Record` and `Map`, boundary typing, version gates | Writing types or public APIs |
| `references/node-runtime.md` | Event loop, async control, streams, lifecycle, profiling | Backend code |
| `references/react.md` | State placement, rendering, effects, composition, UX quality | Frontend code |
| `references/review-checklist.md` | The principal-level review pass | Self-review, or reviewing a design or PR |

## Sibling skills

Each of these owns its topic; load it for the detail.

- `jeeves:typescript-naming` — identifier and file names.
- `jeeves:structured-logging` — logger calls, levels and fields.
- `jeeves:sonar-proactive-rules` — rules the quality gate enforces.
- `jeeves:sqs` — queue type choice.

## Delegate

The `jeeves:principal-engineer` agent designs and reviews in its own
context and returns a written result; it edits no files. Use it for an
independent design, a design review, or a pull-request review.

Before each launch, ask with `AskUserQuestion` which model to run:

| Option | Model | Effort |
|---|---|---|
| Standard (default) | `sonnet` | `medium` |
| Deep | `opus` | `high` |

Pass the chosen model and effort on the `Agent` call. Give the agent the
mode (design, design review or PR review), the repo path, the ticket or
requirement text, and the diff range or design document.

## Reporting results

- **Design:** the Design and Low-level design sections, then the open
  questions that change the design.
- **Code:** the change, plus one line for each advanced construct chosen and
  each trade-off made.
- **Review:** findings ordered by severity, each with file and line, the
  failure it causes and the fix; one line when the review is clean.
- Leave out restated standards, usage examples and closing offers.
