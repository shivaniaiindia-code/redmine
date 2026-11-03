---
name: backend-fastapi-rbac
description: >-
  Use this skill whenever creating, modifying, or securing FastAPI routes,
  SQLAlchemy 2.0 async models, Alembic migrations, or RBAC security dependencies.
---

# Backend Architecture & RBAC Implementation Skill

This skill provides step-by-step procedures and standards for the **Backend Agent** implementing the FastAPI and SQLAlchemy 2.0 service layer.

---

## 1. Directory & Layer Organization

All backend code lives in `/backend/app/`:
```
backend/app/
├── api/v1/          # Route handlers (HTTP requests/responses only)
├── core/            # Config, security, database session, RBAC guards
├── models/          # SQLAlchemy 2.0 ORM models (DeclarativeBase)
├── schemas/         # Pydantic v2 schemas (In/Out/Update)
├── services/        # Pure business logic (transactions, integrations)
└── workers/         # Background scheduler jobs
```

---

## 2. SQLAlchemy 2.0 Async Session Pattern

Always use modern SQLAlchemy 2.0 `select()` syntax with async sessions:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.task import Task
from app.models.project import Project

async def get_dashboard_metrics(db: AsyncSession) -> dict:
    # 1. Active Projects Count
    proj_query = select(func.count()).select_from(Project).where(Project.status == "ACTIVE")
    active_projects = (await db.execute(proj_query)).scalar() or 0

    # 2. Open Tasks Count
    task_query = select(func.count()).select_from(Task).where(Task.status.in_(["New", "In Progress", "Feedback"]))
    open_tasks = (await db.execute(task_query)).scalar() or 0

    # 3. Tasks at Risk / Overdue
    overdue_query = select(func.count()).select_from(Task).where(Task.is_overdue == True)
    overdue_tasks = (await db.execute(overdue_query)).scalar() or 0

    return {
        "active_projects": active_projects,
        "open_tasks": open_tasks,
        "overdue_tasks": overdue_tasks
    }
```

---

## 3. Strict RBAC Dependency Injection

Every protected route must inject `current_user` and validate permitted roles:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User, UserRole

def require_roles(allowed_roles: list[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in [r.value for r in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {allowed_roles}"
            )
        return current_user
    return role_checker

# Example route usage:
router = APIRouter()

@router.get("/admin/audit-logs", dependencies=[Depends(require_roles([UserRole.SUPER_ADMIN]))])
async def get_audit_logs(db: AsyncSession = Depends(get_db)):
    ...
```

---

## 4. Error Envelope & Logging Standards

Never return raw Python exceptions to the client:
```python
from pydantic import BaseModel
from typing import Any, Optional

class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[dict] = None
```

