# Send OpenSearch requests with awscurl

Both domains authenticate with AWS SigV4 and serve a certificate issued by the
private `CN=tryjeeves` CA. Take the endpoint, profile and region from the
environment table at the top of `SKILL.md`.

Shell variables are lost between Bash calls, so run this setup block and the
request in one Bash call:

```bash
# pick the row you need from the SKILL.md environment table
ENDPOINT="https://opensearch.prod.jeeves.vpn"
PROFILE="jeeves_prod"
REGION="us-east-1"

export SSL_CERT_FILE="$HOME/zscaler-merged-ca-bundle.pem"
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
eval "$(aws configure export-credentials --profile "$PROFILE" --format env)"

uvx awscurl --service es --region "$REGION" \
  -X <METHOD> "$ENDPOINT/<path>"
```

Append `-H 'Content-Type: application/json' -d '<json>'` to a request that
sends a body.

- Supply the SSO session with `aws configure export-credentials` — `awscurl`
  reads credentials from environment variables.
- Point both CA variables at `~/zscaler-merged-ca-bundle.pem`, which carries the
  `tryjeeves` root CA. When it is missing, ask the user to build it with
  [README → "3. CA bundle"](https://github.com/apurva-tryjeeves/claude-config#3-ca-bundle).
  A run against the stock trust store or `~/zscaler-root-ca.pem` reports
  `unable to get local issuer certificate`.
- Sign every request with `awscurl --service es`; the domain answers an unsigned
  `curl` with `HTTP 401`.
