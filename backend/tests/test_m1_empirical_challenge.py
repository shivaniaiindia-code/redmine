import pytest
import httpx
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.redmine_service import redmine_service
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskJournal
from app.models.team import Team, TeamMember
from app.models.employee import Employee
from app.models.redmine_sync import RedmineMapping


@pytest.mark.asyncio
async def test_live_redmine_membership_validation(db_session: AsyncSession):
    """
    Requirement 2: Every project membership in live Redmine is mirrored in the
    database with the same user and role (compared against Redmine's current data).
    """
    headers = {
        "X-Redmine-API-Key": settings.REDMINE_API_KEY,
        "Content-Type": "application/json"
    }

    # Query live Redmine directly for active projects
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"{settings.REDMINE_URL}/projects.json", headers=headers)
        assert resp.status_code == 200, f"Redmine projects request failed: {resp.text}"
        redmine_projects = resp.json().get("projects", [])
        assert len(redmine_projects) >= 2, f"Expected at least 2 active Redmine projects, found {len(redmine_projects)}"

        # Query live Redmine memberships for each project
        expected_memberships = {}
        for rp in redmine_projects:
            pid = rp["id"]
            pname = rp["name"]
            m_resp = await client.get(f"{settings.REDMINE_URL}/projects/{pid}/memberships.json", headers=headers)
            assert m_resp.status_code == 200, f"Redmine memberships failed for {pname}: {m_resp.text}"
            m_data = m_resp.json().get("memberships", [])
            expected_memberships[pname] = [
                {
                    "user_name": m["user"]["name"],
                    "user_id": m["user"]["id"],
                    "roles": [r["name"] for r in m.get("roles", [])]
                }
                for m in m_data
            ]

    # Total expected memberships across active projects
    total_expected = sum(len(mems) for mems in expected_memberships.values())
    assert total_expected > 0, "Live Redmine returned no project memberships"

    # Now verify SQLite database mirrors these exact memberships and roles
    for pname, mems in expected_memberships.items():
        p_res = await db_session.execute(select(Project).where(Project.name == pname))
        proj = p_res.scalars().first()
        assert proj is not None, f"Project '{pname}' missing from SQLite"
        assert proj.status == "ACTIVE", f"Project '{pname}' status is {proj.status}, expected ACTIVE"

        pm_res = await db_session.execute(
            select(ProjectMember).where(ProjectMember.project_id == proj.id)
        )
        db_members = pm_res.scalars().all()
        assert len(db_members) == len(mems), (
            f"Project '{pname}' has {len(db_members)} members in DB, expected {len(mems)}"
        )

        # Check each member's employee record and role
        for expected_m in mems:
            user_name = expected_m["user_name"].strip()
            expected_role = ", ".join(expected_m["roles"])

            # Resolve employee
            matched = False
            for db_pm in db_members:
                emp = (await db_session.execute(
                    select(Employee).where(Employee.id == db_pm.employee_id)
                )).scalars().first()
                full_emp_name = f"{emp.first_name} {emp.last_name}".strip()
                if full_emp_name.lower() == user_name.lower():
                    matched = True
                    assert db_pm.role_in_project == expected_role, (
                        f"Role mismatch for {user_name} in {pname}: "
                        f"DB='{db_pm.role_in_project}', Redmine='{expected_role}'"
                    )
                    break
            assert matched, f"Member '{user_name}' not found in SQLite project_members for project '{pname}'"


@pytest.mark.asyncio
async def test_live_redmine_timestamp_fidelity(db_session: AsyncSession):
    """
    Requirement 3: Query Redmine REST API directly (/issues/91.json, /issues/89.json, /issues/1.json)
    and assert that Task.created_at and Task.updated_at in SQLite match Redmine's
    created_on and updated_on exactly to the second.
    """
    headers = {
        "X-Redmine-API-Key": settings.REDMINE_API_KEY,
        "Content-Type": "application/json"
    }

    issue_ids = [91, 89, 1]

    async with httpx.AsyncClient(timeout=20.0) as client:
        for issue_id in issue_ids:
            resp = await client.get(
                f"{settings.REDMINE_URL}/issues/{issue_id}.json?include=journals",
                headers=headers
            )
            assert resp.status_code == 200, f"Failed to fetch Redmine issue #{issue_id}: {resp.text}"
            issue_data = resp.json().get("issue", {})

            redmine_created_on_str = issue_data.get("created_on")
            redmine_updated_on_str = issue_data.get("updated_on")
            assert redmine_created_on_str is not None, f"Issue #{issue_id} missing created_on in Redmine"
            assert redmine_updated_on_str is not None, f"Issue #{issue_id} missing updated_on in Redmine"

            # Parse Redmine ISO 8601 timestamps
            r_created = datetime.fromisoformat(redmine_created_on_str.replace("Z", "+00:00"))
            r_updated = datetime.fromisoformat(redmine_updated_on_str.replace("Z", "+00:00"))

            # Query Task from SQLite
            task_res = await db_session.execute(
                select(Task).where(Task.title.like(f"#{issue_id}:%"))
            )
            task = task_res.scalars().first()
            assert task is not None, f"Task #{issue_id} not found in SQLite"

            # Normalize SQLite timestamps for second-precision comparison
            db_created = task.created_at
            if db_created.tzinfo is None:
                db_created = db_created.replace(tzinfo=timezone.utc)

            db_updated = task.updated_at
            if db_updated.tzinfo is None:
                db_updated = db_updated.replace(tzinfo=timezone.utc)

            # Assert exact timestamp fidelity (second precision)
            assert db_created.year == r_created.year, f"Year mismatch on Task #{issue_id} created_at"
            assert db_created.month == r_created.month, f"Month mismatch on Task #{issue_id} created_at"
            assert db_created.day == r_created.day, f"Day mismatch on Task #{issue_id} created_at"
            assert db_created.hour == r_created.hour, f"Hour mismatch on Task #{issue_id} created_at"
            assert db_created.minute == r_created.minute, f"Minute mismatch on Task #{issue_id} created_at"
            assert db_created.second == r_created.second, f"Second mismatch on Task #{issue_id} created_at"

            assert db_updated.year == r_updated.year, f"Year mismatch on Task #{issue_id} updated_at"
            assert db_updated.month == r_updated.month, f"Month mismatch on Task #{issue_id} updated_at"
            assert db_updated.day == r_updated.day, f"Day mismatch on Task #{issue_id} updated_at"
            assert db_updated.hour == r_updated.hour, f"Hour mismatch on Task #{issue_id} updated_at"
            assert db_updated.minute == r_updated.minute, f"Minute mismatch on Task #{issue_id} updated_at"
            assert db_updated.second == r_updated.second, f"Second mismatch on Task #{issue_id} updated_at"


@pytest.mark.asyncio
async def test_repeated_live_sync_idempotency_via_api(client: AsyncClient):
    """
    Requirement 1 (API Trigger): Successive sync calls via POST /api/v1/redmine/sync/trigger
    must be completely idempotent and not create duplicate memberships, projects, or tasks.
    Compared against live Redmine as it is today (no fixed counts).
    """
    async def row_counts():
        async with AsyncSessionLocal() as session:
            return {
                "projects": (await session.execute(select(func.count(Project.id)))).scalar(),
                "active_projects": (await session.execute(
                    select(func.count(Project.id)).where(Project.status == "ACTIVE"))).scalar(),
                "tasks": (await session.execute(select(func.count(Task.id)))).scalar(),
                "project_members": (await session.execute(select(func.count(ProjectMember.id)))).scalar(),
                "team_members": (await session.execute(select(func.count(TeamMember.id)))).scalar(),
                "journals": (await session.execute(select(func.count(TaskJournal.id)))).scalar(),
            }

    summaries, counts = [], []
    for _ in range(3):
        resp = await client.post("/api/v1/redmine/sync/trigger")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["summary"]["status"] == "SUCCESS"
        summaries.append({k: data["summary"][k] for k in ("projects_synced", "memberships_synced", "tasks_synced")})
        counts.append(await row_counts())

    assert summaries[0]["projects_synced"] > 0 and summaries[0]["tasks_synced"] > 0
    assert summaries[0] == summaries[1] == summaries[2], f"Sync results changed between runs: {summaries}"
    assert counts[0] == counts[1] == counts[2], f"Repeated syncs changed row counts: {counts}"

    async with AsyncSessionLocal() as session:
        pm_duplicates = (await session.execute(
            select(ProjectMember.project_id, ProjectMember.employee_id, func.count(ProjectMember.id))
            .group_by(ProjectMember.project_id, ProjectMember.employee_id)
            .having(func.count(ProjectMember.id) > 1)
        )).all()
        assert len(pm_duplicates) == 0, f"Duplicate project_members found: {pm_duplicates}"

        tm_duplicates = (await session.execute(
            select(TeamMember.team_id, TeamMember.employee_id, func.count(TeamMember.id))
            .group_by(TeamMember.team_id, TeamMember.employee_id)
            .having(func.count(TeamMember.id) > 1)
        )).all()
        assert len(tm_duplicates) == 0, f"Duplicate team_members found: {tm_duplicates}"

        mapping_duplicates = (await session.execute(
            select(RedmineMapping.entity_type, RedmineMapping.redmine_id, func.count(RedmineMapping.id))
            .group_by(RedmineMapping.entity_type, RedmineMapping.redmine_id)
            .having(func.count(RedmineMapping.id) > 1)
        )).all()
        assert len(mapping_duplicates) == 0, f"Duplicate Redmine mappings found: {mapping_duplicates}"


@pytest.mark.asyncio
async def test_database_url_anchoring_and_split_brain_prevention():
    """
    Verifies that Settings always anchors DATABASE_URL to backend/company_intel.db,
    preventing root/backend split-brain irrespective of execution directory.
    """
    from app.core.config import Settings, DEFAULT_DB_FILE

    # Test default
    s = Settings()
    assert s.DATABASE_URL.endswith("company_intel.db")
    assert str(DEFAULT_DB_FILE) in s.DATABASE_URL or DEFAULT_DB_FILE.as_posix() in s.DATABASE_URL

    # Test relative input override
    s_rel = Settings(DATABASE_URL="sqlite+aiosqlite:///./company_intel.db")
    assert DEFAULT_DB_FILE.as_posix() in s_rel.DATABASE_URL
