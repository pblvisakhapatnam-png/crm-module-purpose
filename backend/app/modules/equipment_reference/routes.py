"""Equipment Reference API (WRR-001, ERT-1, ERT-2). docs/agent/contracts/equipment-reference-api-contract.md.

Reading follows EQUIPMENT_REFERENCE_READ; every write, and the Plum report import screens, need
EQUIPMENT_REFERENCE_MANAGE (Admin, until a Fleet Admin role exists). Engine and chassis numbers - on a
machine, and in any correction or value rule of those fields - are shown only with EQUIPMENT_IDENTITY_READ
(Admin only for now). The structure itself still has no write route: it changes only by migration.

Every route's request body is counted as it arrives and refused past the report upload's bound, before it
is parsed - and so before authentication - as Slice 9C's documents routes do: an upload of any size can
otherwise be received in full before anything can refuse it.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.types import Message, Receive

from app.core.database import get_db
from app.modules.authorization.contract import EQUIPMENT_REFERENCE_MANAGE, EQUIPMENT_REFERENCE_READ
from app.modules.authorization.dependencies import require_permission
from app.modules.equipment_reference.contract import MAX_EQUIPMENT_REQUEST_BYTES, MAX_REPORT_BYTES
from app.modules.equipment_reference.schemas import (
    CategoryRuleResponse,
    CorrectionsToSendResponse,
    EquipmentModelActionResponse,
    EquipmentModelCreate,
    EquipmentModelResponse,
    EquipmentModelUpdate,
    EquipmentStructureResponse,
    FitPartInput,
    ImportActionResponse,
    ImportDiscardInput,
    ImportPublishInput,
    ImportRefreshInput,
    ImportResponse,
    ImportSummaryResponse,
    KitAddInput,
    KitAddResponse,
    KitRetireInput,
    MachineActionResponse,
    MachineCapabilitiesInput,
    MachineCorrectionCloseInput,
    MachineCorrectionInput,
    MachineDetailsInput,
    MachineResponse,
    MachineSummaryResponse,
    ModelMappingActionResponse,
    ModelMappingInput,
    RemovePartInput,
    ValueRuleActionResponse,
    ValueRuleInput,
    ValueRuleResponse,
)
from app.modules.equipment_reference.service import get_equipment_structure
from app.modules.equipment_reference.services import imports, machines, models, rules
from app.modules.equipment_reference.services.common import (
    EquipmentConflictError,
    EquipmentNotFoundError,
    EquipmentValidationError,
    can_see_identity_numbers,
)
from app.modules.identity.schemas import AuthUser

_LIMIT_MESSAGE = f"This upload is larger than the {MAX_REPORT_BYTES // (1024 * 1024)} MB limit."


def _count_request_body(receive: Receive) -> Receive:
    """Refuse the request (413) once its body passes MAX_EQUIPMENT_REQUEST_BYTES, counting the bytes that
    actually arrive and consulting no declared size."""
    received = 0

    async def counting_receive() -> Message:
        nonlocal received
        message = await receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > MAX_EQUIPMENT_REQUEST_BYTES:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=_LIMIT_MESSAGE)
        return message

    return counting_receive


class _BoundedBodyRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def bounded_handler(request: Request) -> Response:
            return await handler(Request(request.scope, receive=_count_request_body(request.receive)))

        return bounded_handler


router = APIRouter(prefix="/api/equipment-reference", tags=["equipment-reference"], route_class=_BoundedBodyRoute)

_ERRORS = (EquipmentNotFoundError, EquipmentConflictError, EquipmentValidationError)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EquipmentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, EquipmentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _user(user: AuthUser) -> str | None:
    value = getattr(user, "user_public_id", None) or getattr(user, "public_id", None)
    return str(value) if value else None


def _run(call: Callable[[], Any]) -> Any:
    try:
        return call()
    except _ERRORS as exc:
        raise _http_error(exc) from exc


_read = require_permission(EQUIPMENT_REFERENCE_READ)
_manage = require_permission(EQUIPMENT_REFERENCE_MANAGE)


def _identity(db: Session, user: AuthUser) -> bool:
    """Whether the caller may see engine and chassis numbers (owner, 25 September 2026: Admin only for
    now). Every response that can carry one - a machine, a correction, a value rule - asks this; the
    services withhold them by default. The check itself is the service's: route modules never read roles."""
    return can_see_identity_numbers(db, user)


# --- The structure (WRR-001) -----------------------------------------------------------------------


@router.get("/structure", response_model=EquipmentStructureResponse)
def get_equipment_structure_endpoint(
    db: Session = Depends(get_db), _: AuthUser = Depends(_read)
) -> EquipmentStructureResponse:
    return get_equipment_structure(db)


@router.get("/category-rules", response_model=list[CategoryRuleResponse])
def list_category_rules_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> list[CategoryRuleResponse]:
    return rules.list_category_rules(db)


# --- Machines --------------------------------------------------------------------------------------


@router.get("/machines", response_model=list[MachineSummaryResponse])
def list_machines_endpoint(
    kind_code: str | None = Query(default=None, max_length=20),
    class_code: str | None = Query(default=None, max_length=50),
    type_code: str | None = Query(default=None, max_length=50),
    status_code: str | None = Query(default=None, max_length=20),
    flagged_only: bool = Query(default=False),
    details_to_complete: bool = Query(default=False),
    search: str | None = Query(default=None, max_length=100),
    kit_model_public_id: UUID | None = Query(default=None),
    fits_model_public_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(_read),
) -> list[MachineSummaryResponse]:
    return _run(
        lambda: machines.list_machines(
            db,
            kind_code=kind_code,
            class_code=class_code,
            type_code=type_code,
            status_code=status_code,
            flagged_only=flagged_only,
            details_to_complete=details_to_complete,
            search=search,
            limit=limit,
            offset=offset,
            kit_model_public_id=kit_model_public_id,
            fits_model_public_id=fits_model_public_id,
        )
    )


@router.get("/machines/{public_id}", response_model=MachineResponse)
def get_machine_endpoint(public_id: UUID, db: Session = Depends(get_db), user: AuthUser = Depends(_read)) -> MachineResponse:
    return _run(lambda: machines.get_machine(db, public_id, show_identity=_identity(db, user)))


@router.put("/machines/{public_id}/details", response_model=MachineActionResponse)
def set_machine_details_endpoint(
    public_id: UUID, payload: MachineDetailsInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> MachineActionResponse:
    return _run(lambda: machines.set_machine_details(db, public_id=public_id, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.put("/machines/{public_id}/capabilities", response_model=MachineActionResponse)
def set_machine_capabilities_endpoint(
    public_id: UUID, payload: MachineCapabilitiesInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> MachineActionResponse:
    return _run(lambda: machines.set_machine_capabilities(db, public_id=public_id, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.post("/machines/{public_id}/corrections", response_model=MachineActionResponse, status_code=status.HTTP_201_CREATED)
def record_correction_endpoint(
    public_id: UUID, payload: MachineCorrectionInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> MachineActionResponse:
    return _run(lambda: machines.record_correction(db, public_id=public_id, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.post("/machines/{public_id}/corrections/{correction_public_id}/close", response_model=MachineActionResponse)
def close_correction_endpoint(
    public_id: UUID,
    correction_public_id: UUID,
    payload: MachineCorrectionCloseInput,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_manage),
) -> MachineActionResponse:
    return _run(
        lambda: machines.close_correction(
            db,
            public_id=public_id,
            correction_public_id=correction_public_id,
            payload=payload,
            user_public_id=_user(user),
            show_identity=_identity(db, user),
        )
    )


@router.post("/machines/{public_id}/fitted-parts", response_model=MachineActionResponse, status_code=status.HTTP_201_CREATED)
def fit_part_endpoint(
    public_id: UUID, payload: FitPartInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> MachineActionResponse:
    return _run(lambda: machines.fit_part(db, public_id=public_id, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.post("/machines/{public_id}/fitted-parts/{part_public_id}/remove", response_model=MachineActionResponse)
def remove_part_endpoint(
    public_id: UUID,
    part_public_id: UUID,
    payload: RemovePartInput,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_manage),
) -> MachineActionResponse:
    return _run(
        lambda: machines.remove_part(
            db,
            public_id=public_id,
            part_public_id=part_public_id,
            payload=payload,
            user_public_id=_user(user),
            show_identity=_identity(db, user),
        )
    )


@router.post("/machines/{public_id}/retire", response_model=MachineActionResponse)
def retire_piece_endpoint(
    public_id: UUID, payload: KitRetireInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> MachineActionResponse:
    return _run(lambda: machines.retire_piece(db, public_id=public_id, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


# --- Detachable kit (ERT-2) ------------------------------------------------------------------------


@router.post("/kit", response_model=KitAddResponse, status_code=status.HTTP_201_CREATED)
def add_kit_endpoint(payload: KitAddInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)) -> KitAddResponse:
    return _run(lambda: machines.add_kit(db, payload=payload, user_public_id=_user(user)))


# --- Value rules and the corrections to send to Plum -----------------------------------------------


@router.get("/value-rules", response_model=list[ValueRuleResponse])
def list_value_rules_endpoint(
    open_only: bool = Query(default=False), db: Session = Depends(get_db), user: AuthUser = Depends(_read)
) -> list[ValueRuleResponse]:
    return rules.list_value_rules(db, open_only=open_only, show_identity=_identity(db, user))


@router.put("/value-rules", response_model=ValueRuleActionResponse)
def record_value_rule_endpoint(
    payload: ValueRuleInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> ValueRuleActionResponse:
    return _run(lambda: rules.record_value_rule(db, payload=payload, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.post("/value-rules/{public_id}/close", response_model=ValueRuleActionResponse)
def close_value_rule_endpoint(
    public_id: UUID, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> ValueRuleActionResponse:
    return _run(lambda: rules.close_value_rule(db, public_id=public_id, user_public_id=_user(user), show_identity=_identity(db, user)))


@router.get("/corrections", response_model=CorrectionsToSendResponse)
def corrections_to_send_endpoint(db: Session = Depends(get_db), user: AuthUser = Depends(_read)) -> CorrectionsToSendResponse:
    return rules.corrections_to_send(db, show_identity=_identity(db, user))


# --- Models ----------------------------------------------------------------------------------------


@router.get("/models", response_model=list[EquipmentModelResponse])
def list_models_endpoint(db: Session = Depends(get_db), _: AuthUser = Depends(_read)) -> list[EquipmentModelResponse]:
    return models.list_models(db)


@router.post("/models", response_model=EquipmentModelActionResponse, status_code=status.HTTP_201_CREATED)
def create_model_endpoint(
    payload: EquipmentModelCreate, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> EquipmentModelActionResponse:
    return _run(lambda: models.create_model(db, payload=payload, user_public_id=_user(user)))


@router.put("/models/{public_id}", response_model=EquipmentModelActionResponse)
def update_model_endpoint(
    public_id: UUID, payload: EquipmentModelUpdate, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> EquipmentModelActionResponse:
    return _run(lambda: models.update_model(db, public_id=public_id, payload=payload, user_public_id=_user(user)))


@router.put("/model-mappings", response_model=ModelMappingActionResponse)
def map_model_name_endpoint(
    payload: ModelMappingInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> ModelMappingActionResponse:
    return _run(lambda: models.map_model_name(db, payload=payload, user_public_id=_user(user)))


# --- The Plum report import ------------------------------------------------------------------------


@router.post("/imports", response_model=ImportActionResponse, status_code=status.HTTP_201_CREATED)
def upload_report_endpoint(
    report_date: date = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(_manage),
) -> ImportActionResponse:
    try:
        content = file.file.read(MAX_REPORT_BYTES + 1)
        if len(content) > MAX_REPORT_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=_LIMIT_MESSAGE)
        return _run(lambda: imports.upload_report(db, content=content, report_date=report_date, user_public_id=_user(user)))
    finally:
        file.file.close()


@router.get("/imports", response_model=list[ImportSummaryResponse])
def list_imports_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(_manage),
) -> list[ImportSummaryResponse]:
    return imports.list_imports(db, limit=limit, offset=offset)


@router.get("/imports/{public_id}", response_model=ImportResponse)
def get_import_endpoint(public_id: UUID, db: Session = Depends(get_db), _: AuthUser = Depends(_manage)) -> ImportResponse:
    return _run(lambda: imports.get_import(db, public_id))


@router.post("/imports/{public_id}/refresh", response_model=ImportActionResponse)
def refresh_import_endpoint(
    public_id: UUID, payload: ImportRefreshInput, db: Session = Depends(get_db), _: AuthUser = Depends(_manage)
) -> ImportActionResponse:
    return _run(lambda: imports.refresh_import(db, public_id=public_id, payload=payload))


@router.post("/imports/{public_id}/publish", response_model=ImportActionResponse)
def publish_import_endpoint(
    public_id: UUID, payload: ImportPublishInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> ImportActionResponse:
    return _run(lambda: imports.publish_import(db, public_id=public_id, payload=payload, user_public_id=_user(user)))


@router.post("/imports/{public_id}/discard", response_model=ImportActionResponse)
def discard_import_endpoint(
    public_id: UUID, payload: ImportDiscardInput, db: Session = Depends(get_db), user: AuthUser = Depends(_manage)
) -> ImportActionResponse:
    return _run(lambda: imports.discard_import(db, public_id=public_id, payload=payload, user_public_id=_user(user)))
