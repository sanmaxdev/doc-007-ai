"""Storage interface — implemented by LocalStorage now, S3 later."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Persist bytes under `key`. Returns the stored location/key."""

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Read bytes for `key`."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object at `key` (no-op if missing)."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...
