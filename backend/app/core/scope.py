"""
Project-level data scoping (RBAC row filtering).

  * SUPER_ADMIN and COMPANY_MANAGEMENT have global, company-wide visibility.
  * Every other role (PROJECT_MANAGER, TEAM_LEAD, EMPLOYEE) sees only the
    projects they belong to — a Redmine/DB project membership, being the
    project's manager, or having an issue assigned in it — plus the tasks and
    teammates of exactly those projects.

The scope is always derived from the validated JWT user (never from client
input), and every data endpoint and the AI assistant filter through it.
"""
from dataclasses import dataclass, field
from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User

GLOBAL_ROLES = {"SUPER_ADMIN", "COMPANY_MANAGEMENT"}

ACCESS_DENIED_PROJECTS = "Access Denied: You are only authorized to query your assigned projects."


@dataclass
class AccessScope:
    is_global: bool
    employee_id: Optional[str] = None
    project_ids: set[str] = field(default_factory=set)
    employee_ids: set[str] = field(default_factory=set)  # self + teammates on visible projects

    def can_see_project(self, project_id: Optional[str]) -> bool:
        return self.is_global or (project_id is not None and project_id in self.project_ids)

    def can_see_employee(self, employee_id: Optional[str]) -> bool:
        return self.is_global or (employee_id is not None and employee_id in self.employee_ids)

    def require_project(self, project_id: Optional[str]) -> None:
        if not self.can_see_project(project_id):
            # 404, not 403: do not confirm that a project outside the scope exists
            raise HTTPException(status_code=404, detail="Project not found")

    def filter_projects(self, projects):
        return list(projects) if self.is_global else [p for p in projects if p.id in self.project_ids]

    def filter_tasks(self, tasks):
        return list(tasks) if self.is_global else [t for t in tasks if t.project_id in self.project_ids]

    def can_see_notification(self, n: Notification, task_project: dict[str, str]) -> bool:
        """Scoped users only see alerts about their own projects' tasks/projects."""
        if self.is_global:
            return True
        if n.entity_type == "PROJECT":
            return n.entity_id in self.project_ids
        if n.entity_type == "TASK":
            return task_project.get(n.entity_id or "") in self.project_ids
        return False  # SYSTEM / USER (access requests) / digests: administrators only


async def build_scope(user: User, db: AsyncSession) -> AccessScope:
    role = user.role.name if user.role else ""
    if role in GLOBAL_ROLES:
        return AccessScope(is_global=True, employee_id=user.employee.id if user.employee else None)

    emp = user.employee
    if emp is None:
        emp = (await db.execute(select(Employee).where(Employee.email == user.email))).scalars().first()
    if emp is None:
        return AccessScope(is_global=False)

    project_ids = set((await db.execute(
        select(ProjectMember.project_id).where(ProjectMember.employee_id == emp.id))).scalars().all())
    project_ids |= set((await db.execute(
        select(Project.id).where(Project.project_manager_id == emp.id))).scalars().all())
    project_ids |= set((await db.execute(
        select(Task.project_id).where(Task.assigned_to_id == emp.id))).scalars().all())

    teammates = {emp.id}
    if project_ids:
        teammates |= set((await db.execute(
            select(ProjectMember.employee_id).where(ProjectMember.project_id.in_(project_ids)))).scalars().all())
        teammates |= {eid for eid in (await db.execute(
            select(Task.assigned_to_id).where(Task.project_id.in_(project_ids)))).scalars().all() if eid}
        teammates |= {eid for eid in (await db.execute(
            select(Project.project_manager_id).where(Project.id.in_(project_ids)))).scalars().all() if eid}

    return AccessScope(is_global=False, employee_id=emp.id, project_ids=project_ids, employee_ids=teammates)


async def get_access_scope(current_user: CurrentUser, db: AsyncSession = Depends(get_db)) -> AccessScope:
    return await build_scope(current_user, db)


Scope = Annotated[AccessScope, Depends(get_access_scope)]
