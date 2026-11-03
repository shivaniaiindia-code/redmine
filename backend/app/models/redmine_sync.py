import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class RedmineSyncState(Base):
    __tablename__ = "redmine_sync_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False) # PROJECTS, ISSUES, USERS, TIME_ENTRIES
    last_sync_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="IDLE") # IDLE, SYNCING, FAILED
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class RedmineMapping(Base):
    __tablename__ = "redmine_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False) # PROJECT, ISSUE, USER, TIME_ENTRY, VERSION
    redmine_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    internal_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

