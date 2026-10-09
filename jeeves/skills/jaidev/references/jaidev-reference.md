# Jaidev reference

Observed behaviour of Jaidev ("Jeeves AI Developer", `@jaidev` on Linear), from real tickets. When Jaidev's own messages show something new, update this file in the same turn.

## Contents

1. Lifecycle
2. Commands
3. Triggering a run
4. What its comments look like
5. Limits

## 1. Lifecycle

1. **Start**: a user posts `@jaidev start` as a new comment.
2. **Analysis**: Jaidev reads the ticket, its comments and its knowledge base (`PRODUCT.md`, `PLATFORM.md`, `SERVICE.md`, one file per repository) and explores the repositories.
3. **Questions** (optional): it posts questions and waits. Status shows "Gathering Info (Waiting for Answers)".
4. **Plan**: it posts an "Implementation plan" comment and waits for approval.
5. **Implementation**: after approval it implements and opens one PR per repository, cc'ing the user who started it.
6. **Review**: GitHub PR review comments trigger a revision ("Revision #1 — addressing N new comment(s) — Attempt 2/3").
7. **Deploy** (optional): on request it deploys to a shared develop environment or a short-lived one.
8. **Complete**: after the merge, the status comment shows "Complete ✅".

Throughout, a status comment titled "**Jaidev — <TICKET-ID>**" shows the status, who started it, cost per phase, repositories, PR links and a timeline.

## 2. Commands

| Command | Where | Effect |
|---|---|---|
| `@jaidev start` | New top-level comment | Starts analysis |
| Reply text | In the question's thread | Answers a question |
| `@jaidev skip` | Ticket comment | Skips open questions |
| `@jaidev abort` | Ticket comment | Stops the run |
| `@jaidev plan:approved` | Reply in the plan thread | Approves the plan, starts implementation |
| `@jaidev plan:approved, auto-deploy` | Reply in the plan thread | Approves and provisions a dev environment |
| Feedback text | Reply in the plan thread | Requests plan changes |
| `@jaidev plan:drop <repo-name>` | Reply in the plan thread | Removes a repository from the plan |
| `@jaidev deploy on develop-NN` | Ticket comment | Deploys the ticket's modules to a shared develop environment (`to` and `on` both work) |
| `@jaidev deploy` | Ticket comment | Provisions a short-lived environment `dev-jaidev-<linear-id>`; re-run after pushing changes |

## 3. Triggering a run

- Start every run with a **new top-level comment** whose first line is exactly `@jaidev start`. The full briefing can follow in the same comment.
- Use that exact wording. Close variants (`start @jaidev`, `@jaidev get started`, `@jaidev please pick up this ticket…`) leave Jaidev idle.
- Post a fresh comment rather than editing `start` into an existing one; edits may go unnoticed.
- Assignment alone leaves Jaidev idle — it replies "I don't pick up tickets via assignment anymore. Reply `@jaidev start`".

## 4. What its comments look like

**Implementation plan** sections:

- Header: Complexity, Estimate (points), Repos, Confidence, Delegating User
- Summary
- Key Assumptions, each with the evidence it checked
- Affected Services table: service, base branch, changes
- Implementation Sequence per repository, with "Done when" criteria
- Feature Flags
- Risk Assessment: risk and mitigation pairs
- Cross-Cutting Invariants it verifies before opening a PR
- Context Sources: knowledge-base files and repositories explored
- Footer with the approval commands

When reviewing, focus on Key Assumptions (they carry the most risk), whether Affected Services lists the right repository and base branch, and whether the "Done when" items match the ticket's acceptance criteria.

**PR result** comment: `**<repo>** • ✅ Complete`, PR link, files changed, cost and duration, then revision entries.

**Deploy** comment after the PR: lists the module to deploy and the team's allocated develop environments.

## 5. Limits

- It needs an existing base branch with at least one commit; the first commit of a new repository is a manual step.
- Deploys need the service to exist in the develop environments (Helm chart, HelmRelease).
- Knowledge-base files cover existing repositories. For a new repository Jaidev explores the code directly, so give the briefing extra context.
- Each phase costs money (shown in the status comment). Clear briefings avoid question rounds and plan revisions.
