import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("employees.id"), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members: Mapped[list["TeamMember"]] = relationship("TeamMember", back_populates="team", lazy="selectin")
    lead: Mapped["Employee"] = relationship("Employee", foreign_keys=[lead_id], lazy="selectin")

class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id"), nullable=False)
    role_in_team: Mapped[str] = mapped_column(String(50), default="MEMBER") # LEAD, CORE_MEMBER, CONTRIBUTOR
    joined_at: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    left_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    team: Mapped["Team"] = relationship("Team", back_populates="members")
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")

