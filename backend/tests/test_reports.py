"""Reports & Analytics: figures must equal independent SQL counts."""
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.project import Project
from app.models.task import Task

DONE = {"DONE", "Resolved", "Closed", "Completed"}


@pytest.mark.asyncio
@pytest.mark.parametrize("include_inactive", [False, True])
async def test_report_kpis_match_database(client: AsyncClient, db_session, include_inactive):
    r = await client.get(f"/api/v1/reports/overview?include_inactive={str(include_inactive).lower()}")
    assert r.status_code == 200
    data = r.json()
    projects = (await db_session.execute(select(Project))).scalars().all()
    if not include_inactive:
        projects = [p for p in projects if p.status != "INACTIVE"]
    pids = {p.id for p in projects}
    tasks = [t for t in (await db_session.execute(select(Task))).scalars().all() if t.project_id in pids]
    today = date.today()
    open_t = [t for t in tasks if t.status not in DONE]
    overdue = [t for t in open_t if t.due_date and t.due_date < today]
    k = data["kpis"]
    assert k["projects"] == len(projects)
    assert k["total_tasks"] == len(tasks)
    assert k["open_tasks"] == len(open_t)
    assert k["overdue_tasks"] == len(overdue)
    assert k["completed_tasks"] == len(tasks) - len(open_t)

    # internal consistency across charts
    assert sum(b["count"] for b in data["overdue_aging"]) == len(overdue)
    assert sum(s["count"] for s in data["task_status"]) == len(tasks)
    assert sum(p["count"] for p in data["priorities"]) == len(open_t)
    assert sum(h["count"] for h in data["project_health"]) == len(projects)
    for row in data["projects"]:
        assert row["completed_tasks"] + row["open_on_time"] + row["overdue_tasks"] == row["total_tasks"]
    assert len(data["weekly_trend"]) == 12 and len(data["alerts_daily"]) == 14
    assert [t["days_overdue"] for t in data["top_overdue"]] == sorted(
        [t["days_overdue"] for t in data["top_overdue"]], reverse=True)


@pytest.mark.asyncio
async def test_report_weeks_param_validated(client: AsyncClient):
    assert (await client.get("/api/v1/reports/overview?weeks=2")).status_code == 422
    assert len((await client.get("/api/v1/reports/overview?weeks=26")).json()["weekly_trend"]) == 26


@pytest.mark.asyncio
async def test_people_ranking_and_availability(client: AsyncClient, db_session):
    from app.models.redmine_sync import RedmineMapping
    data = (await client.get("/api/v1/reports/overview?include_inactive=true&days=30")).json()
    people = data["people"]
    rows = people["employees"]
    redmine_users = {m.internal_id for m in (await db_session.execute(
        select(RedmineMapping).where(RedmineMapping.entity_type == "USER"))).scalars().all()}
    assert all(r["employee_id"] in redmine_users for r in rows)          # login-only accounts excluded
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert [r["score"] for r in rows] == sorted((r["score"] for r in rows), reverse=True)
    for r in rows:
        assert r["score"] == 5 * r["completed_in_period"] + 2 * r["updates_in_period"] + r["open_on_time"]
        assert r["open_on_time"] + r["overdue"] == r["open_tasks"]
        assert len(r["weekly_activity"]) == 8
    assert sum(a["count"] for a in people["availability_counts"]) == len(rows)
    assert sorted(people["free_today"]) == sorted(r["name"] for r in rows if r["open_tasks"] == 0)
    assert data["prev_period_stats"] is not None
    assert (await client.get("/api/v1/reports/overview")).json()["prev_period_stats"] is None   # all time
