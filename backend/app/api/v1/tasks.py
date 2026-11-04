from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.models.task import Task
from app.models.project import Project
from app.models.employee import Employee
from app.services.notification_service import notification_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class BlockerPayload(BaseModel):
    is_blocked: bool
    blocker_reason: Optional[str] = None

@router.get("/")
async def list_tasks(
    project_id: Optional[str] = None,
    is_overdue: Optional[bool] = None,
    is_blocked: Optional[bool] = None,
    current_user: CurrentUser = None,
    scope: Scope = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Task).order_by(desc(Task.created_at))
    if project_id:
        scope.require_project(project_id)
        query = query.where(Task.project_id == project_id)
    if is_overdue is not None:
        query = query.where(Task.is_overdue == is_overdue)
    if is_blocked is not None:
        query = query.where(Task.is_blocked == is_blocked)

    result = await db.execute(query)
    tasks = scope.filter_tasks(result.scalars().all())

    # Batch prefetch projects and employees to eliminate N+1 latency
    all_projects = {p.id: p.name for p in (await db.execute(select(Project))).scalars().all()}
    all_employees = {e.id: f"{e.first_name} {e.last_name}" for e in (await db.execute(select(Employee))).scalars().all()}

    response = []
    for t in tasks:
        p_name = all_projects.get(t.project_id, "Unknown")
        emp_name = all_employees.get(t.assigned_to_id, "Unassigned") if t.assigned_to_id else "Unassigned"

        response.append({
            "id": t.id,
            "title": t.title,
            "project_id": t.project_id,
            "project_name": p_name,
            "tracker": t.tracker,
            "status": t.status,
            "priority": t.priority,
            "due_date": str(t.due_date) if t.due_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "is_overdue": t.is_overdue,
            "is_blocked": t.is_blocked,
            "blocker_reason": t.blocker_reason,
            "assigned_to": emp_name,
            "estimated_hours": float(t.estimated_hours or 0.0),
            "progress_percentage": t.progress_percentage
        })

    return response

@router.post("/{task_id}/toggle-blocker")
async def toggle_task_blocker(
    task_id: str,
    payload: BlockerPayload,
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    """Flag or unflag a task as an operational blocker, creating an automated alert."""
    t_res = await db.execute(select(Task).where(Task.id == task_id))
    task = t_res.scalars().first()
    if not task or not scope.can_see_project(task.project_id):
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_blocked = payload.is_blocked
    task.blocker_reason = payload.blocker_reason if payload.is_blocked else None
    await db.commit()

    if task.is_blocked:
        # Trigger immediate critical alert
        await notification_service.create_and_dispatch(
            db=db,
            title=f"Blocker Flagged: {task.title}",
            message=f"Task has been flagged as blocked: '{task.blocker_reason or 'No reason specified'}'.",
            severity="CRITICAL",
            entity_type="TASK",
            entity_id=task.id
        )

    return {"success": True, "id": task.id, "is_blocked": task.is_blocked}

