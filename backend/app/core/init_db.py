import asyncio
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.user import User, Role, UserRole
from app.models.employee import Employee, Skill, EmployeeSkill
from app.models.team import Team, TeamMember
from app.models.project import Project, ProjectMember, ProjectRisk
from app.models.task import Task, TimeEntry, HistoricalContribution
from app.models.notification import Notification
from app.models.alert_config import AlertRecipientConfig

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing_roles = (await db.execute(select(Role))).scalars().all()
        if existing_roles:
            print("Database already initialized.")
            return

        print("Seeding initial enterprise roles...")
        roles_data = [
            (UserRole.SUPER_ADMIN, "Super Administrator with complete platform and integration authority"),
            (UserRole.COMPANY_MANAGEMENT, "Executive Management with company-wide dashboard and KPI visibility"),
            (UserRole.PROJECT_MANAGER, "Project Manager with delivery, risk register, and milestone governance"),
            (UserRole.TEAM_LEAD, "Team Lead with team velocity, member allocation, and blocker monitoring"),
            (UserRole.EMPLOYEE, "Employee with individual 360 dashboard, personal tasks, and growth portfolio")
        ]
        
        role_map = {}
        for role_enum, desc in roles_data:
            role = Role(name=role_enum.value, description=desc, permissions=["*"] if role_enum == UserRole.SUPER_ADMIN else ["read"])
            db.add(role)
            role_map[role_enum.value] = role
        await db.flush()

        print("Seeding Super Admin user...")
        admin_user = User(
            email="admin@company.com",
            hashed_password=get_password_hash("admin123"),
            role_id=role_map[UserRole.SUPER_ADMIN.value].id,
            is_active=True
        )
        db.add(admin_user)
        await db.flush()

        admin_employee = Employee(
            user_id=admin_user.id,
            employee_number="EMP-001",
            first_name="Anil",
            last_name="Abhange",
            email="admin@company.com",
            job_title="Lead Architect & Administrator",
            department="Engineering",
            hire_date=date(2023, 1, 15),
            status="ACTIVE",
            weekly_capacity_hours=40.0
        )
        db.add(admin_employee)
        await db.flush()

        print("Seeding core teams...")
        teams_data = [
            ("AI Team", "Computer vision, deep learning, OCR and LLM solutions", "AI Research"),
            ("Development", "Full-stack web, API, database and cloud architecture", "Engineering"),
            ("QA Team", "Automated regression, security penetration and performance testing", "Quality"),
            ("Research", "Data science algorithms, document extraction and prototypes", "R&D"),
            ("Operations", "DevOps, infrastructure monitoring, CI/CD and security", "Infrastructure")
        ]
        team_map = {}
        for t_name, t_desc, t_dept in teams_data:
            team = Team(name=t_name, description=t_desc, department=t_dept, lead_id=admin_employee.id, is_active=True)
            db.add(team)
            team_map[t_name] = team
        await db.flush()

        # All projects, tasks, and notifications are synchronized dynamically from live Redmine.
        # No mock or demonstration entities are seeded.

        # Seed the default alert recipient configuration
        print("Seeding default alert recipient config (anil.aiindia@gmail.com)...")
        alert_config = AlertRecipientConfig(
            label="Default Admin Recipient",
            recipient_email=settings.DEFAULT_ALERT_EMAIL,
            recipient_name=settings.DEFAULT_ALERT_NAME,
            google_chat_webhook_url=settings.GOOGLE_CHAT_ADMIN_WEBHOOK_URL or None,
            in_app_enabled=True,
            google_chat_enabled=True,
            email_enabled=True,
            is_active=True
        )
        db.add(alert_config)

        await db.commit()
        print("Initialization and seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())

