# AI Workforce Orchestrator — User Stories & Acceptance Criteria

Companion to `spec.md`. `spec.md` defines the architecture and data model; this file defines what "done" looks like for each user-facing or agent-facing capability, at the granularity you'd actually implement one at a time. Each story should be treated as its own scoped unit of work per `CLAUDE.md`'s "one thing at a time" rule.

---

## A. Mart onboarding (Mart owner)

**A1 — Register a new mart**
As a mart owner, I want to register my mart on the platform, so that my inventory and operations can be managed by the AI workforce.
- Acceptance criteria:
  - Owner provides: mart name, address, operating hours (default + optional per-day overrides), one or more categories, contact info.
  - Platform provisions a new isolated Postgres schema for this tenant.
  - New tenant row is created with `status = onboarding`.
  - Owner cannot yet receive customer orders until status is manually or automatically moved to `active` (define which, when implementing).

**A2 — Define reorder policy and permissions**
As a mart owner, I want to set reorder thresholds and approval rules for my mart, so that the Inventory agent knows when to act autonomously vs. ask me.
- Acceptance criteria:
  - Owner can set, per item, a `reorder_point`.
  - Owner can set a blast-radius rule (e.g. max autonomous order value) — stored in KSOR, not in the tenant schema.
  - Changing a KSOR policy does not require a code deploy.

---

## B. Customer identity (Customer)

**B1 — Sign up**
As a customer, I want to create one account, so that I can shop at any mart on the platform with a single identity.
- Acceptance criteria:
  - Signup creates exactly one global `customer_id`, stored in the shared `customers` table (not any tenant schema).
  - Password is hashed, never stored in plaintext.
  - Customer cannot browse or order without being logged in (full auth wall, per confirmed decision).

**B2 — Log in**
As a customer, I want to log in, so that I can browse and shop.
- Acceptance criteria:
  - Successful login is required before any storefront or Shopping Assistant interaction is available.
  - Failed login shows a clear error without revealing whether the email or password was wrong (standard security practice — confirm with developer before implementing differently).

---

## C. Click-based storefront (Customer)

**C1 — Browse a mart's catalog**
As a logged-in customer, I want to browse a specific mart's items, so that I can decide what to buy.
- Acceptance criteria:
  - Only items belonging to the selected mart's schema are shown.
  - Out-of-stock items are visibly indicated, not hidden (confirm with developer which behavior is wanted).

**C2 — Add to cart and check out**
As a logged-in customer, I want to add items to a cart and check out, so that a bill is created.
- Acceptance criteria:
  - Checkout calls the ingestion API.
  - A `bills` row (header) and one or more `bill_items` rows (line items) are created in the resolved mart's schema.
  - Each `bill_item` snapshots the item's cost price *at the time of sale* — never computed retroactively.
  - `inventory.quantity_on_hand` is decremented for each item sold.
  - If two customers attempt to buy the last unit simultaneously, exactly one checkout succeeds (edge case — confirm desired behavior with developer before implementing).
  - "Proceed to pay" is shown; no real payment processing occurs (deferred feature).

---

## D. Conversational ordering (Customer + Shopping Assistant agent)

**Positioning note:** the storefront (section C) and the Shopping Assistant (this section) are both always available — the system does not auto-route between them. The Shopping Assistant is the *recommended* path for multi-item orders and/or when the customer doesn't want to manually browse across marts to find something; for a single simple item, the storefront's click UI is faster and avoids unnecessary LLM cost/latency. A customer may still choose the Shopping Assistant for a single item if they prefer — this is a UX preference, not a technical restriction.

**D1 — Order by natural language, specific mart named**
As a logged-in customer, I want to tell the Shopping Assistant what I want in plain language, so that I don't have to click through a catalog.
- Acceptance criteria:
  - Customer's utterance may include item name, brand, quantity, price range, and mart name (e.g. *"4 packets of chicken roll and 1 mango juice from csd lalkurti"*).
  - Agent resolves the named mart via the `tenants` table.
  - Agent performs vector/semantic search over the resolved mart's `items` (name + brand + description embedding), applying price range as a filter where given.

**D2 — Disambiguate between close matches**
As a customer, when multiple items closely match what I asked for, I want the agent to ask me which one I mean, so that I get the right item.
- Acceptance criteria:
  - If more than one item is a close semantic match (e.g. two brands of mango juice), the agent presents the options and waits for the customer's choice before adding to the bill.
  - Agent does not guess silently when ambiguity exists.

**D3 — Fallback to another mart when item unavailable**
As a customer, if the item/brand I want isn't available at the mart I named, I want the agent to ask whether to check elsewhere, so that I'm not just told "not available" with no next step.
- Acceptance criteria:
  - Fallback only triggers when the item/brand is genuinely unavailable in the named mart (not merely because the customer expressed dissatisfaction with what's shown).
  - Agent explicitly asks: check any other mart, or a specific one the customer names.
  - Agent's read access spans all tenant schemas for this search; any resulting bill write still happens only in the one resolved mart's schema (never split across marts in one bill, unless explicitly designed otherwise — confirm before implementing multi-mart bills).

**D4 — Complete the conversational order**
As a customer, once my order is resolved, I want to see a bill and proceed to pay, so that the flow ends the same way as the click-based storefront.
- Acceptance criteria:
  - Resulting bill structure is identical to the click-based checkout path (same `bills`/`bill_items` tables, same cost-price snapshot rule).
  - "Proceed to pay" shown; no real payment processing (deferred feature), consistent with C2.

---

## E. Inventory reorder chain (system: Inventory agent)

**E1 — Detect a reorder condition**
As the platform, I want to detect when a mart's stock crosses its reorder point, so that the Inventory agent can be woken efficiently.
- Acceptance criteria:
  - Detection is a cheap, deterministic Postgres trigger comparing `quantity_on_hand` to a cached `reorder_point` column — not an LLM call, not a polling script.
  - Trigger fires `pg_notify` only on the crossing event, not on every sale.

**E2 — Decide whether/how much to reorder**
As the Inventory agent, I want to reason over KSOR policy and context when woken, so that ordering decisions are genuinely agentic, not hardcoded.
- Acceptance criteria:
  - Agent reads: current stock, sales velocity (definition of "velocity" to be confirmed with developer before implementation), any pending incoming orders, KSOR pricing/policy for this item.
  - Agent's decision (order / don't order / how much / when) is produced by reasoning, not an if/else threshold check — the threshold check already happened in E1.
  - If the decision exceeds a KSOR blast-radius rule, the workflow pauses and invokes the Owner approval gate before proceeding.

**E3 — Place the order (stubbed wholesaler)**
As the Inventory agent, I want to call the Wholesaler agent through the defined Dapr contract, so that the integration boundary is correct even though the real Wholesaler isn't built yet.
- Acceptance criteria:
  - Request/response shape matches the contract in `spec.md` §7.2.
  - v1 points this call at a stub/fake implementation, clearly documented as such.
  - An `orders` row is created with `status = pending`.
  - Action carries an idempotency key; a retried workflow step must not create a duplicate order.

---

## F. Delivery verification (system: Verification agent)

**F1 — Confirm goods received**
As the Verification agent, I want to confirm delivered quantity via QR/camera, so that inventory reflects reality.
- Acceptance criteria:
  - `orders.status` moves from `pending` to `delivered` (or a mismatch state — define this state before implementing).
  - `inventory.quantity_on_hand` is updated to reflect what actually arrived, which may differ from what was ordered.
  - A mismatch between ordered and delivered quantity triggers Owner escalation (confirm this is desired before implementing — not yet explicitly decided in `spec.md`).

---

## G. Owner approval (Mart owner)

**G1 — Approve an escalated action**
As a mart owner, I want to be notified only when an action exceeds my defined blast radius, so that I'm not interrupted for routine operations.
- Acceptance criteria:
  - Owner is only contacted when a KSOR blast-radius rule is exceeded — never for actions within the safe range.
  - The paused workflow resumes automatically once the owner approves or rejects, via Dapr Workflow's durable state (no data loss if the owner takes hours to respond).
  - Rejected actions are logged, not silently discarded (confirm exact rejection-handling behavior with developer before implementing).

---

## Notes for implementation discussions

- Several acceptance criteria above are flagged **"confirm with developer before implementing"** — these are genuine open questions, not settled behavior. Per `CLAUDE.md`, do not resolve them by assumption.
- This file should grow incrementally: when a new feature-level decision is made in conversation, add or update the relevant story here rather than only relying on `spec.md`'s architecture-level language.