# Milestone M1 Handoff Report: Redmine Sync & Backend Core

**Worker**: Worker M1 (Redmine Sync Backend Worker)  
**Milestone**: M1 - Redmine Sync & Backend Data Engine  
**Date**: 2026-11-03  
**Status**: COMPLETE  

---

## 1. Observation

### 1.1 Database Split-Brain
- Relative path in `backend/app/core/config.py` line 16 was: `DATABASE_URL: str = "sqlite+aiosqlite:///./company_intel.db"`.
- When processes executed from the workspace root, SQLite opened `./company_intel.db` (root mock DB with 4 mock projects). When executed from `backend/`, it opened `backend/company_intel.db` (8 projects).
- Direct SQLite query confirmed:
  - `intelligent_projects_manager/company_intel.db`: `[('employees', 1), ('projects', 4), ('project_members', 0), ('tasks', 3)]`
  - `backend/company_intel.db`: `[('employees', 19), ('projects', 8), ('project_members', 0), ('tasks', 14)]`

### 1.2 Redmine Memberships & Timestamps Gap in `redmine_service.py`
- In `backend/app/services/redmine_service.py`, `ProjectMember` and `TaskJournal` were not imported or populated.
- Table `project_members` had 0 rows.
- Table `task_journals` had 0 rows.
- In `redmine_service.py` lines 336-353, tasks were instantiated without passing Redmine's `created_on` or `updated_on` strings to `Task.created_at` or `Task.updated_at`. Default `datetime.now(timezone.utc)` was used.
- Lines 75, 138, 204 hardcoded `limit=100` with no offset pagination loops.
- Live Redmine query against `https://redmine.aiindia.ai` returned 2 active projects:
  - Project 1 (`aiinvoice`) with 5 members (`anil abhange`, `prajwal abhang`, `ragini thorat`, `Redmine Admin`, `shivani Patil`) with role `aiinvoice`.
  - Project 27 (`MILIT Automatic Number Plate Recognition (ANPR) System`) with 3 members (`shivani Patil`, `anil abhange`, `harshada kupate`) with role `speech-ASR`.
- Live Redmine query returned 3 active issues: #1, #89, #91. Issues #1 and #91 had change journals recorded in Redmine.

### 1.3 Deprecation Warning & Test Pollution
- In `backend/app/api/v1/admin_config.py` line 13:
  `PydanticDeprecatedSince20: Support for class-based config is deprecated, use ConfigDict instead.`
- In `backend/tests/test_automated_alerts.py`, line 25 created `Task(title="Test Overdue Critical Deliverable")` and committed it without deletion at test end. Direct query revealed 6 leftover test tasks and 6 test notifications accumulated in `backend/company_intel.db`.

---

## 2. Logic Chain

1. **Anchoring Database URL** (Ref: Observation 1.1):
   - By calculating `BACKEND_DIR = Path(__file__).resolve().parent.parent.parent` in `backend/app/core/config.py`, `DEFAULT_DB_FILE` is always anchored to `backend/company_intel.db`.
   - Adding a Pydantic `@field_validator("DATABASE_URL", mode="after")` normalizes any relative SQLite URL to `sqlite+aiosqlite:///{DEFAULT_DB_FILE.as_posix()}`.
   - Setting `model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"))` ensures `.env` is loaded reliably regardless of the working directory.
   - Renaming `intelligent_projects_manager/company_intel.db` to `company_intel.db.stale_mock_backup` prevents any lingering references.

2. **Memberships & Delivery Teams Sync** (Ref: Observation 1.2):
   - Added generic pagination helper `_fetch_paginated(client, endpoint, key, params)` using `limit=100` and `offset` loops until `offset >= total_count`.
   - For every active project returned by Redmine, `/projects/{id}/memberships.json` is paginated.
   - For each membership, the user ID is resolved to an internal `Employee.id` (creating an `Employee` record if new).
   - Roles (`aiinvoice`, `speech-ASR`, `Manager`, `Developer`) are extracted and upserted into `ProjectMember(project_id, employee_id, role_in_project)`.
   - A delivery `Team(name=f"{project.name} Team")` is created/verified, `project.primary_team_id` is updated, and members are registered as `TeamMember`, ensuring `/teams/` and `/projects/` report genuine, non-zero membership and project counts.

3. **Exact Redmine Timestamps & Journals** (Ref: Observation 1.2):
   - Added `_parse_iso_datetime` handling ISO 8601 strings with timezone normalization.
   - Redmine's `created_on` and `updated_on` are parsed and explicitly assigned to `Task.created_at` and `Task.updated_at`.
   - If `i_data.get("journals")` is omitted by Redmine's list endpoint, `_fetch_paginated` / detail fetch calls `GET /issues/{id}.json?include=journals`.
   - Changes and author are mapped into `TaskJournal(task_id, author_id, notes, changes, created_at)` and mapped via `RedmineMapping(entity_type="JOURNAL")`.
   - Projects in SQLite not present in Redmine's active project list are marked `Project.status = "INACTIVE"` and `Project.health_reason = "Archived (no longer active in Redmine)"`.

4. **Code Quality & Test Hygiene** (Ref: Observation 1.3):
   - In `backend/app/api/v1/admin_config.py`, replaced `class Config: from_attributes = True` with `model_config = ConfigDict(from_attributes=True)`.
   - Cleaned up accumulated test tasks from `backend/company_intel.db`.
   - In `backend/tests/test_automated_alerts.py`, wrapped alert tests in a `try ... finally` block that deletes `overdue_task` and its generated notifications, ensuring 0 test artifacts remain.
   - In `backend/tests/test_redmine_sync.py`, added assertions for `memberships_synced >= 1`, `ProjectMember` table population, and `Task.created_at` / `Task.updated_at` fidelity.
   - In `backend/tests/test_dashboard_notifications.py`, updated `assert data["project_status"]["total_projects"] >= 2` to reflect genuine active Redmine projects.

---

## 3. Caveats

- Live Redmine instance currently contains 2 active projects (`aiinvoice` and `MILIT ANPR`) and 3 open issues (#1, #89, #91). If new projects or tasks are created in Redmine, `sync_all` will dynamically fetch and index them.
- SQLite naively stores datetimes without microsecond timezone offsets; `_parse_iso_datetime` normalizes UTC offsets properly before saving.
- The 6 historical projects in SQLite no longer present in Redmine (`ansar-photography`, `asset-management`, `blog-generation`, `dmh_whatsapp_outlook`, `paint_defect_detection`, `target-upsc`) have their status set to `INACTIVE` to prevent alerting noise while maintaining referential integrity.

---

## 4. Conclusion

All milestone M1 requirements have been genuinely implemented and validated against the live Redmine server (`https://redmine.aiindia.ai`) and backend database:
- Absolute database path resolution eliminates split-brain across directories.
- Project memberships sync populates `project_members`, delivery `Team`, and `TeamMember` entities.
- Redmine original creation and update timestamps and change journals are fully preserved.
- Offset pagination prevents dropping records when counts exceed 100.
- Zero test pollution is achieved via deterministic cleanup fixtures.
- 100% of the backend test suite (66 tests) passes with 0 warnings and 0 errors.

---

## 5. Verification Method

### 5.1 Verification Commands Run
```powershell
# 1. Verify database anchoring from root
$env:PYTHONPATH="backend"; .\backend\venv\Scripts\python -c 'from app.core.config import settings; print("Anchored URL:", settings.DATABASE_URL)'

# 2. Trigger live sync against Redmine
cd backend; .\venv\Scripts\python -c '
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.redmine_service import redmine_service
async def test():
    async with AsyncSessionLocal() as db:
        summary = await redmine_service.sync_all(db)
        print("Live Sync Summary:", summary)
asyncio.run(test())
'

# 3. Verify SQLite Tables State
cd backend; .\venv\Scripts\python -c '
import sqlite3
conn = sqlite3.connect("company_intel.db")
pm_count = conn.execute("SELECT count(*) FROM project_members").fetchone()[0]
tj_count = conn.execute("SELECT count(*) FROM task_journals").fetchone()[0]
tasks = conn.execute("SELECT title, created_at, updated_at FROM tasks WHERE title LIKE \"#%\"").fetchall()
print(f"project_members count: {pm_count}")
print(f"task_journals count: {tj_count}")
for t in tasks:
    print("Task:", t[0], "| created_at:", t[1], "| updated_at:", t[2])
conn.close()
'

# 4. Run Full Backend Test Suite
cd backend; .\venv\Scripts\python -m pytest tests -v
```

### 5.2 Verification Output Summary
1. `Anchored URL: sqlite+aiosqlite:///C:/Users/Anil Abhange/Downloads/intelligent_projects_manager/backend/company_intel.db`
2. `Live Sync Summary: {'projects_synced': 2, 'memberships_synced': 8, 'employees_synced': 0, 'tasks_synced': 3, 'journals_synced': 3, 'alerts_generated': 0, 'status': 'SUCCESS', 'synced_at': '...'}`
3. `project_members count: 8`, `task_journals count: 3`, tasks `#91`, `#89`, `#1` exact Redmine timestamps verified:
   - `#91`: `created_at: 2026-10-20 07:39:40.000000`, `updated_at: 2026-10-20 08:52:56.000000`
   - `#89`: `created_at: 2026-10-20 07:12:24.000000`, `updated_at: 2026-10-20 07:12:24.000000`
   - `#1`: `created_at: 2026-10-02 09:49:16.000000`, `updated_at: 2026-10-20 07:09:18.000000`
4. Pytest result: `======================== 66 passed in 77.46s (0:01:17) ========================` (0 failed, 0 warnings).

### 5.3 Invalidation Conditions
- If `backend/company_intel.db` is moved or deleted.
- If Redmine server is unreachable or API key `47cc9f603630e16fcb6f73e99a1111c59d080f18` is revoked.

