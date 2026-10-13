from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentMetadataCreate(BaseModel):
    document_type: str = Field(..., min_length=1, max_length=100)
    linked_record_type: str = Field(..., min_length=1, max_length=100)
    linked_record_public_id: UUID
    file_name: str = Field(..., min_length=1, max_length=255)
    original_file_name: str | None = Field(default=None, max_length=255)
    storage_mode: str = Field(default="external_link", max_length=50)
    storage_path_or_url: str | None = Field(default=None, max_length=1000)
    version_no: int = Field(default=1, ge=1)
    status: str = Field(default="Linked", max_length=50)
    remarks: str | None = Field(default=None, max_length=1000)


class DocumentMetadataResponse(BaseModel):
    public_id: UUID
    document_type: str
    linked_record_type: str
    linked_record_public_id: UUID
    file_name: str
    original_file_name: str | None = None
    storage_mode: str
    storage_path_or_url: str | None = None
    version_no: int
    status: str
    # Slice 9C. All four are None for a pre-9C row (external_link/future_sharepoint, or a
    # local_upload row that predates this slice - none exist, per the slice document's
    # verification against the live database, but the field stays nullable for that reason).
    content_type: str | None = None
    byte_size: int | None = None
    checksum_sha256: str | None = None
    retention_due_at: str | None = None
    uploaded_by: UUID | None = None
    uploaded_at: str | None = None
    remarks: str | None = None


class DocumentTypeResponse(BaseModel):
    code: str
    name: str
    description: str


class DocumentMetadataCreatedResponse(BaseModel):
    document: DocumentMetadataResponse
    event: dict[str, Any]


class DocumentUploadedResponse(BaseModel):
    """Response for POST /api/documents/upload (Slice 9C)."""

    document: DocumentMetadataResponse
    event: dict[str, Any]
