"""Eligibility API (ELG-1). docs/agent/contracts/eligibility-api-contract.md.

Reading - certificates, marks, the check, Certificates due and the rules - follows EQUIPMENT_REFERENCE_READ.
Recording and withdrawing certificates and "not applicable" marks needs EQUIPMENT_REFERENCE_MANAGE (Admin,
until a Fleet Admin role exists); adding and ending rules needs ELIGIBILITY_RULE_MANAGE (Admin, Q7).
Certificate numbers are shown only with EQUIPMENT_IDENTITY_READ, which the service resolves: route modules
never read roles. Copies go through POST /api/documents/upload, linked to `eligibility_certificate`.

Reminders (ELG-2): the Alerts that have reached the caller, their count, and marking them seen follow
EQUIPMENT_REFERENCE_READ - a "seen" mark is the person's own and changes no record; the service shows the allocation
reminders only with RESOURCE_ASSIGNMENT_READ. Reading the reminder settings follows EQUIPMENT_REFERENCE_READ; saving
a new version needs ELIGIBILITY_RULE_MANAGE (Q18).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.authorization.contract import (
    ELIGIBILITY_RULE_MANAGE,
    EQUIPMENT_REFERENCE_MANAGE,
    EQUIPMENT_REFERENCE_READ,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.eligibility import alerts, service
from app.modules.eligibility.contract import MAX_ALERT_LIMIT
from app.modules.eligibility.schemas import (
    AlertCountResponse,
    AlertSettingActionResponse,
    AlertSettingInput,
    AlertSettingsResponse,
    AlertsResponse,
    AssetCertificatesResponse,
    CertificateActionResponse,
    CertificateInput,
    CertificateKindResponse,
    CertificatesDueResponse,
    EligibilityCheckResponse,
    JurisdictionResponse,
    NotApplicableInput,
    RuleActionResponse,
    RuleEndInput,
    RuleInput,
    RuleResponse,
    SeenInput,
    SeenResponse,
    WithdrawInput,
)
from app.modules.identity.schemas import AuthUser

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])

_read = require_permission(EQUIPMENT_REFERENCE_READ)
_manage = require_permission(EQUIPMENT_REFERENCE_MANAGE)
_rule_manage = require_permission(ELIGIBILITY_RULE_MANAGE)

_ERRORS = (service.EligibilityNotFoundError, service.EligibilityConflictError, service.EligibilityValidationError)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.EligibilityNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, service.EligibilityConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _run(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except _ERRORS as exc:
        raise _http_error(exc) from exc


def _user(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


# --- Reference lists --------------------------------------------------------------------------------------


@router.get("/jurisdictions", response_model=list[JurisdictionResponse])
def list_jurisdictions_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> list[JurisdictionResponse]:
    return service.list_jurisdictions(db)


@router.get("/certificate-kinds", response_model=list[CertificateKindResponse])
def list_certificate_kinds_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> list[CertificateKindResponse]:
    return service.list_certificate_kinds(db)


# --- An asset's certificates and marks ------------------------------------------------------------------


@router.get("/assets/{asset_public_id}/certificates", response_model=AssetCertificatesResponse)
def get_asset_certificates_endpoint(
    asset_public_id: UUID, db: Session = Depends(get_db), user: AuthUser = Depends(_read)
) -> AssetCertificatesResponse:
    return _run(lambda: service.get_asset_certificates(db, str(asset_public_id), show_numbers=service.can_see_numbers(db, user)))


@router.post("/assets/{asset_public_id}/certificates", response_model=CertificateActionResponse, status_code=status.HTTP_201_CREATED)
def record_certificate_endpoint(
    asset_public_id: UUID, payload: CertificateInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> CertificateActionResponse:
    return _run(
        lambda: service.record_certificate(
            db,
            asset_public_id=str(asset_public_id),
            payload=payload,
            user_public_id=_user(user),
            show_numbers=service.can_see_numbers(db, user),
        )
    )


@router.post("/certificates/{certificate_public_id}/withdraw", response_model=CertificateActionResponse)
def withdraw_certificate_endpoint(
    certificate_public_id: UUID, payload: WithdrawInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> CertificateActionResponse:
    return _run(
        lambda: service.withdraw_certificate(
            db,
            certificate_public_id=str(certificate_public_id),
            payload=payload,
            user_public_id=_user(user),
            show_numbers=service.can_see_numbers(db, user),
        )
    )


@router.post("/assets/{asset_public_id}/not-applicable", response_model=CertificateActionResponse, status_code=status.HTTP_201_CREATED)
def record_not_applicable_endpoint(
    asset_public_id: UUID, payload: NotApplicableInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> CertificateActionResponse:
    return _run(
        lambda: service.record_not_applicable(
            db,
            asset_public_id=str(asset_public_id),
            payload=payload,
            user_public_id=_user(user),
            show_numbers=service.can_see_numbers(db, user),
        )
    )


@router.post("/not-applicable/{mark_public_id}/withdraw", response_model=CertificateActionResponse)
def withdraw_not_applicable_endpoint(
    mark_public_id: UUID, payload: WithdrawInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> CertificateActionResponse:
    return _run(
        lambda: service.withdraw_not_applicable(
            db,
            mark_public_id=str(mark_public_id),
            payload=payload,
            user_public_id=_user(user),
            show_numbers=service.can_see_numbers(db, user),
        )
    )


# --- The check (section 6): nothing is kept ------------------------------------------------------------


@router.get("/assets/{asset_public_id}/check", response_model=EligibilityCheckResponse)
def check_asset_endpoint(
    asset_public_id: UUID,
    state_code: str = Query(min_length=1, max_length=10),
    period_from: date = Query(),
    period_to: date | None = Query(default=None),
    central_government_site: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(_read),
) -> EligibilityCheckResponse:
    return _run(
        lambda: service.evaluate_asset(
            db,
            asset_public_id=str(asset_public_id),
            state_code=state_code,
            central_government_site=central_government_site,
            period_from=period_from,
            period_to=period_to,
        )
    )


# --- Certificates due (section 7) --------------------------------------------------------------------------


@router.get("/certificates-due", response_model=CertificatesDueResponse)
def certificates_due_endpoint(
    band: str | None = Query(default=None, max_length=20),
    class_code: str | None = Query(default=None, max_length=50),
    kind_code: str | None = Query(default=None, max_length=30),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=service.MAX_DUE_LIMIT),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(_read),
) -> CertificatesDueResponse:
    return _run(
        lambda: service.list_certificates_due(
            db, band_code=band, class_code=class_code, kind_code=kind_code, search=search, limit=limit, offset=offset
        )
    )


# --- Rules (Q7) ------------------------------------------------------------------------------------------------


@router.get("/rules", response_model=list[RuleResponse])
def list_rules_endpoint(
    jurisdiction_code: str | None = Query(default=None, max_length=10),
    kind_code: str | None = Query(default=None, max_length=30),
    class_code: str | None = Query(default=None, max_length=50),
    in_effect_on: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(_read),
) -> list[RuleResponse]:
    return service.list_rules(db, jurisdiction_code=jurisdiction_code, kind_code=kind_code, class_code=class_code, in_effect_on=in_effect_on)


@router.post("/rules", response_model=RuleActionResponse, status_code=status.HTTP_201_CREATED)
def record_rule_endpoint(payload: RuleInput, db: Session = Depends(get_db), user: AuthUser = Depends(_rule_manage)) -> RuleActionResponse:
    return _run(lambda: service.record_rule(db, payload=payload, user_public_id=_user(user)))


@router.post("/rules/{rule_public_id}/end", response_model=RuleActionResponse)
def end_rule_endpoint(
    rule_public_id: UUID, payload: RuleEndInput, db: Session = Depends(get_db), user: AuthUser = Depends(_rule_manage)
) -> RuleActionResponse:
    return _run(lambda: service.end_rule(db, rule_public_id=str(rule_public_id), payload=payload, user_public_id=_user(user)))


# --- Reminders and escalation (ELG-2) -------------------------------------------------------------------------


@router.get("/alerts", response_model=AlertsResponse)
def list_alerts_endpoint(
    reminder_kind_code: str | None = Query(default=None, max_length=30),
    unseen_only: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=MAX_ALERT_LIMIT),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_read),
) -> AlertsResponse:
    return _run(
        lambda: alerts.list_alerts(
            db, user, reminder_kind_code=reminder_kind_code, unseen_only=unseen_only, search=search, limit=limit, offset=offset
        )
    )


@router.get("/alerts/count", response_model=AlertCountResponse)
def count_alerts_endpoint(db: Session = Depends(get_db), user: AuthUser = Depends(_read)) -> AlertCountResponse:
    return _run(lambda: alerts.count_alerts(db, user))


@router.post("/alerts/seen", response_model=SeenResponse)
def mark_seen_endpoint(payload: SeenInput, db: Session = Depends(get_db), user: AuthUser = Depends(_read)) -> SeenResponse:
    return _run(lambda: alerts.mark_seen(db, user, payload=payload))


@router.get("/alert-settings", response_model=AlertSettingsResponse)
def get_alert_settings_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> AlertSettingsResponse:
    return alerts.get_settings(db)


@router.post("/alert-settings/{reminder_kind_code}", response_model=AlertSettingActionResponse, status_code=status.HTTP_201_CREATED)
def save_alert_setting_endpoint(
    payload: AlertSettingInput,
    response: Response,
    reminder_kind_code: str = Path(min_length=1, max_length=30),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_rule_manage),
) -> AlertSettingActionResponse:
    result = _run(lambda: alerts.save_setting(db, reminder_kind_code=reminder_kind_code, payload=payload, user_public_id=_user(user)))
    if result.unchanged:
        # The same as the current version: nothing new was recorded.
        response.status_code = status.HTTP_200_OK
    return result
