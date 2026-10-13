from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.commercial_offers.schemas import (
    CommercialOfferCreditReviewCreate,
    CommercialOfferCreditReviewCreatedResponse,
    CommercialOfferCreditReviewResponse,
    CommercialOfferCustomerResponseCreate,
    CommercialOfferCustomerResponseCreatedResponse,
    CommercialOfferCustomerResponseResponse,
    CommercialOfferCreate,
    CommercialOfferLineCreate,
    CommercialOfferLineCreatedResponse,
    CommercialOfferLineResponse,
    CommercialOfferLineUpdate,
    CommercialOfferLineUpdatedResponse,
    CommercialOfferLifecycleGuidanceResponse,
    CommercialOfferMarkedSubmittedResponse,
    CommercialOfferPricingEvidenceBasisSelection,
    CommercialOfferPricingEvidenceCreate,
    CommercialOfferPricingEvidenceCreatedResponse,
    CommercialOfferPricingEvidenceResponse,
    CommercialOfferPricingEvidenceSelectedResponse,
    CommercialOfferRelatedOfferCreate,
    CommercialOfferRelatedOfferCreatedResponse,
    CommercialOfferRevisionActionResponse,
    CommercialOfferRevisionCreate,
    CommercialOfferRevisionMarkResubmitted,
    CommercialOfferRevisionResponse,
    CommercialOfferSubmissionEvidenceCreate,
    CommercialOfferSubmissionEvidenceCreatedResponse,
    CommercialOfferSubmissionEvidenceResponse,
    CommercialOfferTcClauseAttachRequest,
    CommercialOfferTcClauseAttachRecommendedRequest,
    CommercialOfferTcClauseAttachedResponse,
    CommercialOfferTcClauseAttachRecommendedResponse,
    CommercialOfferTcClauseRemovedResponse,
    CommercialOfferTcClauseReadinessResponse,
    CommercialOfferTcClauseResponse,
    CommercialOfferSubmissionReadinessResponse,
    CommercialOfferCreatedResponse,
    CommercialOfferResponse,
    CommercialOfferUpdate,
    CommercialOfferUpdatedResponse,
    CommercialOfferVersionActionResponse,
    CommercialOfferVersionCreate,
    CommercialOfferQuoteDocumentApproveRequest,
    CommercialOfferQuoteDocumentApprovedResponse,
    CommercialOfferQuoteDocumentGeneratedResponse,
    CommercialOfferQuoteDocumentResponse,
)
from app.modules.commercial_offers.service import (
    CommercialOfferConflictError,
    CommercialOfferLineNotFoundError,
    CommercialOfferNotFoundError,
    CommercialOfferOpportunityNotFoundError,
    CommercialOfferPricingEvidenceNotFoundError,
    CommercialOfferQuoteDocumentNotFoundError,
    CommercialOfferRevisionNotFoundError,
    CommercialOfferTcClauseNotFoundError,
    CommercialOfferValidationError,
    approve_commercial_offer_quote_document,
    abandon_commercial_offer_version,
    attach_commercial_offer_tc_clauses,
    attach_recommended_commercial_offer_tc_clauses,
    cancel_commercial_offer_revision,
    create_commercial_offer,
    create_commercial_offer_credit_review,
    create_commercial_offer_customer_response,
    create_commercial_offer_line,
    create_commercial_offer_pricing_evidence,
    create_commercial_offer_revision,
    create_commercial_offer_submission_evidence,
    create_commercial_offer_version,
    create_related_commercial_offer,
    generate_commercial_offer_quote_document,
    get_commercial_offer,
    get_commercial_offer_lifecycle_guidance,
    list_commercial_offer_lines,
    list_commercial_offer_quote_documents,
    list_related_commercial_offers,
    list_commercial_offer_credit_reviews,
    list_commercial_offer_customer_responses,
    list_commercial_offer_pricing_evidence,
    list_commercial_offer_revisions,
    get_commercial_offer_submission_readiness,
    get_commercial_offer_tc_clause_readiness,
    list_commercial_offer_submission_evidence,
    list_commercial_offer_tc_clauses,
    list_commercial_offer_versions,
    list_commercial_offers,
    mark_commercial_offer_submitted,
    mark_commercial_offer_revision_resubmitted,
    remove_commercial_offer_tc_clause,
    select_commercial_offer_basis_rate,
    update_commercial_offer,
    update_commercial_offer_line,
)
from app.modules.authorization.contract import (
    COMMERCIAL_OFFER_CREATE as COMMERCIAL_OFFER_CREATE_PERMISSION,
    COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE,
    COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE,
    COMMERCIAL_OFFER_LINE_WRITE,
    COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE,
    COMMERCIAL_OFFER_QUOTE_APPROVE,
    COMMERCIAL_OFFER_QUOTE_GENERATE,
    COMMERCIAL_OFFER_READ as COMMERCIAL_OFFER_READ_PERMISSION,
    COMMERCIAL_OFFER_REVISION_WRITE,
    COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE,
    COMMERCIAL_OFFER_TC_CLAUSE_WRITE,
    COMMERCIAL_OFFER_UPDATE as COMMERCIAL_OFFER_UPDATE_PERMISSION,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser

router = APIRouter(prefix="/api/commercial-offers", tags=["commercial-offers"])


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.post("", response_model=CommercialOfferCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_commercial_offer_endpoint(
    payload: CommercialOfferCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_CREATE_PERMISSION)),
) -> CommercialOfferCreatedResponse:
    try:
        return create_commercial_offer(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferOpportunityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", response_model=list[CommercialOfferResponse])
def list_commercial_offers_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    status_code: str | None = Query(default=None, max_length=50),
    offer_mode: str | None = Query(default=None, max_length=50),
    opportunity_public_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferResponse]:
    return list_commercial_offers(
        db,
        limit=limit,
        offset=offset,
        status_code=status_code,
        offer_mode=offer_mode,
        opportunity_public_id=opportunity_public_id,
    )


@router.get("/{public_id}", response_model=CommercialOfferResponse)
def get_commercial_offer_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> CommercialOfferResponse:
    try:
        return get_commercial_offer(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/related-offers", response_model=list[CommercialOfferResponse])
def list_related_commercial_offers_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferResponse]:
    try:
        return list_related_commercial_offers(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/related-offers",
    response_model=CommercialOfferRelatedOfferCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_related_commercial_offer_endpoint(
    public_id: UUID,
    payload: CommercialOfferRelatedOfferCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_CREATE_PERMISSION)),
) -> CommercialOfferRelatedOfferCreatedResponse:
    try:
        return create_related_commercial_offer(
            db,
            base_offer_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/quote-documents", response_model=list[CommercialOfferQuoteDocumentResponse])
def list_commercial_offer_quote_documents_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferQuoteDocumentResponse]:
    try:
        return list_commercial_offer_quote_documents(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/quote-documents",
    response_model=CommercialOfferQuoteDocumentGeneratedResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_commercial_offer_quote_document_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_QUOTE_GENERATE)),
) -> CommercialOfferQuoteDocumentGeneratedResponse:
    try:
        return generate_commercial_offer_quote_document(
            db,
            public_id=public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/quote-documents/{quote_document_public_id}/approve",
    response_model=CommercialOfferQuoteDocumentApprovedResponse,
)
def approve_commercial_offer_quote_document_endpoint(
    public_id: UUID,
    quote_document_public_id: UUID,
    payload: CommercialOfferQuoteDocumentApproveRequest | None = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_QUOTE_APPROVE)),
) -> CommercialOfferQuoteDocumentApprovedResponse:
    try:
        return approve_commercial_offer_quote_document(
            db,
            public_id=public_id,
            quote_document_public_id=quote_document_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferQuoteDocumentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/submission-readiness", response_model=CommercialOfferSubmissionReadinessResponse)
def get_commercial_offer_submission_readiness_endpoint(
    public_id: UUID,
    recommendation_basis: str | None = Query(default=None, max_length=50),
    business_line: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> CommercialOfferSubmissionReadinessResponse:
    try:
        return get_commercial_offer_submission_readiness(
            db,
            public_id=public_id,
            recommendation_basis=recommendation_basis or business_line,
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/lifecycle-guidance", response_model=CommercialOfferLifecycleGuidanceResponse)
def get_commercial_offer_lifecycle_guidance_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> CommercialOfferLifecycleGuidanceResponse:
    try:
        return get_commercial_offer_lifecycle_guidance(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/submission-evidence", response_model=list[CommercialOfferSubmissionEvidenceResponse])
def list_commercial_offer_submission_evidence_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferSubmissionEvidenceResponse]:
    try:
        return list_commercial_offer_submission_evidence(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/submission-evidence",
    response_model=CommercialOfferSubmissionEvidenceCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_submission_evidence_endpoint(
    public_id: UUID,
    payload: CommercialOfferSubmissionEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_SUBMISSION_EVIDENCE_WRITE)),
) -> CommercialOfferSubmissionEvidenceCreatedResponse:
    try:
        return create_commercial_offer_submission_evidence(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/credit-review", response_model=list[CommercialOfferCreditReviewResponse])
def list_commercial_offer_credit_reviews_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferCreditReviewResponse]:
    try:
        return list_commercial_offer_credit_reviews(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/credit-review",
    response_model=CommercialOfferCreditReviewCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_credit_review_endpoint(
    public_id: UUID,
    payload: CommercialOfferCreditReviewCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_CREDIT_REVIEW_WRITE)),
) -> CommercialOfferCreditReviewCreatedResponse:
    try:
        return create_commercial_offer_credit_review(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/customer-responses", response_model=list[CommercialOfferCustomerResponseResponse])
def list_commercial_offer_customer_responses_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferCustomerResponseResponse]:
    try:
        return list_commercial_offer_customer_responses(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/customer-responses",
    response_model=CommercialOfferCustomerResponseCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_customer_response_endpoint(
    public_id: UUID,
    payload: CommercialOfferCustomerResponseCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_CUSTOMER_RESPONSE_WRITE)),
) -> CommercialOfferCustomerResponseCreatedResponse:
    try:
        return create_commercial_offer_customer_response(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/revisions", response_model=list[CommercialOfferRevisionResponse])
def list_commercial_offer_revisions_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferRevisionResponse]:
    try:
        return list_commercial_offer_revisions(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/versions", response_model=list[CommercialOfferResponse])
def list_commercial_offer_versions_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferResponse]:
    try:
        return list_commercial_offer_versions(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/versions",
    response_model=CommercialOfferVersionActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_version_endpoint(
    public_id: UUID,
    payload: CommercialOfferVersionCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_UPDATE_PERMISSION)),
) -> CommercialOfferVersionActionResponse:
    try:
        return create_commercial_offer_version(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{public_id}/abandon-version", response_model=CommercialOfferVersionActionResponse)
def abandon_commercial_offer_version_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_UPDATE_PERMISSION)),
) -> CommercialOfferVersionActionResponse:
    try:
        return abandon_commercial_offer_version(
            db,
            public_id=public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/revisions",
    response_model=CommercialOfferRevisionActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_revision_endpoint(
    public_id: UUID,
    payload: CommercialOfferRevisionCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_REVISION_WRITE)),
) -> CommercialOfferRevisionActionResponse:
    try:
        return create_commercial_offer_revision(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/revisions/{revision_public_id}/mark-resubmitted",
    response_model=CommercialOfferRevisionActionResponse,
)
def mark_commercial_offer_revision_resubmitted_endpoint(
    public_id: UUID,
    revision_public_id: UUID,
    payload: CommercialOfferRevisionMarkResubmitted,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_REVISION_WRITE)),
) -> CommercialOfferRevisionActionResponse:
    try:
        return mark_commercial_offer_revision_resubmitted(
            db,
            public_id=public_id,
            revision_public_id=revision_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferRevisionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/revisions/{revision_public_id}/cancel",
    response_model=CommercialOfferRevisionActionResponse,
)
def cancel_commercial_offer_revision_endpoint(
    public_id: UUID,
    revision_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_REVISION_WRITE)),
) -> CommercialOfferRevisionActionResponse:
    try:
        return cancel_commercial_offer_revision(
            db,
            public_id=public_id,
            revision_public_id=revision_public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferRevisionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{public_id}/mark-submitted", response_model=CommercialOfferMarkedSubmittedResponse)
def mark_commercial_offer_submitted_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_UPDATE_PERMISSION)),
) -> CommercialOfferMarkedSubmittedResponse:
    try:
        return mark_commercial_offer_submitted(
            db,
            public_id=public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.put("/{public_id}", response_model=CommercialOfferUpdatedResponse)
def update_commercial_offer_endpoint(
    public_id: UUID,
    payload: CommercialOfferUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_UPDATE_PERMISSION)),
) -> CommercialOfferUpdatedResponse:
    try:
        return update_commercial_offer(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc





@router.get("/{public_id}/lines", response_model=list[CommercialOfferLineResponse])
def list_commercial_offer_lines_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferLineResponse]:
    try:
        return list_commercial_offer_lines(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/lines",
    response_model=CommercialOfferLineCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_line_endpoint(
    public_id: UUID,
    payload: CommercialOfferLineCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_LINE_WRITE)),
) -> CommercialOfferLineCreatedResponse:
    try:
        return create_commercial_offer_line(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.put("/{public_id}/lines/{line_public_id}", response_model=CommercialOfferLineUpdatedResponse)
def update_commercial_offer_line_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    payload: CommercialOfferLineUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_LINE_WRITE)),
) -> CommercialOfferLineUpdatedResponse:
    try:
        return update_commercial_offer_line(
            db,
            public_id=public_id,
            line_public_id=line_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferLineNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/tc-clauses", response_model=list[CommercialOfferTcClauseResponse])
def list_commercial_offer_tc_clauses_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferTcClauseResponse]:
    try:
        return list_commercial_offer_tc_clauses(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/tc-clause-readiness", response_model=CommercialOfferTcClauseReadinessResponse)
def get_commercial_offer_tc_clause_readiness_endpoint(
    public_id: UUID,
    recommendation_basis: str | None = Query(default=None, max_length=50),
    business_line: str | None = Query(default=None, max_length=50),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> CommercialOfferTcClauseReadinessResponse:
    try:
        return get_commercial_offer_tc_clause_readiness(
            db,
            public_id=public_id,
            recommendation_basis=recommendation_basis or business_line,
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/tc-clauses",
    response_model=CommercialOfferTcClauseAttachedResponse,
    status_code=status.HTTP_201_CREATED,
)
def attach_commercial_offer_tc_clauses_endpoint(
    public_id: UUID,
    payload: CommercialOfferTcClauseAttachRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_TC_CLAUSE_WRITE)),
) -> CommercialOfferTcClauseAttachedResponse:
    try:
        return attach_commercial_offer_tc_clauses(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferTcClauseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{public_id}/tc-clauses/attach-recommended", response_model=CommercialOfferTcClauseAttachRecommendedResponse)
def attach_recommended_commercial_offer_tc_clauses_endpoint(
    public_id: UUID,
    payload: CommercialOfferTcClauseAttachRecommendedRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_TC_CLAUSE_WRITE)),
) -> CommercialOfferTcClauseAttachRecommendedResponse:
    try:
        return attach_recommended_commercial_offer_tc_clauses(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferTcClauseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/{public_id}/tc-clauses/{attachment_public_id}", response_model=CommercialOfferTcClauseRemovedResponse)
def remove_commercial_offer_tc_clause_endpoint(
    public_id: UUID,
    attachment_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_TC_CLAUSE_WRITE)),
) -> CommercialOfferTcClauseRemovedResponse:
    try:
        return remove_commercial_offer_tc_clause(
            db,
            public_id=public_id,
            attachment_public_id=attachment_public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except (CommercialOfferNotFoundError, CommercialOfferTcClauseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        # TB-1 TB1-301 (b): a final offer's T&C clauses no longer change.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/pricing-evidence", response_model=list[CommercialOfferPricingEvidenceResponse])
def list_commercial_offer_pricing_evidence_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_READ_PERMISSION)),
) -> list[CommercialOfferPricingEvidenceResponse]:
    try:
        return list_commercial_offer_pricing_evidence(db, public_id)
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/pricing-evidence",
    response_model=CommercialOfferPricingEvidenceCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_offer_pricing_evidence_endpoint(
    public_id: UUID,
    payload: CommercialOfferPricingEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE)),
) -> CommercialOfferPricingEvidenceCreatedResponse:
    try:
        return create_commercial_offer_pricing_evidence(
            db,
            public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/pricing-evidence/{evidence_public_id}/select-basis",
    response_model=CommercialOfferPricingEvidenceSelectedResponse,
)
def select_commercial_offer_basis_rate_endpoint(
    public_id: UUID,
    evidence_public_id: UUID,
    payload: CommercialOfferPricingEvidenceBasisSelection,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE)),
) -> CommercialOfferPricingEvidenceSelectedResponse:
    try:
        return select_commercial_offer_basis_rate(
            db,
            public_id=public_id,
            evidence_public_id=evidence_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except CommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferPricingEvidenceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommercialOfferConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommercialOfferValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
