# Jenkins Build Ops — Diagnose, Trigger, and Agent Checks

## Diagnose a failed build

Read the console log tail for the error first, then check for a
**concurrent-build workspace race**:

- Pipeline jobs often use a workspace path with no build number in it (e.g.
  `workspace/<job-name>/<module>`).
- Two builds of the same job running at the same time on the same agent
  share that directory and collide on git's ref locks.
- The failing step in the console log looks like a `git fetch`/`git
  checkout` with an error such as `cannot lock ref ... File exists` or
  `Another git process seems to be running`.

Confirm the race by comparing the failed build's timestamp+duration window
against the adjacent build numbers:

```bash
jenkins-api builds <job> 20 | python3 -c "
import json,sys
builds = json.load(sys.stdin)['builds']
for b in builds:
    b['end'] = b['timestamp'] + b['duration']
for a, b in zip(builds, builds[1:]):
    overlap = min(a['end'], b['end']) - max(a['timestamp'], b['timestamp'])
    if overlap > 0:
        print(f\"#{a['number']} ({a['result']}) overlaps #{b['number']} ({b['result']}) by {overlap}ms\")
"
```

Read an overlap together with the git-lock error above — a job configured for
concurrent builds overlaps constantly by design (`deploy-DEVELOP-environment`
overlaps on most builds and locks per environment instead), so the error is
what makes the overlap meaningful. The two together confirm the race:

- The failed build lost the git lock to a concurrent run — retrigger it and
  it passes on its own.
- Report the race itself as the root cause, so the result reads as a CI
  concurrency problem rather than a code issue in the deployed module.
- For a lasting fix, point at the job's concurrency/workspace config: serialize
  its builds, or give each build/executor its own workspace.

## Trigger, retry, or abort a build

These change shared CI/deployment state, on dev Jenkins only. Confirm the
exact job and the action with the user before running any of them.

See `deploy-develop-environment.md` for a full worked trigger flow — checking
the target slot, fetching a CSRF crumb, `buildWithParameters`, then resolving
the queue id to your build number with `jenkins-api queued`. The same
mechanics apply to any job: swap in that job's name and parameters.

To **retry** a past build (e.g. a failed deploy), read its parameters, confirm
them with the user, and submit them fresh:

- For a plain job, resubmit the captured parameters as they are.
- For `deploy-DEVELOP-environment`, decode the captured `MODULES` with
  `python3 scripts/modules.py --decode`, confirm the enabled services and
  branches with the user, then build a new string with one `--set` per service.
  That applies the current mode rule and service order — the old string can
  carry a mode that already failed (`latest` on a feature branch) or an
  outdated layout.

```bash
jenkins-api "job/<job>/<build-number>/api/json" | python3 -c "
import json,sys
d = json.load(sys.stdin)
for a in d.get('actions', []):
    if a.get('_class') == 'hudson.model.ParametersAction':
        for p in a['parameters']:
            print(f\"{p['name']}={p['value']}\")
"
```

Abort a running build — POSTs need a CSRF crumb:

```bash
CRUMB=$(jenkins-api crumb)
jenkins-api "job/<job>/<build-number>/stop" -H "$CRUMB" -X POST
```

## Check whether a build's EC2 agent is still alive

- Jenkins build agents run on ephemeral EC2 instances tagged
  `Name=jenkins-worker` that terminate once their build finishes.
- A terminated agent takes its workspace with it, so retrigger the build to
  get a fresh agent and a clean workspace.

Confirm the instance is still running before reaching for SSH/SSM to inspect
a build's workspace on the agent (e.g. to hand-clean a file the console log
points at):

```bash
aws ec2 describe-instances --profile jeeves_dev --instance-ids <instance-id> --query "Reservations[0].Instances[0].{State:State.Name,Name:Tags[?Key=='Name']|[0].Value}"
```

The `jeeves_dev` AWS SSO profile comes from the marketplace README's AWS setup.
Refresh an expired token interactively:

```bash
aws sso login --profile jeeves_dev
```

The `Developers` SSO role supports EC2 instance-state checks
(`describe-instances`) as shown above. Confirm SSM session permissions
(`ssm:DescribeInstanceInformation` and similar) have been added to the role
before relying on direct SSM access to a live agent.
