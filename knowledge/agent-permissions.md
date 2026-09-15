---
type: Document
title: "Agent Permission & Blast-Radius Rules"
description: "Defines the autonomous limits for agents and conditions requiring Mart Owner escalation."
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

This document defines the "Blast Radius"—the boundary between autonomous agent action and mandatory human approval.

## Autonomous Order Limits
The Inventory agent may place orders autonomously without approval up to the following total value thresholds:
- **High-Profit Marts** (Overall profit > 1 Million): up to **Rs. 50,000**.
- **Standard Marts** (Overall profit $\le$ 1 Million): up to **Rs. 30,000**.

Orders exceeding these limits must be escalated to the Mart Owner.

## Supplier Constraints
To ensure security and reliability, agents are restricted to a trusted circle of suppliers:
- **Trusted Only**: Agents may only contact suppliers that are recognized, continuously contacted, and explicitly approved by the Mart Owner.
- **Strict Exclusion**: Unrecognized suppliers must not be addressed, searched for, or contacted by the agent.
- **Escalation**: If the required items are unavailable from all trusted suppliers, the agent must escalate to the Mart Owner.

## Delivery Verification & Mismatches
When the Verification agent confirms goods received, the following rules apply to quantity mismatches:

### 1. Informational (Automatic Proceed)
If the mismatch is **explained** (e.g., marked as defective) AND the **billing has been adjusted correctly** to match the delivered quantity:
- The workflow proceeds automatically.
- The Mart Owner receives an informational notification describing the adjustment (e.g., "3 units defective, delivery adjusted to 47, billed 47 accordingly").

### 2. Critical (Mandatory Escalation)
The workflow must pause and escalate to the Mart Owner if:
- The mismatch is **unexplained**.
- The **billing does not match** the actual delivered quantity.

## Approval Process
Once an action is escalated, the workflow remains paused. No further steps (such as final inventory updates or payment triggers) may occur until the Mart Owner provides explicit input. The system shall then act strictly upon the owner's input.
