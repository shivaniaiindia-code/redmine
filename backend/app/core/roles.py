"""
Displayed titles come only from the role a Super Admin / Company Management
assigned — never from sign-up input, Redmine flags or other guesses.

  * Employee record linked to a platform account -> that account's role label.
  * Employee known only from Redmine (no platform account) -> "Redmine member".
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ROLE_LABELS = {
    "SUPER_ADMIN": "Super Admin",
    "COMPANY_MANAGEMENT": "Company Management",
    "PROJECT_MANAGER": "Project Manager",
    "TEAM_LEAD": "Team Lead",
    "EMPLOYEE": "Employee",
}
NO_PLATFORM_ROLE = "Redmine member"
UNASSIGNED_DEPARTMENT = "Unassigned"


def role_label(role_name: str | None) -> str:
    return ROLE_LABELS.get((role_name or "").upper(), NO_PLATFORM_ROLE)


def apply_role_title(user) -> None:
    """Keeps the linked employee record's title identical to the user's assigned role."""
    emp = getattr(user, "employee", None)
    if emp is not None and user.role is not None:
        emp.job_title = role_label(user.role.name)


async def sync_role_titles(db: AsyncSession) -> int:
    """Startup sweep: every displayed title equals the assigned role (or 'Redmine member')."""
    from app.models.employee import Employee
    from app.models.user import User

    changed = 0
    linked = {}
    for u in (await db.execute(select(User))).scalars().all():
        if u.employee is not None:
            linked[u.employee.id] = role_label(u.role.name if u.role else None)
    for emp in (await db.execute(select(Employee))).scalars().all():
        title = linked.get(emp.id, NO_PLATFORM_ROLE)
        if emp.job_title != title:
            emp.job_title = title
            changed += 1
    if changed:
        await db.commit()
    return changed
