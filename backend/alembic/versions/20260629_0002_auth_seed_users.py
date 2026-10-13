"""seed authentication users - now creates none

Revision ID: 20260629_0002
Revises: 20260629_0001
Create Date: 2026-06-29

Until 7 October 2026 this revision created six demo users - admin1, sales1, manager1, finance1, ops1
and readonly1, all active, all with the password "password" - in every database, production included
(TB-1 TB1-203). They have left the migration chain (owner's decision, 7 October 2026, option a):

- development and CI get them from `python -m tooling.user_admin seed-demo-users`, which the backend
  runs when it starts with a development APP_ENV (`app/startup.py`) and which refuses anywhere else;
- the practice-data harness creates any of the six it needs as an author switched off, with no
  password (`tooling/smoke_data/actors.py`);
- a database that already has them keeps them (owner, 7 October 2026): the hosted pilots retired
  theirs with `tooling.user_admin retire-demo-users`, and `check-default-passwords` stays the
  deployment gate.

The revision stays, empty, so the chain and every database's recorded revision are unchanged.
"""

from __future__ import annotations

revision = "20260629_0002"
down_revision = "20260629_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates no user. See the module docstring."""


def downgrade() -> None:
    """Removes nothing: users this revision once created are left as they are, and the previous
    revision's downgrade drops the user tables in any case."""
