# Jeeves Claude Code marketplace

The `jeeves` plugin: skills and agents for JeevesInc engineering work — Linear,
Jenkins, MySQL, OpenSearch, AWS secrets, releases, and the git/PR, logging, SQS
and SonarCloud conventions.

## Requirements

| Need | Used by |
|---|---|
| macOS (company laptop) | Keychain CA export for Jenkins and OpenSearch |
| Jeeves VPN connected | Jenkins, OpenSearch, MySQL |
| AWS SSO access to Jeeves Dev and Production | `aws-secrets`, `opensearch`, `mysql`, `jenkins` |
| `gh` (logged in to GitHub), `jq`, `uv`, Node.js | CLIs and MCP servers below |
| `mysql-client@8.4` | `jsql` |
| claude.ai Slack connector | `release-notify` |

```bash
brew install gh jq uv node mysql-client@8.4
gh auth login
```

## 1. Install the plugin

In Claude Code:

```text
/plugin marketplace add apurva-tryjeeves/claude-config
/plugin install jeeves@jeeves-local
```

Pull later updates with:

```text
/plugin marketplace update jeeves-local
```

## 2. AWS SSO profiles

Add these to `~/.aws/config` — the skills and MCP servers call them by name:

```ini
[sso-session jeeves_dev]
sso_start_url = https://jeeves.awsapps.com/start
sso_region = us-east-2
sso_registration_scopes = sso:account:access

[profile jeeves_dev]
sso_session = jeeves_dev
sso_account_id = 558433362422
sso_role_name = Developers
region = us-east-2

[profile jeeves_prod]
sso_session = jeeves_dev
sso_account_id = 642613937634
sso_role_name = Developers
region = us-east-1
```

One login covers both profiles:

```bash
aws sso login --profile jeeves_dev
```

## 3. CA bundle

The internal hosts serve certificates from the `tryjeeves` CA, and traffic runs
through Zscaler. Build one bundle holding the public roots plus both:

```bash
{
  cat "$(python3 -c 'import certifi; print(certifi.where())')"
  security find-certificate -c "tryjeeves" -p /Library/Keychains/System.keychain
  security find-certificate -c "Zscaler Root CA" -p /Library/Keychains/System.keychain
} > ~/zscaler-merged-ca-bundle.pem
```

`certifi` comes with `pip3 install certifi` if Python reports it missing.

## 4. MCP servers

Skills and agents call tools as `mcp__<server>__<tool>`, so add each server
under exactly this name:

| Server | Used by |
|---|---|
| `opensearch-dev`, `opensearch-prod` | `opensearch`, `trace-tx`, `prod-debug`, `post-deploy-verify`, `prod-log-investigator` agent |
| `linear` | `linear`, `feature-plan`, `jaidev` |
| `notion` | `notion-templates`, `release-notify`, `hotfix-captain` agent |
| `github` | `feature-plan` |

```bash
claude mcp add --scope user --transport http linear https://mcp.linear.app/mcp
claude mcp add --scope user --transport http notion https://mcp.notion.com/mcp

claude mcp add-json --scope user github "$(cat <<EOF
{"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
 "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "$(gh auth token)"}}
EOF
)"

for env in dev prod; do
  if [ "$env" = dev ]; then url=https://opensearch.dev.tryjeeves.vpn; region=us-east-2
  else url=https://opensearch.prod.jeeves.vpn; region=us-east-1; fi
  claude mcp add-json --scope user "opensearch-$env" "$(cat <<EOF
{"command": "uvx", "args": ["opensearch-mcp-server-py"],
 "env": {"OPENSEARCH_URL": "$url", "AWS_REGION": "$region", "AWS_PROFILE": "jeeves_$env",
         "OPENSEARCH_DISABLED_TOOLS": "GenericOpenSearchApiTool",
         "SSL_CERT_FILE": "$HOME/zscaler-merged-ca-bundle.pem",
         "REQUESTS_CA_BUNDLE": "$HOME/zscaler-merged-ca-bundle.pem"}}
EOF
)"
done
```

Then run `/mcp` in Claude Code and authenticate `linear` and `notion`. Turn on
the Slack connector at claude.ai → Settings → Connectors.

## 5. Credentials and settings

| What | Used by | Set it up |
|---|---|---|
| `~/.config/jeeves/mysql/<env>.env` (dev, preprod) | `mysql`, `trace-tx`, `provision-wallet-via-sql`, `invite-dev-company-user` | In Claude Code run `! jsql-pull-secrets` — it pulls every dev/preprod file from Secrets Manager |
| `~/.config/jeeves/mysql/prod.env` | `mysql` (prod), `trace-tx`, `prod-debug` | Create by hand from Keeper — see below |
| Keychain item `jeeves-cms-dev` | `invite-dev-company-user` | Run `security add-generic-password -U -s jeeves-cms-dev -a '<cms-admin-email>' -w` and enter the CMS super-admin password at the prompt |
| `~/.config/jeeves/jenkins/dev.env` | `jenkins` | Create by hand — see below |
| `SONAR_TOKEN` | `sonar-fix` | sonarcloud.io → My Account → Security → generate a token, then `export SONAR_TOKEN=…` in `~/.zshrc` |
| `JEEVES_REPOS_DIR` (optional) | `jenkins`, `sync-repos` | Where your repo checkouts live; defaults to `~/github/JeevesInc` |
| `JEEVES_RELEASE_CHANNEL_ID` (optional) | `release-notify` | Overrides the default `#deployments` channel id |
| `JEEVES_PLUGIN_SRC` (optional) | skills that record what they learn | Your clone of this repo; defaults to `~/github/apurva-tryjeeves/claude-config` — see Contributing |

**`prod.env`** — copy the prod read-replica credentials from Keeper into the
same format the pull writes:

```bash
cat > ~/.config/jeeves/mysql/prod.env <<'EOF'
MYSQL_HOST=<prod read-replica host>
MYSQL_PORT=3306
MYSQL_USER=<user>
MYSQL_PASS=<password>
MYSQL_DB=<default database>
MYSQL_SSL=<as in your preprod.env>
EOF
chmod 600 ~/.config/jeeves/mysql/prod.env
```

**Jenkins `dev.env`** — generate an API token at
https://jenkins.dev.tryjeeves.vpn → your name → Configure → API Token, then:

```bash
mkdir -p ~/.config/jeeves/jenkins && chmod 700 ~/.config/jeeves/jenkins
security find-certificate -c "tryjeeves" -p /Library/Keychains/System.keychain \
  > ~/.config/jeeves/jenkins/tryjeeves-ca.pem
cat > ~/.config/jeeves/jenkins/dev.env <<EOF
export JENKINS_URL=https://jenkins.dev.tryjeeves.vpn
export JENKINS_USER=<your Jenkins username>
export JENKINS_TOKEN=<API token>
export JENKINS_CACERT=$HOME/.config/jeeves/jenkins/tryjeeves-ca.pem
EOF
chmod 600 ~/.config/jeeves/jenkins/dev.env
```

## 6. Check the setup

In Claude Code:

```text
! jsql dev-01 "SELECT 1;"
! jenkins-api queue
/mcp
```

A row from `jsql`, a queue listing from `jenkins-api`, and every server above
marked connected in `/mcp` means the plugin is ready.

## Optional: PRD-to-release workflows

`feature-plan` and `post-deploy-verify` hand off to the `prd-split`,
`prd-implement` and `release-test` workflows when they are installed in your
`.claude/workflows/`. Both skills run on their own without them.

## Contributing, and keeping what skills learn

Several skills record facts they discover back into their own files:

| Skill | File it updates (from the plugin root, `jeeves/`) |
|---|---|
| `jaidev` | `skills/jaidev/references/jaidev-reference.md`, `skills/jaidev/references/repo-notes.md` |
| `jenkins` | `skills/jenkins/scripts/modules.py`, `skills/jenkins/references/deploy-develop-environment.md`, `skills/jenkins/references/deploy-develop-environment-stages.md` |
| `mysql`, `trace-tx`, `feature-plan`, `post-deploy-verify` | `references/queries.md`, `skills/mysql/references/schema/` |
| `linear` | `skills/linear/references/repo-team-project-map.md` |
| `notion-templates` | `skills/notion-templates/references/release-page.md` |
| `opensearch` | `skills/opensearch/references/alerting-api.md` |
| `aws-secrets` | `skills/aws-secrets/references/secrets-manager.md` |
| `invite-dev-company-user` | `skills/invite-dev-company-user/references/confirmed-envs.md` |
| `git-preferences` | `skills/git-preferences/SKILL.md` |
| `sonar-proactive-rules` | `skills/sonar-proactive-rules/references/sonar-ts-rules-catalog.md` |

Claude Code runs the plugin from a versioned copy under
`~/.claude/plugins/cache/jeeves-local/jeeves/<version>/`, which each update
replaces, so skills write what they learn into your clone of this repo instead:

```bash
git clone git@github.com:apurva-tryjeeves/claude-config.git ~/github/apurva-tryjeeves/claude-config
```

Set `JEEVES_PLUGIN_SRC` when the clone lives elsewhere. Skills follow
[`jeeves/references/write-back.md`](jeeves/references/write-back.md): they read
the clone's copy of these files when it exists, leave their edits uncommitted
there, and tell you when one is ready. Review it, bump `version` in
`jeeves/.claude-plugin/plugin.json`, then commit, push and open a PR. Once it
merges, `/plugin marketplace update jeeves-local` brings the new version to
everyone. Without a clone, skills report the new fact and the edit they would
make.

Timing samples stay on your machine, in `~/.claude/org-memory/jeevesinc/`,
since they change with every run:

| Skill | File |
|---|---|
| `git-preferences`, `jaidev` | `ci-check-timing.md` |
| `jenkins` | `jenkins-deploy-timings.md` |
| `jaidev` | `jaidev-run-timings.md` |

A skill reads its file when it exists and creates it with the first sample.
