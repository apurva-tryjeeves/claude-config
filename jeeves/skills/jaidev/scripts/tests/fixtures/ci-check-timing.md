---
name: ci-check-timing
description: Per-repo PR check settle times (long-pole workflow, check names, min/max/mean, first check, interval); read before starting a checks poller or a Jaidev CI watch, and add or refine a repo's row after its checks settle
metadata:
  type: reference
---

# CI check timing

One row per JeevesInc repo; the git-preferences skill's references/pr-pollers.md "Checks poller" section derives and refines rows.

| Repo | Long-pole workflow | Check name | Settles on | Min | Max | Mean | Sample size | First check | Interval | Known failures |
|---|---|---|---|---|---|---|---|---|---|---|
| sequelize-db-models | validate.yml | `Validate consistency` | `Validate consistency` | 1m17s | 5m25s | 3m11s | 10 | 1min | 3min |  |
| accounting-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 14m15s | 18m20s | 16m31s | 9 | 14min | 2min |  |
| backend | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 7m36s | 26m17s | 12m49s | 20 | 7min | 2min |  |
| wallet-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 17m46s | 23m32s | 20m19s | 20 | 17min | 2min |  |
| stablecoin-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 2m15s | 4m55s | 3m22s | 9 | 2min | 2min |  |
| jeeves-simulation-server | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 1m15s | 5m31s | 3m27s | 10 | 1min | 3min |  |
| jeeves-web | unit-test.yml | `Unit Test` | `Code Analysis`, `SonarCloud Code Analysis` | 33m00s | 36m43s | 35m09s | 18 | 32min | 2min | `Validate Localization` |
| billpay-service | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 12m34s | 16m28s | 14m37s | 9 | 12min | 3min |  |
| ap-data-source-connector | unit-test.yml | `test / Unit Test` | `test / Scan for secrets`, `SonarCloud Code Analysis` | 2m12s | 4m54s | 3m18s | 10 | 2min | 2min |  |
| cms | unit-test.yml | `test / Unit Test` | `test / Code Analysis`, `SonarCloud Code Analysis` | 7m24s | 17m13s | 9m00s | 10 | 7min | 3min |  |
