from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.models.team import Team, TeamMember
from app.models.project import Project, ProjectMember
from app.models.employee import Employee
from app.models.task import Task

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.get("/")
async def list_teams(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns project-wise teams based on live ProjectMember records and Redmine role allocations.
    Maintains full schema backward compatibility with existing tests and clients.
    """
    p_res = await db.execute(
        select(Project).where(Project.status != "INACTIVE").order_by(Project.name)
    )
    projects = scope.filter_projects(p_res.scalars().all())

    response = []
    for p in projects:
        pm_res = await db.execute(
            select(ProjectMember, Employee)
            .join(Employee, ProjectMember.employee_id == Employee.id)
            .where(ProjectMember.project_id == p.id)
            .order_by(Employee.first_name)
        )
        pm_rows = pm_res.all()

        members = []
        seen_emps = set()
        for pm, emp in pm_rows:
            seen_emps.add(emp.id)
            members.append({
                "employee_id": emp.id,
                "name": f"{emp.first_name} {emp.last_name}".strip(),
                "email": emp.email,
                "role": pm.role_in_project or "Contributor"
            })

        t_res = await db.execute(
            select(Task.assigned_to_id)
            .where(Task.project_id == p.id, Task.assigned_to_id.isnot(None))
            .distinct()
        )
        task_emp_ids = t_res.scalars().all()
        for eid in task_emp_ids:
            if eid and eid not in seen_emps:
                e_res = await db.execute(select(Employee).where(Employee.id == eid))
                emp = e_res.scalars().first()
                if emp:
                    seen_emps.add(emp.id)
                    members.append({
                        "employee_id": emp.id,
                        "name": f"{emp.first_name} {emp.last_name}".strip(),
                        "email": emp.email,
                        "role": "Task Assignee"
                    })

        if len(members) == 0:
            continue

        is_act = (p.status == "ACTIVE" or p.status == "Active" or p.status == "1")

        response.append({
            "id": p.id,
            "name": f"{p.name} Team",
            "department": "Engineering",
            "description": p.description or f"Delivery team for {p.name}",
            "is_active": is_act,
            "members_count": len(members),
            "projects_count": 1,
            "projects": [{"id": p.id, "name": p.name, "health_status": p.health_status}],
            "project_id": p.id,
            "project_name": p.name,
            "project_code": p.code,
            "status": "ACTIVE" if is_act else p.status,
            "members": members
        })

    return response

