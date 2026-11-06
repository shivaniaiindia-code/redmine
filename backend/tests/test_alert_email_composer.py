"""LLM-structured alert emails: facts are deterministic, narrative from the LLM, template fallback."""
from datetime import date, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, delete

from app.core.config import settings
from app.models.alert_config import AlertEmailRecipient
from app.models.notification import Notification, NotificationDelivery
from app.models.project import Project
from app.models.task import Task
from app.services.alert_composer import AlertComposer, alert_composer
from app.services.notification_service import notification_service

ADMIN = "connect.aiindia@gmail.com"


@pytest.fixture
def smtp_on(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_USERNAME", "alerts@company-test.io")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "x")


@pytest_asyncio.fixture
async def overdue_task(db_session):
    await db_session.execute(delete(AlertEmailRecipient))
    db_session.add(AlertEmailRecipient(email=ADMIN, name="Administrator", notify_scope="URGENT_CRITICAL"))
    proj = (await db_session.execute(select(Project).where(Project.status == "ACTIVE").limit(1))).scalars().first()
    t = Task(project_id=proj.id, title="Composer probe task", status="New", priority="High",
             due_date=date.today() - timedelta(days=6))
    db_session.add(t)
    await db_session.commit()
    yield t, proj
    ids = select(Notification.id).where(Notification.entity_id == t.id)
    await db_session.execute(delete(NotificationDelivery).where(NotificationDelivery.notification_id.in_(ids)))
    await db_session.execute(delete(Notification).where(Notification.entity_id == t.id))
    await db_session.execute(delete(Task).where(Task.id == t.id))
    await db_session.commit()


def _html(msg):
    return msg.get_body(preferencelist=("html",)).get_content()


def test_parse_narrative_accepts_json_and_rejects_garbage():
    good = AlertComposer.parse_narrative('Sure! {"headline":"Task late","summary":"It is late.",'
                                         '"context":["a",5],"impact":"Delay","actions":["Do x","Do y"]}')
    assert good["headline"] == "Task late" and good["context"] == ["a"] and good["actions"] == ["Do x", "Do y"]
    tagged = AlertComposer.parse_narrative('{"subject":"[CRITICAL] Project X is AT_RISK","headline":"h","summary":"s"}')
    assert tagged["subject"] == "Project X is at risk"        # tag stripped, status code humanized
    assert AlertComposer.parse_narrative("Thinking Process: ...") is None
    assert AlertComposer.parse_narrative('{"headline":"","summary":"x"}') is None
    assert AlertComposer.parse_narrative('{"headline": "x"') is None


@pytest.mark.asyncio
async def test_template_email_is_structured_with_exact_facts(db_session, smtp_on, email_outbox, overdue_task):
    t, proj = overdue_task
    await notification_service.generate_automated_alerts(db_session)
    msg = next(m for m in email_outbox if "Composer probe task" in m["Subject"])
    html = _html(msg)
    assert "6 day(s) past its due date" in msg["Subject"]
    for section in ("Key details", "Why it matters", "Recommended next steps"):
        assert section in html
    assert f"{(date.today() - timedelta(days=6)).isoformat()} (6 day(s) overdue)" in html
    assert proj.name.strip() in html
    assert "Unassigned" in html and "Assign an owner" in html
    assert "Summary written by AI" not in html            # template path is labelled honestly


@pytest.mark.asyncio
async def test_llm_narrative_is_used_but_facts_stay_deterministic(db_session, smtp_on, email_outbox, overdue_task, monkeypatch):
    seen = {}

    async def fake_llm(self, facts):
        seen["facts"] = facts
        return {"subject": "Composer probe task is 6 days overdue", "headline": "Composer probe task is running late",
                "summary": "The task missed its deadline and has no owner.",
                "context": ["Created recently in Redmine."], "impact": "Delivery may slip.",
                "actions": ["Assign an owner", "Set a new date"]}

    monkeypatch.setattr(AlertComposer, "llm_narrative", fake_llm)
    t, _ = overdue_task
    await notification_service.generate_automated_alerts(db_session)
    msg = next(m for m in email_outbox if "Composer probe task" in m["Subject"])
    html = _html(msg)
    assert msg["Subject"] == "Composer probe task is 6 days overdue"   # LLM-written subject, no tags
    assert "The task missed its deadline and has no owner." in html and "<li>Set a new date</li>" in html
    assert "(6 day(s) overdue)" in html                    # details table not written by the LLM
    assert "Summary written by AI" in html
    assert seen["facts"]["task"]["days_overdue"] == 6 and seen["facts"]["task"]["assignee"] is None


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_template(db_session, smtp_on, email_outbox, overdue_task, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_AI_COMPOSE", True)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test")

    import httpx

    class Boom:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): raise httpx.ConnectError("down")
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(httpx, "AsyncClient", Boom)
    t, _ = overdue_task
    await notification_service.generate_automated_alerts(db_session)
    msg = next(m for m in email_outbox if "Composer probe task" in m["Subject"])
    assert "Recommended next steps" in _html(msg)


@pytest.mark.asyncio
async def test_no_llm_call_when_nobody_receives_email(db_session, overdue_task, monkeypatch):
    calls = []

    async def spy(self, db, n, category):
        calls.append(n.id)

    monkeypatch.setattr(AlertComposer, "compose", spy)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")      # SMTP not configured
    await notification_service.create_and_dispatch(db_session, title="no-send", message="m", severity="CRITICAL")
    assert calls == []
