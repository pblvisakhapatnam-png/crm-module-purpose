"""TE-6: the Work Orders service module keeps every public name it had before it was split.

`app.modules.work_orders.service` became a re-export of the `services` package in TE-6. Code written
against the original module - an import from it, or an attribute read on it - must keep working, so
it re-exports every public name the original defined, whether or not anything in the repository imports
that name today (independent review round 1, finding F-01).

Names a concern adds after the split are re-exported too, and pinned in a set of their own, so the set
measured at 944af54 is never edited to fit a later package.
"""

from __future__ import annotations

from app.modules.work_orders import service
from app.modules.work_orders.services import (
    amendments,
    billing_terms,
    common,
    contract_period,
    handoff,
    holidays,
    line_detail,
    resulting_holidays,
)

CONCERN_MODULES = {
    module.__name__: module
    for module in (common, handoff, amendments, line_detail, billing_terms, contract_period, holidays, resulting_holidays)
}

# Every public top-level name defined in backend/app/modules/work_orders/service.py at 944af54, the
# last commit before the split: its functions, its exception classes and its one public constant.
PUBLIC_NAMES_BEFORE_THE_SPLIT = frozenset(
    {
        "INDIA_TIME_ZONE",
        "WorkOrderAmendmentLineNotFoundError",
        "WorkOrderAmendmentNotFoundError",
        "WorkOrderCommercialOfferNotFoundError",
        "WorkOrderContractExtensionNotFoundError",
        "WorkOrderContractPeriodConflictError",
        "WorkOrderLineBillingTermNotFoundError",
        "WorkOrderLineBillingTermsConflictError",
        "WorkOrderLineDetailConflictError",
        "WorkOrderLineNotFoundError",
        "WorkOrderNotFoundError",
        "WorkOrderValidationError",
        "add_work_order_line_billing_terms_period",
        "contract_bounds_for_work_order",
        "contract_gaps_for_work_order",
        "copy_work_order_line_billing_terms",
        "create_work_order_amendment",
        "create_work_order_amendment_line",
        "create_work_order_contract_extension",
        "create_work_order_from_commercial_offer",
        "decide_work_order_amendment",
        "delete_work_order_amendment_line",
        "get_work_order",
        "get_work_order_amendment",
        "get_work_order_amendment_readiness",
        "get_work_order_contract_period",
        "list_work_order_amendment_lines",
        "list_work_order_amendments",
        "list_work_order_billing_terms",
        "list_work_order_line_details",
        "list_work_order_lines",
        "list_work_order_related_offers",
        "list_work_orders",
        "remove_work_order_contract_extension",
        "remove_work_order_line_billing_terms_period",
        "save_work_order_contract_period",
        "save_work_order_line_detail",
        "update_work_order_amendment",
        "update_work_order_amendment_line",
        "update_work_order_line_billing_terms_period",
    }
)


# Every public name a concern module has added to the service since the split, pinned apart so the set
# measured at 944af54 stays exactly what was measured. A later package adds its names here.
NAMES_ADDED_AFTER_THE_SPLIT = frozenset(
    {
        # Slice 7D Part 4 - the holidays a Work Order names (services/holidays.py), and its conflict error.
        "WorkOrderHolidayListConflictError",
        "get_work_order_holidays",
        "save_work_order_holidays",
        # WRR-001 - how a Resource Requirement finds the Work Order its line belongs to (services/handoff.py).
        "get_work_order_line_reference",
        # 8A core - how Resource Requirements hears that a Work Order's end dates moved, and how Resource
        # Assignments holds a Work Order open while it writes (services/common.py).
        "register_end_dates_listener",
        "hold_work_order_status",
        # HOL-1 - the holidays that apply: PBL's calendar as the Work Order changes it (services/resulting_holidays.py).
        "get_work_order_resulting_holidays",
        # CS-04 part 1 - the handoff's refusal when an offer line's quantity is already on Work Orders
        # (services/common.py).
        "WorkOrderHandoffConflictError",
    }
)


def test_the_pinned_list_is_the_one_measured() -> None:
    assert len(PUBLIC_NAMES_BEFORE_THE_SPLIT) == 40


def test_the_names_added_since_are_new_names() -> None:
    """A name added after the split is genuinely new - not one the original module already had."""
    assert not (NAMES_ADDED_AFTER_THE_SPLIT & PUBLIC_NAMES_BEFORE_THE_SPLIT)


def test_every_public_name_of_the_original_module_is_still_on_it() -> None:
    missing = sorted(name for name in PUBLIC_NAMES_BEFORE_THE_SPLIT if not hasattr(service, name))
    assert missing == [], f"no longer available from the Work Orders service module: {missing}"


def test_every_name_added_since_is_on_it() -> None:
    missing = sorted(name for name in NAMES_ADDED_AFTER_THE_SPLIT if not hasattr(service, name))
    assert missing == [], f"not available from the Work Orders service module: {missing}"


def test_all_lists_exactly_those_names() -> None:
    assert len(service.__all__) == len(set(service.__all__)), "a name is listed twice in __all__"
    assert set(service.__all__) == PUBLIC_NAMES_BEFORE_THE_SPLIT | NAMES_ADDED_AFTER_THE_SPLIT


def test_each_name_is_the_object_its_concern_module_defines() -> None:
    """A re-export hands out the definition itself - never a copy, wrapper or second class - so an
    `except WorkOrderValidationError` in a caller still catches what the service raises."""
    for name in sorted(PUBLIC_NAMES_BEFORE_THE_SPLIT | NAMES_ADDED_AFTER_THE_SPLIT):
        obj = getattr(service, name)
        if callable(obj):
            assert obj.__module__ in CONCERN_MODULES, (name, obj.__module__)
            home = CONCERN_MODULES[obj.__module__]
        else:
            home = common  # INDIA_TIME_ZONE, the one public constant
        assert getattr(home, name) is obj, name
