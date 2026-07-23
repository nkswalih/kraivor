from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.score_history import (
    ScoreHistoryEntryResponse,
    ScoreHistoryListResponse,
)
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/score-history", tags=["score-history"])


@router.get("/{repo_id}", response_model=ScoreHistoryListResponse)
async def list_score_history(
    repo_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Max entries to return"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ScoreHistoryListResponse:
    entries = await uow.score_history.get_by_repo(repo_id, limit=limit)
    return ScoreHistoryListResponse(
        entries=[ScoreHistoryEntryResponse(**e) for e in entries],  # type: ignore[arg-type]
        total=len(entries),
    )
