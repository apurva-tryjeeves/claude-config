# `debezium-connector-operations` (dev Jenkins)

Restarts a `develop-NN` env's Debezium UTV (universal transaction view) connector with fresh offsets. Use it when the env stops producing UTV rows, usually after its pods are scaled up.

Job: [debezium-connector-operations](https://jenkins.dev.tryjeeves.vpn/job/debezium-connector-operations/) (VPN on). Confirm the env with the user before each build, as for any trigger (`build-ops.md`).

## Restart flow

1. Open the job → **Build with Parameters**.
2. Run `action` = `stop` for the dev env; wait for it to finish.
3. Run `action` = `restart-delete` for the same env; wait for it to finish.
4. After a few minutes, have the user confirm the connector is healthy in Grafana.
5. Create new transactions on the env and confirm they reach UTV and accounting.

Use `restart-delete`, which clears the offsets; the plain `restart` in `debezium-connector-manage` leaves the pipeline failing.

| Source | What it gives |
| --- | --- |
| Ashwin Yadav, Slack DM, 19 Jun 2026 | The stop → `restart-delete` sequence |
| [universal-transactions-processor-js](https://github.com/JeevesInc/universal-transactions-processor-js) | The UTV code |
