import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=True)
    employee_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    job_title: Mapped[str] = mapped_column(String(150), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    manager_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False) # ACTIVE, ON_LEAVE, DEPARTED
    weekly_capacity_hours: Mapped[float] = mapped_column(Numeric(4, 1), default=40.0, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="employee")
    skills: Mapped[list["EmployeeSkill"]] = relationship("EmployeeSkill", back_populates="employee", lazy="selectin")
    historical_contributions: Mapped[list["HistoricalContribution"]] = relationship("HistoricalContribution", back_populates="employee", lazy="selectin")

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="TECHNICAL") # FRONTEND, BACKEND, AI, DEVOPS, MANAGEMENT

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(36), ForeignKey("skills.id"), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(String(30), default="INTERMEDIATE") # BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", lazy="joined")

