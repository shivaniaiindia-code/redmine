import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.task import Task
from app.models.project import Project

# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================

@pytest.mark.asyncio
async def test_boundary_nonexistent_task_toggle_blocker_returns_404(client: AsyncClient, admin_headers: dict):
    """Tier 2: Requesting toggle-blocker on nonexistent task ID returns HTTP 404."""
    response = await client.post(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": True, "blocker_reason": "Nonexistent task test"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_boundary_nonexistent_notification_read_returns_404(client: AsyncClient, admin_headers: dict):
    """Tier 2: Marking a nonexistent notification ID as read returns HTTP 404."""
    response = await client.patch(
        "/api/v1/notifications/00000000-0000-0000-0000-000000000000/read",
        headers=admin_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_boundary_tasks_filter_nonexistent_project_returns_empty_list(client: AsyncClient, admin_headers: dict):
    """Tier 2: Filtering tasks by non-matching project_id returns [] with status 200, never 500."""
    response = await client.get(
        "/api/v1/tasks/?project_id=nonexistent-project-uuid-99999",
        headers=admin_headers
    )
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_boundary_extreme_blocker_reason_length_and_unicode(client: AsyncClient, admin_headers: dict):
    """Tier 2: Blocker reason with 1000+ chars, emojis, non-ASCII (Hindi/Japanese), and HTML meta-chars."""
    tasks_resp = await client.get("/api/v1/tasks/", headers=admin_headers)
    task_id = tasks_resp.json()[0]["id"]
    
    extreme_reason = (
        "🚨 CRITICAL HARDWARE LOCK: <script>alert('xss')</script> "
        "सर्वर डाउन — データベース接続エラー — " + ("A" * 800)
    )
    
    resp = await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": True, "blocker_reason": extreme_reason}
    )
    assert resp.status_code == 200
    assert resp.json()["is_blocked"] is True
    
    # Restore clean state
    await client.post(
        f"/api/v1/tasks/{task_id}/toggle-blocker",
        headers=admin_headers,
        json={"is_blocked": False}
    )

@pytest.mark.asyncio
async def test_boundary_extreme_notification_payload_unicode(client: AsyncClient, admin_headers: dict):
    """Tier 2: Notification dispatch with unicode characters, symbols, and formatting."""
    payload = {
        "title": "⚡ ANPR 系統警報 — High Load 🚀",
        "message": "Latency exceeded threshold: <tag>test & verify</tag> — 100% load registered.",
        "severity": "CRITICAL",
        "entity_type": "TASK"
    }
    response = await client.post("/api/v1/notifications/trigger", headers=admin_headers, json=payload)
    assert response.status_code == 201
    nid = response.json()["notification_id"]
    
    # Verify in list
    list_resp = await client.get("/api/v1/notifications/", headers=admin_headers)
    items = list_resp.json()
    created = next((i for i in items if i["id"] == nid), None)
    assert created is not None
    assert "系統警報" in created["title"]

@pytest.mark.asyncio
async def test_boundary_admin_update_empty_payload(client: AsyncClient, admin_headers: dict):
    """Tier 2: Submitting an empty JSON object to admin config update succeeds idempotently."""
    response = await client.put(
        "/api/v1/admin/recipient-config",
        headers=admin_headers,
        json={}
    )
    assert response.status_code == 200
    data = response.json()
    assert "recipient_email" in data
    assert "in_app_enabled" in data

@pytest.mark.asyncio
async def test_boundary_tasks_filter_combined_flags(client: AsyncClient, admin_headers: dict):
    """Tier 2: Filtering tasks with combined flags (is_overdue=true, is_blocked=false) executes without error."""
    response = await client.get("/api/v1/tasks/?is_overdue=true&is_blocked=false", headers=admin_headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    for t in tasks:
        assert t["is_overdue"] is True
        assert t["is_blocked"] is False

@pytest.mark.asyncio
async def test_boundary_ai_chat_prompt_with_special_characters(client: AsyncClient, admin_headers: dict):
    """Tier 2: AI Assistant endpoint handles queries with punctuation, symbols, and numbers."""
    payload = {"prompt": "What's the status of PRJ-MILIT & task #101? (Is it > 50% done?)"}
    response = await client.post("/api/v1/ai/chat", headers=admin_headers, json=payload)
    assert response.status_code == 200
    assert "response" in response.json()
