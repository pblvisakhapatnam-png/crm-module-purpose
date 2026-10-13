from uuid import uuid4

from sqlalchemy import text

from app.core.database import SessionLocal


def test_business_party_table_has_foundation_columns():
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'business_party'
                ORDER BY ORDINAL_POSITION
                """
            )
        ).fetchall()

        columns = {row[0] for row in rows}

        expected_columns = {
            "id",
            "business_party_public_id",
            "party_type",
            "account_name",
            "legal_name",
            "pan",
            "gstin",
            "account_status_code",
            "qualification_source",
            "account_owner_user_public_id",
            "segment",
            "industry",
            "source_remarks",
            "created_by",
            "created_at",
            "updated_at",
        }

        assert expected_columns.issubset(columns)
    finally:
        db.close()


def test_can_insert_minimal_business_party_record():
    db = SessionLocal()
    public_id = str(uuid4())

    try:
        db.execute(
            text(
                """
                INSERT INTO business_party (
                    business_party_public_id,
                    account_name,
                    account_status_code,
                    qualification_source,
                    created_by
                ) VALUES (
                    :business_party_public_id,
                    :account_name,
                    :account_status_code,
                    :qualification_source,
                    :created_by
                )
                """
            ),
            {
                "business_party_public_id": public_id,
                "account_name": "Slice 1A Test Account",
                "account_status_code": "DRAFT",
                "qualification_source": "manual",
                "created_by": "00000000-0000-0000-0000-000000000201",
            },
        )

        row = db.execute(
            text(
                """
                SELECT
                    business_party_public_id,
                    party_type,
                    account_name,
                    account_status_code
                FROM business_party
                WHERE business_party_public_id = :business_party_public_id
                """
            ),
            {"business_party_public_id": public_id},
        ).first()

        assert row is not None
        assert row.business_party_public_id == public_id
        assert row.party_type == "organization"
        assert row.account_name == "Slice 1A Test Account"
        assert row.account_status_code == "DRAFT"
    finally:
        db.rollback()
        db.close()