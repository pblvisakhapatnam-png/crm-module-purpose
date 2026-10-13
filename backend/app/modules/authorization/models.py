from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.authorization.contract import AUTHZ_PERMISSION_TABLE, AUTHZ_ROLE_PERMISSION_TABLE


class AuthzPermission(Base):
    """An explicit, stable application-permission code (PF-1A-E1).

    This is a coarse-grained application permission used for backend route
    authorization. It is deliberately not a business authority (see ORA-001):
    it never encodes an employee name, a designation, an HR position or a
    named approver.
    """

    __tablename__ = AUTHZ_PERMISSION_TABLE

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    permission_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class AuthzRolePermission(Base):
    """Compatibility mapping: an existing transitional application role grants a permission.

    `role_code` references the existing `role.role_code` (the same six
    transitional roles routes currently check). This table is the durable
    equivalent of the pre-PF-1A-E1 `require_roles(*SOME_ROLES)` route guards;
    it does not introduce a new role, authority or organization concept.
    """

    __tablename__ = AUTHZ_ROLE_PERMISSION_TABLE
    __table_args__ = (
        UniqueConstraint("role_code", "permission_id", name="uq_authz_role_permission_role_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    role_code: Mapped[str] = mapped_column(String(50), ForeignKey("role.role_code"), nullable=False)
    permission_id: Mapped[int] = mapped_column(ForeignKey(f"{AUTHZ_PERMISSION_TABLE}.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
