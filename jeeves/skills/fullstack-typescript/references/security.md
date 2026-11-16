# Security

Build security into the design; each new surface gets a threat pass before code.

## Threat pass

For each new endpoint, consumer, job or page, answer:

1. Who can reach it, and how are they authenticated?
2. What can they send, and where does it flow?
3. What is the worst outcome, and which control stops it?

## Trust boundaries

- Validate every external input at the edge with a schema (HTTP body, query, headers, queue messages, webhooks, files, environment variables).
- Derive the static type from the schema, and pass only the parsed value inward.
- Allow-list accepted fields; ignore or reject the rest, so a client cannot set `role` or `tenantId`.
- Verify webhook signatures with a constant-time comparison before parsing the body.

## Authentication and authorization

- Authenticate at the edge; authorize in the service, per resource, on every request.
- Take the tenant and user from the verified session, and include the tenant in every query's `WHERE`.
- Check ownership on reads as well as writes, including ids nested in the payload.
- Keep tokens short-lived, scoped and rotated; validate issuer, audience, expiry and algorithm.

## Secrets and sensitive data

- Load secrets from the secret store at runtime; keep them out of code, images, logs and error messages.
- Collect the minimum personal and financial data; encrypt it in transit and at rest.
- Redact by allow-list when logging objects.
- Return generic errors to clients, with a correlation id for the detailed log.

## Node risks and controls

| Risk | Control |
|---|---|
| SQL or NoSQL injection | Parameterized queries; typed query builders |
| Command injection | `execFile` with an argument array; fixed command names |
| Prototype pollution | Schema validation; `Object.create(null)` or `Map` for user-keyed data |
| SSRF | Allow-list of hosts; block private address ranges; no redirects to them |
| Path traversal | Resolve the path, then check it stays under the base directory |
| ReDoS | Linear-time patterns; a length limit before matching |
| Unbounded input | Body size limits, page limits, timeouts |
| Supply chain | Lockfile committed, pinned versions, audit in CI, few dependencies |

## Browser risks and controls

| Risk | Control |
|---|---|
| XSS | Render text through React; sanitize any HTML with a vetted library; a Content Security Policy |
| Token theft | Session in an `HttpOnly`, `Secure`, `SameSite` cookie |
| CSRF | `SameSite` cookies plus a CSRF token on state-changing requests |
| Open redirect | Redirect only to allow-listed or relative paths |
| Data in the bundle | Send the client only the fields it renders; keep secrets and internal flags on the server |
| Clickjacking | `frame-ancestors` in the Content Security Policy |

## Review prompts

- Can one tenant read or change another tenant's data through any id in this request?
- Does any log line, error or analytics event carry a secret or personal data?
- What happens when this input is 1,000 times larger, or repeated 1,000 times?
