# AI Workforce Orchestrator

The AI Workforce Orchestrator is a multi-tenant platform that allows retail marts to onboard their operations onto an AI-driven agent workforce. It leverages a sophisticated architectural stack to ensure data isolation, governed autonomy, and durable execution.

## 🚀 Architecture Overview

The system is designed as an "FDE-style" platform: one core orchestration layer serving multiple independent marts (tenants).

### Core Technical Stack
- **Backend:** FastAPI, OpenAI Agents SDK
- **Orchestration:** Dapr (Service Invocation, Workflows, Pub/Sub)
- **Database:** Postgres + pgvector (Schema-per-tenant isolation)
- **Governance:** KSOR (Knowledge System of Record) for policy-driven "blast radius" control
- **Observability:** Langfuse (Tracing and Evals)
- **Frontend:** React, Tailwind CSS

### Key Architectural Decisions
- **Schema-per-Tenant:** Hard data isolation. Each mart gets its own Postgres schema for items, inventory, and orders.
- **Dapr-First Communication:** Agents never call each other directly; all communication goes through Dapr Service Invocation for centralized coordination and idempotency.
- **Durable Workflows:** Multi-step processes (like Order $\to$ Wholesaler $\to$ Verification) are managed by Dapr Workflows to ensure they are resumable and crash-tolerant.
- **Governed Autonomy:** Instead of a supervisor loop, the system uses KSOR policies. If an agent's action exceeds its "blast radius" (e.g., too expensive an order), the workflow automatically triggers a human-in-the-loop approval gate.
- **Event-Driven Wakeup:** Agents are stateless and event-driven. A Postgres trigger $\to$ Dapr Pub/Sub chain wakes the Inventory Agent only when stock crosses a reorder point.

## 🤖 Agent Workforce

1. **Shopping Assistant (Global):** A customer-facing agent that performs semantic search across all marts to help users find items and place orders via natural language.
2. **Inventory Agent (Per-Mart):** Reasons about sales velocity and supplier terms to decide *what* and *how much* to reorder.
3. **Verification Agent (Per-Mart):** Handles the "goods received" flow, confirming deliveries via QR/Camera.
4. **Wholesaler Agent (Stubbed):** External interface for procurement.

## 🛠️ Getting Started

### Prerequisites
- Docker & Kubernetes (or Docker Desktop with Kubernetes enabled)
- Dapr CLI installed
- Postgres instance with `pgvector` extension

### Setup & Deployment
1. **Clone the repository:**
   ```bash
   git clone https://github.com/AhmedHassanAnsari/mart_AI.git
   cd mart_AI
   ```

2. **Infrastructure:**
   Use the provided `docker-compose.yml` to spin up the database and supporting services.
   ```bash
   docker-compose up -d
   ```

3. **Backend Services:**
   The project uses `uv` for Python package management.
   ```bash
   uv sync
   uv run main.py
   ```

4. **Dapr Initialization:**
   Ensure Dapr is initialized and the components (statestore, pubsub) defined in `/dapr/components` are applied to your cluster.

## 📖 Project Structure
- `/api`: FastAPI endpoints for ingestion and onboarding.
- `/dapr`: Dapr component configurations.
- `/db`: Database management and schema provisioning logic.
- `/spec.md`: The source of truth for system requirements and design.
- `/CLAUDE.md`: Operating rules for development.

## 🛡️ Security & Governance
- **Data Isolation:** Strict schema-level separation prevents cross-tenant leakage.
- **Least Privilege:** The Shopping Assistant has broad read access (for search) but strictly scoped write access (for order creation).
- **Auditability:** All transactional records are immutable and permanent.
