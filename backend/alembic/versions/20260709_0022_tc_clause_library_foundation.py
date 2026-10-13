"""tc clause library foundation

Revision ID: 20260709_0022
Revises: 20260705_0021
Create Date: 2026-07-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260709_0022"
down_revision: Union[str, None] = "20260705_0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TC_CLAUSES = [
    {
        "public_id": "00000000-0000-0000-0000-000000000801",
        "clause_id": "TRANS-TC-001",
        "business_line": "TRANSPORTATION",
        "clause_category": "commercial_charges",
        "source_clause_number": "Transportation Annexure 3, clause 1",
        "title": "Transportation Charges And GST",
        "clause_text": "Transportation charges are fixed as agreed in the Commercial Offer. GST is extra as applicable.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": True,
        "applies_to_line": False,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000802",
        "clause_id": "TRANS-TC-002",
        "business_line": "TRANSPORTATION",
        "clause_category": "customer_scope",
        "source_clause_number": "Transportation Annexure 3, clauses 2-4",
        "title": "Loading, Unloading, Insurance And Transit Documents",
        "clause_text": "Loading, unloading, transit insurance and mandatory transit documents remain in customer scope unless the Commercial Offer states otherwise.",
        "mandatory_default": True,
        "risk_category": "operational",
        "applies_to_header": True,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000803",
        "clause_id": "TRANS-TC-003",
        "business_line": "TRANSPORTATION",
        "clause_category": "detention",
        "source_clause_number": "Transportation Annexure 3, clauses 5-6",
        "title": "Free Time And Detention",
        "clause_text": "Free time at loading and unloading points is as stated in the Commercial Offer. Detention after free time is chargeable per day or part day at the agreed rate.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": False,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000804",
        "clause_id": "TRANS-TC-004",
        "business_line": "TRANSPORTATION",
        "clause_category": "payment_terms",
        "source_clause_number": "Transportation Annexure 3, clause 7",
        "title": "Payment Timeline",
        "clause_text": "Payment is due within the agreed credit period after submission of bills and required supporting documents.",
        "mandatory_default": True,
        "risk_category": "finance",
        "applies_to_header": True,
        "applies_to_line": False,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000805",
        "clause_id": "TRANS-TC-005",
        "business_line": "TRANSPORTATION",
        "clause_category": "reimbursement",
        "source_clause_number": "Transportation Annexure 3, clause 8",
        "title": "En-Route Charges And Penalties",
        "clause_text": "En-route charges, RTO charges and penalties are reimbursable by the customer when supported by receipts, unless separately agreed.",
        "mandatory_default": True,
        "risk_category": "finance",
        "applies_to_header": True,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000806",
        "clause_id": "TRANS-TC-006",
        "business_line": "TRANSPORTATION",
        "clause_category": "billing",
        "source_clause_number": "Transportation Annexure 3, clauses 9-10",
        "title": "Billing Address And Account Statement",
        "clause_text": "Invoices use the Work Order billing address where provided. If not provided, invoicing follows applicable place-of-supply rules. Account statements may be shared at agreed contract or financial-year checkpoints.",
        "mandatory_default": True,
        "risk_category": "tax_billing",
        "applies_to_header": True,
        "applies_to_line": False,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000807",
        "clause_id": "TRANS-TC-007",
        "business_line": "TRANSPORTATION",
        "clause_category": "validity",
        "source_clause_number": "Transportation Annexure 3, clause 12",
        "title": "Quote Validity",
        "clause_text": "The Commercial Offer is valid only for the stated validity period unless extended in writing.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": True,
        "applies_to_line": False,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000808",
        "clause_id": "TRANS-TC-008",
        "business_line": "TRANSPORTATION",
        "clause_category": "weight_tolerance",
        "source_clause_number": "Transportation Annexure 3, clause 14",
        "title": "Gross Weight Tolerance",
        "clause_text": "Gross weight tolerance is limited to the agreed percentage. Deductions or adjustments beyond tolerance are handled as stated in the Commercial Offer.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": False,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#transportation-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000809",
        "clause_id": "HIRE-TC-001",
        "business_line": "HIRING",
        "clause_category": "commercial_charges",
        "source_clause_number": "Equipment Hire T&C, hire charges",
        "title": "Equipment Hire Charges",
        "clause_text": "Equipment hire charges apply as agreed for the equipment and billing basis stated in the Commercial Offer.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": True,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000810",
        "clause_id": "HIRE-TC-002",
        "business_line": "HIRING",
        "clause_category": "mobilization",
        "source_clause_number": "Equipment Hire T&C, mobilization/demobilization",
        "title": "Mobilization And Demobilization",
        "clause_text": "Mobilization and demobilization charges apply as agreed. Customer-scope and PBL-scope items must be stated clearly in the Commercial Offer.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": True,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000811",
        "clause_id": "HIRE-TC-003",
        "business_line": "HIRING",
        "clause_category": "working_hours",
        "source_clause_number": "Equipment Hire T&C, working hours",
        "title": "Working Hours And Breakdown Deduction",
        "clause_text": "Normal working days, shift hours, excluded holidays and lunch breaks must be stated in the Commercial Offer. Breakdown deductions are calculated on the agreed pro-rata basis.",
        "mandatory_default": True,
        "risk_category": "billing",
        "applies_to_header": False,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000812",
        "clause_id": "HIRE-TC-004",
        "business_line": "HIRING",
        "clause_category": "overtime",
        "source_clause_number": "Equipment Hire T&C, overtime",
        "title": "Overtime",
        "clause_text": "Overtime beyond stipulated working hours is chargeable at the agreed hourly rate and must remain traceable to the Work Order line and log sheet.",
        "mandatory_default": True,
        "risk_category": "billing",
        "applies_to_header": False,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000813",
        "clause_id": "HIRE-TC-005",
        "business_line": "HIRING",
        "clause_category": "crew_welfare",
        "source_clause_number": "Equipment Hire T&C, food/accommodation",
        "title": "Crew Food And Accommodation",
        "clause_text": "Crew food and accommodation responsibility must be stated in the Commercial Offer.",
        "mandatory_default": True,
        "risk_category": "operational",
        "applies_to_header": True,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000814",
        "clause_id": "HIRE-TC-006",
        "business_line": "HIRING",
        "clause_category": "fuel",
        "source_clause_number": "Equipment Hire T&C, diesel/fuel",
        "title": "Fuel Consumption And Debit Note",
        "clause_text": "Fuel supply basis, agreed consumption rates and excess-consumption debit note treatment must be stated in the Commercial Offer.",
        "mandatory_default": True,
        "risk_category": "commercial",
        "applies_to_header": False,
        "applies_to_line": True,
        "requires_approval_if_omitted": True,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
    {
        "public_id": "00000000-0000-0000-0000-000000000815",
        "clause_id": "HIRE-TC-007",
        "business_line": "HIRING",
        "clause_category": "advance",
        "source_clause_number": "Equipment Hire T&C, advance",
        "title": "Advance Payment",
        "clause_text": "Any advance payment requirement must be stated in the Commercial Offer and linked to the agreed milestone.",
        "mandatory_default": False,
        "risk_category": "finance",
        "applies_to_header": True,
        "applies_to_line": False,
        "requires_approval_if_omitted": False,
        "requires_approval_if_modified": True,
        "active": True,
        "source_reference": "docs/reference/erp-source-extracts/TERMS_AND_CONDITIONS_EXTRACT.md#hiring-tc-clauses",
    },
]


INSERT_CLAUSE_IF_ABSENT = sa.text(
    """
    INSERT INTO tc_clause_library (
        public_id,
        clause_id,
        business_line,
        clause_category,
        source_clause_number,
        title,
        clause_text,
        mandatory_default,
        risk_category,
        applies_to_header,
        applies_to_line,
        requires_approval_if_omitted,
        requires_approval_if_modified,
        active,
        source_reference,
        created_at,
        updated_at
    )
    SELECT
        :public_id,
        -- :clause_id is also used in the WHERE EXISTS below. Without an explicit cast
        -- PostgreSQL deduces "text" for the SELECT-list occurrence and "character varying"
        -- for the comparison, and rejects the statement as an ambiguous parameter.
        CAST(:clause_id AS VARCHAR),
        :business_line,
        :clause_category,
        :source_clause_number,
        :title,
        :clause_text,
        :mandatory_default,
        :risk_category,
        :applies_to_header,
        :applies_to_line,
        :requires_approval_if_omitted,
        :requires_approval_if_modified,
        :active,
        :source_reference,
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    WHERE NOT EXISTS (
        SELECT 1
        FROM tc_clause_library
        WHERE clause_id = :clause_id
    )
    """
)


def upgrade() -> None:
    op.create_table(
        "tc_clause_library",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("clause_id", sa.Unicode(length=50), nullable=False),
        sa.Column("business_line", sa.String(length=50), nullable=False),
        sa.Column("clause_category", sa.Unicode(length=100), nullable=False),
        sa.Column("source_clause_number", sa.Unicode(length=255), nullable=True),
        sa.Column("title", sa.Unicode(length=255), nullable=False),
        sa.Column("clause_text", sa.UnicodeText(), nullable=False),
        sa.Column("mandatory_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_category", sa.Unicode(length=100), nullable=True),
        sa.Column("applies_to_header", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("applies_to_line", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "requires_approval_if_omitted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "requires_approval_if_modified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_reference", sa.Unicode(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_tc_clause_library"),
        sa.UniqueConstraint("public_id", name="uq_tc_clause_library_public_id"),
        sa.UniqueConstraint("clause_id", name="uq_tc_clause_library_clause_id"),
        sa.CheckConstraint(
            "business_line IN ('TRANSPORTATION', 'HIRING')",
            name="ck_tc_clause_library_business_line",
        ),
    )

    for index_name, columns in (
        ("ix_tc_clause_library_business_line", ["business_line"]),
        ("ix_tc_clause_library_category", ["clause_category"]),
        ("ix_tc_clause_library_active", ["active"]),
        ("ix_tc_clause_library_header", ["applies_to_header"]),
        ("ix_tc_clause_library_line", ["applies_to_line"]),
    ):
        op.create_index(index_name, "tc_clause_library", columns, unique=False)

    # PostgreSQL takes real boolean values; the SQL Server 1/0 coercion is no longer needed.
    connection = op.get_bind()
    for row in TC_CLAUSES:
        connection.execute(INSERT_CLAUSE_IF_ABSENT, row)


def downgrade() -> None:
    op.drop_table("tc_clause_library")

