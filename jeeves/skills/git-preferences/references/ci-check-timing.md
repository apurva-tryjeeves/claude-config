# CI check timing

Per-repo PR check settle times across JeevesInc repos, used to set the checks-poller cadence
per the "Checks poller" section of `SKILL.md`.

One row per repo. Add a new row the first time a repo's cadence is derived; refine an existing
row if a later PR's actual settle time differs noticeably.

| Repo | Long-pole workflow | Check name | Min | Max | Mean | Sample size | First check | Interval |
|---|---|---|---|---|---|---|---|---|
| sequelize-db-models | validate.yml | Validate consistency | 1m17s | 5m25s | 3m11s | 10 | 1min | 3min |
| accounting-service | unit-test.yml | Unit Test | 14m15s | 18m20s | 16m31s | 9 | 14min | 2min |
| backend | unit-test.yml | Unit Test | 17m34s | 27m32s | 24m30s | 10 | 17min | 2min |
| wallet-service | unit-test.yml | Unit Test | 16m16s | 20m14s | 17m18s | 7 | 15min | 2min |
| stablecoin-service | unit-test.yml | Unit Test | 2m15s | 4m55s | 3m22s | 9 | 2min | 2min |
| jeeves-simulation-server | unit-test.yml | Unit Test | 1m15s | 5m31s | 3m27s | 10 | 1min | 3min |
| jeeves-web | unit-test.yml | Unit Test | 33m00s | 36m43s | 35m09s | 18 | 32min | 2min |
| billpay-service | unit-test.yml | Unit Test | 12m34s | 16m28s | 14m37s | 9 | 12min | 3min |

**Deriving a row:** drop any run longer than ~2h before taking min/max/mean. A run that sat queued
or was re-run hours later still reports a huge `updatedAt - createdAt`, and one of those is enough
to pull the mean far off (a jeeves-web sample once carried a 1433m run alongside 33-36m ones).

**Why the long-pole column:** a repo's cadence is driven by its slowest PR-check workflow alone —
faster workflows on the same repo have no bearing on it. Checks that aren't GitHub Actions runs
(e.g. SentinelOne CNS scans) historically settle in well under a minute and are excluded from the
timing data.

**How to apply:** look up the row for the target repo per the Checks poller section in `SKILL.md`.
No row yet for a repo — derive it from that repo's own CI history (see the skill) and add a row here.
