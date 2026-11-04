from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.company import router as company_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.redmine import router as redmine_router
from app.api.v1.ai import router as ai_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.employees import router as employees_router
from app.api.v1.teams import router as teams_router
from app.api.v1.admin_config import router as admin_config_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(company_router)
api_router.include_router(notifications_router)
api_router.include_router(redmine_router)
api_router.include_router(ai_router)
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(employees_router)
api_router.include_router(teams_router)
api_router.include_router(admin_config_router)
api_router.include_router(reports_router)
