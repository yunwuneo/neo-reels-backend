from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.video import Video
from app.schemas.video import FeedResponse, VideoOut

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=FeedResponse)
async def feed(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> FeedResponse:
    limit = min(max(limit, 1), 50)
    offset = max(offset, 0)

    total_result = await session.execute(select(func.count()).select_from(Video))
    total = total_result.scalar_one()

    result = await session.execute(
        select(Video).order_by(Video.created_at.desc()).offset(offset).limit(limit)
    )
    items = [VideoOut.model_validate(video) for video in result.scalars().all()]
    return FeedResponse(items=items, limit=limit, offset=offset, total=total)
