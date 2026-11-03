import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AlertRecipientConfig(Base):
    """
    Stores the configurable default alert recipient.
    All system-generated notifications (employee, project, task, team, company)
    route to this single designated account.
    In-app notifications and external Google Chat delivery are tracked separately
    via the NotificationDelivery model.
    """
    __tablename__ = "alert_recipient_config"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Display label for this config entry
    label: Mapped[str] = mapped_column(String(100), nullable=False, default="Default Admin Recipient")

    # The designated recipient email — all alerts route here
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Administrator")

    # Google Chat webhook (external delivery channel)
    google_chat_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Enable/disable each channel independently
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    google_chat_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Whether this record is the active default
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

