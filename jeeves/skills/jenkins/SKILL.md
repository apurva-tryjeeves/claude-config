---
name: jenkins
description: Check dev Jenkins build and deployment status, console logs, build history, or the queue; diagnose a failed build; and trigger, retry, or abort one. Use when the user asks to deploy a branch to a develop-NN environment, check or debug a deployment or pipeline, check build status, or look at Jenkins.
---

# Jenkins Access

| Env  | Base URL                          | Secrets file                                    |
| ---- | ---------------------------------- | ------------------------------------------------ |
| dev  | https://jenkins.dev.tryjeeves.vpn  | `~/.config/jeeves/jenkins/dev.env`   |

This skill's actions — status, logs, trigger, retry, abort — apply to dev
Jenkins only.

- Connect over the Jeeves VPN.
- The secrets file exports `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`, and
  `JENKINS_CACERT`.
- `JENKINS_CACERT` points at the internal `tryjeeves` CA that the server's
  cert chains to. macOS trusts it, and curl trusts it through this file, so
  every call passes it explicitly.
- First-time setup of the secrets file is in the marketplace README. Regenerate
  the CA file from the macOS System Keychain when it goes missing:

```bash
security find-certificate -c "tryjeeves" -p /Library/Keychains/System.keychain > ~/.config/jeeves/jenkins/tryjeeves-ca.pem
```

## Use `jenkins-api`

- It ships in this plugin's `bin/`, which Claude Code puts on the Bash tool's
  `PATH` while the plugin is enabled, so the bare command resolves with no setup.
- It sources the secrets and supplies the CA and credentials.
- It percent-encodes `tree=` filters, so the logged command stays short and
  carries no token.

| Command | Returns |
| --- | --- |
| `jenkins-api status <job> [build]` | result, duration, timestamp (default `lastBuild`) |
| `jenkins-api builds <job> [n]` | the newest n builds (default 10) |
| `jenkins-api log <job> <build>` | the build's console text |
| `jenkins-api wait <job> <build> [timeout-min] [interval-sec]` | blocks until the build finishes (default 20 min, checking every 60 s), then prints its result and the last 40 log lines; exits 0 on `SUCCESS`, 1 on any other result, 2 on timeout |
| `jenkins-api queue` | what is waiting, and why |
| `jenkins-api queued <queue-id>` | the build number a trigger's queue item became (takes the id or the whole `Location` URL) |
| `jenkins-api url <job> [build]` | the browser URL, making no request |
| `jenkins-api crumb` | a CSRF crumb as `Jenkins-Crumb:<value>`, ready to pass as `-H` on a POST |

A `<job>` is the path after `/job/`, with nested folders separated by `/` —
`deploy-DEVELOP-environment`, or `wallet-service/development` for a folder or
multibranch pipeline.

```bash
jenkins-api status deploy-DEVELOP-environment
jenkins-api builds wallet-service/development 5
```

Anything the subcommands don't cover goes through as a raw API path, with extra
arguments passed to `curl`:

```bash
jenkins-api "job/<job>/<n>/api/json?tree=actions%5Bparameters%5Bname,value%5D%5D"
```

Set `JENKINS_API_DRYRUN=1` to print the URL a command would request instead of
sending it; every subcommand, `queued` and `crumb` included, stops after that
print.

## Name the build you mean

`status`/`builds` without a build number report `lastBuild` — the job's most
recent run across everyone using it. On a shared job such as
`deploy-DEVELOP-environment`, that is routinely another engineer's deploy to
another environment, so read it as "what the job ran last", and confirm whose
it is from its parameters before drawing a conclusion from it:

```bash
jenkins-api "job/<job>/<build>/api/json?tree=actions%5Bparameters%5Bname,value%5D%5D"
```

After triggering a build, capture the queue id from the POST's `Location`
header and resolve it to your build number while the item still exists —
Jenkins keeps a queue item for about five minutes past the build's start:

```bash
jenkins-api queued "$(sed -n 's/^location: //Ip' /tmp/trigger-headers.txt)"
```

Pass that number to every later `status` and `log` call.

Build history records what was built. To say what a `develop-NN` environment
runs now, ask the user, or have them read the Grafana "Environments overview"
dashboard (https://grafana.dev.tryjeeves.vpn/d/jpKChUH7z/environments-overview?orgId=1&refresh=30s)
and paste or screenshot the row. Say "unknown" until one of them gives it.

To report when a build finishes, run `wait` once with `run_in_background`. It
polls inside one process, so the session is woken a single time, when the build
ends:

```bash
jenkins-api wait deploy-DEVELOP-environment <build> 25
```

## Read a console log

```bash
jenkins-api log <job> <build> | tail -40
```

Read the tail first — Jenkins prints the actual failure near the end even
when the log is long or the failing step ran inside a `parallel` block. Pull
out the failing step for the user rather than pasting the whole log back.

Name a step only from the job's stages reference (see "Job-specific
references") or from the log line itself. For a step the reference leaves out,
read the pipeline source it cites, then add the step to the reference in the
same turn.

A `cms` build prints its whole `.env` build file into the log (`+ cat .env`).
Quote only the line you need from it.

## Diagnose, trigger, or check an agent

`references/build-ops.md` covers these heavier, less frequent operations,
kept out of the base skill:

- Diagnosing a failed build (concurrent-build workspace races)
- Triggering, retrying, or aborting a build
- Checking whether a build's EC2 agent is still alive

## Job-specific references

Some jobs have quirks (packed parameter formats, per-environment naming,
locking) worth documenting once rather than rediscovering. Check for a match
before working with a job:

| Job | Reference |
| --- | --- |
| `deploy-DEVELOP-environment` | `references/deploy-develop-environment.md` (parameters, deploy flow, failure signatures; timings live in `~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md`) |
| `deploy-DEVELOP-environment` | `references/deploy-develop-environment-stages.md` (what each stage does and the log lines that mark it; read before saying what a deploy is doing) |

## Scripts

| Script | Use it for |
| --- | --- |
| `scripts/modules.py` | Building and decoding `deploy-DEVELOP-environment`'s packed `MODULES` parameter — `--set`, `--decode`, `--list`, and `--check` against `jenkins-library` (see the deploy reference's re-sync step). It holds the service order, so every service keeps its own position, and enables only the services passed to `--set` |
| `scripts/build-table.py` | Rendering several builds as a markdown table with icons, durations and links |
| `scripts/build-params.py` | Reading a `builds[...]` response with parameters on stdin: `--building` lists running builds and their `ENVIRONMENT`, `--single-service` lists `service number duration` for SUCCESS builds that enabled one service, no flag prints a tab-separated row per build |

Change these scripts through the `jeeves:jeeves-python-engineer` agent.

All take a `scripts/`-relative path, so run them from this skill's own
directory (`cd` there first, or prefix the path).

Build a packed positional parameter with its script rather than assembling the
string by hand — position is the only thing the job reads, so the script's
count check is what keeps a value on the service you meant.

## Reporting results

Lead with the verdict line. Add detail below it only where that detail changes
what the user does next.

Icons, linking and value-rendering vocabulary live in the shared
`../../references/output-style.md` — follow it rather than inventing a format.
A Jenkins `result` maps onto it: `SUCCESS` ✅, `FAILURE` ❌, `UNSTABLE` ⚠️,
`ABORTED` ⛔, building ⏳. A deploy that ends `ABORTED` after `rollout status`
and `Timeout has been exceeded` is a failed rollout, not a user abort — report
it as ❌ and say so.

**One build** — one line: icon, result, a clickable build link, and a
human-readable duration.

> ✅ **SUCCESS** — [#44088](https://jenkins.dev.tryjeeves.vpn/job/deploy-DEVELOP-environment/44088/) · 9m27s

**Several builds** — pipe the API response through the table formatter, which
renders the icons, durations, local start times, and per-build links:

```bash
jenkins-api builds <job> 10 | python3 scripts/build-table.py "$(jenkins-api url <job> | sed 's|/lastBuild/$||')"
```

It also accepts a single build object, so the same script formats a
`lastBuild/api/json` response.

**A failure** — verdict line, then the handful of log lines carrying the failure
in a fenced block, then the root cause (a genuine code/config problem, or a
concurrent-build race per `references/build-ops.md`):

> ❌ **Rollout failed (ABORTED)** — [#45269](https://jenkins.dev.tryjeeves.vpn/job/deploy-DEVELOP-environment/45269/) · 18m29s
>
> ```text
> + kubectl --namespace develop-04 rollout status deploy api --watch
> error: deployment "api" exceeded its progress deadline
> Timeout has been exceeded
> ```
>
> The new `api` pod stayed unready until the deadline — an app issue in the deployed module.

**A running build** — elapsed so far, alongside the service's expected duration
from `~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md` when that file
has a row for it (elapsed alone otherwise), and the current stage named from
the job's stages reference:

> ⏳ **building** — [#44089](https://jenkins.dev.tryjeeves.vpn/job/deploy-DEVELOP-environment/44089/) · 3m20s elapsed, `api` usually takes ~8m56s · in `build` (image scan)

When a deploy finishes and exactly one service was enabled, that build is a
clean timing sample: merge it into that service's row in
`~/.claude/org-memory/jeevesinc/jenkins-deploy-timings.md` — widen min/max, add to the sample
size — in the same turn. When the file doesn't exist yet, create it with this first row, a
`reference` memory frontmatter (`name: jenkins-deploy-timings`) and the header
`| Service | Min | Max | Mean | Sample size |`, then index it in
`~/.claude/org-memory/jeevesinc/MEMORY.md`.

Keep the rest lean: name the failing step, and leave out the steps that
succeeded, the URLs the user already has, `jenkins-api` usage examples, the
restated context of what was asked, and a closing "want me to…?". A caveat
that changes the user's next move earns its words — an empty result that
reads as a failure, or a build whose parameters contradict the premise.
Something the user asked for in its own right — an audit, a comparison, a
build listing — stays as long as it needs to be. Filter with `tree=` and a
`jq` selector rather than piping whole objects through `jq .`.

Save a console log to a file when it needs more than a glance, then grep the
file — a `consoleText` body can run to thousands of lines:

```bash
jenkins-api log <job> <n> > /private/tmp/build.log
grep -nE 'ERROR|FAIL|Exception' /private/tmp/build.log | tail -20
```
