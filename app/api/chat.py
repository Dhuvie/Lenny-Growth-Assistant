import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import SessionModel
from app.schemas.chat import ChatRequest
from app.agent.orchestrator import AgentOrchestrator
from app.core.logging import log_event

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("")
async def send_chat_message(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a message into a session and streams back the assistant response via SSE,
    complete with grounded citations and generated artifacts.
    """
    # Verify session exists
    stmt = select(SessionModel).where(SessionModel.id == payload.session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{payload.session_id}' not found."
        )

    # Automatically rename session if it has default title
    if session.title == "New Growth Conversation":
        new_title = payload.content[:35] + ("..." if len(payload.content) > 35 else "")
        session.title = new_title
        await db.commit()

    async def event_generator():
        try:
            async for event in AgentOrchestrator.run(
                session_id=payload.session_id,
                user_message=payload.content,
                db=db,
                stream=True,
                override_provider=payload.provider,
                override_model=payload.model
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            log_event("API", f"Error during chat stream: {e}")
            err_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(err_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
