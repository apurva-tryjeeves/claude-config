# stablecoin-service schema notes

Applies to `stablecoin_<n>` (dev), `stablecoin` (preprod/prod).

## stablecoin_webhook_events

Outbound event log — the events actually sent to webhook subscribers.

| Column | Type | Notes |
| --- | --- | --- |
| id | char(36) PK | |
| eventId | varchar(40), unique | |
| eventType | enum | `customer.updated`, `transfer.created`, `transfer.completed`, `transfer.failed`, `deposit.received` |
| eventCategory | enum | `customer`, `transfer`, `deposit` |
| eventObjectId | varchar(255) | id of the related object (customer/transfer/deposit) |
| eventObjectStatus | varchar(255), nullable | |
| payload | json | payload delivered to subscriber |
| status | enum, indexed | `pending`, `delivering`, `delivered`, `partially_delivered`, `failed` |
| eventCreatedAt | datetime(3) | when the underlying event occurred |
| deliveredAt | datetime(3), nullable | |
| createdAt / updatedAt / deletedAt | datetime(3) | soft-delete via deletedAt |
| createdBy / updatedBy | varchar(255) | |

## stablecoin_webhook_subscription_events

Join table: which event types a given webhook subscription is subscribed to. No payload — pure config.

| Column | Type | Notes |
| --- | --- | --- |
| id | char(36) PK | |
| subscriptionId | varchar(40), indexed | FK-like ref to the subscription |
| eventType | enum, indexed | same enum as `stablecoin_webhook_events.eventType` |
| createdAt / updatedAt / deletedAt | datetime(3) | soft-delete via deletedAt |
| createdBy / updatedBy | varchar(255) | |
