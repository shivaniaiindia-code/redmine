from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.models.project import Project
from app.models.task import Task

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/")
async def list_projects(
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    query = select(Project).order_by(desc(Project.created_at))
    result = await db.execute(query)
    projects = scope.filter_projects(result.scalars().all())

    response = []
    for p in projects:
        # Get task counts
        t_res = await db.execute(select(Task).where(Task.project_id == p.id))
        tasks = t_res.scalars().all()
        total_tasks = len(tasks)
        overdue_tasks = sum(1 for t in tasks if t.is_overdue and (t.progress_percentage or 0) < 100)
        blocked_tasks = sum(1 for t in tasks if t.is_blocked and (t.progress_percentage or 0) < 100)
        completed_tasks = sum(1 for t in tasks if t.status in ["DONE", "Resolved", "Closed", "Completed"] or (t.progress_percentage or 0) >= 100)

        response.append({
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "description": p.description,
            "status": p.status,
            "health_status": p.health_status,
            "health_reason": p.health_reason,
            "progress_percentage": float(p.progress_percentage or 0.0),
            "start_date": str(p.start_date) if p.start_date else None,
            "target_completion_date": str(p.target_completion_date) if p.target_completion_date else None,
            "total_tasks": total_tasks,
            "overdue_tasks": overdue_tasks,
            "blocked_tasks": blocked_tasks,
            "completed_tasks": completed_tasks
        })

    return response

