"""
Email automation & follow-ups:
  - automatic retry of temporarily failed alert emails
  - alert routing to the task assignee / project manager
  - daily digest + weekly report (PDF) scheduling, idempotency and AI-number guard
  - Administration endpoints for the above
  - employee profile endpoint
  - Alembic migrations match the models
  - legacy company dashboard has no fabricated activity
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.core.config import settings
from app.models.alert_config import AlertEmailRecipient, AlertRecipientConfig, ScheduledEmailRun
from app.models.employee import Employee
from app.models.notification import Notification, NotificationDelivery
from app.models.project import Project
from app.models.redmine_sync import RedmineMapping
from app.models.task import Task
from app.services import scheduled_reports as sr
from app.services.email_service import EmailService, REASON_ASSIGNEE, REASON_MANAGER
from app.services.notification_service import MAX_EMAIL_ATTEMPTS, notification_service

ADMIN_EMAIL = "anil.aiindia@gmail.com"
IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------- #
#  Fixtures                                                               #
# ---------------------------------------------------------------------- #
@pytest.fixture
def smtp_configured(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "alerts@company-test.io")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "test-app-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")


@pytest_asyncio.fixture(autouse=True)
async def baseline(db_session):
    """One admin recipient, routing off, schedule at defaults; scheduled-run log cleared."""
    await db_session.execute(delete(AlertEmailRecipient))
    db_session.add(AlertEmailRecipient(email=ADMIN_EMAIL, name="Anil (Administrator)",
                                       notify_scope="URGENT_CRITICAL", is_active=True))
    await db_session.execute(delete(ScheduledEmailRun))
    cfg = await _config(db_session)
    cfg.email_enabled, cfg.in_app_enabled = True, True
    cfg.notify_assignee = cfg.notify_project_manager = False
    cfg.daily_digest_enabled = cfg.weekly_report_enabled = True
    cfg.digest_hour, cfg.weekly_report_weekday = 9, 0
    await db_session.commit()
    yield


async def _config(db) -> AlertRecipientConfig:
    cfg = (await db.execute(select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True)
                            .limit(1))).scalars().first()
    assert cfg is not None
    return cfg


@pytest_asyncio.fixture
async def people(db_session):
    """A Redmine-mapped assignee + manager, a non-Redmine employee, one project and one task."""
    tag = uuid.uuid4().hex[:8]

    def emp(name, mapped):
        e = Employee(employee_number=f"T-{tag}-{name}", first_name=name, last_name="tester",
                     email=f"{name}.{tag}@company-test.io", job_title="Engineer", department="QA", status="ACTIVE")
        db_session.add(e)
        return e, mapped

    assignee, _ = emp("assignee", True)
    manager, _ = emp("manager", True)
    outsider, _ = emp("outsider", False)
    await db_session.flush()
    for e, rid in ((assignee, 900001), (manager, 900002)):
        db_session.add(RedmineMapping(entity_type="USER", redmine_id=rid, internal_id=e.id))
    project = Project(name=f"Routing test {tag}", code=f"RT-{tag}", status="ACTIVE", project_manager_id=manager.id)
    db_session.add(project)
    await db_session.flush()
    task = Task(project_id=project.id, assigned_to_id=assignee.id, title=f"#9{tag[:3]}: routing test",
                status="New", priority="Normal")
    db_session.add(task)
    await db_session.commit()
    yield {"assignee": assignee, "manager": manager, "outsider": outsider, "project": project, "task": task}

    ids = select(Notification.id).where(Notification.entity_id.in_([task.id, project.id]))
    await db_session.execute(delete(NotificationDelivery).where(NotificationDelivery.notification_id.in_(ids)))
    await db_session.execute(delete(Notification).where(Notification.entity_id.in_([task.id, project.id])))
    await db_session.execute(delete(Task).where(Task.id == task.id))
    await db_session.execute(delete(Project).where(Project.id == project.id))
    await db_session.execute(delete(RedmineMapping).where(RedmineMapping.internal_id.in_([assignee.id, manager.id])))
    await db_session.execute(delete(Employee).where(Employee.id.in_([assignee.id, manager.id, outsider.id])))
    await db_session.commit()


async def _email_deliveries(db, notification_id):
    return (await db.execute(select(NotificationDelivery).where(
        NotificationDelivery.notification_id == notification_id,
        NotificationDelivery.channel == "EMAIL_SMTP"))).scalars().all()


async def _drop_notification(db, n):
    await db.execute(delete(NotificationDelivery).where(NotificationDelivery.notification_id == n.id))
    await db.execute(delete(Notification).where(Notification.id == n.id))
    await db.commit()


# ---------------------------------------------------------------------- #
#  Retry                                                                  #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_temporary_failure_is_retried_and_delivered(db_session, smtp_configured, monkeypatch, email_outbox):
    calls = {"n": 0}

    def flaky(msg):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("connection reset")
        email_outbox.append(msg)

    monkeypatch.setattr(EmailService, "_send_sync", staticmethod(flaky))
    n = await notification_service.create_and_dispatch(db_session, title="Retry me", message="m", severity="URGENT")
    (d,) = await _email_deliveries(db_session, n.id)
    assert d.status == "RETRYING" and d.attempt_count == 1 and d.next_retry_at is not None
    assert "retry automatically" in d.error_message

    # not due yet → nothing happens
    assert await notification_service.retry_pending_emails(db_session) == 0
    d.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()
    assert await notification_service.retry_pending_emails(db_session) == 1
    await db_session.refresh(d)
    assert d.status == "SENT" and d.attempt_count == 2 and d.delivered_at is not None and d.next_retry_at is None
    assert len(email_outbox) == 1
    await _drop_notification(db_session, n)


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts(db_session, smtp_configured, monkeypatch):
    def always_down(msg):
        raise OSError("network unreachable")

    monkeypatch.setattr(EmailService, "_send_sync", staticmethod(always_down))
    n = await notification_service.create_and_dispatch(db_session, title="Never", message="m", severity="CRITICAL")
    (d,) = await _email_deliveries(db_session, n.id)
    for _ in range(MAX_EMAIL_ATTEMPTS - 1):
        assert d.status == "RETRYING"
        d.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db_session.commit()
        await notification_service.retry_pending_emails(db_session)
        await db_session.refresh(d)
    assert d.status == "FAILED" and d.attempt_count == MAX_EMAIL_ATTEMPTS
    assert "Gave up" in d.error_message and d.next_retry_at is None
    await _drop_notification(db_session, n)


@pytest.mark.asyncio
async def test_rejected_address_is_not_retried(db_session, smtp_configured, monkeypatch):
    import smtplib

    def refused(msg):
        raise smtplib.SMTPRecipientsRefused({ADMIN_EMAIL: (550, b"no such user")})

    monkeypatch.setattr(EmailService, "_send_sync", staticmethod(refused))
    n = await notification_service.create_and_dispatch(db_session, title="Bad address", message="m", severity="URGENT")
    (d,) = await _email_deliveries(db_session, n.id)
    assert d.status == "FAILED" and d.next_retry_at is None
    await _drop_notification(db_session, n)


# ---------------------------------------------------------------------- #
#  Routing to assignee / project manager                                  #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_routing_off_by_default(db_session, smtp_configured, people, email_outbox):
    n = await notification_service.create_and_dispatch(
        db_session, title="Overdue Task: routing", message="m", severity="CRITICAL",
        entity_type="TASK", entity_id=people["task"].id)
    assert {d.destination for d in await _email_deliveries(db_session, n.id)} == {ADMIN_EMAIL}


@pytest.mark.asyncio
async def test_routing_to_assignee_and_manager(db_session, smtp_configured, people, email_outbox):
    cfg = await _config(db_session)
    cfg.notify_assignee = cfg.notify_project_manager = True
    await db_session.commit()
    n = await notification_service.create_and_dispatch(
        db_session, title="Overdue Task: routing", message="m", severity="CRITICAL",
        entity_type="TASK", entity_id=people["task"].id)
    dests = {d.destination for d in await _email_deliveries(db_session, n.id)}
    assert dests == {ADMIN_EMAIL, people["assignee"].email, people["manager"].email}

    by_to = {m["To"]: m for m in email_outbox}
    assignee_msg = next(m for t, m in by_to.items() if people["assignee"].email in t)
    manager_msg = next(m for t, m in by_to.items() if people["manager"].email in t)
    assert REASON_ASSIGNEE in assignee_msg.get_body(("plain",)).get_content()
    assert REASON_MANAGER in manager_msg.get_body(("plain",)).get_content()


@pytest.mark.asyncio
async def test_routing_skips_info_and_non_redmine_people(db_session, smtp_configured, people, email_outbox):
    cfg = await _config(db_session)
    cfg.notify_assignee = cfg.notify_project_manager = True
    people["task"].assigned_to_id = people["outsider"].id   # not a Redmine user → never emailed
    await db_session.commit()
    n = await notification_service.create_and_dispatch(
        db_session, title="Overdue Task: routing", message="m", severity="URGENT",
        entity_type="TASK", entity_id=people["task"].id)
    dests = {d.destination for d in await _email_deliveries(db_session, n.id)}
    assert dests == {ADMIN_EMAIL, people["manager"].email}

    info = await notification_service.create_and_dispatch(
        db_session, title="Task Completed: routing", message="m", severity="INFO",
        entity_type="TASK", entity_id=people["task"].id)
    assert await _email_deliveries(db_session, info.id) == []


@pytest.mark.asyncio
async def test_project_alert_goes_to_project_manager(db_session, smtp_configured, people):
    cfg = await _config(db_session)
    cfg.notify_project_manager = True
    await db_session.commit()
    n = await notification_service.create_and_dispatch(
        db_session, title="Project Health Alert: x", message="m", severity="URGENT",
        entity_type="PROJECT", entity_id=people["project"].id)
    assert {d.destination for d in await _email_deliveries(db_session, n.id)} == {ADMIN_EMAIL, people["manager"].email}


# ---------------------------------------------------------------------- #
#  Daily digest / weekly report                                           #
# ---------------------------------------------------------------------- #
def test_schedule_windows():
    cfg = AlertRecipientConfig(email_enabled=True, daily_digest_enabled=True, weekly_report_enabled=True,
                               digest_hour=9, weekly_report_weekday=0)
    monday_930 = datetime(2026, 11, 2, 9, 30, tzinfo=IST)
    assert sr.is_due(sr.KIND_DAILY, cfg, monday_930) and sr.is_due(sr.KIND_WEEKLY, cfg, monday_930)
    assert not sr.is_due(sr.KIND_DAILY, cfg, monday_930.replace(hour=8))            # too early
    assert not sr.is_due(sr.KIND_DAILY, cfg, monday_930.replace(hour=16))           # window passed
    assert not sr.is_due(sr.KIND_WEEKLY, cfg, datetime(2026, 11, 3, 9, 30, tzinfo=IST))  # Tuesday
    assert not sr.is_due(sr.KIND_DAILY, cfg, datetime(2026, 11, 8, 9, 30, tzinfo=IST))   # Sunday
    cfg.daily_digest_enabled = False
    assert not sr.is_due(sr.KIND_DAILY, cfg, monday_930)
    cfg.email_enabled = False
    assert not sr.is_due(sr.KIND_WEEKLY, cfg, monday_930)
    assert sr.period_key(sr.KIND_WEEKLY, monday_930) == "2026-W45"


@pytest.mark.asyncio
async def test_run_due_sends_once_per_period(db_session, smtp_configured, monkeypatch, email_outbox):
    monkeypatch.setattr(sr, "local_now", lambda: datetime(2026, 11, 2, 9, 5, tzinfo=IST))  # Monday 09:05
    done = await sr.run_due(db_session)
    assert len(done) == 2 and all("SENT (1/1)" in line for line in done)
    subjects = sorted(m["Subject"] for m in email_outbox)
    assert subjects[0].startswith("Daily digest") and subjects[1].startswith("Weekly report")
    weekly = next(m for m in email_outbox if m["Subject"].startswith("Weekly report"))
    pdfs = [p for p in weekly.iter_attachments() if p.get_content_type() == "application/pdf"]
    assert len(pdfs) == 1 and pdfs[0].get_content()[:4] == b"%PDF"

    # a restart in the same window must not send again
    assert await sr.run_due(db_session) == []
    assert len(email_outbox) == 2


@pytest.mark.asyncio
async def test_run_due_noop_without_email_setup(db_session, monkeypatch, email_outbox):
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(sr, "local_now", lambda: datetime(2026, 11, 2, 9, 5, tzinfo=IST))
    assert await sr.run_due(db_session) == []
    assert email_outbox == []


def test_ai_summary_number_guard():
    facts = '{"overdue": 2, "open": 3, "days_overdue": 22}'
    assert sr.numbers_grounded("2 of 3 tasks are overdue, the oldest by 22 days.", facts)
    assert not sr.numbers_grounded("17 tasks are overdue.", facts)


@pytest.mark.asyncio
async def test_digest_content_uses_live_figures(db_session):
    built = await sr.build(db_session, sr.KIND_DAILY)
    f = built["facts"]
    assert set(f) >= {"right_now", "since_yesterday", "overdue", "due_soon", "projects_needing_attention", "free_today"}
    subject, body, text = sr.render_daily(f, built["summary"], "Hi Anil,", built["label"])
    assert f'{f["right_now"]["overdue_tasks"]} overdue' in subject
    assert "Open Dashboard" in body and "SMTP" not in body and "OpenRouter" not in body


# ---------------------------------------------------------------------- #
#  Administration endpoints                                               #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_email_automation_endpoints(client, admin_token, people, smtp_configured, email_outbox):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = await client.get("/api/v1/admin/email-automation", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["routing"] == {"notify_assignee": False, "notify_project_manager": False}
    assert body["schedule"]["digest_hour"] == 9 and body["schedule"]["timezone"] == settings.APP_TIMEZONE
    assert any(p["id"] == people["project"].id for p in body["projects"])
    names = {p["id"] for p in body["people"]}
    assert people["assignee"].id in names and people["outsider"].id not in names

    r = await client.put("/api/v1/admin/email-automation", headers=h,
                         json={"notify_assignee": True, "digest_hour": 8, "weekly_report_weekday": 4})
    assert r.status_code == 200
    assert r.json()["routing"]["notify_assignee"] is True and r.json()["schedule"]["digest_hour"] == 8
    assert (await client.put("/api/v1/admin/email-automation", headers=h, json={"digest_hour": 30})).status_code == 422

    url = f"/api/v1/admin/projects/{people['project'].id}/manager"
    assert (await client.put(url, headers=h, json={"employee_id": people["outsider"].id})).status_code == 422
    r = await client.put(url, headers=h, json={"employee_id": people["assignee"].id})
    assert r.status_code == 200 and r.json()["manager_id"] == people["assignee"].id
    assert (await client.put(url, headers=h, json={"employee_id": None})).json()["manager_id"] is None

    r = await client.post("/api/v1/admin/email-automation/send-now", headers=h, json={"kind": "daily"})
    assert r.status_code == 200 and r.json()["success"] is True
    assert len(email_outbox) == 1 and email_outbox[0]["Subject"].startswith("Daily digest")
    runs = (await client.get("/api/v1/admin/email-automation", headers=h)).json()["last_runs"]
    assert runs["DAILY_DIGEST"]["manual"] is True and runs["DAILY_DIGEST"]["sent_count"] == 1


# ---------------------------------------------------------------------- #
#  Employee profile                                                       #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_employee_profile(client, admin_token, people):
    h = {"Authorization": f"Bearer {admin_token}"}
    r = await client.get(f"/api/v1/employees/{people['assignee'].id}/profile", headers=h)
    assert r.status_code == 200
    p = r.json()
    assert p["employee"]["name"] == "Assignee Tester"
    assert p["stats"]["open_tasks"] == 1 and p["stats"]["projects_count"] == 1
    assert len(p["weekly"]) == 12 and len(p["monthly"]) == 12
    assert p["open_tasks"][0]["title"] == people["task"].title
    assert p["ranking"] is not None and p["ranking"]["of"] >= 2

    m = (await client.get(f"/api/v1/employees/{people['manager'].id}/profile", headers=h)).json()
    assert m["projects"][0]["is_manager"] is True
    assert (await client.get("/api/v1/employees/does-not-exist/profile", headers=h)).status_code == 404


# ---------------------------------------------------------------------- #
#  Migrations & legacy endpoint                                           #
# ---------------------------------------------------------------------- #
def test_migrations_build_the_model_schema(tmp_path):
    """A fresh database built only by Alembic migrations matches the SQLAlchemy models exactly."""
    import sqlalchemy as sa
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from app.core.config import BACKEND_DIR
    from app.models import Base

    engine = sa.create_engine(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    with engine.begin() as conn:
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        assert diff == []
        assert conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == "0005"
    engine.dispose()


@pytest.mark.asyncio
async def test_company_dashboard_has_no_fabricated_activity(client, admin_token):
    r = await client.get("/api/v1/company/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    acts = r.json()["recent_activities"]
    assert not any(a["id"] in ("a1", "a2", "a3") for a in acts)
    assert not any("Delta Sync Processed" in a["title"] for a in acts)
