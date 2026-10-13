"""Post-baseline route/permission pins: routes added or tightened after the PF-1A-E1 baseline.

Unlike `pf_1a_e1_baseline_authorization.py`, THIS FILE IS NOT FROZEN EVIDENCE. It is the live,
growing record of every route/permission pairing established after that baseline - mirroring
exactly how `POST_BASELINE_ROLE_PERMISSION_MATRIX` sits alongside the frozen
`ROLE_PERMISSION_COMPATIBILITY_MATRIX` in app.modules.authorization.contract: one side is frozen
historical fact, the other is where a later, reviewed, deliberate change is recorded additively.

Two structures, with deliberately different invariants:

- `POST_BASELINE_TIGHTENED_ROUTES` - a route the baseline recorded as ungated that a later
  package deliberately migrated to `require_permission(...)`. Every entry MUST also appear in
  `BASELINE_UNGATED_ROUTES`: this records a transition FROM ungated.
- `POST_BASELINE_NEW_ROUTES` - a route that did not exist at baseline at all. Every entry must
  be absent from BOTH baseline structures.

Why a tightening cannot simply edit `BASELINE_UNGATED_ROUTES`: that set is independently
re-derived evidence of what was true at the PF-1A-E1 baseline commit, and its own module
docstring says as much - "this file must NOT be silently edited to match" a later change. A
route already in the frozen `BASELINE_ROUTE_PERMISSION_INVENTORY` belongs in neither structure
here; it is already pinned there.

**Why new routes need pinning too** (added by independent review correction pass 1, finding 5):
an earlier version of this file recorded only tightenings, on the reasoning that the route
guard's `unaccounted_for` fallback branch already required a new route to carry some permission.
That branch checks *presence*, not *identity* - so `POST /api/documents/upload` and
`GET /api/documents/{public_id}/content` could have had their permissions swapped with each
other, or replaced with any other registered code, and every check would still have passed.
Naming them explicitly puts them through the same missing/wrong/multiple classification as any
baseline-protected route.

Slice 9C (8 September 2026) is the first entry in both structures: owner decision 5 approved
tightening the four `/api/documents/*` routes the baseline recorded as authenticated-only,
closing a defect where any logged-in user - including MANAGEMENT_READ_ONLY - could enumerate
every document in the system by file name; and the slice adds two genuinely new routes. See
docs/agent/slices/slice-9c-document-storage-foundation.md.
"""

from __future__ import annotations

from tests.fixtures.pf_1a_e1_baseline_authorization import (
    BASELINE_ROUTE_PERMISSION_INVENTORY,
    BASELINE_UNGATED_ROUTES,
)

# ---------------------------------------------------------------------------------------
# Slice 9C - Document Storage Foundation. All four pre-existing /api/documents/* routes that
# BASELINE_UNGATED_ROUTES records as authenticated-only, now migrated to require_permission(...)
# exactly as any baseline-protected route would be. The two brand-new routes this slice adds
# (POST /api/documents/upload, GET /api/documents/{public_id}/content) are NOT listed here -
# they never existed at baseline, so they are not a "tightening". They are pinned separately in
# POST_BASELINE_NEW_ROUTES below, which carries a different invariant.
# ---------------------------------------------------------------------------------------
POST_BASELINE_TIGHTENED_ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/api/documents/types"): "DOCUMENT_READ",
    ("GET", "/api/documents/recent"): "DOCUMENT_READ",
    ("GET", "/api/documents/by-record/{record_type}/{record_public_id}"): "DOCUMENT_READ",
    ("POST", "/api/documents/metadata"): "DOCUMENT_UPLOAD",
}


# ---------------------------------------------------------------------------------------
# Routes that did not exist at baseline at all, each pinned to the EXACT permission it must
# request.
#
# Without this, a genuinely new route only had to carry *some* permission dependency - the
# route-inventory guard's fallback branch checks presence, not identity - so upload and
# content-download could have been swapped with each other, or with any other registered
# permission, and every check would still have passed (independent review, correction pass 1,
# finding 5). Naming them here puts them through the same missing/wrong/multiple classification
# as any baseline-protected route.
#
# Unlike POST_BASELINE_TIGHTENED_ROUTES above, entries here must NOT appear in either baseline
# structure: a route already recorded as ungated is a tightening (list it above), and a route
# already in the frozen permission inventory is baseline-protected (do not list it at all).
# ---------------------------------------------------------------------------------------
POST_BASELINE_NEW_ROUTES: dict[tuple[str, str], str] = {
    # Slice 9C - Document Storage Foundation.
    ("POST", "/api/documents/upload"): "DOCUMENT_UPLOAD",
    ("GET", "/api/documents/{public_id}/content"): "DOCUMENT_CONTENT_READ",
    # Slice 9E - Quotation Generation.
    ("GET", "/api/commercial-offers/{public_id}/quote-documents"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/quote-documents"): "COMMERCIAL_OFFER_QUOTE_GENERATE",
    (
        "POST",
        "/api/commercial-offers/{public_id}/quote-documents/{quote_document_public_id}/approve",
    ): "COMMERCIAL_OFFER_QUOTE_APPROVE",
    # Slice 9F - Commercial Offer versions.
    ("GET", "/api/commercial-offers/{public_id}/versions"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/versions"): "COMMERCIAL_OFFER_UPDATE",
    ("POST", "/api/commercial-offers/{public_id}/abandon-version"): "COMMERCIAL_OFFER_UPDATE",
    # Slice 7C - Work Order Line Operational Detail.
    ("GET", "/api/work-orders/{public_id}/line-details"): "WORK_ORDER_READ",
    ("PUT", "/api/work-orders/{public_id}/lines/{line_public_id}/detail"): "WORK_ORDER_LINE_DETAIL_WRITE",
    # Slice 7D Part 1 - Work Order Line Billing Terms.
    ("GET", "/api/work-orders/{public_id}/billing-terms"): "WORK_ORDER_READ",
    ("POST", "/api/work-orders/{public_id}/lines/{line_public_id}/billing-terms"): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    (
        "PUT",
        "/api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}",
    ): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    (
        "DELETE",
        "/api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}",
    ): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    # Slice 7D Part 3 - the Work Order contract period, its extensions, and copying one line's terms
    # onto other lines. The copy route asks for the billing-terms permission, not one of its own:
    # it writes billing terms.
    ("GET", "/api/work-orders/{public_id}/contract-period"): "WORK_ORDER_READ",
    ("PUT", "/api/work-orders/{public_id}/contract-period"): "WORK_ORDER_CONTRACT_PERIOD_WRITE",
    ("POST", "/api/work-orders/{public_id}/contract-extensions"): "WORK_ORDER_CONTRACT_EXTENSION_WRITE",
    # The owner's screen check of 22 September 2026: the latest extension can be removed.
    (
        "DELETE",
        "/api/work-orders/{public_id}/contract-extensions/{extension_public_id}",
    ): "WORK_ORDER_CONTRACT_EXTENSION_WRITE",
    (
        "POST",
        "/api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/apply-to-lines",
    ): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    # Slice 7D Part 4 - the holidays the Work Order names. Written under the billing-terms permission,
    # not one of its own: which days are holidays decides which days take a line's off-day rate.
    ("GET", "/api/work-orders/{public_id}/holidays"): "WORK_ORDER_READ",
    ("PUT", "/api/work-orders/{public_id}/holidays"): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    # HOL-1 - the holidays that apply: PBL's calendar as the Work Order changes it. A read, as the list's is.
    ("GET", "/api/work-orders/{public_id}/holidays/resulting"): "WORK_ORDER_READ",
    # WRR-001 - the platform's Equipment Reference (read only: version 1 changes only by migration) and
    # Resource Requirements. Reading follows WORK_ORDER_READ's six roles; writing is Operations and Admin.
    ("GET", "/api/equipment-reference/structure"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/resource-requirements"): "RESOURCE_REQUIREMENT_READ",
    ("GET", "/api/resource-requirements/defaults"): "RESOURCE_REQUIREMENT_READ",
    ("GET", "/api/resource-requirements/{public_id}"): "RESOURCE_REQUIREMENT_READ",
    ("POST", "/api/resource-requirements"): "RESOURCE_REQUIREMENT_WRITE",
    ("PUT", "/api/resource-requirements/{public_id}"): "RESOURCE_REQUIREMENT_WRITE",
    ("POST", "/api/resource-requirements/{public_id}/cancel"): "RESOURCE_REQUIREMENT_WRITE",
    # ERT-1 - Plum's machines into the Equipment Reference. Reading machines, models, value rules,
    # corrections and the category rules follows EQUIPMENT_REFERENCE_READ's six roles; every write, and the
    # import screens, need EQUIPMENT_REFERENCE_MANAGE (Admin only, owner's comment 1 of 25 September 2026).
    ("GET", "/api/equipment-reference/category-rules"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/equipment-reference/machines"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/equipment-reference/machines/{public_id}"): "EQUIPMENT_REFERENCE_READ",
    ("PUT", "/api/equipment-reference/machines/{public_id}/details"): "EQUIPMENT_REFERENCE_MANAGE",
    ("PUT", "/api/equipment-reference/machines/{public_id}/capabilities"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/machines/{public_id}/corrections"): "EQUIPMENT_REFERENCE_MANAGE",
    (
        "POST",
        "/api/equipment-reference/machines/{public_id}/corrections/{correction_public_id}/close",
    ): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/machines/{public_id}/fitted-parts"): "EQUIPMENT_REFERENCE_MANAGE",
    (
        "POST",
        "/api/equipment-reference/machines/{public_id}/fitted-parts/{part_public_id}/remove",
    ): "EQUIPMENT_REFERENCE_MANAGE",
    ("GET", "/api/equipment-reference/value-rules"): "EQUIPMENT_REFERENCE_READ",
    ("PUT", "/api/equipment-reference/value-rules"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/value-rules/{public_id}/close"): "EQUIPMENT_REFERENCE_MANAGE",
    ("GET", "/api/equipment-reference/corrections"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/equipment-reference/models"): "EQUIPMENT_REFERENCE_READ",
    ("POST", "/api/equipment-reference/models"): "EQUIPMENT_REFERENCE_MANAGE",
    ("PUT", "/api/equipment-reference/models/{public_id}"): "EQUIPMENT_REFERENCE_MANAGE",
    ("PUT", "/api/equipment-reference/model-mappings"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/imports"): "EQUIPMENT_REFERENCE_MANAGE",
    ("GET", "/api/equipment-reference/imports"): "EQUIPMENT_REFERENCE_MANAGE",
    ("GET", "/api/equipment-reference/imports/{public_id}"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/imports/{public_id}/refresh"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/imports/{public_id}/publish"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/imports/{public_id}/discard"): "EQUIPMENT_REFERENCE_MANAGE",
    # ERT-2 - detachable kit, held for the crane models it fits. Adding and retiring pieces are writes, so
    # EQUIPMENT_REFERENCE_MANAGE (Admin, as for ERT-1); reading kit is reading machines.
    ("POST", "/api/equipment-reference/kit"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/equipment-reference/machines/{public_id}/retire"): "EQUIPMENT_REFERENCE_MANAGE",
    # ELG-1 - machine eligibility. Reading certificates, marks, the check, Certificates due and the rules follows
    # EQUIPMENT_REFERENCE_READ's six roles; recording and withdrawing certificates and "not applicable" marks is
    # EQUIPMENT_REFERENCE_MANAGE (Admin); adding and ending rules is ELIGIBILITY_RULE_MANAGE (Admin, owner Q7).
    ("GET", "/api/eligibility/jurisdictions"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/certificate-kinds"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/assets/{asset_public_id}/certificates"): "EQUIPMENT_REFERENCE_READ",
    ("POST", "/api/eligibility/assets/{asset_public_id}/certificates"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/eligibility/certificates/{certificate_public_id}/withdraw"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/eligibility/assets/{asset_public_id}/not-applicable"): "EQUIPMENT_REFERENCE_MANAGE",
    ("POST", "/api/eligibility/not-applicable/{mark_public_id}/withdraw"): "EQUIPMENT_REFERENCE_MANAGE",
    ("GET", "/api/eligibility/assets/{asset_public_id}/check"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/certificates-due"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/rules"): "EQUIPMENT_REFERENCE_READ",
    ("POST", "/api/eligibility/rules"): "ELIGIBILITY_RULE_MANAGE",
    ("POST", "/api/eligibility/rules/{rule_public_id}/end"): "ELIGIBILITY_RULE_MANAGE",
    # ELG-2 - certificate reminders and escalation. The Alerts that have reached the caller, their count and marking
    # them seen follow EQUIPMENT_REFERENCE_READ - a "seen" mark is the person's own and changes no record; reading the
    # reminder settings does too; saving a new version is ELIGIBILITY_RULE_MANAGE (Admin, owner Q18).
    ("GET", "/api/eligibility/alerts"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/alerts/count"): "EQUIPMENT_REFERENCE_READ",
    ("POST", "/api/eligibility/alerts/seen"): "EQUIPMENT_REFERENCE_READ",
    ("GET", "/api/eligibility/alert-settings"): "EQUIPMENT_REFERENCE_READ",
    ("POST", "/api/eligibility/alert-settings/{reminder_kind_code}"): "ELIGIBILITY_RULE_MANAGE",
    # 8A core - own machines allocated to the resource requirements. Reading follows WORK_ORDER_READ's six roles
    # (RESOURCE_ASSIGNMENT_READ); allocating, replacing, freeing, changing dates, checking again, trips and kit are
    # Operations' and Admin's (RESOURCE_ASSIGNMENT_WRITE); the billing cycle is a billing term, so its route asks for
    # WORK_ORDER_LINE_BILLING_TERMS_WRITE (Slice 7D: who may change a line's rates is one answer).
    ("GET", "/api/resource-assignments"): "RESOURCE_ASSIGNMENT_READ",
    ("GET", "/api/resource-assignments/candidates"): "RESOURCE_ASSIGNMENT_READ",
    ("GET", "/api/resource-assignments/{public_id}"): "RESOURCE_ASSIGNMENT_READ",
    ("POST", "/api/resource-assignments"): "RESOURCE_ASSIGNMENT_WRITE",
    ("POST", "/api/resource-assignments/{public_id}/replace"): "RESOURCE_ASSIGNMENT_WRITE",
    ("POST", "/api/resource-assignments/{public_id}/release"): "RESOURCE_ASSIGNMENT_WRITE",
    ("PUT", "/api/resource-assignments/{public_id}/dates"): "RESOURCE_ASSIGNMENT_WRITE",
    ("POST", "/api/resource-assignments/{public_id}/check"): "RESOURCE_ASSIGNMENT_WRITE",
    ("PUT", "/api/resource-assignments/{public_id}/billing-cycle"): "WORK_ORDER_LINE_BILLING_TERMS_WRITE",
    ("GET", "/api/resource-assignments/{public_id}/kit-options"): "RESOURCE_ASSIGNMENT_READ",
    ("POST", "/api/resource-assignments/{public_id}/trips"): "RESOURCE_ASSIGNMENT_WRITE",
    ("PUT", "/api/resource-assignments/{public_id}/trips/{trip_number}/note"): "RESOURCE_ASSIGNMENT_WRITE",
    ("POST", "/api/resource-assignments/{public_id}/kit"): "RESOURCE_ASSIGNMENT_WRITE",
    ("POST", "/api/resource-assignments/{public_id}/kit/{kit_line_public_id}/remove"): "RESOURCE_ASSIGNMENT_WRITE",
    # HOL-1 - PBL's holiday calendar. Everyone reads it (HOLIDAY_CALENDAR_READ, the six roles); saving a year and
    # marking it complete is Admin's until a position is mapped under ORA-001 (HOLIDAY_CALENDAR_MANAGE).
    ("GET", "/api/holiday-calendar/states"): "HOLIDAY_CALENDAR_READ",
    ("GET", "/api/holiday-calendar/years"): "HOLIDAY_CALENDAR_READ",
    ("GET", "/api/holiday-calendar/years/{calendar_year}"): "HOLIDAY_CALENDAR_READ",
    ("PUT", "/api/holiday-calendar/years/{calendar_year}"): "HOLIDAY_CALENDAR_MANAGE",
}


def assert_tightened_routes_were_baseline_ungated(
    tightened: dict[tuple[str, str], str],
    baseline_ungated: frozenset[tuple[str, str]],
) -> None:
    """A route recorded in POST_BASELINE_TIGHTENED_ROUTES must be one the baseline snapshot
    actually recorded as ungated.

    Guards against two mistakes this structure could otherwise make silently: naming a route
    that was already baseline-protected (which belongs in BASELINE_ROUTE_PERMISSION_INVENTORY, a
    frozen file this module must never touch), and naming a brand-new route that never existed
    at baseline at all (which belongs in POST_BASELINE_NEW_ROUTES, where a different invariant
    applies).

    Exposed as a function, not written inline, so it can be driven with synthetic input by a
    test - a guard never shown to fail is an assertion of intent, not a control.
    """
    not_baseline_ungated = set(tightened) - set(baseline_ungated)
    if not_baseline_ungated:
        raise RuntimeError(
            "POST_BASELINE_TIGHTENED_ROUTES names route(s) the baseline snapshot did not record "
            f"as ungated: {sorted(not_baseline_ungated)}. A route already baseline-protected "
            "belongs in BASELINE_ROUTE_PERMISSION_INVENTORY (frozen; do not edit it here), and a "
            "brand-new route belongs in POST_BASELINE_NEW_ROUTES."
        )


def assert_new_routes_are_genuinely_new(
    new_routes: dict[tuple[str, str], str],
    baseline_ungated: frozenset[tuple[str, str]],
    baseline_inventory: dict[tuple[str, str], str],
) -> None:
    """A route recorded as new must be absent from BOTH baseline structures.

    Guards the two ways this list could be populated wrongly: naming a route the baseline
    recorded as ungated (that is a tightening - it belongs in POST_BASELINE_TIGHTENED_ROUTES,
    where a different invariant applies), and naming a route already in the frozen permission
    inventory (that is baseline-protected and must not be re-pinned here, where an edit would
    escape the frozen fixture's own review requirement).

    Exposed as a function, not written inline, so it can be driven with synthetic input by a
    test - a guard never shown to fail is an assertion of intent, not a control.
    """
    not_new = (set(new_routes) & set(baseline_ungated)) | (set(new_routes) & set(baseline_inventory))
    if not_new:
        raise RuntimeError(
            "POST_BASELINE_NEW_ROUTES names route(s) that are not new - the baseline already "
            f"knows about them: {sorted(not_new)}. A route the baseline recorded as ungated "
            "belongs in POST_BASELINE_TIGHTENED_ROUTES; a route already in the frozen permission "
            "inventory must not be listed here at all."
        )


assert_tightened_routes_were_baseline_ungated(POST_BASELINE_TIGHTENED_ROUTES, BASELINE_UNGATED_ROUTES)
assert_new_routes_are_genuinely_new(
    POST_BASELINE_NEW_ROUTES, BASELINE_UNGATED_ROUTES, BASELINE_ROUTE_PERMISSION_INVENTORY
)

# The two post-baseline structures describe disjoint situations and must never name the same
# route: one records a transition FROM ungated, the other a route that never existed at baseline.
_overlapping = set(POST_BASELINE_TIGHTENED_ROUTES) & set(POST_BASELINE_NEW_ROUTES)
if _overlapping:
    raise RuntimeError(
        f"route(s) recorded as both tightened and new: {sorted(_overlapping)}. A route is one or "
        "the other, never both."
    )
