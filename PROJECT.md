# Project: Intelligent Projects Manager Production-Ready Readiness

## Architecture
- **Backend**: FastAPI (Python 3.12 / 3.11), SQLAlchemy 2.0 async, SQLite database anchored at `backend/company_intel.db`. Single-User Admin Mode with JWT authentication.
- **Frontend**: Next.js 15.1.7 App Router, React 19, Tailwind CSS, Lucide icons. Modular view-switching dashboard architecture (`src/app/page.tsx` + `src/components/views/*`).
- **External Integrations**:
  - Live Redmine REST API (`https://redmine.aiindia.ai`, API key: `d1dff27e7aa00ff795adb4bc24ac8a6005046a75`).
  - OpenRouter AI Gateway (Model: `qwen/qwen3.5-flash-02-23`).
  - SMTP Email Alerting Server (Destination: `anil.aiindia@gmail.com`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | DB Path Resolution | Consolidate SQLite DB to absolute path `backend/company_intel.db` to eliminate root/backend split-brain | M1 | Survey |
| 2 | Redmine Memberships Sync | Fetch `/projects/{id}/memberships.json` to populate `project_members` with project IDs, employee IDs, and Redmine roles | M1 | Survey |
| 3 | Redmine Timestamps & Journals | Preserve original Redmine `created_on` and `updated_on` timestamps in `Task.created_at` / `Task.updated_at` and store journals | M1 | Survey |
| 4 | Sync Pagination & Cleanup | Implement offset pagination loops and mark/archive stale projects no longer present in Redmine | M1 | Survey |
| 5 | Teams View & Project-Wise API | Update `api/v1/teams.py` and `TeamsView.tsx` to group and render team members project-wise based on Redmine memberships and roles | M2 | Survey |
| 6 | Employees View Allocations & Workload | Update `api/v1/employees.py` and `EmployeesView.tsx` with status badges, current project assignments, and visual workload distribution gauge | M2 | Survey |
| 7 | Tasks View Timestamps & Statuses | Expose original Redmine timestamps in `api/v1/tasks.py` and render in `TasksView.tsx` with full status categorization | M2 | Survey |
| 8 | Global Sync Trigger & Empty State Guard | Add global "Sync Redmine Now" trigger, cross-tab cache refresh, and distinct error reporting in `ProjectsView.tsx` | M2 | Survey |
| 9 | Frontend Lint & API URL Config | Fix `eslint.config.mjs` ESM imports (`.js`) and centralize API URL via `NEXT_PUBLIC_API_URL` | M2 | Survey |
| 10 | SMTP Email Alerting Service | Implement backend SMTP client delivering all `CRITICAL` and `URGENT` alerts exclusively to `anil.aiindia@gmail.com` with `EMAIL_SMTP` tracking | M3 | Survey |
| 11 | Notification UI Streamlining | Add category filter pills (`All`, `Critical`, `Urgent`, `Completed / Closed`) and remove legacy custom dispatch cards in `NotificationModal.tsx` and `AdminView.tsx` | M3 | Survey |
| 12 | AI Assistant Grounding | Enrich `ai_service.py` with all active tasks, project memberships, and employee assignments for deterministic zero-hallucination answers | M4 | Survey |
| 13 | Administration Settings & Cards | Add dedicated admin settings endpoints (`/admin/settings`, `/admin/smtp-config`, `/admin/smtp-test`) and modernize `AdminView.tsx` into a 4-card management view | M4 | Survey |
| 14 | E2E Test Suite & Hardening | Pass 100% of E2E test suite (Tiers 1-4) and adversarial coverage hardening (Tier 5) | M5 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Live Redmine Sync & Backend Data Engine | Features 1, 2, 3, 4: Absolute DB path, memberships sync, original timestamps, pagination, and backend test hygiene | none | DONE |
| M2 | Primary Dashboard Views & Data Visibility | Features 5, 6, 7, 8, 9: Project-wise Teams view, Employee 360 allocations & workload gauge, Tasks view timestamps, global sync trigger, lint fix | M1 | DONE |
| M3 | Notification Engine & SMTP Email Alerting | Features 10, 11: SMTP email service for urgent/critical to `anil.aiindia@gmail.com`, notification category filter tabs, remove legacy dispatch forms | M1 | PLANNED |
| M4 | AI Assistant & Administration Configuration | Features 12, 13: Grounded AI assistant for employee project assignments and live project statuses, admin settings API and 4-card management view | M1, M2, M3 | PLANNED |
| M5 | E2E Verification & Hardening | Feature 14: Full test suite verification (pytest, npm run build/lint, live sync validation) | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### Redmine Sync ↔ Backend Models
- `ProjectMember`: `id` (UUID), `project_id` (UUID), `employee_id` (UUID), `role` (str, e.g. "aiinvoice", "speech-ASR"), `created_at` (datetime).
- `Task`: `created_at` (datetime, from Redmine `created_on`), `updated_at` (datetime, from Redmine `updated_on`), `is_blocked` (bool), `status` (str).

### Backend APIs ↔ Frontend Views
- `GET /api/v1/teams/`: Returns list of project-wise teams:
  ```json
  [
    {
      "project_id": "...",
      "project_name": "MILIT Automatic Number Plate Recognition (ANPR) System",
      "project_code": "PRJ-MILIT",
      "status": "ACTIVE",
      "members_count": 3,
      "members": [
        {"employee_id": "...", "name": "shivani Patil", "email": "...", "role": "speech-ASR"},
        {"employee_id": "...", "name": "anil abhange", "email": "anil.aiindia@gmail.com", "role": "speech-ASR"},
        {"employee_id": "...", "name": "harshada kupate", "email": "...", "role": "speech-ASR"}
      ]
    }
  ]
  ```
- `GET /api/v1/employees/`: Returns list of employees with current project assignments and workload metrics:
  ```json
  [
    {
      "id": "...",
      "name": "shivani Patil",
      "email": "...",
      "department": "Engineering",
      "job_title": "Developer",
      "status": "ACTIVE",
      "weekly_capacity_hours": 40,
      "total_tasks": 5,
      "overdue_tasks": 1,
      "completed_tasks": 2,
      "current_projects": [{"id": "...", "name": "MILIT ANPR", "code": "PRJ-MILIT", "role": "speech-ASR"}],
      "allocated_hours": 35.0,
      "workload_score": 0.88
    }
  ]
  ```
- `GET /api/v1/tasks/`: Returns list of tasks including original Redmine timestamps:
  ```json
  [
    {
      "id": "...",
      "title": "Prepare Hardware, Software Requirements...",
      "project_name": "MILIT Automatic Number Plate Recognition (ANPR) System",
      "status": "New",
      "priority": "Normal",
      "due_date": "2026-10-19",
      "created_at": "2026-10-05T10:15:00Z",
      "updated_at": "2026-10-19T08:30:00Z",
      "is_overdue": true,
      "is_blocked": false,
      "assigned_to": null
    }
  ]
  ```
- `POST /api/v1/notifications/generate-alerts`: Triggers automated scan. Urgent/Critical alerts deliver SMTP email to `anil.aiindia@gmail.com`.
- `GET /api/v1/notifications/`: Supports query param `category=all|critical|urgent|completed`.
- `POST /api/v1/ai/chat`: Answers employee assignment and project status queries deterministically with zero hallucination.

## Code Layout
- Backend: `backend/app/`
  - `api/v1/`: `projects.py`, `teams.py`, `employees.py`, `tasks.py`, `notifications.py`, `admin_config.py`, `ai.py`, `redmine.py`
  - `services/`: `redmine_service.py`, `notification_service.py`, `email_service.py`, `ai_service.py`, `analytics_service.py`
  - `models/`: `project.py`, `employee.py`, `task.py`, `team.py`, `notification.py`, `alert_config.py`
  - `core/`: `config.py`, `database.py`, `permissions.py`, `security.py`, `init_db.py`
- Frontend: `frontend/src/`
  - `components/views/`: `ProjectsView.tsx`, `TeamsView.tsx`, `EmployeesView.tsx`, `TasksView.tsx`, `AdminView.tsx`
  - `components/`: `NotificationModal.tsx`, `NotificationsFeed.tsx`, `TopNav.tsx`, `AIAssistantDrawer.tsx`
