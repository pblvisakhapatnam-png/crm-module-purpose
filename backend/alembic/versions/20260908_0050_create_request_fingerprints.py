"""A create's request key replays only the very same request (TB-1 finding TB1-102 part b, CS-06's early step)

Record: docs/continuity/TB1_102B_REPLAY_RULE.md.

Equipment models, kit lots and resource requirements are each made once per request key, and until now a second
request with a used key was answered with the first record whatever it asked for (a requirement's key only on the
same line, a kit lot's only for the same kit model). They now follow the rule Resource Assignments built (8A core,
`resource_assignment_request.request_fingerprint`): the record keeps the SHA-256 of the request that made it
(`app/shared/request_keys.py`), the same request again is answered with that record, and any other request is
refused.

1. `create_request_fingerprint` on `equipment_model`, `equipment_asset` (every record of a kit lot carries its
   request's) and `resource_requirement`: 64 hexadecimal digits, and only on a record a request key made. A record
   made before this revision has none, and is not given one - the request that made it cannot be known now - so a
   later use of its key is refused, never replayed.

2. The request that made a record never changes: its key and its fingerprint (`create_request_kept`), as ERT-2
   already held for kit's key, place in the lot and model asked for.

Downgrade drops the trigger, its function, the checks and the columns: the three creates' code from before this
revision reads none of them.

Revision ID: 20260908_0050
Revises: 20260908_0049
Create Date: 2026-10-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0050"
down_revision: Union[str, None] = "20260908_0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("equipment_model", "equipment_asset", "resource_requirement")
COLUMN = "create_request_fingerprint"


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column(COLUMN, sa.String(length=64), nullable=True))
        op.create_check_constraint(
            f"ck_{table}_{COLUMN}",
            table,
            f"{COLUMN} IS NULL OR (create_request_key IS NOT NULL AND {COLUMN} ~ '^[0-9a-f]{{64}}$')",
        )
    op.execute(
        """
        CREATE FUNCTION create_request_kept() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            -- A repeated request is judged by the request that made the record: its key and its fingerprint.
            IF NEW.create_request_key IS DISTINCT FROM OLD.create_request_key
                OR NEW.create_request_fingerprint IS DISTINCT FROM OLD.create_request_fingerprint THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_' || TG_TABLE_NAME || '_create_request_kept',
                    MESSAGE = 'The request that made a record never changes.';
            END IF;
            RETURN NEW;
        END
        $body$
        """
    )
    for table in TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_create_request_kept
            BEFORE UPDATE OF create_request_key, {COLUMN} ON {table}
            FOR EACH ROW EXECUTE FUNCTION create_request_kept()
            """
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_create_request_kept ON {table}")
    op.execute("DROP FUNCTION IF EXISTS create_request_kept()")
    for table in TABLES:
        op.drop_constraint(f"ck_{table}_{COLUMN}", table, type_="check")
        op.drop_column(table, COLUMN)
