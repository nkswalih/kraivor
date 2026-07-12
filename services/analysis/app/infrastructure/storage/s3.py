from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()
from app.core.logging import get_logger
from app.domain.contracts.storage import AbstractStorage

logger = get_logger(__name__)


class S3Storage(AbstractStorage):
    """S3-compatible storage adapter supporting MinIO, AWS S3, Backblaze B2, R2.

    Uses the same boto3 API for all providers.
    """

    def __init__(self) -> None:
        config = Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30,
        )

        client_kwargs: dict[str, Any] = {  # type: ignore[explicit-any]
            "service_name": "s3",
            "config": config,
            "aws_access_key_id": settings.s3.access_key_id,
            "aws_secret_access_key": settings.s3.secret_access_key.get_secret_value(),
            "region_name": settings.s3.region,
            "use_ssl": settings.s3.use_ssl,
        }

        if settings.s3.endpoint_url:
            client_kwargs["endpoint_url"] = settings.s3.endpoint_url

        self._client = boto3.client(**client_kwargs)
        self._bucket = settings.s3.reports_bucket

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/json"
    ) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
            )
            logger.info("storage_upload", key=key, size=len(data))
            return key
        except ClientError as e:
            logger.error("storage_upload_failed", key=key, error=str(e))
            raise

    async def download(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            data = response["Body"].read()
            return data  # type: ignore[no-any-return]
        except ClientError as e:
            logger.error("storage_download_failed", key=key, error=str(e))
            raise

    async def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    async def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("storage_delete", key=key)
        except ClientError as e:
            logger.error("storage_delete_failed", key=key, error=str(e))
            raise

    async def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expiration,
            )
            return url  # type: ignore[no-any-return]
        except ClientError as e:
            logger.error("storage_presigned_url_failed", key=key, error=str(e))
            raise

    async def list_keys(self, prefix: str) -> list[str]:
        try:
            keys: list[str] = []
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        keys.append(obj["Key"])
            return keys
        except ClientError as e:
            logger.error("storage_list_failed", prefix=prefix, error=str(e))
            raise
