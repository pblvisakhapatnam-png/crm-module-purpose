from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    WORK_ORDER_CONTRACT_EXTENSION_WRITE as WORK_ORDER_CONTRACT_EXTENSION_WRITE_PERMISSION,
    WORK_ORDER_CONTRACT_PERIOD_WRITE as WORK_ORDER_CONTRACT_PERIOD_WRITE_PERMISSION,
    WORK_ORDER_CREATE as WORK_ORDER_CREATE_PERMISSION,
    WORK_ORDER_LINE_BILLING_TERMS_WRITE as WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION,
    WORK_ORDER_LINE_DETAIL_WRITE as WORK_ORDER_LINE_DETAIL_WRITE_PERMISSION,
    WORK_ORDER_READ as WORK_ORDER_READ_PERMISSION,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.identity.schemas import AuthUser
from app.modules.work_orders.schemas import (
    WorkOrderContractExtensionCreate,
    WorkOrderContractPeriodActionResponse,
    WorkOrderContractPeriodResponse,
    WorkOrderContractPeriodUpdate,
    WorkOrderLineBillingTermsCopyRequest,
    WorkOrderLineBillingTermsCopyResponse,
    WorkOrderAmendmentActionResponse,
    WorkOrderAmendmentCreate,
    WorkOrderAmendmentDecision,
    WorkOrderAmendmentLineActionResponse,
    WorkOrderAmendmentLineCreate,
    WorkOrderAmendmentLineResponse,
    WorkOrderAmendmentLineUpdate,
    WorkOrderAmendmentReadinessResponse,
    WorkOrderAmendmentResponse,
    WorkOrderAmendmentUpdate,
    WorkOrderCreateFromCommercialOffer,
    WorkOrderCreatedResponse,
    WorkOrderLineBillingTermsActionResponse,
    WorkOrderLineBillingTermsPeriodCreate,
    WorkOrderLineBillingTermsPeriodUpdate,
    WorkOrderLineBillingTermsResponse,
    WorkOrderLineDetailActionResponse,
    WorkOrderLineDetailResponse,
    WorkOrderLineDetailUpdate,
    WorkOrderLineResponse,
    WorkOrderReadResponse,
    WorkOrderRelatedOfferSummary,
    WorkOrderHolidayListActionResponse,
    WorkOrderHolidayListResponse,
    WorkOrderHolidayListUpdate,
    WorkOrderResultingHolidaysResponse,
)
from app.modules.work_orders.service import (
    WorkOrderContractExtensionNotFoundError,
    WorkOrderContractPeriodConflictError,
    copy_work_order_line_billing_terms,
    create_work_order_contract_extension,
    get_work_order_contract_period,
    remove_work_order_contract_extension,
    save_work_order_contract_period,
    WorkOrderAmendmentLineNotFoundError,
    WorkOrderAmendmentNotFoundError,
    WorkOrderLineBillingTermNotFoundError,
    WorkOrderLineBillingTermsConflictError,
    WorkOrderLineDetailConflictError,
    WorkOrderLineNotFoundError,
    WorkOrderCommercialOfferNotFoundError,
    WorkOrderHandoffConflictError,
    WorkOrderNotFoundError,
    WorkOrderValidationError,
    add_work_order_line_billing_terms_period,
    create_work_order_amendment,
    create_work_order_amendment_line,
    create_work_order_from_commercial_offer,
    decide_work_order_amendment,
    delete_work_order_amendment_line,
    get_work_order,
    get_work_order_amendment,
    get_work_order_amendment_readiness,
    list_work_order_amendment_lines,
    list_work_order_amendments,
    list_work_order_billing_terms,
    list_work_order_line_details,
    list_work_order_lines,
    list_work_order_related_offers,
    list_work_orders,
    remove_work_order_line_billing_terms_period,
    save_work_order_line_detail,
    update_work_order_amendment,
    update_work_order_amendment_line,
    update_work_order_line_billing_terms_period,
    WorkOrderHolidayListConflictError,
    get_work_order_holidays,
    get_work_order_resulting_holidays,
    save_work_order_holidays,
)

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


def _user_public_id(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


@router.post("/from-commercial-offer", response_model=WorkOrderCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_work_order_from_commercial_offer_endpoint(
    payload: WorkOrderCreateFromCommercialOffer,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderCreatedResponse:
    try:
        return create_work_order_from_commercial_offer(
            db,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except WorkOrderCommercialOfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderHandoffConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", response_model=list[WorkOrderReadResponse])
def list_work_orders_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    commercial_offer_public_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderReadResponse]:
    return list_work_orders(
        db,
        limit=limit,
        offset=offset,
        commercial_offer_public_id=commercial_offer_public_id,
    )


@router.get("/{public_id}", response_model=WorkOrderReadResponse)
def get_work_order_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderReadResponse:
    try:
        return get_work_order(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/lines", response_model=list[WorkOrderLineResponse])
def list_work_order_lines_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderLineResponse]:
    try:
        return list_work_order_lines(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{public_id}/related-offers", response_model=list[WorkOrderRelatedOfferSummary])
def list_work_order_related_offers_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderRelatedOfferSummary]:
    try:
        return list_work_order_related_offers(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# --- Slice 6O.2 Work Order Amendment intake foundation -----------------------------------
# Intake/review records only. See work_orders/service.py module docstring note - nothing
# under these routes is ever applied to the Work Order or its lines.


@router.get("/{public_id}/amendments", response_model=list[WorkOrderAmendmentResponse])
def list_work_order_amendments_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderAmendmentResponse]:
    try:
        return list_work_order_amendments(db, work_order_public_id=public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/amendments",
    response_model=WorkOrderAmendmentActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order_amendment_endpoint(
    public_id: UUID,
    payload: WorkOrderAmendmentCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderAmendmentActionResponse:
    try:
        return create_work_order_amendment(
            db,
            work_order_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{public_id}/amendments/{amendment_public_id}", response_model=WorkOrderAmendmentResponse)
def get_work_order_amendment_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderAmendmentResponse:
    try:
        return get_work_order_amendment(db, work_order_public_id=public_id, amendment_public_id=amendment_public_id)
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{public_id}/amendments/{amendment_public_id}", response_model=WorkOrderAmendmentActionResponse)
def update_work_order_amendment_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderAmendmentActionResponse:
    try:
        return update_work_order_amendment(
            db,
            work_order_public_id=public_id,
            amendment_public_id=amendment_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post(
    "/{public_id}/amendments/{amendment_public_id}/decision",
    response_model=WorkOrderAmendmentActionResponse,
)
def decide_work_order_amendment_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentDecision,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderAmendmentActionResponse:
    try:
        return decide_work_order_amendment(
            db,
            work_order_public_id=public_id,
            amendment_public_id=amendment_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get(
    "/{public_id}/amendments/{amendment_public_id}/readiness",
    response_model=WorkOrderAmendmentReadinessResponse,
)
def get_work_order_amendment_readiness_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderAmendmentReadinessResponse:
    try:
        return get_work_order_amendment_readiness(
            db, work_order_public_id=public_id, amendment_public_id=amendment_public_id
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/{public_id}/amendments/{amendment_public_id}/lines",
    response_model=list[WorkOrderAmendmentLineResponse],
)
def list_work_order_amendment_lines_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderAmendmentLineResponse]:
    try:
        return list_work_order_amendment_lines(
            db, work_order_public_id=public_id, amendment_public_id=amendment_public_id
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/amendments/{amendment_public_id}/lines",
    response_model=WorkOrderAmendmentLineActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order_amendment_line_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    payload: WorkOrderAmendmentLineCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderAmendmentLineActionResponse:
    try:
        return create_work_order_amendment_line(
            db,
            work_order_public_id=public_id,
            amendment_public_id=amendment_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.put(
    "/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}",
    response_model=WorkOrderAmendmentLineActionResponse,
)
def update_work_order_amendment_line_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderAmendmentLineUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> WorkOrderAmendmentLineActionResponse:
    try:
        return update_work_order_amendment_line(
            db,
            work_order_public_id=public_id,
            amendment_public_id=amendment_public_id,
            line_public_id=line_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError, WorkOrderAmendmentLineNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete(
    "/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}",
    status_code=status.HTTP_200_OK,
)
def delete_work_order_amendment_line_endpoint(
    public_id: UUID,
    amendment_public_id: UUID,
    line_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CREATE_PERMISSION)),
) -> dict[str, object]:
    try:
        event = delete_work_order_amendment_line(
            db,
            work_order_public_id=public_id,
            amendment_public_id=amendment_public_id,
            line_public_id=line_public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderAmendmentNotFoundError, WorkOrderAmendmentLineNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"deleted": True, "event": event}


# --- Slice 7C Work Order line operational detail ----------------------------------------------
# Detail recorded after handoff. GET /{public_id}/lines above is deliberately unchanged: its model
# is the one the frozen handoff returns.


@router.get("/{public_id}/line-details", response_model=list[WorkOrderLineDetailResponse])
def list_work_order_line_details_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderLineDetailResponse]:
    try:
        return list_work_order_line_details(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{public_id}/lines/{line_public_id}/detail", response_model=WorkOrderLineDetailActionResponse)
def save_work_order_line_detail_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineDetailUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_DETAIL_WRITE_PERMISSION)),
) -> WorkOrderLineDetailActionResponse:
    try:
        return save_work_order_line_detail(
            db,
            work_order_public_id=public_id,
            line_public_id=line_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except (WorkOrderNotFoundError, WorkOrderLineNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkOrderLineDetailConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkOrderValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


# --- Slice 7D Work Order line billing terms (Part 1) -----------------------------------------------
# One row per period per line, recorded after handoff. GET /{public_id}/lines is still unchanged.

_BILLING_TERMS_ERRORS = (
    WorkOrderNotFoundError,
    WorkOrderLineNotFoundError,
    WorkOrderLineBillingTermNotFoundError,
    WorkOrderLineBillingTermsConflictError,
    WorkOrderValidationError,
)


def _billing_terms_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (WorkOrderNotFoundError, WorkOrderLineNotFoundError, WorkOrderLineBillingTermNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, WorkOrderLineBillingTermsConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{public_id}/billing-terms", response_model=list[WorkOrderLineBillingTermsResponse])
def list_work_order_billing_terms_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> list[WorkOrderLineBillingTermsResponse]:
    try:
        return list_work_order_billing_terms(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{public_id}/lines/{line_public_id}/billing-terms",
    response_model=WorkOrderLineBillingTermsActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_work_order_line_billing_terms_period_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineBillingTermsPeriodCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION)),
) -> WorkOrderLineBillingTermsActionResponse:
    try:
        return add_work_order_line_billing_terms_period(
            db,
            work_order_public_id=public_id,
            line_public_id=line_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _BILLING_TERMS_ERRORS as exc:
        raise _billing_terms_http_error(exc) from exc


@router.put(
    "/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}",
    response_model=WorkOrderLineBillingTermsActionResponse,
)
def update_work_order_line_billing_terms_period_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    term_public_id: UUID,
    payload: WorkOrderLineBillingTermsPeriodUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION)),
) -> WorkOrderLineBillingTermsActionResponse:
    try:
        return update_work_order_line_billing_terms_period(
            db,
            work_order_public_id=public_id,
            line_public_id=line_public_id,
            term_public_id=term_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _BILLING_TERMS_ERRORS as exc:
        raise _billing_terms_http_error(exc) from exc


@router.delete(
    "/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}",
    response_model=WorkOrderLineBillingTermsActionResponse,
)
def remove_work_order_line_billing_terms_period_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    term_public_id: UUID,
    expected_term_revision: int = Query(ge=1),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION)),
) -> WorkOrderLineBillingTermsActionResponse:
    try:
        return remove_work_order_line_billing_terms_period(
            db,
            work_order_public_id=public_id,
            line_public_id=line_public_id,
            term_public_id=term_public_id,
            expected_term_revision=expected_term_revision,
            current_user_public_id=_user_public_id(current_user),
        )
    except _BILLING_TERMS_ERRORS as exc:
        raise _billing_terms_http_error(exc) from exc


# --- Slice 7D Part 3: the contract period, extensions and copying terms between lines --------------
# The Work Order's contract start and end dates and the extensions that move them. GET returns the
# period with its extensions inline, as a line's billing terms return their periods inline: they are
# the history of one record, not a separate list to fetch.

_CONTRACT_PERIOD_ERRORS = (
    WorkOrderNotFoundError,
    WorkOrderLineNotFoundError,
    WorkOrderContractExtensionNotFoundError,
    WorkOrderContractPeriodConflictError,
    WorkOrderLineBillingTermsConflictError,
    WorkOrderValidationError,
)


def _contract_period_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (WorkOrderNotFoundError, WorkOrderLineNotFoundError, WorkOrderContractExtensionNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, (WorkOrderContractPeriodConflictError, WorkOrderLineBillingTermsConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{public_id}/contract-period", response_model=WorkOrderContractPeriodResponse)
def get_work_order_contract_period_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderContractPeriodResponse:
    try:
        return get_work_order_contract_period(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{public_id}/contract-period", response_model=WorkOrderContractPeriodActionResponse)
def save_work_order_contract_period_endpoint(
    public_id: UUID,
    payload: WorkOrderContractPeriodUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CONTRACT_PERIOD_WRITE_PERMISSION)),
) -> WorkOrderContractPeriodActionResponse:
    try:
        return save_work_order_contract_period(
            db,
            work_order_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _CONTRACT_PERIOD_ERRORS as exc:
        raise _contract_period_http_error(exc) from exc


@router.post(
    "/{public_id}/contract-extensions",
    response_model=WorkOrderContractPeriodActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order_contract_extension_endpoint(
    public_id: UUID,
    payload: WorkOrderContractExtensionCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CONTRACT_EXTENSION_WRITE_PERMISSION)),
) -> WorkOrderContractPeriodActionResponse:
    try:
        return create_work_order_contract_extension(
            db,
            work_order_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _CONTRACT_PERIOD_ERRORS as exc:
        raise _contract_period_http_error(exc) from exc


@router.delete(
    "/{public_id}/contract-extensions/{extension_public_id}",
    response_model=WorkOrderContractPeriodActionResponse,
)
def remove_work_order_contract_extension_endpoint(
    public_id: UUID,
    extension_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_CONTRACT_EXTENSION_WRITE_PERMISSION)),
) -> WorkOrderContractPeriodActionResponse:
    """Remove the most recent extension (owner, 22 September 2026). The same permission as recording
    one: who may extend a contract is who may withdraw an extension recorded in error."""
    try:
        return remove_work_order_contract_extension(
            db,
            work_order_public_id=public_id,
            extension_public_id=extension_public_id,
            current_user_public_id=_user_public_id(current_user),
        )
    except _CONTRACT_PERIOD_ERRORS as exc:
        raise _contract_period_http_error(exc) from exc


@router.post(
    "/{public_id}/lines/{line_public_id}/billing-terms/apply-to-lines",
    response_model=WorkOrderLineBillingTermsCopyResponse,
)
def copy_work_order_line_billing_terms_endpoint(
    public_id: UUID,
    line_public_id: UUID,
    payload: WorkOrderLineBillingTermsCopyRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION)),
) -> WorkOrderLineBillingTermsCopyResponse:
    """Copy the terms of the line in the path onto the chosen other lines (owner decision 20).

    It writes billing terms, so it asks for the permission that already governs writing them rather
    than one of its own: who may change a line's rates should be one answer, not two.
    """
    try:
        return copy_work_order_line_billing_terms(
            db,
            work_order_public_id=public_id,
            line_public_id=line_public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _CONTRACT_PERIOD_ERRORS as exc:
        raise _contract_period_http_error(exc) from exc


# --- Slice 7D Part 4: the holidays a Work Order names; since HOL-1 its changes to PBL's calendar --------
# One list on the Work Order for every line (owner decision 27), with the answer that tells "follows PBL's
# calendar unchanged" from "not entered yet" (decision 29). Written under the billing-terms permission: which
# days are holidays decides which days take a line's off-day rate, so who may change a rate decides them too.

_HOLIDAY_LIST_ERRORS = (
    WorkOrderNotFoundError,
    WorkOrderHolidayListConflictError,
    WorkOrderValidationError,
)


def _holiday_list_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WorkOrderNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, WorkOrderHolidayListConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{public_id}/holidays", response_model=WorkOrderHolidayListResponse)
def get_work_order_holidays_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderHolidayListResponse:
    try:
        return get_work_order_holidays(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{public_id}/holidays", response_model=WorkOrderHolidayListActionResponse)
def save_work_order_holidays_endpoint(
    public_id: UUID,
    payload: WorkOrderHolidayListUpdate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE_PERMISSION)),
) -> WorkOrderHolidayListActionResponse:
    try:
        return save_work_order_holidays(
            db,
            work_order_public_id=public_id,
            payload=payload,
            current_user_public_id=_user_public_id(current_user),
        )
    except _HOLIDAY_LIST_ERRORS as exc:
        raise _holiday_list_http_error(exc) from exc


@router.get("/{public_id}/holidays/resulting", response_model=WorkOrderResultingHolidaysResponse)
def get_work_order_resulting_holidays_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_permission(WORK_ORDER_READ_PERMISSION)),
) -> WorkOrderResultingHolidaysResponse:
    """HOL-1: the holidays that apply - PBL's calendar as the Work Order changes it, for each state's lines, over the
    contract. A read: it never writes."""
    try:
        return get_work_order_resulting_holidays(db, public_id)
    except WorkOrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
