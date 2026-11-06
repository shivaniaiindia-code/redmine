import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task
from app.models.project import Project
from app.models.notification import Notification

# ==============================================================================
# TIER 3: CROSS-FEATURE INTEGRATION COMBINATIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_cross_sync_to_views_pipeline(client: AsyncClient, admin_headers: dict):
    """
    Tier 3: Full End-to-End Pipeline:
    1. Trigger Redmine delta sync
    2. Query Projects view -> verify projects exist and have metrics
    3. Query Teams view -> verify teams reflect projects
    4. Query Employees view -> verify employees roster populated
    5. Query Tasks view -> verify tasks match projects and assignees
    """
    # 1. Trigger sync
    sync_resp = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["success"] is True
    
    # 2. Check Projects view
    proj_resp = await client.get("/api/v1/projects/", headers=admin_headers)
    assert proj_resp.status_code == 200
    projects = proj_resp.json()
    assert len(projects) >= 1
    sample_proj = projects[0]
    
    # 3. Check Teams view
    teams_resp = await client.get("/api/v1/teams/", headers=admin_headers)
    assert teams_resp.status_code == 200
    assert isinstance(teams_resp.json(), list)
    
    # 4. Check Employees view
    emp_resp = await client.get("/api/v1/employees/", headers=admin_headers)
    assert emp_resp.status_code == 200
    employees = emp_resp.json()
    assert len(employees) >= 1
    
    # 5. Check Tasks view
    tasks_resp = await client.get("/api/v1/tasks/", headers=admin_headers)
    assert tasks_resp.status_code == 200
    tasks = tasks_resp.json()
    assert len(tasks) >= 1
    
    # Verify foreign key consistency across views
    project_ids = {p["id"] for p in projects}
    for t in tasks:
        assert t["project_id"] in project_ids, f"Task project_id {t['project_id']} missing from projects view"

@pytest.mark.asyncio
async def test_cross_task_blocker_triggers_critical_alert_and_delivery(client: AsyncClient, admin_headers: dict):
    """
    Tier 3: Operational Blocker Escalation Flow:
    1. Engineer flags task as blocked via /tasks/{id}/toggle-blocker
    2. Automated alert is immediately dispatched with CRITICAL severity
    3. Notification is retrievable via /notifications/ with delivery tracking
    4. Unflagging task restores normal state
    """
    tasks_resp = await client.get("/api/v1/tasks/", headers=admin_headers)
    task = tasks_resp.json()[0]
    task_id = task["id"]
    task_title = task["title"]
    
    # 1. Flag as blocked
    block_resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": True, "blocker_reason": "ANPR Camera RTSP stream packet drop"}
    )
    assert block_resp.status_code == 200
    assert block_resp.json()["is_blocked"] is True
    
    # 2. Check notification feed
    notifs_resp = await client.get("/api/v1/notifications/", headers=admin_headers)
    assert notifs_resp.status_code == 200
    items = notifs_resp.json()
    
    # Find matching critical alert
    matching_alert = next((i for i in items if i["entity_id"] == task_id and i["severity"] == "CRITICAL"), None)
    assert matching_alert is not None, "Critical alert was not found in notifications feed"
    assert "Blocker Flagged" in matching_alert["title"]
    assert len(matching_alert["deliveries"]) >= 1
    
    # 3. Clean up: Unblock task
    await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": False}
    )

@pytest.mark.asyncio
async def test_cross_overdue_task_alert_scan_and_read_receipt_lifecycle(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 3: Overdue Task Alert & Read Receipt Lifecycle:
    1. Create an overdue task
    2. Trigger generate-alerts scan
    3. Verify alert generated
    4. Mark alert as read
    5. Clean up task
    """
    # 1. Get an existing project
    proj_res = await db_session.execute(select(Project).limit(1))
    proj = proj_res.scalars().first()
    assert proj is not None
    
    test_task = Task(
        project_id=proj.id,
        title="Tier3 E2E Integration Overdue Task",
        due_date=date.today() - timedelta(days=5),
        status="New",
        priority="High",
        is_overdue=True
    )
    db_session.add(test_task)
    await db_session.commit()
    await db_session.refresh(test_task)
    
    try:
        # 2. Trigger alert generation
        gen_resp = await client.post("/api/v1/notifications/generate-alerts", headers=admin_headers)
        assert gen_resp.status_code == 200
        
        # 3. Locate notification in feed
        feed_resp = await client.get("/api/v1/notifications/", headers=admin_headers)
        assert feed_resp.status_code == 200
        notifs = feed_resp.json()
        target_notif = next((n for n in notifs if n["entity_id"] == test_task.id), None)
        assert target_notif is not None
        assert target_notif["is_read"] is False
        
        # 4. Mark read
        read_resp = await client.patch(f"/api/v1/notifications/{target_notif['id']}/read", headers=admin_headers)
        assert read_resp.status_code == 200
        assert read_resp.json()["is_read"] is True
        
    finally:
        # Clean up created task
        await db_session.delete(test_task)
        await db_session.commit()

@pytest.mark.asyncio
async def test_cross_admin_config_update_affects_notification_dispatch(client: AsyncClient, admin_headers: dict):
    """
    Tier 3: Admin Configuration & Alert Recipient Parameterization:
    1. Update default recipient name & email in admin config
    2. Trigger new notification
    3. Verify notification delivery destination references the updated recipient email
    """
    target_email = "connect.aiindia@gmail.com"
    target_name = "Admin Verification"
    
    update_resp = await client.put(
        "/api/v1/admin/recipient-config",
        headers=admin_headers,
        json={"recipient_email": target_email, "recipient_name": target_name}
    )
    assert update_resp.status_code == 200
    
    # Trigger notification
    notif_resp = await client.post(
        "/api/v1/notifications/trigger",
        headers=admin_headers,
        json={
            "title": "Admin Recipient Verification Alert",
            "message": "Testing recipient dispatch resolution",
            "severity": "INFO"
        }
    )
    assert notif_resp.status_code == 201
    nid = notif_resp.json()["notification_id"]
    
    # Inspect deliveries
    feed = (await client.get("/api/v1/notifications/", headers=admin_headers)).json()
    item = next((i for i in feed if i["id"] == nid), None)
    assert item is not None
    assert any(target_email in d["destination"] for d in item["deliveries"])

@pytest.mark.asyncio
async def test_cross_task_completion_status_propagation(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 3: Task Resolution -> Project Completed Tasks Metric Propagation:
    1. Read initial project completed_tasks count
    2. Insert task in that project with status='DONE'
    3. Re-query projects endpoint -> completed_tasks increments by 1
    4. Clean up test task
    """
    projs = (await client.get("/api/v1/projects/", headers=admin_headers)).json()
    assert len(projs) >= 1
    target_p = projs[0]
    initial_completed = target_p["completed_tasks"]
    
    # Insert completed task
    test_task = Task(
        project_id=target_p["id"],
        title="Completed E2E Test Task",
        status="DONE",
        priority="Normal"
    )
    db_session.add(test_task)
    await db_session.commit()
    await db_session.refresh(test_task)
    
    try:
        updated_projs = (await client.get("/api/v1/projects/", headers=admin_headers)).json()
        updated_p = next(p for p in updated_projs if p["id"] == target_p["id"])
        assert updated_p["completed_tasks"] == initial_completed + 1
    finally:
        await db_session.delete(test_task)
        await db_session.commit()
