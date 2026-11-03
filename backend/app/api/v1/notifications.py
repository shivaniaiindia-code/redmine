from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.models.notification import Notification, NotificationDelivery
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class TriggerNotificationRequest(BaseModel):
    title: str
    message: str
    severity: str = "WARNING"  # INFO, WARNING, URGENT, CRITICAL
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
    deliveries: List[DeliveryItem] = []


@router.get("/", response_model=List[NotificationItem])
async def list_notifications(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Notification)
        .options(selectinload(Notification.deliveries))
        .order_by(desc(Notification.created_at))
        .limit(50)
    )
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
    Scans tasks for overdue deadlines, blockers, and project risks.
    Generates notifications dispatched to Admin System Notification Bar and Google Chat.
    All alerts route to the single designated account.
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
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers a notification using the mandatory dual-dispatch architecture:
    1. Persists in database & pushes to the System Notification Bar.
    2. Mirrors 1:1 to the Admin Google Chat Webhook in Cards v2 schema.
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
        "message": "Notification dispatched to System Notification Bar and mirrored to Admin Google Chat"
    }


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    query = select(Notification).where(Notification.id == notification_id)
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
    db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification).where(Notification.is_read == False).values(is_read=True)
    )
    await db.commit()
    return {"success": True, "message": "All notifications marked as read"}
