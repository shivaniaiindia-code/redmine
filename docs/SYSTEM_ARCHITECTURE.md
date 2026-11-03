# SYSTEM ARCHITECTURE SPECIFICATION
## Company Intelligence Platform: Enterprise Project, Team, Employee & AI-Powered Management System

---

## 1. Executive Summary & Topology

The **Company Intelligence Platform** is a centralized operational intelligence web platform designed to give leadership, project managers, team leads, and employees real-time visibility into project health, team velocity, individual workloads, and historical contributions. It unifies project tracking from external sources (such as Redmine) with an internal notification engine, Google Chat broadcast spaces, and an AI-powered conversational intelligence layer powered by OpenRouter.

### 1.1 High-Level Architecture Topology

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Layer (Next.js 14+ Web Application)"]
        TOPBAR["Top Navigation Bar<br/>• Global Search (Ctrl+K)<br/>• AI Assistant Drawer Trigger<br/>• System Notification Bell (Badge: 12)<br/>• User Profile"]
        SIDEBAR["Sidebar Navigation<br/>• Dashboard (Active)<br/>• Projects, Teams, Employees, Tasks<br/>• Notifications (12)<br/>• AI Assistant & Reports<br/>• Integrations (Redmine ✓, Google Chat ✓)<br/>• Administration"]
        DASH["Main Management Canvas<br/>• Greeting & Range Filter (Last 7 Days)<br/>• 6 Top KPI Metrics Cards<br/>• 3-Col Visual Analytics (Donut, Task Bars, Workload)<br/>• 3-Col Operational Feeds (Deadlines, Activity, Notifications)"]
        
        TOPBAR --- SIDEBAR --- DASH
    end

    subgraph APILayer ["Backend API Gateway (FastAPI 0.110+)"]
        AUTH_MW["JWT Auth & Role-Based Access Control (RBAC)"]
        ROUTERS["Modular FastAPI Routers (/api/v1)"]
        AUTH_MW --> ROUTERS
        
        subgraph Services ["Core Business Logic Services"]
            ANALYTICS_SRV["Analytics & Metric Engine"]
            PROJECT_SRV["Project & Team Service"]
            EMPLOYEE_SRV["Employee 360 & Skill Service"]
            SYNC_SRV["Redmine Synchronization Service"]
            NOTIF_SRV["Dual-Dispatch Notification & Escalation Service"]
            AI_SRV["AI Orchestrator & Deterministic Tool Caller"]
        end
        
        ROUTERS --> Services
    end

    subgraph DualDispatch ["Dual-Dispatch Notification Engine"]
        IN_APP_PUSH["In-App Push (SSE / WebSockets)<br/>• System Notification Bar & Bell Drawer"]
        ADMIN_MIRROR["Admin Google Chat Webhook Dispatcher<br/>• 100% 1:1 Mirroring in Cards v2 Format"]
        NOTIF_SRV --> IN_APP_PUSH
        NOTIF_SRV --> ADMIN_MIRROR
    end

    subgraph DataLayer ["Data & Storage Layer"]
        DB[(PostgreSQL 16 / SQLite for Dev)]
        ALEMBIC["Alembic Migrations Engine"]
        CACHE[(Redis / Memory Cache)]
        DB --- ALEMBIC
    end

    subgraph BackgroundLayer ["Background Workers & Schedulers"]
        SCHEDULER["Background Scheduler (APScheduler / Celery)"]
        SYNC_WORKER["Redmine Delta Poller (Watermark)"]
        BRIEFING_WORKER["Daily Briefing & Escalation Dispatcher"]
        SCHEDULER --> SYNC_WORKER
        SCHEDULER --> BRIEFING_WORKER
    end

    subgraph ExternalIntegrations ["External Integrations"]
        REDMINE["Redmine Server (REST API)"]
        GOOGLE_CHAT["Admin Google Chat Space & Team Spaces"]
        OPENROUTER["OpenRouter API (Claude 3.5 Sonnet / Gemini 2.0)"]
    end

    ClientLayer <-->|REST API & SSE| APILayer
    Services --> DB
    Services --> CACHE
    BackgroundLayer --> Services
    IN_APP_PUSH -.->|Real-time Events| TOPBAR
    ADMIN_MIRROR -->|Cards v2 HTTPS POST| GOOGLE_CHAT
    SYNC_SRV <-->|REST API + API Key| REDMINE
    AI_SRV <-->|OpenAI-Compatible REST| OPENROUTER
```

---

## 2. Dashboard UI Layout Architecture (Reference Visual Design)

The primary management dashboard implements the professional enterprise layout structured below:

```mermaid
graph TD
    subgraph Shell ["Application Shell (Responsive Desktop Layout)"]
        subgraph TopNav ["Top Navigation Bar (Sticky Header)"]
            BRAND["Brand Logo & CIP Title"]
            SEARCH["Global Omni-Search Bar (Ctrl + K)"]
            AI_BTN["✨ AI Assistant Drawer Trigger"]
            BELL["🔔 System Notification Bell [Badge: 12]"]
            AVATAR["User Avatar (Admin)"]
            BRAND --- SEARCH --- AI_BTN --- BELL --- AVATAR
        end

        subgraph Body ["Dashboard Body Grid"]
            subgraph LeftSidebar ["Sidebar Navigation (Dark Indigo Theme)"]
                S1["📊 Dashboard (Active)"]
                S2["📁 Projects"]
                S3["👥 Teams"]
                S4["👤 Employees"]
                S5["☑️ Tasks"]
                S6["🔔 Notifications [12]"]
                S7["✨ AI Assistant"]
                S8["📈 Reports & Analytics"]
                subgraph S_INTEG ["Integrations (Accordion)"]
                    INT_R["Redmine: Synced ✓"]
                    INT_G["Google Chat: Connected ✓"]
                end
                S9["⚙️ Administration"]
                S_FOOT["CIP v1.0.0"]
            end

            subgraph MainCanvas ["Main Content Area"]
                GREETING["Good Morning, Admin 👋 | Date Filter: Last 7 Days ⌵"]

                subgraph KPIRow ["Row 1: Key Performance Indicators (6 KPI Metric Cards)"]
                    K1["📁 Active Projects: 18 (+12%)"]
                    K2["☑️ Open Tasks: 146 (+8%)"]
                    K3["⚠️ Projects at Risk: 3 (+1)"]
                    K4["👥 Total Employees: 42 (No change)"]
                    K5["🏢 Teams: 5"]
                    K6["✅ Task Completion: 78% (+6pp)"]
                end

                subgraph VisualAnalyticsRow ["Row 2: Visual Analytics (3 Cards)"]
                    C1["Project Status Overview<br/>• Donut Chart (18 Projects)<br/>• On Track 11 | At Risk 3 | In Progress 2 | Completed 2"]
                    C2["Task Distribution<br/>• Bar Chart by Status<br/>• In Progress 64 | Pending 42 | Overdue 18 | Blocked 12 | Completed 76"]
                    C3["Team Workload<br/>• Horizontal Stacked Bars<br/>• AI Team (34) | Dev (52) | QA (28) | Research (20) | Ops (12)"]
                end

                subgraph FeedsRow ["Row 3: Operational Feeds & Notification Bar (3 Cards)"]
                    F1["Upcoming Deadlines<br/>• ANPR System (2d - Critical)<br/>• Document AI (3d - Warning)<br/>• Invoice OCR (5d)<br/>• Vehicle Analytics (7d)"]
                    F2["Recent Activities<br/>• Model training pipeline completed<br/>• Data validation assigned<br/>• ANPR System: At Risk → On Track<br/>• Priya Mehta added to AI Team"]
                    F3["System Notification Bar (12)<br/>• ANPR System deadline in 2 days (Critical)<br/>• 3 overdue tasks in Dev Team<br/>• Daily Team Summary ready<br/>• Review meeting tomorrow<br/><b>[Mirrored 1:1 to Admin Google Chat]</b>"]
                end
            end
        end
    end
```

---

## 2. Multi-Agent Development & Organizational Model

To develop, verify, and maintain this enterprise platform, work is partitioned across **7 specialized engineering agents** governed by a **Main Orchestrator Agent**:

```mermaid
flowchart TD
    MOA["Main Orchestrator Agent<br/>• Architecture, Task Planning, Integration & Code Review"]
    
    FA["Frontend Agent<br/>• Dashboard, Employee UI, Project & Team Screens"]
    BA["Backend Agent<br/>• APIs, Business Logic, Authentication & RBAC"]
    RA["Redmine Agent<br/>• API Discovery, Sync & Data Mapping"]
    NA["Notification Agent<br/>• Rules, Scheduling & Google Chat Webhooks"]
    AA["AI Agent<br/>• OpenRouter, Deterministic Tools & Grounded Responses"]
    QA["QA Agent<br/>• Unit/Integration Testing, Security & Validation"]

    MOA --> FA
    MOA --> BA
    MOA --> RA
    MOA --> NA
    MOA --> AA
    MOA --> QA

    FA <--> BA
    BA <--> RA
    BA <--> NA
    BA <--> AA
    QA -.->|Audits & Verifies| FA
    QA -.->|Audits & Verifies| BA
    QA -.->|Audits & Verifies| RA
    QA -.->|Audits & Verifies| NA
    QA -.->|Audits & Verifies| AA
```

### Agent Roles & Boundaries Matrix

| Agent | Core Responsibilities | Input Artifacts | Output Deliverables |
|---|---|---|---|
| **Main Orchestrator Agent** | Architecture governance, cross-module schema alignment, task planning, pull request review, progress tracking. | Master System Prompt, User Requirements | Architecture Specs, System Models, Sprint Roadmaps, Code Review approvals. |
| **Frontend Agent** | Building responsive, role-tailored dashboards (Company, Project, Team, Employee 360), reusable components, UI state management, Recharts analytics. | UI/UX Design System, API contracts | Next.js components, page routes, state hooks, chart visualizations. |
| **Backend Agent** | FastAPI endpoints, SQLAlchemy async models, database migrations, authentication, RBAC enforcement, query optimization. | API Design, Database Design, RBAC Matrix | FastAPI routes, schemas, database models, auth middleware. |
| **Redmine Agent** | Redmine REST API client, schema discovery, delta synchronizer, entity mappers (projects, issues, time entries, custom fields), resilience/rate limiting. | Redmine Data Mapping spec, Redmine API docs | Sync engine, mapping algorithms, synchronization logs, health status. |
| **Notification Agent** | Event dispatching, severity tagging, rule evaluation, escalation queues, user preference filters, Google Chat webhook card formatting. | Notification Rules spec, Google Chat card layout | Notification dispatcher, background scheduler, Google Chat client, daily briefings. |
| **AI Agent** | OpenRouter integration, tool-use framework (deterministic SQL/metric tools), role-aware query filtering, grounded responses with evidence citations. | AI Architecture spec, DB schemas | AI Chat service, tool execution handlers, context builders, token/audit tracking. |
| **QA Agent** | Test automation (pytest for backend, Vitest/Playwright for frontend), security auditing (RBAC penetration, SQL injection, token leaks), performance benchmarking. | Acceptance Criteria, Test Scenarios | Test suites, security scan reports, load test scripts, CI pipelines. |

---

## 3. Technology Stack Specification

### 3.1 Frontend Stack
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript 5.x (strict type checking enabled)
- **Styling**: Tailwind CSS with enterprise color palettes (slate/indigo/neutral themes)
- **Component Primitives**: Radix UI / shadcn/ui (Accessible, headless, customizable)
- **Icons**: Lucide React
- **Data Visualization**: Recharts (Burn-down charts, team velocity, project status donuts, workload bars)
- **State Management**: TanStack Query (React Query) for server state caching + Zustand for lightweight local UI state
- **HTTP Client**: Axios / Fetch with automatic auth token refresh

### 3.2 Backend Stack
- **Framework**: FastAPI (Python 3.11+)
- **Async Runtime**: AnyIO / Uvicorn
- **ORM & Migrations**: SQLAlchemy 2.0 (asyncio syntax) + Alembic for migrations
- **Data Validation & Serialisation**: Pydantic v2 (Strict typing, JSON schema generation)
- **Authentication**: OAuth2 Password Flow + PyJWT (Access Tokens & Refresh Tokens)
- **Password Hashing**: Passlib with bcrypt / Argon2
- **Database Engine**: PostgreSQL 16 (production) / SQLite via aiosqlite (local development & unit testing)
- **Task Scheduling & Worker**: APScheduler 3.x / Celery with Redis for asynchronous background tasks

### 3.3 Integrations & Third-Party APIs
- **Redmine API**: `python-redmine` and `httpx` async HTTP client with exponential backoff
- **Google Chat**: HTTPS Webhook client with Google Chat Card v2 format
- **AI Gateway**: OpenRouter API (`https://openrouter.ai/api/v1`) using `httpx` or `openai` SDK pointing to custom base URL, supporting models such as `anthropic/claude-3.5-sonnet`, `openai/gpt-4o`, `google/gemini-2.0-flash`.

---

## 4. Security & Role-Based Access Control (RBAC) Architecture

The platform enforces strict role boundaries across all API endpoints and frontend views.

### 4.1 Role Hierarchy & Permissions

```mermaid
graph TD
    SA["Super Administrator<br/>(Full system access, configs, API keys, audit logs)"]
    CM["Company Management<br/>(Company-wide dashboards, all projects/teams, executive reports)"]
    PM["Project Manager<br/>(Assigned projects, members, task health, project alerts)"]
    TL["Team Lead<br/>(Assigned team dashboard, member workloads, team tasks, blockers)"]
    EMP["Employee<br/>(Personal 360 dashboard, assigned tasks, historical contributions)"]

    SA --> CM
    CM --> PM
    CM --> TL
    PM --> EMP
    TL --> EMP
```

### 4.2 Security Principles
1. **Zero Secret Leaks**: API tokens for Redmine, Google Chat webhooks, and OpenRouter keys are stored in encrypted environment variables or database settings tables with restricted Super Admin access. They are never sent to the client.
2. **Deterministic Data Scoping**: Every API request extracts `current_user` from the JWT token. Query scopes are computed server-side:
   - An employee querying `/api/v1/tasks` only gets tasks assigned to them.
   - A team lead querying `/api/v1/teams/{id}/workload` must be assigned as lead to `{id}` or have `Company Management`/`Super Admin` role.
3. **Audit Logging**: Any administrative changes (role modification, integration key update, sync trigger, manual escalation) write an immutable record to the `audit_logs` table.
4. **AI Output Grounding**: The AI assistant never executes raw user SQL. It invokes pre-authorized Python tools that inherit the caller's RBAC scope.

---

## 5. Repository Directory Layout

```
intelligent_projects_manager/
│
├── docs/                               # Architectural & Technical Blueprint
│   ├── SYSTEM_ARCHITECTURE.md          # Topology, agents, and security
│   ├── DATABASE_DESIGN.md              # Relational models, ERD, indexing
│   ├── API_DESIGN.md                   # OpenAPI router tree & endpoints
│   ├── REDMINE_DATA_MAPPING.md         # Redmine sync protocol & mappings
│   ├── NOTIFICATION_RULES.md           # Alert tiers, escalation, Google Chat
│   ├── AI_AGENT_ARCHITECTURE.md        # OpenRouter tool-use & grounding
│   └── IMPLEMENTATION_PLAN.md          # Phased sprint delivery roadmap
│
├── backend/                            # FastAPI Application
│   ├── app/
│   │   ├── api/                        # API route controllers
│   │   │   ├── v1/
│   │   │   │   ├── auth.py             # Login, token refresh, current user
│   │   │   │   ├── company.py          # Executive KPIs, company activity
│   │   │   │   ├── projects.py         # Project health, milestones, members
│   │   │   │   ├── teams.py            # Team velocity, workload, members
│   │   │   │   ├── employees.py        # Employee 360, skills, history
│   │   │   │   ├── tasks.py            # Tasks, blockers, deadlines
│   │   │   │   ├── notifications.py    # Notification center & preferences
│   │   │   │   ├── redmine.py          # Redmine sync triggers & status
│   │   │   │   ├── ai.py               # Conversational AI & tool queries
│   │   │   │   ├── reports.py          # Exportable reports & analytics
│   │   │   │   └── admin.py            # RBAC management & integrations
│   │   │   └── router.py               # Combined API v1 router
│   │   ├── core/                       # Core infrastructure
│   │   │   ├── config.py               # Pydantic Settings & env vars
│   │   │   ├── database.py             # SQLAlchemy async engine & session
│   │   │   ├── security.py             # Password hashing, JWT utils
│   │   │   └── permissions.py          # RBAC dependency guards
│   │   ├── models/                     # SQLAlchemy 2.0 ORM models
│   │   │   ├── user.py                 # Users, Roles, Permissions
│   │   │   ├── employee.py             # Employee profile, skills, history
│   │   │   ├── team.py                 # Teams, team memberships
│   │   │   ├── project.py              # Projects, milestones, contributors
│   │   │   ├── task.py                 # Tasks, time entries, blockers
│   │   │   ├── notification.py         # Notifications, rules, delivery
│   │   │   ├── redmine_sync.py         # Redmine mapping & sync logs
│   │   │   └── audit.py                # System audit logs
│   │   ├── schemas/                    # Pydantic v2 validation models
│   │   ├── services/                   # Business logic layer
│   │   │   ├── redmine_service.py      # Redmine client & delta synchronizer
│   │   │   ├── notification_service.py # Event dispatcher & escalation engine
│   │   │   ├── google_chat_service.py  # Webhook & card formatter
│   │   │   ├── ai_service.py           # OpenRouter client & tool executors
│   │   │   └── analytics_service.py    # Metric & KPI aggregations
│   │   └── workers/                    # Background scheduler tasks
│   │       ├── scheduler.py            # Periodic jobs (sync, briefings)
│   │       └── sync_worker.py          # Redmine polling worker
│   ├── alembic/                        # Database migration scripts
│   ├── tests/                          # Backend test suite (pytest)
│   ├── requirements.txt                # Python dependencies
│   └── main.py                         # Application entrypoint
│
├── frontend/                           # Next.js 14+ Application
│   ├── src/
│   │   ├── app/                        # App Router directory
│   │   │   ├── (auth)/login/           # Login screen
│   │   │   ├── (dashboard)/
│   │   │   │   ├── layout.tsx          # App shell (Sidebar, Header, Search)
│   │   │   │   ├── page.tsx            # Company Dashboard
│   │   │   │   ├── projects/           # Projects list & Project detail
│   │   │   │   ├── teams/              # Teams list & Team detail
│   │   │   │   ├── employees/          # Employee directory & 360 profile
│   │   │   │   ├── tasks/              # Task board / list / blockers
│   │   │   │   ├── notifications/      # Notification Center & History
│   │   │   │   ├── reports/            # Reports generator & export
│   │   │   │   └── admin/              # User, team, and integration admin
│   │   ├── components/                 # Reusable UI widgets
│   │   │   ├── ui/                     # Button, Dialog, Dropdown, Input, etc.
│   │   │   ├── layout/                 # Sidebar, TopNav, GlobalSearch
│   │   │   ├── cards/                  # KPICard, HealthBadge, RiskBadge
│   │   │   ├── charts/                 # BurnDownChart, WorkloadChart, Donut
│   │   │   ├── ai/                     # AssistantDrawer, GroundedResponseCard
│   │   │   └── notifications/          # NotificationBell, BriefingModal
│   │   ├── lib/                        # Client utilities, API client, auth
│   │   ├── types/                      # TypeScript definitions
│   │   └── hooks/                      # Custom React hooks (useAuth, useTasks)
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
│
├── plan.md                             # Master System Prompt & Requirements
└── README.md                           # Quickstart & Repository Overview
```



---

## 6. End-to-End Operational Sequence (7-Agent Interaction)

The following sequence visualizes how the 7 specialized agents cooperate during a live operational cycle:

```mermaid
sequenceDiagram
    autonumber
    participant Redmine as External Redmine API
    participant RA as Redmine Agent (Sync Engine)
    participant BA as Backend Agent (DB & APIs)
    participant NA as Notification Agent (Dual-Dispatch)
    participant GChat as Admin Google Chat Space
    participant FA as Frontend Agent (Next.js UI)
    participant AA as AI Agent (OpenRouter)

    %% Step 1: Redmine Sync
    Note over RA,Redmine: Watermark Delta Sync Triggered
    RA->>Redmine: GET /issues.json?updated_on=>={watermark}
    Redmine-->>RA: Returns updated issues & custom fields
    RA->>BA: Upsert tasks, project links & mappings
    
    %% Step 2: Metric & Alert Evaluation
    BA->>BA: Calculate Project Health & Overdue SLA (ANPR System)
    BA->>NA: Operational Event: TASK_OVERDUE (Critical, 2 days left, 2 blocked)
    
    %% Step 3: Dual-Dispatch Notifications
    par Real-Time System Notification Bar Push
        NA->>FA: SSE Push -> Increment Bell Badge (12) & Add to Feed
    and 1:1 Admin Google Chat Mirroring
        NA->>GChat: HTTPS POST Cards v2 Payload (with 1-click deep link)
    end
    
    %% Step 4: Management UI Refresh
    FA->>BA: GET /api/v1/company/kpis & /feed
    BA-->>FA: Return updated KPIs (Active: 18, At Risk: 3, Open: 146)
    FA->>FA: Re-render Donut Chart, Task Distribution & Workload Bars
    
    %% Step 5: Grounded AI Assistant Query
    Note over FA,AA: Admin opens AI Assistant Drawer
    FA->>AA: User Query: "Why is the ANPR System at risk?"
    AA->>BA: Execute Tool: get_projects_overview(code="ANPR")
    BA-->>AA: Return verified DB record: 2 tasks blocked, 2 days to deadline
    AA->>AA: Synthesize grounded response citing [Task #1042] & [ANPR System]
    AA-->>FA: Return response with clickable citation chips
```


---

## 7. The Dual-Intelligence Architecture (Operational vs. Management Intelligence)

To guarantee absolute trust, transparency, and eliminate AI hallucinations, the platform strictly bifurcates intelligence into two distinct, decoupled layers:

```mermaid
flowchart TD
    subgraph LayerA ["Layer A: Operational Intelligence Engine (Deterministic & Exact)"]
        INPUTS["Raw Event Inputs<br/>• Redmine Sync (Issues, Milestones, Journals)<br/>• Internal Task Updates & Blocker Flags<br/>• Time Entries & Capacities"]
        
        CALC["Deterministic Python Metric Engine<br/>• Mathematical Overdue SLA Calculation<br/>• Critical Path & Blocker Blast Radius<br/>• Context-Switching Workload Formula<br/>• Milestone Slip & Budget Variance %"]
        
        PERSIST["Verified Facts Database<br/>• Exact KPI Counts (Active: 18, At Risk: 3)<br/>• Explainable Health Reason Strings<br/>• Triggered Alerts & Severity Tiers"]
        
        INPUTS --> CALC --> PERSIST
    end

    subgraph LayerB ["Layer B: Management Intelligence Layer (Conversational & Grounded)"]
        PROMPT["Management Natural Language Query<br/>'Why is the ANPR project at risk, and what is our delivery exposure?'"]
        
        TOOL_GATE["Deterministic Tool Gateway<br/>• Injects User RBAC Scope<br/>• Executes Python Tools on Layer A Data"]
        
        SYNTHESIS["OpenRouter LLM Synthesis (Claude 3.5 / Gemini 2.0)<br/>• Explains Bottlenecks Based Solely on Layer A Facts<br/>• Recommends Proactive Mitigations<br/>• Formats Executive Digests & Summaries"]
        
        CITATIONS["Grounded Output with Clickable Sources<br/>• Exact Project Code & Deep Link<br/>• Specific Blocker Task # & Assignee<br/>• Zero Hallucinated Records"]
        
        PROMPT --> TOOL_GATE
        PERSIST -.->|Grounded Verified Facts| TOOL_GATE
        TOOL_GATE --> SYNTHESIS --> CITATIONS
    end
```

### Architectural Safeguards
1. **Never Calculate in Prose**: Numbers, percentages, project health statuses, and overdue days are never computed by the LLM prompt. They are computed by Python code in Layer A and passed as verified arguments to Layer B.
2. **Explainable Health Grounding**: Every health badge in the UI (e.g. `AT_RISK`) is accompanied by the exact deterministic string generated by Layer A (e.g. *"2 critical path tasks overdue by 4 days, impacting Milestone Release 1.2.0"*).
3. **Audited Insights**: Every AI explanation generated in Layer B is stored in `ai_messages` alongside the exact tool output snapshot that grounded it.
