from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from tooling.user_admin import service as user_admin

# sales1 is one of the six demo users, with the SALES_USER role, the same role most Commercial
# Offer creation/lifecycle actions use in the documented manual UAT flow (see docs/agent/acceptance
# files). Using a real user id keeps created_by/business_event actor fields realistic.
DEFAULT_ACTOR_USERNAME = "sales1"


def resolve_actor(db: Session, username: str = DEFAULT_ACTOR_USERNAME) -> dict[str, str]:
    """The user seeded records are written as.

    Development and CI databases get the demo users, able to sign in, when the backend starts
    (`python -m tooling.user_admin seed-demo-users`). Since TB-1 TB1-203 (7 October 2026) no other
    database does, but the hosted sites' practice data is still written as them; so a demo user
    missing here is created switched off, with no password - an author that cannot sign in - and
    committed at once. Any other missing name is refused.
    """
    row = db.execute(
        # Matched case-insensitively, consistent with login and the
        # ux_app_user_username_lower unique index.
        text(
            "SELECT public_id, username FROM app_user "
            "WHERE lower(username) = lower(CAST(:username AS VARCHAR))"
        ),
        {"username": username},
    ).first()
    if row is not None:
        return {"public_id": str(row.public_id), "username": row.username}
    if username.strip().lower() not in {demo.username for demo in user_admin.DEMO_USERS}:
        raise RuntimeError(f"Seed user {username!r} was not found in app_user.")
    author = user_admin.add_demo_author(db, username)
    db.commit()
    return {"public_id": author.public_id, "username": author.username}
