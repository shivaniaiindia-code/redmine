import time
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal, Optional
from app.core.database import get_db
from app.core.permissions import RequireAdminOrManagement as CurrentUser
from app.models.alert_config import AlertRecipientConfig, AlertEmailRecipient
from app.models.redmine_sync import RedmineSyncState
from app.models.project import Project
from app.core.config import settings
from app.services.email_service import email_service
from app.services.redmine_service import redmine_service
from app.services.notification_service import SCOPE_ALL

router = APIRouter(prefix="/admin", tags=["Admin Configuration"])


# ---------------------------------------------------------------------- #
#  Alert recipient configuration                                          #
# ---------------------------------------------------------------------- #
class RecipientConfigResponse(BaseModel):
    id: str
    label: str
    recipient_email: str
    recipient_name: str
    in_app_enabled: bool
    email_enabled: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RecipientConfigUpdate(BaseModel):
    recipient_email: Optional[EmailStr] = None
    recipient_name: Optional[str] = Field(default=None, max_length=150)
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None


async def _active_config(db: AsyncSession) -> AlertRecipientConfig | None:
    return (
        await db.execute(
            select(AlertRecipientConfig).where(AlertRecipientConfig.is_active == True).limit(1)
        )
    ).scalars().first()


def _default_config_dict() -> dict:
    return {
        "id": "not-configured",
        "label": "Default Admin Recipient",
        "recipient_email": settings.DEFAULT_ALERT_EMAIL,
        "recipient_name": settings.DEFAULT_ALERT_NAME,
        "in_app_enabled": True,
        "email_enabled": True,
        "is_active": True,
    }


@router.get("/recipient-config", response_model=RecipientConfigResponse)
async def get_recipient_config(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Current designated alert recipient (all alerts route to this account)."""
    config = await _active_config(db)
    return config if config else _default_config_dict()


@router.put("/recipient-config", response_model=RecipientConfigResponse)
async def update_recipient_config(
    payload: RecipientConfigUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update the designated alert recipient and channel toggles from Admin Settings."""
    config = await _active_config(db)
    if not config:
        config = AlertRecipientConfig(
            label="Default Admin Recipient",
            recipient_email=settings.DEFAULT_ALERT_EMAIL,
            recipient_name=settings.DEFAULT_ALERT_NAME,
            in_app_enabled=True,
            google_chat_enabled=False,
            email_enabled=True,
            is_active=True,
        )
        db.add(config)
        await db.flush()

    if payload.recipient_email is not None:
        config.recipient_email = str(payload.recipient_email)
    if payload.recipient_name is not None and payload.recipient_name.strip():
        config.recipient_name = payload.recipient_name.strip()
    if payload.in_app_enabled is not None:
        config.in_app_enabled = payload.in_app_enabled
    if payload.email_enabled is not None:
        config.email_enabled = payload.email_enabled

    await db.commit()
    await db.refresh(config)
    return config


# ---------------------------------------------------------------------- #
#  Integration overview (secret-free)                                     #
# ---------------------------------------------------------------------- #
def _mask(value: str) -> str | None:
    if not value:
        return None
    return f"{'•' * 8}{value[-4:]}" if len(value) > 4 else "•" * len(value)


@router.get("/settings", include_in_schema=True, summary="Alias of /admin/integrations (handover contract)")
@router.get("/integrations")
async def get_integrations(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """
    Single source for the Administration view: Redmine, SMTP, OpenRouter and
    recipient status. Secrets are never returned — only masked suffixes.
    Credentials are configured in backend/.env.
    """
    sync_state = (
        await db.execute(select(RedmineSyncState).where(RedmineSyncState.entity_type == "ISSUES"))
    ).scalars().first()
    config = await _active_config(db)
    recipient = (
        RecipientConfigResponse.model_validate(config).model_dump() if config else _default_config_dict()
    )

    return {
        "redmine": {
            "url": settings.REDMINE_URL,
            "api_key_configured": bool(settings.REDMINE_API_KEY),
            "api_key_hint": _mask(settings.REDMINE_API_KEY),
            "sync_interval_minutes": settings.REDMINE_SYNC_INTERVAL_MINUTES,
            "last_synced_at": sync_state.last_sync_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            if sync_state and sync_state.last_sync_timestamp else None,
            "records_synced": sync_state.records_synced if sync_state else 0,
            "sync_status": sync_state.status if sync_state else "IDLE",
            "active_projects_count": len((await db.execute(
                select(Project.id).where(Project.status == "ACTIVE"))).all()),
        },
        "smtp": email_service.config_summary(),
        "openrouter": {
            "configured": bool(settings.OPENROUTER_API_KEY),
            "api_key_hint": _mask(settings.OPENROUTER_API_KEY),
            "base_url": settings.OPENROUTER_BASE_URL,
            "default_model": settings.OPENROUTER_DEFAULT_MODEL,
            "fallback_model": settings.OPENROUTER_FALLBACK_MODEL,
        },
        "recipient": recipient,
        "email_recipients": [
            EmailRecipientOut.model_validate(r).model_dump()
            for r in (await db.execute(select(AlertEmailRecipient).order_by(AlertEmailRecipient.created_at))).scalars().all()
        ],
        "config_source": "backend/.env (restart backend after editing)",
    }


# ---------------------------------------------------------------------- #
#  Connectivity tests                                                     #
# ---------------------------------------------------------------------- #
async def _send_test_email(to_email: str, to_name: str) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    started = time.perf_counter()
    result = await email_service.send_alert(
        to_email=to_email,
        to_name=to_name,
        title="SMTP configuration test",
        message="This is a test email from the Project Manager Administration page. "
                "You are on the platform's email recipient list.",
        severity="INFO",
        entity_type="SYSTEM",
        created_at_label=now,
        deep_link=f"{settings.APP_BASE_URL.rstrip('/')}/?view=admin",
    )
    return {
        "recipient": to_email,
        "success": result.success,
        "status": result.status,
        "detail": result.detail,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }


@router.post("/smtp-test", summary="Alias of /admin/smtp/test (handover contract)")
@router.post("/smtp/test")
async def send_smtp_test_email(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Sends a real test email to every active email recipient."""
    recipients = (await db.execute(
        select(AlertEmailRecipient).where(AlertEmailRecipient.is_active == True)
        .order_by(AlertEmailRecipient.created_at)
    )).scalars().all()
    if not recipients:
        return {"success": False, "status": "NO_RECIPIENTS", "detail": "No active email recipients.", "results": []}
    results = [await _send_test_email(r.email, r.name) for r in recipients]
    ok = all(r["success"] for r in results)
    return {
        "success": ok,
        "status": "SENT" if ok else results[0]["status"] if all(not r["success"] for r in results) else "PARTIAL",
        "detail": results[0]["detail"] if not ok else f"Sent to {len(results)} recipient(s)",
        "results": results,
    }


# ---------------------------------------------------------------------- #
#  Email recipients (who receives platform notifications by email)        #
# ---------------------------------------------------------------------- #
Scope = Literal["ALL", "URGENT_CRITICAL"]


class EmailRecipientOut(BaseModel):
    id: str
    email: str
    name: str
    notify_scope: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class EmailRecipientCreate(BaseModel):
    email: EmailStr
    name: str = Field(default="", max_length=150)
    notify_scope: Scope = SCOPE_ALL


class EmailRecipientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=150)
    notify_scope: Optional[Scope] = None
    is_active: Optional[bool] = None


async def _get_recipient_or_404(db: AsyncSession, recipient_id: str) -> AlertEmailRecipient:
    r = (await db.execute(select(AlertEmailRecipient).where(AlertEmailRecipient.id == recipient_id))).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Email recipient not found")
    return r


async def _active_count(db: AsyncSession) -> int:
    return len((await db.execute(
        select(AlertEmailRecipient.id).where(AlertEmailRecipient.is_active == True)
    )).all())


@router.get("/email-recipients", response_model=list[EmailRecipientOut])
async def list_email_recipients(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(AlertEmailRecipient).order_by(AlertEmailRecipient.created_at))).scalars().all()


@router.post("/email-recipients", response_model=EmailRecipientOut, status_code=status.HTTP_201_CREATED)
async def add_email_recipient(payload: EmailRecipientCreate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    email = str(payload.email).strip().lower()
    dup = (await db.execute(select(AlertEmailRecipient).where(AlertEmailRecipient.email == email))).scalars().first()
    if dup:
        raise HTTPException(status_code=409, detail=f"{email} is already on the recipient list")
    r = AlertEmailRecipient(
        email=email,
        name=payload.name.strip() or email.split("@")[0],
        notify_scope=payload.notify_scope,
        is_active=True,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.patch("/email-recipients/{recipient_id}", response_model=EmailRecipientOut)
async def update_email_recipient(
    recipient_id: str, payload: EmailRecipientUpdate, current_user: CurrentUser, db: AsyncSession = Depends(get_db)
):
    r = await _get_recipient_or_404(db, recipient_id)
    if payload.is_active is False and r.is_active and await _active_count(db) <= 1:
        raise HTTPException(status_code=409, detail="At least one active email recipient is required")
    if payload.name is not None and payload.name.strip():
        r.name = payload.name.strip()
    if payload.notify_scope is not None:
        r.notify_scope = payload.notify_scope
    if payload.is_active is not None:
        r.is_active = payload.is_active
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/email-recipients/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_email_recipient(recipient_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    r = await _get_recipient_or_404(db, recipient_id)
    if r.is_active and await _active_count(db) <= 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last active email recipient")
    await db.delete(r)
    await db.commit()


@router.post("/email-recipients/{recipient_id}/test")
async def test_email_recipient(recipient_id: str, current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    r = await _get_recipient_or_404(db, recipient_id)
    return await _send_test_email(r.email, r.name)


@router.post("/openrouter/test")
async def test_openrouter(current_user: CurrentUser):
    """Minimal live completion against OpenRouter with the configured model."""
    if not settings.OPENROUTER_API_KEY:
        return {"success": False, "detail": "The AI assistant is not set up yet. Ask your technical administrator to connect it."}
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{settings.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "X-Title": "Company Intelligence Platform",
                },
                json={
                    "model": settings.OPENROUTER_DEFAULT_MODEL,
                    "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
                    "max_tokens": 20,
                },
            )
        elapsed = int((time.perf_counter() - started) * 1000)
        if res.status_code == 200:
            return {"success": True, "model": settings.OPENROUTER_DEFAULT_MODEL,
                    "detail": f"Assistant replied in {elapsed} ms", "elapsed_ms": elapsed}
        return {"success": False, "model": settings.OPENROUTER_DEFAULT_MODEL,
                "detail": f"The assistant service returned an error ({res.status_code}). Please try again later.", "elapsed_ms": elapsed}
    except Exception as exc:
        return {"success": False, "model": settings.OPENROUTER_DEFAULT_MODEL,
                "detail": f"{type(exc).__name__}: {exc}"[:300]}


@router.post("/redmine/test")
async def test_redmine(current_user: CurrentUser):
    """Live connectivity check against the Redmine REST API."""
    started = time.perf_counter()
    info = await redmine_service.test_connection()
    info["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    info["success"] = bool(info.get("connected"))
    return info


# ---------------------------------------------------------------------- #
#  Email automation: alert routing + daily digest / weekly report          #
# ---------------------------------------------------------------------- #
class EmailAutomationUpdate(BaseModel):
    notify_assignee: Optional[bool] = None
    notify_project_manager: Optional[bool] = None
    daily_digest_enabled: Optional[bool] = None
    weekly_report_enabled: Optional[bool] = None
    digest_hour: Optional[int] = Field(default=None, ge=0, le=23)
    weekly_report_weekday: Optional[int] = Field(default=None, ge=0, le=6)


class ProjectManagerUpdate(BaseModel):
    employee_id: Optional[str] = None


class SendNowRequest(BaseModel):
    kind: Literal["daily", "weekly"]


async def _config_or_create(db: AsyncSession) -> AlertRecipientConfig:
    config = await _active_config(db)
    if config is None:
        config = AlertRecipientConfig(
            label="Default Admin Recipient", recipient_email=settings.DEFAULT_ALERT_EMAIL,
            recipient_name=settings.DEFAULT_ALERT_NAME, in_app_enabled=True, google_chat_enabled=False,
            email_enabled=True, is_active=True,
        )
        db.add(config)
        await db.flush()
    return config


async def _redmine_people(db: AsyncSession) -> list[dict]:
    from app.models.employee import Employee
    from app.models.redmine_sync import RedmineMapping
    mapped = {m for (m,) in (await db.execute(
        select(RedmineMapping.internal_id).where(RedmineMapping.entity_type == "USER"))).all()}
    emps = (await db.execute(select(Employee).where(Employee.status == "ACTIVE"))).scalars().all()
    people = [{"id": e.id, "name": f"{e.first_name} {e.last_name}".strip().title(), "email": e.email}
              for e in emps if e.id in mapped]
    return sorted(people, key=lambda p: p["name"].lower())


@router.get("/email-automation")
async def get_email_automation(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    from app.services import scheduled_reports
    config = await _config_or_create(db)
    await db.commit()
    people = await _redmine_people(db)
    names = {p["id"]: p["name"] for p in people}
    projects = (await db.execute(select(Project).where(Project.status == "ACTIVE").order_by(Project.name))).scalars().all()
    return {
        "routing": {"notify_assignee": config.notify_assignee, "notify_project_manager": config.notify_project_manager},
        "schedule": {
            "daily_digest_enabled": config.daily_digest_enabled,
            "weekly_report_enabled": config.weekly_report_enabled,
            "digest_hour": config.digest_hour,
            "weekly_report_weekday": config.weekly_report_weekday,
            "timezone": settings.APP_TIMEZONE,
        },
        "last_runs": await scheduled_reports.last_runs(db),
        "projects": [{"id": p.id, "name": p.name.strip(), "manager_id": p.project_manager_id,
                      "manager_name": names.get(p.project_manager_id)} for p in projects],
        "people": people,
        "email_ready": email_service.is_configured() and config.email_enabled,
    }


@router.put("/email-automation")
async def update_email_automation(payload: EmailAutomationUpdate, current_user: CurrentUser,
                                  db: AsyncSession = Depends(get_db)):
    config = await _config_or_create(db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(config, field, value)
    await db.commit()
    return await get_email_automation(current_user, db)


@router.put("/projects/{project_id}/manager")
async def set_project_manager(project_id: str, payload: ProjectManagerUpdate, current_user: CurrentUser,
                              db: AsyncSession = Depends(get_db)):
    """Project manager receives that project's urgent/critical alerts when routing is enabled."""
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.employee_id and payload.employee_id not in {p["id"] for p in await _redmine_people(db)}:
        raise HTTPException(status_code=422, detail="Choose a person who is an active Redmine user.")
    project.project_manager_id = payload.employee_id or None
    await db.commit()
    return {"project_id": project.id, "manager_id": project.project_manager_id}


@router.post("/email-automation/send-now")
async def send_scheduled_email_now(payload: SendNowRequest, current_user: CurrentUser,
                                   db: AsyncSession = Depends(get_db)):
    """Sends the daily digest or weekly report right now to every active recipient."""
    from app.services import scheduled_reports
    if not email_service.is_configured():
        raise HTTPException(status_code=409, detail="Email sending is not set up yet.")
    kind = scheduled_reports.KIND_DAILY if payload.kind == "daily" else scheduled_reports.KIND_WEEKLY
    key = f"manual {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    run = await scheduled_reports.send(db, kind, key)
    label = "Daily digest" if payload.kind == "daily" else "Weekly report"
    if run.status == "NO_RECIPIENTS":
        message = "There are no active email recipients."
    elif run.status == "SENT":
        message = f"{label} sent to {run.sent_count} recipient(s)."
    else:
        message = f"{label} reached {run.sent_count} of {run.recipient_count} recipient(s)."
    return {"success": run.status == "SENT", "status": run.status, "message": message,
            "sent_count": run.sent_count, "recipient_count": run.recipient_count}
