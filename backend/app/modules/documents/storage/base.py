"""Storage provider interface (Slice 9C).

Every method takes and returns provider-neutral values: an opaque `storage_key` the SERVICE
LAYER generates (never the caller, and never derived from a caller-supplied file name), a byte
stream, and a content type. No provider-specific concept - a filesystem path, a SharePoint drive
item id - crosses this boundary. That is what makes a future SharePoint provider a swap rather
than a rewrite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, ContextManager


class DocumentStorageError(Exception):
    """Base class for storage-provider failures."""


class StorageKeyError(DocumentStorageError):
    """Raised when a storage_key does not resolve to a location inside the provider's root.

    This is the control, not the caller's care. "The service only ever generates safe keys" is
    an assertion; a provider that does not itself refuse an escaping key has no control at all -
    it merely has not yet been asked to prove one. Every provider implementation must raise this
    for any key that would resolve outside its configured storage root, regardless of how that
    key was produced.
    """


class StorageObjectNotFoundError(DocumentStorageError):
    """Raised by `open()` when no object exists at the given storage_key."""


class UnknownStorageProviderError(DocumentStorageError):
    """Raised when a stored `storage_provider_code` names a provider this deployment cannot
    resolve.

    Fail-closed by design. A document row records which provider holds its bytes precisely so
    the object can be resolved back to that provider after a provider swap; falling back to the
    currently-configured provider instead would silently resolve content through the wrong
    backend - which is the defect this exception exists to prevent (independent review,
    correction pass 1, finding 3).
    """


@dataclass(frozen=True)
class StoredObject:
    """What a provider reports back after successfully storing bytes.

    Provider-neutral: byte_size and checksum_sha256 are computable by any provider, and
    storage_key is already opaque by construction. Nothing here names a filesystem path.
    """

    storage_key: str
    byte_size: int
    checksum_sha256: str


class DocumentStorageProvider(ABC):
    """Provider-neutral document storage contract.

    provider_code is the value persisted in document_metadata.storage_provider_code, so a stored
    object's future can be resolved back to the provider that holds it even after a provider
    swap changes which one is currently configured.
    """

    provider_code: str

    @abstractmethod
    def save(self, *, storage_key: str, stream: BinaryIO, content_type: str) -> StoredObject:
        """Store the bytes read from `stream` under `storage_key`.

        Implementations must count bytes as they are read from `stream`, not trust any
        caller-declared size, and must refuse (via StorageKeyError) before writing anything if
        `storage_key` would resolve outside the provider's root.
        """

    @abstractmethod
    def open(self, *, storage_key: str) -> ContextManager[BinaryIO]:
        """Return a context manager yielding a readable binary stream for `storage_key`.

        Raises StorageObjectNotFoundError if nothing is stored there, or StorageKeyError if the
        key does not resolve inside the provider's root.
        """

    @abstractmethod
    def exists(self, *, storage_key: str) -> bool:
        """Whether an object is currently stored at `storage_key`."""

    @abstractmethod
    def delete(self, *, storage_key: str) -> None:
        """Remove the object at `storage_key`, if present. A no-op if it is already absent."""
