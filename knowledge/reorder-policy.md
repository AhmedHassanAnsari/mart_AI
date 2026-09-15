---
type: Document
title: "Reorder Policy"
description: "Rules for determining reorder quantities, supplier selection, and sales velocity calculations."
status: stable
generated:
  by: human:ahmedhassanansari
  at: 2026-09-12T17:00:00Z
ksor:
  approval:
    by: human:ahmedhassanansari
    at: 2026-09-12T17:01:00Z
  audience: [public]
  owner: human:ahmedhassanansari
---

This policy governs how the Inventory agent reasons over stock triggers to determine the final order quantity and supplier.

## Reorder Quantity
When a reorder is triggered, the agent shall order a quantity equal to **two times (2x) the total unit sales from the last two weeks**.

## Supplier Selection
The agent must select suppliers based on the item's category and historical reliability:
1.  **Category Match**: The supplier must be authorized for the item's category (e.g., electronics for TVs).
2.  **Frequency Preference**: Among category-authorized suppliers, the agent shall prioritize those the mart deals with most frequently.
3.  **Escalation**: If the required item is out of stock across all preferred and authorized suppliers, the agent must not guess a new supplier; it must escalate to the Mart Owner to ask for a supplier selection.

## Sales Velocity Calculation
For the purpose of reasoning and reporting, "sales velocity" is defined as the **average daily sales over the last 14 days**.
