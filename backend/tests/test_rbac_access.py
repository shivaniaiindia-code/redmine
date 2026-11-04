"""
RBAC access matrix: anonymous requests are rejected, every role can read the
workspace views, and administration endpoints are limited to SUPER_ADMIN /
COMPANY_MANAGEMENT (user role & status changes: SUPER_ADMIN only).
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.user import Role, User

API = "/api/v1"

WORKSPACE_READS = [
    "/auth/me",
    "/projects/",
    "/tasks/",
    "/employees/",
    "/teams/",
    "/reports/overview",
    "/notifications/",
    "/notifications/summary",
    "/redmine/status",
]

ADMIN_READS = [
    "/admin/integrations",
    "/admin/email-recipients",
    "/admin/recipient-config",
    "/admin/email-automation",
    "/auth/users",
]


@pytest_asyncio.fixture
async def role_headers(db_session):
    """Creates one throwaway user per role in the test DB and returns auth headers."""
    headers = {}
    created = []
    for role_name in ("SUPER_ADMIN", "COMPANY_MANAGEMENT", "PROJECT_MANAGER", "TEAM_LEAD", "EMPLOYEE"):
        role = (await db_session.execute(select(Role).where(Role.name == role_name))).scalar_one()
        user = User(
            id=str(uuid.uuid4()),
            email=f"rbac-{role_name.lower()}-{uuid.uuid4().hex[:6]}@test.local",
            hashed_password=get_password_hash("x"),
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        created.append(user)
        token = create_access_token({"sub": user.id, "email": user.email, "role": role_name})
        headers[role_name] = {"Authorization": f"Bearer {token}"}
    await db_session.commit()
    headers["_users"] = {u.email.split("-")[1]: u for u in created}
    yield headers
    for u in created:
        await db_session.delete(u)
    await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", WORKSPACE_READS + ADMIN_READS)
async def test_anonymous_requests_are_rejected(anon_client, path):
    res = await anon_client.get(API + path)
    assert res.status_code == 401, f"{path} must require sign-in, got {res.status_code}"


@pytest.mark.asyncio
async def test_invalid_token_is_rejected(anon_client):
    client = anon_client
    res = await client.get(API + "/projects/", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "COMPANY_MANAGEMENT", "PROJECT_MANAGER", "TEAM_LEAD", "EMPLOYEE"])
async def test_every_role_can_read_workspace(client, role_headers, role):
    for path in WORKSPACE_READS:
        res = await client.get(API + path, headers=role_headers[role])
        assert res.status_code == 200, f"{role} {path} -> {res.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected", [
    ("SUPER_ADMIN", 200), ("COMPANY_MANAGEMENT", 200),
    ("PROJECT_MANAGER", 403), ("TEAM_LEAD", 403), ("EMPLOYEE", 403),
])
async def test_admin_endpoints_restricted(client, role_headers, role, expected):
    for path in ADMIN_READS:
        res = await client.get(API + path, headers=role_headers[role])
        assert res.status_code == expected, f"{role} {path} -> {res.status_code}"


@pytest.mark.asyncio
async def test_me_returns_the_token_owner(client, role_headers):
    res = await client.get(API + "/auth/me", headers=role_headers["EMPLOYEE"])
    assert res.status_code == 200
    assert res.json()["role"]["name"] == "EMPLOYEE"


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected", [("COMPANY_MANAGEMENT", 403), ("EMPLOYEE", 403)])
async def test_only_super_admin_changes_roles(client, role_headers, role, expected):
    target = role_headers["_users"]["employee"]
    res = await client.put(API + f"/auth/users/{target.id}/role", json={"role": "SUPER_ADMIN"},
                           headers=role_headers[role])
    assert res.status_code == expected


@pytest.mark.asyncio
async def test_employee_cannot_block_or_delete_users(client, role_headers):
    target = role_headers["_users"]["team_lead"]
    res = await client.put(API + f"/auth/users/{target.id}/status", json={"is_active": False},
                           headers=role_headers["EMPLOYEE"])
    assert res.status_code == 403
    res = await client.delete(API + f"/auth/users/{target.id}", headers=role_headers["EMPLOYEE"])
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_management_cannot_block_or_delete_super_admin(client, role_headers):
    target = role_headers["_users"]["super_admin"]
    res = await client.put(API + f"/auth/users/{target.id}/status", json={"is_active": False},
                           headers=role_headers["COMPANY_MANAGEMENT"])
    assert res.status_code == 403
    res = await client.delete(API + f"/auth/users/{target.id}", headers=role_headers["COMPANY_MANAGEMENT"])
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_trigger_admin_alert_email(client, role_headers, email_outbox):
    res = await client.post(API + "/notifications/trigger", headers=role_headers["EMPLOYEE"], json={
        "title": "x", "message": "x", "severity": "CRITICAL",
    })
    assert res.status_code == 403
    assert email_outbox == []


@pytest.mark.asyncio
async def test_deactivated_user_is_locked_out(client, role_headers, db_session):
    user = role_headers["_users"]["employee"]
    user.is_active = False
    await db_session.commit()
    res = await client.get(API + "/projects/", headers=role_headers["EMPLOYEE"])
    assert res.status_code == 401
