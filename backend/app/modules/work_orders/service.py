"""The Work Orders service.

The code lives in services/, one module per concern: handoff, amendments, line_detail,
billing_terms, contract_period, holidays and resulting_holidays, with what several of them share in common. This module
re-exports every public name it defined before it was split (TE-6), so code written against it
keeps working - including the few names nothing in the repository imports today - and every public
name a concern has added since (Slice 7D Part 4's holiday list, and WRR-001's line lookup). Import from here, not from
services/.

A test that monkeypatches a name a service function looks up must patch it on the module that
function is defined in; patching it here would change nothing the function sees.
"""

from __future__ import annotations

from app.modules.work_orders.services.common import (
    INDIA_TIME_ZONE,
    WorkOrderAmendmentLineNotFoundError,
    WorkOrderAmendmentNotFoundError,
    WorkOrderCommercialOfferNotFoundError,
    WorkOrderContractExtensionNotFoundError,
    WorkOrderContractPeriodConflictError,
    WorkOrderHandoffConflictError,
    WorkOrderHolidayListConflictError,
    WorkOrderLineBillingTermNotFoundError,
    WorkOrderLineBillingTermsConflictError,
    WorkOrderLineDetailConflictError,
    WorkOrderLineNotFoundError,
    WorkOrderNotFoundError,
    WorkOrderValidationError,
    contract_bounds_for_work_order,
    contract_gaps_for_work_order,
    get_work_order,
    hold_work_order_status,
    register_end_dates_listener,
)
from app.modules.work_orders.services.handoff import (
    create_work_order_from_commercial_offer,
    get_work_order_line_reference,
    list_work_order_lines,
    list_work_order_related_offers,
    list_work_orders,
)
from app.modules.work_orders.services.amendments import (
    create_work_order_amendment,
    create_work_order_amendment_line,
    decide_work_order_amendment,
    delete_work_order_amendment_line,
    get_work_order_amendment,
    get_work_order_amendment_readiness,
    list_work_order_amendment_lines,
    list_work_order_amendments,
    update_work_order_amendment,
    update_work_order_amendment_line,
)
from app.modules.work_orders.services.line_detail import (
    list_work_order_line_details,
    save_work_order_line_detail,
)
from app.modules.work_orders.services.billing_terms import (
    add_work_order_line_billing_terms_period,
    copy_work_order_line_billing_terms,
    list_work_order_billing_terms,
    remove_work_order_line_billing_terms_period,
    update_work_order_line_billing_terms_period,
)
from app.modules.work_orders.services.contract_period import (
    create_work_order_contract_extension,
    get_work_order_contract_period,
    remove_work_order_contract_extension,
    save_work_order_contract_period,
)
from app.modules.work_orders.services.holidays import (
    get_work_order_holidays,
    save_work_order_holidays,
)
from app.modules.work_orders.services.resulting_holidays import get_work_order_resulting_holidays

__all__ = [
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
    # Added after the split (Slice 7D Part 4). The TE-6 surface test pins these in a set of their own.
    "WorkOrderHolidayListConflictError",
    "get_work_order_holidays",
    "save_work_order_holidays",
    # Added by WRR-001: how a Resource Requirement finds the Work Order its line belongs to.
    "get_work_order_line_reference",
    # Added by 8A core: how Resource Requirements hears that a Work Order's end dates moved, and how Resource
    # Assignments holds a Work Order open while it writes.
    "register_end_dates_listener",
    "hold_work_order_status",
    # Added by HOL-1: the holidays that apply - PBL's calendar as the Work Order changes it.
    "get_work_order_resulting_holidays",
    # Added by CS-04 part 1: the handoff's refusal of what is already on a Work Order - more of an offer line than it
    # has left (a line may be split across Work Orders up to its quantity), or a customer reference already used.
    "WorkOrderHandoffConflictError",
]
