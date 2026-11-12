# `deploy-DEVELOP-environment` — what each stage does

The stage-by-stage flow of one deploy, with the console-log lines that mark
each step. Read it before describing what a running or finished deploy is
doing, and name a step only from this file or the console log.

Sources, read on 2026-11-12:

| Source | Holds |
|---|---|
| `jenkins-pipelines` → `deploy/deploy-DEVELOP-environment.jenkins` | The stages, locks and timeouts |
| `jenkins-library` → `vars/buildUtils.groovy` (`buildModules`), `buildService.groovy`, `buildCMS.groovy`, `dockerBuildAndPush.groovy`, `imageScan.groovy`, `resources/security/image-scan.sh` | The per-service build |
| `jenkins-library` → `vars/jeevesUtils.groovy` (`parseModulesForm`, `checkRollout`), `flux.groovy`, `eks.groovy` | Parsing, the HelmRelease update and the rollout check |
| Build #46681 (`develop-07`, `accounting` + `cms`, both `rebuild`) | The log lines quoted below |

When a log shows a step this file leaves out, read the pipeline source above,
then add the step here in the same turn.

## Timeouts and locks

| Scope | Limit or lock |
|---|---|
| Whole build | 3 h timeout |
| `prepare`, scale-up | Lock `eks-<env>` |
| `prepare`, git setup | Lock `git-config` |
| `deploy` | Lock `config-repo`, 2 min timeout |
| `check rollout` | Lock `eks-<env>`, 10 min timeout on the rollout watch |

`Resource [<name>] did not exist. Created.` is Jenkins creating the lock on
first use.

## 1. Agent and checkout (before `prepare`)

| Step | Log lines |
|---|---|
| Load `jenkins-library` at `master` | `Loading library jeeves@master`, then `Checking out Revision <sha> (master)` |
| Schedule the Kubernetes deploy pod (`pod-templates/developWorkerSpot.yml`) | `Pod [Pending][Unschedulable] ...` while a spot node comes up, then `Agent ... is provisioned` |
| Check out `jenkins-pipelines` | `(Declarative: Checkout SCM)`, `Cloning repository git@github.com:JeevesInc/jenkins-pipelines` |

## 2. `prepare`

| Step | Log lines |
|---|---|
| Parse `MODULES` into one entry per service (`parseModulesForm`) | `input: <MODULES>`, then `params map:` with `enable`, `image`, `branch`, `rebuild` per service |
| Stop on `develop-14`/`develop-15` (FluxCD image automation) | `... is managed with FluxCD image automation`, build `ABORTED` |
| Name the target | `Namespace: <env>`, `Helm release: jeeves-<env>` |
| Scale every deployment in the env to 1 replica, without waiting | `kubectl -n <env> scale deploy --all --replicas=1`, one `deployment.apps/<name> scaled` per deployment |
| Set each enabled service's starting tag: `latest` for a rebuild, the resolved real tag for a `latest`-mode `development` deploy (`ecr.resolveLatestTag`) | `Init modules tags: [<service>:<tag>, ...]` |
| Configure git and SSH for the config-repo push | `git config --global user.name 'Jenkins Jeeves'`, `ssh-keyscan github.com` |

`rebuild` is true when the service is enabled and its mode is `rebuild` or its
branch is not `development`.

## 3. `build`

One parallel branch per service to rebuild, on an EC2 build agent
(`jenkins-worker-build`), all failing fast together. `cms` builds whenever it
is enabled, in either mode.

| Step | Log lines |
|---|---|
| Start the branches | `Service key: <service>, branch: <branch>`, `[Pipeline] { (Branch: <service>)` |
| Wait for the EC2 build agent | `Still waiting to schedule task`, `'EC2 (ec2-jeeves-dev) - jenkins-worker-build (i-...)' is offline`, then `Running on EC2 ...` |
| Log in to ECR | `docker login ... 558433362422.dkr.ecr.us-east-2.amazonaws.com`, `Login Succeeded` |
| Shallow-clone the service repo at the branch | `Cloning repository git@github.com:JeevesInc/<repo>`, `Checking out Revision <sha> (refs/remotes/origin/<branch>)`, `Commit message: "<subject>"` |
| cms only: write `.env` from Secrets Manager `/build/cms/env-dev-aws-tryjeeves`, fill in the env name, print it | `secretsmanager get-secret-value --secret-id /build/cms/env-dev-aws-tryjeeves`, `sed -i 's/{{env_name}}/<env>/g' .env`, `+ cat .env` followed by the file |
| Build the image | `docker build ... -t .../jeeves-<repo>:<tag> -f Dockerfile .` (`Dockerfile.eks` for cms) |
| Scan the image before the push (`image-scan.sh gate`, Trivy and Grype) | `image-scan: <repo> CRITICAL=<n> HIGH=<n> ... gating=<n> mode=audit` |
| Push the image | `docker push .../jeeves-<repo>:<tag>`, `<tag>: digest: sha256:...` |
| Publish the scan and SBOM (`image-scan.sh publish`, Cosign) | `image-scan: <repo> published trivy report and attested CycloneDX SBOM for ...` |
| Collect the new tags | `Updated modules tags: [<service>:<tag>, ...]` |

Tag formats:

| Service | Tag |
|---|---|
| Most services (`buildService`) | `<branch with / as ->-<short sha>-b<yyyyMMddHHmmss>`, for example `jai-dev-acc-1640-4f99402-b20261112115825` |
| `cms` (`buildCMS`) | `<env>-<branch>-<short sha>-b<timestamp>`, for example `develop-07-jai-dev-acc-1642-4290d1f-b20261112115825` |

The scan gate runs in `audit` mode on this job: it reports the counts and the
build carries on. In `block` mode a gating finding fails the build.

## 4. `deploy`

Runs when at least one service has a tag.

| Step | Log lines |
|---|---|
| Clone `infra-deploy-config-development` at `master` | `git clone git@github.com:JeevesInc/infra-deploy-config-development.git -b master . --depth=1` |
| Set each enabled service's `image.tag` (and `enabled: true`) in `us-east-2/helm-releases/jeeves-<env>.yml` | `git --no-pager diff` showing `-        tag: <old>` and `+        tag: <new>` per service |
| Commit and push to `master` | `[Jenkins] Update jeeves-<env> with deploy-DEVELOP-environment n. <build>`, then `remote: Bypassed rule violations for refs/heads/master` and `master -> master` |

The diff's `-        tag:` line is the tag that service ran before this
deploy.

## 5. `check rollout`

| Step | Log lines |
|---|---|
| Make FluxCD fetch the new config commit | `flux reconcile source git flux-system`, `✔ fetched revision master@sha1:<commit>`, then two 10 s sleeps |
| Restart the deployments of every enabled service in `latest` mode | `Modules with latest tag: [...]`, then `kubectl ... rollout restart deploy <name>` each. A rebuild lists `[]` here: its new tag in the HelmRelease rolls the pods instead |
| Watch each deployment of each enabled service roll out, one at a time | `Deployment list: [<deployments>]`, `kubectl -n <env> get deploy <name>`, `kubectl --namespace <env> rollout status deploy <name> --watch`, then `deployment "<name>" successfully rolled out` |

Deployments per service come from `jeevesPlatformInfo.modules[<service>].deployment`,
for example `cms` → `cms`, and `accounting` → `accounting-api`,
`accounting-worker`, `accounting-jobexecutor`. A listed deployment missing
from the env logs `Deployment [<name>] not found: skip`.

`Waiting for deployment "<name>" rollout to finish: 1 old replicas are pending termination...`
is kubectl reporting that the new replicas are updated and an old one is
still running.

When a watch outlasts the 10 min timeout, the log reads, in order:

```text
Cancelling nested steps due to timeout
Sending interrupt signal to process
error: deployment "<name>" exceeded its progress deadline
Timeout has been exceeded
Finished: ABORTED
```

The deployments after it in the list are left unchecked, and the HelmRelease
commit from `deploy` stays in place, so FluxCD keeps applying the new tag.
Report it as a failed rollout per SKILL.md → "Reporting results".

## 6. Post

`(Declarative: Post Actions)` runs `slackSend` to `#jenkins-ci-dev` with the
result, the env and the service → tag map, then the log ends with
`Finished: <RESULT>`.
