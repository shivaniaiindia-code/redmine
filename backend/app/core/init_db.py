import asyncio
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
import secrets
from app.core.security import get_password_hash, verify_password
from app.core.config import settings, ROOT_ADMIN_EMAIL
from app.models.user import User, Role, UserRole
from app.models.employee import Employee, Skill, EmployeeSkill
from app.models.team import Team, TeamMember
from app.models.project import Project, ProjectMember, ProjectRisk
from app.models.task import Task, TimeEntry, HistoricalContribution
from app.models.notification import Notification
from app.models.alert_config import AlertRecipientConfig

BASELINE_REVISION = "0001"  # schema as it was when tables were still created with create_all()


def _run_migrations(sync_conn) -> None:
    """
    Applies versioned Alembic migrations (backend/migrations).
    A database created before migrations existed (tables present, no
    alembic_version) is stamped at the baseline first, then upgraded.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect
    from app.core.config import BACKEND_DIR

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["connection"] = sync_conn
    from sqlalchemy import text
    tables = set(inspect(sync_conn).get_table_names())
    versioned = "alembic_version" in tables and sync_conn.execute(
        text("SELECT count(*) FROM alembic_version")).scalar()
    if not versioned and "users" in tables:
        command.stamp(cfg, BASELINE_REVISION)
    command.upgrade(cfg, "head")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing_roles = (await db.execute(select(Role))).scalars().all()
        if existing_roles:
            await secure_builtin_admin(db)
            from app.core.roles import sync_role_titles
            fixed = await sync_role_titles(db)
            if fixed:
                print(f"[Roles] {fixed} displayed title(s) aligned with assigned roles.")
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
            email=ROOT_ADMIN_EMAIL,
            hashed_password=_admin_password_hash(),
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
            email=ROOT_ADMIN_EMAIL,
            job_title="Super Admin",
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
            in_app_enabled=True,
            google_chat_enabled=False,
            email_enabled=True,
            is_active=True
        )
        db.add(alert_config)

        await db.commit()
        print("Initialization and seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())



LEGACY_DEFAULT_ADMIN_PASSWORDS = ("admin123",)


def _admin_password_hash() -> str:
    """ADMIN_PASSWORD from backend/.env, or an unguessable value (password login disabled)."""
    return get_password_hash(settings.ADMIN_PASSWORD or secrets.token_urlsafe(32))


async def secure_builtin_admin(db: AsyncSession) -> None:
    """
    The root admin password is managed only through ADMIN_PASSWORD in backend/.env
    (applied on every startup). Without it, a published default password is never
    kept: password login for the root account is disabled instead.
    """
    admin = (await db.execute(select(User).where(User.email == ROOT_ADMIN_EMAIL))).scalar_one_or_none()
    if admin is None:
        return
    if settings.ADMIN_PASSWORD:
        if not verify_password(settings.ADMIN_PASSWORD, admin.hashed_password):
            admin.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            await db.commit()
            print(f"[Security] Root admin password set from ADMIN_PASSWORD ({ROOT_ADMIN_EMAIL}).")
    elif any(verify_password(p, admin.hashed_password) for p in LEGACY_DEFAULT_ADMIN_PASSWORDS):
        admin.hashed_password = _admin_password_hash()
        await db.commit()
        print("[Security] Default root admin password removed; password login disabled until ADMIN_PASSWORD is set.")
