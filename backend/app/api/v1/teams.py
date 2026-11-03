from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.models.team import Team, TeamMember
from app.models.project import Project

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.get("/")
async def list_teams(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    t_res = await db.execute(select(Team).order_by(Team.name))
    teams = t_res.scalars().all()

    response = []
    for team in teams:
        m_res = await db.execute(select(TeamMember).where(TeamMember.team_id == team.id))
        members = m_res.scalars().all()

        p_res = await db.execute(select(Project).where(Project.primary_team_id == team.id))
        projects = p_res.scalars().all()

        response.append({
            "id": team.id,
            "name": team.name,
            "department": team.department,
            "description": team.description,
            "is_active": team.is_active,
            "members_count": len(members),
            "projects_count": len(projects),
            "projects": [{"id": p.id, "name": p.name, "health_status": p.health_status} for p in projects]
        })

    return response

