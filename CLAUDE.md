# CLAUDE.md & AGENT GUIDELINES
## Company Intelligence Platform: Enterprise Project, Team, Employee & AI-Powered Management System

---

## 1. Project Overview & Architecture

The **Company Intelligence Platform** is an enterprise-grade operational management web application that unifies:
1. Executive, Project, Team, and Employee 360-degree dashboards.
2. External issue tracking via **Redmine REST API** with watermark delta synchronization.
3. Event-driven notifications: **System Notification Bar** for every alert + **SMTP email to the Administrator** for urgent/critical alerts.
4. Grounded conversational AI assistant powered by **OpenRouter** and deterministic backend Python tools (zero hallucination).

All detailed system designs and schemas are located in [`docs/`](./docs/):
- [`docs/SYSTEM_ARCHITECTURE.md`](./docs/SYSTEM_ARCHITECTURE.md): System topology & 7-agent organization.
- [`docs/DATABASE_DESIGN.md`](./docs/DATABASE_DESIGN.md): Relational models, ERD, and historical preservation.
- [`docs/REDMINE_DATA_MAPPING.md`](./docs/REDMINE_DATA_MAPPING.md): Redmine discovery and delta sync protocol.
- [`docs/NOTIFICATION_RULES.md`](./docs/NOTIFICATION_RULES.md): Notification triggers (note: delivery is now in-app + SMTP email; Google Chat sections are superseded).
- [`docs/AI_AGENT_ARCHITECTURE.md`](./docs/AI_AGENT_ARCHITECTURE.md): OpenRouter gateway & deterministic tool execution.
- [`docs/API_DESIGN.md`](./docs/API_DESIGN.md): Modular FastAPI REST routes and RBAC guards.
- [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md): Phased sprint delivery roadmap.

---

## 2. Multi-Agent Organization Model

Development and code modifications must respect the responsibilities of the **7 specialized agents**:

1. **Main Orchestrator Agent**: High-level architecture, task breakdown, schema consistency, and code review.
2. **Frontend Agent**: Next.js 14+ App Router, TypeScript, Tailwind CSS, shadcn/ui, Recharts visualizations, Employee 360 & Project dashboards.
3. **Backend Agent**: FastAPI application, SQLAlchemy 2.0 async models, Alembic migrations, JWT authentication, and RBAC enforcement.
4. **Redmine Agent**: Redmine REST client (`httpx`), metadata discovery, watermark sync loop, mapping tables (`redmine_mappings`), and offline cache fallback.
5. **Notification Agent**: Rule evaluation engine, alert dispatching, in-app notification bar, escalation chains, and **SMTP email delivery of urgent/critical alerts to the Administrator**.
6. **AI Agent**: OpenRouter LLM integration, deterministic Python tool catalog (`get_projects_overview`, `get_employee_workload`, etc.), RBAC context filtering, and source citation badges.
7. **QA Agent**: Pytest test suites, Vitest UI testing, security auditing, and boundary penetration testing.

---

## 3. Mandatory Development Rules & Constraints

1. **Admin SMTP Email Alerting Mandate** (replaced Google Chat mirroring, 2026-11-03):
   - Every notification is recorded in the **System Notification Bar** (in-app header bar, notification drawer, bell badge).
   - Every **URGENT** and **CRITICAL** notification **MUST** be delivered by SMTP email to the designated administrator (default `anil.aiindia@gmail.com`, configurable in Administration). Google Chat dispatch has been removed.
   - Emails must include full event metadata, severity tagging, and a deep link back to the platform. Every delivery attempt is tracked in `notification_deliveries` (`EMAIL_SMTP`: SENT / FAILED / NOT_CONFIGURED / DISABLED).
   - SMTP credentials live only in `backend/.env`; they are never stored in the database or returned by the API.
2. **Dual-Intelligence Principle**:
   - **Operational Intelligence (Deterministic)**: Overdue counts, project health status, burn-down percentages, capacity hours, and critical path slip MUST be calculated deterministically in backend Python code.
   - **Management Intelligence (Grounded AI)**: The AI layer explains bottlenecks, summarizes delivery risks, and answers management questions based strictly on the verified operational facts.
3. **Dashboard-First Priority**: The primary product is the management dashboard; the AI assistant is an integrated intelligence feature within the dashboard.
4. **No Fake Production Data**: Never represent mock or fabricated records as live company data. Fixtures are strictly for local UI testing and must be clearly labeled.
5. **No Non-Functional Buttons**: Never render placeholder buttons or non-functional UI controls. Every control must trigger a verified route or modal.
6. **Strict RBAC Enforcement**: Extract `current_user` from the validated JWT token on every protected endpoint. Never trust client-supplied user IDs or role claims.
7. **Preserve Historical Continuity**: Employee historical contributions and past completed projects must be preserved permanently in `historical_contributions`, even if current team memberships change.
8. **Migrations Required**: All database schema alterations must be managed via versioned Alembic migration scripts. No raw ad-hoc `ALTER TABLE` in production code.

---

## 4. Specialized Workspace Skills (`.agents/skills/`)

Our coding agents operate with reference-backed runbooks:
- `company-intel-workflow`: Main Orchestrator phased progression and quality gates.
- `project-manager`: Planning, milestones, risk register, RACI matrix, and closure (Asana + VoltAgent).
- `frontend-dashboard`: Next.js 14 App Router, dark indigo theme tokens, and Recharts.
- `backend-fastapi-rbac`: FastAPI async endpoints, SQLAlchemy 2.0, and RBAC guards.
- `redmine-sync`: Discovery, watermark delta polling, journals change history, and pagination (MCP Market + Redmine CLI).
- `notification-google-chat`: System notification bar rules (its Google Chat mirroring parts are superseded by SMTP email alerting).
- `ai-openrouter-grounding`: OpenRouter gateway, deterministic tools catalog, and source citation chips.
- `qa-security-testing`: Pytest fixtures, RBAC penetration testing, and API error resilience.
- `employee-360-growth`: Employee 360, career ladder rubrics, and historical continuity.

---

## 4. Technology Stack & Standard Commands

### Backend (`/backend`)
- **Runtime**: Python 3.11+
- **Framework**: FastAPI + Uvicorn
- **ORM & DB**: SQLAlchemy 2.0 (asyncio) + Alembic + PostgreSQL 16 (or SQLite with aiosqlite for local tests)
- **Validation**: Pydantic v2
- **Testing**: Pytest with `pytest-asyncio`

```bash
# Setup backend environment
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests
pytest -v
```

### Frontend (`/frontend`)
- **Runtime**: Node.js 20+ / 24+
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript 5.x (strict mode)
- **Styling**: Tailwind CSS + shadcn/ui primitives + Lucide React
- **Charts**: Recharts
- **State**: TanStack Query (React Query) + Zustand

```bash
# Setup frontend dependencies
cd frontend
npm install

# Start development server
npm run dev

# Run linting and type checking
npm run lint
npm run build
```

---

## 5. Phased Implementation Sequence

- **Phase 0**: Architectural Blueprints & Planning (Complete in `docs/`)
- **Phase 1**: System Foundation, Database & Core RBAC (FastAPI bootstrap, Auth, Next.js App Shell)
- **Phase 2**: Redmine Integration & Data Synchronization Engine (Discovery, watermark sync, cache)
- **Phase 3**: Core Role-Based Dashboards & Work Management (Company, Project, Team, Employee 360)
- **Phase 4**: Notification Engine & SMTP Email Alerting (In-app bar + urgent/critical email to the Administrator)
- **Phase 5**: AI Company Assistant (OpenRouter + Deterministic Tool Registry + RBAC Grounding)
- **Phase 6**: Reports, Analytics & Employee Growth (Export engine, skill matrix)
- **Phase 7**: QA Validation, Security Auditing & Production Hardening

