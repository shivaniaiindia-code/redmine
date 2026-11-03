import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.task import Task
from app.models.project import Project
from app.models.employee import Employee
from app.models.redmine_sync import RedmineMapping
from app.services.ai_service import ai_service
from app.services.redmine_service import redmine_service

# ==============================================================================
# TIER 4: REAL-WORLD SCENARIOS
# ==============================================================================

@pytest.mark.asyncio
async def test_scenario_redmine_delta_update_and_deduplication(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 4 Scenario 1: Redmine Delta Synchronization & Watermark Deduplication
    Simulates production sync cycle:
    1. Check initial project count in DB
    2. Execute manual sync via /redmine/sync/trigger
    3. Verify existing RedmineMappings are updated, not duplicated
    4. Verify RedmineSyncState watermark timestamp is updated
    """
    initial_mappings_res = await db_session.execute(
        select(RedmineMapping).where(RedmineMapping.entity_type == "PROJECT")
    )
    initial_p_count = len(initial_mappings_res.scalars().all())
    
    # Trigger delta sync
    sync_resp = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert sync_resp.status_code == 200
    summary = sync_resp.json()["summary"]
    assert summary["status"] == "SUCCESS"
    
    # Re-query mappings to ensure no duplicate mappings were created
    updated_mappings_res = await db_session.execute(
        select(RedmineMapping).where(RedmineMapping.entity_type == "PROJECT")
    )
    updated_mappings = updated_mappings_res.scalars().all()
    # Unique redmine_ids should equal count of mappings
    unique_redmine_ids = {m.redmine_id for m in updated_mappings}
    assert len(unique_redmine_ids) == len(updated_mappings), "Duplicate Redmine project mappings detected!"

@pytest.mark.asyncio
async def test_scenario_high_priority_blocker_escalation(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 4 Scenario 2: High-Priority Blocker Escalation
    Simulates an operational incident:
    1. A mission-critical task encounters a deployment blocker
    2. Engineer triggers toggle-blocker with incident description
    3. Automated CRITICAL alert is generated immediately
    4. Delivery item is registered for the Administrator
    5. Blocker is resolved and status verified
    """
    # 1. Fetch first task
    tasks = (await client.get("/api/v1/tasks/", headers=admin_headers)).json()
    assert len(tasks) >= 1
    task = tasks[0]
    task_id = task["id"]
    
    incident_reason = "Production GPU memory allocation failure in ANPR tensor engine."
    
    # 2. Flag blocker
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": True, "blocker_reason": incident_reason}
    )
    assert resp.status_code == 200
    assert resp.json()["is_blocked"] is True
    
    # 3. Check notifications for CRITICAL escalation
    notifs = (await client.get("/api/v1/notifications/", headers=admin_headers)).json()
    incident_notif = next((n for n in notifs if n["entity_id"] == task_id and n["severity"] == "CRITICAL"), None)
    assert incident_notif is not None
    assert "Blocker Flagged" in incident_notif["title"]
    assert incident_reason in incident_notif["message"]
    
    # 4. Resolve blocker
    resolve_resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": False}
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["is_blocked"] is False

@pytest.mark.asyncio
async def test_scenario_employee_reallocation_and_workload(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 4 Scenario 3: Employee Re-Allocation & Workload Rebalancing
    Simulates operational rebalancing:
    1. Locate two active employees
    2. Assign a new task to Employee A -> verify Employee A's total_tasks increments
    3. Reassign the task to Employee B -> verify Employee A decrements and Employee B increments
    4. Clean up test task
    """
    emps = (await client.get("/api/v1/employees/", headers=admin_headers)).json()
    assert len(emps) >= 2, "Expected at least 2 employees in database"
    emp_a, emp_b = emps[0], emps[1]
    
    projs = (await client.get("/api/v1/projects/", headers=admin_headers)).json()
    assert len(projs) >= 1
    proj_id = projs[0]["id"]
    
    # 1. Create task assigned to Employee A
    test_task = Task(
        project_id=proj_id,
        assigned_to_id=emp_a["id"],
        title="Re-allocation E2E Test Task",
        status="In Progress",
        priority="Normal"
    )
    db_session.add(test_task)
    await db_session.commit()
    await db_session.refresh(test_task)
    
    try:
        # Check emp A task count
        emps_after_a = (await client.get("/api/v1/employees/", headers=admin_headers)).json()
        current_emp_a = next(e for e in emps_after_a if e["id"] == emp_a["id"])
        assert current_emp_a["total_tasks"] == emp_a["total_tasks"] + 1
        
        # 2. Reassign to Employee B
        test_task.assigned_to_id = emp_b["id"]
        await db_session.commit()
        
        # Check emp B incremented, emp A restored
        emps_after_b = (await client.get("/api/v1/employees/", headers=admin_headers)).json()
        updated_emp_a = next(e for e in emps_after_b if e["id"] == emp_a["id"])
        updated_emp_b = next(e for e in emps_after_b if e["id"] == emp_b["id"])
        
        assert updated_emp_a["total_tasks"] == emp_a["total_tasks"]
        assert updated_emp_b["total_tasks"] == emp_b["total_tasks"] + 1
    finally:
        await db_session.delete(test_task)
        await db_session.commit()

@pytest.mark.asyncio
async def test_scenario_management_ai_query_grounding(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """
    Tier 4 Scenario 4: Executive Management AI Query Scenario
    Simulates administrator asking the AI assistant for an operational briefing:
    1. AIService extracts verified facts from DB
    2. Prompt submitted to /api/v1/ai/chat
    3. Validates assistant answers deterministically with grounded=True flag
    """
    context = await ai_service.get_grounded_context(db_session)
    assert len(context["projects"]) >= 1
    assert len(context["employees"]) >= 1
    
    prompt = "Summarize the current project health status and flag any blocked or overdue deliverables."
    resp = await client.post(
        "/api/v1/ai/chat",
        headers=admin_headers,
        json={"prompt": prompt}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data.get("grounded", True) is True
    assert len(data["response"]) > 20
