---
name: sonar-fix
description: Clear a failing SonarCloud quality gate on a JeevesInc pull request — read the gate, fix every open issue and hotspot, close the coverage-on-new-code gap, verify locally, commit and push. Trigger when a PR's Sonar check is red, a quality gate is blocking a merge, or the user asks to fix Sonar issues or new-code coverage.
---

# Sonar Fix

Fix the SonarCloud quality gate for a pull request end to end.

## Inputs
- **PR number** — take it from the request; ask which PR when none is given.
- **Repo** — take it from the request, else infer it from the current git repo:
  ```bash
  gh repo view --json nameWithOwner -q .nameWithOwner
  ```
- **SonarCloud auth** — the `SONAR_TOKEN` env var (a read-only user token from sonarcloud.io → My Account → Security). Export it from your shell profile (see the marketplace README) so every shell has it. Confirm it's set:
  ```bash
  [ -n "${SONAR_TOKEN}" ] && echo set || echo unset
  ```
  It prints `set` or `unset` and keeps the value itself out of any output. When it's unset, ask the user to export `SONAR_TOKEN` and restart the session.
  Use the token only inside `curl -u "${SONAR_TOKEN}:"` for every SonarCloud call — keep it confined to that flag, out of any other output or commit.

## Steps

0. **Check out the PR branch.** Confirm the working tree is clean, then compare the current branch with the PR's head:
   ```bash
   git status --porcelain
   ```
   ```bash
   gh pr view <pr-number> --json headRefName -q .headRefName
   ```
   ```bash
   git branch --show-current
   ```
   When `git status --porcelain` prints anything, stop and report the changed files to the user. When the current branch differs from `headRefName`, check out the PR:
   ```bash
   gh pr checkout <pr-number>
   ```
   Every later edit and commit lands on this branch.

1. **Resolve project.** Read `sonar-project.properties` at the repo root for `sonar.projectKey` and `sonar.organization`.

2. **Read the gate.** Query these four sources with `curl -u "${SONAR_TOKEN}:"` against `https://sonarcloud.io/`, and list every failed condition and every issue/hotspot before changing anything:

   | Source | Endpoint | What it gives you |
   |---|---|---|
   | Gate conditions | `api/qualitygates/project_status?projectKey=<key>&pullRequest=<pr-number>` | Each condition's own `errorThreshold` — set per-project (e.g. `new_coverage` can require 50% on one project, 100% on another); treat this response as the source of truth for the actual number |
   | Open issues | `api/issues/search?componentKeys=<key>&pullRequest=<pr-number>&statuses=OPEN,CONFIRMED&ps=100` | Rule, component, line, message for each `CODE_SMELL`/`BUG`/`VULNERABILITY` |
   | Security hotspots | `api/hotspots/search?projectKey=<key>&pullRequest=<pr-number>&ps=100` | Findings behind a red `new_security_hotspots_reviewed` condition — a distinct SonarCloud concept, not returned by `issues/search` |
   | Duplicated blocks | `api/measures/component?component=<key>&pullRequest=<pr-number>&metricKeys=new_duplicated_lines_density,new_duplicated_blocks` | The duplication figure behind a red `new_duplicated_lines_density` condition |

   Page through issues and hotspots: add `&p=<n>` and repeat until `p × 100` reaches `paging.total`. For issues:
   ```bash
   p=1
   while :; do
     page=$(curl -s -u "${SONAR_TOKEN}:" "https://sonarcloud.io/api/issues/search?componentKeys=<key>&pullRequest=<pr-number>&statuses=OPEN,CONFIRMED&ps=100&p=${p}")
     echo "${page}" | jq -c '.issues[] | {rule, component, line, message}'
     [ $((p * 100)) -ge "$(echo "${page}" | jq '.paging.total')" ] && break
     p=$((p + 1))
   done
   ```
   For hotspots, run the same loop against `api/hotspots/search?projectKey=<key>&pullRequest=<pr-number>&ps=100&p=${p}` and read `.hotspots[]`.

3. **Fix each issue by rule.** Consult the `jeeves:sonar-proactive-rules` skill (and its `references/sonar-ts-rules-catalog.md`) for what each rule id requires. Apply the minimal, behavior-preserving change (e.g. S7776 → `Set`+`.has()`, S6582 → optional chaining, S6606 → `??=`/`??`, S3776 → extract a helper — note `?.` and `??` each cost a cognitive-complexity point, so extraction, not just rewriting a condition, is what actually lowers S3776).

   **Resolve each hotspot.** For every hotspot with status `TO_REVIEW`, read its rule in `sonar-ts-rules-catalog.md` and the flagged code. When the code carries the risk, apply the fix and let the next analysis close the hotspot. When the code is safe, show the user the hotspot link and a one-line reason, and ask them to mark it **Safe** in SonarCloud — `SONAR_TOKEN` is read-only.

4. **Fix coverage-on-new-code failures.** When the `new_coverage` condition is red (below the `errorThreshold` read in step 2): run the repo's tests with coverage and find the uncovered new lines. If the file is a bootstrap/entry point already in jest.config `coveragePathIgnorePatterns` (e.g. `start-*.ts`, `main.ts`, `server.ts`, barrels), show the user the `sonar.coverage.exclusions` line you will write in `sonar-project.properties`, then wait for the user's yes before writing it (keep the two lists in sync). Otherwise, add tests until coverage on the new/changed lines clears that project's actual threshold.

   **Fix duplication failures.** When `new_duplicated_lines_density` is red, extract the repeated new code into a shared helper. For generated code or test fixtures, show the user the `sonar.cpd.exclusions` line you will write in `sonar-project.properties`, then wait for the user's yes before writing it.

5. **Verify locally** before committing, with the repo's own tooling:
   ```bash
   [ -f tsconfig.json ] && npx tsc --noEmit
   npx eslint <changed files>
   npm run   # lists the repo's scripts; pick its test/coverage script
   ```
   Run `eslint --fix` for pure formatting, then run the repo's test script with coverage (jest in most services, mocha in `backend`) — confirm all tests pass and coverage on changed files clears the threshold from step 2.

6. **Commit exactly the files you edited**, staged explicitly by path (leave `*.postman_collection.json` unstaged if it appears among changes — it is a local Postman export, outside the Sonar fix). Follow the `jeeves:git-preferences` skill for commit message style and the co-author trailer. Show the staged files and the commit message, then wait for the user's yes before committing.

7. **Push** once the user confirms — show the branch and the commit(s) first. Then follow the `jeeves:git-preferences` skill's PR Post-Create Polling section: ask which poller(s) to start, and for the Checks poller use its per-repo cadence and stop rule until the `SonarCloud Code Analysis` check reaches a terminal state, then report pass/fail. Re-read the gate (step 2) and iterate against the live result to confirm each fix worked.

## Notes
- SonarCloud projects here are private: the GitHub check annotations carry locations only — the API (with the token) is the only reliable source of the actual issue text.
- Confirm every condition in the gate response individually shows `status: OK` — clearing the gate needs all conditions green, not just the one just fixed.
- A call to `api/qualitygates/project_status` returning `{"errors":[{"msg":"Project doesn't exist"}]}` signals a missing/unsent `SONAR_TOKEN` on this private project, even when the project key is correct — reissue the same call with `-u "${SONAR_TOKEN}:"` attached.

## Report the outcome

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.

- **Verdict line first** — icon, the gate's state, and the PR as a link:
  `✅ quality gate passing — [#534](https://github.com/JeevesInc/<repo>/pull/534)`.
- **Table the conditions** — columns `Condition | Threshold | Actual | Result`,
  one row per gate condition, so a still-red condition is visible at a glance.
- **Table the fixes** — columns `Rule | File | Change`, one row per issue
  cleared, with the rule id linked per the shared doc's SonarCloud pattern.

Answer with the verdict and the tables, then stop — leave out the `curl` calls
made, the full issue list already fixed, and "want me to keep polling?"
follow-ups.
