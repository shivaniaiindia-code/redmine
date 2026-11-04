# CLAUDE_HANDOVER.md — Intelligent Projects Manager Handover Package

**Project**: Intelligent Projects Manager (Company Intelligence Platform)  
**Handover Date**: 2026-11-03  
**Author**: Teamwork Orchestrator  
**Target Recipient**: Autonomous Claude Agents / Engineering Team  
**Handover Status**: **Milestones 1 & 2 Fully Implemented and Empirically Verified (100% Pass Rate). Milestones 3, 4, and 5 fully scoped with detailed technical implementation blueprints below.**

---

## 1. Executive Summary & Project Baseline

The Intelligent Projects Manager platform has been brought from an unanchored state with UI empty-data defects and directory split-brains into an **empirically validated, production-grade baseline**.

### What Has Been Accomplished (Milestones 1 & 2 + E2E Track):
1. **Live Redmine Data Synchronization (`https://redmine.aiindia.ai`)**:
   - Live Redmine REST API client (`backend/app/services/redmine_service.py`) now synchronizes projects, users, issues, and project memberships.
   - Project memberships (`/projects/{id}/memberships.json`) are paginated and mapped to internal `ProjectMember` records (8 active members mapped across `aiinvoice` and `MILIT ANPR` projects with authentic roles like `aiinvoice` and `speech-ASR`).
   - Original Redmine timestamps (`created_on`, `updated_on`) are preserved with exact second-level precision into `Task.created_at` and `Task.updated_at`.
   - Issue change journals (`include=journals`) are mapped into `task_journals`.
   - Inactive/stale projects in the database are cleanly marked `INACTIVE` to prevent alerting noise.
2. **Database Split-Brain Resolution**:
   - Anchored SQLite database path in `backend/app/core/config.py` using `Path(__file__).resolve().parent.parent.parent / "company_intel.db"` with a Pydantic `@field_validator`.
   - Commands executed from the workspace root and `backend/` now point to the identical database file: `backend/company_intel.db`. Stale mock database at root quarantined to `.stale_mock_backup`.
3. **Primary Dashboard Views & UI Visibility**:
   - **Projects View**: Displays live Redmine projects with health badges, progress bars, and operational metrics. Fetch error handling disambiguates backend network/auth issues from true empty states.
   - **Teams View**: Displays project-wise teams grouped by project, showing member names, email addresses, and Redmine project role badges. Empty team cards ("0 Members") are completely eliminated through dual-layer backend and client-side filtering.
   - **Employees View**: Displays individual employee status badges (`ACTIVE`, `ON_LEAVE`, `DEPARTED`), current project assignment pills, and visual workload distribution bars calculating:
     $$\text{Workload Score} = \left(\frac{\text{Allocated Hours}}{\text{Weekly Capacity}}\right) \times \left(1 + 0.15 \times \max(0, \text{Active Projects} - 1)\right)$$
   - **Tasks View**: Displays original Redmine creation and update timestamps alongside due dates, with robust status filtering (`ALL`, `OVERDUE`, `BLOCKED`, `IN_PROGRESS`, `COMPLETED`).
   - **Global Sync Trigger**: Added "Sync Redmine Now" button in `TopNav.tsx` with animated spinner and live status feedback, triggering reactive cross-tab dashboard re-fetching.
4. **Build & Lint Verification**:
   - `frontend/eslint.config.mjs` fixed to use explicit ESM imports (`.js`). `npm run lint` passes with **0 errors**.
   - `npm run build` compiles with **0 errors** (5/5 static pages prerendered).
5. **E2E Testing Infrastructure**:
   - Created `TEST_INFRA.md` and `TEST_READY.md` establishing a 4-tier requirement-driven opaque-box testing framework.
   - **109 of 109 backend tests passing (100% pass rate)**:
     - 40 Tier 1 Core Feature Tests
     - 8 Tier 2 Boundary Tests
     - 5 Tier 3 Cross-Feature Integration Tests
     - 4 Tier 4 Real-World Scenario Tests
     - 8 M1 & M2 Empirical Challenge Tests
     - 44 Core Unit & Integration Tests

---

## 2. Environment & Live Credentials

- **Workspace Root**: `c:\Users\Anil Abhange\Downloads\intelligent_projects_manager`
- **Backend Directory**: `backend/`
- **Frontend Directory**: `frontend/`
- **Active Database**: `backend/company_intel.db` (SQLite with WAL mode enabled)
- **Python Virtualenv**: `backend/venv/Scripts/python.exe`
- **Redmine Instance**: `https://redmine.aiindia.ai`
- **Redmine Admin API Key**: `47cc9f603630e16fcb6f73e99a1111c59d080f18`
- **Default Alert Recipient**: `anil.aiindia@gmail.com`
- **OpenRouter AI Gateway**: `https://openrouter.ai/api/v1/chat/completions`
- **OpenRouter Model**: `qwen/qwen3.5-flash-02-23`
- **OpenRouter API Key**: Pre-configured in `backend/.env` (`sk-or-v1-95fe...`)

---

## 3. Verification Commands Baseline

Any Claude agent taking over can immediately verify system health with these commands:

```powershell
# 1. Run all 109 Backend Tests (Pytest)
cd "c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\backend"
.\venv\Scripts\pytest tests -v
# Expected: 109 passed in ~170s, exit code 0

# 2. Run Standalone E2E Runner (57 Tests)
cd "c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\backend"
.\venv\Scripts\python run_e2e_tests.py
# Expected: 57 passed, exit code 0

# 3. Verify Frontend Linting
cd "c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\frontend"
npm run lint
# Expected: 0 errors, exit code 0

# 4. Verify Frontend Production Build
cd "c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\frontend"
npm run build
# Expected: "Compiled successfully", 5/5 static pages, exit code 0
```

---

## 4. Detailed Roadmap & Technical Blueprint for Remaining Milestones

Per user directive, the remaining milestones are documented with exact file paths, line references, and implementation requirements:

### Milestone 3: Notification Engine & SMTP Email Alerting (Requirement R2)

#### Objective
Streamline notifications by removing legacy dispatch cards, adding category filter pills in the UI modal, and delivering all `CRITICAL` and `URGENT` alerts exclusively via SMTP to `anil.aiindia@gmail.com`.

#### Backend Implementation (`backend/`):
1. **Add SMTP Configuration (`backend/app/core/config.py` & `backend/.env`)**:
   Add to `Settings` class:
   ```python
   SMTP_HOST: str = "smtp.gmail.com"
   SMTP_PORT: int = 587
   SMTP_USERNAME: str = ""
   SMTP_PASSWORD: str = ""
   SMTP_USE_TLS: bool = True
   SMTP_FROM_EMAIL: str = "notifications@companyintel.ai"
   DEFAULT_ALERT_EMAIL: str = "anil.aiindia@gmail.com"
   ```
2. **Implement Email Service (`backend/app/services/email_service.py`)**:
   Create an asynchronous email dispatcher:
   ```python
   import asyncio, smtplib
   from email.mime.text import MIMEText
   from email.mime.multipart import MIMEMultipart

   class EmailService:
       @staticmethod
       def send_email_sync(host, port, username, password, use_tls, from_addr, to_addr, subject, html_body):
           msg = MIMEMultipart("alternative")
           msg["Subject"] = subject
           msg["From"] = from_addr
           msg["To"] = to_addr
           msg.attach(MIMEText(html_body, "html"))
           
           with smtplib.SMTP(host, port, timeout=10) as server:
               if use_tls:
                   server.starttls()
               if username and password:
                   server.login(username, password)
               server.send_message(msg)

       @classmethod
       async def send_alert_email(cls, recipient: str, title: str, message: str, severity: str, entity_type: str, entity_id: str):
           # Use asyncio.to_thread to prevent blocking FastAPI event loop
           # If credentials not set, log warning and gracefully record FAILED in notification_deliveries
           ...
   ```
3. **Update Notification Dispatcher (`backend/app/services/notification_service.py`)**:
   - In `create_and_dispatch`:
     ```python
     if severity in ["URGENT", "CRITICAL"]:
         # Deliver exclusively to anil.aiindia@gmail.com
         # Record NotificationDelivery with channel="EMAIL_SMTP", destination="anil.aiindia@gmail.com"
         # Mark status="SENT" or "FAILED"
     ```
   - Standard `INFO` and `WARNING` notifications remain in-app only and **do not trigger SMTP emails**.
4. **Update Notifications API (`backend/app/api/v1/notifications.py`)**:
   - Add query parameter support: `GET /api/v1/notifications/?category=all|critical|urgent|completed`.

#### Frontend Implementation (`frontend/`):
1. **Streamline `frontend/src/components/NotificationModal.tsx`**:
   - **Remove Legacy Elements**:
     - Remove `showTestForm` state (line 62).
     - Remove `handleTriggerTest` handler (lines 96–130).
     - Remove `+ Dispatch Custom Alert` toggle button (lines 228–234).
     - Completely delete the collapsible custom test dispatch form card (lines 245–283).
   - **Add Category Filter Tabs / Pills**:
     - Above the notifications list, add 4 filter pills:
       - `All`
       - `Critical` (badge with count)
       - `Urgent` (badge with count)
       - `Completed / Closed` (badge with count)
     - Filter notifications array dynamically based on the active tab.
2. **Streamline `frontend/src/components/views/AdminView.tsx`**:
   - Remove legacy Google Chat Webhook URL input and "Dispatch Channels" card (lines 183–320).
   - Replace Card 4 with a dedicated **SMTP Email Alerting Engine** card displaying:
     - Recipient: `anil.aiindia@gmail.com`
     - SMTP Server host and port
     - TLS active status
     - "Send Test Alert Email" trigger button calling `POST /api/v1/admin/smtp-test`.
3. **Streamline Labels**:
   - In `TopNav.tsx` and `NotificationsFeed.tsx`, update legacy text referencing "Google Chat Mirroring" to "Executive Alerting & SMTP Mirroring".

---

### Milestone 4: AI Assistant Grounding & Administration Configuration (Requirements R3 & R4)

#### Objective
Ensure the AI Assistant provides zero-hallucination, grounded answers regarding employee project assignments and live project statuses using real Redmine data, and complete the administration configuration APIs.

#### Backend Implementation (`backend/`):
1. **Enrich AI Grounding Context (`backend/app/services/ai_service.py`)**:
   - Currently, `get_grounded_context` filters out non-overdue/non-blocked tasks and does not map employees to their projects.
   - **Update**:
     - Query all active projects and their members:
       ```python
       # Build deterministic employee_assignments mapping
       # For each employee: project names, project codes, assigned roles, total assigned tasks
       ```
     - Query all live tasks (including In Progress, New, Resolved, Closed):
       ```python
       # For each project: total_tasks, in_progress_tasks, completed_tasks, overdue_tasks, blocked_tasks, assigned_members
       ```
     - Inject these deterministic structures into the system prompt context so `qwen/qwen3.5-flash-02-23` has complete visibility over who is working on what project.
2. **Deterministic Query Tools / Helpers**:
   - Implement structured retrieval methods:
     - `get_employee_assignments(employee_name: str)`
     - `get_project_live_status(project_name_or_code: str)`
   - Ensure the assistant formats responses with verified citations:
     - `[Project: <name> (#<code\>)](/projects/<id>)`
     - `[Employee: <name>](/employees/<id>)`
3. **Admin Settings API (`backend/app/api/v1/admin_config.py`)**:
   - Implement `GET /api/v1/admin/settings` returning aggregated status for:
     - Redmine API (`connected`, `url`, `last_synced_at`, `active_projects_count`)
     - OpenRouter AI (`model`, `connected`, `zero_hallucination_active`)
     - SMTP Email Alerting (`host`, `recipient_email`, `status`)
   - Implement `POST /api/v1/admin/smtp-test` to test email sending to `anil.aiindia@gmail.com`.

#### Frontend Implementation (`frontend/`):
1. **Modernize `AdminView.tsx`**:
   - Present a clean 4-card operational dashboard:
     - **Card 1**: Redmine Synchronization Engine (status, manual sync button, sync stats).
     - **Card 2**: SMTP Email Alerting Engine (recipient: `anil.aiindia@gmail.com`, test email button).
     - **Card 3**: OpenRouter AI Assistant (model: `qwen/qwen3.5-flash-02-23`, deterministic status).
     - **Card 4**: Automated Alerts Scanner (overdue/blocker scanner, manual scan button).
2. **AI Assistant Drawer (`frontend/src/components/AIAssistantDrawer.tsx`)**:
   - Verify sample prompts:
     - *"What projects is Anil Abhange currently working on?"*
     - *"What is the live status and health of the MILIT ANPR System?"*
   - Verify that citations render as clickable navigation links.

---

### Milestone 5: Full E2E Verification & Hardening

#### Objective
Run complete verification across the entire platform, pass 100% of automated tests, and harden against edge cases.

1. **Execute Full Test Matrix**:
   - `backend/venv/Scripts/python.exe run_e2e_tests.py` (Assert all 4 tiers pass).
   - `backend/venv/Scripts/pytest.exe tests -v` (Assert all unit, integration, and empirical tests pass).
   - `cd frontend; npm run lint` (Assert 0 errors).
   - `cd frontend; npm run build` (Assert 0 type errors, clean static generation).
2. **Live Integration Smoke Test**:
   - Click "Sync Redmine Now" in the UI TopNav.
   - Verify all views update reactively:
     - Projects view shows active Redmine projects (`aiinvoice`, `MILIT ANPR`).
     - Teams view displays project-wise member cards with roles.
     - Employees view displays workload bars and project assignment pills.
     - Tasks view shows original Redmine timestamps.
     - Urgent/Critical alert sends an email to `anil.aiindia@gmail.com`.
     - AI assistant answers project assignment queries deterministically.

---

## 5. Summary of Modified Files

For reference, the following files were touched and verified during Milestones 1 and 2:

### Backend:
- `backend/app/core/config.py` — Anchored `DATABASE_URL` to absolute POSIX path, environment resolution.
- `backend/app/services/redmine_service.py` — Paginated membership sync, exact Redmine timestamps, change journals, inactive project archiving.
- `backend/app/api/v1/teams.py` — Project-wise teams endpoint with member lists, roles, and inactive project filtering.
- `backend/app/api/v1/employees.py` — Dynamic `current_projects` mapping and mathematical workload score calculation.
- `backend/app/api/v1/tasks.py` — Serialized Redmine `created_at` and `updated_at` timestamps.
- `backend/app/api/v1/admin_config.py` — Pydantic v2 `ConfigDict` deprecation fix.
- `backend/tests/test_automated_alerts.py` — Foreign-key cascade test cleanup.
- `backend/tests/test_redmine_sync.py` — Membership and timestamp assertions.
- `backend/tests/test_dashboard_notifications.py` — Active projects count assertions.
- `backend/tests/test_m1_empirical_challenge.py` — 4 empirical challenge tests for M1.
- `backend/tests/test_m2_empirical_challenge.py` — 4 empirical challenge tests for M2.
- `backend/tests/test_m2_adversarial_verification.py` — 4 adversarial stress tests for M2.
- `backend/tests/e2e/*` — Complete 57-test 4-tier E2E test suite.
- `backend/run_e2e_tests.py` — Standalone test runner CLI.
- `backend/pytest.ini` — Pytest configuration.

### Frontend:
- `frontend/eslint.config.mjs` — Fixed ESM FlatCompat imports (`.js`).
- `frontend/src/components/views/TeamsView.tsx` — Project-wise member cards with Redmine role badges and empty card elimination.
- `frontend/src/components/views/EmployeesView.tsx` — Status badges, project allocation pills, and visual workload distribution gauge.
- `frontend/src/components/views/TasksView.tsx` — Rendered original Redmine timestamps and robust status filtering.
- `frontend/src/components/views/ProjectsView.tsx` — Diagnostic network/auth error handling with retry trigger.
- `frontend/src/components/TopNav.tsx` — Global "Sync Redmine Now" button with spinner and reactive sync notifications.
- `frontend/src/app/page.tsx` — Connected TopNav sync trigger to reactive `refreshKey` cross-tab refetching.

---

## 6. Architectural Continuity Note for Claude Agents

- **Rule 1**: Maintain database path anchoring. Never introduce relative `sqlite://./` paths.
- **Rule 2**: Never fabricate mock data in production endpoints. All data must originate from `company_intel.db` or live Redmine.
- **Rule 3**: In `TeamsView.tsx` and `EmployeesView.tsx`, always filter inactive projects (`Project.status != "INACTIVE"`) when displaying current delivery teams and calculating active workloads.
- **Rule 4**: In Milestone 3, deliver urgent and critical alerts exclusively to `anil.aiindia@gmail.com` via SMTP, while keeping standard notifications in-app only.
- **Rule 5**: In Milestone 4, AI responses must be strictly grounded in the database context without hallucinating employee allocations or task counts.

*Document compiled and certified by Teamwork Orchestrator.*

---

## 7. Status Update — Milestones 3 & 4 Implemented (Claude, 2026-11-03)

**M3 and M4 are implemented and verified.** Verification: `pytest tests` → 116 passed; `run_e2e_tests.py` → all 4 tiers pass; `npm run lint` → 0 errors / 0 warnings; `npm run build` → clean.

Deviations from the blueprint above (decided with the user):
- **Recipients are a list, not a single address (supersedes Rule 4).** Administration → *Email Recipients* lets anyone be added. Each recipient chooses `ALL` (every notification, same as the notification bar) or `URGENT_CRITICAL`. `anil.aiindia@gmail.com` is seeded as the first recipient with `URGENT_CRITICAL`. The last active recipient cannot be removed/paused. API: `GET/POST /admin/email-recipients`, `PATCH/DELETE /admin/email-recipients/{id}`, `POST /admin/email-recipients/{id}/test`.
- **Google Chat dispatch removed entirely** (CLAUDE.md rule #1 updated accordingly).
- Endpoint names: `/admin/integrations` + `/admin/smtp/test`; the blueprint names `/admin/settings` and `/admin/smtp-test` exist as aliases.
- Category filter also exposes `info`; `GET /notifications/summary` provides pill counts. Extra alert rules: Redmine priority Immediate/Urgent escalation, completed/closed tasks (last 7 days). Repeat alerts per entity+rule are suppressed for 24h even after "mark read".
- AI: questions about an employee's projects / a project's status are answered by deterministic tools with no LLM call; other questions go to OpenRouter with verified facts only (`reasoning: {enabled: false}` — Qwen otherwise leaks its chain-of-thought), falling back to verified figures when the gateway fails.
- **Tests no longer touch the live DB**: `tests/conftest.py` snapshots `company_intel.db` into a per-run copy and replaces SMTP with an in-memory outbox.

Open items:
- SMTP credentials must be added to `backend/.env` (`SMTP_USERNAME`, `SMTP_PASSWORD` = Gmail App Password) for real delivery; until then deliveries record `NOT_CONFIGURED`.
- No Alembic setup exists; the new `alert_email_recipients` table is created by `create_all` at startup.
- Earlier test runs left test notifications in the live DB (pending user decision on cleanup).
