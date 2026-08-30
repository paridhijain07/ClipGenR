import abc
from typing import BinaryIO, Optional


class BaseStorageService(abc.ABC):
    """Abstract interface for object storage providers (Local, S3, MinIO)."""

    @abc.abstractmethod
    def save_file(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Save a file-like object to storage and return its storage key."""
        pass

    @abc.abstractmethod
    def get_file_path_or_url(self, storage_key: str) -> str:
        """Get absolute local filesystem path or signed URL for reading."""
        pass

    @abc.abstractmethod
    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from storage."""
        pass

    @abc.abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abc.abstractmethod
    def get_download_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a download URL."""
        pass
