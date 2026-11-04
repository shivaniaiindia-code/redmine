from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.permissions import CurrentUser
from app.core.scope import Scope
from app.services.ai_service import ai_service
from app.services.alert_composer import AlertComposer

router = APIRouter(prefix="/ai", tags=["AI Assistant"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[ChatMessage]] = None

@router.post("/chat")
async def chat_with_assistant(
    req: ChatRequest,
    current_user: CurrentUser,
    scope: Scope,
    db: AsyncSession = Depends(get_db)
):
    """
    OpenRouter Conversational Assistant powered by Qwen3.5-Flash.
    Uses deterministic Python tools to retrieve live database ground truth
    (projects, overdue tasks, blockers, employees) ensuring zero hallucination.
    """
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history] if req.history else None
    result = await ai_service.answer_management_query(
        db=db,
        prompt=req.prompt,
        conversation_history=history_dicts,
        scope=scope,
    )
    # Users see plain words, never internal status codes (AT_RISK → "at risk")
    result["response"] = AlertComposer.humanize(result.get("response", ""))
    return result

