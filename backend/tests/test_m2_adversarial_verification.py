import pytest
import httpx
from datetime import datetime
from httpx import AsyncClient
from app.core.config import settings
from app.models.project import Project, ProjectMember
from app.models.employee import Employee
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_adversarial_teams_zero_empty_cards_and_exact_memberships(client: AsyncClient, admin_token: str):
    """
    Empirical Challenge 1:
    Assert GET /api/v1/teams/ returns ZERO empty cards with '0 Members'.
    Assert active delivery teams ('aiinvoice' with 5 members, 'MILIT ANPR' with 3 members)
    are present with exact live Redmine roles.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/teams/", headers=headers)
    assert response.status_code == 200, f"Failed GET /api/v1/teams/: {response.text}"
    teams = response.json()
    assert isinstance(teams, list)

    # 1. Assert ZERO empty cards
    for t in teams:
        members = t.get("members", [])
        members_count = t.get("members_count", 0)
        assert members_count > 0, f"Empty card detected: {t.get('name')} has members_count={members_count}"
        assert len(members) > 0, f"Empty card detected: {t.get('name')} has 0 members in members list"
        assert members_count == len(members), f"Mismatch between members_count ({members_count}) and len(members) ({len(members)}) in team {t.get('name')}"

    # 2. Locate aiinvoice and MILIT ANPR teams
    aiinvoice_team = next((t for t in teams if "aiinvoice" in t.get("project_code", "").lower() or "aiinvoice" in t.get("name", "").lower()), None)
    anpr_team = next((t for t in teams if "milit" in t.get("project_code", "").lower() or "milit" in t.get("name", "").lower()), None)

    assert aiinvoice_team is not None, "aiinvoice team is missing from /api/v1/teams/"
    assert anpr_team is not None, "MILIT ANPR team is missing from /api/v1/teams/"

    # 3. Assert aiinvoice team properties and exact 5 members with roles
    ai_members = aiinvoice_team["members"]
    assert len(ai_members) == 5, f"Expected exactly 5 members in aiinvoice, got {len(ai_members)}: {ai_members}"
    ai_member_map = {m["name"].lower(): m["role"] for m in ai_members}
    
    expected_ai_members = {
        "abhange": "aiinvoice",
        "prajwal abhang": "aiinvoice",
        "ragini thorat": "aiinvoice",
        "shivani patil": "aiinvoice",
        "redmine admin": "aiinvoice"
    }
    for exp_name, exp_role in expected_ai_members.items():
        assert exp_name in ai_member_map, f"Member '{exp_name}' missing from aiinvoice team members: {list(ai_member_map.keys())}"
        assert ai_member_map[exp_name] == exp_role, f"Role mismatch for '{exp_name}': expected '{exp_role}', got '{ai_member_map[exp_name]}'"

    # 4. Assert MILIT ANPR team properties and exact 3 members with roles
    anpr_members = anpr_team["members"]
    assert len(anpr_members) == 3, f"Expected exactly 3 members in MILIT ANPR, got {len(anpr_members)}: {anpr_members}"
    anpr_member_map = {m["name"].lower(): m["role"] for m in anpr_members}

    expected_anpr_members = {
        "abhange": "speech-ASR",
        "harshada kupate": "speech-ASR",
        "shivani patil": "speech-ASR"
    }
    for exp_name, exp_role in expected_anpr_members.items():
        assert exp_name in anpr_member_map, f"Member '{exp_name}' missing from MILIT ANPR team members: {list(anpr_member_map.keys())}"
        assert anpr_member_map[exp_name] == exp_role, f"Role mismatch for '{exp_name}': expected '{exp_role}', got '{anpr_member_map[exp_name]}'"


@pytest.mark.asyncio
async def test_adversarial_employees_no_inactive_projects_in_workload(client: AsyncClient, admin_token: str, db_session):
    """
    Empirical Challenge 2:
    Verify that employee workload scores in /api/v1/employees/ are accurately calculated
    and do NOT include inactive projects.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/employees/", headers=headers)
    assert response.status_code == 200
    employees = response.json()

    # Query all inactive project IDs directly from DB
    from sqlalchemy import select
    inactive_projs_res = await db_session.execute(select(Project.id, Project.name).where(Project.status == "INACTIVE"))
    inactive_project_map = dict(inactive_projs_res.all())

    for emp in employees:
        current_projs = emp.get("current_projects", [])
        emp_pids = [p["id"] for p in current_projs]
        
        # Assert none of the current_projects belong to inactive projects
        for pid in emp_pids:
            assert pid not in inactive_project_map, (
                f"Employee {emp['name']} has inactive project '{inactive_project_map[pid]}' (id={pid}) "
                f"in current_projects! Inactive projects must be excluded."
            )

        # Assert workload score calculation accuracy
        cap = float(emp.get("weekly_capacity_hours") or 40.0)
        alloc = float(emp.get("allocated_hours") or 0.0)
        num_p = len(current_projs)
        if num_p == 0 and alloc == 0.0:
            expected_score = 0.0
        else:
            mult = 1.0 + 0.15 * max(0, num_p - 1)
            expected_score = round((alloc / cap) * mult, 2)
        
        actual_score = emp.get("workload_score")
        assert abs(actual_score - expected_score) <= 0.01, (
            f"Workload calculation mismatch for {emp['name']}: actual={actual_score}, expected={expected_score}"
        )


@pytest.mark.asyncio
async def test_adversarial_tasks_timestamps_match_live_redmine_second_precision(client: AsyncClient, admin_token: str):
    """
    Empirical Challenge 3:
    Verify task timestamps in /api/v1/tasks/ match Redmine's created_on and updated_on.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/tasks/", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0

    # Query live Redmine API
    redmine_headers = {
        "X-Redmine-API-Key": settings.REDMINE_API_KEY,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=20.0) as http_client:
        r_resp = await http_client.get(
            f"{settings.REDMINE_URL}/issues.json?status_id=*",
            headers=redmine_headers
        )
        assert r_resp.status_code == 200
        live_issues = {i["id"]: i for i in r_resp.json().get("issues", [])}

    assert len(live_issues) > 0, "No issues returned from live Redmine"

    # Match each live issue against API tasks
    for issue_id, r_issue in live_issues.items():
        matching = next((t for t in tasks if t["title"].startswith(f"#{issue_id}:")), None)
        assert matching is not None, f"Live issue #{issue_id} not present in /api/v1/tasks/"

        r_c = datetime.fromisoformat(r_issue["created_on"].replace("Z", "+00:00"))
        r_u = datetime.fromisoformat(r_issue["updated_on"].replace("Z", "+00:00"))

        t_c = datetime.fromisoformat(matching["created_at"])
        t_u = datetime.fromisoformat(matching["updated_at"])

        # Timestamp exact second match
        assert (t_c.year, t_c.month, t_c.day, t_c.hour, t_c.minute, t_c.second) == \
               (r_c.year, r_c.month, r_c.day, r_c.hour, r_c.minute, r_c.second), (
            f"created_at timestamp discrepancy for task #{issue_id}: API={t_c}, Redmine={r_c}"
        )
        assert (t_u.year, t_u.month, t_u.day, t_u.hour, t_u.minute, t_u.second) == \
               (r_u.year, r_u.month, r_u.day, r_u.hour, r_u.minute, r_u.second), (
            f"updated_at timestamp discrepancy for task #{issue_id}: API={t_u}, Redmine={r_u}"
        )


@pytest.mark.asyncio
async def test_adversarial_teams_with_simulated_empty_and_inactive_projects(client: AsyncClient, admin_token: str, db_session):
    """
    Empirical Challenge 4:
    Stress-test teams endpoint by inserting simulated edge cases:
    - An ACTIVE project with 0 members (must NOT appear in teams response)
    - An INACTIVE project with members (must NOT appear in teams response)
    - An INACTIVE project with 0 members (must NOT appear in teams response)
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create simulated ACTIVE project with 0 members
    p_active_empty = Project(
        id="proj-sim-act-empty",
        name="Simulated Active Empty Project",
        code="SIM_ACT_EMPTY",
        status="ACTIVE"
    )
    # 2. Create simulated INACTIVE project with 1 member
    p_inactive_with_member = Project(
        id="proj-sim-inact-member",
        name="Simulated Inactive Project With Member",
        code="SIM_INACT_MEM",
        status="INACTIVE"
    )
    # 3. Create simulated INACTIVE project with 0 members
    p_inactive_empty = Project(
        id="proj-sim-inact-empty",
        name="Simulated Inactive Empty Project",
        code="SIM_INACT_EMPTY",
        status="INACTIVE"
    )

    db_session.add_all([p_active_empty, p_inactive_with_member, p_inactive_empty])
    await db_session.commit()

    # Add member to p_inactive_with_member
    pm = ProjectMember(
        id="pm-sim-inact",
        project_id=p_inactive_with_member.id,
        employee_id="emp-sim-test",
        role_in_project="Lead"
    )
    db_session.add(pm)
    await db_session.commit()

    # Query GET /api/v1/teams/
    response = await client.get("/api/v1/teams/", headers=headers)
    assert response.status_code == 200
    teams = response.json()

    returned_team_names = [t["name"] for t in teams]
    returned_pids = [t["project_id"] for t in teams]

    # None of the 3 simulated projects should be present in teams
    assert p_active_empty.id not in returned_pids, (
        f"Active project with 0 members '{p_active_empty.name}' was returned by /api/v1/teams/! Must be excluded."
    )
    assert p_inactive_with_member.id not in returned_pids, (
        f"Inactive project with member '{p_inactive_with_member.name}' was returned by /api/v1/teams/! Must be excluded."
    )
    assert p_inactive_empty.id not in returned_pids, (
        f"Inactive project with 0 members '{p_inactive_empty.name}' was returned by /api/v1/teams/! Must be excluded."
    )
