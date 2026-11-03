# Comprehensive Survey Report: Redmine Synchronization & Backend Architecture

**Explorer**: Explorer 1 (Redmine & Backend Explorer)  
**Target Platform**: Intelligent Projects Manager (Company Intelligence Platform)  
**Date**: 2026-11-03  
**Status**: Investigation Complete  

---

## 1. Executive Summary

This report delivers a thorough architectural, data-model, API, and runtime investigation of the backend system (`backend/`), data stores (`company_intel.db`), live Redmine integration (`https://redmine.aiindia.ai`), and the test suite.

The primary finding is that while live connectivity to Redmine functions and basic project/user/issue upserts succeed, **critical gaps exist in entity mapping, relational association, timestamp preservation, and view-level API schemas**. Specifically:
1. **Database Path Split-Brain**: Two separate SQLite databases exist (`./company_intel.db` in workspace root and `backend/company_intel.db`). Because `.env` configures `DATABASE_URL="sqlite+aiosqlite:///./company_intel.db"` with a relative path, running processes from root vs `backend/` accesses completely different databases with differing data snapshots (mock seed vs synced Redmine).
2. **Teams View Empty State Root Cause**: Redmine project memberships (`/projects/{id}/memberships.json`) are completely bypassed during sync. The platform's `ProjectMember` and `TeamMember` tables have 0 rows. The Teams API serves 5 static dummy teams (`init_db.py`) with 0 members and 0 projects.
3. **Employees View Missing Data**: `api/v1/employees.py` and `EmployeesView.tsx` lack fields and calculations for current project assignments and workload distribution.
4. **Tasks View Missing Timestamps & Status Details**: Original Redmine timestamps (`created_on`, `updated_on`) are discarded during sync and omitted from `api/v1/tasks.py`. Redmine statuses (`New`, `In-Progress`, `Closed`) are partially normalized, and task blockers are hardcoded to `False`.
5. **Notification Engine & Alerting Missing SMTP**: No SMTP client or email dispatch logic exists in `notification_service.py` (only in-app and Google Chat webhook exist). The UI notification modal still contains a custom test dispatch card and lacks urgent/critical/closed category filter tabs.
6. **AI Assistant Grounding Gaps**: `ai_service.py` filters out non-overdue/non-blocked tasks from the prompt context and does not provide employee project assignment mappings, preventing zero-hallucination answers regarding employee assignments.
7. **Test Suite Status**: 9 of 9 backend tests pass in `backend/venv`, but `test_automated_alerts.py` commits test rows (`Test Overdue Critical Deliverable`) directly into the active SQLite database without cleanup.

---

## 2. Codebase Architecture & File Structure (`backend/`)

```
backend/
├── .env                          # Environment config (REDMINE_URL, API_KEY, DATABASE_URL)
├── .env.example
├── company_intel.db              # Active SQLite DB when running from backend/ (425 KB)
├── main.py                       # FastAPI entrypoint, lifespan startup, periodic background worker
├── requirements.txt              # Backend dependencies
├── test_check_live_db.py         # Utility script
├── test_redmine_live.py          # Utility script
├── app/
│   ├── api/
│   │   ├── router.py             # Main API v1 router mounting all sub-routers
│   │   └── v1/
│   │       ├── admin_config.py   # Admin recipient settings (/admin/recipient-config)
│   │       ├── ai.py             # AI chat endpoint (/ai/chat)
│   │       ├── auth.py           # Admin authentication (/auth/login, /auth/me)
│   │       ├── company.py        # Executive dashboard metrics (/company/dashboard)
│   │       ├── employees.py      # Employee roster (/employees/)
│   │       ├── notifications.py  # Notification list, alert trigger, read endpoints
│   │       ├── projects.py       # Projects portfolio list (/projects/)
│   │       ├── redmine.py        # Sync trigger (/redmine/sync/trigger) & status
│   │       ├── tasks.py          # Tasks list (/tasks/) & blocker toggle
│   │       └── teams.py          # Teams list (/teams/)
│   ├── core/
│   │   ├── config.py             # Pydantic BaseSettings
│   │   ├── database.py           # SQLAlchemy 2.0 AsyncEngine & async_sessionmaker
│   │   ├── init_db.py            # Startup table creation and initial admin seed
│   │   ├── permissions.py        # Single-User Admin Mode dependency (CurrentUser)
│   │   └── security.py           # JWT encoding/decoding & bcrypt hashing
│   ├── models/                   # SQLAlchemy 2.0 ORM models
│   │   ├── alert_config.py       # AlertRecipientConfig
│   │   ├── audit.py              # AuditLog
│   │   ├── employee.py           # Employee, Skill, EmployeeSkill
│   │   ├── notification.py       # Notification, NotificationDelivery, NotificationRule
│   │   ├── project.py            # Project, ProjectMember, ProjectMilestone, ProjectRisk, ProjectRACI
│   │   ├── redmine_sync.py       # RedmineSyncState, RedmineMapping
│   │   ├── task.py               # Task, TaskDependency, TimeEntry, HistoricalContribution, TaskJournal
│   │   ├── team.py               # Team, TeamMember
│   │   └── user.py               # User, Role
│   ├── schemas/
│   │   ├── auth.py               # Token & login schemas
│   │   └── company.py            # Pydantic v2 schemas for dashboard KPIs and charts
│   └── services/
│       ├── ai_service.py         # OpenRouter AI Qwen3.5-Flash grounding
│       ├── analytics_service.py  # Dashboard KPI aggregation
│       ├── notification_service.py # In-app notification & alert generation engine
│       └── redmine_service.py    # Redmine REST API client & delta sync engine
├── tests/                        # Pytest automated test suite
│   ├── conftest.py               # Async client & session fixtures
│   ├── test_ai_grounding.py      # AI assistant grounding tests
│   ├── test_auth.py              # Authentication tests
│   ├── test_automated_alerts.py  # Alert generation & deduplication tests
│   ├── test_dashboard_notifications.py # Dashboard metrics & dual-dispatch tests
│   └── test_redmine_sync.py      # Live Redmine sync endpoint tests
└── venv/                         # Python 3.11 virtual environment
```

---

## 3. Data Models & Database Split-Brain Diagnosis

### 3.1 Two SQLite Databases in the Workspace
Inspection revealed two distinct database files:
1. `c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\company_intel.db` (340 KB)
   - Created during early development or when executing commands from root.
   - Contains: 4 mock projects (`PRJ-ANPR`, `PRJ-DOCAI`, `PRJ-INVOCR`), 2 mock tasks, 1 admin employee, 0 Redmine mappings, 0 sync state records.
2. `c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\backend\company_intel.db` (426 KB)
   - Created when uvicorn/python runs inside `backend/`.
   - Contains: 8 projects, 12 tasks (including 3 test tasks), 19 employees, 35 Redmine mappings, 1 sync state record.

**Root Cause**: In `backend/.env`, line 5 sets:
```ini
DATABASE_URL="sqlite+aiosqlite:///./company_intel.db"
```
Because `./company_intel.db` is relative, the file opened depends entirely on the working directory of the process. When running `pytest` or `start_all.ps1` (which does `cd backend`), `backend/company_intel.db` is used. But if any command or server is executed from the repository root, it opens `company_intel.db` in root, presenting stale mock data to the client!

**Alembic Migrations**:
No Alembic migrations exist (`alembic.ini` and `alembic/versions` are absent). Tables are managed solely through `Base.metadata.create_all` in `app/core/init_db.py`.

---

## 4. Live Redmine Synchronization Engine Analysis

### 4.1 Live Redmine Instance Discovery
Using the live credentials (`https://redmine.aiindia.ai` with API key `47cc9f603630e16fcb6f73e99a1111c59d080f18`), direct queries to the Redmine REST API verified:

| Entity | Live Redmine Reality | Platform Database State | Discrepancy / Issue |
|---|---|---|---|
| **Current User** | ID 12: `anil abhange` (admin: True, mail: `anil.aiindia@gmail.com`) | Mapped to Employee ID `b7607ec6...` | Synced correctly |
| **Active Projects** | **2 active projects**: <br>1. ID 1: `aiinvoice` (status: 1)<br>2. ID 27: `MILIT Automatic Number Plate Recognition (ANPR) System` (status: 1) | **8 projects** in `backend/company_intel.db` | Stale projects (e.g. `ansar-photography`, `asset-management`, `blog-generation`, `dmh_whatsapp_outlook`, `paint_defect_detection`, `target-upsc`) remain from prior syncs; sync never purges or archives deleted/inaccessible projects |
| **Project Memberships** | **Project 1 (`aiinvoice`)**: 5 members: <br>- anil abhange (ID 12, role: `aiinvoice`)<br>- prajwal abhang (ID 7, role: `aiinvoice`)<br>- ragini thorat (ID 9, role: `aiinvoice`)<br>- Redmine Admin (ID 1, role: `aiinvoice`)<br>- shivani Patil (ID 22, role: `aiinvoice`)<br><br>**Project 27 (`MILIT ANPR`)**: 3 members:<br>- shivani Patil (ID 22, role: `speech-ASR`)<br>- anil abhange (ID 12, role: `speech-ASR`)<br>- harshada kupate (ID 8, role: `speech-ASR`) | **0 rows in `project_members`**<br>**0 rows in `team_members`** | **CRITICAL DEFECT**: `redmine_service.py` NEVER queries `/projects/{id}/memberships.json`! `ProjectMember` is completely untouched. |
| **Active Issues / Tasks** | **3 active issues**: <br>- #91: `Prepare Hardware, Software Requirements and Project Timeline for MILIT ANPR ` (Status: New, Due: 2026-10-19 [Overdue], Assignee: None)<br>- #89: `Contabo VPS processing issue because of unauthorised process is active` (Status: New, Due: 2026-10-12 [Overdue], Assignee: shivani Patil [ID 22])<br>- #1: `deploy 3.8 Flash model` (Status: New, Due: None, Assignee: shivani Patil [ID 22]) | **12 tasks** in `backend/company_intel.db` (9 synced + 3 test artifacts) | Synced, but original timestamps (`created_on`, `updated_on`) are discarded. `TaskJournal` is never populated. |
| **Users / Employees** | **18 registered users** with active email addresses | **19 employees** (1 admin + 18 synced) | Synced, but employees have no project assignment linkage |
| **Trackers & Statuses** | Trackers: `New Bug`, `New Feature`, `New Task`, `In-Progress`, `Closed`<br>Statuses: `New` (ID 1), `Closed` (ID 2), `In-Progress` (ID 3) | Tasks mapped to 'New', 'In Progress', 'DONE' | Mapped coarsely. Blocked status is hardcoded to `False`. |

### 4.2 In-Depth Code Inspection of `redmine_service.py`

1. **Pagination Defect**:
   Lines 75, 138, 204 hardcode `limit=100` without any `offset` pagination loop:
   ```python
   proj_url = f"{self.base_url}/projects.json?limit=100"
   users_url = f"{self.base_url}/users.json?limit=100"
   issues_url = f"{self.base_url}/issues.json?status_id=*&limit=100&include=journals"
   ```
   If records exceed 100, remaining records are silently omitted.
2. **Missing Memberships Sync**:
   `redmine_service.py` does not contain any call to `/projects/{id}/memberships.json`. `ProjectMember` is not even imported!
3. **Discarded Timestamps**:
   Lines 336-353 populate `due_date` and `start_date`, but do not pass Redmine's `created_on` or `updated_on` to `created_at` or `updated_at`. Default `datetime.now(timezone.utc)` is used.
4. **Watermarking Inefficiency**:
   Lines 380-394 write to `RedmineSyncState` (`last_sync_timestamp`), but lines 204 NEVER read this watermark or pass `updated_on=>={watermark}`. Every sync requests `status_id=*&limit=100`.
5. **Journals History Discarded**:
   Line 204 passes `include=journals`, but `i_data.get("journals")` is never stored into `TaskJournal`. `task_journals` table remains empty (0 rows).

---

## 5. Root-Cause Analysis for Empty / Missing UI Views

### 5.1 Projects View (`ProjectsView.tsx`)
- **API Called**: `GET /api/v1/projects/`
- **Current Behavior**:
  - If backend is not running or root DB is loaded, it shows: *"No projects found. Click 'Sync Redmine Now' to populate."*
  - When connected to `backend/company_intel.db`, it returns 8 projects.
  - However, 6 of these 8 projects are stale/obsolete (no longer present in live Redmine).
  - Health status is updated during `generate_automated_alerts` based on overdue/blocked tasks.

### 5.2 Teams View (`TeamsView.tsx`) — **MAJOR EMPTY STATE**
- **API Called**: `GET /api/v1/teams/`
- **Observed Response**:
  ```json
  [
    {"id": "...", "name": "AI Team", "department": "AI Research", "members_count": 0, "projects_count": 0, "projects": []},
    {"id": "...", "name": "Development", "department": "Engineering", "members_count": 0, "projects_count": 0, "projects": []},
    {"id": "...", "name": "Operations", "department": "Infrastructure", "members_count": 0, "projects_count": 0, "projects": []},
    {"id": "...", "name": "QA Team", "department": "Quality", "members_count": 0, "projects_count": 0, "projects": []},
    {"id": "...", "name": "Research", "department": "R&D", "members_count": 0, "projects_count": 0, "projects": []}
  ]
  ```
- **UI Render**: Every card displays *"0 Members"*, *"0 Projects"*, and *"No assigned projects"*.
- **Root Cause**:
  1. Requirement R1 specifies: *"Teams View: Display project-wise teams based on current Redmine memberships and role allocations."*
  2. `api/v1/teams.py` queries `Team` and `TeamMember`, which were only seeded as 5 dummy organizational departments in `init_db.py`.
  3. Redmine project memberships were never synced into `project_members` or mapped to project-wise delivery teams.
  4. Synced Redmine projects have `Project.primary_team_id = NULL`, so `projects_count` is always 0.

### 5.3 Employees View (`EmployeesView.tsx`) — **MISSING ALLOCATIONS & WORKLOAD**
- **API Called**: `GET /api/v1/employees/`
- **Current Response**:
  Returns `id`, `name`, `email`, `job_title`, `department`, `status`, `weekly_capacity_hours`, `total_tasks`, `overdue_tasks`, `completed_tasks`.
- **Missing Elements**:
  - Does NOT return assigned projects (`current_projects: [...]`).
  - Does NOT return workload distribution (e.g. estimated hours assigned vs weekly capacity).
- **UI Render**: Only displays task counts (total, overdue, done). No project badges, no allocation percentage, no workload visualizations.
- **Root Cause**: `api/v1/employees.py` does not query `ProjectMember` or compute distinct projects from assigned tasks.

### 5.4 Tasks View (`TasksView.tsx`) — **MISSING ORIGINAL TIMESTAMPS**
- **API Called**: `GET /api/v1/tasks/`
- **Current Response**:
  Returns `id`, `title`, `project_id`, `project_name`, `tracker`, `status`, `priority`, `due_date`, `is_overdue`, `is_blocked`, `blocker_reason`, `assigned_to`, `estimated_hours`, `progress_percentage`.
- **Missing Elements**:
  - `created_at` (original Redmine `created_on`) is not returned.
  - `updated_at` (original Redmine `updated_on`) is not returned.
  - In `TasksView.tsx`, the table only has a `Due Date` column; creation date and last updated date are absent.
- **Categorization**:
  Filter tabs exist in `TasksView.tsx` (`ALL`, `OVERDUE`, `BLOCKED`, `IN_PROGRESS`, `COMPLETED`).
  Because all 3 current Redmine tasks are in status `New` (with 2 overdue), `IN_PROGRESS` and `COMPLETED` return 0 items.

### 5.5 Notification Engine & Admin Alerting (`NotificationModal.tsx`, `AdminView.tsx`)
- **Requirement R2 Audit**:
  1. *Deliver all urgent and critical alert notifications exclusively via SMTP email to `anil.aiindia@gmail.com`*:
     - **FAILED / NOT IMPLEMENTED**: `notification_service.py` has NO SMTP sending code. It only has In-App and Google Chat webhook logic.
  2. *Remove legacy dispatch settings and interfaces*:
     - **FAILED / STILL PRESENT**: `NotificationModal.tsx` lines 228-283 still include `+ Dispatch Custom Alert` with inputs for test title, message, severity, and `Dispatch to Bar + Admin Google Chat`.
  3. *Categorize alert messages into urgent, critical, completed/closed with filter tabs/pills*:
     - **FAILED / NOT IMPLEMENTED**: `NotificationModal.tsx` renders all alerts in a single unfilterable list. It lacks tab buttons for Urgent, Critical, and Completed/Closed.

---

## 6. AI Assistant Grounding & Context Extraction Deficiencies

In `backend/app/services/ai_service.py`:
- `get_grounded_context()` gathers:
  - `projects`: `id, name, code, status, health_status, health_reason, progress_percentage`
  - `tasks`: only tasks where `is_overdue` or `is_blocked` are injected into prompt lines 120-121:
    ```python
    - Overdue Tasks: {json.dumps([t for t in context['tasks'] if t['is_overdue']])}
    - Blocked Tasks: {json.dumps([t for t in context['tasks'] if t['is_blocked']])}
    ```
- **Consequence for Requirement R3**:
  - Regular active tasks (e.g. status "In Progress" or "New" with normal due dates) are completely excluded from the AI prompt!
  - Project memberships (which employee belongs to which project) are completely absent.
  - When the user asks: *"What are the current project assignments for shivani Patil?"*, the AI assistant cannot answer or will state that no matching record exists, because `shivani Patil`'s non-overdue task (#1) and project memberships are omitted from the ground-truth payload.

---

## 7. Automated Test Suite (`pytest`) Status

### 7.1 Execution Command & Environment
- Command: `cd backend; $env:PYTHONPATH='.'; .\venv\Scripts\pytest tests -v`
- Python version: 3.11.9
- Pytest version: 9.2.0

### 7.2 Results
```
tests/test_ai_grounding.py::test_ai_grounded_chat PASSED                 [ 11%]
tests/test_auth.py::test_health_check PASSED                             [ 22%]
tests/test_auth.py::test_admin_login_success PASSED                      [ 33%]
tests/test_auth.py::test_admin_login_failure PASSED                      [ 44%]
tests/test_auth.py::test_get_me PASSED                                   [ 55%]
tests/test_automated_alerts.py::test_automated_alert_generation_engine PASSED [ 66%]
tests/test_dashboard_notifications.py::test_company_dashboard_data PASSED [ 77%]
tests/test_dashboard_notifications.py::test_notification_dual_dispatch PASSED [ 88%]
tests/test_redmine_sync.py::test_redmine_connection_and_sync PASSED      [100%]

======================== 9 passed, 1 warning in 15.20s ========================
```

### 7.3 Warning Identified
`app/api/v1/admin_config.py:13`: PydanticDeprecatedSince20: Support for class-based `config` is deprecated. Use `model_config = ConfigDict(...)` instead of `class Config:`.

### 7.4 Test Pollution Discovery
In `tests/test_automated_alerts.py`, line 34 commits a task `title="Test Overdue Critical Deliverable"` directly into the production database. Each test run permanently leaves garbage records in `company_intel.db`. A transactional rollback fixture or separate test SQLite database must be used.

---

## 8. Summary of Actionable Remediation Items

| ID | Component | Remediation Required |
|---|---|---|
| **ACT-1** | `core/config.py` & `.env` | Consolidate database path into an absolute path or fixed location relative to `backend/` to prevent root/backend split-brain. Remove stale mock `company_intel.db` from root. |
| **ACT-2** | `services/redmine_service.py` | 1. Implement `/projects/{id}/memberships.json` fetch for each active project and populate `project_members`.<br>2. Clean up or mark obsolete projects no longer present in Redmine.<br>3. Preserve Redmine's `created_on` and `updated_on` into `Task.created_at` and `Task.updated_at`.<br>4. Parse `include=journals` and populate `task_journals`.<br>5. Support pagination loops for >100 records. |
| **ACT-3** | `api/v1/teams.py` & `TeamsView.tsx` | Redesign `/teams/` to return project-wise teams based on Redmine project memberships (`project_members`), listing team members, their project roles (`aiinvoice`, `speech-ASR`), and associated project metadata. Update `TeamsView.tsx` accordingly. |
| **ACT-4** | `api/v1/employees.py` & `EmployeesView.tsx` | Enrich employee response with `current_projects` (from `project_members` and active assigned tasks) and workload allocation metrics (assigned tasks/hours vs capacity). Update `EmployeesView.tsx` with project pills and capacity visual. |
| **ACT-5** | `api/v1/tasks.py` & `TasksView.tsx` | Expose `created_at` and `updated_at` (original Redmine timestamps) in `api/v1/tasks.py`. Display them in `TasksView.tsx`. |
| **ACT-6** | `services/notification_service.py` | Implement direct SMTP email delivery for all URGENT and CRITICAL alerts to `anil.aiindia@gmail.com`. |
| **ACT-7** | `NotificationModal.tsx` & `AdminView.tsx` | Remove legacy custom dispatch form cards. Add category filter tabs (Urgent, Critical, Completed/Closed) in `NotificationModal.tsx`. |
| **ACT-8** | `services/ai_service.py` | Expand grounded context to include ALL tasks, project memberships, and employee project allocations so AI answers questions about employee project assignments deterministically. |
| **ACT-9** | `backend/tests/` | Fix test database pollution by isolating test sessions, and update Pydantic v2 `ConfigDict` in `admin_config.py`. |
