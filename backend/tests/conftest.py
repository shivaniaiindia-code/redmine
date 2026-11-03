import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.core.config import settings
from main import app
from app.core.security import create_access_token
from app.core.database import AsyncSessionLocal

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def admin_token():
    return create_access_token(
        data={"sub": "admin-test-id", "email": "admin@company.com", "role": "SUPER_ADMIN"}
    )

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
