"""Sign-in hardening: ending earlier sign-ins, and stopping repeated wrong passwords (TB-1 TB1-204 part a)

Record: docs/continuity/TB1_204A_SIGN_IN_HARDENING.md (the owner's decisions of 7 October 2026).

1. `app_user.token_version`: a number every sign-in token carries. A password reset, disabling or retiring an
   account, and the account tool's `end-sign-ins` raise it, and a token carrying an older number is refused on its
   next request. A token issued before this revision carries no number, which is read as 0. Active accounts start at
   0, so deploying this ends no active account's sign-in; accounts already disabled or retired start at 1, so enabling one later
   does not bring back a sign-in made before it was disabled (`INACTIVE_ACCOUNTS_START_ENDED`).

2. `sign_in_attempt` and `sign_in_stop`: one row per recent sign-in attempt, numbered by its sequence (never
   reused), and one per stopped username - whether or not an account has that name, so being stopped never shows
   which usernames exist. The username is held only as the SHA-256 of its lower-cased form (the same `lower()` the
   sign-in lookup uses), never as text: what someone typed in the username box is sometimes their password. The
   attempts in the last window are the count, so the window rolls. A successful sign-in removes its own attempt and
   those numbered before it; the account tool's `unlock` removes a stop in force and its attempts; rows long past are
   pruned by later sign-ins (`app.modules.identity.throttle`).

Downgrade drops all three: every account's earlier sign-ins become valid again until they expire, and every stop is
lifted.

Revision ID: 20260908_0048
Revises: 20260908_0047
Create Date: 2026-10-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0048"
down_revision: Union[str, None] = "20260908_0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# A token issued before this revision counts as 0; an account already disabled or retired must not match it again.
INACTIVE_ACCOUNTS_START_ENDED = "UPDATE app_user SET token_version = 1 WHERE is_active IS FALSE"


def upgrade() -> None:
    op.add_column(
        "app_user",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.create_check_constraint("ck_app_user_token_version_not_negative", "app_user", "token_version >= 0")
    op.execute(INACTIVE_ACCOUNTS_START_ENDED)

    op.create_table(
        "sign_in_attempt",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username_digest", sa.String(64), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("username_digest ~ '^[0-9a-f]{64}$'", name="ck_sign_in_attempt_username_digest_hex"),
    )
    op.create_index(
        "ix_sign_in_attempt_username_digest_attempted_at", "sign_in_attempt", ["username_digest", "attempted_at"]
    )
    op.create_index("ix_sign_in_attempt_attempted_at", "sign_in_attempt", ["attempted_at"])
    op.create_table(
        "sign_in_stop",
        sa.Column("username_digest", sa.String(64), primary_key=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("username_digest ~ '^[0-9a-f]{64}$'", name="ck_sign_in_stop_username_digest_hex"),
    )


def downgrade() -> None:
    op.drop_table("sign_in_stop")
    op.drop_index("ix_sign_in_attempt_attempted_at", table_name="sign_in_attempt")
    op.drop_index("ix_sign_in_attempt_username_digest_attempted_at", table_name="sign_in_attempt")
    op.drop_table("sign_in_attempt")
    op.drop_constraint("ck_app_user_token_version_not_negative", "app_user", type_="check")
    op.drop_column("app_user", "token_version")
