from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.models.employee import Employee
from app.models.task import Task

router = APIRouter(prefix="/employees", tags=["Employees"])

@router.get("/")
async def list_employees(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    e_res = await db.execute(select(Employee).order_by(Employee.first_name))
    employees = e_res.scalars().all()

    response = []
    for emp in employees:
        tasks_res = await db.execute(select(Task).where(Task.assigned_to_id == emp.id))
        emp_tasks = tasks_res.scalars().all()

        total_tasks = len(emp_tasks)
        overdue_tasks = sum(1 for t in emp_tasks if t.is_overdue)
        completed_tasks = sum(1 for t in emp_tasks if t.status in ["DONE", "Resolved", "Closed"])

        response.append({
            "id": emp.id,
            "name": f"{emp.first_name} {emp.last_name}",
            "email": emp.email,
            "job_title": emp.job_title,
            "department": emp.department,
            "status": emp.status,
            "weekly_capacity_hours": float(emp.weekly_capacity_hours or 40.0),
            "total_tasks": total_tasks,
            "overdue_tasks": overdue_tasks,
            "completed_tasks": completed_tasks
        })

    return response

