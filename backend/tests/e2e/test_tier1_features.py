import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.project import Project
from app.models.task import Task
from app.models.employee import Employee
from app.models.team import Team
from app.services.ai_service import ai_service

# ==============================================================================
# FEATURE 1: PROJECTS VIEW ENDPOINT (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_projects_list_returns_valid_array_with_required_fields(client: AsyncClient, admin_headers: dict):
    """Tier 1.1: Verify GET /api/v1/projects/ returns valid list with all required schema fields."""
    response = await client.get("/api/v1/projects/", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) >= 1, "Expected at least 1 project in database"
    
    first = projects[0]
    required_keys = [
        "id", "name", "code", "description", "status", "health_status",
        "health_reason", "progress_percentage", "start_date",
        "target_completion_date", "total_tasks", "overdue_tasks",
        "blocked_tasks", "completed_tasks"
    ]
    for key in required_keys:
        assert key in first, f"Missing required project key: {key}"

@pytest.mark.asyncio
async def test_projects_health_status_and_reasons_fidelity(client: AsyncClient, admin_headers: dict):
    """Tier 1.1: Verify health status values adhere to domain enum (ON_TRACK, AT_RISK, OFF_TRACK, BLOCKED)."""
    response = await client.get("/api/v1/projects/", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    valid_health = {"ON_TRACK", "AT_RISK", "OFF_TRACK", "BLOCKED"}
    for p in projects:
        assert p["health_status"] in valid_health, f"Invalid health status {p['health_status']} in project {p['id']}"

@pytest.mark.asyncio
async def test_projects_task_metrics_aggregation_counts(client: AsyncClient, admin_headers: dict):
    """Tier 1.1: Verify task count metrics are non-negative and mathematically consistent."""
    response = await client.get("/api/v1/projects/", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    for p in projects:
        assert p["total_tasks"] >= 0
        assert p["overdue_tasks"] >= 0
        assert p["blocked_tasks"] >= 0
        assert p["completed_tasks"] >= 0
        assert p["overdue_tasks"] <= p["total_tasks"]
        assert p["completed_tasks"] <= p["total_tasks"]

@pytest.mark.asyncio
async def test_projects_progress_percentage_bounds(client: AsyncClient, admin_headers: dict):
    """Tier 1.1: Verify progress_percentage is bounded between 0.0 and 100.0."""
    response = await client.get("/api/v1/projects/", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    for p in projects:
        progress = p["progress_percentage"]
        assert isinstance(progress, (int, float))
        assert 0.0 <= progress <= 100.0, f"Progress out of bounds: {progress}"

@pytest.mark.asyncio
async def test_projects_start_and_target_completion_dates(client: AsyncClient, admin_headers: dict):
    """Tier 1.1: Verify date fields format is ISO or null, and start <= target if both present."""
    response = await client.get("/api/v1/projects/", headers=admin_headers)
    assert response.status_code == 200
    projects = response.json()
    for p in projects:
        s_date = p["start_date"]
        t_date = p["target_completion_date"]
        if s_date and t_date:
            assert s_date <= t_date, f"Project {p['name']} has start_date {s_date} > target {t_date}"


# ==============================================================================
# FEATURE 2: TEAMS VIEW ENDPOINT (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_teams_list_structure_and_required_keys(client: AsyncClient, admin_headers: dict):
    """Tier 1.2: Verify GET /api/v1/teams/ returns list with required schema keys."""
    response = await client.get("/api/v1/teams/", headers=admin_headers)
    assert response.status_code == 200
    teams = response.json()
    assert isinstance(teams, list)
    if len(teams) > 0:
        team = teams[0]
        required_keys = ["id", "name", "department", "description", "is_active", "members_count", "projects_count", "projects"]
        for key in required_keys:
            assert key in team, f"Missing team key: {key}"

@pytest.mark.asyncio
async def test_teams_project_association_and_health_structure(client: AsyncClient, admin_headers: dict):
    """Tier 1.2: Verify team projects contain project id, name, and health_status."""
    response = await client.get("/api/v1/teams/", headers=admin_headers)
    assert response.status_code == 200
    teams = response.json()
    for team in teams:
        for prj in team.get("projects", []):
            assert "id" in prj
            assert "name" in prj
            assert "health_status" in prj

@pytest.mark.asyncio
async def test_teams_members_count_non_negative(client: AsyncClient, admin_headers: dict):
    """Tier 1.2: Verify members_count and projects_count are non-negative integers."""
    response = await client.get("/api/v1/teams/", headers=admin_headers)
    assert response.status_code == 200
    teams = response.json()
    for team in teams:
        assert isinstance(team["members_count"], int)
        assert team["members_count"] >= 0
        assert isinstance(team["projects_count"], int)
        assert team["projects_count"] >= 0

@pytest.mark.asyncio
async def test_teams_active_status_fidelity(client: AsyncClient, admin_headers: dict):
    """Tier 1.2: Verify is_active flag is a boolean."""
    response = await client.get("/api/v1/teams/", headers=admin_headers)
    assert response.status_code == 200
    teams = response.json()
    for team in teams:
        assert isinstance(team["is_active"], bool)

@pytest.mark.asyncio
async def test_teams_department_categorization_validity(client: AsyncClient, admin_headers: dict):
    """Tier 1.2: Verify department field is a non-empty string."""
    response = await client.get("/api/v1/teams/", headers=admin_headers)
    assert response.status_code == 200
    teams = response.json()
    for team in teams:
        assert isinstance(team["department"], str)
        assert len(team["department"].strip()) > 0


# ==============================================================================
# FEATURE 3: EMPLOYEES VIEW ENDPOINT (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_employees_list_roster_data_fidelity(client: AsyncClient, admin_headers: dict):
    """Tier 1.3: Verify GET /api/v1/employees/ returns employee roster with required keys."""
    response = await client.get("/api/v1/employees/", headers=admin_headers)
    assert response.status_code == 200
    employees = response.json()
    assert isinstance(employees, list)
    assert len(employees) >= 1
    
    first = employees[0]
    required_keys = ["id", "name", "email", "job_title", "department", "status", "weekly_capacity_hours", "total_tasks", "overdue_tasks", "completed_tasks"]
    for key in required_keys:
        assert key in first, f"Missing employee key: {key}"

@pytest.mark.asyncio
async def test_employees_weekly_capacity_and_workload(client: AsyncClient, admin_headers: dict):
    """Tier 1.3: Verify employee weekly capacity is positive and standard float."""
    response = await client.get("/api/v1/employees/", headers=admin_headers)
    assert response.status_code == 200
    employees = response.json()
    for emp in employees:
        assert isinstance(emp["weekly_capacity_hours"], (int, float))
        assert emp["weekly_capacity_hours"] > 0

@pytest.mark.asyncio
async def test_employees_task_metrics_correlation(client: AsyncClient, admin_headers: dict):
    """Tier 1.3: Verify employee task metrics are non-negative and overdue <= total."""
    response = await client.get("/api/v1/employees/", headers=admin_headers)
    assert response.status_code == 200
    employees = response.json()
    for emp in employees:
        assert emp["total_tasks"] >= 0
        assert emp["overdue_tasks"] >= 0
        assert emp["completed_tasks"] >= 0
        assert emp["overdue_tasks"] <= emp["total_tasks"]

@pytest.mark.asyncio
async def test_employees_department_and_job_title_fidelity(client: AsyncClient, admin_headers: dict):
    """Tier 1.3: Verify employee job_title and department are strings."""
    response = await client.get("/api/v1/employees/", headers=admin_headers)
    assert response.status_code == 200
    employees = response.json()
    for emp in employees:
        assert isinstance(emp["job_title"], str)
        assert isinstance(emp["department"], str)

@pytest.mark.asyncio
async def test_employees_active_status_reporting(client: AsyncClient, admin_headers: dict):
    """Tier 1.3: Verify employee status is an expected enum value (ACTIVE, ON_LEAVE, DEPARTED)."""
    response = await client.get("/api/v1/employees/", headers=admin_headers)
    assert response.status_code == 200
    employees = response.json()
    valid_statuses = {"ACTIVE", "ON_LEAVE", "DEPARTED"}
    for emp in employees:
        assert emp["status"] in valid_statuses


# ==============================================================================
# FEATURE 4: TASKS VIEW ENDPOINT (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_tasks_list_fidelity_and_attributes(client: AsyncClient, admin_headers: dict):
    """Tier 1.4: Verify GET /api/v1/tasks/ returns tasks with all schema attributes."""
    response = await client.get("/api/v1/tasks/", headers=admin_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) >= 1
    
    first = tasks[0]
    required_keys = ["id", "title", "project_id", "project_name", "tracker", "status", "priority", "due_date", "is_overdue", "is_blocked", "blocker_reason", "assigned_to", "estimated_hours", "progress_percentage"]
    for key in required_keys:
        assert key in first, f"Missing task key: {key}"

@pytest.mark.asyncio
async def test_tasks_project_id_filtering(client: AsyncClient, admin_headers: dict):
    """Tier 1.4: Verify filtering tasks by project_id returns only tasks for that project."""
    tasks_resp = await client.get("/api/v1/tasks/", headers=admin_headers)
    tasks = tasks_resp.json()
    sample_pid = tasks[0]["project_id"]
    
    filtered_resp = await client.get(f"/api/v1/tasks/?project_id={sample_pid}", headers=admin_headers)
    assert filtered_resp.status_code == 200
    filtered_tasks = filtered_resp.json()
    assert len(filtered_tasks) >= 1
    for t in filtered_tasks:
        assert t["project_id"] == sample_pid

@pytest.mark.asyncio
async def test_tasks_overdue_flag_filtering(client: AsyncClient, admin_headers: dict):
    """Tier 1.4: Verify filtering tasks by is_overdue=true/false works correctly."""
    response = await client.get("/api/v1/tasks/?is_overdue=true", headers=admin_headers)
    assert response.status_code == 200
    overdue_tasks = response.json()
    for t in overdue_tasks:
        assert t["is_overdue"] is True

@pytest.mark.asyncio
async def test_tasks_blocked_flag_filtering(client: AsyncClient, admin_headers: dict):
    """Tier 1.4: Verify filtering tasks by is_blocked=true returns only blocked tasks."""
    response = await client.get("/api/v1/tasks/?is_blocked=true", headers=admin_headers)
    assert response.status_code == 200
    blocked_tasks = response.json()
    for t in blocked_tasks:
        assert t["is_blocked"] is True

@pytest.mark.asyncio
async def test_tasks_toggle_blocker_operational_trigger(client: AsyncClient, admin_headers: dict):
    """Tier 1.4: Verify toggling blocker on a task updates state and reason."""
    tasks_resp = await client.get("/api/v1/tasks/", headers=admin_headers)
    task = tasks_resp.json()[0]
    task_id = task["id"]
    
    # 1. Flag as blocked
    block_resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": True, "blocker_reason": "Waiting on client API credentials"}
    )
    assert block_resp.status_code == 200
    assert block_resp.json()["is_blocked"] is True
    
    # 2. Unflag blocker
    unblock_resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": False}
    )
    assert unblock_resp.status_code == 200
    assert unblock_resp.json()["is_blocked"] is False


# ==============================================================================
# FEATURE 5: REDMINE SYNC ENGINE (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_redmine_status_connectivity(client: AsyncClient, admin_headers: dict):
    """Tier 1.5: Verify GET /api/v1/redmine/status reports connection status and metadata."""
    response = await client.get("/api/v1/redmine/status", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert "base_url" in data
    assert "last_synced_at" in data
    assert "records_synced" in data
    assert "status" in data

@pytest.mark.asyncio
async def test_redmine_manual_sync_trigger_execution(client: AsyncClient, admin_headers: dict):
    """Tier 1.5: Verify POST /api/v1/redmine/sync/trigger completes and returns summary."""
    response = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "summary" in data

@pytest.mark.asyncio
async def test_redmine_sync_summary_response_schema(client: AsyncClient, admin_headers: dict):
    """Tier 1.5: Verify sync summary includes counts for projects, tasks, employees, and alerts."""
    response = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "projects_synced" in summary
    assert "tasks_synced" in summary
    assert "employees_synced" in summary
    assert "alerts_generated" in summary
    assert summary["status"] == "SUCCESS"

@pytest.mark.asyncio
async def test_redmine_sync_watermark_state_persistence(client: AsyncClient, admin_headers: dict):
    """Tier 1.5: Verify that after sync, status reports records_synced > 0 and recent timestamp."""
    status_resp = await client.get("/api/v1/redmine/status", headers=admin_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["last_synced_at"] != "Never"
    assert status_data["records_synced"] >= 1

@pytest.mark.asyncio
async def test_redmine_repeated_sync_idempotency(client: AsyncClient, admin_headers: dict):
    """Tier 1.5: Verify triggering sync twice consecutively succeeds without duplicate key errors."""
    resp1 = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert resp1.status_code == 200
    resp2 = await client.post("/api/v1/redmine/sync/trigger", headers=admin_headers)
    assert resp2.status_code == 200
    assert resp2.json()["success"] is True


# ==============================================================================
# FEATURE 6: NOTIFICATIONS & ALERTING (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_notifications_list_retrieval(client: AsyncClient, admin_headers: dict):
    """Tier 1.6: Verify GET /api/v1/notifications/ returns list with delivery items."""
    response = await client.get("/api/v1/notifications/", headers=admin_headers)
    assert response.status_code == 200
    notifications = response.json()
    assert isinstance(notifications, list)
    if len(notifications) > 0:
        n = notifications[0]
        assert "id" in n
        assert "title" in n
        assert "severity" in n
        assert "is_read" in n
        assert "deliveries" in n

@pytest.mark.asyncio
async def test_notifications_manual_trigger_creation(client: AsyncClient, admin_headers: dict):
    """Tier 1.6: Verify POST /api/v1/notifications/trigger dispatches new notification."""
    payload = {
        "title": "E2E Automated Notification Test",
        "message": "Validating notification dual-dispatch and persistence",
        "severity": "WARNING",
        "entity_type": "PROJECT"
    }
    response = await client.post("/api/v1/notifications/trigger", headers=admin_headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "notification_id" in data

@pytest.mark.asyncio
async def test_notifications_mark_single_as_read(client: AsyncClient, admin_headers: dict):
    """Tier 1.6: Verify PATCH /api/v1/notifications/{id}/read marks a notification as read."""
    # Create notification
    create_resp = await client.post(
        "/api/v1/notifications/trigger",
        headers=admin_headers,
        json={"title": "Read Test", "message": "To be marked read", "severity": "INFO"}
    )
    nid = create_resp.json()["notification_id"]
    
    # Mark as read
    patch_resp = await client.patch(f"/api/v1/notifications/{nid}/read", headers=admin_headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_read"] is True

@pytest.mark.asyncio
async def test_notifications_mark_all_as_read(client: AsyncClient, admin_headers: dict):
    """Tier 1.6: Verify POST /api/v1/notifications/read-all marks all notifications as read."""
    response = await client.post("/api/v1/notifications/read-all", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_notifications_automated_alerts_scan(client: AsyncClient, admin_headers: dict):
    """Tier 1.6: Verify POST /api/v1/notifications/generate-alerts scans and reports alerts count."""
    response = await client.post("/api/v1/notifications/generate-alerts", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "alerts_generated" in data


# ==============================================================================
# FEATURE 7: AI ASSISTANT GROUNDING (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_chat_grounded_response_contract(client: AsyncClient, admin_headers: dict):
    """Tier 1.7: Verify POST /api/v1/ai/chat returns grounded response structure."""
    response = await client.post(
        "/api/v1/ai/chat",
        headers=admin_headers,
        json={"prompt": "Provide a brief project status overview."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "grounded" in data
    assert "model" in data

@pytest.mark.asyncio
async def test_ai_chat_conversation_history_handling(client: AsyncClient, admin_headers: dict):
    """Tier 1.7: Verify AI chat accepts previous conversation history."""
    payload = {
        "prompt": "What was my previous question?",
        "history": [
            {"role": "user", "content": "What is the project count?"},
            {"role": "assistant", "content": "There are active projects."}
        ]
    }
    response = await client.post("/api/v1/ai/chat", headers=admin_headers, json=payload)
    assert response.status_code == 200
    assert "response" in response.json()

@pytest.mark.asyncio
async def test_ai_grounded_context_projects_extraction(db_session: AsyncSession):
    """Tier 1.7: Verify AIService extracts projects list from live DB."""
    context = await ai_service.get_grounded_context(db_session)
    assert "projects" in context
    assert isinstance(context["projects"], list)
    assert len(context["projects"]) >= 1

@pytest.mark.asyncio
async def test_ai_grounded_context_overdue_tasks_extraction(db_session: AsyncSession):
    """Tier 1.7: Verify AIService extracts overdue and blocked tasks correctly."""
    context = await ai_service.get_grounded_context(db_session)
    assert "tasks" in context
    assert isinstance(context["tasks"], list)
    assert "current_date" in context

@pytest.mark.asyncio
async def test_ai_grounded_context_employee_extraction(db_session: AsyncSession):
    """Tier 1.7: Verify AIService extracts employee roster from live DB."""
    context = await ai_service.get_grounded_context(db_session)
    assert "employees" in context
    assert isinstance(context["employees"], list)
    assert len(context["employees"]) >= 1


# ==============================================================================
# FEATURE 8: ADMIN SETTINGS & CONFIGURATION (>= 5 TESTS)
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_get_recipient_config_defaults(client: AsyncClient, admin_headers: dict):
    """Tier 1.8: Verify GET /api/v1/admin/recipient-config returns default admin recipient."""
    response = await client.get("/api/v1/admin/recipient-config", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["recipient_email"] == "connect.aiindia@gmail.com"
    assert "in_app_enabled" in data
    assert "email_enabled" in data
    assert "google_chat_enabled" not in data  # legacy Google Chat dispatch removed (M3)

@pytest.mark.asyncio
async def test_admin_update_recipient_email(client: AsyncClient, admin_headers: dict):
    """Tier 1.8: Verify PUT /api/v1/admin/recipient-config updates recipient email."""
    update_payload = {"recipient_email": "connect.aiindia@gmail.com"}
    response = await client.put("/api/v1/admin/recipient-config", headers=admin_headers, json=update_payload)
    assert response.status_code == 200
    assert response.json()["recipient_email"] == "connect.aiindia@gmail.com"

@pytest.mark.asyncio
async def test_admin_update_recipient_name(client: AsyncClient, admin_headers: dict):
    """Tier 1.8: Verify updating recipient name persists."""
    update_payload = {"recipient_name": "Lead Admin"}
    response = await client.put("/api/v1/admin/recipient-config", headers=admin_headers, json=update_payload)
    assert response.status_code == 200
    assert response.json()["recipient_name"] == "Lead Admin"

@pytest.mark.asyncio
async def test_admin_toggle_notification_channels(client: AsyncClient, admin_headers: dict):
    """Tier 1.8: Verify toggling delivery channel flags persists."""
    payload = {"in_app_enabled": True, "email_enabled": True}
    response = await client.put("/api/v1/admin/recipient-config", headers=admin_headers, json=payload)
    assert response.status_code == 200
    assert response.json()["in_app_enabled"] is True
    assert response.json()["email_enabled"] is True

@pytest.mark.asyncio
async def test_admin_rejects_legacy_google_chat_fields_silently(client: AsyncClient, admin_headers: dict):
    """Tier 1.8: Legacy Google Chat webhook settings are no longer part of the admin contract (M3)."""
    payload = {"google_chat_webhook_url": "https://chat.googleapis.com/v1/spaces/TEST/messages"}
    response = await client.put("/api/v1/admin/recipient-config", headers=admin_headers, json=payload)
    assert response.status_code == 200
    assert "google_chat_webhook_url" not in response.json()
