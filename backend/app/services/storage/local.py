from pathlib import Path
from typing import BinaryIO, Optional
from backend.app.core.config import settings
from backend.app.services.storage.base import BaseStorageService


class LocalStorageService(BaseStorageService):
    """Local filesystem storage provider with path isolation and chunked streaming."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, storage_key: str) -> Path:
        # Sanitize storage_key
        clean_key = storage_key.lstrip("/\\").replace("\\", "/")
        target_path = (self.base_dir / clean_key).resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise ValueError(f"Directory traversal detected for storage key: {storage_key}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path

    def save_file(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        target_path = self._resolve_path(storage_key)
        try:
            file_obj.seek(0)
        except Exception:
            pass
        with open(target_path, "wb") as f_out:
            while True:
                chunk = file_obj.read(1024 * 1024)
                if not chunk:
                    break
                f_out.write(chunk)
        return storage_key

    def save_bytes(self, data: bytes, storage_key: str) -> str:
        target_path = self._resolve_path(storage_key)
        with open(target_path, "wb") as f_out:
            f_out.write(data)
        return storage_key

    def get_file_path_or_url(self, storage_key: str) -> str:
        target_path = self._resolve_path(storage_key)
        return str(target_path)

    def delete_file(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        if target_path.exists():
            try:
                target_path.unlink()
                return True
            except OSError:
                return False
        return False

    def exists(self, storage_key: str) -> bool:
        target_path = self._resolve_path(storage_key)
        return target_path.exists()

    def get_download_url(self, storage_key: str, expires_in: int = 3600) -> str:
        return f"{settings.API_V1_STR}/videos/stream/{storage_key}"
