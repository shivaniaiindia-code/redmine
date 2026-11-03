import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_company_dashboard_data(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/company/dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Verify 6 Top KPI Cards
    assert len(data["kpis"]) == 6
    kpi_labels = [k["label"] for k in data["kpis"]]
    assert "Active Projects" in kpi_labels
    assert "Open Tasks" in kpi_labels
    assert "Projects at Risk" in kpi_labels

    # Verify Project Status Donut
    assert "project_status" in data
    assert data["project_status"]["total_projects"] >= 2

    # Verify Task Distribution & Team Workload
    assert len(data["task_distribution"]) >= 5
    assert len(data["team_workload"]) >= 1

    # Verify Feeds
    assert len(data["upcoming_deadlines"]) >= 1
    assert len(data["notifications"]) >= 1

@pytest.mark.asyncio
async def test_notification_dual_dispatch(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]

    # Trigger alert
    trigger_resp = await client.post(
        "/api/v1/notifications/trigger",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Critical Blocker in ANPR System",
            "message": "Payment gateway sandbox auth keys failed validation",
            "severity": "CRITICAL",
            "entity_type": "TASK"
        }
    )
    assert trigger_resp.status_code == 201
    assert trigger_resp.json()["success"] is True

    # Check notification list
    list_resp = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(i["title"] == "Critical Blocker in ANPR System" for i in items)
