import asyncio
import logging
import os
import subprocess
import tempfile
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.video import Video
from app.services.storage import get_s3_client
from app.tasks.worker import celery_app

logger = logging.getLogger(__name__)


async def _get_video(video_id: str) -> Video | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        )
        return result.scalar_one_or_none()


async def _update_video(
    video_id: str,
    status: str,
    processed_key: str | None = None,
    cover_key: str | None = None,
    duration_sec: int | None = None,
    error_message: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Video).where(Video.id == uuid.UUID(video_id))
        )
        video = result.scalar_one_or_none()
        if video is None:
            return
        video.status = status
        if processed_key is not None:
            video.processed_object_key = processed_key
        if cover_key is not None:
            video.cover_object_key = cover_key
        if duration_sec is not None:
            video.duration_sec = duration_sec
        video.error_message = error_message
        await session.commit()


def _ffmpeg_run(args: list[str]) -> None:
    subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _get_duration_sec(input_path: str) -> int | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_path,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    value = result.stdout.strip()
    if not value:
        return None
    return int(float(value))


@celery_app.task(bind=True, name="transcode_video")
def transcode_video(self, video_id: str) -> None:
    settings = get_settings()
    client = get_s3_client()

    logger.info("video_status_change video_id=%s status=processing", video_id)

    async def _process() -> None:
        video = await _get_video(video_id)
        if video is None:
            return
        if video.status == "ready":
            return
        await _update_video(video_id, status="processing", error_message=None)

        with tempfile.TemporaryDirectory(prefix="transcode_") as tmpdir:
            input_path = os.path.join(tmpdir, "input")
            client.download_file(settings.minio_bucket, video.raw_object_key, input_path)

            output_video = os.path.join(tmpdir, "output_720p.mp4")
            cover_path = os.path.join(tmpdir, "cover.jpg")

            _ffmpeg_run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path,
                    "-vf",
                    "scale=-2:720",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    output_video,
                ]
            )

            _ffmpeg_run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "1",
                    "-i",
                    input_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    cover_path,
                ]
            )

            duration = _get_duration_sec(input_path)

            processed_key = f"processed/{video_id}/video_720p.mp4"
            cover_key = f"processed/{video_id}/cover.jpg"

            client.upload_file(
                output_video,
                settings.minio_bucket,
                processed_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )
            client.upload_file(
                cover_path,
                settings.minio_bucket,
                cover_key,
                ExtraArgs={"ContentType": "image/jpeg"},
            )

            await _update_video(
                video_id,
                status="ready",
                processed_key=processed_key,
                cover_key=cover_key,
                duration_sec=duration,
                error_message=None,
            )
            logger.info("video_status_change video_id=%s status=ready", video_id)

    try:
        asyncio.run(_process())
    except Exception as exc:
        message = str(exc)
        asyncio.run(_update_video(video_id, status="failed", error_message=message))
        logger.exception("video_status_change video_id=%s status=failed", video_id)
        raise
