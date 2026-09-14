import uuid
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import MessageModel, SessionModel
from app.schemas.artifact import ArtifactCreate, ArtifactResponse

router = APIRouter(prefix="/api/artifacts", tags=["Artifacts"])


@router.post("", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    payload: ArtifactCreate,
    db: AsyncSession = Depends(get_db)
):
    # Verify session exists
    stmt = select(SessionModel).where(SessionModel.id == payload.session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{payload.session_id}' not found."
        )

    word_count = len(re.findall(r"\b\w+\b", payload.content))
    artifact_id = str(uuid.uuid4())
    artifact_dict = {
        "id": artifact_id,
        "title": payload.title,
        "type": payload.type,
        "content": payload.content,
        "word_count": word_count,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Store as an assistant message containing the artifact
    msg = MessageModel(
        session_id=payload.session_id,
        role="assistant",
        content=f"Saved artifact: **{payload.title}**",
        sources=[],
        artifacts=[artifact_dict],
        model_provider="manual"
    )
    db.add(msg)
    await db.commit()

    return ArtifactResponse(
        id=artifact_id,
        session_id=payload.session_id,
        title=payload.title,
        type=payload.type,
        content=payload.content,
        word_count=word_count,
        created_at=datetime.now(timezone.utc)
    )
