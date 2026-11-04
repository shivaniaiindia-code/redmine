from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.models.redmine_sync import RedmineSyncState
from app.services.redmine_service import redmine_service
from app.core.config import settings

router = APIRouter(prefix="/redmine", tags=["Redmine Integration"])

class RedmineConfigPayload(BaseModel):
    url: Optional[str] = None
    api_key: Optional[str] = None

@router.get("/status")
async def get_redmine_status(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """Check connectivity and last sync watermark from Redmine."""
    conn_info = await redmine_service.test_connection()
    state_res = await db.execute(select(RedmineSyncState).where(RedmineSyncState.entity_type == "ISSUES"))
    sync_state = state_res.scalars().first()

    return {
        "connected": conn_info.get("connected", False),
        "base_url": conn_info.get("base_url"),
        "error": conn_info.get("error"),
        "last_synced_at": sync_state.last_sync_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if sync_state else "Never",
        "records_synced": sync_state.records_synced if sync_state else 0,
        "status": sync_state.status if sync_state else "IDLE",
        "syncing_now": redmine_service.is_syncing(),
        "auto_sync_interval_seconds": int(max(15.0, settings.REDMINE_SYNC_INTERVAL_MINUTES * 60)),
        "next_sync_at": redmine_service.next_sync_at.strftime("%Y-%m-%d %H:%M:%S UTC") if redmine_service.next_sync_at else None,
        "last_sync_summary": redmine_service.last_sync_summary,
    }

@router.post("/sync/trigger", status_code=status.HTTP_200_OK)
async def trigger_redmine_sync(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers immediate bidirectional delta synchronization:
    - Syncs projects, issues, assignees from Redmine
    - Generates automated alerts for Admin (overdue, blockers, risk)
    - Returns detailed synchronization statistics
    """
    summary = await redmine_service.sync_all(db)
    return {
        "success": True,
        "message": "Redmine delta synchronization completed successfully",
        "summary": summary
    }

