from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import List, Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, or_, and_, not_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.permissions import CurrentUser, RequireAdminOrManagement
from app.models.notification import Notification, NotificationDelivery
from app.models.task import Task
from app.core.scope import Scope, AccessScope
from app.services.notification_service import (
    notification_service, categorize, PREFIX_COMPLETED,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class TriggerNotificationRequest(BaseModel):
    title: str
    message: str
    severity: Literal["INFO", "WARNING", "URGENT", "CRITICAL"] = "WARNING"
    entity_type: str = "TASK"
    entity_id: Optional[str] = None


class DeliveryItem(BaseModel):
    id: str
    channel: str
    destination: str
    status: str
    delivered_at: Optional[str] = None
    error_message: Optional[str] = None


class NotificationItem(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    entity_type: str
    entity_id: Optional[str] = None
    is_read: bool
    created_at: str
    category: str
    deep_link: str
    deliveries: List[DeliveryItem] = []


Category = Literal["all", "critical", "urgent", "completed", "info"]

_COMPLETED_COND = Notification.title.like(f"{PREFIX_COMPLETED}%")


def _category_condition(category: str):
    """SQL equivalent of notification_service.categorize()."""
    if category == "completed":
        return _COMPLETED_COND
    if category == "critical":
        return and_(Notification.severity == "CRITICAL", not_(_COMPLETED_COND))
    if category == "urgent":
        return and_(Notification.severity == "URGENT", not_(_COMPLETED_COND))
    if category == "info":
        return and_(Notification.severity.notin_(["CRITICAL", "URGENT"]), not_(_COMPLETED_COND))
    return None


def _visibility_condition(scope: AccessScope):
    """None for company-wide roles; otherwise only alerts about the user's own projects and their tasks."""
    if scope.is_global:
        return None
    pids = list(scope.project_ids)
    return or_(
        and_(Notification.entity_type == "PROJECT", Notification.entity_id.in_(pids)),
        and_(Notification.entity_type == "TASK",
             Notification.entity_id.in_(select(Task.id).where(Task.project_id.in_(pids)))),
    )


@router.get("/summary")
async def notification_summary(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    """Per-category totals and unread counts for the notification filter pills."""
    result = {}
    visible = _visibility_condition(scope)
    for cat in ("critical", "urgent", "completed", "info"):
        cond = _category_condition(cat)
        if visible is not None:
            cond = and_(cond, visible)
        total = (await db.execute(select(func.count()).select_from(Notification).where(cond))).scalar_one()
        unread = (await db.execute(
            select(func.count()).select_from(Notification).where(and_(cond, Notification.is_read == False))
        )).scalar_one()
        result[cat] = {"total": total, "unread": unread}
    result["all"] = {
        "total": sum(v["total"] for v in result.values()),
        "unread": sum(v["unread"] for v in result.values()),
    }
    return result


@router.get("/", response_model=List[NotificationItem])
async def list_notifications(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db),
    category: Category = Query("all", description="all | critical | urgent | completed | info"),
    unread_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
):
    query = select(Notification).options(selectinload(Notification.deliveries))
    visible = _visibility_condition(scope)
    if visible is not None:
        query = query.where(visible)
    cond = _category_condition(category)
    if cond is not None:
        query = query.where(cond)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(desc(Notification.created_at)).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    items = []
    for n in notifications:
        delivery_items = [
            DeliveryItem(
                id=d.id,
                channel=d.channel,
                destination=d.destination,
                status=d.status,
                delivered_at=d.delivered_at.strftime("%Y-%m-%d %H:%M:%S") if d.delivered_at else None,
                error_message=d.error_message
            )
            for d in (n.deliveries or [])
        ]
        items.append(
            NotificationItem(
                id=n.id,
                title=n.title,
                message=n.message,
                severity=n.severity,
                entity_type=n.entity_type,
                entity_id=n.entity_id,
                is_read=n.is_read,
                created_at=n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                category=categorize(n.severity, n.title),
                deep_link=notification_service.deep_link(n),
                deliveries=delivery_items
            )
        )
    return items


@router.post("/generate-alerts")
async def generate_alerts(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Automated Alert Generation trigger:
    Scans synchronized Redmine tasks/projects for overdue deadlines, blockers,
    priority escalations, completions and project risks. Every alert lands in the
    System Notification Bar; URGENT and CRITICAL alerts are also emailed via SMTP
    to the designated administrator.
    """
    alerts = await notification_service.generate_automated_alerts(db)
    return {
        "success": True,
        "alerts_generated": len(alerts),
        "alerts": [{"id": a.id, "title": a.title, "severity": a.severity} for a in alerts]
    }


@router.post("/trigger", status_code=status.HTTP_201_CREATED)
async def trigger_notification(
    req: TriggerNotificationRequest,
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    """
    Programmatic notification entry point (used by integrations and tests):
    1. Persists in database & pushes to the System Notification Bar.
    2. URGENT / CRITICAL severities are emailed via SMTP to the administrator.
    """
    notification = await notification_service.create_and_dispatch(
        db=db,
        title=req.title,
        message=req.message,
        severity=req.severity,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        recipient_id=current_user.id
    )
    return {
        "success": True,
        "notification_id": notification.id,
        "message": "Notification recorded in the System Notification Bar"
                   + (" and emailed to the administrator" if req.severity in ("URGENT", "CRITICAL") else "")
    }


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    query = select(Notification).where(Notification.id == notification_id)
    visible = _visibility_condition(scope)
    if visible is not None:
        query = query.where(visible)
    result = await db.execute(query)
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    await db.commit()
    return {"success": True, "id": notification_id, "is_read": True}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    stmt = update(Notification).where(Notification.is_read == False)
    visible = _visibility_condition(scope)
    if visible is not None:
        stmt = stmt.where(visible)
    await db.execute(stmt.values(is_read=True).execution_options(synchronize_session=False))
    await db.commit()
    return {"success": True, "message": "All notifications marked as read"}
