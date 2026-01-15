from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings


@lru_cache
def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name=settings.minio_region,
    )


def generate_presigned_put_url(object_key: str, content_type: str, expires_in: int = 900) -> str:
    settings = get_settings()
    client = get_s3_client()
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.minio_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )


def object_exists(object_key: str) -> bool:
    settings = get_settings()
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.minio_bucket, Key=object_key)
        return True
    except ClientError:
        return False
