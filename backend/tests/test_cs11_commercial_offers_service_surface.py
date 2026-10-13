"""CS-11 (TB-1 TB1-601): the Commercial Offers service module keeps every public name it had before it was split.

`app.modules.commercial_offers.service` became a re-export of the `services` package in CS-11, as the Work Orders
service did in TE-6. Code written against the original module - an import from it, or an attribute read on it -
must keep working, so it re-exports every public name the original defined, whether or not anything in the
repository imports that name today. The names the original only imported are not re-exported (TE-6's rule,
CODING_STANDARDS.md, "When a service outgrows one file").

Names a concern adds after the split are re-exported too, and pinned in a set of their own, so the set measured
at 5e19123 is never edited to fit a later package.
"""

from __future__ import annotations

import ast
import inspect

from app.modules.commercial_offers import service
from app.modules.commercial_offers.services import (
    common,
    credit_reviews,
    customer_responses,
    lifecycle_guidance,
    lines,
    mark_submitted,
    offers,
    pricing_evidence,
    quote_documents,
    related_offers,
    revisions,
    submission_evidence,
    submission_readiness,
    tc_clauses,
    versions,
)

CONCERN_MODULES = (
    common,
    offers,
    related_offers,
    pricing_evidence,
    lines,
    tc_clauses,
    submission_readiness,
    submission_evidence,
    credit_reviews,
    mark_submitted,
    revisions,
    customer_responses,
    lifecycle_guidance,
    quote_documents,
    versions,
)

# Every public top-level name defined in backend/app/modules/commercial_offers/service.py at 5e19123, the last
# commit before the split: its functions, its exception classes and its public constants.
PUBLIC_NAMES_BEFORE_THE_SPLIT = frozenset(
    {
        "COMMERCIAL_OFFER_ACCOUNT_TRACEABILITY_REQUIRED_STATUSES",
        "COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS",
        "COMMERCIAL_OFFER_TC_READINESS_DEFERRAL_NOTES",
        "COMMERCIAL_OFFER_TC_RECOMMENDATION_BASIS_ALIASES",
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
    }
)


# Every public name a concern module has added to the service since the split, pinned apart so the set measured
# at 5e19123 stays exactly what was measured. A later package adds its names here.
NAMES_ADDED_AFTER_THE_SPLIT: frozenset[str] = frozenset(
    {
        "CommercialOfferConflictError",  # CS-05a: a stale save, answered with 409
        "abandon_commercial_offer_version",
        "create_commercial_offer_version",
        "list_commercial_offer_versions",
    }
)


def _defined_at_top_level(module) -> set[str]:
    names: set[str] = set()
    for node in ast.parse(inspect.getsource(module)).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names |= {target.id for target in node.targets if isinstance(target, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def test_the_pinned_list_is_the_one_measured() -> None:
    assert len(PUBLIC_NAMES_BEFORE_THE_SPLIT) == 54


def test_the_names_added_since_are_new_names() -> None:
    """A name added after the split is genuinely new - not one the original module already had."""
    assert not (NAMES_ADDED_AFTER_THE_SPLIT & PUBLIC_NAMES_BEFORE_THE_SPLIT)


def test_every_public_name_of_the_original_module_is_still_on_it() -> None:
    missing = sorted(name for name in PUBLIC_NAMES_BEFORE_THE_SPLIT if not hasattr(service, name))
    assert missing == [], f"no longer available from the Commercial Offers service module: {missing}"


def test_every_name_added_since_is_on_it() -> None:
    missing = sorted(name for name in NAMES_ADDED_AFTER_THE_SPLIT if not hasattr(service, name))
    assert missing == [], f"not available from the Commercial Offers service module: {missing}"


def test_all_lists_exactly_those_names() -> None:
    assert len(service.__all__) == len(set(service.__all__)), "a name is listed twice in __all__"
    assert set(service.__all__) == PUBLIC_NAMES_BEFORE_THE_SPLIT | NAMES_ADDED_AFTER_THE_SPLIT


def test_each_name_is_the_object_its_concern_module_defines() -> None:
    """A re-export hands out the definition itself - never a copy, wrapper or second class - so an
    `except CommercialOfferValidationError` in a caller still catches what the service raises. Each name is
    defined in exactly one concern module."""
    defined = {module: _defined_at_top_level(module) for module in CONCERN_MODULES}
    for name in sorted(PUBLIC_NAMES_BEFORE_THE_SPLIT | NAMES_ADDED_AFTER_THE_SPLIT):
        homes = [module for module, names in defined.items() if name in names]
        assert len(homes) == 1, (name, [module.__name__ for module in homes])
        assert getattr(service, name) is getattr(homes[0], name), name
