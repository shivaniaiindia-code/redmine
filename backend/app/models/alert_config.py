import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Integer, UniqueConstraint, false, true, text
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

    # Alert routing: also email the people responsible (urgent / critical only)
    notify_assignee: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    notify_project_manager: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)

    # Scheduled emails to the recipient list (times are in APP_TIMEZONE)
    daily_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    weekly_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    digest_hour: Mapped[int] = mapped_column(Integer, default=9, server_default=text("9"), nullable=False)
    weekly_report_weekday: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"), nullable=False)  # 0 = Monday

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



class AlertEmailRecipient(Base):
    """
    People who receive platform notifications by email (managed in Administration).
    notify_scope:
      ALL             — every notification shown in the System Notification Bar
      URGENT_CRITICAL — only URGENT and CRITICAL alerts
    """
    __tablename__ = "alert_email_recipients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    notify_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="ALL")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ScheduledEmailRun(Base):
    """One row per scheduled email actually sent (daily digest / weekly report), so a restart never re-sends."""
    __tablename__ = "scheduled_email_runs"
    __table_args__ = (UniqueConstraint("kind", "period_key", name="uq_scheduled_email_run"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kind: Mapped[str] = mapped_column(String(30), nullable=False)          # DAILY_DIGEST | WEEKLY_REPORT
    period_key: Mapped[str] = mapped_column(String(30), nullable=False)    # 2026-11-03 | 2026-W45
    status: Mapped[str] = mapped_column(String(20), nullable=False)        # SENT | PARTIAL | FAILED | NO_RECIPIENTS
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
