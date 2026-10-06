# `deploy-DEVELOP-environment` (dev Jenkins)

Deploys one or more Jeeves services into a shared ephemeral `develop-NN`
environment.

- Pipeline job defined in the `jenkins-pipelines` repo, at
  `deploy/deploy-DEVELOP-environment.jenkins`.
- `concurrentBuild: true` — multiple builds can run at once (see
  "Concurrency model" below).

## Parameters

- `ENVIRONMENT` — Active Choices `ChoiceParameter`. Full choice list (from
  the job's Build with Parameters UI): `develop-01` through `develop-20`,
  plus `sandbox`.
- `MODULES` — Active Choices `DynamicReferenceParameter`. Packs every
  deployable service into one comma-separated string with no name-to-field
  mapping in the REST API: three values per service, in this fixed
  positional order — `enable(true/false), branch, mode(latest/rebuild)` —
  followed by a trailing comma, exactly as the job's form submits it.

  | Field | Enabled service | Disabled service |
  |---|---|---|
  | `enable` | `true` | `false` |
  | `branch` | the branch the user asked for | the service's default branch (`development`, or `main` for `simulationserver`, `utvservice`, `aiweb`) |
  | `mode` | `rebuild` for any feature branch; `latest` on the default branch; whatever the user asks for overrides both | `latest` |

  The pipeline builds and deploys only `enable=true` services and leaves every
  other service in the environment as it is, so a disabled triple's branch and
  mode are never read. Mode `latest` makes the pipeline resolve the service's
  current `:latest` ECR image before building (`ecr.resolveLatestTag`), and
  that step fails the build when the image carries more than one tag — which
  is why a feature branch goes out as `rebuild`.

  `scripts/modules.py` is the one place this order lives. It builds and reads
  the value, keeping every service on its own position and checking the string
  carries one triple per service:

  ```bash
  python3 scripts/modules.py --list               # position, service, local repo
  python3 scripts/modules.py --decode "$MODULES"  # what a string resolves to
  ```

  `--list` prints each service alongside its git repo name; the local
  checkout lives under `${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}`. A service showing `-` has no repo recorded yet: ask
  the user for the repo name and branch, then add the repo to `SERVICES` in
  `scripts/modules.py` in the same turn, so the next run reads it instead of
  asking again.

  Example decoded triple from a captured build: `api` at position 1 with
  `true,MP-5198,latest` means deploy `api`, branch `MP-5198`, mode `latest`.

## Deploying a service — flow

1. **Identify the service(s)** the user wants deployed — by service name, or
   by the repo they're currently working in. `python3 scripts/modules.py
   --list` maps every service to its local repo.
2. **Determine the branch.** If the user names one, use it. Otherwise, if
   the service maps to a local repo, read the branch currently checked out
   there (or in the session's working directory when the repo lives elsewhere)
   and offer it as the default — confirm with the user before using
   it, since "currently checked out" isn't necessarily "what they want
   deployed":

   ```bash
   git -C "${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/<repo>" branch --show-current
   ```

3. **Determine the environment.** The choice list (`develop-01`–`develop-20`,
   `sandbox`) has 21 entries, past the 4-option cap on `AskUserQuestion` —
   print the full list as plain text and ask the user to reply with a slot
   name rather than using `AskUserQuestion`.
4. **Build `MODULES` with the script** from exactly the services and branches
   the user asked for — one `--set` per service. Every other service goes in
   disabled:

   ```bash
   MODULES=$(python3 scripts/modules.py --set accounting=feat/ACC-1568 --set web=feat/ACC-1603)
   ```

   Append `:latest` or `:rebuild` to a value (`web=<branch>:latest`) when the
   user names a mode. The script prints the enabled services and their
   positions to stderr — read that line back and confirm it names exactly the
   services and branches requested before moving on.
5. **Check the payload.** Decode the string you are about to send and compare
   it with the request — the enabled list must match it one for one:

   ```bash
   python3 scripts/modules.py --decode "$MODULES"
   ```

6. **Confirm before triggering.** State the exact `ENVIRONMENT` and each
   enabled service's branch and mode, and get explicit go-ahead — this is a
   shared dev environment other people may be using. Mention the expected
   duration from "Per-service deploy timing" below for the service(s) being
   deployed, if a row exists there.
7. **Trigger.** Builds lock per environment, so check whether anything is
   already working on *your* slot — a build on another slot runs in parallel
   and is someone else's deploy, not a blocker:

   ```bash
   jenkins-api "job/deploy-DEVELOP-environment/api/json?tree=builds[number,building,actions[parameters[name,value]]]{0,10}" \
   | python3 -c "
   import json, sys
   for b in json.load(sys.stdin)['builds']:
       params = {p['name']: p['value'] for a in b.get('actions', []) for p in a.get('parameters', [])}
       if b['building']:
           print('building:', b['number'], params.get('ENVIRONMENT'))
   "
   jenkins-api queue
   ```

   Fetch a CSRF crumb (required for POST requests):

   ```bash
   CRUMB=$(jenkins-api crumb)
   ```

   POST the params to `buildWithParameters`, keeping the response headers so
   the queue id is captured:

   ```bash
   jenkins-api "job/deploy-DEVELOP-environment/buildWithParameters" -H "$CRUMB" -X POST \
     --data-urlencode "ENVIRONMENT=<chosen slot>" \
     --data-urlencode "MODULES=$MODULES" -D /tmp/trigger-headers.txt
   ```

   This returns `201` with a `Location: .../queue/item/<id>/` header — no
   build number yet. Resolve that id to your build number right away, since
   Jenkins keeps a queue item for about five minutes after the build starts:

   ```bash
   jenkins-api queued "$(sed -n 's/^location: //Ip' /tmp/trigger-headers.txt)"
   ```

   It prints the build number once assigned, or `waiting: <why>` while the
   item sits in the queue.
8. **Track that build number** through every later call:

   ```bash
   jenkins-api status deploy-DEVELOP-environment <number>
   jenkins-api log deploy-DEVELOP-environment <number>
   ```

   This job runs concurrently across ~20 environments, so a bare
   `status deploy-DEVELOP-environment` reports `lastBuild` — routinely
   another engineer's deploy to another slot.
9. **Confirm the deploy touched the intended service.** The console log names
   each repo it clones, so a positional slip in `MODULES` shows up here as a
   different service than the one you meant:

   ```bash
   jenkins-api log deploy-DEVELOP-environment <number> | grep -E 'Cloning repository|Failed in branch'
   ```

   Then interpret the outcome using "Reading a build's outcome" below rather
   than dumping the raw log.

## Concurrency model

The pipeline takes a lockable resource for the target `ENVIRONMENT` before
deploying, so two builds targeting the **same** `develop-NN` slot queue and
run in sequence, while builds targeting different slots run in parallel —
this job does not hit the shared-workspace git-ref race described in
`build-ops.md`. Check `$JENKINS_URL/lockable-resources/` before retriggering
into a busy environment.

## Reading a build's outcome from the console log

| Console log signature | Meaning |
| --- | --- |
| `Pod [Pending][Unschedulable] ...` | The deploy agent is waiting on capacity; usually clears on its own within the build |
| `... not found` + `Error restarting X. Not a big deal` | The service has no matching cron/side deployment in this environment — expected/benign, not a build failure signal |
| `... rollout status ... exceeded its progress deadline` | The newly deployed service failed to become ready in time — a genuine app/code issue in the deployed module, not a Jenkins problem |
| `Couldn't find any revision to build` on a repo you did not target, within a minute or two of the trigger | The `MODULES` triples shifted position, so your branch landed on a neighbouring service whose repo has no such branch. The build stops at checkout, so nothing deployed. Rebuild the string with `scripts/modules.py` and retrigger |

Diagnose using the console log text alone — that's the source of truth
available from this session.

Failures post to the `#jenkins-ci-dev` Slack channel via the pipeline's
`slackSend` post-action step.

## Per-service deploy timing

Build durations derived from build history where **exactly one** service was
`enable=true` in the `MODULES` string, so the full build duration attributes
cleanly to that one service — a multi-service build's duration can't be
split back out per service since they build/deploy in parallel.

One row per service, carried forward across sessions. The job's
`BuildDiscarderProperty` keeps a rolling window (72 builds as of 2026-09-22,
6 the day before), so a service's earlier samples age out of the API while
its row here keeps them — merge a fresh sample into the existing row (widen
min/max, add to the sample size) rather than replacing the row with whatever
the current window holds. A service with no row yet gets one the first time
a clean single-service build appears for it.

| Service | Min | Max | Mean | Sample size |
|---|---|---|---|---|
| api | 4m27s | 12m06s | 8m56s | 15 |
| accounting | 4m02s | 4m38s | 4m17s | 3 |
| billpay | 2m10s | 6m49s | 4m29s | 5 |
| cards | 6m49s | 10m48s | 8m57s | 4 |
| cms | 6m33s | 12m43s | 9m38s | 2 |
| credit | 3m25s | 3m25s | 3m25s | 1 |
| creditstatements | 13m04s | 13m04s | 13m04s | 1 |
| expensemanagement | 2m27s | 5m39s | 4m13s | 6 |
| flows | 10m06s | 10m10s | 10m08s | 2 |
| productaccount | 2m04s | 9m50s | 5m22s | 4 |
| stablecoinservice | 3m32s | 5m10s | 4m04s | 4 |
| utvservice | 1m45s | 4m26s | 3m11s | 7 |
| wallet | 4m35s | 9m05s | 6m43s | 6 |
| web | 11m14s | 15m46s | 13m26s | 7 |

**How to derive/refine a row:** fetch recent builds' params and durations in
one batched request, filter to
`result == "SUCCESS"` builds whose `MODULES` string has exactly one
`enable=true` triple, and use that build's total `duration` as one sample for
that service:

```bash
jenkins-api "job/deploy-DEVELOP-environment/api/json?tree=builds[number,result,duration,actions[parameters[name,value]]]{0,300}" \
| python3 -c "
import json, sys
sys.path.insert(0, 'scripts')
from modules import NAMES, parse
for b in json.load(sys.stdin)['builds']:
    if b['result'] != 'SUCCESS' or not b['duration']:
        continue
    params = {p['name']: p['value'] for a in b.get('actions', []) for p in a.get('parameters', [])}
    if not params.get('MODULES'):
        continue
    enabled = [NAMES[i] for i, t in enumerate(parse(params['MODULES'])) if t[0] == 'true']
    if len(enabled) == 1:
        print(enabled[0], b['number'], b['duration'])
"
```

**Caveat:** these durations reflect a **single-service** build. A build
deploying multiple services at once (e.g. `web` + `accounting` + `aiservice`
together) runs them in parallel, so its total duration is closer to the
*slowest* of the enabled services' individual times, not their sum — use the
single-service numbers above as a per-service ceiling estimate, not an
additive one.
