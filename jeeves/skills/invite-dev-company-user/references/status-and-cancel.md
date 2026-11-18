# Check invite status and cancel an invite

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
- `mail` `not sent`: the mail stopped before SES, which on a dev env means a recipient domain outside `ALLOWED_EMAIL_DOMAINS` (`SKILL.md` → Flow step 2).
- `status` `pending` with `userId` `NULL`: invited, sign-up still open.
- `status` `active` with `userId` set: accepted; `userStatus` is the new user's status.
- The invite API answers `"Invitation mail successfully sent."` whether or not a mail went out, so this query (or `emailsNotSent`) is the record of what was sent.

## Cancel an invite

Cancel a `pending` invite to re-send its mail or to drop it. Show the env,
the company and one row per invite with `id`, `email` and `role`, then wait
for the user's yes. Then run `SKILL.md` → Flow step 3's `API`, `ITEM`, `CMS_*` and `TOKEN`
lines and post each invite `id` in the same Bash call:

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

- After a cancel: one markdown table of `id`, `status`, `deletedAt` (in local time).
- After a status check: one markdown table with a row per invite: `id`, `companyId`, `email`, `role`, `status`, Email (`✅ sent (audit <auditId>)` or `❌ not sent`), acceptance (`userId` or `pending`), `createdAt` (in local time).
