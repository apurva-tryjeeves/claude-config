# Bank feeds (Codat → Xero)

Debug a company whose bank feed stopped reaching its ERP. accounting-service
pushes each Jeeves account's settled transactions to Codat, and Codat forwards
them to the ERP (Xero) as bank statement lines.

| Source | Holds | Reach it with |
|---|---|---|
| `${CLAUDE_SKILL_DIR}/references/bank-feed-queries.sql` | Every query below, numbered, with a `params` CTE to fill in | `jsql prod/<db> '<block>'` (Skill `jeeves:mysql`) |
| `${CLAUDE_SKILL_DIR}/scripts/codat-bank-feeds.sh` | Codat reads (`read`) and the feed remap (`remap`) | Codat API key, asked for at run time |
| accounting-service | The push code | `${JEEVES_REPOS_DIR:-$HOME/github/JeevesInc}/accounting-service` |

## 🔁 How a push works

- **Schedule:** a bank-feed `job` runs hourly at :15 per account; each push call is a `batch`, and each line in it a `bank_feeds_sync_history` row (`payload` = the line sent).
- **Codat ids:** `integration.externalCompanyId` is the Codat company and `integration.connectionId` the connection (`src/services/erp/erp-context.resolver.ts`).
- **Line balance:** `resolveBalance` in `src/helpers/bank-feeds.helpers.ts` merges a payment with its fees into one line, and takes the smallest `accountBalance` among them for a debit (largest for a credit). Fee balances come from `transaction_fees_charges.accountBalance`. `applyRollingBalance` recomputes balances for LOC accounts only.
- **Codat checks the chain:** each line's balance must equal the previous line's balance plus its amount. One wrong balance rejects the whole batch, and every later line queues behind it.
- **Errors:** the Codat error is in `batch.log` (last entry). `bank_feeds_sync_history.log` stays `NULL` on failed lines.
- **Account status:** Codat webhooks `bankFeeds.sourceAccount.connected` / `.disconnected` set `bank_feeds_account.status`.

## 🧭 Triage

1. Find the integration, connection and accounts: queries 1a–1c.
2. List the latest batches (2a) and the outcome per account (2b).
3. Read the error of the latest failed batch (2c), then match it below.
4. When nothing is failing, check the source side for new transactions (5a).

## ❌ Error: `BankStatementLine[n].Balance (…) does not equal the expected rolling balance (…)`

- **Cause seen so far:** two bill-pays with FX fees settled at the same moment. wallet-service settles a payment's rows in parallel, so one payment's principal lands between another payment and its fee in `product_accounts_ledger_audit_logs`. The merged line then carries the wrong balance (WAL-7077).
- **Confirm:**
  1. Find the last line Codat accepted per account (4a); its balance is the `openingBalance`.
  2. Compare expected and sent balance per line of the failing batch (3a). The first line with `diff ≠ 0` is the broken one.
  3. Read its fee rows (3b) and the source audit log and `postedAt` running balance (3c, 3d) to see the interleaving.
- **Fix the line:** set the fee row's `accountBalance` to the line's `expectedBalance` (3e: pre-check, update, verify). It is a prod write, so it goes through the prod SQL approval flow. The next hourly push sends the queued lines.

## ❌ Error: `feedConnectionId … not found` (from Xero)

- **Cause:** the customer reset or reconnected the bank feed in Xero. Codat's mapping for the account drops to `disconnected` with no target. Reconnecting in the Jeeves UI only un-pauses our rows (`handleBankFeedAccount` in `src/services/integration/bank-feeds-account.service.ts` returns early for connected accounts), so the mapping stays broken.
- **Confirm:** run the script's `read` and check `account-mapping.json`: `status` `disconnected`, no `targetAccountId`.
- **Fix by remapping each account:**
  1. Get the ids from 1c: `codatSourceAccountId` is `<sourceId>`, `xeroAccountId` is `<targetId>`.
  2. Get the feed start from 4a: the last synced line's `txDate` plus one second, as `YYYY-MM-DDTHH:MM:SS` UTC. Xero then imports only the lines after it.
  3. Run the remap; it shows the plan, asks `y/N`, posts the mapping and polls until `connected`:
     ```bash
     ${CLAUDE_SKILL_DIR}/scripts/codat-bank-feeds.sh remap <companyId> <connectionId> \
       --map <sourceId> <targetId> <YYYY-MM-DDTHH:MM:SS>
     ```
     `<companyId>` and `<connectionId>` are the Codat ids from 1a.

## 🔌 Codat endpoints

Base URL `https://api.codat.io`, header `Authorization: Basic <base64 API key>`. The script's `read` calls all of these and saves each response.

| Endpoint | Tells you |
|---|---|
| `GET /companies/{c}/connections/{conn}` | Connection status |
| `GET /companies/{c}/connections/{conn}/connectionInfo/bankFeedAccounts` | Source accounts Jeeves registered |
| `GET`/`POST /companies/{c}/connections/{conn}/bankFeedAccounts/mapping` | Source → Xero account mapping, its status and feed start; `POST` remaps |
| `GET /companies/{c}/connections/{conn}/data/bankAccounts` | The ERP's bank accounts (mapping targets) |
| `GET /companies/{c}/push` and `/push/{pushOperationKey}` | Push history and one push's error; `batch.syncId` is the key |

## ✅ Verify

- Re-run 1c: every account `connected`.
- After the next :15 push, re-run 2a: the newest batch is `success` with `erroredCount` 0.
- Ask the customer to confirm the lines appear in the ERP.
