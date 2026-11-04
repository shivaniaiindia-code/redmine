from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.permissions import require_roles, CurrentUser, RequireAdminOrManagement
from app.models.user import UserRole
from app.schemas.company import CompanyDashboardData
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/company", tags=["Company Dashboard"])

@router.get("/dashboard", response_model=CompanyDashboardData)
@router.get("/overview", response_model=CompanyDashboardData)
async def get_company_dashboard(
    current_user: RequireAdminOrManagement,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns full Company Intelligence Platform Dashboard metrics matching the enterprise layout:
    - 6 Top KPI metric cards
    - Project status overview donut chart
    - Task distribution bar chart
    - Team workload stacked bar chart
    - Upcoming deadlines feed
    - Recent activities feed
    - System notification bar drawer items (mirrored to Admin Google Chat)
    """
    return await analytics_service.get_dashboard_metrics(db)

