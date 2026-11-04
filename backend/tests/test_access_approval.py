"""
Access approval: self sign-ups (email or Google) see no company data until a
Super Admin or Company Management approves them; the request raises an URGENT
alert for the administrator.
"""
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.models.notification import Notification
from app.models.user import Role, User

API = "/api/v1"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _self_signup(anon_client) -> tuple[str, str]:
    email = f"applicant-{uuid.uuid4().hex[:8]}@example.com"
    res = await anon_client.post(API + "/auth/register", json={
        "email": email, "password": "Password123!", "first_name": "Asha", "last_name": "Applicant",
    })
    assert res.status_code == 200, res.text
    return email, res.json()["access_token"]


async def _user_id(db_session, email: str) -> str:
    return (await db_session.execute(select(User.id).where(User.email == email))).scalar_one()


async def _token_for_role(db_session, role_name: str) -> str:
    """Token of a fresh approved account holding `role_name`."""
    from app.core.security import get_password_hash
    role = (await db_session.execute(select(Role).where(Role.name == role_name))).scalar_one()
    u = User(id=str(uuid.uuid4()), email=f"rev-{role_name.lower()}-{uuid.uuid4().hex[:6]}@example.com",
             hashed_password=get_password_hash("x"), role_id=role.id, is_active=True)
    db_session.add(u)
    await db_session.commit()
    return create_access_token({"sub": u.id, "email": u.email, "role": role_name})


@pytest.mark.asyncio
async def test_self_signup_is_pending_and_sees_no_data(anon_client, db_session):
    email, token = await _self_signup(anon_client)

    me = await anon_client.get(API + "/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["approval_status"] == "PENDING"
    assert me.json()["role"]["name"] == "EMPLOYEE"

    for path in ("/projects/", "/tasks/", "/employees/", "/reports/overview", "/notifications/summary"):
        res = await anon_client.get(API + path, headers=_auth(token))
        assert res.status_code == 403, path
        assert res.json()["detail"] == "ACCOUNT_PENDING_APPROVAL"

    user_id = await _user_id(db_session, email)
    alert = (await db_session.execute(select(Notification).where(
        Notification.entity_type == "USER", Notification.entity_id == user_id))).scalars().first()
    assert alert is not None and alert.severity == "URGENT"
    assert "waiting for approval" in alert.title


@pytest.mark.asyncio
async def test_management_approves_with_role_then_dashboard_opens(anon_client, db_session):
    email, token = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    mgmt = await _token_for_role(db_session, "COMPANY_MANAGEMENT")

    res = await anon_client.put(API + f"/auth/users/{user_id}/approval",
                                json={"approve": True, "role": "TEAM_LEAD"}, headers=_auth(mgmt))
    assert res.status_code == 200, res.text
    assert res.json()["approval_status"] == "APPROVED"

    me = (await anon_client.get(API + "/auth/me", headers=_auth(token))).json()
    assert me["approval_status"] == "APPROVED" and me["role"]["name"] == "TEAM_LEAD"
    assert (await anon_client.get(API + "/projects/", headers=_auth(token))).status_code == 200


@pytest.mark.asyncio
async def test_management_cannot_grant_admin_roles(anon_client, db_session):
    email, _ = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    mgmt = await _token_for_role(db_session, "COMPANY_MANAGEMENT")
    for role in ("SUPER_ADMIN", "COMPANY_MANAGEMENT"):
        res = await anon_client.put(API + f"/auth/users/{user_id}/approval",
                                    json={"approve": True, "role": role}, headers=_auth(mgmt))
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_grant_management(client, anon_client, db_session):
    email, token = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    res = await client.put(API + f"/auth/users/{user_id}/approval",
                           json={"approve": True, "role": "COMPANY_MANAGEMENT"})
    assert res.status_code == 200
    me = (await anon_client.get(API + "/auth/me", headers=_auth(token))).json()
    assert me["role"]["name"] == "COMPANY_MANAGEMENT"


@pytest.mark.asyncio
async def test_declined_user_stays_locked_out(client, anon_client, db_session):
    email, token = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    res = await client.put(API + f"/auth/users/{user_id}/approval", json={"approve": False})
    assert res.status_code == 200
    me = (await anon_client.get(API + "/auth/me", headers=_auth(token))).json()
    assert me["approval_status"] == "REJECTED"
    res = await anon_client.get(API + "/projects/", headers=_auth(token))
    assert res.status_code == 403 and res.json()["detail"] == "ACCOUNT_REJECTED"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["EMPLOYEE", "TEAM_LEAD", "PROJECT_MANAGER"])
async def test_non_admin_roles_cannot_approve(anon_client, db_session, role):
    email, _ = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    reviewer = await _token_for_role(db_session, role)
    res = await anon_client.put(API + f"/auth/users/{user_id}/approval",
                                json={"approve": True}, headers=_auth(reviewer))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_pending_user_cannot_approve_themselves(anon_client):
    email, token = await _self_signup(anon_client)
    me = (await anon_client.get(API + "/auth/me", headers=_auth(token))).json()
    res = await anon_client.put(API + f"/auth/users/{me['id']}/approval",
                                json={"approve": True, "role": "SUPER_ADMIN"}, headers=_auth(token))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_password_signup_with_owner_email_gets_no_admin_rights(anon_client, db_session):
    """An unverified password sign-up never becomes SUPER_ADMIN, whatever the email."""
    email = f"anil.aiindia+{uuid.uuid4().hex[:6]}@gmail.com"
    res = await anon_client.post(API + "/auth/register", json={
        "email": email, "password": "Password123!", "first_name": "X", "last_name": "Y"})
    me = (await anon_client.get(API + "/auth/me", headers=_auth(res.json()["access_token"]))).json()
    assert me["role"]["name"] == "EMPLOYEE" and me["approval_status"] == "PENDING"


@pytest.mark.asyncio
async def test_account_created_by_admin_is_approved_immediately(client):
    email = f"added-by-admin-{uuid.uuid4().hex[:6]}@example.com"
    res = await client.post(API + "/auth/register", json={
        "email": email, "password": "Password123!", "first_name": "New", "last_name": "Hire"})
    assert res.status_code == 200
    users = (await client.get(API + "/auth/users")).json()
    assert next(u for u in users if u["email"] == email)["approval_status"] == "APPROVED"


@pytest.mark.asyncio
async def test_new_google_account_is_pending(anon_client, monkeypatch):
    email = f"google-{uuid.uuid4().hex[:6]}@gmail.com"
    payload = {"aud": settings.GOOGLE_CLIENT_ID or "mock", "email": email, "email_verified": "true",
               "given_name": "Gia", "family_name": "Google", "name": "Gia Google"}

    import httpx
    real_get = httpx.AsyncClient.get

    async def fake_get(self, url, *args, **kwargs):
        if "oauth2.googleapis.com" in str(url):
            m = MagicMock()
            m.status_code = 200
            m.json.return_value = payload
            return m
        return await real_get(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    res = await anon_client.post(API + "/auth/google", json={"id_token": "mock"})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    me = (await anon_client.get(API + "/auth/me", headers=_auth(token))).json()
    assert me["approval_status"] == "PENDING"
    assert (await anon_client.get(API + "/projects/", headers=_auth(token))).status_code == 403


# ----------------------------- deployment hardening ----------------------------- #
def test_published_or_weak_secret_key_is_rejected():
    from pydantic import ValidationError
    from app.core.config import Settings
    for bad in ("", "short", "cip-super-secret-production-key-change-in-env-2026-xyz"):
        with pytest.raises(ValidationError):
            Settings(SECRET_KEY=bad, _env_file=None)


@pytest.mark.asyncio
async def test_default_admin_password_is_replaced(db_session, monkeypatch):
    from app.core import init_db as init_mod
    from app.core.security import get_password_hash, verify_password
    admin = (await db_session.execute(select(User).where(User.email == "admin@aiindia.com"))).scalar_one()
    original = admin.hashed_password
    try:
        admin.hashed_password = get_password_hash("admin123")
        await db_session.commit()
        monkeypatch.setattr(init_mod.settings, "ADMIN_PASSWORD", "a-strong-configured-password")
        await init_mod.secure_builtin_admin(db_session)
        await db_session.refresh(admin)
        assert not verify_password("admin123", admin.hashed_password)
        assert verify_password("a-strong-configured-password", admin.hashed_password)
    finally:
        admin.hashed_password = original
        await db_session.commit()


def test_migration_puts_existing_non_admin_accounts_in_review(tmp_path):
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from app.core.config import BACKEND_DIR

    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0003")
        for rid, name in (("r1", "SUPER_ADMIN"), ("r2", "COMPANY_MANAGEMENT"), ("r3", "EMPLOYEE")):
            conn.execute(sa.text("INSERT INTO roles (id, name, permissions, created_at) VALUES (:i, :n, '[]', CURRENT_TIMESTAMP)"), {"i": rid, "n": name})
        for uid, rid in (("u1", "r1"), ("u2", "r2"), ("u3", "r3")):
            conn.execute(sa.text("INSERT INTO users (id, email, hashed_password, role_id, is_active, created_at, updated_at) "
                                 "VALUES (:u, :e, 'x', :r, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"), {"u": uid, "e": f"{uid}@example.com", "r": rid})
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0004")
    with engine.connect() as conn:
        status = dict(conn.execute(sa.text("SELECT id, approval_status FROM users")).all())
    engine.dispose()
    assert status == {"u1": "APPROVED", "u2": "APPROVED", "u3": "PENDING"}


# --------------------- displayed title == role assigned by an admin --------------------- #
async def _employee_title(db_session, email: str) -> str:
    from app.models.employee import Employee
    db_session.expire_all()
    return (await db_session.execute(select(Employee.job_title).where(Employee.email == email))).scalar_one()


@pytest.mark.asyncio
async def test_signup_cannot_choose_its_own_title(anon_client, db_session):
    email = f"titled-{uuid.uuid4().hex[:6]}@example.com"
    await anon_client.post(API + "/auth/register", json={
        "email": email, "password": "Password123!", "first_name": "T", "last_name": "U",
        "job_title": "CTO", "department": "Board"})
    assert await _employee_title(db_session, email) == "Employee"


@pytest.mark.asyncio
async def test_title_follows_approval_and_every_role_change(client, anon_client, db_session):
    email, _ = await _self_signup(anon_client)
    user_id = await _user_id(db_session, email)
    await client.put(API + f"/auth/users/{user_id}/approval", json={"approve": True, "role": "TEAM_LEAD"})
    assert await _employee_title(db_session, email) == "Team Lead"
    for role, label in (("PROJECT_MANAGER", "Project Manager"), ("EMPLOYEE", "Employee"),
                        ("COMPANY_MANAGEMENT", "Company Management")):
        res = await client.put(API + f"/auth/users/{user_id}/role", json={"role": role})
        assert res.status_code == 200
        assert await _employee_title(db_session, email) == label


@pytest.mark.asyncio
async def test_pending_signup_not_listed_as_employee(client, anon_client, db_session):
    email, _ = await _self_signup(anon_client)
    people = {e["email"] for e in (await client.get(API + "/employees/")).json()}
    assert email not in people


@pytest.mark.asyncio
async def test_startup_sweep_aligns_titles(db_session):
    from app.core.roles import sync_role_titles, NO_PLATFORM_ROLE
    from app.models.employee import Employee
    stray = Employee(id=str(uuid.uuid4()), employee_number=f"T-{uuid.uuid4().hex[:8]}", first_name="R",
                     last_name="M", email=f"redmine-only-{uuid.uuid4().hex[:6]}@example.com",
                     job_title="Lead Architect & Administrator", department="Engineering")
    db_session.add(stray)
    await db_session.commit()
    await sync_role_titles(db_session)
    assert await _employee_title(db_session, stray.email) == NO_PLATFORM_ROLE
    admin_title = await _employee_title(db_session, "admin@aiindia.com")
    assert admin_title == "Super Admin"


def test_migration_renames_root_admin(tmp_path):
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from app.core.config import BACKEND_DIR

    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0004")
        conn.execute(sa.text("INSERT INTO roles (id, name, permissions, created_at) VALUES ('r1', 'SUPER_ADMIN', '[]', CURRENT_TIMESTAMP)"))
        conn.execute(sa.text("INSERT INTO users (id, email, hashed_password, role_id, is_active, approval_status, created_at, updated_at) "
                             "VALUES ('root', 'admin@company.com', 'x', 'r1', 1, 'APPROVED', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
        conn.execute(sa.text("INSERT INTO employees (id, user_id, employee_number, first_name, last_name, email, job_title, department, hire_date, status, weekly_capacity_hours, created_at, updated_at) "
                             "VALUES ('e1', 'root', 'EMP-001', 'Anil', 'Abhange', 'admin@company.com', 'Super Admin', 'Engineering', CURRENT_DATE, 'ACTIVE', 40, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0005")
    with engine.connect() as conn:
        assert conn.execute(sa.text("SELECT id FROM users WHERE email='admin@aiindia.com'")).scalar() == "root"
        assert conn.execute(sa.text("SELECT email FROM employees WHERE id='e1'")).scalar() == "admin@aiindia.com"
    engine.dispose()


@pytest.mark.asyncio
async def test_root_admin_password_comes_from_env(db_session, monkeypatch):
    from app.core import init_db as init_mod
    from app.core.security import verify_password
    admin = (await db_session.execute(select(User).where(User.email == "admin@aiindia.com"))).scalar_one()
    original = admin.hashed_password
    try:
        monkeypatch.setattr(init_mod.settings, "ADMIN_PASSWORD", "Rotated#Pass123")
        await init_mod.secure_builtin_admin(db_session)
        await db_session.refresh(admin)
        assert verify_password("Rotated#Pass123", admin.hashed_password)
    finally:
        admin.hashed_password = original
        await db_session.commit()


@pytest.mark.asyncio
async def test_root_admin_is_protected(client):
    users = (await client.get(API + "/auth/users")).json()
    root = next(u for u in users if u["email"] == "admin@aiindia.com")
    assert (await client.put(API + f"/auth/users/{root['id']}/role", json={"role": "EMPLOYEE"})).status_code == 400
