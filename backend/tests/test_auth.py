import pytest
from httpx import AsyncClient, Response
from unittest.mock import patch, MagicMock
from app.core.config import settings

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_admin_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aiindia.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_admin_login_failure(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aiindia.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    # 1. Login to get token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aiindia.com", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]

    # 2. Call /auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "admin@aiindia.com"
    assert user_data["role"]["name"] == "SUPER_ADMIN"
    assert user_data["employee"]["first_name"] == "Administrator"

@pytest.mark.asyncio
async def test_register_and_list_users(client: AsyncClient):
    # Register new user
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev.test@company.com",
            "password": "Password123!",
            "first_name": "Dev",
            "last_name": "Tester",
            "department": "Engineering",
            "job_title": "Fullstack Developer"
        }
    )
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert "access_token" in reg_data

    # Duplicate registration fails
    dup_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dev.test@company.com",
            "password": "Password123!",
            "first_name": "Dev",
            "last_name": "Tester"
        }
    )
    assert dup_resp.status_code == 400

    # Regular employee token cannot view active users (403 Forbidden)
    emp_token = reg_data["access_token"]
    forbidden_resp = await client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {emp_token}"}
    )
    assert forbidden_resp.status_code == 403

    # Admin lists users
    users_resp = await client.get("/api/v1/auth/users")
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) >= 2
    dev_user = next((u for u in users if u["email"] == "dev.test@company.com"), None)
    assert dev_user is not None
    assert dev_user["name"] == "Dev Tester"
    assert dev_user["is_active"] is True
    assert dev_user["auth_provider"] == "email"

    # Toggle active status to False
    toggle_resp = await client.put(
        f"/api/v1/auth/users/{dev_user['id']}/status",
        json={"is_active": False}
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_active"] is False

    # Login fails when inactive
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "dev.test@company.com", "password": "Password123!"}
    )
    assert bad_login.status_code == 400

    # Toggle back to True
    await client.put(
        f"/api/v1/auth/users/{dev_user['id']}/status",
        json={"is_active": True}
    )

    # Change user role to PROJECT_MANAGER
    role_resp = await client.put(
        f"/api/v1/auth/users/{dev_user['id']}/role",
        json={"role": "PROJECT_MANAGER"}
    )
    assert role_resp.status_code == 200
    assert role_resp.json()["role"] == "PROJECT_MANAGER"

@pytest.mark.asyncio
async def test_google_auth_mock(client: AsyncClient, monkeypatch):
    mock_payload = {
        "aud": settings.GOOGLE_CLIENT_ID or "mock-client-id",
        "email": "google.user@company.com",
        "name": "Google TestUser",
        "given_name": "Google",
        "family_name": "TestUser",
        "picture": "https://example.com/avatar.jpg"
    }

    async def mock_get(*args, **kwargs):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_payload
        return mock_res

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    res = await client.post(
        "/api/v1/auth/google",
        json={"id_token": "valid-mock-token"}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
