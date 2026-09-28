# Inventory Reorder End-to-End Result

**Date:** 2026-09-15  
**Environment:** Local development

## Executive Result

The complete v1 chain did not complete. The real test successfully reached checkout, inventory mutation, and the PostgreSQL reorder trigger. It stopped before the bridge, Dapr pub/sub, Dapr Workflow, Wholesaler, and approval branches.

Approximate acceptance coverage: **50%**.

## Verified Chain

The following path was executed successfully:

```text
Authenticated signup
  -> authenticated login
  -> ingestion checkout
  -> bill creation
  -> inventory decrement
  -> reorder-point trigger
  -> tenant-specific PostgreSQL notification
```

### Checkout

- Tenant: Lalkurti Electronics
- Item: Cooler
- Reorder point: `5`
- Test stock before checkout: `50`
- Quantity purchased: `46`
- Stock after checkout: `4`
- HTTP checkout status: `200`
- Bill ID: `27eeaa14-544f-4285-9ca4-cc22b97bcd42`
- Bill total: `1,380,000`

Authentication initially returned HTTP 500 because `create_refresh_token` was not imported by `api/routers/auth.py`. The import was corrected, and signup/login/checkout then succeeded.

### PostgreSQL Trigger

The trigger fired after stock crossed from `50` to `4`.

The trigger was verified on the corrected global notification channel:

```text
inventory_reorder_events
```

Payload shape:

```json
{
  "item_id": "7fc0f7ca-d8d8-439c-8a74-fec47be17c8d",
  "quantity": 4,
  "reorder_point": 5,
  "tenant_id": "788aeac9-8539-4ad5-8fc7-356b4d1633da"
}
```

## Blocking Issues

### 1. Trigger channel drift

The migration and bridge both use `inventory_reorder_events`. The live database function had drifted to a tenant-specific channel and was corrected to match the original global-channel design.

### 2. Dapr is not running

The local runtime check reported:

```text
No Dapr instances found.
127.0.0.1:3500: connection refused
```

Consequently, the test could not verify:

- Bridge publication to `inventory-pubsub/inventory-reorder`
- Dapr subscription delivery
- New Dapr Workflow instance creation
- Workflow activity execution
- Durable approval waiting/resumption

### 3. Wholesaler activity is missing

The workflow currently invokes the Inventory decision activity and can wait for an approval event, but no Wholesaler activity/stub is implemented.

The following outcomes could not be verified:

- Automatic Wholesaler invocation within blast radius
- Order creation with `status = pending`
- Post-approval Wholesaler invocation

### 4. Idempotency is missing

The tenant `orders` table currently has these columns:

```text
order_id
item_id
quantity
status
created_at
```

There is no idempotency key column, unique constraint, or duplicate-event handling. Retried triggers cannot yet be proven safe.

### 5. Langfuse correlation is incomplete

Development Langfuse observations were successfully created for:

- `context-service-get-reorder-context`
- `postgres-operational-facts`
- Two `ksor-search` retrievers
- `inventory-reorder-decision` synthetic workflow activity

However, the queried observations showed blank `userId` and `sessionId` values. The requirement that every observation contain:

```text
user_id = tenant_id
session_id = Dapr workflow instance ID
```

is not yet verified.

There is no real agent decision trace from the complete checkout-to-workflow path because Dapr was unavailable.

## Prompt/Acceptance Status

| Area | Status | Notes |
|---|---|---|
| Authenticated checkout | Complete | Real HTTP checkout succeeded after auth import fix. |
| Inventory decrement | Complete | Stock changed from 50 to 4. |
| Reorder trigger | Complete | Trigger fired and tenant-specific notification was received. |
| Bridge republish | Ready for runtime verification | Trigger and bridge now share `inventory_reorder_events`; Dapr runtime was unavailable during the test. |
| Dapr pub/sub | Blocked | No Dapr sidecar running. |
| Dapr Workflow | Implemented structurally, not live-tested | Runtime unavailable. |
| Inventory agent activity | Synthetic test only | Real workflow invocation not reached. |
| Context-service | Verified separately | Live Postgres and KSOR data retrieval works. |
| KSOR policy retrieval | Verified separately | Live calls to KSOR MCP succeeded. |
| Within-blast-radius branch | Not verified | Wholesaler activity missing. |
| Escalation branch | Not verified live | Approval route exists, but Dapr workflow was unavailable. |
| Wholesaler stub | Missing | No activity/order creation path exists. |
| Idempotency | Missing | No key or uniqueness enforcement exists. |
| Langfuse traces | Partially verified | Development observations exist, but full correlation is not proven. |

## Quality and Consistency Findings

The strongest verified path is:

```text
Checkout -> PostgreSQL inventory update -> reorder trigger -> live context-service
-> Postgres facts + KSOR policy -> Langfuse observations
```

The following consistency corrections are required before claiming full v1 completion:

1. Start and configure the Dapr sidecar/runtime.
2. Add the Wholesaler stub activity.
3. Add an idempotency key and unique constraint to orders.
4. Execute both workflow branches against live Dapr.
5. Verify `user_id` and `session_id` on every Langfuse observation in both traces.

## Final Status

The checkout and database trigger layers are operational. The orchestration and ordering layers are not yet acceptance-complete because the Dapr runtime was unavailable, the Wholesaler activity and idempotency model are missing, and Langfuse correlation is incomplete for a full trigger-to-decision-to-order demonstration.
