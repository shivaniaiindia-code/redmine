# Comprehensive Survey Report: Notifications, AI Assistant & Administration (R2, R3, R4)

**Surveyor**: Explorer 3 (Notifications, AI & Admin Explorer)  
**Date**: 2026-11-03  
**Status**: Investigation Complete  
**Target Codebase**: `intelligent_projects_manager` (FastAPI backend + Next.js 14 App Router frontend)  

---

## 1. Executive Summary

This survey report provides a forensic investigation of **Requirement 2 (Notification Engine & SMTP Alerting)**, **Requirement 3 (AI Assistant Integration)**, and **Requirement 4 (Administration & Integration)** as mandated by the authoritative user request in `ORIGINAL_REQUEST.md`.

Key findings across the three requirements:
1. **R2 (Notifications & Alerting)**:
   - The backend notification dispatcher currently routes only to `IN_APP` and `GOOGLE_CHAT_ADMIN`. **SMTP email dispatch is completely absent from backend code**.
   - In the frontend `NotificationModal.tsx`, a legacy custom dispatch form ("+ Dispatch Custom Alert") exists and must be removed.
   - In `AdminView.tsx`, legacy Google Chat dual-dispatch settings and channel toggles exist and should be streamlined into a dedicated SMTP configuration card.
   - Category filtering tabs (`All`, `Critical`, `Urgent`, `Completed / Closed`) are missing in `NotificationModal.tsx` and need to be implemented.
   - Urgent and critical alerts must be delivered exclusively to `anil.aiindia@gmail.com` via SMTP with full delivery tracking.
2. **R3 (AI Assistant Integration)**:
   - Model `qwen/qwen3.5-flash-02-23` is already configured in `.env` and `config.py`.
   - However, `ai_service.py` currently omits **employee project assignments** and **live non-overdue/non-blocked tasks** from the grounding context. If management asks about an employee's current project assignments, the assistant cannot answer accurately. A deterministic calculation and enriched context pipeline is required to guarantee zero hallucination.
   - RBAC is checked at the HTTP route level but not passed into `ai_service`.
3. **R4 (Administration & Integration)**:
   - Admin settings only support `alert_recipient_config` and lack dedicated SMTP configuration endpoints and test-email triggers.
   - Relative database path `sqlite+aiosqlite:///./company_intel.db` causes split-brain database behavior when commands run from root vs `backend/`. This path must be normalized.

---

## 2. Requirement 2: Notification Engine & Alerting

### 2.1 Existing Backend Architecture

The existing notification engine is implemented across four primary files:
- **`backend/app/models/notification.py`**:
  - `Notification`: Stores `id`, `recipient_id`, `title`, `message`, `severity` (`INFO`, `WARNING`, `URGENT`, `CRITICAL`), `entity_type` (`TASK`, `PROJECT`, `TEAM`, `EMPLOYEE`, `SYSTEM`), `entity_id`, `is_read`, `created_at`.
  - `NotificationDelivery`: Tracks per-channel dispatch status: `id`, `notification_id`, `channel` (`IN_APP`, `GOOGLE_CHAT_ADMIN`), `destination`, `status` (`PENDING`, `SENT`, `FAILED`, `PENDING_WEBHOOK`), `attempt_count`, `response_payload`, `error_message`, `delivered_at`.
  - `NotificationRule`: Pre-configured event rules (`TASK_OVERDUE`, `TASK_BLOCKED`, etc.).
  - `GoogleChatSpace`: Legacy space webhook table.
- **`backend/app/models/alert_config.py`**:
  - `AlertRecipientConfig`: Stores `recipient_email` (default: `anil.aiindia@gmail.com`), `recipient_name`, `google_chat_webhook_url`, and channel toggles (`in_app_enabled`, `google_chat_enabled`, `email_enabled`).
- **`backend/app/services/notification_service.py`**:
  - `create_and_dispatch` (lines 28–97): Creates a notification and creates `NotificationDelivery` for `IN_APP` and `GOOGLE_CHAT_ADMIN`. **Does not send SMTP email**.
  - `generate_automated_alerts` (lines 103–261): Scans active tasks and projects:
    - Overdue tasks (< today): `CRITICAL` (>= 3 days) or `URGENT` (< 3 days).
    - Blocked tasks (`is_blocked = True`): `CRITICAL`.
    - Deadlines approaching (<= 2 days): `WARNING`.
    - Project health changes: `BLOCKED` (CRITICAL), `AT_RISK` (URGENT).
    - Excludes completed/closed tasks (`~Task.status.in_(["Resolved", "Closed", "DONE", "Completed"])`).
- **`backend/app/api/v1/notifications.py`**:
  - `GET /api/v1/notifications/`: Lists recent notifications with delivery statuses.
  - `POST /api/v1/notifications/generate-alerts`: Triggers the automated alert scan.
  - `POST /api/v1/notifications/trigger`: Dispatches manual notification.
  - `PATCH /api/v1/notifications/{id}/read` & `POST /read-all`: Mark read endpoints.

### 2.2 Legacy Dispatch Settings & Interfaces to Remove

The following legacy dispatch cards and UI elements must be eliminated:

| Location | Lines | Element / Code | Issue & Removal Action |
|---|---|---|---|
| `frontend/src/components/NotificationModal.tsx` | Line 62 | `const [showTestForm, setShowTestForm] = useState(false);` | Remove state variable |
| `frontend/src/components/NotificationModal.tsx` | Lines 96–130 | `handleTriggerTest` function | Remove manual dispatch trigger handler |
| `frontend/src/components/NotificationModal.tsx` | Lines 228–234 | `{showTestForm ? "Hide Test Dispatch" : "+ Dispatch Custom Alert"}` | Remove "+ Dispatch Custom Alert" button from action bar |
| `frontend/src/components/NotificationModal.tsx` | Lines 245–283 | `showTestForm && (<div className="p-4 bg-indigo-50/50 ...">...</div>)` | Completely remove the collapsible custom dispatch card |
| `frontend/src/components/views/AdminView.tsx` | Lines 250–266 | `Google Chat Webhook URL (External Mirroring Channel)` input | Remove or replace with SMTP settings |
| `frontend/src/components/views/AdminView.tsx` | Lines 269–307 | `Dispatch Channels (Separately Tracked)` toggles | Remove legacy channel toggles |
| `frontend/src/components/views/AdminView.tsx` | Lines 447–476 | Card 4: `Admin Google Chat Mirroring` card | Replace with dedicated **SMTP Email Alerting** card |
| `frontend/src/components/NotificationsFeed.tsx` | Lines 91–100 | `1:1 Admin Google Chat Mirroring Active ✓` footer | Streamline footer |
| `frontend/src/components/TopNav.tsx` | Line 54 | `title="System Notification Bar (Mirrored to Admin Google Chat)"` | Streamline title |

### 2.3 Categorizing Alert Messages by Redmine Categories

Redmine operational data contains the following statuses and priorities:
- **Statuses**: `New`, `In Progress`, `Feedback`, `Resolved`, `Closed` (mapped to `DONE`).
- **Priorities**: `Low`, `Normal`, `High`, `Urgent`, `Immediate`.
- **Blockers & Deadlines**: `is_blocked`, `blocker_reason`, `is_overdue`, `due_date`.

Alert categorization mapping:
1. **Critical Alerts (`CRITICAL`)**:
   - Tasks with active blockers (`is_blocked = True`).
   - Tasks overdue by 3 or more days.
   - Tasks with priority `Immediate`.
   - Projects with health status `BLOCKED`.
2. **Urgent Alerts (`URGENT`)**:
   - Tasks overdue by 1–2 days.
   - Tasks with priority `Urgent` or approaching deadline (within 48 hours).
   - Projects with health status `AT_RISK`.
3. **Completed / Closed State Alerts (`COMPLETED`)**:
   - Tasks transitioning to `Resolved`, `Closed`, or `DONE`.
   - Projects with status `COMPLETED` or achieved milestones.
   - Alert notifications associated with closed tasks or resolution notices.

#### UI Filter Tabs / Pills Implementation in `NotificationModal.tsx`
Add a filter pill bar above the alerts list with 4 states:
- `All` pill (showing total count)
- `Critical` pill (`bg-red-100 text-red-700 border-red-200`)
- `Urgent` pill (`bg-amber-100 text-amber-800 border-amber-200`)
- `Completed / Closed` pill (`bg-emerald-100 text-emerald-800 border-emerald-200`)

When a user clicks a pill, only alerts matching that category are rendered.

### 2.4 Exclusive SMTP Email Delivery to `anil.aiindia@gmail.com`

Requirement: **"Deliver all urgent and critical alert notifications exclusively via SMTP email to `anil.aiindia@gmail.com`."**

#### Backend SMTP Service Architecture
Create `backend/app/services/email_service.py` (or integrate into `notification_service.py`):
1. **Configuration**:
   - Add the following to `Settings` (`backend/app/core/config.py`):
     ```python
     SMTP_HOST: str = "smtp.gmail.com"
     SMTP_PORT: int = 587
     SMTP_USERNAME: str = ""
     SMTP_PASSWORD: str = ""
     SMTP_USE_TLS: bool = True
     SMTP_USE_SSL: bool = False
     SMTP_FROM_EMAIL: str = "notifications@companyintel.ai"
     SMTP_FROM_NAME: str = "Company Intelligence Platform"
     DEFAULT_ALERT_EMAIL: str = "anil.aiindia@gmail.com"
     ```
2. **Dispatch Filter Invariant**:
   - In `create_and_dispatch`:
     ```python
     if severity in ["URGENT", "CRITICAL"]:
         await NotificationService._dispatch_smtp_email(db, notification, recipient_email)
     ```
   - Standard `INFO` and `WARNING` notifications are recorded in-app only and **do not trigger SMTP emails**.
3. **Delivery Tracking**:
   - For every urgent/critical alert, create a `NotificationDelivery` record:
     - `channel = "EMAIL_SMTP"`
     - `destination = "anil.aiindia@gmail.com"`
     - `status = "SENT"` on success, `"FAILED"` on exception.
     - `delivered_at = datetime.now(timezone.utc)`
     - `error_message` records the failure traceback if offline/unconfigured.
4. **HTML Email Template**:
   - Header with severity badge (Red for `CRITICAL`, Orange for `URGENT`).
   - Title, full message body, entity type, entity ID, and timestamp.
   - Action button linking directly to the task or project.
   - Footer clearly addressed to Administrator Anil Abhange (`anil.aiindia@gmail.com`).

---

## 3. Requirement 3: AI Assistant Integration

### 3.1 OpenRouter Gateway Configuration

- **Active Model**: `qwen/qwen3.5-flash-02-23`
- **Fallback Model**: `qwen/qwen3.8-flash`
- **Gateway Endpoint**: `https://openrouter.ai/api/v1/chat/completions`
- **API Key**: Verified present in `backend/.env` (`sk-or-v1-95fe...`)
- **Latency & Temperature**: Fast response time with `temperature=0.2` for deterministic synthesis.

### 3.2 Grounding & Zero Hallucination Audit

In `backend/app/services/ai_service.py`:
- Currently, `AIService.get_grounded_context` (lines 18–100) extracts:
  1. `projects`: `id`, `name`, `code`, `status`, `health_status`, `health_reason`, `progress_percentage`.
  2. `tasks`: All tasks, BUT in `system_instruction` (lines 120–121) it only injects:
     - `Overdue Tasks`: `[t for t in context['tasks'] if t['is_overdue']]`
     - `Blocked Tasks`: `[t for t in context['tasks'] if t['is_blocked']]`
  3. `employees`: `emp_list = [{"id": e.id, "name": ..., "email": ..., "department": ..., "job_title": ...}]`
  4. `active_alerts`: Recent unread notifications.

#### Critical Gaps Identified
1. **Missing Employee Project Assignments**:
   - The prompt provides no mapping between employees and projects.
   - `project_members` table is never queried.
   - The tasks assigned to an employee that are *not* overdue or blocked are completely omitted from the prompt.
   - Consequently, when an administrator asks: *"What projects is Anil assigned to?"* or *"Who is working on the ANPR System?"*, the model cannot see the assignment records and will report that no record exists.
2. **Missing Live Project Detail Context**:
   - The context does not aggregate total tasks, in-progress tasks, completed tasks, and assigned team members per project.
3. **No Role-Based Context Filtering**:
   - `POST /api/v1/ai/chat` requires authentication (`current_user`), but does not forward `current_user` to `ai_service.answer_management_query`.

#### Grounding & Tool Retrieval Solution
Enrich `ai_service.py` with deterministic database aggregations:
1. **`employee_assignments`**:
   - For every employee, deterministically compute:
     - Assigned project names and codes (from `ProjectMember` and assigned `Task` records).
     - Count of active tasks assigned, overdue tasks count, and allocated weekly hours.
2. **`live_project_statuses`**:
   - For every project: Status (`ACTIVE`, `PLANNING`, `COMPLETED`), Health Status (`ON_TRACK`, `AT_RISK`, `BLOCKED`), Health Reason, Total Tasks, Overdue Tasks Count, Blocked Tasks Count, and Assignee names.
3. **Deterministic Helper Queries**:
   - `get_employee_assignments(employee_name_or_id)`
   - `get_projects_health(status_filter)`
   - `get_operational_blockers(project_id)`
4. **Structured Verified Citations**:
   - Conclude every response with verified links:
     - `[Project: <name> (#<code\>)](/projects/<id>)`
     - `[Employee: <name>](/employees/<id>)`
     - `[Task: #<id> <title>](/tasks/<id>)`

---

## 4. Requirement 4: Administration & Integration

### 4.1 Administration Settings Page & Endpoints

#### Existing Endpoints in `backend/app/api/v1/admin_config.py`
- `GET /api/v1/admin/recipient-config`
- `PUT /api/v1/admin/recipient-config`
- Currently only updates `AlertRecipientConfig` fields.

#### Endpoints Needed for Complete Administration
1. `GET /api/v1/admin/settings`:
   - Comprehensive status endpoint returning:
     - Redmine API status (`connected`, `base_url`, `last_synced_at`).
     - OpenRouter AI status (`model`, `gateway_reachable`).
     - SMTP Email Alerting status (`host`, `port`, `from_email`, `recipient_email`, `configured`).
2. `PUT /api/v1/admin/smtp-config`:
   - Updates SMTP host, port, username, password, TLS/SSL, and sender email.
3. `POST /api/v1/admin/smtp-test`:
   - Triggers an immediate test email to `anil.aiindia@gmail.com` to verify SMTP credentials and server connectivity.

#### Frontend `AdminView.tsx` Modernization
Replace the current layout with a cohesive 4-card management view:
- **Card 1: Redmine Integration Engine** (`https://redmine.aiindia.ai`, status badge, last sync timestamp, "Trigger Redmine Sync Now" button).
- **Card 2: SMTP Email Alerting Engine** (Recipient: `anil.aiindia@gmail.com`, SMTP server, port, TLS status, "Send Test Alert Email" button).
- **Card 3: OpenRouter AI Gateway** (Model: `qwen/qwen3.5-flash-02-23`, deterministic grounding status, zero-hallucination verification badge).
- **Card 4: Automated Alert Generation Engine** (Overdue & blocker scanner, deduplication badge, "Scan & Generate Alerts Now" button).

### 4.2 System Resilience & Path Resolution

1. **SQLite Database Relative Path Split-Brain**:
   - `backend/app/core/config.py`: `DATABASE_URL: str = "sqlite+aiosqlite:///./company_intel.db"`.
   - When commands or dev servers run from project root, SQLite creates a database at `intelligent_projects_manager/company_intel.db`.
   - When running from `backend/`, SQLite looks at `backend/company_intel.db`.
   - In fact, `backend/company_intel.db` (425 KB) contains all synchronized Redmine projects, while the root database was partially unmigrated.
   - **Fix**: Anchor the default database path to the backend directory using absolute path resolution:
     ```python
     BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
     DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'company_intel.db')}"
     ```
2. **SMTP Fault Tolerance**:
   - If SMTP server is unreachable or credentials invalid, the dispatcher catches the exception, records status `FAILED` in `notification_deliveries`, logs a warning, and returns a successful HTTP response so that in-app notification creation is never interrupted.
3. **OpenRouter Fault Tolerance**:
   - If OpenRouter API is rate-limited or times out, the assistant catches the exception and returns a formatted local database snapshot summary without crashing the UI.

---

## 5. Architectural Verification & Quality Gates

### 5.1 Backend Test Suite (`pytest`)
- All 9 backend tests pass cleanly when run against `backend/company_intel.db`:
  - `test_ai_grounded_chat` PASSED
  - `test_health_check` PASSED
  - `test_admin_login_success` PASSED
  - `test_admin_login_failure` PASSED
  - `test_get_me` PASSED
  - `test_automated_alert_generation_engine` PASSED
  - `test_company_dashboard_data` PASSED
  - `test_notification_dual_dispatch` PASSED
  - `test_redmine_sync_connection_and_sync` PASSED

### 5.2 Frontend Build (`next build`)
- Next.js 15.1.7 compiles with zero type errors and zero build errors:
  - `Route (app) /`: 17.8 kB (Static prerendered)
  - `Route (app) /_not-found`: 979 B

---

## 6. Actionable Implementation Checklist

### For Requirement 2 (Notifications & Alerting)
- [ ] Add SMTP configuration options to `backend/app/core/config.py` and `.env`.
- [ ] Create `EmailService` (using standard `smtplib` + `email.mime` in `asyncio.to_thread`).
- [ ] Update `NotificationService.create_and_dispatch` to send SMTP email to `anil.aiindia@gmail.com` when severity is `CRITICAL` or `URGENT`.
- [ ] Record `EMAIL_SMTP` channel delivery in `notification_deliveries`.
- [ ] Remove `showTestForm`, `handleTriggerTest`, and custom test alert form from `NotificationModal.tsx`.
- [ ] Implement category filter pills (`All`, `Critical`, `Urgent`, `Completed / Closed`) in `NotificationModal.tsx`.
- [ ] Add support for completed/closed task/project alerts.

### For Requirement 3 (AI Assistant)
- [ ] Enrich `ai_service.get_grounded_context` with:
  - Employee project assignments (mapping employees to project names, roles, and task counts).
  - Complete live project status details (active, overdue, blocked, total tasks).
  - All assigned tasks per employee.
- [ ] Verify OpenRouter model `qwen/qwen3.5-flash-02-23` answers questions like:
  - *"What are the current project assignments for employee X?"*
  - *"What is the live status of project Y?"*
- [ ] Ensure responses include verified citations.

### For Requirement 4 (Administration & Integration)
- [ ] Anchor `DATABASE_URL` in `config.py` to absolute path to prevent split-brain DB issues.
- [ ] Add `PUT /api/v1/admin/smtp-config` and `POST /api/v1/admin/smtp-test` in `admin_config.py`.
- [ ] Update `AdminView.tsx` with modern 4-card layout including dedicated SMTP Email Alerting card with live test button.
- [ ] Remove legacy Google Chat webhook inputs and toggles from `AdminView.tsx`.
