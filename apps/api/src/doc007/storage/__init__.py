"""File storage abstraction.

`get_storage()` returns the configured backend. Local now; an S3/MinIO
backend can be dropped in later by implementing the same `Storage` interface.
"""

from __future__ import annotations

from doc007.core.config import settings
from doc007.storage.base import Storage
from doc007.storage.local import LocalStorage


def get_storage() -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_local_path)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
