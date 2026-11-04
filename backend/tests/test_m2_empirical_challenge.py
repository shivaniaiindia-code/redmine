import pytest
import httpx
from datetime import datetime, timezone
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_challenge_teams_active_members_and_roles_fidelity(client: AsyncClient, admin_token: str):
    """
    Milestone 2 Challenge:
    Verify project-wise teams are returned, members list matches the 8 live Redmine memberships,
    and roles ('aiinvoice', 'speech-ASR') are present.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/teams/", headers=headers)
    assert response.status_code == 200, f"Teams API returned status {response.status_code}: {response.text}"
    teams = response.json()
    assert isinstance(teams, list), "Expected teams response to be a list"

    # Find the active delivery teams corresponding to live Redmine projects
    aiinvoice_team = next((t for t in teams if "aiinvoice" in t.get("project_code", "").lower() or "aiinvoice" in t.get("name", "").lower()), None)
    anpr_team = next((t for t in teams if "milit" in t.get("project_code", "").lower() or "milit" in t.get("name", "").lower()), None)

    assert aiinvoice_team is not None, "aiinvoice team missing from /api/v1/teams/"
    assert anpr_team is not None, "MILIT ANPR team missing from /api/v1/teams/"

    # Check aiinvoice members (5 members in live Redmine)
    ai_members = aiinvoice_team.get("members", [])
    assert len(ai_members) == 5, f"Expected 5 members in aiinvoice team, got {len(ai_members)}"
    ai_roles = {m["role"] for m in ai_members}
    assert "aiinvoice" in ai_roles, f"Role 'aiinvoice' missing from aiinvoice team roles: {ai_roles}"

    # Check MILIT ANPR members (3 members in live Redmine)
    anpr_members = anpr_team.get("members", [])
    assert len(anpr_members) == 3, f"Expected 3 members in MILIT ANPR team, got {len(anpr_members)}"
    anpr_roles = {m["role"] for m in anpr_members}
    assert "speech-ASR" in anpr_roles, f"Role 'speech-ASR' missing from MILIT ANPR team roles: {anpr_roles}"

    # Verify key employees are members of these teams
    ai_member_names = {m["name"].lower() for m in ai_members}
    anpr_member_names = {m["name"].lower() for m in anpr_members}
    assert "anil abhange" in ai_member_names, "anil abhange missing from aiinvoice team"
    assert "anil abhange" in anpr_member_names, "anil abhange missing from MILIT ANPR team"
    assert "shivani patil" in ai_member_names, "shivani patil missing from aiinvoice team"
    assert "shivani patil" in anpr_member_names, "shivani patil missing from MILIT ANPR team"


@pytest.mark.asyncio
async def test_challenge_teams_no_empty_cards(client: AsyncClient, admin_token: str):
    """
    Milestone 2 Challenge:
    Explicit check: Verify no '0 Members' empty cards are returned by GET /api/v1/teams/.
    If inactive/stale projects with 0 members are included in the response,
    the UI renders empty cards displaying '0 Members'.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/teams/", headers=headers)
    assert response.status_code == 200
    teams = response.json()

    empty_cards = [
        t for t in teams
        if t.get("members_count") == 0 or len(t.get("members", [])) == 0
    ]

    empty_desc = [f"{t.get('name')} (Status: {t.get('status')})" for t in empty_cards]
    assert len(empty_cards) == 0, (
        f"Found {len(empty_cards)} empty team card(s) with '0 Members': {empty_desc}. "
        f"GET /api/v1/teams/ must filter out inactive/empty projects to prevent rendering empty cards."
    )


@pytest.mark.asyncio
async def test_challenge_employees_workload_formula_and_project_allocations(client: AsyncClient, admin_token: str):
    """
    Milestone 2 Challenge:
    Verify employees assigned to projects (e.g. anil abhange, shivani Patil) have
    current_projects populated, allocated hours, and accurate workload scores matching:
      Workload Score = (Allocated Hours / Weekly Capacity) * (1 + 0.15 * (Active Projects - 1))
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/employees/", headers=headers)
    assert response.status_code == 200, f"Employees API returned {response.status_code}: {response.text}"
    employees = response.json()
    assert isinstance(employees, list), "Expected employees response to be a list"

    emp_by_name = {e["name"].lower(): e for e in employees}

    # 1. Check anil abhange
    assert "anil abhange" in emp_by_name, "anil abhange missing from employee roster"
    anil = emp_by_name["anil abhange"]
    assert len(anil["current_projects"]) >= 2, f"Expected anil abhange to have at least 2 projects, got {len(anil['current_projects'])}"
    anil_proj_names = [p["name"].lower() for p in anil["current_projects"]]
    assert any("aiinvoice" in n for n in anil_proj_names), "aiinvoice missing from anil abhange projects"
    assert any("milit" in n for n in anil_proj_names), "MILIT ANPR missing from anil abhange projects"
    assert anil["allocated_hours"] > 0, f"Expected allocated hours for anil abhange, got {anil['allocated_hours']}"
    # Formula: (allocated / capacity) * (1 + 0.15 * (projects - 1))
    expected_anil_score = round((anil["allocated_hours"] / anil["weekly_capacity_hours"])
                                * (1 + 0.15 * (len(anil["current_projects"]) - 1)), 2)
    assert anil["workload_score"] == expected_anil_score, (
        f"Workload score mismatch for anil abhange: expected {expected_anil_score}, got {anil['workload_score']}"
    )

    # 2. Check shivani patil
    assert "shivani patil" in emp_by_name, "shivani patil missing from employee roster"
    shivani = emp_by_name["shivani patil"]
    assert len(shivani["current_projects"]) >= 2, f"Expected shivani patil to have at least 2 projects, got {len(shivani['current_projects'])}"
    assert shivani["allocated_hours"] > 0
    expected_shivani_score = round((shivani["allocated_hours"] / shivani["weekly_capacity_hours"])
                                   * (1 + 0.15 * (len(shivani["current_projects"]) - 1)), 2)
    assert shivani["workload_score"] == expected_shivani_score, (
        f"Workload score mismatch for shivani patil: expected {expected_shivani_score}, got {shivani['workload_score']}"
    )

    # 3. Check harshada kupate (single project member)
    assert "harshada kupate" in emp_by_name, "harshada kupate missing from employee roster"
    harshada = emp_by_name["harshada kupate"]
    assert len(harshada["current_projects"]) >= 1
    expected_harshada = round((harshada["allocated_hours"] / harshada["weekly_capacity_hours"])
                              * (1 + 0.15 * (len(harshada["current_projects"]) - 1)), 2)
    assert abs(harshada["workload_score"] - expected_harshada) <= 0.01, (
        f"Expected {expected_harshada} for harshada, got {harshada['workload_score']}")

    # 4. Stress-test workload score formula across ALL employees
    for emp in employees:
        cap = float(emp["weekly_capacity_hours"] or 40.0)
        alloc = float(emp["allocated_hours"] or 0.0)
        num_p = len(emp.get("current_projects", []))
        if num_p == 0 and alloc == 0.0:
            expected_score = 0.0
        else:
            mult = 1.0 + 0.15 * max(0, num_p - 1)
            expected_score = round((alloc / cap) * mult, 2)
        assert abs(emp["workload_score"] - expected_score) <= 0.01, (
            f"Formula mismatch for {emp['name']}: got {emp['workload_score']}, expected {expected_score}"
        )


@pytest.mark.asyncio
async def test_challenge_tasks_timestamps_presence_and_live_redmine_fidelity(client: AsyncClient, admin_token: str):
    """
    Milestone 2 Challenge:
    Query GET /api/v1/tasks/: Verify created_at and updated_at are present on all tasks
    and match Redmine timestamps to second precision.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await client.get("/api/v1/tasks/", headers=headers)
    assert response.status_code == 200, f"Tasks API returned {response.status_code}: {response.text}"
    tasks = response.json()
    assert isinstance(tasks, list), "Expected tasks response to be a list"
    assert len(tasks) > 0, "No tasks returned by /api/v1/tasks/"

    # 1. Assert all tasks have created_at and updated_at
    for t in tasks:
        assert t.get("created_at") is not None, f"Task {t['id']} missing 'created_at'"
        assert t.get("updated_at") is not None, f"Task {t['id']} missing 'updated_at'"
        # Verify valid ISO format
        datetime.fromisoformat(t["created_at"])
        datetime.fromisoformat(t["updated_at"])

    # 2. Query live Redmine issues and verify timestamp fidelity
    redmine_headers = {
        "X-Redmine-API-Key": settings.REDMINE_API_KEY,
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=20.0) as http_client:
        r_resp = await http_client.get(
            f"{settings.REDMINE_URL}/issues.json?status_id=*",
            headers=redmine_headers
        )
        assert r_resp.status_code == 200, f"Failed to fetch live Redmine issues: {r_resp.text}"
        live_issues = {i["id"]: i for i in r_resp.json().get("issues", [])}

    # Verify each live issue has a corresponding task with matching timestamps
    for issue_id, r_issue in live_issues.items():
        matching_task = next((t for t in tasks if t["title"].startswith(f"#{issue_id}:")), None)
        assert matching_task is not None, f"Live Redmine issue #{issue_id} not found in /api/v1/tasks/"

        r_c_str = r_issue.get("created_on")
        r_u_str = r_issue.get("updated_on")
        assert r_c_str is not None, f"Live issue #{issue_id} missing created_on in Redmine"
        assert r_u_str is not None, f"Live issue #{issue_id} missing updated_on in Redmine"

        r_c = datetime.fromisoformat(r_c_str.replace("Z", "+00:00"))
        r_u = datetime.fromisoformat(r_u_str.replace("Z", "+00:00"))

        t_c = datetime.fromisoformat(matching_task["created_at"])
        t_u = datetime.fromisoformat(matching_task["updated_at"])

        # Assert second-precision fidelity
        assert (t_c.year, t_c.month, t_c.day, t_c.hour, t_c.minute, t_c.second) == \
               (r_c.year, r_c.month, r_c.day, r_c.hour, r_c.minute, r_c.second), (
            f"created_at mismatch for task #{issue_id}: API={matching_task['created_at']}, Redmine={r_c_str}"
        )

        assert (t_u.year, t_u.month, t_u.day, t_u.hour, t_u.minute, t_u.second) == \
               (r_u.year, r_u.month, r_u.day, r_u.hour, r_u.minute, r_u.second), (
            f"updated_at mismatch for task #{issue_id}: API={matching_task['updated_at']}, Redmine={r_u_str}"
        )
