# Allow an invitee mail domain on a dev env

- For a domain missing from the list, tell the user before inviting and hand them these steps; the user makes each change:
  1. Append the domain to `ALLOWED_EMAIL_DOMAINS` in `/develop-NN/notification-service/notification-secrets` (AWS Secrets Manager, profile `jeeves_dev`).
  2. Sync the External Secrets Operator copy. It refreshes the pod's Kubernetes Secret every 1 h (`infra-helm-charts/AGENTS.md`), and a pod started before the sync keeps the old value.
  3. Redeploy `notification` on that env with `development:latest`. When the user asks you to run the redeploy, use Skill `jeeves:jenkins` and its confirmation.
- Confirm the new value took effect by inviting one person first: an empty `emailsNotSent` proves it.
