from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.accounts.contract import (
    BUSINESS_PARTY_ADDRESS_TABLE,
    BUSINESS_PARTY_CONTACT_TABLE,
    BUSINESS_PARTY_GSTIN_TABLE,
    BUSINESS_PARTY_TABLE,
    DOCUMENT_METADATA_TABLE,
    BUSINESS_PARTY_TAX_PROFILE_TABLE,
    BUSINESS_PARTY_WORKFLOW_MODULE,
)
from app.modules.accounts.schemas import (
    AccountAddressResponse,
    AccountClassificationResponse,
    AccountContactResponse,
    AccountDocumentResponse,
    AccountGstinResponse,
    AccountResponse,
    AccountTaxProfileResponse,
)


# Qualified with the `bp` alias because ACCOUNT_ACTOR_JOINS brings app_user into the same FROM
# clause, and app_user also has id, created_at and updated_at.
ACCOUNT_SELECT_COLUMNS = """
    bp.business_party_public_id AS public_id,
    bp.party_type,
    bp.account_name,
    bp.legal_name,
    bp.pan,
    bp.gstin,
    bp.account_status_code,
    bp.qualification_source,
    bp.account_owner_user_public_id,
    account_owner.display_name AS account_owner_display_name,
    bp.segment,
    bp.industry,
    bp.source_remarks,
    bp.is_strategic_account,
    bp.classification_notes,
    bp.created_by,
    account_creator.display_name AS created_by_display_name,
    bp.created_at,
    bp.updated_at
"""

# Read-only display names for the owner/creator ids, resolved in the same query so a list stays one
# round trip. LEFT JOINs, following QUOTE_DOCUMENT_ACTOR_JOINS in the commercial_offers repository:
# an Account whose id matches no app_user row still lists, with a NULL name.
ACCOUNT_ACTOR_JOINS = """
    LEFT JOIN app_user account_owner ON account_owner.public_id = bp.account_owner_user_public_id
    LEFT JOIN app_user account_creator ON account_creator.public_id = bp.created_by
"""

CONTACT_SELECT_COLUMNS = """
    c.contact_public_id AS public_id,
    bp.business_party_public_id AS account_public_id,
    c.contact_name,
    c.designation,
    c.department,
    c.phone,
    c.email,
    c.is_primary,
    c.is_active,
    c.remarks,
    c.created_by,
    c.created_at,
    c.updated_at
"""

TAX_PROFILE_SELECT_COLUMNS = """
    t.tax_profile_public_id AS public_id,
    bp.business_party_public_id AS account_public_id,
    t.pan,
    t.pan_verification_state_code,
    t.pan_legal_name,
    t.remarks,
    t.created_by,
    t.created_at,
    t.updated_at
"""

GSTIN_SELECT_COLUMNS = """
    g.gstin_public_id AS public_id,
    bp.business_party_public_id AS account_public_id,
    g.gstin,
    g.gstin_verification_state_code,
    g.state_code,
    g.state_name,
    g.legal_name,
    g.trade_name,
    g.is_primary,
    g.is_active,
    g.remarks,
    g.created_by,
    g.created_at,
    g.updated_at
"""

DOCUMENT_SELECT_COLUMNS = """
    d.document_public_id AS public_id,
    bp.business_party_public_id AS account_public_id,
    d.document_type,
    d.file_name,
    d.original_file_name,
    d.storage_mode,
    d.storage_path_or_url,
    d.version_no,
    d.status,
    d.uploaded_by,
    d.uploaded_at,
    d.remarks
"""

ADDRESS_SELECT_COLUMNS = """
    a.address_public_id AS public_id,
    bp.business_party_public_id AS account_public_id,
    a.address_type_code,
    a.address_line1,
    a.address_line2,
    a.city,
    a.district,
    a.state,
    a.postal_code,
    a.country_code,
    a.is_primary,
    a.is_active,
    a.remarks,
    a.created_by,
    a.created_at,
    a.updated_at
"""


def _row_to_account(row: Any) -> AccountResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountResponse(
        public_id=data["public_id"],
        party_type=data["party_type"],
        account_name=data["account_name"],
        legal_name=data.get("legal_name"),
        pan=data.get("pan"),
        gstin=data.get("gstin"),
        account_status_code=data["account_status_code"],
        qualification_source=data.get("qualification_source"),
        account_owner_user_public_id=data.get("account_owner_user_public_id"),
        account_owner_display_name=data.get("account_owner_display_name"),
        segment=data.get("segment"),
        industry=data.get("industry"),
        source_remarks=data.get("source_remarks"),
        is_strategic_account=bool(data.get("is_strategic_account", False)),
        classification_notes=data.get("classification_notes"),
        created_by=data.get("created_by"),
        created_by_display_name=data.get("created_by_display_name"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_classification(row: Any) -> AccountClassificationResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountClassificationResponse(
        account_public_id=data["account_public_id"],
        account_owner_user_public_id=data.get("account_owner_user_public_id"),
        account_owner_display_name=data.get("account_owner_display_name"),
        segment=data.get("segment"),
        industry=data.get("industry"),
        is_strategic_account=bool(data.get("is_strategic_account", False)),
        classification_notes=data.get("classification_notes"),
        updated_at=data["updated_at"],
    )


def _row_to_contact(row: Any) -> AccountContactResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountContactResponse(
        public_id=data["public_id"],
        account_public_id=data["account_public_id"],
        contact_name=data["contact_name"],
        designation=data.get("designation"),
        department=data.get("department"),
        phone=data.get("phone"),
        email=data.get("email"),
        is_primary=bool(data["is_primary"]),
        is_active=bool(data["is_active"]),
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_address(row: Any) -> AccountAddressResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountAddressResponse(
        public_id=data["public_id"],
        account_public_id=data["account_public_id"],
        address_type_code=data["address_type_code"],
        address_line1=data["address_line1"],
        address_line2=data.get("address_line2"),
        city=data["city"],
        district=data.get("district"),
        state=data["state"],
        postal_code=data.get("postal_code"),
        country_code=data["country_code"],
        is_primary=bool(data["is_primary"]),
        is_active=bool(data["is_active"]),
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_tax_profile(row: Any) -> AccountTaxProfileResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountTaxProfileResponse(
        public_id=data["public_id"],
        account_public_id=data["account_public_id"],
        pan=data.get("pan"),
        pan_verification_state_code=data["pan_verification_state_code"],
        pan_legal_name=data.get("pan_legal_name"),
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_gstin(row: Any) -> AccountGstinResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountGstinResponse(
        public_id=data["public_id"],
        account_public_id=data["account_public_id"],
        gstin=data["gstin"],
        gstin_verification_state_code=data["gstin_verification_state_code"],
        state_code=data["state_code"],
        state_name=data.get("state_name"),
        legal_name=data.get("legal_name"),
        trade_name=data.get("trade_name"),
        is_primary=bool(data["is_primary"]),
        is_active=bool(data["is_active"]),
        remarks=data.get("remarks"),
        created_by=data.get("created_by"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def _row_to_document(row: Any) -> AccountDocumentResponse:
    data = row._mapping if hasattr(row, "_mapping") else row
    return AccountDocumentResponse(
        public_id=data["public_id"],
        account_public_id=data["account_public_id"],
        document_type=data["document_type"],
        file_name=data["file_name"],
        original_file_name=data.get("original_file_name"),
        storage_mode=data["storage_mode"],
        storage_path_or_url=data.get("storage_path_or_url"),
        version_no=data["version_no"],
        status=data["status"],
        uploaded_by=data.get("uploaded_by"),
        uploaded_at=data["uploaded_at"],
        remarks=data.get("remarks"),
    )


def active_account_status_exists(db: Session, status_code: str) -> bool:
    exists = db.execute(
        text(
            """
            SELECT 1
            FROM workflow_status
            WHERE module = :module
              AND status_code = :status_code
              AND is_active IS TRUE
            """
        ),
        {"module": BUSINESS_PARTY_WORKFLOW_MODULE, "status_code": status_code},
    ).scalar()
    return exists == 1


def insert_business_party(
    db: Session,
    *,
    public_id: str,
    values: dict[str, Any],
) -> AccountResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {BUSINESS_PARTY_TABLE} (
                business_party_public_id,
                party_type,
                account_name,
                legal_name,
                pan,
                gstin,
                account_status_code,
                qualification_source,
                account_owner_user_public_id,
                segment,
                industry,
                source_remarks,
                is_strategic_account,
                classification_notes,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :business_party_public_id,
                :party_type,
                :account_name,
                :legal_name,
                :pan,
                :gstin,
                :account_status_code,
                :qualification_source,
                :account_owner_user_public_id,
                :segment,
                :industry,
                :source_remarks,
                :is_strategic_account,
                :classification_notes,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {"business_party_public_id": public_id, **values},
    )
    account = get_business_party_by_public_id(db, public_id)
    if account is None:
        raise RuntimeError("Inserted Account could not be reloaded.")
    return account


def get_business_party_by_public_id(db: Session, public_id: str) -> AccountResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {ACCOUNT_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_TABLE} bp
            {ACCOUNT_ACTOR_JOINS}
            WHERE bp.business_party_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_account(row) if row else None


def get_business_party_id_by_public_id(db: Session, public_id: str) -> int | None:
    value = db.execute(
        text(
            f"""
            SELECT id
            FROM {BUSINESS_PARTY_TABLE}
            WHERE business_party_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).scalar()
    return int(value) if value is not None else None


def list_recent_business_parties(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    status_code: str | None = None,
) -> list[AccountResponse]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    params: dict[str, Any] = {}
    where_clause = ""

    if status_code:
        where_clause = "WHERE bp.account_status_code = :status_code"
        params["status_code"] = status_code

    rows = db.execute(
        text(
            f"""
            SELECT
                {ACCOUNT_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_TABLE} bp
            {ACCOUNT_ACTOR_JOINS}
            {where_clause}
            ORDER BY bp.created_at DESC, bp.id DESC
            LIMIT {safe_limit} OFFSET {safe_offset}
            """
        ),
        params,
    ).fetchall()
    return [_row_to_account(row) for row in rows]



def get_business_party_classification_by_public_id(
    db: Session,
    public_id: str,
) -> AccountClassificationResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                bp.business_party_public_id AS account_public_id,
                bp.account_owner_user_public_id,
                account_owner.display_name AS account_owner_display_name,
                bp.segment,
                bp.industry,
                bp.is_strategic_account,
                bp.classification_notes,
                bp.updated_at
            FROM {BUSINESS_PARTY_TABLE} bp
            {ACCOUNT_ACTOR_JOINS}
            WHERE bp.business_party_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_classification(row) if row else None


def update_business_party_classification(
    db: Session,
    *,
    account_public_id: str,
    values: dict[str, Any],
) -> AccountClassificationResponse:
    db.execute(
        text(
            f"""
            UPDATE {BUSINESS_PARTY_TABLE}
            SET account_owner_user_public_id = :account_owner_user_public_id,
                segment = :segment,
                industry = :industry,
                is_strategic_account = :is_strategic_account,
                classification_notes = :classification_notes,
                updated_at = CURRENT_TIMESTAMP
            WHERE business_party_public_id = :account_public_id
            """
        ),
        {"account_public_id": account_public_id, **values},
    )
    classification = get_business_party_classification_by_public_id(db, account_public_id)
    if classification is None:
        raise RuntimeError("Updated Account classification could not be reloaded.")
    return classification

def insert_business_party_contact(
    db: Session,
    *,
    public_id: str,
    business_party_id: int,
    values: dict[str, Any],
) -> AccountContactResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {BUSINESS_PARTY_CONTACT_TABLE} (
                contact_public_id,
                business_party_id,
                contact_name,
                designation,
                department,
                phone,
                email,
                is_primary,
                is_active,
                remarks,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :contact_public_id,
                :business_party_id,
                :contact_name,
                :designation,
                :department,
                :phone,
                :email,
                :is_primary,
                TRUE,
                :remarks,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "contact_public_id": public_id,
            "business_party_id": business_party_id,
            **values,
        },
    )
    contact = get_business_party_contact_by_public_id(db, public_id)
    if contact is None:
        raise RuntimeError("Inserted Account Contact could not be reloaded.")
    return contact


def get_business_party_contact_by_public_id(db: Session, public_id: str) -> AccountContactResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {CONTACT_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_CONTACT_TABLE} c
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = c.business_party_id
            WHERE c.contact_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_contact(row) if row else None


def list_business_party_contacts(
    db: Session,
    *,
    account_public_id: str,
) -> list[AccountContactResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {CONTACT_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_CONTACT_TABLE} c
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = c.business_party_id
            WHERE bp.business_party_public_id = :account_public_id
              AND c.is_active IS TRUE
            ORDER BY c.is_primary DESC, c.created_at DESC, c.id DESC
            """
        ),
        {"account_public_id": account_public_id},
    ).fetchall()
    return [_row_to_contact(row) for row in rows]


def insert_business_party_address(
    db: Session,
    *,
    public_id: str,
    business_party_id: int,
    values: dict[str, Any],
) -> AccountAddressResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {BUSINESS_PARTY_ADDRESS_TABLE} (
                address_public_id,
                business_party_id,
                address_type_code,
                address_line1,
                address_line2,
                city,
                district,
                state,
                postal_code,
                country_code,
                is_primary,
                is_active,
                remarks,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :address_public_id,
                :business_party_id,
                :address_type_code,
                :address_line1,
                :address_line2,
                :city,
                :district,
                :state,
                :postal_code,
                :country_code,
                :is_primary,
                TRUE,
                :remarks,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "address_public_id": public_id,
            "business_party_id": business_party_id,
            **values,
        },
    )
    address = get_business_party_address_by_public_id(db, public_id)
    if address is None:
        raise RuntimeError("Inserted Account Address could not be reloaded.")
    return address


def get_business_party_address_by_public_id(db: Session, public_id: str) -> AccountAddressResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {ADDRESS_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_ADDRESS_TABLE} a
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = a.business_party_id
            WHERE a.address_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_address(row) if row else None


def list_business_party_addresses(
    db: Session,
    *,
    account_public_id: str,
) -> list[AccountAddressResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {ADDRESS_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_ADDRESS_TABLE} a
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = a.business_party_id
            WHERE bp.business_party_public_id = :account_public_id
              AND a.is_active IS TRUE
            ORDER BY a.is_primary DESC, a.created_at DESC, a.id DESC
            """
        ),
        {"account_public_id": account_public_id},
    ).fetchall()
    return [_row_to_address(row) for row in rows]


def get_business_party_tax_profile_by_account_public_id(
    db: Session,
    *,
    account_public_id: str,
) -> AccountTaxProfileResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {TAX_PROFILE_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_TAX_PROFILE_TABLE} t
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = t.business_party_id
            WHERE bp.business_party_public_id = :account_public_id
            """
        ),
        {"account_public_id": account_public_id},
    ).first()
    return _row_to_tax_profile(row) if row else None


def upsert_business_party_tax_profile(
    db: Session,
    *,
    public_id: str,
    business_party_id: int,
    values: dict[str, Any],
) -> AccountTaxProfileResponse:
    existing_public_id = db.execute(
        text(
            f"""
            SELECT tax_profile_public_id
            FROM {BUSINESS_PARTY_TAX_PROFILE_TABLE}
            WHERE business_party_id = :business_party_id
            """
        ),
        {"business_party_id": business_party_id},
    ).scalar()

    if existing_public_id:
        db.execute(
            text(
                f"""
                UPDATE {BUSINESS_PARTY_TAX_PROFILE_TABLE}
                SET pan = :pan,
                    pan_verification_state_code = :pan_verification_state_code,
                    pan_legal_name = :pan_legal_name,
                    remarks = :remarks,
                    updated_at = CURRENT_TIMESTAMP
                WHERE business_party_id = :business_party_id
                """
            ),
            {"business_party_id": business_party_id, **values},
        )
        tax_profile_public_id = str(existing_public_id)
    else:
        db.execute(
            text(
                f"""
                INSERT INTO {BUSINESS_PARTY_TAX_PROFILE_TABLE} (
                    tax_profile_public_id,
                    business_party_id,
                    pan,
                    pan_verification_state_code,
                    pan_legal_name,
                    remarks,
                    created_by,
                    created_at,
                    updated_at
                ) VALUES (
                    :tax_profile_public_id,
                    :business_party_id,
                    :pan,
                    :pan_verification_state_code,
                    :pan_legal_name,
                    :remarks,
                    :created_by,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "tax_profile_public_id": public_id,
                "business_party_id": business_party_id,
                **values,
            },
        )
        tax_profile_public_id = public_id

    tax_profile = get_business_party_tax_profile_by_public_id(db, tax_profile_public_id)
    if tax_profile is None:
        raise RuntimeError("Saved Account Tax Profile could not be reloaded.")
    return tax_profile


def get_business_party_tax_profile_by_public_id(db: Session, public_id: str) -> AccountTaxProfileResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {TAX_PROFILE_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_TAX_PROFILE_TABLE} t
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = t.business_party_id
            WHERE t.tax_profile_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_tax_profile(row) if row else None


def insert_business_party_gstin(
    db: Session,
    *,
    public_id: str,
    business_party_id: int,
    values: dict[str, Any],
) -> AccountGstinResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {BUSINESS_PARTY_GSTIN_TABLE} (
                gstin_public_id,
                business_party_id,
                gstin,
                gstin_verification_state_code,
                state_code,
                state_name,
                legal_name,
                trade_name,
                is_primary,
                is_active,
                remarks,
                created_by,
                created_at,
                updated_at
            ) VALUES (
                :gstin_public_id,
                :business_party_id,
                :gstin,
                :gstin_verification_state_code,
                :state_code,
                :state_name,
                :legal_name,
                :trade_name,
                :is_primary,
                TRUE,
                :remarks,
                :created_by,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "gstin_public_id": public_id,
            "business_party_id": business_party_id,
            **values,
        },
    )
    gstin = get_business_party_gstin_by_public_id(db, public_id)
    if gstin is None:
        raise RuntimeError("Inserted Account GSTIN could not be reloaded.")
    return gstin


def get_business_party_gstin_by_public_id(db: Session, public_id: str) -> AccountGstinResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {GSTIN_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_GSTIN_TABLE} g
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = g.business_party_id
            WHERE g.gstin_public_id = :public_id
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_gstin(row) if row else None


def list_business_party_gstins(
    db: Session,
    *,
    account_public_id: str,
) -> list[AccountGstinResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {GSTIN_SELECT_COLUMNS}
            FROM {BUSINESS_PARTY_GSTIN_TABLE} g
            INNER JOIN {BUSINESS_PARTY_TABLE} bp ON bp.id = g.business_party_id
            WHERE bp.business_party_public_id = :account_public_id
              AND g.is_active IS TRUE
            ORDER BY g.is_primary DESC, g.created_at DESC, g.id DESC
            """
        ),
        {"account_public_id": account_public_id},
    ).fetchall()
    return [_row_to_gstin(row) for row in rows]


def gstin_exists(db: Session, gstin: str) -> bool:
    exists = db.execute(
        text(
            f"""
            SELECT 1
            FROM {BUSINESS_PARTY_GSTIN_TABLE}
            WHERE gstin = :gstin
            """
        ),
        {"gstin": gstin},
    ).scalar()
    return exists == 1


def insert_account_document_metadata(
    db: Session,
    *,
    public_id: str,
    account_public_id: str,
    values: dict[str, Any],
) -> AccountDocumentResponse:
    db.execute(
        text(
            f"""
            INSERT INTO {DOCUMENT_METADATA_TABLE} (
                document_public_id,
                document_type,
                linked_record_type,
                linked_record_public_id,
                file_name,
                original_file_name,
                storage_mode,
                storage_path_or_url,
                version_no,
                status,
                uploaded_by,
                uploaded_at,
                remarks,
                created_at
            ) VALUES (
                :document_public_id,
                :document_type,
                'business_party',
                :linked_record_public_id,
                :file_name,
                :original_file_name,
                :storage_mode,
                :storage_path_or_url,
                :version_no,
                :status,
                :uploaded_by,
                CURRENT_TIMESTAMP,
                :remarks,
                CURRENT_TIMESTAMP
            )
            """
        ),
        {
            "document_public_id": public_id,
            "linked_record_public_id": account_public_id,
            **values,
        },
    )
    document = get_account_document_by_public_id(db, public_id)
    if document is None:
        raise RuntimeError("Inserted Account Document metadata could not be reloaded.")
    return document


def get_account_document_by_public_id(db: Session, public_id: str) -> AccountDocumentResponse | None:
    row = db.execute(
        text(
            f"""
            SELECT
                {DOCUMENT_SELECT_COLUMNS}
            FROM {DOCUMENT_METADATA_TABLE} d
            INNER JOIN {BUSINESS_PARTY_TABLE} bp
                ON bp.business_party_public_id = d.linked_record_public_id
            WHERE d.document_public_id = :public_id
              AND d.linked_record_type = 'business_party'
            """
        ),
        {"public_id": public_id},
    ).first()
    return _row_to_document(row) if row else None


def list_account_document_metadata(
    db: Session,
    *,
    account_public_id: str,
) -> list[AccountDocumentResponse]:
    rows = db.execute(
        text(
            f"""
            SELECT
                {DOCUMENT_SELECT_COLUMNS}
            FROM {DOCUMENT_METADATA_TABLE} d
            INNER JOIN {BUSINESS_PARTY_TABLE} bp
                ON bp.business_party_public_id = d.linked_record_public_id
            WHERE d.linked_record_type = 'business_party'
              AND d.linked_record_public_id = :account_public_id
            ORDER BY d.uploaded_at DESC, d.id DESC
            """
        ),
        {"account_public_id": account_public_id},
    ).fetchall()
    return [_row_to_document(row) for row in rows]
