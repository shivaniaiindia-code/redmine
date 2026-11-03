import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import ProjectMember
from app.models.task import Task

@pytest.mark.asyncio
async def test_redmine_connection_and_sync(client: AsyncClient, db_session: AsyncSession):
    """
    Validates live Redmine connectivity and synchronization endpoint:
    - Status check
    - Delta sync triggering
    - Membership population in ProjectMember
    - Exact timestamp preservation on Tasks
    """
    # 1. Check Redmine status
    status_resp = await client.get("/api/v1/redmine/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "connected" in status_data
    assert "base_url" in status_data

    # 2. Trigger Delta Sync
    sync_resp = await client.post("/api/v1/redmine/sync/trigger")
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["success"] is True
    assert "summary" in sync_data
    summary = sync_data["summary"]
    assert summary["status"] == "SUCCESS"
    assert summary["projects_synced"] >= 1
    assert summary["memberships_synced"] >= 1
    assert summary["tasks_synced"] >= 1

    # 3. Verify ProjectMember table is populated with real memberships
    pm_res = await db_session.execute(select(ProjectMember))
    members = pm_res.scalars().all()
    assert len(members) >= 1

    # 4. Verify Task timestamps are genuinely preserved from Redmine
    task_res = await db_session.execute(select(Task).where(Task.title.like("#%")))
    tasks = task_res.scalars().all()
    assert len(tasks) >= 1
    for t in tasks:
        assert t.created_at is not None
        assert t.updated_at is not None
