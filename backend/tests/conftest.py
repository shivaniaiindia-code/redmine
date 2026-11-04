"""
Test isolation (applies to tests/ and tests/e2e/):

1. DATABASE ISOLATION — before the app is imported, the live database
   (backend/company_intel.db) is snapshotted with the SQLite backup API into
   tests/.test_company_intel.db and the engine is pointed at that copy.
   Tests keep realistic Redmine-synced data but never write test alerts,
   tasks or notifications into the administrator's live dashboard.

2. EMAIL ISOLATION — the SMTP transport is replaced by an in-memory outbox
   for every test, so no test can ever send a real email. Tests that need the
   real SMTP protocol opt in with the `real_smtp_transport` fixture and point
   the settings at a local throwaway SMTP server.
"""
import asyncio
import atexit
import os
import secrets
import sqlite3
from pathlib import Path

# CI has no backend/.env: give the test process its own signing key (never a committed value)
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))

from app.core import config as _config

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_LIVE_DB = _BACKEND_DIR / "company_intel.db"
_TESTS_DIR = Path(__file__).resolve().parent
_TEST_DB = _TESTS_DIR / f".test_company_intel.{os.getpid()}.db"


def _remove_snapshot_files(base: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(str(base) + suffix).unlink(missing_ok=True)
        except OSError:
            pass  # still locked by a live process; removed on a later run


def _snapshot_live_db() -> None:
    # best-effort cleanup of snapshots left behind by earlier runs
    for old in _TESTS_DIR.glob(".test_company_intel*.db"):
        _remove_snapshot_files(old)
    if _LIVE_DB.exists():
        src = sqlite3.connect(f"file:{_LIVE_DB.as_posix()}?mode=ro", uri=True, timeout=30)
        dst = sqlite3.connect(_TEST_DB)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()


_snapshot_live_db()
atexit.register(_remove_snapshot_files, _TEST_DB)
_config.settings.DATABASE_URL = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
# Tests sign in as the built-in admin with a known password — only in the throwaway test DB
TEST_ADMIN_PASSWORD = "admin123"
_config.settings.ADMIN_PASSWORD = TEST_ADMIN_PASSWORD

# Imports below create the engine — they must come after the URL override.
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from main import app  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.init_db import init_db  # noqa: E402
from app.services.email_service import EmailService  # noqa: E402
from app.services.notification_service import notification_service  # noqa: E402

assert str(engine.url).endswith(_TEST_DB.name), "Tests must never run against the live database"


async def _prepare_schema():
    """Creates tables/seed on a fresh checkout where no live DB exists yet."""
    await init_db()
    async with AsyncSessionLocal() as db:
        await notification_service.seed_email_recipients_if_empty(db)
        # The snapshot carries the real admin password hash; tests use their own
        from sqlalchemy import update
        from app.core.security import get_password_hash
        from app.models.user import User
        await db.execute(update(User).where(User.email == "admin@aiindia.com")
                         .values(hashed_password=get_password_hash(TEST_ADMIN_PASSWORD)))
        await db.commit()
    await engine.dispose()  # don't leak pooled connections bound to this temporary loop


asyncio.run(_prepare_schema())

_REAL_SEND_SYNC = EmailService.__dict__["_send_sync"]


@pytest.fixture(autouse=True)
def _no_llm_email_compose(monkeypatch):
    """Alert emails and AI tool answers stay deterministic in tests unless a test opts in."""
    monkeypatch.setattr(_config.settings, "EMAIL_AI_COMPOSE", False)
    monkeypatch.setattr(_config.settings, "AI_EXPLAIN_TOOL_ANSWERS", False)


@pytest.fixture(autouse=True)
def email_outbox(monkeypatch):
    """In-memory SMTP replacement: every message a test 'sends' lands here."""
    outbox = []
    monkeypatch.setattr(EmailService, "_send_sync", staticmethod(lambda msg: outbox.append(msg)))
    return outbox


@pytest.fixture
def real_smtp_transport(monkeypatch, email_outbox):
    """Restores the real smtplib transport (use only with a local test SMTP server)."""
    monkeypatch.setattr(EmailService, "_send_sync", _REAL_SEND_SYNC)


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


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
