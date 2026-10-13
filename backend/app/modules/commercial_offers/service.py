"""The Commercial Offers service.

The code lives in services/, one module per concern - offers, related_offers, pricing_evidence, lines,
tc_clauses, submission_readiness, submission_evidence, credit_reviews, mark_submitted, revisions,
customer_responses, lifecycle_guidance and quote_documents - with what several of them share in common.
This module re-exports every public name it defined before it was split (CS-11), so code written against
it keeps working, including the names nothing in the repository imports today. Import from here, not from
services/.

A test that monkeypatches a name a service function looks up must patch it on the module that function
is defined in; patching it here would change nothing the function sees.
"""

from __future__ import annotations

from app.modules.commercial_offers.services.common import (
    COMMERCIAL_OFFER_ACCOUNT_TRACEABILITY_REQUIRED_STATUSES,
    COMMERCIAL_OFFER_TC_READINESS_DEFERRAL_NOTES,
    COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES,
    CommercialOfferConflictError,
    CommercialOfferLineNotFoundError,
    CommercialOfferNotFoundError,
    CommercialOfferOpportunityNotFoundError,
    CommercialOfferPricingEvidenceNotFoundError,
    CommercialOfferQuoteDocumentNotFoundError,
    CommercialOfferRevisionNotFoundError,
    CommercialOfferTcClauseNotFoundError,
    CommercialOfferValidationError,
    get_commercial_offer,
    get_commercial_offer_tc_clause_readiness,
    normalize_tc_recommendation_basis,
)
from app.modules.commercial_offers.services.offers import (
    create_commercial_offer,
    list_commercial_offers,
    update_commercial_offer,
)
from app.modules.commercial_offers.services.related_offers import (
    create_related_commercial_offer,
    list_related_commercial_offers,
)
from app.modules.commercial_offers.services.pricing_evidence import (
    create_commercial_offer_pricing_evidence,
    list_commercial_offer_pricing_evidence,
    select_commercial_offer_basis_rate,
)
from app.modules.commercial_offers.services.lines import (
    create_commercial_offer_line,
    list_commercial_offer_lines,
    update_commercial_offer_line,
)
from app.modules.commercial_offers.services.tc_clauses import (
    attach_commercial_offer_tc_clauses,
    attach_recommended_commercial_offer_tc_clauses,
    list_commercial_offer_tc_clauses,
    remove_commercial_offer_tc_clause,
)
from app.modules.commercial_offers.services.submission_readiness import (
    COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS,
    get_commercial_offer_submission_readiness,
)
from app.modules.commercial_offers.services.submission_evidence import (
    create_commercial_offer_submission_evidence,
    list_commercial_offer_submission_evidence,
)
from app.modules.commercial_offers.services.credit_reviews import (
    create_commercial_offer_credit_review,
    list_commercial_offer_credit_reviews,
)
from app.modules.commercial_offers.services.mark_submitted import (
    mark_commercial_offer_submitted,
)
from app.modules.commercial_offers.services.revisions import (
    cancel_commercial_offer_revision,
    create_commercial_offer_revision,
    list_commercial_offer_revisions,
    mark_commercial_offer_revision_resubmitted,
)
from app.modules.commercial_offers.services.versions import (
    abandon_commercial_offer_version,
    create_commercial_offer_version,
    list_commercial_offer_versions,
)
from app.modules.commercial_offers.services.customer_responses import (
    create_commercial_offer_customer_response,
    list_commercial_offer_customer_responses,
)
from app.modules.commercial_offers.services.lifecycle_guidance import (
    get_commercial_offer_lifecycle_guidance,
)
from app.modules.commercial_offers.services.quote_documents import (
    INDIA_DISPLAY_TIME_ZONE,
    QUOTE_DOCUMENT_ADDRESS_TYPE_LABELS,
    QUOTE_DOCUMENT_ALLOWED_ADDRESS_TYPES,
    QUOTE_SNAPSHOT_SCHEMA_VERSION,
    approve_commercial_offer_quote_document,
    build_quote_snapshot,
    build_quote_snapshot_at_one_instant,
    compute_source_fingerprint,
    generate_commercial_offer_quote_document,
    list_commercial_offer_quote_documents,
    quote_document_approval_blocked_reason,
)

__all__ = [
    "COMMERCIAL_OFFER_ACCOUNT_TRACEABILITY_REQUIRED_STATUSES",
    "COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS",
    "COMMERCIAL_OFFER_TC_READINESS_DEFERRAL_NOTES",
    "COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES",
    "CommercialOfferConflictError",
    "CommercialOfferLineNotFoundError",
    "CommercialOfferNotFoundError",
    "CommercialOfferOpportunityNotFoundError",
    "CommercialOfferPricingEvidenceNotFoundError",
    "CommercialOfferQuoteDocumentNotFoundError",
    "CommercialOfferRevisionNotFoundError",
    "CommercialOfferTcClauseNotFoundError",
    "CommercialOfferValidationError",
    "INDIA_DISPLAY_TIME_ZONE",
    "QUOTE_DOCUMENT_ADDRESS_TYPE_LABELS",
    "QUOTE_DOCUMENT_ALLOWED_ADDRESS_TYPES",
    "QUOTE_SNAPSHOT_SCHEMA_VERSION",
    "approve_commercial_offer_quote_document",
    "abandon_commercial_offer_version",
    "attach_commercial_offer_tc_clauses",
    "attach_recommended_commercial_offer_tc_clauses",
    "build_quote_snapshot",
    "build_quote_snapshot_at_one_instant",
    "cancel_commercial_offer_revision",
    "compute_source_fingerprint",
    "create_commercial_offer",
    "create_commercial_offer_credit_review",
    "create_commercial_offer_customer_response",
    "create_commercial_offer_line",
    "create_commercial_offer_pricing_evidence",
    "create_commercial_offer_revision",
    "create_commercial_offer_submission_evidence",
    "create_commercial_offer_version",
    "create_related_commercial_offer",
    "generate_commercial_offer_quote_document",
    "get_commercial_offer",
    "get_commercial_offer_lifecycle_guidance",
    "get_commercial_offer_submission_readiness",
    "get_commercial_offer_tc_clause_readiness",
    "list_commercial_offer_credit_reviews",
    "list_commercial_offer_customer_responses",
    "list_commercial_offer_lines",
    "list_commercial_offer_pricing_evidence",
    "list_commercial_offer_quote_documents",
    "list_commercial_offer_revisions",
    "list_commercial_offer_submission_evidence",
    "list_commercial_offer_tc_clauses",
    "list_commercial_offer_versions",
    "list_commercial_offers",
    "list_related_commercial_offers",
    "mark_commercial_offer_revision_resubmitted",
    "mark_commercial_offer_submitted",
    "normalize_tc_recommendation_basis",
    "quote_document_approval_blocked_reason",
    "remove_commercial_offer_tc_clause",
    "select_commercial_offer_basis_rate",
    "update_commercial_offer",
    "update_commercial_offer_line",
]
