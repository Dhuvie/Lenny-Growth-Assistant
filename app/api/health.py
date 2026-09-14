from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import EpisodeModel, TranscriptChunkModel
from app.schemas.health import HealthResponse, LLMProviderStatus
from app.agent.providers.factory import get_llm_provider
from app.core.logging import log_event

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Evaluates DB reachability, active LLM provider connectivity,
    and returns indexed corpus metrics. Returns 503 if any core dependency fails.
    """
    db_status = "connected"
    indexed_episodes = 0
    indexed_chunks = 0

    # 1. Check Database connectivity
    try:
        await db.execute(text("SELECT 1;"))
        ep_count_stmt = select(func.count(EpisodeModel.id))
        chunk_count_stmt = select(func.count(TranscriptChunkModel.id))
        indexed_episodes = (await db.execute(ep_count_stmt)).scalar() or 0
        indexed_chunks = (await db.execute(chunk_count_stmt)).scalar() or 0
    except Exception as e:
        db_status = f"error: {str(e)}"
        log_event("DB", f"Health check DB ping failed: {e}")

    # 2. Check active LLM provider reachability
    provider = get_llm_provider()
    provider_health = await provider.check_health()

    is_healthy = (db_status == "connected") and (provider_health.status == "reachable")

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy" if db_status != "connected" else "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        llm_provider=LLMProviderStatus(
            provider=provider_health.provider,
            model=provider_health.model,
            status=provider_health.status,
            latency_ms=provider_health.latency_ms,
            detail=provider_health.detail
        ),
        indexed_episodes=indexed_episodes,
        indexed_chunks=indexed_chunks,
        timestamp=datetime.now(timezone.utc)
    )
