---
format: 2
name: mart-knowledge
title: "Retail Mart AI Workforce Policy"
description: "Governed operational policy for a retail mart's AI agent workforce on the AI Workforce Orchestrator platform."
toolchain:
  requires: ">=0.0.60"
  scaffolded: "0.0.60"
database:
  dsn_env: KSOR_DB_URL
---

This record is authoritative for the governed operational policy of a retail mart's AI agent workforce on the AI Workforce Orchestrator platform. It defines reorder policies (per-item or per-category rules), agent permission scopes for autonomous actions, and blast-radius escalation rules for routing to the mart owner.

It does NOT cover:
- Live operational data (stock counts, sale transactions, order status, customer data)
- Item catalogs (names, brands, prices)
- Wholesaler agent rules or data
- Payment/checkout processing rules
- General product documentation, UI copy, or marketing content

When asked about things outside this scope—such as current stock levels, order status, or other marts' rules—the record must firmly decline, as "not in this corpus" is the correct answer. It should not blend policy rules with live operational facts it does not hold.
