---
name: qa-security-testing
description: >-
  Use this skill whenever authoring or running automated test suites, validating
  RBAC permission boundaries, checking security vulnerabilities, or profiling API latency.
---

# QA Validation & Security Auditing Skill

This skill provides testing procedures, security auditing scripts, and quality gates for the **QA Agent**.

---

## 1. Test Automation Structure

```
backend/tests/
├── conftest.py            # Async test fixtures, test DB, auth token helpers
├── test_auth.py           # Login, JWT issue, token refresh, invalid password
├── test_rbac.py           # Permission gate penetration tests
├── test_projects.py       # Project listing, metrics, health status calculation
├── test_redmine_sync.py   # Redmine discovery & watermark sync verification
├── test_notifications.py  # System bar push & Admin Google Chat webhook mirroring
└── test_ai_grounding.py   # Tool execution accuracy & RBAC scoping
```

---

## 2. RBAC Boundary Penetration Testing

The QA Agent must explicitly test that lower-privileged roles cannot access restricted resources:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_employee_cannot_access_admin_settings(employee_client: AsyncClient):
    """Verify an Employee role receives HTTP 403 when requesting admin endpoints."""
    response = await employee_client.get("/api/v1/admin/settings")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

@pytest.mark.asyncio
async def test_employee_cannot_view_other_employee_private_notes(employee_client: AsyncClient):
    """Verify an Employee cannot access another employee's performance reviews."""
    response = await employee_client.get("/api/v1/employees/emp-other-id/private-evaluations")
    assert response.status_code == 403
```

---

## 3. Dual-Dispatch Notification Verification Test

```python
@pytest.mark.asyncio
async def test_notification_dual_dispatch_mirrors_to_admin_chat(client: AsyncClient, mock_google_chat):
    """Verify triggering an alert creates a system notification AND mirrors to Google Chat webhook."""
    payload = {
        "title": "ANPR System Deadline Critical",
        "severity": "CRITICAL",
        "entity_type": "PROJECT",
        "entity_id": "prj-anpr-01",
        "message": "5 tasks pending, 2 blocked"
    }
    response = await client.post("/api/v1/notifications/trigger", json=payload)
    assert response.status_code == 201

    # Verify Google Chat Webhook was called with Card v2 schema
    mock_google_chat.post.assert_called_once()
    sent_payload = mock_google_chat.post.call_args[1]["json"]
    assert "cardsV2" in sent_payload
    assert "[SYSTEM BAR MIRROR]" in sent_payload["cardsV2"][0]["card"]["header"]["title"]
```

