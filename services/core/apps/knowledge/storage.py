import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage, default_storage

logger = logging.getLogger(__name__)


class KnowledgeAssetStorage:
    """
    File storage adapter for KnowledgeAsset files.

    Development: uses Django's FileSystemStorage (local MEDIA_ROOT).
    Production: swap _get_storage() to return an S3Storage or MinIO
    client and implement _generate_url() to return pre-signed URLs.

    File layout:  knowledge/<knowledge_space_id>/<uuid>_<original_name>
    """

    def _get_storage(self):
        if hasattr(settings, "KNOWLEDGE_STORAGE") and callable(
            settings.KNOWLEDGE_STORAGE
        ):
            return settings.KNOWLEDGE_STORAGE()
        return default_storage

    def _generate_url(self, storage_key: str) -> str:
        if isinstance(self._get_storage(), FileSystemStorage):
            return self._get_storage().url(storage_key)
        return None

    def save(
        self, knowledge_space_id: uuid.UUID, file_field
    ) -> tuple[str, int, str, str | None]:
        """
        Save an uploaded file to storage.

        Returns: (storage_key, file_size, mime_type, url)
        """
        storage = self._get_storage()
        original_name = file_field.name
        ext = Path(original_name).suffix or ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        storage_key = f"knowledge/{knowledge_space_id}/{unique_name}"

        saved_path = storage.save(storage_key, file_field)
        file_size = file_field.size
        mime_type = getattr(file_field, "content_type", "application/octet-stream")
        url = self._generate_url(saved_path)

        logger.info(
            "asset.file_saved",
            extra={
                "storage_key": saved_path,
                "size": file_size,
                "mime": mime_type,
                "knowledge_space_id": str(knowledge_space_id),
            },
        )

        return saved_path, file_size, mime_type, url

    def delete(self, storage_key: str) -> None:
        """Delete a file from storage. Silently succeeds if missing."""
        try:
            self._get_storage().delete(storage_key)
            logger.info("asset.file_deleted", extra={"storage_key": storage_key})
        except Exception as exc:
            logger.warning(
                "asset.file_delete_failed",
                extra={"storage_key": storage_key, "error": str(exc)},
            )
