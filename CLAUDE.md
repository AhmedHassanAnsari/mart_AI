# CLAUDE.md — Operating rules for this project

This file governs how Claude (via Claude Code or any agentic coding session) works on the AI Workforce Orchestrator project. Read this before touching any code. `spec.md` is the source of truth for what the system does — this file governs *how* to work on it and `user.md` tells what the suer want from a feature and its acceptance criteria.

---

## 1. The golden rule: never assume, always ask

This is the single most important rule in this file.

- If a requirement, table, field, API shape, or UX flow is not explicitly written in `spec.md`, **do not invent it**. Stop and ask the developer (Ahmed).
- If two reasonable implementations both seem to satisfy `spec.md`, **do not silently pick one**. Present the options and ask which to use.
- If a task seems to require a library, framework, service, or pattern not listed in §2 below, **do not add it silently**. Ask first, and explain why it's needed.
- "It's a reasonable default" is not a justification for proceeding without asking. Reasonable-but-unconfirmed is still unconfirmed.
- When in doubt, under-build and ask, rather than over-build and guess.

## 2. Approved technical stack — do not deviate without asking

**Backend / agents:**
- OpenAI Agents SDK
- FastAPI
- MCP (Model Context Protocol)
- Postgres + pgvector
- Dapr (Service Invocation, Workflows, pub/sub)
- KSOR (`panaversity/ksor`) — integrated as a dependency, never re-implemented

**Deployment:**
- Docker
- Kubernetes
- Helm
- CI/CD (details TBD — ask before choosing a specific CI tool)

**Observability:**
- Langfuse (both tracing and evals, for this project specifically — do not add Braintrust here without asking, even though it's used in the developer's other projects)

**Frontend:**
- HTML, CSS, Tailwind CSS
- React

**Package Management**
- use uv to add packages like `uv add openai-agents` and `uv add fastapi[standard]`

If a task seems to need something outside this list (a new npm package, a different database, a different agent framework, a different CSS approach), stop and ask before adding it.

## 3. Always check for skills and MCP servers before starting a task

Before implementing anything:
1. Check whether a relevant Claude Code skill already exists for the task (e.g. document generation, a specific framework's best practices).
2. Check whether a relevant MCP server is available or connected that would help (e.g. a Postgres MCP server, a Dapr-related tool, GitHub, etc.).
3. If a skill or MCP server that would clearly help is **not currently available**, tell the developer explicitly what's missing and why it would help, and offer to assist in setting it up or connecting it, rather than working around its absence silently.
4. Do not proceed to build a workaround for a missing skill/MCP server without first surfacing the gap to the developer.

## 4. Working process — one thing at a time

- Do not implement multiple unrelated pieces of the system in one pass. Pick one concrete, scoped piece of work (one table, one endpoint, one agent's reasoning step), confirm the plan with the developer, implement it, then stop.
- After finishing a scoped piece, summarize what was built and explicitly ask what to work on next — do not chain into the next feature unprompted.
- Follow the build order implied by `spec.md`'s dependency structure (e.g. shared tables before tenant-scoped tables; ingestion API before agent reasoning logic) unless told otherwise.

## 5. Respect the architectural constraints already decided

These are locked decisions from the design phase — do not silently redesign them:
- Schema-per-tenant isolation; `tenants`/`customers`/`categories`/`tenant_categories` are global/shared, everything else is per-tenant-schema.
- Agents never call each other directly — all agent-to-agent communication goes through Dapr Service Invocation.
- Durable multi-step processes use Dapr Workflows, not a custom retry mechanism.
- Conflict prevention uses idempotency keys, not locking.
- Agent "wake" triggers are event-driven (Postgres NOTIFY → Dapr pub/sub), never a polling watcher script.
- The Owner approval gate is conditional (invoked only on KSOR blast-radius escalation), never a standing supervisor loop.
- The Shopping Assistant agent is global with broad read / narrow scoped write — do not give it blanket write access across tenants.
- Cost price is snapshotted at time of sale in `bill_items` — never computed retroactively from current item price.

If a task seems to require breaking one of these constraints, stop and ask — do not quietly work around it.

## 6. Out-of-scope reminders

Do not build these unless explicitly asked to move them into scope:
- A real Wholesaler agent (stub/contract only, per `spec.md` §7.2)
- Real payment gateway integration
- A precomputed cross-mart search index

## 7. When you're not sure this file or spec.md is still accurate

`spec.md` and this file reflect the design as of the last update. If something in the codebase seems to contradict them, or a decision seems to have changed in conversation but isn't reflected here yet, flag the mismatch to the developer rather than trusting one source silently over the other.

## 8. Maintaining consistency
- Make sure spec.md, user.md and CLAUDE.md are consistent on feature being implemented and no contradiction exist, if contradiction exists and ambiguity is present, escalate to developer and require his input.