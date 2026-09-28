---
name: sqs
description: Choose or reason about an AWS SQS queue type (FIFO vs Standard) for a JeevesInc microservice — ordering, dedup, and throughput tradeoffs. Trigger when creating a new SQS queue, deciding between FIFO and Standard, or reasoning about MessageGroupId, MessageDeduplicationId, or per-message DelaySeconds in a Jeeves repo.
---

# AWS SQS — FIFO vs Standard Queues

Reference for choosing/reasoning about SQS queue types across Jeeves services.

| Property | Standard | FIFO (`*.fifo`) |
|---|---|---|
| Ordering | Best-effort, can arrive out of order | Strict order **within a `MessageGroupId`** |
| Delivery | At-least-once (duplicates are normal) | Exactly-once within the 5-min dedup window (via `MessageDeduplicationId`) |
| Throughput | Effectively unlimited | 300 msg/s (3,000 batched); more only in high-throughput mode |
| Consumer concurrency | Unlimited parallel pulls | Serialized **per group**; different groups run in parallel |
| Per-message `DelaySeconds` | ✅ Supported | ❌ Not supported (only a queue-wide delay) |

**`MessageGroupId`** = the ordering "lane". All messages sharing a group are processed strictly in order, one at a time (next isn't released until the current is deleted); different groups run concurrently. Key it by the logical entity whose steps must stay ordered (e.g. a transaction/transfer id) so unrelated entities don't block each other.

**`MessageDeduplicationId`** = what SQS treats as a duplicate within the 5-min window. Scope it per step: give each step of an entity its own dedup id, so a replay of the same step collapses to one while distinct steps of the same entity still each go through. Sharing one dedup id across ordered steps of the same entity causes the second step to be silently dropped as a "duplicate".

**How to choose:**
- Use **FIFO** only when order **and** exactly-once genuinely matter and you don't need per-message delays (e.g. sequential money-movement legs: warm→hot must precede hot→external).
- Use **Standard** otherwise, and make handlers **idempotent** (dedupe on a business `eventId`, check state before acting, use provider idempotency keys). Standard is required when retry backoff uses per-message `DelaySeconds` — a per-message delay is Standard-only — e.g. outbound webhook delivery with exponential backoff.

Rule of thumb: prefer Standard + idempotent handlers; reach for FIFO when ordering is a hard correctness requirement.
