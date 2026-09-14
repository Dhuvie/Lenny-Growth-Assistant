from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.db.session import get_db
from app.db.models import SessionModel, MessageModel
from app.schemas.session import SessionCreate, SessionUpdate, SessionRead, SessionDetailRead
from app.schemas.message import MessageRead

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = SessionModel(
        title=payload.title or "New Growth Conversation",
        session_metadata=payload.session_metadata
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionRead(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        session_metadata=session.session_metadata,
        message_count=0
    )


@router.get("", response_model=List[SessionRead])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(SessionModel, func.count(MessageModel.id).label("msg_count"))
        .outerjoin(MessageModel, SessionModel.id == MessageModel.session_id)
        .group_by(SessionModel.id)
        .order_by(SessionModel.updated_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    sessions = []
    for s, count in rows:
        sessions.append(SessionRead(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
            session_metadata=s.session_metadata,
            message_count=count
        ))
    return sessions


@router.get("/{session_id}", response_model=SessionDetailRead)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    msg_stmt = (
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
    )
    msg_res = await db.execute(msg_stmt)
    messages = msg_res.scalars().all()

    return SessionDetailRead(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        session_metadata=session.session_metadata,
        message_count=len(messages),
        messages=[MessageRead.model_validate(m) for m in messages]
    )


@router.patch("/{session_id}", response_model=SessionRead)
async def update_session(session_id: str, payload: SessionUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )

    if payload.title is not None:
        session.title = payload.title
    if payload.session_metadata is not None:
        session.session_metadata = payload.session_metadata

    await db.commit()
    await db.refresh(session)
    return SessionRead.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found."
        )
    await db.delete(session)
    await db.commit()
    return None
