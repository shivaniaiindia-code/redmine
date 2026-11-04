import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import event
from main import app
from app.core.security import create_access_token
from app.core.database import AsyncSessionLocal, engine
from app.models.project import Project
from app.models.employee import Employee
from app.models.team import Team
from app.models.task import Task
from app.models.notification import Notification

# Ensure SQLite connections wait if another process/task is busy
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.close()
    except Exception:
        pass

def _test_admin_headers():
    token = create_access_token(
        data={"sub": "admin-test-id", "email": "admin@aiindia.com", "role": "SUPER_ADMIN"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """Signed in as the seeded Super Admin (the API rejects anonymous calls)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers=_test_admin_headers()) as ac:
        yield ac


@pytest_asyncio.fixture
async def anon_client():
    """No credentials: for asserting that endpoints require sign-in."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def admin_token():
    return create_access_token(
        data={"sub": "admin-test-id", "email": "admin@aiindia.com", "role": "SUPER_ADMIN"}
    )

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
