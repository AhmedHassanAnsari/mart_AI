# AI Workforce Orchestrator

The AI Workforce Orchestrator is a multi-tenant platform designed to onboard retail mart operations onto an AI-driven agent workforce. This project demonstrates an architectural implementation of agentic workflows, multi-tenant data isolation, and governed autonomy.

## 🚀 Architecture Overview

The system is built as a scalable orchestration layer that can serve multiple independent marts (tenants).

### Core Technical Stack
- **Backend:** FastAPI, OpenAI Agents SDK
- **Orchestration:** Dapr (Service Invocation, Workflows, Pub/Sub)
- **Database:** Postgres + pgvector (Schema-per-tenant isolation)
- **Observability:** Langfuse (Tracing and Evals)
- **Infrastructure:** Docker, Kubernetes

### Key Architectural Implementations
- **Schema-per-Tenant:** Implements strict data isolation where each onboarded mart receives its own Postgres schema.
- **Dapr-First Communication:** Utilizes Dapr Service Invocation for agent-to-agent communication, ensuring that coordination is centralized and supports idempotency.
- **Event-Driven Triggering:** Uses Postgres triggers and Dapr Pub/Sub to wake agents based on real-time data changes (e.g., inventory crossing a reorder point).
- **Governed Autonomy:** Integration with a Knowledge System of Record (KSOR) to define policy-driven "blast radius" control for agent actions.

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

## 📖 Project Structure
- `/api`: FastAPI endpoints for ingestion and authentication.
- `/dapr`: Dapr component configurations.
- `/db`: Database management, migration scripts, and schema provisioning logic.
- `/agent`: Agent logic and workflow definitions.
- `/context_service`: Service for querying the Knowledge System of Record.
