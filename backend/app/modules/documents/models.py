from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentMetadata(Base):
    __tablename__ = "document_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    linked_record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linked_record_public_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path_or_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Uploaded")
    # Slice 9C - Document Storage Foundation. All nullable: absent for a metadata-only row
    # (external_link/future_sharepoint) and required together only when storage_mode =
    # 'local_upload', which the ck_document_metadata_local_upload_has_bytes CHECK constraint
    # (added by Alembic revision 20260908_0034) enforces at the database, not here.
    storage_provider_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Shape only - owner decision 4 (8 September 2026): retention is not decided now. Never set
    # by this slice's code; nothing purges against it. See the Alembic migration docstring.
    retention_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    remarks: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "storage_mode <> 'local_upload' OR ("
            "storage_provider_code IS NOT NULL AND "
            "storage_key IS NOT NULL AND "
            "byte_size IS NOT NULL AND "
            "checksum_sha256 IS NOT NULL"
            ")",
            name="ck_document_metadata_local_upload_has_bytes",
        ),
    )
