# CI check timing

Per-repo PR check settle times across JeevesInc repos, used to set the checks-poller cadence
per the "Checks poller" section of `SKILL.md`.

One row per repo. Add a new row the first time a repo's cadence is derived; refine an existing
row if a later PR's actual settle time differs noticeably — both per "Write back a timing row" in
`SKILL.md`.

| Repo | Long-pole workflow | Check name | Settles on | Min | Max | Mean | Sample size | First check | Interval |
|---|---|---|---|---|---|---|---|---|---|
| sequelize-db-models | validate.yml | `Validate consistency` | `Validate consistency` | 1m17s | 5m25s | 3m11s | 10 | 1min | 3min |
| accounting-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 14m15s | 18m20s | 16m31s | 9 | 14min | 2min |
| backend | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 7m36s | 26m17s | 12m49s | 20 | 7min | 2min |
| wallet-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 17m46s | 23m32s | 20m19s | 20 | 17min | 2min |
| stablecoin-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 2m15s | 4m55s | 3m22s | 9 | 2min | 2min |
| jeeves-simulation-server | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 1m15s | 5m31s | 3m27s | 10 | 1min | 3min |
| jeeves-web | unit-test.yml | `Unit Test` | `Code Analysis`, `SonarCloud Code Analysis` | 33m00s | 36m43s | 35m09s | 18 | 32min | 2min |
| billpay-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 12m34s | 16m28s | 14m37s | 9 | 12min | 3min |
| ap-data-source-connector | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 2m12s | 4m54s | 3m18s | 10 | 2min | 2min |

**Check names:** copy them from the PR's own rollup (`gh pr view <n> --json statusCheckRollup`).
Repos on the shared `infra-reusable-workflows` unit-test workflow prefix each job with `test / `;
jeeves-web runs its own workflow with unprefixed names.

**Deriving a row:** drop any run longer than ~2h before taking min/max/mean. A run that sat queued
or was re-run hours later still reports a huge `updatedAt - createdAt`, and one of those is enough
to pull the mean far off (a jeeves-web sample once carried a 1433m run alongside 33-36m ones).

**Why the long-pole column:** a repo's cadence is driven by its slowest PR-check workflow alone —
faster workflows on the same repo have no bearing on it. Checks that aren't GitHub Actions runs
(e.g. SentinelOne CNS scans) historically settle in well under a minute and are excluded from the
timing data.

**How to apply:** look up the row for the target repo per the Checks poller section in `SKILL.md`.
No row yet for a repo — derive it from that repo's own CI history (see the skill) and add a row here.
