"""document metadata api foundation

Revision ID: 20260629_0005
Revises: 20260629_0003
Create Date: 2026-06-29

"""

from typing import Sequence, Union


revision: str = "20260629_0005"
down_revision: Union[str, None] = "20260629_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Document metadata table already exists from the platform foundation.
    # Slice 0F adds API/UI behavior only.
    pass


def downgrade() -> None:
    pass