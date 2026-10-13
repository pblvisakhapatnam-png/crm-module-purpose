"""One active Base Offer per Opportunity, held by the database (TB-1 CS-05c; the deferred "Database-level uniqueness
for the one-active-Base-Offer rule")

Record: docs/continuity/CS_05C_SUBMITTED_OFFER_LOCK.md (the owner's decision of 9 October 2026: the database enforces
the rule, "for consistency").

`ux_crm_commercial_offer_one_active_base_per_opportunity`: a partial unique index over `crm_commercial_offer
(opportunity_id)` for Base Offers whose status is not Withdrawn, Rejected or Closed - exactly the rule Commercial Offer
creation checks under the Opportunity's row lock (Slice 6B.1, scoped to Base Offers by Slice 6O.1;
`COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` in `commercial_offers/contract.py`, which a test holds equal to
`INACTIVE_STATUSES` below). Draft, Ready for Review, Submitted, Revised and Accepted all count as active, and any other
status would too; Supplementary Offers and Change Quotations never count. Both columns are NOT NULL, so the index and
the check see the same rows. Creation answers the index with the check's own refusal, naming the active offer.

An Opportunity that already has two active Base Offers cannot be put under the rule - before Slice 9B a late award could
bring a rejected offer back after a replacement was made - so the upgrade first looks for any and, finding one, stops
and lists them, changing nothing. Which offer stays active is the business's choice, made by hand (withdraw or close the
other), then the upgrade is run again. It locks the offer table against writes before it looks, so nothing written
between the look and the index escapes it; the backend's start runs migrations before it serves anything, so in a
deploy nothing waits.

Downgrade drops the index: the rule is then held by the application's check alone, as before.

Revision ID: 20260908_0053
Revises: 20260908_0052
Create Date: 2026-10-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0053"
down_revision: Union[str, None] = "20260908_0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX = "ux_crm_commercial_offer_one_active_base_per_opportunity"
INACTIVE_STATUSES = ("WITHDRAWN", "REJECTED", "CLOSED")
ACTIVE_BASE_OFFER = (
    "offer_purpose = 'BASE' AND offer_status_code NOT IN ("
    + ", ".join(f"'{status}'" for status in INACTIVE_STATUSES)
    + ")"
)

OPPORTUNITIES_WITH_TWO_ACTIVE_BASE_OFFERS = f"""
    SELECT o.opportunity_name, o.opportunity_public_id,
           string_agg(COALESCE(co.offer_code, co.offer_public_id) || ' (' || co.offer_status_code || ')', ', '
                      ORDER BY co.id) AS offers
    FROM crm_commercial_offer co
    INNER JOIN crm_opportunity o ON o.id = co.opportunity_id
    WHERE {ACTIVE_BASE_OFFER.replace('offer_', 'co.offer_')}
    GROUP BY o.id, o.opportunity_name, o.opportunity_public_id
    HAVING COUNT(*) > 1
    ORDER BY o.id
"""


def refusal(bind: sa.engine.Connection) -> str | None:
    """What the upgrade stops with, naming each Opportunity with more than one active Base Offer; None if none has."""
    found = [
        f"Opportunity {row.opportunity_name} ({row.opportunity_public_id}) has {row.offers}"
        for row in bind.execute(sa.text(OPPORTUNITIES_WITH_TWO_ACTIVE_BASE_OFFERS)).fetchall()
    ]
    if not found:
        return None
    return (
        "20260908_0053 stopped, changing nothing: these Opportunities have more than one active Base Offer, which the "
        "rule it adds forbids. Decide which offer stays active, withdraw or close the others, then upgrade again. "
        + "; ".join(found)
    )


def upgrade() -> None:
    # Held to the end of the migration's transaction: no offer is written between the look and the index.
    op.execute("LOCK TABLE crm_commercial_offer IN SHARE ROW EXCLUSIVE MODE")
    stopped = refusal(op.get_bind())
    if stopped is not None:
        raise RuntimeError(stopped)
    op.create_index(
        INDEX,
        "crm_commercial_offer",
        ["opportunity_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_BASE_OFFER),
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name="crm_commercial_offer")
