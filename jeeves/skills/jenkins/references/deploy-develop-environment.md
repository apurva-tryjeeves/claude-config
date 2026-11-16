# `deploy-DEVELOP-environment` (dev Jenkins)

Deploys one or more Jeeves services into a shared ephemeral `develop-NN`
environment.

- Pipeline job defined in the `jenkins-pipelines` repo, at
  `deploy/deploy-DEVELOP-environment.jenkins`.
- `concurrentBuild: true` — multiple builds can run at once (see
  "Concurrency model" below).

## Parameters

- `ENVIRONMENT` — Active Choices `ChoiceParameter`, generated live from the
  EKS namespaces matching `^(develop-|sandbox).*`: `develop-01` through
  `develop-20` plus `sandbox`. `develop-14` and `develop-15` are managed by
  FluxCD image automation and the pipeline aborts any build that targets them,
  so offer the other slots.
- `MODULES` — Active Choices `DynamicReferenceParameter`. Packs every
  deployable service into one comma-separated string with no name-to-field
  mapping in the REST API: three values per service, in this fixed
  positional order — `enable(true/false), branch, mode(latest/rebuild)` —
  followed by a trailing comma, exactly as the job's form submits it.

  | Field | Enabled service | Disabled service |
  |---|---|---|
  | `enable` | `true` | `false` |
  | `branch` | the branch the user asked for | the form's pre-filled branch (`development`, or `main` for `simulationserver` and `aiweb`) |
  | `mode` | `latest` when the branch is `development`, `rebuild` for every other branch; whatever the user asks for overrides both | `latest` |

  The pipeline builds and deploys only `enable=true` services and leaves every
  other service in the environment as it is, so a disabled triple's branch and
  mode are never read. It rebuilds any enabled service whose branch is not
  `development` (`parseModulesForm`: `rebuild = enable && (mode == 'rebuild' ||
  branch != 'development')`). Mode `latest` additionally resolves the service's
  current `:latest` ECR image (`ecr.resolveLatestTag`), which needs exactly one
  non-`latest` tag on that image and fails the build otherwise — so `latest`
  only fits `development`, and a `resolveLatestTag` failure is retried with
  `:rebuild`.

  `scripts/modules.py` holds this order. The pipeline's own source of it is
  `jenkins-library` `vars/jeevesPlatformInfo.groovy`: the `modules` map,
  filtered to entries with a non-empty `giturl` and no
  `standaloneHelmRelease`; `jeevesUtils.parseModulesForm` reads only that
  many triples. The job's form can append extra triples for skipped modules
  (`calm`, `calmweb`), which the pipeline ignores. The script builds and
  reads the value, keeping every service on its own position, and drops
  those trailing triples when decoding:

  ```bash
  python3 scripts/modules.py --list               # position, service, local repo
  python3 scripts/modules.py --decode "$MODULES"  # what a string resolves to
  ```

  `--list` prints each service alongside its git repo name; the local
  checkout lives under `${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}`. A
  service showing `-` has no repo recorded yet: ask the user for the repo
  name, then record it by editing `SERVICES` in `scripts/modules.py`, following
  `references/write-back.md` at the plugin root.

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

3. **Determine the environment.** The usable slots (`develop-01`–`develop-20`
   except `develop-14` and `develop-15`, plus `sandbox`) number 19, past the
   4-option cap on `AskUserQuestion` — print the list as plain text and ask
   the user to reply with a slot name rather than using `AskUserQuestion`.
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
   duration from `~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md` for the service(s)
   being deployed, when that file exists and has their rows. To say what the slot runs now, use
   the user's answer or the Grafana dashboard per SKILL.md → "Name the build
   you mean"; otherwise leave it out.
7. **Trigger.** Same-slot builds run concurrently (see "Concurrency model"),
   so check whether anything is already working on *your* slot. When a build
   is running or queued for that slot, stop and ask the user before
   triggering. A build on another slot is someone else's deploy, not a
   blocker:

   ```bash
   TREE='builds[number,building,actions[parameters[name,value]]]{0,10}'
   jenkins-api "job/deploy-DEVELOP-environment/api/json?tree=${TREE}" \
     | python3 scripts/build-params.py --building
   jenkins-api queue
   ```

   The queue output carries each item's `params`; match `ENVIRONMENT=<chosen slot>` there.

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
   jenkins-api log deploy-DEVELOP-environment <number> \
     | grep -E 'Cloning repository|Failed in branch'
   ```

   Then interpret the outcome using "Reading a build's outcome" below rather
   than dumping the raw log. Name the stage a running build is in from
   `deploy-develop-environment-stages.md`, which maps each stage to the log
   lines that mark it.

## Concurrency model

Two builds targeting the **same** `develop-NN` slot run concurrently. The
per-environment lock `eks-<ENVIRONMENT>` covers only the scale-up in
`prepare` and the `check rollout` stage; `build` runs unlocked, and `deploy`
takes only the global `config-repo` lock while it commits the HelmRelease. So
two same-slot builds both build and both commit, the later commit wins, and
they serialize only at rollout. Builds targeting different slots run fully in
parallel. Check `$JENKINS_URL/lockable-resources/` and the running builds
before triggering into a busy environment.

## Reading a build's outcome from the console log

| Console log signature | Meaning |
| --- | --- |
| `Pod [Pending][Unschedulable] ...` | The deploy agent is waiting on capacity; usually clears on its own within the build |
| `... not found` + `Error restarting X. Not a big deal` | The service has no matching cron/side deployment in this environment — expected/benign, not a build failure signal |
| `rollout status deploy <x>` then `exceeded its progress deadline` / `Timeout has been exceeded`, ending `Finished: ABORTED` | The newly deployed service stayed unready until the deadline — a genuine app/code issue in the deployed module, not a user abort. Report it as a failed rollout |
| `ERROR: resolveLatestTag: expected exactly one non-latest tag alongside :latest for <repo>, found N` | Mode `latest` hit an ECR image with zero or several real tags. Retrigger that service with `:rebuild` |
| `ArrayIndexOutOfBoundsException: Index <n> out of bounds` in `parseModulesForm` | The `MODULES` triple count no longer matches `jeevesPlatformInfo`'s module list. Run "Re-sync `SERVICES` with jenkins-library" below, then retrigger |
| `Couldn't find any revision to build` on a repo you did not target, within a minute or two of the trigger | The `MODULES` triples shifted position, so your branch landed on a neighbouring service whose repo has no such branch. The build stops at checkout, so nothing deployed. Run "Re-sync `SERVICES` with jenkins-library" below, rebuild the string with `scripts/modules.py`, and retrigger |

Diagnose from the console log, and from the pipeline source that
`deploy-develop-environment-stages.md` cites when a line needs explaining.

Every build result — success, failure and aborted — posts to the
`#jenkins-ci-dev` Slack channel via the pipeline's `slackSend` post-action
step.

## Re-sync `SERVICES` with jenkins-library

Run this when a triggered build fails with either positional signature above,
or when `--decode` reports a field count it cannot read.

1. Compare the script's `SERVICES` with `jenkins-library` master:

   ```bash
   git -C "${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/jenkins-library" fetch -q origin
   git -C "${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/jenkins-library" \
     show origin/master:vars/jeevesPlatformInfo.groovy \
     | python3 scripts/modules.py --check -
   ```

   - `SERVICES matches jenkins-library (N services)` means the order is current;
     look for the failure's cause in the console log instead.
   - On a mismatch it names the modules added and removed upstream and prints
     the full replacement `SERVICES` block.
2. Apply the change in `scripts/modules.py`, following
   `references/write-back.md` at the plugin root:
   - Replace `SERVICES` with the printed block.
   - Set `MAIN_BRANCH` to the modules with a `developmentbranch` other than `development` (today `simulationserver`, `aiweb`).
   - Update `tests/test_modules.py` where it names a removed module or the service count.
3. Run the tests, then rebuild `MODULES` and retrigger:

   ```bash
   python3 -m unittest discover -s scripts/tests -q
   ```

4. Report the result as the write-back rule says.

## Per-service deploy timing

Build durations derived from build history where **exactly one** service was
`enable=true` in the `MODULES` string, so the full build duration attributes
cleanly to that one service — a multi-service build's duration can't be
split back out per service since they build/deploy in parallel.

One row per service, carried forward across sessions. The job keeps builds
for one day (`logRotator(daysToKeepStr: '1')`), so a service's earlier samples
age out of the API while its row keeps them — merge a fresh sample into the
existing row (widen min/max, add to the sample size) rather than replacing it.
A service with no row yet gets one the first time a clean single-service build
appears for it. Record rows in `~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md`
in the same turn, creating the file with the first row when it doesn't exist yet (SKILL.md
has its header).

**How to derive/refine a row:** fetch recent builds' params and durations in
one batched request, filter to
`result == "SUCCESS"` builds whose `MODULES` string has exactly one
`enable=true` triple, and use that build's total `duration` as one sample for
that service:

```bash
TREE='builds[number,result,duration,actions[parameters[name,value]]]{0,300}'
jenkins-api "job/deploy-DEVELOP-environment/api/json?tree=${TREE}" \
  | python3 scripts/build-params.py --single-service
```

**Caveat:** these durations reflect a **single-service** build. A build
deploying multiple services at once (e.g. `web` + `accounting` + `aiservice`
together) runs them in parallel, so its total duration is closer to the
*slowest* of the enabled services' individual times, not their sum — use the
single-service numbers in `~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md`
as a per-service ceiling estimate, not an additive one.
