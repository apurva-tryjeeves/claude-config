---
name: invite-dev-company-user
description: Invite a user to a company on a Jeeves develop-NN env via the CMS admin API, then confirm the invite, its mail and its acceptance in the DB. Trigger when asked to invite, add or onboard a user to a dev company (e.g. "invite Jane Doe as Manager to company 12 on dev-16"), to check whether dev invites were sent or accepted, or to cancel one.
---

# Invite a User to a Dev Company

Log in to the CMS admin API, invite the user to the company, confirm the
pending invite in the backend database, and confirm the new user once the
invite is accepted.

| Env | CMS page | API base | Database |
| --- | --- | --- | --- |
| `develop-NN` | `https://admin-develop-NN.dev.tryjeeves.vpn/admin/login` | `https://api-develop-NN.dev.tryjeeves.com` | `develop_NN` (`jsql dev-NN/develop`) |

## Inputs

Collect these before calling the API:

- env, e.g. `develop-16`
- `companyId`
- for each person: first name, last name, email as typed, and role
- role is sent as its display name: `Admin`, `Employee`, `Bookkeeper`, `Manager` or `Finance`
- names in letters and spaces only, with accents dropped (`Matías` → `Matias`)

When the role is missing, list those five in a plain chat message and ask for
one; the list is longer than an `AskUserQuestion` holds.

## Confirmed envs

`references/confirmed-envs.md` lists the envs where this flow has run end to
end, with the Keychain item each one logs in with. Read it before the first
call and use that env's item in step 3; an env with no row uses
`jeeves-cms-dev`. After the first run on a new env, add its row in that same
turn.

## CMS admin credentials

The CMS super-admin login lives in the macOS Keychain item `jeeves-cms-dev`:
the email is the account and the password is the secret. When the item is
missing, ask the user to create it (the trailing `-w` prompts for the
password, keeping it out of shell history):

```bash
security add-generic-password -U -s jeeves-cms-dev -a '<cms-admin-email>' -w
```

## Flow

1. **Confirm the company exists** on that env (load Skill `jeeves:mysql` first):

   ```bash
   jsql dev-NN/develop 'SELECT id, name, status FROM companies WHERE id = <companyId>'
   ```

2. **Confirm the invite mail can go out.** Outside production,
   notification-service mails only `@tryjeeves.com` plus the domains in
   `ALLOWED_EMAIL_DOMAINS`, a comma-separated string such as
   `@conexa.ai,@acme.com` (`notification-service`
   `src/services/email/email-service.ts`). It reads that key from two
   secrets; print it from each:

   ```bash
   for s in /develop-NN/notification-service/notification-secrets \
            /shared/notification-service/notification-secrets; do
     AWS_PROFILE=jeeves_dev AWS_REGION=us-east-2 aws secretsmanager get-secret-value \
       --secret-id "${s}" --query SecretString --output text \
       | jq -r --arg s "${s}" '"\($s): \(.ALLOWED_EMAIL_DOMAINS // "(not set)")"'
   done
   ```

   Then confirm the company has no `DISABLED_EMAIL_TYPE` tag listing `INVITE_USERS`:

   ```bash
   jsql dev-NN/develop '
   SELECT tag, extra FROM company_tags
   WHERE companyId = <companyId> AND tag = "DISABLED_EMAIL_TYPE"
   '
   ```

   - The mail goes out when every invitee's domain is `@tryjeeves.com` or listed, and the tag query is empty.
   - For a domain missing from the list, tell the user before inviting.
   - The fix is to append the domain to `ALLOWED_EMAIL_DOMAINS` in `/develop-NN/notification-service/notification-secrets`, then redeploy `notification` on that env (Skill `jeeves:jenkins`, `development:latest`).
   - Both change shared state; make them on the user's go-ahead.
   - The External Secrets Operator copies the secret into the pod's Kubernetes Secret on a 1 h refresh (`infra-helm-charts/AGENTS.md`). Ask the user to sync it before the redeploy; a pod started earlier keeps the old value.
   - Confirm the new value took effect by inviting one person first: an empty `emailsNotSent` proves it.
   - Record each env's list in `references/confirmed-envs.md` → "Mail delivery per env".

3. **Log in and invite in one Bash call.** The `secretToken` from login
   expires 60 seconds after it is issued, so fetch it and use it in the same
   command. The token and password stay in variables; only the invite
   response prints.

   ```bash
   API="https://api-develop-NN.dev.tryjeeves.com"
   ITEM="jeeves-cms-dev"   # the env's item from references/confirmed-envs.md
   export CMS_EMAIL="$(security find-generic-password -s "${ITEM}" \
     | awk -F'"' '/"acct"/ {print $4}')"
   export CMS_PASS="$(security find-generic-password -s "${ITEM}" -w)"
   TOKEN="$(jq -n '{email: env.CMS_EMAIL, password: env.CMS_PASS, ipAddress: "127.0.0.1"}' \
     | curl -sS "${API}/v2/admin/login" \
         -H 'content-type: application/json' -H 'platform-type: admin' \
         -H 'x-client-address: 127.0.0.1' \
         --data @- \
     | jq -r '.data.secretToken')"
   jq -n --arg c '<companyId>' --arg f '<firstName>' --arg l '<lastName>' \
         --arg m '<email>' --arg r '<Role>' \
     '{users: [{firstName: $f, lastName: $l, email: $m, role: $r}], companyId: $c}' \
     | curl -sS "${API}/v2/admin/invite-users" \
         -H 'content-type: application/json' -H 'platform-type: admin' \
         -H 'x-client-address: 127.0.0.1' \
         -H "x-auth-token: ${TOKEN}" \
         --data @-
   ```

   - `companyId` goes in as a string.
   - To invite several people to one company, put one entry per person in `users`; one call creates every invite.
   - Success is `"status": true` with `"msg": "Invitation mail successfully sent."`; the invite rows exist from here on.
   - **Mail sent check:** an empty `data.emailsNotSent` confirms every invite mail went out.
   - notification-service logs each send as `Sending email result: [{"status":true,...}]` with an SES `MessageId`; search `app_name.keyword` `notification-service` for that phrase (Skill `jeeves:opensearch`) to confirm a send.
   - Each address in `emailsNotSent` still has its invite row, without a mail. Report the list; to re-send, cancel those invites (see "Cancel an invite") and rerun this step for those people.
   - When `TOKEN` comes back `null`, check the Keychain item's email and password, then rerun the call.

4. **Confirm the invite rows and their mail.** Look the invites up by `normalizedEmail`, the address as typed, listing every invited address. The join reads each invite's mail from `notification_audits`:

   ```bash
   jsql dev-NN/develop '
   SELECT i.id, i.companyId, i.email, i.normalizedEmail, i.role, i.status,
          i.createdUserId, i.createdAt,
          IF(a.awsMessageId IS NOT NULL, "sent", "not sent") AS mail, a.id AS auditId
   FROM invite_users i
   LEFT JOIN notification_audits a
     ON a.toEmail = i.normalizedEmail
    AND a.emailType = "INVITE_USERS"
    AND a.createdAt BETWEEN i.createdAt AND i.createdAt + INTERVAL 10 SECOND
   WHERE i.companyId = <companyId>
     AND i.normalizedEmail IN ("<email1>", "<email2>")
     AND i.deletedAt IS NULL
   ORDER BY i.id
   '
   ```

   - Success is one row per invited address, each with `status` `pending`, the role in lowercase (e.g. `manager`), `createdUserId` `NULL`, and `mail` `sent`.
   - `mail` `sent` means notification-service wrote an audit row with an SES `awsMessageId`; this is the database record of the mail sent check.
   - `notification_audits.toEmail` holds the address with any `+alias` removed, so the join matches on `normalizedEmail` and the send time (within 10 s of the invite). An alias invite's mail lands in the person's normal inbox.
   - `email` is the address the invitee signs up with.
   - The invite keeps the typed address while no live user or invite holds it.
   - When one does, the invite gets an alias `<local>+<companyId>-<8 hex>@<domain>`, e.g. `jane+12-75179971@tryjeeves.com`.
   - One person can therefore hold live invites to several companies: the typed address for the first, an alias for each later one.
   - A cancelled invite (`deletedAt` set) that holds the typed address is renamed to an alias, and the new invite keeps the typed address.
   - Both rules live in backend `modules/v2/web/user/userService.js`: `generateUniqueEmailForNewUser` and `freeUpDeletedEmailsForReuse`.
   - `createdAt` is UTC; add 5 h 30 min when quoting it in IST.

5. **Confirm the acceptance** once the user says the invitee has signed up.
   Acceptance does three things in the same second:

   - sets `invite_users.status` to `active`
   - fills `invite_users.createdUserId`
   - creates the `users` row with the invite's `email`

   ```bash
   jsql dev-NN/develop '
   SELECT i.id AS inviteId, i.status AS inviteStatus, u.id AS userId, u.uuid, u.companyId,
          u.email, u.role, u.status AS userStatus, u.createdAt
   FROM invite_users i
   JOIN users u ON u.id = i.createdUserId
   WHERE i.companyId = <companyId> AND i.normalizedEmail = "<email>"
   ORDER BY i.id DESC
   LIMIT 1
   '
   ```

   - Success is one row with `inviteStatus` and `userStatus` both `active`, and the invite's `email`.
   - An empty result means no user exists for the invite yet; rerun step 4 to show its `status`.

## Check invite status

Answer "were the invites sent, and has anyone signed up?" for one or more
companies with one query: `invite_users` for the invite, `notification_audits`
for its mail, `users` for its acceptance.

```bash
jsql dev-NN/develop '
SELECT i.id, i.companyId, i.email, i.role, i.status,
       IF(a.awsMessageId IS NOT NULL, "sent", "not sent") AS mail, a.id AS auditId,
       u.id AS userId, u.status AS userStatus, i.createdAt
FROM invite_users i
LEFT JOIN notification_audits a
  ON a.toEmail = i.normalizedEmail
 AND a.emailType = "INVITE_USERS"
 AND a.createdAt BETWEEN i.createdAt AND i.createdAt + INTERVAL 10 SECOND
LEFT JOIN users u ON u.id = i.createdUserId
WHERE i.companyId IN (<companyId>)
  AND i.deletedAt IS NULL
ORDER BY i.companyId, i.id
'
```

- `mail` `sent`: notification-service wrote an audit row with an SES `awsMessageId`.
- `mail` `not sent`: the mail stopped before SES, which on a dev env means a recipient domain outside `ALLOWED_EMAIL_DOMAINS` (step 2).
- `status` `pending` with `userId` `NULL`: invited, sign-up still open.
- `status` `active` with `userId` set: accepted; `userStatus` is the new user's status.
- The invite API answers `"Invitation mail successfully sent."` whether or not a mail went out, so this query (or `emailsNotSent`) is the record of what was sent.

## Cancel an invite

Cancel a `pending` invite to re-send its mail or to drop it. Run step 3's
`API`, `ITEM`, `CMS_*` and `TOKEN` lines, then post each invite `id` in the same
Bash call:

```bash
for id in <inviteId1> <inviteId2>; do
  curl -sS "${API}/v2/admin/cancel-user-invitation" \
    -H 'content-type: application/json' -H 'platform-type: admin' \
    -H 'x-client-address: 127.0.0.1' \
    -H "x-auth-token: ${TOKEN}" \
    --data "{\"id\":${id}}"
  echo
done
```

- Success is `{"msg":"Success.","status":true}` per id.
- The row turns `in-active` with `deletedAt` set:

  ```bash
  jsql dev-NN/develop '
  SELECT id, status, deletedAt FROM invite_users
  WHERE id IN (<inviteId1>, <inviteId2>)
  '
  ```

- A cancelled invite frees its address: the next invite for that person keeps the typed address.

## Reporting results

Answer with the row from the step just run and stop:

- After the invite (step 4): one markdown table with a row per invite, every value from step 4's query: `id`, `companyId`, `email`, `role`, `status`, Email (`✅ sent (audit <auditId>)` or `❌ not sent`), `createdAt` (in IST).
- After acceptance (step 5): one markdown table of the joined row, with `uuid` in full and `createdAt` in IST.
- After a cancel: one markdown table of `id`, `status`, `deletedAt` (in IST).
- After a status check: one markdown table with a row per invite: `id`, `companyId`, `email`, `role`, `status`, Email (`✅ sent (audit <auditId>)` or `❌ not sent`), acceptance (`userId` or `pending`), `createdAt` (in IST).
- When `email` differs from `normalizedEmail`, add one line saying the invitee signs up with the alias.
- Add a line only for addresses in `emailsNotSent` or an invited address with no row.
- Leave out the API response body, the token, the curl commands and next-step suggestions.
