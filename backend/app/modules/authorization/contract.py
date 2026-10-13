"""PF-1A-E1 explicit application-permission contract.

This module is the single authoritative source for:

- every explicit application-permission code introduced by PF-1A-E1;
- the compatibility mapping from the six existing transitional application
  roles to those permission codes.

Context: PF-1A-E1 is a compatibility/migration foundation, not the full
Organization Authority implementation. See `docs/agent/contracts/
organization-authority-authorization-contract.md` (ORA-001) and
`docs/agent/pf-1a/PF_1A_E1_EXPLICIT_PERMISSION_COMPATIBILITY_FOUNDATION.md`.

The compatibility matrix below was derived directly from the actual
`require_roles(...)` route guards (and one embedded in-body role check in the
Accounts module) present on branch `pf-1a-e1-permission-compatibility-foundation`
at baseline commit `3c69355858ab352e246a8775f8a463ca7c9c15be`, not invented or
guessed from documentation. Every permission code below corresponds 1:1 to a
previously-named `*_ROLES` route-level constant (or, where no named constant
existed, to one inline role tuple), so that the current effective access
matrix is preserved exactly rather than re-derived through a new judgement
about which endpoints "really" share a capability.

Do not add a business-authority code (CREDIT_ASSESSOR, CREDIT_APPROVER, or any
future ORA authority code) to this file. This contract is limited to
coarse-grained application permissions used for backend route authorization.
"""

from __future__ import annotations

AUTHZ_PERMISSION_TABLE = "authz_permission"
AUTHZ_ROLE_PERMISSION_TABLE = "authz_role_permission"

# The six existing transitional application roles (see `role` table, seeded by
# Alembic revision 20260629_0001). PF-1A-E1 treats these as compatibility
# input only; it does not add, remove or rename any role.
ROLE_ADMIN = "ADMIN"
ROLE_SALES_USER = "SALES_USER"
ROLE_SALES_MANAGER = "SALES_MANAGER"
ROLE_FINANCE_USER = "FINANCE_USER"
ROLE_OPERATIONS_USER = "OPERATIONS_USER"
ROLE_MANAGEMENT_READ_ONLY = "MANAGEMENT_READ_ONLY"

KNOWN_ROLE_CODES = (
    ROLE_ADMIN,
    ROLE_SALES_USER,
    ROLE_SALES_MANAGER,
    ROLE_FINANCE_USER,
    ROLE_OPERATIONS_USER,
    ROLE_MANAGEMENT_READ_ONLY,
)

# ---------------------------------------------------------------------------
# Accounts (backend/app/modules/accounts/routes.py)
# ---------------------------------------------------------------------------
ACCOUNT_CREATE = "ACCOUNT_CREATE"
ACCOUNT_READ = "ACCOUNT_READ"
ACCOUNT_CLASSIFICATION_MANAGE = "ACCOUNT_CLASSIFICATION_MANAGE"
ACCOUNT_TAX_CAPTURE = "ACCOUNT_TAX_CAPTURE"
ACCOUNT_TAX_VERIFY = "ACCOUNT_TAX_VERIFY"
ACCOUNT_DOCUMENT_CAPTURE = "ACCOUNT_DOCUMENT_CAPTURE"

# ---------------------------------------------------------------------------
# Commercial Offers (backend/app/modules/commercial_offers/routes.py)
# ---------------------------------------------------------------------------
COMMERCIAL_OFFER_CREATE = "COMMERCIAL_OFFER_CREATE"
COMMERCIAL_OFFER_READ = "COMMERCIAL_OFFER_READ"
COMMERCIAL_OFFER_UPDATE = "COMMERCIAL_OFFER_UPDATE"
COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE = "COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE"
COMMERCIAL_OFFER_LINE_WRITE = "COMMERCIAL_OFFER_LINE_WRITE"
COMMERCIAL_OFFER_TC_CLAUSE_WRITE = "COMMERCIAL_OFFER_TC_CLAUSE_WRITE"
COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE = "COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE"
COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE = "COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE"
COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE = "COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE"
COMMERCIAL_OFFER_REVISION_WRITE = "COMMERCIAL_OFFER_REVISION_WRITE"

# ---------------------------------------------------------------------------
# Leads (backend/app/modules/leads/routes.py)
# ---------------------------------------------------------------------------
LEAD_CREATE = "LEAD_CREATE"
LEAD_READ = "LEAD_READ"
LEAD_UPDATE = "LEAD_UPDATE"
LEAD_QUALIFICATION_DECIDE = "LEAD_QUALIFICATION_DECIDE"
LEAD_CONVERT = "LEAD_CONVERT"
LEAD_ACTIVITY_CREATE = "LEAD_ACTIVITY_CREATE"

# ---------------------------------------------------------------------------
# Opportunities (backend/app/modules/opportunities/routes.py)
# ---------------------------------------------------------------------------
OPPORTUNITY_CREATE = "OPPORTUNITY_CREATE"
OPPORTUNITY_READ = "OPPORTUNITY_READ"
OPPORTUNITY_UPDATE = "OPPORTUNITY_UPDATE"
OPPORTUNITY_ACCOUNT_REPAIR = "OPPORTUNITY_ACCOUNT_REPAIR"

# ---------------------------------------------------------------------------
# Terms and Conditions (backend/app/modules/terms_and_conditions/routes.py)
# ---------------------------------------------------------------------------
TC_CLAUSE_READ = "TC_CLAUSE_READ"

# ---------------------------------------------------------------------------
# Work Orders (backend/app/modules/work_orders/routes.py)
# ---------------------------------------------------------------------------
WORK_ORDER_CREATE = "WORK_ORDER_CREATE"
WORK_ORDER_READ = "WORK_ORDER_READ"

# ---------------------------------------------------------------------------
# Events (backend/app/modules/events/routes.py)
# ---------------------------------------------------------------------------
EVENTS_READ = "EVENTS_READ"

# ---------------------------------------------------------------------------
# Identity administration (backend/app/modules/identity/routes.py)
#
# This is the role *catalogue* read used by administrative screens, not
# authentication itself. Login (`POST /api/auth/login`) and the authenticated
# self profile (`GET /api/auth/me`) remain pure authentication and are not
# permission-gated; they stay on `get_current_user` only, per the ORA-001
# authentication/authorization separation.
# ---------------------------------------------------------------------------
IDENTITY_ROLE_CATALOG_READ = "IDENTITY_ROLE_CATALOG_READ"


# ===========================================================================
# POST-BASELINE PERMISSIONS
#
# Everything above this line existed at PF-1A-E1 and is part of the frozen
# baseline evidence (see ROLE_PERMISSION_COMPATIBILITY_MATRIX below). Codes
# below this line were introduced afterwards and belong to
# POST_BASELINE_ROLE_PERMISSION_MATRIX instead. Keep the two sides separate:
# adding a new code to the baseline matrix destroys the independence of
# PF-1A-E1's proof, which is exactly what that proof exists to rule out.
# ===========================================================================

# ---------------------------------------------------------------------------
# Interactions - Slice 9D (backend/app/modules/interactions/routes.py)
#
# INTERACTION_READ covers the metadata of a recorded conversation: who, when,
# which channel, the subject and the outcome. INTERACTION_CONTENT_READ is a
# deliberately separate grant covering the stored message body, the
# participants' email addresses/phone numbers, and the external references
# that ADDRESS that body - all Restricted personal/statutory data under
# DATA_CLASSIFICATION_AND_HANDLING.md.
#
# The split exists so that *who may read customer correspondence* is a grant
# that can change without a code change. A caller holding INTERACTION_READ but
# not INTERACTION_CONTENT_READ sees the conversation with its content blanked
# - not a 403, because the existence of the conversation is not the sensitive
# part.
# ---------------------------------------------------------------------------
INTERACTION_READ = "INTERACTION_READ"
INTERACTION_CONTENT_READ = "INTERACTION_CONTENT_READ"
INTERACTION_CREATE = "INTERACTION_CREATE"
INTERACTION_UPDATE = "INTERACTION_UPDATE"
INTERACTION_DELETE = "INTERACTION_DELETE"

# ---------------------------------------------------------------------------
# Documents - Slice 9C (backend/app/modules/documents/routes.py)
#
# DOCUMENT_READ is granted to all six roles, reproducing today's authenticated-only reach so
# tightening these previously-ungated routes (see POST_BASELINE_TIGHTENED_ROUTES in
# tests/fixtures/post_baseline_tightened_routes.py) changes nothing for an existing caller at
# the route level. The real narrowing this slice adds is NOT this permission - it is the
# record-scoped, fail-closed check in documents/service.py, which limits what DOCUMENT_READ
# actually returns to documents linked to a record the caller may independently read.
#
# DOCUMENT_CONTENT_READ is the download grant, deliberately separate from DOCUMENT_READ (a
# caller may see that a document exists without being able to fetch its bytes) and narrower:
# downloading a document linked to a customer conversation additionally requires
# INTERACTION_CONTENT_READ, so an attachment cannot be used as a pointer around the content
# redaction Slice 9D already established for message bodies.
#
# DOCUMENT_UPLOAD works like DOCUMENT_READ (owner decision, 11 September 2026): all six roles
# hold it, and it only admits a caller to the upload and metadata routes. What they may attach a
# file to is decided per linked record type by DOCUMENT_LINK_WRITE_PERMISSION in
# documents/contract.py - the permission to change that record - so MANAGEMENT_READ_ONLY can
# attach to nothing despite holding this grant. Its description below predates that decision
# and is unchanged.
# ---------------------------------------------------------------------------
DOCUMENT_READ = "DOCUMENT_READ"
DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
DOCUMENT_CONTENT_READ = "DOCUMENT_CONTENT_READ"

# ---------------------------------------------------------------------------
# Commercial Offer quotation generation - Slice 9E
# (backend/app/modules/commercial_offers/routes.py)
#
# COMMERCIAL_OFFER_QUOTE_GENERATE matches the existing Commercial Offer create/manage role set
# (ADMIN, SALES_USER, SALES_MANAGER): preparing a quote document is ordinary Sales work, the
# same as adding a line or attaching a T&C clause.
#
# COMMERCIAL_OFFER_QUOTE_APPROVE is deliberately narrower and deliberately excludes
# SALES_USER (owner decision 4, 8 September 2026): a Sales User may generate a quote but not
# approve it for issue, so the "only approved quotations may be shared with customers" gate
# separates preparation from release rather than being a self-attestation any preparer can also
# grant themselves. This does not achieve full maker-checker - a Sales Manager may still both
# prepare and approve their own quote - that residual limitation is `APR-001`'s to close; see
# docs/agent/slices/slice-9e-quotation-generation.md, "Decision 3, and what the gate does and
# does not do".
# ---------------------------------------------------------------------------
COMMERCIAL_OFFER_QUOTE_GENERATE = "COMMERCIAL_OFFER_QUOTE_GENERATE"
COMMERCIAL_OFFER_QUOTE_APPROVE = "COMMERCIAL_OFFER_QUOTE_APPROVE"

# ---------------------------------------------------------------------------
# Work Order line operational detail - Slice 7C
# (backend/app/modules/work_orders/routes.py)
#
# Its own permission rather than a reuse of WORK_ORDER_CREATE, although today it holds the same
# four roles (owner decision 2, 14 September 2026). Reusing WORK_ORDER_CREATE would mean a later
# change to who may create a Work Order silently changed who may record a line's site and billing
# GSTIN - the coupling DEFERRED_REQUIREMENTS.md already records against document upload.
# ---------------------------------------------------------------------------
WORK_ORDER_LINE_DETAIL_WRITE = "WORK_ORDER_LINE_DETAIL_WRITE"

# ---------------------------------------------------------------------------
# Post-baseline (Slice 7D Part 1): Work Order line billing terms. Its own permission, holding the same
# four roles as WORK_ORDER_LINE_DETAIL_WRITE (owner decision 5, 14 September 2026), so who may change
# a line's rates can later differ from who may change its site and billing identity.
# ---------------------------------------------------------------------------
WORK_ORDER_LINE_BILLING_TERMS_WRITE = "WORK_ORDER_LINE_BILLING_TERMS_WRITE"

# ---------------------------------------------------------------------------
# Post-baseline (Slice 7D Part 3): the Work Order's contract period, and the extensions that move its
# end date. Two permissions rather than one, and both holding the same four roles today, because
# owner decision 18 of 17 September 2026 asks for the dates to be recordable "under a permission of
# their own, so extensions can later be narrowed to managers without touching code" - narrowing a
# single shared permission would also narrow who may set the original dates, which is not that.
#
# These govern the WORK ORDER's contract dates only. A line's own start and end dates are part of
# that line's operational detail - they live on its 7C detail row and are saved through the 7C route -
# so they are governed by WORK_ORDER_LINE_DETAIL_WRITE, like every other field on that row. An
# earlier draft of this comment claimed otherwise, which independent review caught: a permission
# description must state what is actually enforced, or narrowing a grant will not narrow what the
# description promised (round 1, finding F-04).
#
# Copying one line's terms onto other lines is deliberately NOT a third permission: it writes billing
# terms, so it asks for WORK_ORDER_LINE_BILLING_TERMS_WRITE above. So does Slice 7D Part 4's holiday
# list, although it belongs to the Work Order rather than a line: which days are holidays decides which
# days take a line's off-day rate.
# ---------------------------------------------------------------------------
WORK_ORDER_CONTRACT_PERIOD_WRITE = "WORK_ORDER_CONTRACT_PERIOD_WRITE"
WORK_ORDER_CONTRACT_EXTENSION_WRITE = "WORK_ORDER_CONTRACT_EXTENSION_WRITE"

# ---------------------------------------------------------------------------
# Post-baseline (WRR-001): Resource Requirements and the platform's Equipment Reference
# (backend/app/modules/resource_requirements/routes.py, backend/app/modules/equipment_reference/routes.py).
#
# Reading follows who can view Work Orders. Writing is Operations and Admin only (owner, answer Q6 of
# 24 September 2026): a requirement is Operations' record of what a line needs on site, so Sales and
# Finance read it but do not change it. The equipment structure has no write permission: version 1
# changes only by migration, and a maintenance screen for its owner will bring its own.
# ---------------------------------------------------------------------------
RESOURCE_REQUIREMENT_READ = "RESOURCE_REQUIREMENT_READ"
RESOURCE_REQUIREMENT_WRITE = "RESOURCE_REQUIREMENT_WRITE"
EQUIPMENT_REFERENCE_READ = "EQUIPMENT_REFERENCE_READ"

# ---------------------------------------------------------------------------
# Post-baseline (ERT-1): the Plum report transformer, models and machines
# (backend/app/modules/equipment_reference/routes.py).
#
# Managing equipment - importing and confirming Plum's report, models and their mapping, value rules,
# machine corrections, a machine's details and own values, fitting parts - is Admin's alone (owner,
# comment 1 of 25 September 2026): setting up equipment rests with one or two responsible people outside
# day-to-day operations. A Fleet Admin role, when it exists, is given this permission by a grant with no
# code change. Reading machines, models and corrections follows EQUIPMENT_REFERENCE_READ.
# ---------------------------------------------------------------------------
EQUIPMENT_REFERENCE_MANAGE = "EQUIPMENT_REFERENCE_MANAGE"
# A machine's engine and chassis numbers are confidential (owner, 25 September 2026): shown to Admin only
# for now. Whether Operations should see them, and Finance during audits, is the owner's to decide later;
# either is a grant of this permission, with no code change. Without it, a reader sees every other fact of a machine, and a
# correction or value rule that carries such a number shows that it exists but not the number.
EQUIPMENT_IDENTITY_READ = "EQUIPMENT_IDENTITY_READ"

# ---------------------------------------------------------------------------
# Post-baseline (ELG-1): machine eligibility (backend/app/modules/eligibility/routes.py).
#
# Seeing certificates, marks, the check, Certificates due and the rules follows EQUIPMENT_REFERENCE_READ;
# recording certificates and "not applicable" marks is EQUIPMENT_REFERENCE_MANAGE's, as every fleet record
# is; certificate numbers and copies follow EQUIPMENT_IDENTITY_READ (owner, 27 September 2026, Q6). Adding
# and ending the rules is Admin's alone (Q7), under its own code: rules are law rather than fleet data, and
# the people half's rules (8B) will sit under the same permission, so a compliance officer can be given it
# without the fleet's rights - a grant, with no code change.
# ---------------------------------------------------------------------------
ELIGIBILITY_RULE_MANAGE = "ELIGIBILITY_RULE_MANAGE"

# ---------------------------------------------------------------------------
# Post-baseline (8A core): own machines allocated to the resource requirements
# (backend/app/modules/resource_assignments/routes.py).
#
# Reading follows who can view Work Orders. Allocating, replacing, freeing, changing dates, checking again
# and the kit list are Operations' and Admin's, as requirements are (WRR-001, Q6) - under codes of their
# own, so who may commit machines can later differ from who records what is needed, with no code change.
# Setting a machine's billing cycle asks for WORK_ORDER_LINE_BILLING_TERMS_WRITE instead: who may change a
# line's rates should be one answer, not two (Slice 7D).
# ---------------------------------------------------------------------------
RESOURCE_ASSIGNMENT_READ = "RESOURCE_ASSIGNMENT_READ"
RESOURCE_ASSIGNMENT_WRITE = "RESOURCE_ASSIGNMENT_WRITE"

# ---------------------------------------------------------------------------
# Post-baseline (HOL-1): PBL's holiday calendar (backend/app/modules/holiday_calendar/routes.py).
#
# Everyone reads it, so the six roles hold HOLIDAY_CALENDAR_READ. Keeping it - entering and changing a year, and
# marking it complete - is Admin's until a position is mapped under ORA-001 (owner, 2 October 2026), given by a grant
# with no code change. A Work Order's own changes to the calendar are its billing terms, so they stay under
# WORK_ORDER_LINE_BILLING_TERMS_WRITE (Slice 7D Part 4).
# ---------------------------------------------------------------------------
HOLIDAY_CALENDAR_READ = "HOLIDAY_CALENDAR_READ"
HOLIDAY_CALENDAR_MANAGE = "HOLIDAY_CALENDAR_MANAGE"


PERMISSION_DESCRIPTIONS: dict[str, str] = {
    ACCOUNT_CREATE: "Create an Account / business_party, an Account Contact or an Account Address.",
    ACCOUNT_READ: "View Account / business_party records and their subordinate detail sections.",
    ACCOUNT_CLASSIFICATION_MANAGE: "Update Account ownership/classification (owner, segment, industry, strategic flag).",
    ACCOUNT_TAX_CAPTURE: "Capture/update Account PAN/GST tax-profile and GSTIN entries.",
    ACCOUNT_TAX_VERIFY: "Set an Account PAN/GST verification state to a final state (VERIFIED / REJECTED_INCORRECT).",
    ACCOUNT_DOCUMENT_CAPTURE: "Record Account document metadata.",
    COMMERCIAL_OFFER_CREATE: "Create a Commercial Offer, including a related (Supplementary/Change Quotation) offer.",
    COMMERCIAL_OFFER_READ: "View Commercial Offers and their subordinate detail/readiness/history views.",
    COMMERCIAL_OFFER_UPDATE: "Update a Commercial Offer header or mark it submitted.",
    COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE: "Add Commercial Offer pricing evidence or select the basis rate.",
    COMMERCIAL_OFFER_LINE_WRITE: "Add or update a Commercial Offer line.",
    COMMERCIAL_OFFER_TC_CLAUSE_WRITE: "Attach or remove Commercial Offer header T&C clauses.",
    COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE: "Record Commercial Offer submission evidence.",
    COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE: "Record a Commercial Offer manual credit/exposure review.",
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE: "Record a Commercial Offer customer response / award outcome.",
    COMMERCIAL_OFFER_REVISION_WRITE: "Open, resubmit or cancel a Commercial Offer revision.",
    LEAD_CREATE: "Create a Lead.",
    LEAD_READ: "View Leads and their activities.",
    LEAD_UPDATE: "Update early Lead details.",
    LEAD_QUALIFICATION_DECIDE: "Record a Lead qualification/closure decision.",
    LEAD_CONVERT: "Convert a qualified Lead into an Account and Opportunity.",
    LEAD_ACTIVITY_CREATE: "Record a Lead activity/follow-up.",
    OPPORTUNITY_CREATE: "Create an Opportunity.",
    OPPORTUNITY_READ: "View Opportunities.",
    OPPORTUNITY_UPDATE: "Update an Opportunity.",
    OPPORTUNITY_ACCOUNT_REPAIR: "Repair a missing Opportunity-to-Account link.",
    TC_CLAUSE_READ: "View the Terms and Conditions clause library.",
    WORK_ORDER_CREATE: "Create a Work Order shell handoff, or create/update a Work Order Amendment.",
    WORK_ORDER_READ: "View Work Orders, their lines, related offers and amendments.",
    EVENTS_READ: "View recent business events.",
    IDENTITY_ROLE_CATALOG_READ: "View the application role catalogue.",
    # Post-baseline (Slice 9D).
    INTERACTION_READ: "View recorded conversations: who, when, which channel, subject and outcome.",
    INTERACTION_CONTENT_READ: "Read the stored message content and participant email addresses or phone numbers.",
    INTERACTION_CREATE: "Record a conversation against a Lead, Account, Opportunity, Commercial Offer or Work Order.",
    INTERACTION_UPDATE: "Correct the outcome or follow-up date on a recorded conversation.",
    INTERACTION_DELETE: "Soft-delete a conversation recorded in error.",
    # Post-baseline (Slice 9C).
    DOCUMENT_READ: "Use the documents API and see document metadata for records you may read.",
    DOCUMENT_UPLOAD: "Upload a file, or record document metadata pointing at an external file.",
    DOCUMENT_CONTENT_READ: "Download the stored bytes of an uploaded document.",
    # Post-baseline (Slice 9E).
    COMMERCIAL_OFFER_QUOTE_GENERATE: "Generate a frozen quotation document version from a Commercial Offer.",
    COMMERCIAL_OFFER_QUOTE_APPROVE: "Approve a generated quotation document version for issue to the customer.",
    WORK_ORDER_LINE_DETAIL_WRITE: (
        "Record or change a Work Order line's site, billing GSTIN, billing address and customer line reference."
    ),
    # Reworded by Slice 7D Part 4 (migration 20260908_0040), which also puts the Work Order's holiday
    # list under it: holidays decide which days take a line's off-day rate, so who may change a rate
    # decides them too. The 0037 wording had not named Part 2's terms or Part 3's copying either.
    WORK_ORDER_LINE_BILLING_TERMS_WRITE: (
        "Record or change a Work Order line's billing terms and their periods, copy them to other lines, "
        "and record the holidays the Work Order names."
    ),
    # Post-baseline (WRR-001).
    RESOURCE_REQUIREMENT_READ: "View the resources Work Order lines need, and the planning list.",
    RESOURCE_REQUIREMENT_WRITE: "Record, change or cancel what a Work Order line needs on site.",
    EQUIPMENT_REFERENCE_READ: (
        "View the platform's equipment structure: classes, types, capabilities and the words that map to them."
    ),
    # Post-baseline (ERT-1).
    EQUIPMENT_REFERENCE_MANAGE: (
        "Import Plum's vehicle report and confirm it; record models and map Plum's model names to them; "
        "record how Plum's values are read and correct one machine's values; enter a machine's details and "
        "own capability values; fit parts to machines."
    ),
    EQUIPMENT_IDENTITY_READ: (
        "See machines' engine and chassis numbers, including in the corrections and value rules that carry them."
    ),
    # Post-baseline (ELG-1).
    ELIGIBILITY_RULE_MANAGE: (
        "Add and end the rules that say which certificates each kind of machine needs, where, and how often."
    ),
    # Post-baseline (8A core).
    RESOURCE_ASSIGNMENT_READ: "View the machines allocated to Work Orders, and find machines for a requirement.",
    RESOURCE_ASSIGNMENT_WRITE: (
        "Allocate machines to a Work Order's requirements; replace or free them, change their dates, check them "
        "again, and list the kit going to site."
    ),
    # Post-baseline (HOL-1).
    HOLIDAY_CALENDAR_READ: "View PBL's holiday calendar, year by year.",
    HOLIDAY_CALENDAR_MANAGE: "Enter and change PBL's holiday calendar for a year, and mark a year complete.",
    # Post-baseline (Slice 7D Part 3).
    WORK_ORDER_CONTRACT_PERIOD_WRITE: (
        "Record or change a Work Order's contract start and end dates."
    ),
    WORK_ORDER_CONTRACT_EXTENSION_WRITE: (
        "Record an extension that moves a Work Order's contract end date."
    ),
}

# The complete current-effective compatibility mapping. This is the actual
# access matrix in force immediately before PF-1A-E1, expressed as data
# instead of route-level role tuples. Every value below is copied verbatim
# from the corresponding pre-existing `*_ROLES` constant (or inline tuple).
ROLE_PERMISSION_COMPATIBILITY_MATRIX: dict[str, tuple[str, ...]] = {
    ACCOUNT_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ACCOUNT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    ACCOUNT_CLASSIFICATION_MANAGE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    ACCOUNT_TAX_CAPTURE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    # Deliberately narrower than ACCOUNT_TAX_CAPTURE and deliberately excludes
    # ROLE_ADMIN: only Finance/Accounts may set a final PAN/GST verification
    # state today. This is the pre-existing ACCOUNT_TAX_VERIFICATION_ROLES
    # tuple; preserving it here is the concrete proof that PF-1A-E1 does not
    # grant ADMIN an implicit universal permission.
    ACCOUNT_TAX_VERIFY: (ROLE_FINANCE_USER,),
    ACCOUNT_DOCUMENT_CAPTURE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_FINANCE_USER),
    COMMERCIAL_OFFER_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    COMMERCIAL_OFFER_UPDATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_OPERATIONS_USER,
    ),
    COMMERCIAL_OFFER_LINE_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_TC_CLAUSE_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_REVISION_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    LEAD_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    LEAD_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    LEAD_UPDATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    LEAD_QUALIFICATION_DECIDE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    LEAD_CONVERT: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    LEAD_ACTIVITY_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    OPPORTUNITY_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    OPPORTUNITY_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    OPPORTUNITY_UPDATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    OPPORTUNITY_ACCOUNT_REPAIR: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    TC_CLAUSE_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    WORK_ORDER_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    WORK_ORDER_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    # Deliberately excludes ROLE_ADMIN's usual Sales/Finance/Operations peers:
    # only ADMIN and MANAGEMENT_READ_ONLY may read the recent business-event
    # feed today.
    EVENTS_READ: (ROLE_ADMIN, ROLE_MANAGEMENT_READ_ONLY),
    # Deliberately the narrowest permission in the catalogue: only ADMIN may
    # read the role catalogue today.
    IDENTITY_ROLE_CATALOG_READ: (ROLE_ADMIN,),
}

# Permissions introduced after PF-1A-E1. This is the live, growing half of the
# catalogue; the matrix above is the frozen half and must never gain an entry.
#
# Why the split exists: ROLE_PERMISSION_COMPATIBILITY_MATRIX is PF-1A-E1's
# evidence that migrating every route guard to an explicit permission preserved
# the pre-existing access matrix exactly. That evidence is only worth anything
# because the fixture it is compared against was derived independently from the
# pre-E1 code. Adding a post-E1 permission to it would make the comparison
# vacuous from that point on - the proof would be comparing a moved goalpost to
# itself. So new permissions land here instead, and every consumer that cares
# about what the system actually enforces reads EFFECTIVE_ROLE_PERMISSION_MATRIX.
POST_BASELINE_ROLE_PERMISSION_MATRIX: dict[str, tuple[str, ...]] = {
    # Slice 9D - Interaction Foundation.
    INTERACTION_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    # Deliberately narrower than INTERACTION_READ, and deliberately excludes
    # ROLE_FINANCE_USER: Finance can see that a conversation happened, its
    # channel, subject and outcome, but not the customer's message body or the
    # participants' addresses. Restricted personal/statutory data is
    # need-to-know under DATA_CLASSIFICATION_AND_HANDLING.md, and Finance's
    # work - receivables, activation, invoicing - is served by the metadata.
    # If Finance is later found to need message bodies, grant this explicitly
    # rather than widening by default.
    INTERACTION_CONTENT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    INTERACTION_CREATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    INTERACTION_UPDATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    # Deleting a recorded conversation removes evidence, so it is narrower than
    # recording or correcting one.
    INTERACTION_DELETE: (ROLE_ADMIN, ROLE_SALES_MANAGER),
    # Slice 9C - Document Storage Foundation. All six roles, reproducing the pre-9C
    # authenticated-only reach of these routes exactly - see the DOCUMENT_READ contract-level
    # comment above for why the real narrowing is the record-scoped check in service.py, not
    # this grant.
    DOCUMENT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    DOCUMENT_UPLOAD: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    DOCUMENT_CONTENT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    # Slice 9E - Quotation Generation. Generating a quote matches the existing Commercial Offer
    # create/manage role set; approving one for issue is deliberately narrower - see the
    # contract-level comment above for owner decision 4.
    COMMERCIAL_OFFER_QUOTE_GENERATE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER),
    COMMERCIAL_OFFER_QUOTE_APPROVE: (ROLE_ADMIN, ROLE_SALES_MANAGER),
    # Slice 7C - Work Order Line Operational Detail. Same four roles as WORK_ORDER_CREATE, held as
    # its own code - see the contract-level comment above.
    WORK_ORDER_LINE_DETAIL_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    WORK_ORDER_LINE_BILLING_TERMS_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    # Slice 7D Part 3 - the contract period and its extensions. The same four roles today (owner
    # decision 18); kept as two permissions so extensions can later be narrowed on their own.
    WORK_ORDER_CONTRACT_PERIOD_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    WORK_ORDER_CONTRACT_EXTENSION_WRITE: (ROLE_ADMIN, ROLE_SALES_USER, ROLE_SALES_MANAGER, ROLE_OPERATIONS_USER),
    # WRR-001 - Resource Requirements and the Equipment Reference. Reading follows WORK_ORDER_READ, all six
    # roles; writing is Operations and Admin only (owner, Q6) - see the contract-level comment above.
    RESOURCE_REQUIREMENT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    RESOURCE_REQUIREMENT_WRITE: (ROLE_ADMIN, ROLE_OPERATIONS_USER),
    EQUIPMENT_REFERENCE_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    # ERT-1 - Admin only until a Fleet Admin role exists (owner, comment 1); see the contract-level comment.
    EQUIPMENT_REFERENCE_MANAGE: (ROLE_ADMIN,),
    # Admin only for now (owner, 25 September 2026); Operations, and Finance for audits, may be granted it later.
    EQUIPMENT_IDENTITY_READ: (ROLE_ADMIN,),
    # ELG-1 - Admin only (owner, Q7); a compliance officer may be granted it later.
    ELIGIBILITY_RULE_MANAGE: (ROLE_ADMIN,),
    # 8A core - reading follows WORK_ORDER_READ; allocating is Operations and Admin, as requirements are.
    RESOURCE_ASSIGNMENT_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    RESOURCE_ASSIGNMENT_WRITE: (ROLE_ADMIN, ROLE_OPERATIONS_USER),
    # HOL-1 - everyone reads PBL's holiday calendar; Admin keeps it until a position is mapped under ORA-001.
    HOLIDAY_CALENDAR_READ: (
        ROLE_ADMIN,
        ROLE_SALES_USER,
        ROLE_SALES_MANAGER,
        ROLE_FINANCE_USER,
        ROLE_OPERATIONS_USER,
        ROLE_MANAGEMENT_READ_ONLY,
    ),
    HOLIDAY_CALENDAR_MANAGE: (ROLE_ADMIN,),
}

def assert_permission_matrices_are_disjoint(
    baseline: dict[str, tuple[str, ...]],
    post_baseline: dict[str, tuple[str, ...]],
) -> None:
    """Raise if any permission code appears in both matrices.

    A code must live in exactly one. Checked before the union is built, because dict merging
    would silently let a post-baseline entry shadow a baseline one - which is precisely the
    corruption the split exists to prevent, and it would do so while every count still looked
    plausible.

    Exposed as a function rather than written inline so it can be driven with synthetic
    overlapping input by a test. A guard that has never been shown to fail is an assertion of
    intent, not a control.
    """
    overlapping = set(baseline) & set(post_baseline)
    if overlapping:
        raise RuntimeError(
            "permission code(s) present in BOTH the frozen PF-1A-E1 baseline matrix and the "
            f"post-baseline matrix: {sorted(overlapping)}. A code belongs to exactly one. "
            "If you are adding a permission, add it to POST_BASELINE_ROLE_PERMISSION_MATRIX only; "
            "the baseline matrix is frozen evidence and must not gain entries."
        )


assert_permission_matrices_are_disjoint(
    ROLE_PERMISSION_COMPATIBILITY_MATRIX, POST_BASELINE_ROLE_PERMISSION_MATRIX
)

# What the system actually enforces: the disjoint union of the frozen baseline
# and everything added since. Consumers checking live behaviour must read this,
# never the baseline matrix alone.
EFFECTIVE_ROLE_PERMISSION_MATRIX: dict[str, tuple[str, ...]] = {
    **ROLE_PERMISSION_COMPATIBILITY_MATRIX,
    **POST_BASELINE_ROLE_PERMISSION_MATRIX,
}

ALL_PERMISSION_CODES: tuple[str, ...] = tuple(EFFECTIVE_ROLE_PERMISSION_MATRIX.keys())

# Defensive invariant: every permission code must have a description and every
# described code must be a real permission. This does not itself constitute a
# test, but it fails loudly (ImportError-adjacent, at module import time) if
# the two structures above ever drift apart during future edits.
if set(PERMISSION_DESCRIPTIONS.keys()) != set(ALL_PERMISSION_CODES):
    _missing_description = set(ALL_PERMISSION_CODES) - set(PERMISSION_DESCRIPTIONS)
    _orphan_description = set(PERMISSION_DESCRIPTIONS) - set(ALL_PERMISSION_CODES)
    raise RuntimeError(
        "PERMISSION_DESCRIPTIONS and EFFECTIVE_ROLE_PERMISSION_MATRIX have drifted apart in "
        f"app.modules.authorization.contract. Undescribed: {sorted(_missing_description)}; "
        f"described but not a permission: {sorted(_orphan_description)}."
    )

for _permission_code, _role_codes in EFFECTIVE_ROLE_PERMISSION_MATRIX.items():
    _unknown_roles = set(_role_codes) - set(KNOWN_ROLE_CODES)
    if _unknown_roles:
        raise RuntimeError(
            f"Permission {_permission_code!r} maps to unknown role code(s) {_unknown_roles!r}."
        )
