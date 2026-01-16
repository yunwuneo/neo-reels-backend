import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.user import User
from app.models.video import Video
from app.schemas.video import (
    VideoOut,
    VideoUploadCompleteRequest,
    VideoUploadInitRequest,
    VideoUploadInitResponse,
)
from app.services.storage import generate_presigned_put_url, object_exists
from app.tasks.worker import celery_app

router = APIRouter(prefix="/videos", tags=["videos"])


def _safe_filename(filename: str) -> str:
    return os.path.basename(filename)


@router.post("/upload/init", response_model=VideoUploadInitResponse)
async def init_upload(
    payload: VideoUploadInitRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> VideoUploadInitResponse:
    settings = get_settings()
    if payload.content_type not in settings.allowed_content_types:
        raise AppError("invalid_content_type", "Unsupported content type", status_code=400)
    if payload.size_bytes > settings.max_upload_size_bytes:
        raise AppError("file_too_large", "File too large", status_code=400)

    safe_name = _safe_filename(payload.filename)
    suffix = Path(safe_name).suffix or ".bin"
    video = Video(
        user_id=current_user.id,
        status="pending",
        title=payload.title,
        raw_object_key="",
    )
    session.add(video)
    await session.flush()

    object_key = f"raw/{video.id}/{video.id}{suffix}"
    video.raw_object_key = object_key
    await session.commit()
    await session.refresh(video)

    upload_url = generate_presigned_put_url(object_key, payload.content_type)
    return VideoUploadInitResponse(upload_url=upload_url, object_key=object_key, video_id=video.id)


@router.post("/upload/complete", response_model=VideoOut)
async def complete_upload(
    payload: VideoUploadCompleteRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> VideoOut:
    result = await session.execute(select(Video).where(Video.id == payload.video_id))
    video = result.scalar_one_or_none()
    if video is None:
        raise AppError("video_not_found", "Video not found", status_code=404)
    if video.user_id != current_user.id:
        raise AppError("forbidden", "No access to this video", status_code=403)

    if video.status in {"processing", "ready"}:
        return VideoOut.model_validate(video)

    if not object_exists(video.raw_object_key):
        raise AppError("upload_missing", "Uploaded object not found", status_code=400)

    video.status = "processing"
    video.error_message = None
    await session.commit()
    await session.refresh(video)

    celery_app.send_task("transcode_video", args=[str(video.id)])
    return VideoOut.model_validate(video)


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(video_id: UUID, session: AsyncSession = Depends(get_session)) -> VideoOut:
    result = await session.execute(select(Video).where(Video.id == video_id))
    video = result.scalar_one_or_none()
    if video is None:
        raise AppError("video_not_found", "Video not found", status_code=404)
    return VideoOut.model_validate(video)
