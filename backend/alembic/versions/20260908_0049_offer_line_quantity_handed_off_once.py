"""An accepted offer line's quantity goes onto Work Orders once, and no Work Order from a Change Quotation (TB-1 CS-04
part 1, HOF-2)

Record: docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md (the owner's decisions of 8 October 2026) and the
dated amendment at the end of docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md.

1. `crm_work_order_line_within_offer_quantity`: the Work Order lines made from one offer line together hold no more
   than that line's quantity. A customer may award one line in parts - quantity 4 as 3 on one Work Order and 1 on
   another - but never more than 4 in all. The handoff checks this under the offer's row lock and names the Work
   Orders that already hold the line; the trigger is what still holds when two requests arrive at once, or when
   anything writes Work Order lines without the handoff: each Work Order line of an offer line first locks that offer
   line, so a second waits for the first and then counts it. A part of zero or less was already refused
   (`ck_crm_work_order_line_quantity`).

2. `crm_commercial_offer_line_keeps_its_work_orders`: an offer line's own quantity cannot go below what its Work Orders
   hold (review round 2), and an offer line a Work Order holds cannot move to another offer (review round 4). The
   application never changes an Accepted offer's lines (#97); this holds for any other writer too. The update holds
   the offer line's row lock while it counts, the lock rules 1 and 3 take on it first, so neither can pass the other.
   Its refusals carry those rules' names: the same rules, seen from the offer line.

3. `crm_work_order_line_from_its_offer`: a Work Order line's offer line belongs to its Work Order's own offer (review
   round 3) - so no rule above can be got round by pointing a line at another offer's line, a Change Quotation's
   included. Checked when a Work Order line is written or moved, by rule 4's trigger when a Work Order is moved to
   another offer, and by rule 2's when an offer line is. The line's check takes a share lock on its Work Order and the
   offer line's row lock, so a move of either waits for it and then sees it.

4. `crm_work_order_not_from_change_quotation`: a Work Order is made from a Base Offer or a Supplementary Offer, never
   from a Change Quotation, which changes work already on a Work Order and is cited on a Work Order amendment. Checked
   when a Work Order is written or moved to another offer, so one made from a Change Quotation before this revision
   stays as it is. `crm_commercial_offer_keeps_its_work_orders_purpose` holds the same rule from the offer's side: an
   offer with a Work Order cannot become a Change Quotation (review round 3). A Work Order's check takes a share lock on
   its offer, which a change of purpose must wait for, and the change counts the offer's Work Orders under its own row
   lock, which a Work Order's check must wait for.

5. `crm_work_order_has_customer_reference` and `ux_crm_work_order_customer_reference`: a Work Order carries the
   customer's Work Order reference - their order number, or the Letter of Intent's - and one offer never has two Work
   Orders with the same reference, compared without case or surrounding whitespace - the whitespace the application
   strips, tabs and line breaks included (review round 5) - (the owner, 8 October 2026, after
   review round 3). One customer order makes one Work Order, so a request repeated - a Create pressed again, a second
   tab, two people at once - is refused, whole line or part; a second order of the same size carries its own number.
   Required when a Work Order is written or its reference changed, so Work Orders made before this revision without
   one stay as they are; the unique index is what holds two at once.

A line already over its quantity, or on a Work Order of another offer, or a reference used twice on one offer, cannot
be put under the rules, so the upgrade first looks for any and, finding one, stops and lists them, changing nothing; what to keep is the business's choice,
made by hand. It locks the Work Order and offer line tables against writes before it looks (review round 2), so nothing
written between the look and the rules escapes them: a writer already under way finishes first and is counted, a later
one waits for the rules. The backend's start runs migrations before it serves anything, so in a deploy nothing waits.

Downgrade drops them all: a line may again be handed off past its quantity or from another offer, a Change Quotation
handed off, and a Work Order made without a reference or with one already used.

Revision ID: 20260908_0049
Revises: 20260908_0048
Create Date: 2026-10-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0049"
down_revision: Union[str, None] = "20260908_0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

QUANTITY_RULE = "crm_work_order_line_within_offer_quantity"
SHRINK_RULE = "crm_commercial_offer_line_keeps_its_work_orders"
LINE_OFFER_RULE = "crm_work_order_line_from_its_offer"
PURPOSE_RULE = "crm_work_order_not_from_change_quotation"
OFFER_PURPOSE_RULE = "crm_commercial_offer_keeps_its_work_orders_purpose"
REFERENCE_RULE = "crm_work_order_has_customer_reference"
REFERENCE_INDEX = "ux_crm_work_order_customer_reference"
# The whitespace the application strips from a reference (every character Python's str.isspace() accepts, which is
# what the handoff's strip() removes), as a PostgreSQL regular-expression class (review round 5: btrim() removes
# spaces only). `work_orders/contract.py` holds the same class for the handoff's lookup; a test checks they agree.
REFERENCE_SPACE = r"\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
REFERENCE_BLANK = f"^[{REFERENCE_SPACE}]*$"
# How two references are compared: without case, and without that whitespace around them.
REFERENCE_KEY = f"lower(regexp_replace(customer_wo_reference, '^[{REFERENCE_SPACE}]+|[{REFERENCE_SPACE}]+$', '', 'g'))"
# A reference that counts: present and not whitespace alone.
REFERENCE_GIVEN = f"COALESCE(customer_wo_reference, '') !~ '{REFERENCE_BLANK}'"

WORK_ORDER_CODE = "COALESCE(wo.work_order_code, CAST(wo.work_order_public_id AS VARCHAR))"

LINES_OVER_THEIR_QUANTITY = f"""
    SELECT co.offer_code, col.line_number, col.quantity,
           string_agg({WORK_ORDER_CODE} || ' (' || wol.quantity || ')', ', ' ORDER BY wo.id) AS work_orders
    FROM crm_work_order_line wol
    INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
    INNER JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
    INNER JOIN crm_commercial_offer co ON co.id = col.commercial_offer_id
    GROUP BY co.offer_code, col.line_number, col.quantity, wol.commercial_offer_line_id
    HAVING SUM(wol.quantity) > col.quantity
    ORDER BY co.offer_code, col.line_number
"""

LINES_FROM_ANOTHER_OFFER = f"""
    SELECT {WORK_ORDER_CODE} AS work_order, wol.line_number, co.offer_code AS line_offer
    FROM crm_work_order_line wol
    INNER JOIN crm_work_order wo ON wo.id = wol.work_order_id
    INNER JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
    INNER JOIN crm_commercial_offer co ON co.id = col.commercial_offer_id
    WHERE col.commercial_offer_id <> wo.commercial_offer_id
    ORDER BY wo.id, wol.line_number
"""

REFERENCES_USED_TWICE = f"""
    SELECT co.offer_code, MIN(wo.customer_wo_reference) AS reference,
           string_agg({WORK_ORDER_CODE}, ', ' ORDER BY wo.id) AS work_orders
    FROM crm_work_order wo
    INNER JOIN crm_commercial_offer co ON co.id = wo.commercial_offer_id
    WHERE {REFERENCE_GIVEN.replace('customer_wo_reference', 'wo.customer_wo_reference')}
    GROUP BY co.offer_code, wo.commercial_offer_id, {REFERENCE_KEY.replace('customer_wo_reference', 'wo.customer_wo_reference')}
    HAVING COUNT(*) > 1
    ORDER BY co.offer_code
"""


def _refuse_lines_the_rules_cannot_hold() -> None:
    bind = op.get_bind()
    found = [
        f"offer {row.offer_code} line {row.line_number} (quantity {row.quantity}) is on {row.work_orders}"
        for row in bind.execute(sa.text(LINES_OVER_THEIR_QUANTITY)).fetchall()
    ] + [
        f"{row.work_order} line {row.line_number} is a line of another offer, {row.line_offer}"
        for row in bind.execute(sa.text(LINES_FROM_ANOTHER_OFFER)).fetchall()
    ] + [
        f"offer {row.offer_code} has customer reference {row.reference} on {row.work_orders}"
        for row in bind.execute(sa.text(REFERENCES_USED_TWICE)).fetchall()
    ]
    if found:
        raise RuntimeError(
            "20260908_0049 stopped, changing nothing: these Work Orders break the rules it adds - an offer line on "
            "Work Orders for more than its quantity, a Work Order line from another offer, or one customer reference on "
            "two Work Orders of one offer. Decide what to keep, "
            "correct the rest by hand, then upgrade again. " + "; ".join(found)
        )


def _rule(function: str, body: str, trigger: str) -> None:
    op.execute(f"CREATE FUNCTION {function}() RETURNS trigger LANGUAGE plpgsql AS $body$ {body} $body$")
    op.execute(f"CREATE TRIGGER {function} {trigger} FOR EACH ROW EXECUTE FUNCTION {function}()")


def upgrade() -> None:
    # Held to the end of the migration's transaction: nothing the rules govern is written between the look and them.
    op.execute("LOCK TABLE crm_work_order, crm_work_order_line, crm_commercial_offer_line IN SHARE ROW EXCLUSIVE MODE")
    _refuse_lines_the_rules_cannot_hold()
    _rule(
        QUANTITY_RULE,
        f"""
        DECLARE
            offered numeric(18, 2);
            taken numeric(18, 2);
        BEGIN
            IF NEW.commercial_offer_line_id IS NULL THEN
                RETURN NEW;
            END IF;
            -- Every Work Order line of one offer line queues on that offer line, so two at once cannot both count the same room.
            SELECT quantity INTO offered FROM crm_commercial_offer_line
            WHERE id = NEW.commercial_offer_line_id FOR NO KEY UPDATE;
            SELECT COALESCE(SUM(quantity), 0) INTO taken FROM crm_work_order_line
            WHERE commercial_offer_line_id = NEW.commercial_offer_line_id AND id IS DISTINCT FROM NEW.id;
            IF taken + NEW.quantity > offered THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{QUANTITY_RULE}',
                    MESSAGE = 'An offer line''s Work Orders hold at most its quantity, ' || offered || '; '
                        || taken || ' is already on a Work Order.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE INSERT OR UPDATE OF commercial_offer_line_id, quantity ON crm_work_order_line",
    )
    _rule(
        SHRINK_RULE,
        f"""
        DECLARE
            taken numeric(18, 2);
        BEGIN
            -- The update already holds this offer line's row lock, which every Work Order line of it takes first.
            IF NEW.commercial_offer_id IS DISTINCT FROM OLD.commercial_offer_id
                AND EXISTS (SELECT 1 FROM crm_work_order_line WHERE commercial_offer_line_id = NEW.id) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{LINE_OFFER_RULE}',
                    MESSAGE = 'An offer line on a Work Order cannot move to another offer.';
            END IF;
            SELECT COALESCE(SUM(quantity), 0) INTO taken FROM crm_work_order_line WHERE commercial_offer_line_id = NEW.id;
            IF taken > NEW.quantity THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{QUANTITY_RULE}',
                    MESSAGE = 'An offer line''s quantity cannot go below what its Work Orders hold, ' || taken || '.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE UPDATE OF quantity, commercial_offer_id ON crm_commercial_offer_line",
    )
    _rule(
        LINE_OFFER_RULE,
        f"""
        DECLARE
            work_order_offer integer;
            line_offer integer;
        BEGIN
            IF NEW.commercial_offer_line_id IS NULL THEN
                RETURN NEW;
            END IF;
            -- A share lock on the Work Order: moving it to another offer waits for this line, then sees it.
            SELECT commercial_offer_id INTO work_order_offer FROM crm_work_order WHERE id = NEW.work_order_id FOR SHARE;
            -- And the offer line's row lock, the one rule 1 takes: moving the offer line waits for this line, then sees it.
            SELECT commercial_offer_id INTO line_offer FROM crm_commercial_offer_line
            WHERE id = NEW.commercial_offer_line_id FOR NO KEY UPDATE;
            IF line_offer IS DISTINCT FROM work_order_offer THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{LINE_OFFER_RULE}',
                    MESSAGE = 'A Work Order line comes from a line of its own Work Order''s offer.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE INSERT OR UPDATE OF work_order_id, commercial_offer_line_id ON crm_work_order_line",
    )
    _rule(
        PURPOSE_RULE,
        f"""
        DECLARE
            purpose varchar(50);
        BEGIN
            -- A Work Order left on its offer keeps it, even one made from a Change Quotation before this revision.
            IF TG_OP = 'UPDATE' AND NEW.commercial_offer_id IS NOT DISTINCT FROM OLD.commercial_offer_id THEN
                RETURN NEW;
            END IF;
            -- A share lock on the offer: changing its purpose waits for this Work Order, then sees it.
            SELECT offer_purpose INTO purpose FROM crm_commercial_offer WHERE id = NEW.commercial_offer_id FOR SHARE;
            IF purpose IS DISTINCT FROM 'BASE' AND purpose IS DISTINCT FROM 'SUPPLEMENTARY' THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{PURPOSE_RULE}',
                    MESSAGE = 'A Work Order is made from a Base Offer or a Supplementary Offer, not from a '
                        || COALESCE(purpose, 'missing') || ' offer.';
            END IF;
            IF TG_OP = 'UPDATE' AND EXISTS (
                SELECT 1 FROM crm_work_order_line wol
                INNER JOIN crm_commercial_offer_line col ON col.id = wol.commercial_offer_line_id
                WHERE wol.work_order_id = NEW.id AND col.commercial_offer_id <> NEW.commercial_offer_id
            ) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{LINE_OFFER_RULE}',
                    MESSAGE = 'A Work Order cannot move to another offer while its lines come from its own.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE INSERT OR UPDATE OF commercial_offer_id ON crm_work_order",
    )
    _rule(
        OFFER_PURPOSE_RULE,
        f"""
        BEGIN
            -- The update holds the offer's row lock, which a Work Order's check takes in share first.
            IF NEW.offer_purpose IS DISTINCT FROM OLD.offer_purpose
                AND NEW.offer_purpose IS DISTINCT FROM 'BASE' AND NEW.offer_purpose IS DISTINCT FROM 'SUPPLEMENTARY'
                AND EXISTS (SELECT 1 FROM crm_work_order WHERE commercial_offer_id = NEW.id) THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{PURPOSE_RULE}',
                    MESSAGE = 'An offer with a Work Order cannot become a Change Quotation.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE UPDATE OF offer_purpose ON crm_commercial_offer",
    )

    _rule(
        REFERENCE_RULE,
        f"""
        BEGIN
            -- A Work Order made before this revision without a reference keeps it until its reference is changed.
            IF TG_OP = 'UPDATE' AND NEW.customer_wo_reference IS NOT DISTINCT FROM OLD.customer_wo_reference THEN
                RETURN NEW;
            END IF;
            IF COALESCE(NEW.customer_wo_reference, '') ~ '{REFERENCE_BLANK}' THEN
                RAISE EXCEPTION USING
                    ERRCODE = 'check_violation',
                    CONSTRAINT = 'ck_{REFERENCE_RULE}',
                    MESSAGE = 'A Work Order carries the customer''s Work Order or Letter of Intent reference.';
            END IF;
            RETURN NEW;
        END
        """,
        "BEFORE INSERT OR UPDATE OF customer_wo_reference ON crm_work_order",
    )
    op.execute(
        f"CREATE UNIQUE INDEX {REFERENCE_INDEX} ON crm_work_order (commercial_offer_id, {REFERENCE_KEY}) "
        f"WHERE {REFERENCE_GIVEN}"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX {REFERENCE_INDEX}")
    for function, table in (
        (REFERENCE_RULE, "crm_work_order"),
        (OFFER_PURPOSE_RULE, "crm_commercial_offer"),
        (PURPOSE_RULE, "crm_work_order"),
        (LINE_OFFER_RULE, "crm_work_order_line"),
        (SHRINK_RULE, "crm_commercial_offer_line"),
        (QUANTITY_RULE, "crm_work_order_line"),
    ):
        op.execute(f"DROP TRIGGER {function} ON {table}")
        op.execute(f"DROP FUNCTION {function}()")
