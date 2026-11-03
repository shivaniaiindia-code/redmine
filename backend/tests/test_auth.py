import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_admin_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_admin_login_failure(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    # 1. Login to get token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    token = login_resp.json()["access_token"]

    # 2. Call /auth/me
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == "admin@company.com"
    assert user_data["role"]["name"] == "SUPER_ADMIN"
    assert user_data["employee"]["first_name"] == "Anil"

