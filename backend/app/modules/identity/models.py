from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppUser(Base):
    __tablename__ = "app_user"

    # Username uniqueness is enforced case-insensitively by a unique expression index rather than
    # a plain UNIQUE column, matching the case-insensitive login lookup in this module's
    # repository. See Alembic revision 20260629_0001.
    __table_args__ = (
        Index("ux_app_user_username_lower", text("lower(username)"), unique=True),
        CheckConstraint("token_version >= 0", name="ck_app_user_token_version_not_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Carried in every sign-in token; raising it ends every earlier sign-in (TB-1 TB1-204 part a, revision
    # 20260908_0048).
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    role_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SignInAttempt(Base):
    """One recent sign-in attempt for a typed username (TB-1 TB1-204 part a).

    Keyed to the SHA-256 of the lower-cased typed name, never the name itself, and kept whether or not an account has
    that name; numbered by the table's sequence, never reused. See `app.modules.identity.throttle` and revision
    20260908_0048.
    """

    __tablename__ = "sign_in_attempt"
    __table_args__ = (
        CheckConstraint("username_digest ~ '^[0-9a-f]{64}$'", name="ck_sign_in_attempt_username_digest_hex"),
        Index("ix_sign_in_attempt_username_digest_attempted_at", "username_digest", "attempted_at"),
        Index("ix_sign_in_attempt_attempted_at", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SignInStop(Base):
    """A typed username stopped after repeated failed sign-ins, and until when (TB-1 TB1-204 part a)."""

    __tablename__ = "sign_in_stop"
    __table_args__ = (
        CheckConstraint("username_digest ~ '^[0-9a-f]{64}$'", name="ck_sign_in_stop_username_digest_hex"),
    )

    username_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
