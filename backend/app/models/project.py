import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class CompanyGoal(Base):
    __tablename__ = "company_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    quarter: Mapped[str] = mapped_column(String(20), nullable=False) # e.g. "2026-Q4"
    target_metric: Mapped[str] = mapped_column(String(150), nullable=False)
    current_progress: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE") # ACTIVE, ACHIEVED, AT_RISK

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    goal_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("company_goals.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False) # PLANNING, ACTIVE, ON_HOLD, COMPLETED, CANCELLED
    health_status: Mapped[str] = mapped_column(String(20), default="ON_TRACK", nullable=False) # ON_TRACK, AT_RISK, OFF_TRACK, BLOCKED
    health_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_manager_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    primary_team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_total_hours: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    progress_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    members: Mapped[list["ProjectMember"]] = relationship("ProjectMember", back_populates="project", lazy="selectin")
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="project", lazy="selectin")
    milestones: Mapped[list["ProjectMilestone"]] = relationship("ProjectMilestone", back_populates="project", lazy="selectin")
    risks: Mapped[list["ProjectRisk"]] = relationship("ProjectRisk", back_populates="project", lazy="selectin")
    manager: Mapped["Employee"] = relationship("Employee", foreign_keys=[project_manager_id], lazy="selectin")
    team: Mapped["Team"] = relationship("Team", foreign_keys=[primary_team_id], lazy="selectin")

class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    role_in_project: Mapped[str] = mapped_column(String(50), default="CONTRIBUTOR")
    allocated_hours_per_week: Mapped[float] = mapped_column(Numeric(4, 1), default=0.0)
    joined_at: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")

class ProjectMilestone(Base):
    __tablename__ = "project_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="OPEN") # OPEN, LOCKED, CLOSED
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="milestones")

class ProjectRisk(Base):
    __tablename__ = "project_risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="TECHNICAL") # TECHNICAL, RESOURCE, EXTERNAL_DEPENDENCY
    probability: Mapped[str] = mapped_column(String(20), default="MEDIUM") # LOW, MEDIUM, HIGH
    impact: Mapped[str] = mapped_column(String(20), default="MODERATE") # MINOR, MODERATE, CRITICAL
    risk_score: Mapped[int] = mapped_column(Integer, default=5) # 1 to 9
    mitigation_plan: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")

    project: Mapped["Project"] = relationship("Project", back_populates="risks")

class ProjectRACI(Base):
    __tablename__ = "project_raci"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    deliverable_name: Mapped[str] = mapped_column(String(200), nullable=False)
    responsible_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    accountable_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    consulted_ids: Mapped[dict] = mapped_column(JSON, default=list)
    informed_ids: Mapped[dict] = mapped_column(JSON, default=list)

class ProjectClosureReport(Base):
    __tablename__ = "project_closure_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), unique=True, nullable=False)
    final_deliverables_summary: Mapped[str] = mapped_column(Text, nullable=False)
    budget_estimated_hours: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    actual_hours_spent: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    variance_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

