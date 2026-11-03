# Handoff Report: Redmine & Backend Exploration

**Agent**: Explorer 1 (`teamwork_explorer_survey_1`)  
**Parent Orchestrator ID**: `797d74c2-a70d-48f3-87bb-02fd6b60d98d`  
**Date**: 2026-11-03  
**Status**: Hard Handoff (Investigation Complete)  

---

## 1. Observation

### Obs 1: Database File Split-Brain
- Direct SQLite query on `company_intel.db` (workspace root):
  - 4 mock projects (`PRJ-ANPR`, `PRJ-DOCAI`, `PRJ-INVOCR`), 2 tasks, 1 employee, 0 `redmine_mappings`, 0 `redmine_sync_state`.
- Direct SQLite query on `backend/company_intel.db`:
  - 8 projects (`aiinvoice`, `milit-automatic-number-plate-recognition-anpr-system`, plus 6 older projects), 12 tasks, 19 employees, 35 `redmine_mappings`, 1 `redmine_sync_state` record.
- In `backend/.env`, Line 5:
  ```ini
  DATABASE_URL="sqlite+aiosqlite:///./company_intel.db"
  ```
  Relative path `./company_intel.db` binds to whatever folder python/uvicorn is launched from.

### Obs 2: Live Redmine State via REST API
Using API key `47cc9f603630e16fcb6f73e99a1111c59d080f18` against `https://redmine.aiindia.ai`:
- `GET /users/current.json`: User ID 12 (`anil abhange`, admin: True, mail: `anil.aiindia@gmail.com`).
- `GET /projects.json?status=1`: Exactly 2 active projects:
  - ID 1: `aiinvoice` (Identifier: `aiinvoice`)
  - ID 27: `MILIT Automatic Number Plate Recognition (ANPR) System` (Identifier: `milit-automatic-number-plate-recognition-anpr-system`)
- `GET /projects/1/memberships.json`: 5 members:
  - anil abhange (ID 12, Role: `aiinvoice`)
  - prajwal abhang (ID 7, Role: `aiinvoice`)
  - ragini thorat (ID 9, Role: `aiinvoice`)
  - Redmine Admin (ID 1, Role: `aiinvoice`)
  - shivani Patil (ID 22, Role: `aiinvoice`)
- `GET /projects/27/memberships.json`: 3 members:
  - shivani Patil (ID 22, Role: `speech-ASR`)
  - anil abhange (ID 12, Role: `speech-ASR`)
  - harshada kupate (ID 8, Role: `speech-ASR`)
- `GET /issues.json?status_id=*&limit=100`: Exactly 3 issues:
  - #91: `Prepare Hardware, Software Requirements and Project Timeline for MILIT ANPR ` (Status: 'New', Created: 2026-10-20T07:39:40Z, Updated: 2026-10-20T08:52:56Z, Due: 2026-10-19 [Overdue], Assignee: None)
  - #89: `Contabo VPS processing issue because of unauthorised process is active` (Status: 'New', Created: 2026-10-20T07:12:24Z, Updated: 2026-10-20T07:12:24Z, Due: 2026-10-12 [Overdue], Assignee: shivani Patil [ID 22])
  - #1: `deploy 3.8 Flash model` (Status: 'New', Created: 2026-10-02T09:49:16Z, Updated: 2026-10-20T07:09:18Z, Due: None, Assignee: shivani Patil [ID 22])
- `GET /users.json?limit=100`: 18 users.

### Obs 3: Sync Engine Deficiencies in `backend/app/services/redmine_service.py`
- Lines 7-10:
  ```python
  from app.models.project import Project
  from app.models.task import Task
  from app.models.employee import Employee
  from app.models.redmine_sync import RedmineSyncState, RedmineMapping
  ```
  `ProjectMember` is not imported and never queried or populated.
- In `backend/company_intel.db`, table `project_members` has count: `0`.
- In `backend/company_intel.db`, table `team_members` has count: `0`.
- Lines 336-353: When creating `Task`, `created_at` and `updated_at` default to `datetime.now(timezone.utc)`. The Redmine values `created_on` and `updated_on` are ignored.
- Lines 204: `issues_url = f"{self.base_url}/issues.json?status_id=*&limit=100&include=journals"`. The journals array `i_data.get("journals")` is never stored; `task_journals` in DB has 0 rows.
- Lines 380-394: Watermark is written to `RedmineSyncState`, but line 204 never reads or filters with `updated_on=>={watermark}`.

### Obs 4: Teams View Root Cause (`backend/app/api/v1/teams.py` & `frontend/src/components/views/TeamsView.tsx`)
- In `api/v1/teams.py` lines 16-25:
  Queries `select(Team)` and `select(TeamMember).where(TeamMember.team_id == team.id)` and `select(Project).where(Project.primary_team_id == team.id)`.
  The only teams in DB are 5 mock departments from `init_db.py`. Members count is 0, projects count is 0.
- `TeamsView.tsx` displays "0 Members", "0 Projects", "No assigned projects".

### Obs 5: Employees View Missing Allocations (`backend/app/api/v1/employees.py` & `frontend/src/components/views/EmployeesView.tsx`)
- `api/v1/employees.py` lines 28-39: returns only `id, name, email, job_title, department, status, weekly_capacity_hours, total_tasks, overdue_tasks, completed_tasks`.
- No project assignment list or capacity allocation is returned.
- `EmployeesView.tsx` has no project assignment badges or workload distribution indicators.

### Obs 6: Tasks View Missing Timestamps (`backend/app/api/v1/tasks.py` & `frontend/src/components/views/TasksView.tsx`)
- `api/v1/tasks.py` lines 50-65: returns `id, title, project_id, project_name, tracker, status, priority, due_date, is_overdue, is_blocked, blocker_reason, assigned_to, estimated_hours, progress_percentage`.
- Does not return `created_at` or `updated_at`.
- `TasksView.tsx` only renders `due_date`.

### Obs 7: Notification Engine Missing SMTP & Filter Tabs
- In `backend/app/services/notification_service.py` lines 62-95:
  Only two channels exist: `IN_APP` and `GOOGLE_CHAT_ADMIN`. No SMTP code (`smtplib` or `aiosmtplib`) exists.
- In `frontend/src/components/NotificationModal.tsx` lines 228-283:
  Custom test alert dispatch form (`+ Dispatch Custom Alert`) is still present.
  No category filter tabs exist for Urgent, Critical, and Completed/Closed.

### Obs 8: AI Assistant Context Omission (`backend/app/services/ai_service.py`)
- Lines 120-121:
  Only overdue tasks and blocked tasks are passed into the prompt:
  ```python
  - Overdue Tasks: {json.dumps([t for t in context['tasks'] if t['is_overdue']])}
  - Blocked Tasks: {json.dumps([t for t in context['tasks'] if t['is_blocked']])}
  ```
  All normal active tasks and employee project memberships are absent from context.

### Obs 9: Pytest Suite Execution
- Running `cd backend; $env:PYTHONPATH='.'; .\venv\Scripts\pytest tests -v` produced:
  `9 passed, 1 warning in 15.20s`.
- In `tests/test_automated_alerts.py` line 33-35, a task titled `Test Overdue Critical Deliverable` is committed to `company_intel.db` without rollback, polluting the production DB.

---

## 2. Logic Chain

1. **Premise 1 (from Obs 1)**: Because `DATABASE_URL="sqlite+aiosqlite:///./company_intel.db"` uses a relative path, running processes from root loads the un-synced root `company_intel.db` (containing mock data: PRJ-ANPR, PRJ-DOCAI, PRJ-INVOCR), causing the UI to show mock/empty data unless explicitly launched from `backend/`.
2. **Premise 2 (from Obs 2 & Obs 3)**: Live Redmine has 2 active projects (`aiinvoice` with 5 members, `MILIT ANPR` with 3 members). However, `redmine_service.py` does not fetch `/projects/{id}/memberships.json` or populate `ProjectMember` or project teams.
3. **Premise 3 (from Obs 4)**: Because project memberships are never synced and `Project.primary_team_id` is never set, `api/v1/teams.py` queries empty `team_members` for the 5 static mock teams, causing `TeamsView.tsx` to render "0 Members" and "No assigned projects".
4. **Premise 4 (from Obs 5)**: Because `api/v1/employees.py` does not compute or return assigned projects from tasks or memberships, `EmployeesView.tsx` cannot render current project assignments or workload distribution.
5. **Premise 5 (from Obs 2, Obs 3, Obs 6)**: Because Redmine's `created_on` and `updated_on` are discarded in `redmine_service.py` and omitted from `api/v1/tasks.py`, `TasksView.tsx` cannot display the actual Redmine timestamps required by R1.
6. **Premise 6 (from Obs 7)**: Because `notification_service.py` has no SMTP implementation, urgent and critical alerts cannot be delivered to `anil.aiindia@gmail.com` via email as required by R2.
7. **Premise 7 (from Obs 8)**: Because `ai_service.py` omits non-overdue tasks and project memberships from the LLM prompt, the AI Assistant cannot answer queries regarding employee project assignments deterministically as required by R3.

---

## 3. Caveats

1. **Redmine Archive/Delete Policy**: Live Redmine currently returns 2 projects (`aiinvoice` and `MILIT ANPR`), while `backend/company_intel.db` contains 8 projects from previous syncs. The sync engine must be updated to decide whether non-returned projects should be archived (status="ON_HOLD") or soft-deleted.
2. **SMTP Credentials**: While `settings.DEFAULT_ALERT_EMAIL="anil.aiindia@gmail.com"` is defined in `.env`, SMTP host, port, username, and password credentials need to be configured in `.env` (or mock SMTP for testing) to enable live email delivery.
3. **No Alembic Migration History**: There are no existing Alembic version files. Schema updates should be applied cleanly either via `init_db.py` or by initializing Alembic.

---

## 4. Conclusion

The platform is functionally very close to production readiness, but requires 8 targeted implementation steps:
1. **Consolidate SQLite Path**: Fix `DATABASE_URL` in `config.py` and `.env` to resolve the root/backend split-brain. Remove root `company_intel.db`.
2. **Implement Project Memberships Sync**: In `redmine_service.py`, fetch `/projects/{id}/memberships.json` for each active project and populate `project_members` with roles.
3. **Re-architect Teams API & View**: In `api/v1/teams.py` and `TeamsView.tsx`, group and render project-wise teams based on Redmine project memberships.
4. **Enrich Employees API & View**: Return assigned projects and workload capacity percentages in `api/v1/employees.py` and display them in `EmployeesView.tsx`.
5. **Capture & Display Original Timestamps**: Save Redmine `created_on` and `updated_on` in `redmine_service.py`, expose them in `api/v1/tasks.py`, and display them in `TasksView.tsx`.
6. **Implement SMTP Alerting**: Add an asynchronous SMTP delivery channel in `notification_service.py` for URGENT and CRITICAL alerts routing to `anil.aiindia@gmail.com`.
7. **Clean Notification UI**: Remove the legacy test dispatch card from `NotificationModal.tsx` and add Urgent, Critical, Completed/Closed filter pills.
8. **Enrich AI Assistant Context**: Inject full task lists and employee-project assignments into `ai_service.py` to ensure grounded zero-hallucination responses.

---

## 5. Verification Method

To independently verify these findings, run the following commands in PowerShell from the project root:

1. **Verify Live Redmine Projects & Memberships**:
   ```powershell
   python -c "import urllib.request, json; h={'User-Agent':'Mozilla/5.0','X-Redmine-API-Key':'47cc9f603630e16fcb6f73e99a1111c59d080f18'}; r=urllib.request.urlopen(urllib.request.Request('https://redmine.aiindia.ai/projects.json', headers=h)); print(json.loads(r.read().decode('utf-8')))"
   ```
2. **Verify Database Split-Brain**:
   ```powershell
   python -c "import sqlite3; print('Root DB projects:', sqlite3.connect('company_intel.db').cursor().execute('SELECT count(*) FROM projects').fetchone()[0]); print('Backend DB projects:', sqlite3.connect('backend/company_intel.db').cursor().execute('SELECT count(*) FROM projects').fetchone()[0])"
   ```
3. **Verify Zero Rows in `project_members`**:
   ```powershell
   python -c "import sqlite3; print('Project members:', sqlite3.connect('backend/company_intel.db').cursor().execute('SELECT count(*) FROM project_members').fetchone()[0])"
   ```
4. **Run Backend Test Suite**:
   ```powershell
   cd backend; $env:PYTHONPATH='.'; .\venv\Scripts\pytest tests -v
   ```
5. **Inspect Survey Report**:
   Inspect `c:\Users\Anil Abhange\Downloads\intelligent_projects_manager\.agents\teamwork\teamwork_explorer_survey_1\survey_report.md`.
