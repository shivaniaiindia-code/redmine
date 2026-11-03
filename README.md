# Company Intelligence Platform
### Enterprise Project, Team, Employee & AI-Powered Management System

A centralized internal company intelligence web platform that unifies project tracking, team workloads, individual employee contributions, real-time notifications with Google Chat, and conversational AI insights powered by OpenRouter.

---

## 🏛 System Architecture & Master Blueprints

Complete technical specifications and multi-agent development blueprints are documented in [`docs/`](./docs/):

1. **[System Architecture Specification](./docs/SYSTEM_ARCHITECTURE.md)**: High-level topology, multi-agent development organization, technology stack, and security model.
2. **[Database Design & ERD](./docs/DATABASE_DESIGN.md)**: Complete PostgreSQL entity relationship diagram, schema definitions, indexing, and historical preservation strategy.
3. **[Redmine Integration & Data Mapping](./docs/REDMINE_DATA_MAPPING.md)**: API discovery protocol, data mapping matrices, watermark delta synchronization, and rate-limiting resilience.
4. **[Notification Rules & Google Chat Integration](./docs/NOTIFICATION_RULES.md)**: Severity tiers, rule triggers, escalation matrix, and Google Chat Cards v2 webhook architecture.
5. **[AI Agent & Grounded Retrieval](./docs/AI_AGENT_ARCHITECTURE.md)**: OpenRouter multi-model gateway, deterministic tool calling, RBAC-aware context retrieval, and zero-hallucination citations.
6. **[API Design & Specifications](./docs/API_DESIGN.md)**: Modular FastAPI REST API routing tree, response envelopes, and RBAC dependency guards.
7. **[Phased Implementation Roadmap](./docs/IMPLEMENTATION_PLAN.md)**: Phase-by-phase delivery plan governed by the 7 specialized engineering agents.

---

## 🤖 Multi-Agent Development Organization

Development is structured across 7 specialized engineering roles:
- **Main Orchestrator Agent**: Architecture governance, task planning, integration, and code review.
- **Frontend Agent**: Next.js 14+ App Router, Tailwind CSS, 360 Dashboards, and UI visualizations.
- **Backend Agent**: FastAPI REST endpoints, SQLAlchemy async models, JWT authentication, and RBAC.
- **Redmine Agent**: Redmine API discovery, watermark delta sync, and entity mapping.
- **Notification Agent**: Rule evaluation, escalation cascades, and Google Chat webhook cards.
- **AI Agent**: OpenRouter LLM gateway, deterministic Python tool catalog, and grounded source citations.
- **QA Agent**: Test automation (pytest/Vitest), security auditing, and acceptance verification.

---

## 🚀 Recommended Tech Stack
- **Frontend**: Next.js 14+ (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, Recharts.
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (asyncio), Pydantic v2, Alembic.
- **Database**: PostgreSQL 16 (production) / SQLite via aiosqlite (local development).
- **Background Jobs**: APScheduler / Celery with Redis.
- **Integrations**: Redmine REST API, Google Chat Webhooks (Cards v2), OpenRouter AI API.
