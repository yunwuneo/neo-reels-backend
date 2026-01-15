from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VideoUploadInitRequest(BaseModel):
    title: str | None = None
    filename: str = Field(min_length=1)
    content_type: str
    size_bytes: int = Field(gt=0)


class VideoUploadInitResponse(BaseModel):
    upload_url: str
    object_key: str
    video_id: UUID


class VideoUploadCompleteRequest(BaseModel):
    video_id: UUID


class VideoOut(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    title: str | None
    raw_object_key: str
    processed_object_key: str | None
    cover_object_key: str | None
    duration_sec: int | None
    created_at: datetime
    updated_at: datetime
    error_message: str | None

    model_config = {"from_attributes": True}


class FeedResponse(BaseModel):
    items: list[VideoOut]
    limit: int
    offset: int
    total: int
