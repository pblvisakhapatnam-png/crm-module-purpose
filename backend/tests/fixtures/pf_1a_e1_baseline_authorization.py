"""PF-1A-E1 baseline-derived authorization snapshot (C1-01 / C1-02 correction).

This module is INDEPENDENT TEST EVIDENCE, not runtime configuration and not part of the
candidate implementation. It must never be imported by `app.*` production code, and its
tests must never import `app.modules.authorization.contract` as their expected value.

Provenance
----------
Every value in this file was read directly from the pre-PF-1A-E1 baseline commit,

    3c69355858ab352e246a8775f8a463ca7c9c15be

(the protected HEAD of branch `pf-1a-e1-permission-compatibility-foundation`, before the
uncommitted PF-1A-E1 working-tree changes), using

    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:<path>

against each of the nine route modules PF-1A-E1 touches, cross-checked against the full
`git diff HEAD -- <path>` (HEAD == baseline) of each file. Nothing here was copied from
`app.modules.authorization.contract`, from the Alembic seed migration, or generated at
test-collection time from candidate code.

If a future PF-1A-E1 edit changes `contract.py` or the seed migration, this file must NOT
be silently edited to match. A mismatch between this snapshot and the candidate is exactly
the signal `test_authorization_baseline_equivalence.py` exists to raise. This snapshot may
only be revised through a reviewed, human-approved change that records a new baseline
decision - never as a routine part of an ordinary PF-1A implementation or correction pass.

What this file covers
----------------------
1. `BASELINE_ROLE_CODES` - the six pre-existing transitional application roles.
2. `BASELINE_PERMISSION_ROLE_MATRIX` - all 31 permission capabilities x all 6 roles
   (186 allow/deny cells), keyed by the same permission-code strings PF-1A-E1 assigned to
   each pre-existing `*_ROLES` route-level constant (or, for Account tax verification, the
   one embedded in-body role check). The permission-code *strings* are stable identifiers
   chosen by PF-1A-E1's own naming; the *role tuples* mapped to them are the independently
   re-derived baseline fact this file exists to protect.
3. `BASELINE_ROUTE_PERMISSION_INVENTORY` - the exact `(HTTP method, path)` -> permission
   code for every one of the 76 baseline `require_roles(...)`-guarded routes.
4. `BASELINE_UNGATED_ROUTES` - the exact `(HTTP method, path)` for every route that was
   genuinely authenticated-only (or fully unauthenticated) at baseline, with no role
   distinction at all. This is an exact enumeration, not a path-prefix rule, so a future
   new route added under `/api/documents/*` or `/api/workflow/*` is NOT automatically
   exempted merely because it shares a prefix with a legitimately ungated legacy route.

Independent re-verification command (for a future reviewer)
--------------------------------------------------------------
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/accounts/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/commercial_offers/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/leads/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/opportunities/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/terms_and_conditions/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/work_orders/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/events/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/identity/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/documents/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/modules/workflow/routes.py
    git show 3c69355858ab352e246a8775f8a463ca7c9c15be:backend/app/main.py
"""

from __future__ import annotations

BASELINE_COMMIT = "3c69355858ab352e246a8775f8a463ca7c9c15be"
BASELINE_BRANCH = "pf-1a-e1-permission-compatibility-foundation"

# ---------------------------------------------------------------------------------------
# The six pre-existing transitional application roles. Copied literally (string
# constants), never imported from app.modules.authorization.contract.
# ---------------------------------------------------------------------------------------
ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

BASELINE_ROLE_CODES: tuple[str, ...] = (
    ROLE_ADMIN,
    ROLE_SALES_USER,
    ROLE_SALES_MANAGER,
    ROLE_FINANCE_USER,
    ROLE_OPERATIONS_USER,
    ROLE_MANAGEMENT_READ_ONLY,
)

# Two role-tuple shapes reused verbatim, at baseline, by many separate `*_ROLES`
# constants across modules. Naming them once here mirrors the baseline fact (the same
# tuple literal was independently written out in each baseline routes.py file) without
# inventing a new grouping concept.
_SALES_AND_ADMIN = (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER)
_ALL_SIX_ROLES = BASELINE_ROLE_CODES

# ---------------------------------------------------------------------------------------
# 31 permission codes x 6 roles = 186 cells. Each entry's baseline provenance (the exact
# pre-PF-1A-E1 module/constant it was read from) is recorded in
# `BASELINE_PERMISSION_SOURCE` immediately below the matrix, so a reviewer can trace every
# cell back to the file/line it was independently re-derived from.
# ---------------------------------------------------------------------------------------
BASELINE_PERMISSION_ROLE_MATRIX: dict[str, tuple[str, ...]] = {
    "ACCOUNT_CREATE": _SALES_AND_ADMIN,
    "ACCOUNT_READ": _ALL_SIX_ROLES,
    "ACCOUNT_CLASSIFICATION_MANAGE": _SALES_AND_ADMIN,
    "ACCOUNT_TAX_CAPTURE": (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    "ACCOUNT_TAX_VERIFY": (ROLE_FINANCE_USER,),
    "ACCOUNT_DOCUMENT_CAPTURE": (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    "COMMERCIAL_OFFER_CREATE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_READ": _ALL_SIX_ROLES,
    "COMMERCIAL_OFFER_UPDATE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE": (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_OPERATIONS_USER,
    ),
    "COMMERCIAL_OFFER_LINE_WRITE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_TC_CLAUSE_WRITE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE": _SALES_AND_ADMIN,
    "COMMERCIAL_OFFER_REVISION_WRITE": _SALES_AND_ADMIN,
    "LEAD_CREATE": _SALES_AND_ADMIN,
    "LEAD_READ": _ALL_SIX_ROLES,
    "LEAD_UPDATE": _SALES_AND_ADMIN,
    "LEAD_QUALIFICATION_DECIDE": _SALES_AND_ADMIN,
    "LEAD_CONVERT": _SALES_AND_ADMIN,
    "LEAD_ACTIVITY_CREATE": _SALES_AND_ADMIN,
    "OPPORTUNITY_CREATE": _SALES_AND_ADMIN,
    "OPPORTUNITY_READ": _ALL_SIX_ROLES,
    "OPPORTUNITY_UPDATE": _SALES_AND_ADMIN,
    "OPPORTUNITY_ACCOUNT_REPAIR": _SALES_AND_ADMIN,
    "TC_CLAUSE_READ": _ALL_SIX_ROLES,
    "WORK_ORDER_CREATE": (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    "WORK_ORDER_READ": _ALL_SIX_ROLES,
    "EVENTS_READ": (ROLE_ADMIN, ROLE_MANAGEMENT_READ_ONLY),
    "IDENTITY_ROLE_CATALOG_READ": (ROLE_ADMIN,),
}

assert len(BASELINE_PERMISSION_ROLE_MATRIX) == 31, (
    f"expected 31 baseline permission capabilities, found {len(BASELINE_PERMISSION_ROLE_MATRIX)}"
)

# Baseline file/constant each permission code's role tuple was read from. Traceability
# only; not consumed by runtime code or by the equivalence tests themselves.
BASELINE_PERMISSION_SOURCE: dict[str, str] = {
    "ACCOUNT_CREATE": "accounts/routes.py: ACCOUNT_CREATE_ROLES",
    "ACCOUNT_READ": "accounts/routes.py: ACCOUNT_READ_ROLES",
    "ACCOUNT_CLASSIFICATION_MANAGE": "accounts/routes.py: ACCOUNT_CLASSIFICATION_MAINTAIN_ROLES",
    "ACCOUNT_TAX_CAPTURE": "accounts/routes.py: ACCOUNT_TAX_CAPTURE_ROLES",
    "ACCOUNT_TAX_VERIFY": "accounts/routes.py: ACCOUNT_TAX_VERIFICATION_ROLES (embedded in-body check)",
    "ACCOUNT_DOCUMENT_CAPTURE": "accounts/routes.py: ACCOUNT_DOCUMENT_CAPTURE_ROLES",
    "COMMERCIAL_OFFER_CREATE": "commercial_offers/routes.py: COMMERCIAL_OFFER_CREATE_ROLES",
    "COMMERCIAL_OFFER_READ": "commercial_offers/routes.py: COMMERCIAL_OFFER_READ_ROLES",
    "COMMERCIAL_OFFER_UPDATE": "commercial_offers/routes.py: COMMERCIAL_OFFER_UPDATE_ROLES",
    "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE": (
        "commercial_offers/routes.py: COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE_ROLES"
    ),
    "COMMERCIAL_OFFER_LINE_WRITE": "commercial_offers/routes.py: COMMERCIAL_OFFER_LINE_WRITE_ROLES",
    "COMMERCIAL_OFFER_TC_CLAUSE_WRITE": "commercial_offers/routes.py: COMMERCIAL_OFFER_TC_CLAUSE_WRITE_ROLES",
    "COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE": (
        "commercial_offers/routes.py: COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE_ROLES"
    ),
    "COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE": "commercial_offers/routes.py: COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE_ROLES",
    "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE": (
        "commercial_offers/routes.py: COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE_ROLES"
    ),
    "COMMERCIAL_OFFER_REVISION_WRITE": "commercial_offers/routes.py: COMMERCIAL_OFFER_REVISION_WRITE_ROLES",
    "LEAD_CREATE": "leads/routes.py: LEAD_CREATE_ROLES",
    "LEAD_READ": "leads/routes.py: LEAD_READ_ROLES",
    "LEAD_UPDATE": "leads/routes.py: LEAD_UPDATE_ROLES",
    "LEAD_QUALIFICATION_DECIDE": "leads/routes.py: LEAD_QUALIFICATION_DECISION_ROLES",
    "LEAD_CONVERT": "leads/routes.py: LEAD_CONVERSION_ROLES",
    "LEAD_ACTIVITY_CREATE": "leads/routes.py: LEAD_ACTIVITY_CREATE_ROLES",
    "OPPORTUNITY_CREATE": "opportunities/routes.py: OPPORTUNITY_CREATE_ROLES",
    "OPPORTUNITY_READ": "opportunities/routes.py: OPPORTUNITY_READ_ROLES",
    "OPPORTUNITY_UPDATE": "opportunities/routes.py: OPPORTUNITY_UPDATE_ROLES",
    "OPPORTUNITY_ACCOUNT_REPAIR": "opportunities/routes.py: OPPORTUNITY_ACCOUNT_REPAIR_ROLES",
    "TC_CLAUSE_READ": "terms_and_conditions/routes.py: TC_CLAUSE_READ_ROLES",
    "WORK_ORDER_CREATE": "work_orders/routes.py: WORK_ORDER_CREATE_ROLES",
    "WORK_ORDER_READ": "work_orders/routes.py: WORK_ORDER_READ_ROLES",
    "EVENTS_READ": 'events/routes.py: inline require_roles("ADMIN", "MANAGEMENT_READ_ONLY")',
    "IDENTITY_ROLE_CATALOG_READ": 'identity/routes.py: inline require_roles("ADMIN")',
}

assert set(BASELINE_PERMISSION_SOURCE.keys()) == set(BASELINE_PERMISSION_ROLE_MATRIX.keys())

for _permission_code, _role_codes in BASELINE_PERMISSION_ROLE_MATRIX.items():
    _unknown = set(_role_codes) - set(BASELINE_ROLE_CODES)
    if _unknown:
        raise RuntimeError(f"baseline snapshot: {_permission_code!r} maps to unknown role(s) {_unknown!r}")


# ---------------------------------------------------------------------------------------
# Exact (HTTP method, path) -> permission code for all 76 baseline `require_roles(...)`
# guarded routes, independently re-derived from the same nine baseline route modules
# (plus `app/main.py` for router mounting) named in the module docstring above.
#
# Baseline `require_roles(*ROLES)` guards resolved to a role tuple; PF-1A-E1 assigns each
# of those pre-existing route-level guards to exactly one new permission code. This table
# therefore proves route-level migration completeness/correctness (right route -> right
# permission), while `BASELINE_PERMISSION_ROLE_MATRIX` above proves permission-level
# compatibility (right permission -> right roles). Both are required; neither implies the
# other.
# ---------------------------------------------------------------------------------------
BASELINE_ROUTE_PERMISSION_INVENTORY: dict[tuple[str, str], str] = {
    # Accounts (backend/app/modules/accounts/routes.py) - 14 routes
    ("POST", "/api/accounts"): "ACCOUNT_CREATE",
    ("GET", "/api/accounts"): "ACCOUNT_READ",
    ("GET", "/api/accounts/{public_id}/classification"): "ACCOUNT_READ",
    ("PUT", "/api/accounts/{public_id}/classification"): "ACCOUNT_CLASSIFICATION_MANAGE",
    ("GET", "/api/accounts/{public_id}/contacts"): "ACCOUNT_READ",
    ("POST", "/api/accounts/{public_id}/contacts"): "ACCOUNT_CREATE",
    ("GET", "/api/accounts/{public_id}/addresses"): "ACCOUNT_READ",
    ("POST", "/api/accounts/{public_id}/addresses"): "ACCOUNT_CREATE",
    ("GET", "/api/accounts/{public_id}/tax-profile"): "ACCOUNT_READ",
    ("POST", "/api/accounts/{public_id}/tax-profile"): "ACCOUNT_TAX_CAPTURE",
    ("POST", "/api/accounts/{public_id}/gstins"): "ACCOUNT_TAX_CAPTURE",
    ("GET", "/api/accounts/{public_id}/documents"): "ACCOUNT_READ",
    ("POST", "/api/accounts/{public_id}/documents"): "ACCOUNT_DOCUMENT_CAPTURE",
    ("GET", "/api/accounts/{public_id}"): "ACCOUNT_READ",
    # Commercial Offers (backend/app/modules/commercial_offers/routes.py) - 30 routes
    ("POST", "/api/commercial-offers"): "COMMERCIAL_OFFER_CREATE",
    ("GET", "/api/commercial-offers"): "COMMERCIAL_OFFER_READ",
    ("GET", "/api/commercial-offers/{public_id}"): "COMMERCIAL_OFFER_READ",
    ("GET", "/api/commercial-offers/{public_id}/related-offers"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/related-offers"): "COMMERCIAL_OFFER_CREATE",
    ("GET", "/api/commercial-offers/{public_id}/submission-readiness"): "COMMERCIAL_OFFER_READ",
    ("GET", "/api/commercial-offers/{public_id}/lifecycle-guidance"): "COMMERCIAL_OFFER_READ",
    ("GET", "/api/commercial-offers/{public_id}/submission-evidence"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/submission-evidence"): "COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE",
    ("GET", "/api/commercial-offers/{public_id}/credit-review"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/credit-review"): "COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE",
    ("GET", "/api/commercial-offers/{public_id}/customer-responses"): "COMMERCIAL_OFFER_READ",
    (
        "POST",
        "/api/commercial-offers/{public_id}/customer-responses",
    ): "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE",
    ("GET", "/api/commercial-offers/{public_id}/revisions"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/revisions"): "COMMERCIAL_OFFER_REVISION_WRITE",
    (
        "POST",
        "/api/commercial-offers/{public_id}/revisions/{revision_public_id}/mark-resubmitted",
    ): "COMMERCIAL_OFFER_REVISION_WRITE",
    (
        "POST",
        "/api/commercial-offers/{public_id}/revisions/{revision_public_id}/cancel",
    ): "COMMERCIAL_OFFER_REVISION_WRITE",
    ("POST", "/api/commercial-offers/{public_id}/mark-submitted"): "COMMERCIAL_OFFER_UPDATE",
    ("PUT", "/api/commercial-offers/{public_id}"): "COMMERCIAL_OFFER_UPDATE",
    ("GET", "/api/commercial-offers/{public_id}/lines"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/lines"): "COMMERCIAL_OFFER_LINE_WRITE",
    ("PUT", "/api/commercial-offers/{public_id}/lines/{line_public_id}"): "COMMERCIAL_OFFER_LINE_WRITE",
    ("GET", "/api/commercial-offers/{public_id}/tc-clauses"): "COMMERCIAL_OFFER_READ",
    ("GET", "/api/commercial-offers/{public_id}/tc-clause-readiness"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/tc-clauses"): "COMMERCIAL_OFFER_TC_CLAUSE_WRITE",
    (
        "POST",
        "/api/commercial-offers/{public_id}/tc-clauses/attach-recommended",
    ): "COMMERCIAL_OFFER_TC_CLAUSE_WRITE",
    (
        "DELETE",
        "/api/commercial-offers/{public_id}/tc-clauses/{attachment_public_id}",
    ): "COMMERCIAL_OFFER_TC_CLAUSE_WRITE",
    ("GET", "/api/commercial-offers/{public_id}/pricing-evidence"): "COMMERCIAL_OFFER_READ",
    ("POST", "/api/commercial-offers/{public_id}/pricing-evidence"): "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE",
    (
        "POST",
        "/api/commercial-offers/{public_id}/pricing-evidence/{evidence_public_id}/select-basis",
    ): "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE",
    # Leads (backend/app/modules/leads/routes.py) - 8 routes
    ("POST", "/api/leads"): "LEAD_CREATE",
    ("GET", "/api/leads"): "LEAD_READ",
    ("GET", "/api/leads/{public_id}/activities"): "LEAD_READ",
    ("POST", "/api/leads/{public_id}/activities"): "LEAD_ACTIVITY_CREATE",
    ("POST", "/api/leads/{public_id}/qualification-decision"): "LEAD_QUALIFICATION_DECIDE",
    ("POST", "/api/leads/{public_id}/convert"): "LEAD_CONVERT",
    ("GET", "/api/leads/{public_id}"): "LEAD_READ",
    ("PUT", "/api/leads/{public_id}"): "LEAD_UPDATE",
    # Opportunities (backend/app/modules/opportunities/routes.py) - 5 routes
    ("POST", "/api/opportunities"): "OPPORTUNITY_CREATE",
    ("GET", "/api/opportunities"): "OPPORTUNITY_READ",
    ("GET", "/api/opportunities/{public_id}"): "OPPORTUNITY_READ",
    ("PUT", "/api/opportunities/{public_id}"): "OPPORTUNITY_UPDATE",
    ("POST", "/api/opportunities/{public_id}/account-repair"): "OPPORTUNITY_ACCOUNT_REPAIR",
    # Terms and Conditions (backend/app/modules/terms_and_conditions/routes.py) - 2 routes
    ("GET", "/api/tc-clauses"): "TC_CLAUSE_READ",
    ("GET", "/api/tc-clauses/{public_id}"): "TC_CLAUSE_READ",
    # Work Orders (backend/app/modules/work_orders/routes.py) - 15 routes
    ("POST", "/api/work-orders/from-commercial-offer"): "WORK_ORDER_CREATE",
    ("GET", "/api/work-orders"): "WORK_ORDER_READ",
    ("GET", "/api/work-orders/{public_id}"): "WORK_ORDER_READ",
    ("GET", "/api/work-orders/{public_id}/lines"): "WORK_ORDER_READ",
    ("GET", "/api/work-orders/{public_id}/related-offers"): "WORK_ORDER_READ",
    ("GET", "/api/work-orders/{public_id}/amendments"): "WORK_ORDER_READ",
    ("POST", "/api/work-orders/{public_id}/amendments"): "WORK_ORDER_CREATE",
    ("GET", "/api/work-orders/{public_id}/amendments/{amendment_public_id}"): "WORK_ORDER_READ",
    ("PUT", "/api/work-orders/{public_id}/amendments/{amendment_public_id}"): "WORK_ORDER_CREATE",
    ("POST", "/api/work-orders/{public_id}/amendments/{amendment_public_id}/decision"): "WORK_ORDER_CREATE",
    ("GET", "/api/work-orders/{public_id}/amendments/{amendment_public_id}/readiness"): "WORK_ORDER_READ",
    ("GET", "/api/work-orders/{public_id}/amendments/{amendment_public_id}/lines"): "WORK_ORDER_READ",
    ("POST", "/api/work-orders/{public_id}/amendments/{amendment_public_id}/lines"): "WORK_ORDER_CREATE",
    (
        "PUT",
        "/api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}",
    ): "WORK_ORDER_CREATE",
    (
        "DELETE",
        "/api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}",
    ): "WORK_ORDER_CREATE",
    # Events (backend/app/modules/events/routes.py) - 1 route
    ("GET", "/api/events/recent"): "EVENTS_READ",
    # Identity administration (backend/app/modules/identity/routes.py) - 1 route
    ("GET", "/api/auth/roles"): "IDENTITY_ROLE_CATALOG_READ",
}

assert len(BASELINE_ROUTE_PERMISSION_INVENTORY) == 76, (
    f"expected 76 baseline protected routes, found {len(BASELINE_ROUTE_PERMISSION_INVENTORY)}"
)
assert set(BASELINE_ROUTE_PERMISSION_INVENTORY.values()) <= set(BASELINE_PERMISSION_ROLE_MATRIX.keys()), (
    "route inventory references a permission code absent from the baseline role matrix"
)

# ---------------------------------------------------------------------------------------
# Exact (HTTP method, path) for every route that was genuinely authenticated-only, or
# fully unauthenticated, at baseline - never `require_roles(...)` guarded, so leaving it
# unmigrated is not a PF-1A-E1 gap. This is an EXACT enumeration (11 routes), not a
# path-prefix allowlist: a new route later added under `/api/documents/*` or
# `/api/workflow/*` must be explicitly added here (after confirming it genuinely has no
# role distinction) or it will correctly fail the route-permission-inventory test.
# ---------------------------------------------------------------------------------------
BASELINE_UNGATED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # No authenticated caller yet exists; this route creates the session.
        ("POST", "/api/auth/login"),
        # Returns the caller's own identity; no role/permission decides it.
        ("GET", "/api/auth/me"),
        # Unauthenticated diagnostics, defined directly in app/main.py.
        ("GET", "/api/health"),
        ("GET", "/api/platform/config-summary"),
        ("GET", "/api/platform/db-health"),
        # backend/app/modules/documents/routes.py: bespoke "any authenticated user"
        # dependency (`require_current_user`), never `require_roles(...)`.
        ("GET", "/api/documents/types"),
        ("GET", "/api/documents/recent"),
        ("GET", "/api/documents/by-record/{record_type}/{record_public_id}"),
        ("POST", "/api/documents/metadata"),
        # backend/app/modules/workflow/routes.py: `get_current_user` directly, never
        # `require_roles(...)`.
        ("GET", "/api/workflow/statuses"),
        ("GET", "/api/workflow/modules"),
    }
)

assert len(BASELINE_UNGATED_ROUTES) == 11, f"expected 11 baseline ungated routes, found {len(BASELINE_UNGATED_ROUTES)}"
assert BASELINE_UNGATED_ROUTES.isdisjoint(BASELINE_ROUTE_PERMISSION_INVENTORY.keys()), (
    "a route cannot be both permission-gated and ungated"
)
