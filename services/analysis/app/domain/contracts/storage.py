from abc import ABC, abstractmethod


class AbstractStorage(ABC):
    """Contract for object storage (S3, MinIO, etc.)."""

    @abstractmethod
    async def upload(
        self, key: str, data: bytes, content_type: str = "application/json"
    ) -> str:
        """Upload data to storage. Returns the object key."""
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download data from storage."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if an object exists in storage."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object from storage."""
        ...

    @abstractmethod
    async def get_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> str:
        """Generate a presigned URL for temporary access."""
        ...

    @abstractmethod
    async def list_keys(self, prefix: str) -> list[str]:
        """List all keys with a given prefix."""
        ...
