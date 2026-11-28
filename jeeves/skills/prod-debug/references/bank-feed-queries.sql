-- Bank-feed (Codat → Xero) debugging queries.
--
-- Run each block with jsql against the database named in its header, e.g.
--   jsql prod/accounting '<block>'
-- Each read starts with a `params` CTE: replace every <placeholder> with the value under
-- investigation (jsql runs only SELECT/WITH on prod). Add a UNION ALL row per extra id.
-- Where each id comes from:
--   <companyId>         Jeeves company id
--   <integrationId>     integration.id (1a)
--   <accountId>         bank_feeds_account.accountId / account.id (1c)
--   <batchId>           batch.id (2a)
--   <openingBalance>    balance of the last line Codat accepted (4a)
--   <paymentRef>        transaction reference id of a bill-pay (3a transactionId → transaction.transactionReferenceId)
--   <feeRef>            transaction_fees_charges.transactionReferenceId (3b)
--   <feeRowId>          transaction_fees_charges.id (3b)
--   <productAccountId>  transaction.sourceProductAccountId, or product_accounts.id in product_account

-- =========================================================================
-- 1. Find the company's integration, connection and bank-feed accounts
-- =========================================================================

-- 1a. Integration: Codat company id (externalCompanyId) and connection id the push uses
-- DB: prod/accounting
WITH params AS (SELECT <companyId> AS companyId)
SELECT i.id AS integrationId, i.platformName, i.status, i.externalCompanyId, i.connectionId, i.createdAt, i.updatedAt
FROM integration i, params p
WHERE i.companyId = p.companyId;

-- 1b. Bank-feed connection
-- DB: prod/accounting
WITH params AS (SELECT <companyId> AS companyId)
SELECT c.id, c.integrationId, c.status, c.feedStartDate, c.errorMessage, c.linkedAt, c.unlinkedAt,
       c.createdAt, c.updatedAt, c.deletedAt
FROM bank_feeds_connection c, params p
WHERE c.companyId = p.companyId
ORDER BY c.createdAt;

-- 1c. Bank-feed accounts: codatSourceAccountId and xeroAccountId are the remap's --map ids
-- DB: prod/accounting
WITH params AS (SELECT "<integrationId>" AS integrationId)
SELECT bfa.id AS codatSourceAccountId, bfa.accountId, a.externalAccountId AS xeroAccountId,
       bfa.status, bfa.balance, bfa.errorMessage, bfa.updatedAt
FROM bank_feeds_account bfa
JOIN account a ON a.id = bfa.accountId
JOIN params p ON p.integrationId = bfa.integrationId
WHERE bfa.deletedAt IS NULL
ORDER BY bfa.createdAt;

-- =========================================================================
-- 2. Batch status and the Codat error
-- =========================================================================

-- 2a. Latest bank-feed batches for the integration
-- DB: prod/accounting
WITH params AS (SELECT "<integrationId>" AS integrationId)
SELECT b.id AS batchId, j.accountId, b.status, b.transactionCount, b.successCount, b.erroredCount,
       b.createdAt, b.updatedAt
FROM batch b
JOIN job j ON j.id = b.jobId
JOIN params p ON p.integrationId = j.integrationId
WHERE b.transactionType = "bank_feed"
ORDER BY b.createdAt DESC
LIMIT 20;

-- 2b. Batch outcomes per account since a date
-- DB: prod/accounting
WITH params AS (SELECT "<integrationId>" AS integrationId, "<YYYY-MM-DD>" AS since)
SELECT j.accountId, b.status, COUNT(*) AS batches, MIN(b.createdAt) AS firstAt, MAX(b.createdAt) AS lastAt
FROM batch b
JOIN job j ON j.id = b.jobId
JOIN params p ON p.integrationId = j.integrationId
WHERE b.transactionType = "bank_feed"
  AND b.createdAt >= p.since
GROUP BY j.accountId, b.status;

-- 2c. Codat error from a batch: the last entry of batch.log
-- DB: prod/accounting
WITH params AS (SELECT "<batchId>" AS batchId)
SELECT JSON_LENGTH(b.log) AS entries, b.syncId, b.status, b.completedAt,
       LEFT(JSON_UNQUOTE(JSON_EXTRACT(b.log, CONCAT("$[", JSON_LENGTH(b.log) - 1, "]"))), 1500) AS lastEntry
FROM batch b
JOIN params p ON p.batchId = b.id;

-- 2d. Failed lines: attempts, transactions stuck, first and last failure.
--     Failed lines carry log = NULL; the Codat error lives in batch.log (2c).
-- DB: prod/accounting
WITH params AS (SELECT <companyId> AS companyId, "<YYYY-MM-DD>" AS since)
SELECT COUNT(*) AS attempts, COUNT(DISTINCT h.transactionId) AS transactions,
       MIN(h.createdAt) AS firstAt, MAX(h.createdAt) AS lastAt
FROM bank_feeds_sync_history h
JOIN transaction t ON t.id = h.transactionId
JOIN params p ON p.companyId = t.companyId
WHERE h.status = "failed"
  AND h.createdAt >= p.since;

-- =========================================================================
-- 3. Error "BankStatementLine[n].Balance … does not equal the expected rolling balance"
-- =========================================================================

-- 3a. Expected vs sent balance per line of a batch.
--     The first line with diff ≠ 0 is the one to fix.
-- DB: prod/accounting
WITH params AS (SELECT "<batchId>" AS batchId, <openingBalance> AS openingBalance),
feed AS (
  SELECT h.transactionId,
         JSON_UNQUOTE(JSON_EXTRACT(h.payload, "$.date")) AS txDate,
         JSON_UNQUOTE(JSON_EXTRACT(h.payload, "$.counterparty")) AS counterparty,
         CAST(JSON_EXTRACT(h.payload, "$.amount") AS DECIMAL(30,2)) AS amount,
         CAST(JSON_EXTRACT(h.payload, "$.balance") AS DECIMAL(30,2)) AS sentBalance,
         p.openingBalance
  FROM bank_feeds_sync_history h
  JOIN params p ON p.batchId = h.batchId
)
SELECT ROW_NUMBER() OVER w - 1 AS line, txDate, transactionId, LEFT(counterparty, 40) AS counterparty,
       amount, sentBalance,
       openingBalance + SUM(amount) OVER w AS expectedBalance,
       sentBalance - (openingBalance + SUM(amount) OVER w) AS diff
FROM feed
WINDOW w AS (ORDER BY txDate, transactionId ROWS UNBOUNDED PRECEDING)
ORDER BY txDate, transactionId;

-- 3b. Fee rows for the payments: a debit line's balance is the smallest accountBalance
--     among the payment and its fees (accounting-service resolveBalance)
-- DB: prod/accounting
WITH params AS (
  SELECT "<paymentRef1>" AS paymentRef
  UNION ALL SELECT "<paymentRef2>"
)
SELECT f.id, f.transactionReferenceId, f.relatedTransactionId, f.amount, f.accountBalance, f.updatedAt
FROM transaction_fees_charges f
JOIN params p ON p.paymentRef = f.relatedTransactionId;

-- 3c. Source balances: ledger audit log for the payments and their fees.
--     Interleaving shows as one payment's row settling between another payment and its fee.
-- DB: prod/product_account
WITH params AS (
  SELECT "<productAccountId>" AS productAccountId, "<paymentRef1>" AS ref
  UNION ALL SELECT "<productAccountId>", "<feeRef1>"
  UNION ALL SELECT "<productAccountId>", "<paymentRef2>"
  UNION ALL SELECT "<productAccountId>", "<feeRef2>"
)
SELECT a.createdAt, a.transactionReferenceId, l.transactionTypeTag, a.transactionStatus,
       a.baseCurrencyAmount, a.accountBalance, a.availableBalance
FROM product_accounts_ledger_audit_logs a
JOIN product_accounts_ledger l ON l.id = a.productAccountLedgerId
JOIN params p ON p.productAccountId = a.productAccountId AND p.ref = a.transactionReferenceId
ORDER BY a.createdAt;

-- 3d. Running balance over settled ledger rows ordered by postedAt, around the given rows
-- DB: prod/product_account
WITH params AS (
  SELECT "<productAccountId>" AS productAccountId, "<paymentRef1>" AS ref
  UNION ALL SELECT "<productAccountId>", "<feeRef1>"
  UNION ALL SELECT "<productAccountId>", "<paymentRef2>"
  UNION ALL SELECT "<productAccountId>", "<feeRef2>"
),
base AS (
  SELECT l.id, l.transactionReferenceId ref, l.parentTransactionReferenceId parentRef,
         l.transactionTypeTag tag, l.postedAt,
         CASE WHEN l.transactionType = "credit" THEN l.baseCurrencyAmount ELSE -l.baseCurrencyAmount END signed
  FROM product_accounts_ledger l
  WHERE l.productAccountId = (SELECT MIN(productAccountId) FROM params)
    AND l.transactionStatus = "settled"
    AND l.deletedAt IS NULL
),
ranked AS (
  SELECT b.*,
         ROW_NUMBER() OVER (ORDER BY postedAt, id) pos,
         SUM(signed) OVER (ORDER BY postedAt, id ROWS UNBOUNDED PRECEDING) running
  FROM base b
),
span AS (
  SELECT MIN(pos) lo, MAX(pos) hi
  FROM ranked
  WHERE ref IN (SELECT ref FROM params)
)
SELECT r.pos, r.postedAt, r.ref, r.parentRef, r.tag, r.signed, r.running
FROM ranked r, span s
WHERE r.pos BETWEEN s.lo - 1 AND s.hi + 1
ORDER BY r.pos;

-- 3e. One-off fix: set the fee row's balance to the line's expectedBalance from 3a.
--     Writes go through the prod SQL approval flow, not jsql.
--     Run pre-check (expect 1 row), update, verify. Rollback: the same UPDATE with the two balances swapped.
-- DB: prod/accounting (write)
SELECT id, transactionReferenceId, relatedTransactionId, amount, accountBalance, updatedAt
FROM transaction_fees_charges
WHERE id = "<feeRowId>"
  AND relatedTransactionId = "<paymentRef>"
  AND accountBalance = <sentBalance>;

UPDATE transaction_fees_charges
SET accountBalance = <expectedBalance>,
    updatedAt = NOW()
WHERE id = "<feeRowId>"
  AND relatedTransactionId = "<paymentRef>"
  AND accountBalance = <sentBalance>;

SELECT id, accountBalance, updatedAt
FROM transaction_fees_charges
WHERE id = "<feeRowId>";

-- =========================================================================
-- 4. Error "feedConnectionId … not found": remap the feed
-- =========================================================================

-- 4a. Last line already synced per account: its date + 1 second is the remap feedStartDate,
--     and its balance is openingBalance for 3a
-- DB: prod/accounting
WITH params AS (SELECT "<integrationId>" AS integrationId),
synced AS (
  SELECT j.accountId,
         JSON_UNQUOTE(JSON_EXTRACT(h.payload, "$.date")) AS txDate,
         JSON_EXTRACT(h.payload, "$.amount") AS amount,
         JSON_EXTRACT(h.payload, "$.balance") AS balance,
         h.createdAt AS syncedAt,
         ROW_NUMBER() OVER (PARTITION BY j.accountId ORDER BY JSON_UNQUOTE(JSON_EXTRACT(h.payload, "$.date")) DESC) AS rn
  FROM bank_feeds_sync_history h
  JOIN batch b ON b.id = h.batchId
  JOIN job j ON j.id = b.jobId
  JOIN params p ON p.integrationId = j.integrationId
  WHERE h.status = "success"
)
SELECT accountId, txDate, amount, balance, syncedAt
FROM synced
WHERE rn = 1;

-- 4b. After the remap: re-run 1c and expect every account connected (Codat webhooks update the status),
--     then 2a for the next batch.

-- =========================================================================
-- 5. Source side: is there anything new to push?
-- =========================================================================

-- 5a. Latest transactions on a bank-feed account
-- DB: prod/accounting
WITH params AS (SELECT "<accountId>" AS accountId)
SELECT t.id, t.transactionReferenceId, t.tag, t.type, t.amount, t.currency, t.initiatedAt, t.settledAt,
       t.createdAt, t.bankFeedSyncStatus
FROM transaction t
JOIN params p ON p.accountId = t.accountId
WHERE t.deletedAt IS NULL
ORDER BY t.createdAt DESC
LIMIT 5;
