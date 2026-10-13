"""Document Storage Foundation API routes (Slice 9C).

HTTP wiring only - every business rule lives in service.py. See that module's docstring for why
the record-scoped read and attach checks happen there rather than here.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session
from starlette.types import Message, Receive

from app.core.database import get_db
from app.modules.authorization.contract import (
    DOCUMENT_CONTENT_READ,
    DOCUMENT_READ,
    DOCUMENT_UPLOAD,
)
from app.modules.authorization.dependencies import require_permission
from app.modules.documents.contract import MAX_DOCUMENTS_REQUEST_BYTES
from app.modules.documents.schemas import (
    DocumentMetadataCreate,
    DocumentMetadataCreatedResponse,
    DocumentMetadataResponse,
    DocumentTypeResponse,
    DocumentUploadedResponse,
)
from app.modules.documents.service import (
    DocumentAccessDeniedError,
    DocumentContentUnavailableError,
    DocumentNotFoundError,
    DocumentUploadTooLargeError,
    DocumentUploadTypeError,
    DocumentValidationError,
    create_document_metadata_for_caller,
    get_document_content_for_caller,
    iter_document_content,
    list_documents_for_record_for_caller,
    list_recent_documents_for_caller,
    upload_document_for_caller,
)
from app.modules.identity.schemas import AuthUser

def _count_request_body(receive: Receive) -> Receive:
    """Wrap an ASGI receive channel so the request is refused (413) once its body passes
    MAX_DOCUMENTS_REQUEST_BYTES.

    Counts the bytes actually received - the same principle as the storage limit
    (_SizeLimitingReader in service.py) - and consults no declared size.
    """
    received = 0

    async def counting_receive() -> Message:
        nonlocal received
        message = await receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > MAX_DOCUMENTS_REQUEST_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="This upload is larger than the 25 MB limit.",
                )
        return message

    return counting_receive


class _BoundedBodyRoute(APIRoute):
    """The route class for every documents route: the request body is capped as it arrives.

    FastAPI reads a request's form or JSON body before it runs any dependency - authentication
    and require_permission included - and the record-scoped attach check runs later still, in the
    service. Without this cap an upload of any size, from any caller, signed in or not, was
    received in full and spooled to a temporary file before it could be refused (independent
    review of the upload package, round 1). The counting channel runs before the body is parsed,
    so the most any caller can make the server receive is one bounded request.
    """

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def bounded_handler(request: Request) -> Response:
            return await handler(Request(request.scope, receive=_count_request_body(request.receive)))

        return bounded_handler


router = APIRouter(prefix="/api/documents", tags=["documents"], route_class=_BoundedBodyRoute)

DOCUMENT_TYPES: list[DocumentTypeResponse] = [
    DocumentTypeResponse(code="PAN", name="PAN", description="PAN proof or PAN-related document."),
    DocumentTypeResponse(code="GST", name="GST", description="GST registration or GST proof."),
    DocumentTypeResponse(code="KYC", name="KYC", description="General customer/prospect KYC document."),
    DocumentTypeResponse(code="RFQ", name="RFQ", description="Request for quotation or enquiry document."),
    DocumentTypeResponse(code="COMMERCIAL", name="Commercial", description="Commercial offer, quote, tender or related document."),
    DocumentTypeResponse(code="OTHER", name="Other", description="Other supporting document."),
    DocumentTypeResponse(
        code="CERTIFICATE", name="Certificate", description="The copy of a machine's certificate: road papers or a lifting examination."
    ),
]


def _content_disposition(file_name: str) -> str:
    """Build an ASCII-safe `Content-Disposition` carrying the real (possibly Unicode) name.

    Response headers are encoded latin-1 by the ASGI layer, so interpolating a raw file name
    raised `UnicodeEncodeError` and failed the whole download for an ordinary name such as
    `quotation-报价.pdf` (independent review, correction pass 1, finding 2).

    RFC 6266/5987 form: a sanitised ASCII `filename` that every client understands, plus
    `filename*=UTF-8''<percent-encoded>` that modern clients prefer and which recovers the
    original name exactly. The ASCII fallback also strips quotes, backslashes and control
    characters, so a crafted file name cannot terminate the quoted string early and inject
    further header parameters.
    """
    ascii_fallback = "".join(
        character if 32 <= ord(character) < 127 and character not in '"\\' else "_"
        for character in file_name
    ).strip()
    if not ascii_fallback:
        ascii_fallback = "document"
    encoded = quote(file_name, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


@router.get("/types", response_model=list[DocumentTypeResponse])
def list_document_types(
    current_user: AuthUser = Depends(require_permission(DOCUMENT_READ)),
) -> list[DocumentTypeResponse]:
    return DOCUMENT_TYPES


@router.get("/recent", response_model=list[DocumentMetadataResponse])
def list_recent_documents_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(DOCUMENT_READ)),
) -> list[DocumentMetadataResponse]:
    return list_recent_documents_for_caller(db, limit=limit, current_user=current_user)


@router.get("/by-record/{record_type}/{record_public_id}", response_model=list[DocumentMetadataResponse])
def list_documents_for_record_endpoint(
    record_type: str,
    record_public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(DOCUMENT_READ)),
) -> list[DocumentMetadataResponse]:
    try:
        return list_documents_for_record_for_caller(
            db,
            linked_record_type=record_type,
            linked_record_public_id=str(record_public_id),
            current_user=current_user,
        )
    except DocumentAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/metadata", response_model=DocumentMetadataCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_document_metadata_endpoint(
    payload: DocumentMetadataCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(DOCUMENT_UPLOAD)),
) -> DocumentMetadataCreatedResponse:
    try:
        return create_document_metadata_for_caller(db, payload=payload, current_user=current_user)
    except DocumentAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DocumentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/upload", response_model=DocumentUploadedResponse, status_code=status.HTTP_201_CREATED)
def upload_document_endpoint(
    linked_record_type: str = Form(...),
    linked_record_public_id: UUID = Form(...),
    document_type: str = Form(...),
    remarks: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(DOCUMENT_UPLOAD)),
) -> DocumentUploadedResponse:
    try:
        return upload_document_for_caller(
            db,
            current_user=current_user,
            linked_record_type=linked_record_type,
            linked_record_public_id=linked_record_public_id,
            document_type=document_type,
            file_name=file.filename or "",
            declared_content_type=file.content_type,
            stream=file.file,
            remarks=remarks,
        )
    except DocumentAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DocumentUploadTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except (DocumentUploadTypeError, DocumentValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    finally:
        file.file.close()


@router.get("/{public_id}/content")
def download_document_content_endpoint(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_permission(DOCUMENT_CONTENT_READ)),
) -> StreamingResponse:
    try:
        row, stream_context = get_document_content_for_caller(db, public_id=public_id, current_user=current_user)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DocumentContentUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    file_name = row.get("original_file_name") or row["file_name"] or "document"
    return StreamingResponse(
        iter_document_content(stream_context),
        media_type=row.get("content_type") or "application/octet-stream",
        headers={"Content-Disposition": _content_disposition(file_name)},
    )
