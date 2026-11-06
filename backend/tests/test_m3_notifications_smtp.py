"""
Milestone 3 — Notification Engine & SMTP Email Alerting.

Runs against the isolated test DB snapshot (see conftest.py). Email delivery is
verified two ways:
  * in-memory outbox (default, autouse) for pipeline/routing behaviour
  * a real SMTP protocol exchange with a throwaway local SMTP server
    (LocalSMTPServer below — a test fixture, not production code)
"""
import base64
import socket
import socketserver
import threading
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alert_config import AlertRecipientConfig, AlertEmailRecipient
from app.models.notification import Notification, NotificationDelivery
from app.models.project import Project
from app.models.task import Task
from app.services.email_service import email_service, EmailService
from app.services.notification_service import (
    notification_service, categorize, PREFIX_COMPLETED, PREFIX_OVERDUE,
)

ADMIN_EMAIL = "connect.aiindia@gmail.com"


# ---------------------------------------------------------------------- #
#  Fixtures                                                               #
# ---------------------------------------------------------------------- #
@pytest.fixture
def smtp_configured(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setattr(settings, "SMTP_USERNAME", "alerts@test.invalid")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "test-app-password")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")


@pytest_asyncio.fixture(autouse=True)
async def only_admin_recipient(db_session):
    """Every test starts with exactly one email recipient: the admin, urgent & critical only."""
    await db_session.execute(delete(AlertEmailRecipient))
    db_session.add(AlertEmailRecipient(email=ADMIN_EMAIL, name="Administrator",
                                       notify_scope="URGENT_CRITICAL", is_active=True))
    await db_session.commit()
    yield


async def _add_recipient(db: AsyncSession, email: str, scope: str = "ALL", active: bool = True):
    r = AlertEmailRecipient(email=email, name=email.split("@")[0], notify_scope=scope, is_active=active)
    db.add(r)
    await db.commit()
    return r


async def _reset_recipient(db: AsyncSession, **overrides):
    cfg = (await db.execute(
        select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True).limit(1)
    )).scalars().first()
    assert cfg is not None
    cfg.recipient_email = overrides.get("recipient_email", ADMIN_EMAIL)
    cfg.in_app_enabled = overrides.get("in_app_enabled", True)
    cfg.email_enabled = overrides.get("email_enabled", True)
    await db.commit()
    return cfg


async def _deliveries(db: AsyncSession, notification_id: str) -> list[NotificationDelivery]:
    return (await db.execute(
        select(NotificationDelivery).where(NotificationDelivery.notification_id == notification_id)
    )).scalars().all()


async def _cleanup_entity(db: AsyncSession, entity_id: str):
    ids = select(Notification.id).where(Notification.entity_id == entity_id)
    await db.execute(delete(NotificationDelivery).where(NotificationDelivery.notification_id.in_(ids)))
    await db.execute(delete(Notification).where(Notification.entity_id == entity_id))
    await db.execute(delete(Task).where(Task.id == entity_id))
    await db.commit()


class _SMTPHandler(socketserver.StreamRequestHandler):
    """Minimal RFC 5321 server: EHLO, AUTH PLAIN, MAIL, RCPT, DATA, QUIT."""

    def _reply(self, line: str):
        self.wfile.write((line + "\r\n").encode())

    def handle(self):
        srv = self.server
        self._reply("220 local-test-smtp ready")
        while True:
            raw = self.rfile.readline()
            if not raw:
                return
            line = raw.decode(errors="replace").rstrip("\r\n")
            cmd = line.upper()
            if cmd.startswith("EHLO") or cmd.startswith("HELO"):
                self._reply("250-local-test-smtp")
                self._reply("250 AUTH PLAIN")
            elif cmd.startswith("AUTH PLAIN"):
                parts = line.split(" ", 2)
                creds = base64.b64decode(parts[2]).split(b"\0") if len(parts) == 3 else []
                srv.auth.append([c.decode() for c in creds])
                ok = len(creds) == 3 and creds[2].decode() == srv.expected_password
                self._reply("235 2.7.0 Authentication successful" if ok else "535 5.7.8 Bad credentials")
            elif cmd.startswith("MAIL FROM"):
                srv.mail_from.append(line[10:].strip())
                self._reply("250 OK")
            elif cmd.startswith("RCPT TO"):
                srv.rcpt_to.append(line[8:].strip())
                self._reply("250 OK")
            elif cmd == "DATA":
                self._reply("354 End data with <CR><LF>.<CR><LF>")
                chunks = []
                while True:
                    d = self.rfile.readline()
                    if d in (b".\r\n", b".\n", b""):
                        break
                    chunks.append(d)
                srv.messages.append(b"".join(chunks).decode(errors="replace"))
                self._reply("250 OK queued")
            elif cmd == "QUIT":
                self._reply("221 Bye")
                return
            else:
                self._reply("250 OK")


class LocalSMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, expected_password: str):
        super().__init__(("127.0.0.1", 0), _SMTPHandler)
        self.expected_password = expected_password
        self.auth, self.mail_from, self.rcpt_to, self.messages = [], [], [], []


@pytest.fixture
def local_smtp(monkeypatch, real_smtp_transport):
    server = LocalSMTPServer(expected_password="local-app-password")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", server.server_address[1])
    monkeypatch.setattr(settings, "SMTP_USERNAME", "alerts@local.test")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "local-app-password")
    monkeypatch.setattr(settings, "SMTP_USE_STARTTLS", False)
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 5.0)
    yield server
    server.shutdown()
    server.server_close()


# ---------------------------------------------------------------------- #
#  Unit: categorisation & message                                         #
# ---------------------------------------------------------------------- #
def test_categorize_maps_severity_and_completion():
    assert categorize("CRITICAL", "Overdue Task: x") == "critical"
    assert categorize("URGENT", "Project Health Alert: y") == "urgent"
    assert categorize("INFO", f"{PREFIX_COMPLETED}: z") == "completed"
    assert categorize("CRITICAL", f"{PREFIX_COMPLETED}: z") == "completed"
    assert categorize("WARNING", "Deadline Warning: w") == "info"
    assert categorize("INFO", "anything") == "info"


def test_alert_email_message_contents(smtp_configured):
    msg = EmailService.build_alert_message(
        to_email=ADMIN_EMAIL, to_name="Administrator", title="Overdue Task: <Deploy>",
        message="Due 2026-10-01 & late", severity="CRITICAL", entity_type="TASK",
        created_at_label="2026-11-03 10:00 UTC", deep_link="http://localhost:3000/?id=1&x=2",
    )
    assert msg["Subject"] == "Overdue Task: <Deploy>"
    assert ADMIN_EMAIL in msg["To"]
    assert "alerts@test.invalid" in msg["From"]
    assert msg["X-Priority"] == "1"
    text = msg.get_body(preferencelist=("plain",)).get_content()
    html = msg.get_body(preferencelist=("html",)).get_content()
    assert "Due 2026-10-01 & late" in text and "http://localhost:3000/?id=1&x=2" in text
    assert "&lt;Deploy&gt;" in html and "<Deploy>" not in html          # HTML-escaped
    assert 'href="http://localhost:3000/?id=1&amp;x=2"' in html


@pytest.mark.asyncio
async def test_send_returns_not_configured_without_credentials(monkeypatch, email_outbox):
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    res = await email_service.send_alert(ADMIN_EMAIL, "Administrator", "t", "m", "URGENT", "TASK", "now", "http://x")
    assert res.success is False and res.status == "NOT_CONFIGURED"
    assert email_outbox == []


# ---------------------------------------------------------------------- #
#  Real SMTP protocol exchange (local throwaway server)                   #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_real_smtp_protocol_delivery_to_admin(local_smtp):
    res = await email_service.send_alert(
        ADMIN_EMAIL, "Administrator", "Blocker Alert: ANPR pipeline", "Task is blocked",
        "CRITICAL", "TASK", "2026-11-03 10:00 UTC", "http://localhost:3000/?notifications=open",
    )
    assert res.success is True, res.detail
    assert res.status == "SENT"
    assert local_smtp.auth == [["", "alerts@local.test", "local-app-password"]]
    assert local_smtp.rcpt_to and ADMIN_EMAIL in local_smtp.rcpt_to[0]
    assert "Subject: Blocker Alert: ANPR pipeline" in local_smtp.messages[0]


@pytest.mark.asyncio
async def test_real_smtp_bad_password_reports_auth_failure(local_smtp, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "wrong-password")
    res = await email_service.send_alert(ADMIN_EMAIL, "Administrator", "t", "m", "URGENT", "TASK", "now", "http://x")
    assert res.success is False and res.status == "FAILED"
    assert "rejected the sign-in" in res.detail
    assert local_smtp.messages == []


@pytest.mark.asyncio
async def test_unreachable_smtp_server_is_recorded_as_failed(monkeypatch, real_smtp_transport):
    with socket.socket() as s:            # grab a free port with nothing listening
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setattr(settings, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "SMTP_PORT", port)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "u@x")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(settings, "SMTP_USE_STARTTLS", False)
    monkeypatch.setattr(settings, "SMTP_TIMEOUT_SECONDS", 3.0)
    res = await email_service.send_alert(ADMIN_EMAIL, "Administrator", "t", "m", "URGENT", "TASK", "now", "http://x")
    assert res.success is False and res.status == "FAILED"


# ---------------------------------------------------------------------- #
#  Dispatch pipeline                                                      #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize("severity", ["URGENT", "CRITICAL"])
async def test_urgent_and_critical_are_emailed_to_admin(db_session, smtp_configured, email_outbox, severity):
    await _reset_recipient(db_session)
    n = await notification_service.create_and_dispatch(
        db_session, title=f"M3 {severity} check", message="pipeline test", severity=severity,
        entity_type="SYSTEM",
    )
    try:
        d = {x.channel: x for x in await _deliveries(db_session, n.id)}
        assert d["IN_APP"].status == "SENT"
        assert d["EMAIL_SMTP"].status == "SENT"
        assert d["EMAIL_SMTP"].destination == ADMIN_EMAIL
        assert "GOOGLE_CHAT_ADMIN" not in d
        assert len(email_outbox) == 1
        assert ADMIN_EMAIL in email_outbox[0]["To"]
        assert email_outbox[0]["Subject"].startswith({"CRITICAL": "Action needed:", "URGENT": "Attention:"}[severity])
        assert "[CIP" not in email_outbox[0]["Subject"]
        assert f"id={n.id}" in email_outbox[0].get_body(preferencelist=("plain",)).get_content()
    finally:
        await db_session.execute(delete(NotificationDelivery).where(NotificationDelivery.notification_id == n.id))
        await db_session.execute(delete(Notification).where(Notification.id == n.id))
        await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("severity", ["INFO", "WARNING"])
async def test_info_and_warning_stay_in_app_only(db_session, smtp_configured, email_outbox, severity):
    await _reset_recipient(db_session)
    n = await notification_service.create_and_dispatch(db_session, title="M3 low", message="m", severity=severity)
    channels = [x.channel for x in await _deliveries(db_session, n.id)]
    assert channels == ["IN_APP"]
    assert email_outbox == []


@pytest.mark.asyncio
async def test_missing_smtp_credentials_keep_alert_and_record_not_configured(db_session, monkeypatch, email_outbox):
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    await _reset_recipient(db_session)
    n = await notification_service.create_and_dispatch(db_session, title="M3 nocreds", message="m", severity="CRITICAL")
    d = {x.channel: x for x in await _deliveries(db_session, n.id)}
    assert d["IN_APP"].status == "SENT"
    assert d["EMAIL_SMTP"].status == "NOT_CONFIGURED"
    assert "not set up" in d["EMAIL_SMTP"].error_message
    assert "SMTP" not in d["EMAIL_SMTP"].error_message and ".env" not in d["EMAIL_SMTP"].error_message
    assert email_outbox == []


@pytest.mark.asyncio
async def test_email_channel_toggle_disables_email(db_session, smtp_configured, email_outbox):
    await _reset_recipient(db_session, email_enabled=False)
    try:
        n = await notification_service.create_and_dispatch(db_session, title="M3 off", message="m", severity="URGENT")
        d = {x.channel: x for x in await _deliveries(db_session, n.id)}
        assert d["EMAIL_SMTP"].status == "DISABLED"
        assert email_outbox == []
    finally:
        await _reset_recipient(db_session)


@pytest.mark.asyncio
async def test_each_recipient_gets_email_per_scope(db_session, smtp_configured, email_outbox):
    await _add_recipient(db_session, "pm.all@test.invalid", scope="ALL")
    await _add_recipient(db_session, "lead.urgent@test.invalid", scope="URGENT_CRITICAL")
    await _add_recipient(db_session, "paused@test.invalid", scope="ALL", active=False)

    # INFO → only the ALL-scope recipient (same as the notification bar)
    n_info = await notification_service.create_and_dispatch(db_session, title="M3 scope info", message="m", severity="INFO")
    info_to = [m["To"] for m in email_outbox]
    assert len(info_to) == 1 and "pm.all@test.invalid" in info_to[0]
    d = [(x.channel, x.destination) for x in await _deliveries(db_session, n_info.id)]
    assert ("EMAIL_SMTP", "pm.all@test.invalid") in d and len([c for c, _ in d if c == "EMAIL_SMTP"]) == 1

    # CRITICAL → admin + ALL + URGENT_CRITICAL, never the inactive one
    email_outbox.clear()
    n_crit = await notification_service.create_and_dispatch(db_session, title="M3 scope crit", message="m", severity="CRITICAL")
    to = sorted(m["To"] for m in email_outbox)
    assert len(to) == 3
    assert not any("paused@test.invalid" in t for t in to)
    dests = {x.destination for x in await _deliveries(db_session, n_crit.id) if x.channel == "EMAIL_SMTP"}
    assert dests == {ADMIN_EMAIL, "pm.all@test.invalid", "lead.urgent@test.invalid"}


@pytest.mark.asyncio
async def test_one_failed_recipient_does_not_block_others(db_session, smtp_configured, monkeypatch):
    await _add_recipient(db_session, "bounce@test.invalid", scope="ALL")
    sent = []

    def _flaky(msg):
        if "bounce@test.invalid" in msg["To"]:
            raise OSError("550 mailbox unavailable")
        sent.append(msg["To"])

    monkeypatch.setattr(EmailService, "_send_sync", staticmethod(_flaky))
    n = await notification_service.create_and_dispatch(db_session, title="M3 partial", message="m", severity="URGENT")
    status_by_dest = {x.destination: x.status for x in await _deliveries(db_session, n.id) if x.channel == "EMAIL_SMTP"}
    assert status_by_dest == {ADMIN_EMAIL: "SENT", "bounce@test.invalid": "RETRYING"}  # temporary failure → automatic retry
    assert len(sent) == 1


# ---------------------------------------------------------------------- #
#  Automated engine: overdue → email, dedupe after read, completions      #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_overdue_alert_emailed_once_and_not_reemailed_after_mark_read(db_session, smtp_configured, email_outbox):
    await _reset_recipient(db_session)
    proj = (await db_session.execute(select(Project).where(Project.status == "ACTIVE").limit(1))).scalars().first()
    assert proj is not None
    task = Task(project_id=proj.id, title="M3 overdue email probe", status="New", priority="Normal",
                due_date=date.today() - timedelta(days=5))
    db_session.add(task)
    await db_session.commit()
    try:
        await notification_service.generate_automated_alerts(db_session)
        mine = [m for m in email_outbox if "M3 overdue email probe" in m["Subject"]]
        assert len(mine) == 1 and mine[0]["Subject"].startswith("Action needed:")   # 5 days late → CRITICAL

        # Admin presses "Mark all read" → next scan must NOT re-email the same issue
        notes = (await db_session.execute(select(Notification).where(Notification.entity_id == task.id))).scalars().all()
        for n in notes:
            n.is_read = True
        await db_session.commit()
        await notification_service.generate_automated_alerts(db_session)
        mine = [m for m in email_outbox if "M3 overdue email probe" in m["Subject"]]
        assert len(mine) == 1

        # After the 24h window a reminder is allowed again
        for n in notes:
            n.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
        await db_session.commit()
        await notification_service.generate_automated_alerts(db_session)
        mine = [m for m in email_outbox if "M3 overdue email probe" in m["Subject"]]
        assert len(mine) == 2
    finally:
        await _cleanup_entity(db_session, task.id)


@pytest.mark.asyncio
async def test_completed_task_generates_single_completed_alert_without_email(db_session, smtp_configured, email_outbox):
    proj = (await db_session.execute(select(Project).limit(1))).scalars().first()
    task = Task(project_id=proj.id, title="M3 completed probe", status="DONE", priority="Normal",
                updated_at=datetime.now(timezone.utc))
    db_session.add(task)
    await db_session.commit()
    try:
        created = await notification_service.generate_automated_alerts(db_session)
        mine = [a for a in created if a.entity_id == task.id]
        assert len(mine) == 1
        assert mine[0].title == f"{PREFIX_COMPLETED}: M3 completed probe"
        assert categorize(mine[0].severity, mine[0].title) == "completed"
        assert not [m for m in email_outbox if "M3 completed probe" in m["Subject"]]
        again = await notification_service.generate_automated_alerts(db_session)
        assert not [a for a in again if a.entity_id == task.id]
    finally:
        await _cleanup_entity(db_session, task.id)


@pytest.mark.asyncio
async def test_old_completed_tasks_do_not_flood(db_session, smtp_configured):
    proj = (await db_session.execute(select(Project).limit(1))).scalars().first()
    task = Task(project_id=proj.id, title="M3 old closed probe", status="Closed", priority="Normal",
                updated_at=datetime.now(timezone.utc) - timedelta(days=40))
    db_session.add(task)
    await db_session.commit()
    try:
        created = await notification_service.generate_automated_alerts(db_session)
        assert not [a for a in created if a.entity_id == task.id]
    finally:
        await _cleanup_entity(db_session, task.id)


@pytest.mark.asyncio
async def test_redmine_immediate_priority_escalates_critical(db_session, smtp_configured, email_outbox):
    proj = (await db_session.execute(select(Project).limit(1))).scalars().first()
    task = Task(project_id=proj.id, title="M3 immediate probe", status="In Progress", priority="Immediate")
    db_session.add(task)
    await db_session.commit()
    try:
        created = await notification_service.generate_automated_alerts(db_session)
        mine = [a for a in created if a.entity_id == task.id]
        assert len(mine) == 1 and mine[0].severity == "CRITICAL" and mine[0].title.startswith("Priority Escalation")
        assert [m for m in email_outbox if "M3 immediate probe" in m["Subject"]]
    finally:
        await _cleanup_entity(db_session, task.id)


# ---------------------------------------------------------------------- #
#  API: category filters, summary, admin endpoints                        #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_api_category_filter_and_summary(client: AsyncClient, db_session, smtp_configured):
    made = []
    for sev, title in [("CRITICAL", "M3 api crit"), ("URGENT", "M3 api urg"),
                       ("INFO", f"{PREFIX_COMPLETED}: M3 api done"), ("WARNING", "M3 api warn")]:
        made.append(await notification_service.create_and_dispatch(db_session, title=title, message="m", severity=sev))

    for cat, title in [("critical", "M3 api crit"), ("urgent", "M3 api urg"),
                       ("completed", f"{PREFIX_COMPLETED}: M3 api done"), ("info", "M3 api warn")]:
        r = await client.get(f"/api/v1/notifications/?category={cat}&limit=200")
        assert r.status_code == 200
        items = r.json()
        assert items and all(i["category"] == cat for i in items)
        assert any(i["title"] == title for i in items)

    everything = (await client.get("/api/v1/notifications/?limit=200")).json()
    crit = next(i for i in everything if i["title"] == "M3 api crit")
    assert {d["channel"] for d in crit["deliveries"]} == {"IN_APP", "EMAIL_SMTP"}
    assert crit["deep_link"].endswith(f"category=critical&id={crit['id']}")

    summary = (await client.get("/api/v1/notifications/summary")).json()
    assert set(summary) == {"all", "critical", "urgent", "completed", "info"}
    assert summary["all"]["total"] == sum(summary[c]["total"] for c in ("critical", "urgent", "completed", "info"))
    total_db = len((await db_session.execute(select(Notification.id))).all())
    assert summary["all"]["total"] == total_db

    bad = await client.get("/api/v1/notifications/?category=bogus")
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_api_trigger_rejects_unknown_severity(client: AsyncClient):
    r = await client.post("/api/v1/notifications/trigger", json={"title": "x", "message": "y", "severity": "PANIC"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_integrations_never_leak_secrets(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_USERNAME", "alerts@test.invalid")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "super-secret-app-pass")
    r = await client.get("/api/v1/admin/integrations")
    assert r.status_code == 200
    body = r.text
    data = r.json()
    assert "super-secret-app-pass" not in body
    if settings.REDMINE_API_KEY:
        assert settings.REDMINE_API_KEY not in body
    if settings.OPENROUTER_API_KEY:
        assert settings.OPENROUTER_API_KEY not in body
    assert data["smtp"]["configured"] is True and data["smtp"]["password_set"] is True
    assert data["smtp"]["alert_severities"] == ["CRITICAL", "URGENT"]
    assert set(data) >= {"redmine", "smtp", "openrouter", "recipient"}
    assert "google_chat_webhook_url" not in data["recipient"]


@pytest.mark.asyncio
async def test_admin_smtp_test_endpoint_sends_to_recipient(client: AsyncClient, db_session, smtp_configured, email_outbox):
    await _reset_recipient(db_session)
    await _add_recipient(db_session, "second@test.invalid")
    r = await client.post("/api/v1/admin/smtp/test")
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert {x["recipient"] for x in data["results"]} == {ADMIN_EMAIL, "second@test.invalid"}
    assert len(email_outbox) == 2 and all("SMTP configuration test" in m["Subject"] for m in email_outbox)


@pytest.mark.asyncio
async def test_admin_smtp_test_endpoint_reports_missing_credentials(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    data = (await client.post("/api/v1/admin/smtp/test")).json()
    assert data["success"] is False and data["status"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_admin_recipient_rejects_invalid_email(client: AsyncClient):
    r = await client.put("/api/v1/admin/recipient-config", json={"recipient_email": "not-an-email"})
    assert r.status_code == 422


# ---------------------------------------------------------------------- #
#  Email recipient management API                                         #
# ---------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_recipient_crud_lifecycle(client: AsyncClient, smtp_configured, email_outbox):
    r = await client.post("/api/v1/admin/email-recipients",
                          json={"email": "  New.Person@Company-Test.io ", "name": "New Person"})
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["email"] == "new.person@company-test.io"
    assert created["notify_scope"] == "ALL" and created["is_active"] is True

    listing = (await client.get("/api/v1/admin/email-recipients")).json()
    assert {x["email"] for x in listing} == {ADMIN_EMAIL, "new.person@company-test.io"}

    dup = await client.post("/api/v1/admin/email-recipients", json={"email": "new.person@company-test.io"})
    assert dup.status_code == 409

    upd = await client.patch(f"/api/v1/admin/email-recipients/{created['id']}",
                             json={"notify_scope": "URGENT_CRITICAL", "is_active": False})
    assert upd.status_code == 200
    assert upd.json()["notify_scope"] == "URGENT_CRITICAL" and upd.json()["is_active"] is False

    t = (await client.post(f"/api/v1/admin/email-recipients/{created['id']}/test")).json()
    assert t["success"] is True and t["recipient"] == "new.person@company-test.io"
    assert "new.person@company-test.io" in email_outbox[-1]["To"]

    d = await client.delete(f"/api/v1/admin/email-recipients/{created['id']}")
    assert d.status_code == 204
    assert (await client.delete(f"/api/v1/admin/email-recipients/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_recipient_validation(client: AsyncClient):
    assert (await client.post("/api/v1/admin/email-recipients", json={"email": "nope"})).status_code == 422
    assert (await client.post("/api/v1/admin/email-recipients",
                              json={"email": "a@company-test.io", "notify_scope": "SOMETIMES"})).status_code == 422


@pytest.mark.asyncio
async def test_last_active_recipient_cannot_be_removed_or_paused(client: AsyncClient):
    only = (await client.get("/api/v1/admin/email-recipients")).json()
    assert len(only) == 1
    assert (await client.delete(f"/api/v1/admin/email-recipients/{only[0]['id']}")).status_code == 409
    assert (await client.patch(f"/api/v1/admin/email-recipients/{only[0]['id']}",
                               json={"is_active": False})).status_code == 409


@pytest.mark.asyncio
async def test_integrations_lists_email_recipients(client: AsyncClient):
    data = (await client.get("/api/v1/admin/integrations")).json()
    assert [r["email"] for r in data["email_recipients"]] == [ADMIN_EMAIL]


@pytest.mark.asyncio
async def test_handover_endpoint_aliases(client: AsyncClient, db_session, smtp_configured, email_outbox):
    """CLAUDE_HANDOVER.md names: GET /admin/settings and POST /admin/smtp-test."""
    settings_resp = await client.get("/api/v1/admin/settings")
    integ = await client.get("/api/v1/admin/integrations")
    assert settings_resp.status_code == 200
    assert settings_resp.json()["smtp"] == integ.json()["smtp"]
    active = len((await db_session.execute(select(Project.id).where(Project.status == "ACTIVE"))).all())
    assert settings_resp.json()["redmine"]["active_projects_count"] == active

    r = await client.post("/api/v1/admin/smtp-test")
    assert r.status_code == 200 and r.json()["success"] is True
    assert ADMIN_EMAIL in email_outbox[0]["To"]
