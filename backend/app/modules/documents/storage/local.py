"""Local filesystem storage provider (Slice 9C).

Backs `DOCUMENT_STORAGE_ROOT` (a named Docker volume in Compose, so files survive restarts and
image rebuilds - see docker-compose.yml). This is the ONLY place in the module that touches a
filesystem path; `storage_key` is opaque everywhere else.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from pathlib import Path
from typing import BinaryIO, ContextManager, Iterator

from app.modules.documents.contract import STORAGE_PROVIDER_LOCAL
from app.modules.documents.storage.base import (
    DocumentStorageError,
    DocumentStorageProvider,
    StorageKeyError,
    StorageObjectNotFoundError,
    StoredObject,
)

_READ_CHUNK_BYTES = 65536


class LocalFilesystemStorageProvider(DocumentStorageProvider):
    provider_code = STORAGE_PROVIDER_LOCAL

    def __init__(self, *, root: str) -> None:
        self._root = Path(root).resolve()
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            # The default root (`/app/document-store`) matches the Compose volume mount and is
            # correct inside the container, but it is a container-absolute path: anything
            # running outside the container - CI, or a developer invoking pytest on the host -
            # gets a bare `PermissionError: '/app'` from deep inside pathlib, which says
            # nothing about what to change. Name the setting instead.
            raise DocumentStorageError(
                f"Cannot use {self._root} as the document storage root: {exc}. "
                "Set DOCUMENT_STORAGE_ROOT to a writable directory for this environment "
                "(the default suits the container, where it is a mounted volume)."
            ) from exc

    def _resolve(self, storage_key: str) -> Path:
        """Resolve storage_key to an absolute path INSIDE the configured root, or refuse.

        This is the control the module docstring promises: "the service generates safe keys" is
        an assertion, this method is what actually refuses one that is not. A key containing
        `..`, an absolute path, or a symlink component that would resolve outside `self._root`
        is rejected here, before any filesystem operation touches it - never trusted because it
        "should" already be safe by construction upstream.
        """
        if not storage_key or storage_key.strip() != storage_key:
            raise StorageKeyError(f"Invalid storage key: {storage_key!r}")

        candidate = (self._root / storage_key).resolve()
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise StorageKeyError(
                f"Storage key {storage_key!r} resolves outside the configured storage root."
            ) from exc
        return candidate

    def save(self, *, storage_key: str, stream: BinaryIO, content_type: str) -> StoredObject:
        del content_type  # not needed for a local filesystem write; kept for interface symmetry
        destination = self._resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        byte_size = 0
        # Write to a temporary sibling file first, so a failure partway through (including the
        # caller's own size-limit wrapper raising mid-stream) never leaves a partially-written
        # file at the real storage_key. os.replace is atomic on the same filesystem, which a
        # sibling temp file guarantees.
        temp_path = destination.with_name(destination.name + f".part-{os.getpid()}")
        try:
            with open(temp_path, "wb") as handle:
                while True:
                    chunk = stream.read(_READ_CHUNK_BYTES)
                    if not chunk:
                        break
                    digest.update(chunk)
                    byte_size += len(chunk)
                    handle.write(chunk)
            os.replace(temp_path, destination)
        except Exception:
            with contextlib.suppress(OSError):
                temp_path.unlink()
            raise

        return StoredObject(
            storage_key=storage_key,
            byte_size=byte_size,
            checksum_sha256=digest.hexdigest(),
        )

    def open(self, *, storage_key: str) -> ContextManager[BinaryIO]:
        path = self._resolve(storage_key)
        if not path.is_file():
            raise StorageObjectNotFoundError(f"No stored object at key {storage_key!r}.")

        @contextlib.contextmanager
        def _opener() -> Iterator[BinaryIO]:
            handle = open(path, "rb")
            try:
                yield handle
            finally:
                handle.close()

        return _opener()

    def exists(self, *, storage_key: str) -> bool:
        try:
            return self._resolve(storage_key).is_file()
        except StorageKeyError:
            return False

    def delete(self, *, storage_key: str) -> None:
        path = self._resolve(storage_key)
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
