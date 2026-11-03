from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from app.core.database import get_db
from app.models.alert_config import AlertRecipientConfig
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin Configuration"])


class RecipientConfigResponse(BaseModel):
    id: str
    label: str
    recipient_email: str
    recipient_name: str
    google_chat_webhook_url: Optional[str]
    in_app_enabled: bool
    google_chat_enabled: bool
    email_enabled: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RecipientConfigUpdate(BaseModel):
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    google_chat_webhook_url: Optional[str] = None
    in_app_enabled: Optional[bool] = None
    google_chat_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None


@router.get("/recipient-config", response_model=RecipientConfigResponse)
async def get_recipient_config(db: AsyncSession = Depends(get_db)):
    """Get the current default alert recipient configuration."""
    config = (
        await db.execute(
            select(AlertRecipientConfig)
            .where(AlertRecipientConfig.is_active == True)
            .limit(1)
        )
    ).scalars().first()

    if not config:
        # Return defaults from settings if no DB record exists yet
        return {
            "id": "not-configured",
            "label": "Default Admin Recipient",
            "recipient_email": settings.DEFAULT_ALERT_EMAIL,
            "recipient_name": settings.DEFAULT_ALERT_NAME,
            "google_chat_webhook_url": settings.GOOGLE_CHAT_ADMIN_WEBHOOK_URL or None,
            "in_app_enabled": True,
            "google_chat_enabled": True,
            "email_enabled": True,
            "is_active": True,
        }

    return config


@router.put("/recipient-config", response_model=RecipientConfigResponse)
async def update_recipient_config(
    payload: RecipientConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update the default alert recipient configuration from Admin Settings."""
    config = (
        await db.execute(
            select(AlertRecipientConfig)
            .where(AlertRecipientConfig.is_active == True)
            .limit(1)
        )
    ).scalars().first()

    if not config:
        # Create fresh if none exists
        config = AlertRecipientConfig(
            label="Default Admin Recipient",
            recipient_email=settings.DEFAULT_ALERT_EMAIL,
            recipient_name=settings.DEFAULT_ALERT_NAME,
            in_app_enabled=True,
            google_chat_enabled=True,
            email_enabled=True,
            is_active=True,
        )
        db.add(config)
        await db.flush()

    # Apply updates
    if payload.recipient_email is not None:
        config.recipient_email = payload.recipient_email
    if payload.recipient_name is not None:
        config.recipient_name = payload.recipient_name
    if payload.google_chat_webhook_url is not None:
        config.google_chat_webhook_url = payload.google_chat_webhook_url
    if payload.in_app_enabled is not None:
        config.in_app_enabled = payload.in_app_enabled
    if payload.google_chat_enabled is not None:
        config.google_chat_enabled = payload.google_chat_enabled
    if payload.email_enabled is not None:
        config.email_enabled = payload.email_enabled

    await db.commit()
    await db.refresh(config)
    return config

