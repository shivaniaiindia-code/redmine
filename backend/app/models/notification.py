import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=True) # Null = Broadcast/Admin
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False) # INFO, WARNING, URGENT, CRITICAL
    entity_type: Mapped[str] = mapped_column(String(50), default="SYSTEM") # TASK, PROJECT, TEAM, EMPLOYEE
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    deliveries: Mapped[list["NotificationDelivery"]] = relationship("NotificationDelivery", back_populates="notification", lazy="selectin")

class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id: Mapped[str] = mapped_column(String(36), ForeignKey("notifications.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False) # IN_APP, GOOGLE_CHAT_ADMIN, GOOGLE_CHAT_SPACE
    destination: Mapped[str] = mapped_column(Text, nullable=False) # Webhook URL or User ID
    status: Mapped[str] = mapped_column(String(30), default="PENDING") # PENDING, SENT, FAILED, RETRYING
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    response_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    notification: Mapped["Notification"] = relationship("Notification", back_populates="deliveries")

class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False) # TASK_OVERDUE, TASK_BLOCKED, PROJECT_AT_RISK, WORKLOAD_EXCEEDED
    severity: Mapped[str] = mapped_column(String(20), default="WARNING")
    condition_config: Mapped[dict] = mapped_column(JSON, default=dict)
    escalation_delay_hours: Mapped[int] = mapped_column(Integer, default=24)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class GoogleChatSpace(Base):
    __tablename__ = "google_chat_spaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    space_name: Mapped[str] = mapped_column(String(100), nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), default="PROJECT_ALERTS") # ADMIN_SYSTEM_MIRROR, COMPANY_BROADCAST, TEAM_SPACE, PROJECT_ALERTS
    team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

