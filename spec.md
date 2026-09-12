# AI Workforce Orchestrator — Software Requirements Specification

**Version:** 0.1 (draft, pre-implementation)
**Status:** Design phase — no code written yet
**Owner:** Ahmed Hassan Ansari

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for the AI Workforce Orchestrator — a general, multi-tenant platform that lets any retail mart onboard its own inventory and operations onto an AI-driven agent workforce. It is a standalone portfolio project, inspired by (but not a copy of) a Senior Agentic AI Architect job posting, and generalizes the design ideas behind the author's separate, confidential [Mart AI Employee] product.

### 1.2 Scope (v1)
v1 covers the **mart side only**. It does not implement a real Wholesaler agent (treated as a separate, external AI employee with its own database and policies — out of scope, stubbed for integration testing). Online payment processing is deferred to a future enhancement; v1 stops at "proceed to pay."

### 1.3 Definitions
- **Tenant** — one onboarded mart. Owns an isolated Postgres schema containing its own items, inventory, bills, orders, and agent memory.
- **KSOR** — Knowledge System of Record (`panaversity/ksor` SDK). A separate, already-existing framework for governed, human-approved knowledge (rules, policies, thresholds). Not designed as part of this project's schema — integrated as a dependency.
- **Blast radius** — the set of conditions under which an agent may act autonomously without human approval, defined as KSOR-governed policy.
- **Shopping Assistant agent** — the customer-facing, global (not tenant-scoped) conversational agent that interprets natural-language orders.

### 1.4 Out of Scope (v1)
- Real Wholesaler agent implementation (stub/contract only)
- Online payment gateway integration (UI shows a "pay" affordance; no real transaction processing)
- Cross-mart shared search index (searches happen live, agent-side, across tenant schemas — no precomputed global index yet)
- Formal human/AI task-transition framework (replaced by KSOR blast-radius rules, which serve the same governance purpose more simply)

---

## 2. Overall Description

### 2.1 Product Perspective
The platform is built as an FDE-style general-purpose system: one platform, many marts, each onboarding their own data and use case rather than a bespoke build per store. It demonstrates the same architectural concerns as the reference job posting — agent hierarchy, shared/agent memory, approval gates, durable workflows, observability — applied to a concrete, believable vertical (retail/mart operations).

### 2.2 User Classes
- **Mart owner** — onboards their mart, defines KSOR policies/thresholds, approves escalations.
- **Customer** — signs up once (global identity), can browse or shop by voice/text at any onboarded mart.
- **Platform operator (the author, as FDE)** — designs, deploys, and operates the orchestration layer itself.

### 2.3 Constraints
- Full per-mart data isolation is a hard security requirement.
- No agent may act outside its KSOR-defined permission scope without escalation.
- No two agents may execute conflicting/duplicate actions (idempotency-key enforced).

---

## 3. System Architecture Overview

### 3.1 Components
| Component | Role |
|---|---|
| Storefront (click-based) | Traditional browse → cart → checkout UI; the faster, lower-cost path for simple single-item, single-mart purchases |
| Shopping Assistant agent | Global, conversational (voice/text) order intake across any mart; best suited to multi-item and/or cross-mart orders, where its search/reasoning cost is justified |
| Inventory/Ordering agent | Per-mart, event-driven; decides whether/how much to reorder |
| Wholesaler/Supply agent | **Out of scope v1** — external AI employee, stubbed contract only |
| Verification agent | Per-mart; QR/camera-based goods-received confirmation |
| Owner approval gate | Conditional human-in-the-loop, invoked only on KSOR escalation triggers |
| Dapr (Service Invocation + Workflows) | Agent-to-agent communication and durable, resumable orchestration |
| Postgres (schema-per-tenant) | System of record for isolated per-mart data |
| Shared/global tables | `tenants`, `customers`, `categories`, `tenant_categories` |
| KSOR | Governed shared knowledge: policies, thresholds, permissions, approval stamps |
| Langfuse | Observability and evals (single tool for both, per project decision) |

### 3.2 Agent-to-agent communication
All agent-to-agent calls go through **Dapr Service Invocation**. No agent calls another agent directly. This is a deliberate constraint: it keeps coordination centralized in the orchestration layer and is what makes idempotency-key enforcement and durable retries possible.

### 3.3 Durable execution
**Dapr Workflows** own all multi-step, resumable processes (e.g., order → wholesaler call → verification → inventory update). Dapr Workflow state is the platform's actual "always-on" component — not the agents (event-driven, stateless) and not the Owner (conditional gate).

### 3.4 Conflict prevention
**Idempotency keys** on all state-changing actions. Locking was explicitly rejected (deadlock/coordination-complexity risk) in favor of idempotency keys, which pair naturally with Dapr Workflow's own retry/dedupe semantics.

---

## 4. Multi-Tenancy & Isolation Model

### 4.1 Isolation strategy
**Schema-per-tenant** in a single Postgres instance. Each onboarded mart gets its own schema (`mart_<name>`) containing its private copies of: `items`, `inventory`, `bills`, `bill_items`, `orders`, `agent_memory`.

### 4.2 Shared/global tables
`tenants`, `customers`, `categories`, `tenant_categories` live outside any tenant schema (e.g. in `public`). Rationale: customer identity must be portable across marts (one signup, one permanent `customer_id`, usable anywhere on the platform), so it cannot live inside an isolated tenant schema. Purchase history and business data remain fully isolated per mart — only login identity is shared, analogous to a single account working across independent services.

### 4.3 Shopping Assistant access model
The Shopping Assistant agent is **global**, with:
- **Broad read access** across all tenant schemas — required for cross-mart item search.
- **Narrow, scoped write access** — limited to the one specific mart's schema resolved for a given transaction.

This is a deliberate, least-privilege exception to strict per-tenant isolation, justified by the agent's legitimate need to search across marts; it must never be used to write outside the resolved mart's own schema.

---

## 5. Data Model (v1)

### 5.1 Shared/global tables
- **`tenants`** — `tenant_id` (PK), `schema_name`, `mart_name`, `address`, `operating_hours` (JSONB: default + per-day overrides), `owner_name`, `contact_info`, `status` (onboarding/active/suspended), `created_at`.
- **`categories`** — `category_id` (PK), `name`.
- **`tenant_categories`** — `(tenant_id, category_id)` composite PK — supports multi-category marts (e.g. a mega mart spanning groceries + electronics).
- **`customers`** — global identity: credentials (hashed), profile info, permanent `customer_id`.

### 5.2 Per-tenant schema tables
- **`items`** — catalog: name, brand, price, `reorder_point`, `embedding` (vector, for semantic search).
- **`inventory`** — live mutable stock: `quantity_on_hand`, references `items`.
- **`bills`** — header: `bill_id` (PK), `customer_id` (FK → shared `customers`), timestamp, total price.
- **`bill_items`** — line items: `bill_id` (FK), item, quantity, sale price, **cost price snapshot at time of sale** (not looked up later — required for accurate historical profit reporting even if wholesaler prices change).
- **`orders`** — orders placed to the wholesaler: item, quantity, status (pending/confirmed/delivered).
- **`agent_memory`** — persistent per-agent working memory: recent raw entries + periodic structured rollup summaries (e.g. per-supplier totals, dates, deal terms) to bound storage/context growth.

### 5.3 Explicitly excluded from this schema
KSOR is **not** designed here — it is an integrated framework/SDK (`panaversity/ksor`) with its own internal structure (pgvector-backed), referenced by agents at decision time, not created as part of this project's tables.

### 5.4 Data retention principle
Transactional/audit records (`bills`, `bill_items`, `orders`) are kept in full, indefinitely, for accountability — never summarized. Only **agent working memory** (semantic/reasoning context, not audit data) is compacted via the raw+rollup pattern.

---

## 6. Functional Requirements

### 6.1 Trigger / wake chain (Inventory agent)
1. External event (real POS, or in-demo: the storefront/Shopping Assistant checkout) calls the ingestion API.
2. Ingestion API writes the `bills`/`bill_items` rows and decrements `inventory.quantity_on_hand`.
3. A lightweight, deterministic Postgres trigger checks: did `quantity_on_hand` just cross below the cached `reorder_point`? If yes → `pg_notify`.
4. Dapr pub/sub receives the notification and starts a Dapr Workflow.
5. The workflow invokes the Inventory agent, which performs actual agentic reasoning (LLM + KSOR context: sales velocity, incoming shipments, supplier terms) to decide whether/how much/from whom to order — this decision is **not** hardcoded if/else logic.
6. If ordering, the workflow invokes the Wholesaler agent via the defined Dapr service contract (stubbed for v1 demo).
7. On delivery, the Verification agent (QR/camera) confirms goods received, updates inventory, and the workflow completes.
8. Any step exceeding KSOR's blast-radius policy escalates to the Owner approval gate before proceeding.

**Design principle:** the *decision to wake* an agent is cheap and deterministic (DB-level). The *decision of what to do* once woken is genuinely agentic (LLM reasoning against KSOR). Do not conflate these two.

### 6.2 Customer-facing ordering (Shopping Assistant agent)
1. Customer must be logged in to browse or order (full auth wall — not guest checkout).
2. Customer expresses an order in natural language, optionally including item name, brand, price range, and a specific mart name (e.g. *"4 packets of chicken roll and 1 mango juice from csd lalkurti"*).
3. Agent resolves the named mart, then performs vector/semantic search over that mart's `items` (matching on name + brand + description embedding), applying price range as a filter.
4. If multiple close matches exist (e.g. different brands), the agent asks the customer to disambiguate.
5. If the item/brand is genuinely unavailable in the named mart, the agent explicitly asks whether to check other marts (any, or a customer-named alternative) — this is a message-driven fallback, never automatic/silent.
6. Once resolved, the agent builds the bill in the **resolved mart's own schema** (scoped write) and presents a "proceed to pay" step. Real payment processing is deferred; v1 shows the UI affordance only.

### 6.3 Both interaction modes
The traditional click-based storefront (browse → cart → checkout) and the conversational Shopping Assistant coexist as two independent entry points into the same underlying bill-creation flow.

**Positioning, not gating:** the two entry points are not automatically routed between by the system — the customer chooses which to use. However, the intended value proposition differs: for a single, simple item, clicking "+" in the storefront is faster and avoids unnecessary LLM cost/latency. The Shopping Assistant's semantic search, disambiguation, and cross-mart fallback logic earn their cost specifically for multi-item orders and/or cases where the customer doesn't want to manually browse multiple marts to find an item. This is a UX/product positioning decision, not a technical restriction — a customer is free to use the Shopping Assistant for a single item if they prefer.

---

## 7. External Interfaces

### 7.1 Ingestion API
FastAPI service in front of Postgres. Accepts sale/order events (line items: item ID, quantity, sale price, timestamp) from either the storefront checkout or (in production) a real POS/checkout system. Also the entry point for tenant onboarding (registering a new mart, provisioning its schema, loading initial KSOR policies).

### 7.2 Wholesaler agent contract (stub for v1)
A Dapr service invocation contract is designed as if the real Wholesaler agent existed, even though v1 points it at a fake/stub implementation. Request: order details (item, quantity, requesting mart). Response: confirmation, ETA, price terms. This lets the integration boundary be swapped for a real Wholesaler agent later without redesigning the Inventory agent's workflow.

---

## 8. Non-Functional Requirements

- **Security/isolation:** schema-per-tenant; no cross-tenant data leakage except the deliberate, scoped Shopping Assistant read-access exception (§4.3).
- **Observability:** Langfuse for both tracing and evals (single tool, per project decision — differs from the author's general Langfuse+Braintrust preference).
- **Durability:** all multi-step processes must be resumable after failure via Dapr Workflows; no silent data loss on crash.
- **Idempotency:** every state-changing agent action carries an idempotency key.
- **Auditability:** all transactional data (`bills`, `bill_items`, `orders`) is immutable and permanent.

---

## 9. Governance Model (replaces formal task-transition framework)

Rather than a static human/AI task matrix, escalation is **rule-driven via KSOR**:
- KSOR stores role-based permissions per agent (what it may do autonomously) and blast-radius thresholds (e.g. order value ceiling, unfamiliar supplier).
- Anything within the safe blast radius executes fully automated.
- Anything beyond it pauses the workflow and invokes the Owner approval gate.
- The Owner is never a standing supervisor — only a conditional gate inside the workflow.

---

## 10. Assumptions and Dependencies

- KSOR (`panaversity/ksor`) is available as an integratable framework/SDK; this project does not build it.
- Dapr (Service Invocation, Workflows, pub/sub) is available in the deployment environment (Kubernetes + Dapr sidecars).
- Postgres with `pgvector` extension is available for both KSOR and item-embedding search.
- The Wholesaler agent, when eventually built, will conform to the contract defined in §7.2.

---

## 11. Open Items (explicitly deferred, not forgotten)
- Real Wholesaler agent build-out and live integration.
- Real payment gateway integration.
- Cross-mart shared search index (v1 does live per-request cross-schema search only, no precomputed index).
- Formal frontend design decisions beyond "React + Tailwind" (component structure, specific UX flows for disambiguation dialogs, etc.) — to be designed incrementally, one feature at a time, per CLAUDE.md working process.