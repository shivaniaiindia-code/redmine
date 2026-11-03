import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, Numeric, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    assigned_to_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=True)
    author_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracker: Mapped[str] = mapped_column(String(50), default="Feature", nullable=False) # Feature, Bug, Support, Task
    status: Mapped[str] = mapped_column(String(50), default="New", nullable=False) # New, In Progress, Feedback, Resolved, Closed
    priority: Mapped[str] = mapped_column(String(30), default="Normal", nullable=False) # Low, Normal, High, Urgent, Immediate
    estimated_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0)
    spent_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0)
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    cycle_time_hours: Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    blocker_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    assignee: Mapped["Employee"] = relationship("Employee", foreign_keys=[assigned_to_id], lazy="selectin")
    time_entries: Mapped[list["TimeEntry"]] = relationship("TimeEntry", back_populates="task", lazy="selectin")
    journals: Mapped[list["TaskJournal"]] = relationship("TaskJournal", back_populates="task", lazy="selectin")

class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    depends_on_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(30), default="BLOCKS") # BLOCKS, RELATES_TO, PRECEDES

class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    hours: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), default="Development")
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task: Mapped["Task"] = relationship("Task", back_populates="time_entries")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")

class HistoricalContribution(Base):
    __tablename__ = "historical_contributions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), index=True, nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=False)
    role_played: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_hours_logged: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0, nullable=False)
    deliverable_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employee: Mapped["Employee"] = relationship("Employee", back_populates="historical_contributions")
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

class TaskJournal(Base):
    __tablename__ = "task_journals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True, nullable=False)
    author_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[dict] = mapped_column(JSON, default=list) # [{field, old_value, new_value}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    task: Mapped["Task"] = relationship("Task", back_populates="journals")
    author: Mapped["Employee"] = relationship("Employee", lazy="selectin")

