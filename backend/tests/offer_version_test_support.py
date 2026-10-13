"""Test support for CS-05a (TB-1 TB1-303): an edit of a Commercial Offer or one of its lines sends the `row_version` the
screen loaded. A test that edits stands for a screen opened just before the save, so it sends the version as it is now;
the CS-05a tests send an older one on purpose."""

from __future__ import annotations

from sqlalchemy import text

from app.core.database import SessionLocal


def offer_row_version(offer_public_id: object) -> int:
    """The offer's version as a screen loading it now would see it."""
    with SessionLocal() as db:
        return int(
            db.execute(
                text("SELECT row_version FROM crm_commercial_offer WHERE offer_public_id = :public_id"),
                {"public_id": str(offer_public_id)},
            ).scalar_one()
        )


def line_row_version(line_public_id: object) -> int:
    """The offer line's version as a screen loading it now would see it. A line that does not exist reads as 1, so a
    test of an unknown line still reaches the route's own 404."""
    with SessionLocal() as db:
        version = db.execute(
            text("SELECT row_version FROM crm_commercial_offer_line WHERE line_public_id = :public_id"),
            {"public_id": str(line_public_id)},
        ).scalar_one_or_none()
    return int(version) if version is not None else 1
