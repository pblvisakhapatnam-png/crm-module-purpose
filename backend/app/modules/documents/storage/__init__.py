"""Document storage provider abstraction (Slice 9C).

One local filesystem provider today, behind a provider-neutral interface. The later move to
SharePoint is intended to be a provider swap plus a file migration, not a rewrite: no filesystem
concept appears in `base.DocumentStorageProvider`, in `document_metadata`, or anywhere in
`documents/service.py` - only `storage_provider_code` and an opaque `storage_key`.

Two distinct lookups, and the difference matters:

- `get_storage_provider()` returns the provider to WRITE new objects through - whatever this
  deployment is currently configured to use.
- `get_storage_provider_by_code(code)` returns the provider that holds an EXISTING object,
  resolved from the `storage_provider_code` recorded on its row. Reads must use this one. Using
  the configured provider to open an object stored by a different one is exactly the silent
  wrong-backend resolution the recorded column exists to prevent (independent review, correction
  pass 1, finding 3).
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.modules.documents.contract import STORAGE_PROVIDER_LOCAL
from app.modules.documents.storage.base import (
    DocumentStorageProvider,
    UnknownStorageProviderError,
)
from app.modules.documents.storage.local import LocalFilesystemStorageProvider

__all__ = [
    "DocumentStorageProvider",
    "UnknownStorageProviderError",
    "get_storage_provider",
    "get_storage_provider_by_code",
]


@lru_cache
def get_storage_provider_by_code(provider_code: str) -> DocumentStorageProvider:
    """Resolve a specific provider by its recorded code, or fail closed.

    Never falls back to the configured provider for an unrecognised code: a row naming a
    provider this deployment cannot resolve means the bytes are somewhere this process does not
    know how to reach, and answering with a different backend's view of that storage key would
    be worse than refusing.

    Cached because a filesystem provider is cheap to reuse and stateless beyond its configured
    root.
    """
    if provider_code == STORAGE_PROVIDER_LOCAL:
        return LocalFilesystemStorageProvider(root=get_settings().document_storage_root)
    raise UnknownStorageProviderError(
        f"No storage provider is registered for code {provider_code!r} in this deployment."
    )


def get_storage_provider() -> DocumentStorageProvider:
    """The provider new objects are written through, selected by configuration.

    Configuration rather than a hard-coded import, so a future provider (SharePoint) is added by
    registering it in `get_storage_provider_by_code` and pointing the setting at it, not by
    changing every caller.
    """
    settings = get_settings()
    return get_storage_provider_by_code(
        getattr(settings, "document_storage_provider", STORAGE_PROVIDER_LOCAL)
    )
