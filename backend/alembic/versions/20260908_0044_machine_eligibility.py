"""machine eligibility: certificates, "not applicable" marks, rules per jurisdiction and decisions (ELG-1)

Design: docs/agent/slices/elg-1-machine-eligibility.md (every question answered by the owner, 27 September
2026), sections 5, 9 and 12. Everything is the new Eligibility module's; no other module's table changes.
Its records key on the Equipment Reference's assets by their public id, and on its classes and types by
their codes, as WRR-001's requirements do.

- **Jurisdictions.** `IN` for the central government's own sites, and the 36 states and union territories
  by their ISO 3166-2:IN codes (as revised in 2023: IN-CG, IN-OD, IN-TS, IN-UK), each with its GST state
  code. A new state or territory is added by a migration.
- **Certificate kinds.** The eight of section 5.4. Each says whether its end date may be empty, whether it
  is valid only in a named place (a permit), whether it is an examination whose interval a rule sets, and
  whether it states how the vehicle is registered. A certificate carries its kind's flags under a composite
  key, so the database itself holds the rules they imply.
- **Certificates** of one asset, never edited; withdrawn only if recorded by mistake.
- **"Not applicable" marks** of one asset and one kind, allowed only where a rule says the law is unclear
  (the owner's conservative principle, 27 September 2026). The rule that allowed one is kept on it.
- **Rules**, dated, per jurisdiction or for all of India (an empty jurisdiction: the baseline). Two rules
  for the same kind, class, type, "applies when" and jurisdiction may not be in effect on the same day: an
  exclusion constraint on the period, with `btree_gist` and COALESCE on the nullable keys. The first rules
  of section 5.4 are seeded, in effect from 21 November 2025, when the OSH Code replaced the old Acts.
- **Decisions** and their results: the `ELA-001` answer, stored when 8A allocates on it.
- **`ELIGIBILITY_RULE_MANAGE`**, granted to Admin: adding and ending rules (Q7).

Spells out every row rather than importing them, so this revision stays a frozen historical snapshot (the
20260908_0033 to 0043 convention).

Revision ID: 20260908_0044
Revises: 20260908_0043
Create Date: 2026-09-27
"""

from __future__ import annotations

from datetime import date
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0044"
down_revision: Union[str, None] = "20260908_0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


JURISDICTION_TABLE = "eligibility_jurisdiction"
KIND_TABLE = "eligibility_certificate_kind"
CERTIFICATE_TABLE = "eligibility_certificate"
MARK_TABLE = "eligibility_not_applicable"
RULE_TABLE = "eligibility_rule"
DECISION_TABLE = "eligibility_decision"
RESULT_TABLE = "eligibility_decision_result"

ASSET_TABLE = "equipment_asset"
CLASS_TABLE = "equipment_class"
TYPE_TABLE = "equipment_type"
USER_TABLE = "app_user"

# code: (label, kind, GST state code). `IN` is the central government's own sites (Q8): central public
# sector undertakings, railways and metros, major ports, oil fields and mines, with their contractors.
JURISDICTIONS: tuple[tuple[str, str, str, str | None], ...] = (
    ("IN", "Central government sites", "CENTRAL", None),
    ("IN-AN", "Andaman and Nicobar Islands", "UNION_TERRITORY", "35"),
    ("IN-AP", "Andhra Pradesh", "STATE", "37"),
    ("IN-AR", "Arunachal Pradesh", "STATE", "12"),
    ("IN-AS", "Assam", "STATE", "18"),
    ("IN-BR", "Bihar", "STATE", "10"),
    ("IN-CH", "Chandigarh", "UNION_TERRITORY", "04"),
    ("IN-CG", "Chhattisgarh", "STATE", "22"),
    ("IN-DH", "Dadra and Nagar Haveli and Daman and Diu", "UNION_TERRITORY", "26"),
    ("IN-DL", "Delhi", "UNION_TERRITORY", "07"),
    ("IN-GA", "Goa", "STATE", "30"),
    ("IN-GJ", "Gujarat", "STATE", "24"),
    ("IN-HR", "Haryana", "STATE", "06"),
    ("IN-HP", "Himachal Pradesh", "STATE", "02"),
    ("IN-JK", "Jammu and Kashmir", "UNION_TERRITORY", "01"),
    ("IN-JH", "Jharkhand", "STATE", "20"),
    ("IN-KA", "Karnataka", "STATE", "29"),
    ("IN-KL", "Kerala", "STATE", "32"),
    ("IN-LA", "Ladakh", "UNION_TERRITORY", "38"),
    ("IN-LD", "Lakshadweep", "UNION_TERRITORY", "31"),
    ("IN-MP", "Madhya Pradesh", "STATE", "23"),
    ("IN-MH", "Maharashtra", "STATE", "27"),
    ("IN-MN", "Manipur", "STATE", "14"),
    ("IN-ML", "Meghalaya", "STATE", "17"),
    ("IN-MZ", "Mizoram", "STATE", "15"),
    ("IN-NL", "Nagaland", "STATE", "13"),
    ("IN-OD", "Odisha", "STATE", "21"),
    ("IN-PY", "Puducherry", "UNION_TERRITORY", "34"),
    ("IN-PB", "Punjab", "STATE", "03"),
    ("IN-RJ", "Rajasthan", "STATE", "08"),
    ("IN-SK", "Sikkim", "STATE", "11"),
    ("IN-TN", "Tamil Nadu", "STATE", "33"),
    ("IN-TS", "Telangana", "STATE", "36"),
    ("IN-TR", "Tripura", "STATE", "16"),
    ("IN-UP", "Uttar Pradesh", "STATE", "09"),
    ("IN-UK", "Uttarakhand", "STATE", "05"),
    ("IN-WB", "West Bengal", "STATE", "19"),
)

# code: (label, end date may be empty, valid only in a named place, an examination, states registration)
KINDS: tuple[tuple[str, str, bool, bool, bool, bool], ...] = (
    ("REGISTRATION", "Registration", False, False, False, True),
    ("INSURANCE", "Insurance", False, False, False, False),
    ("POLLUTION_UNDER_CONTROL", "Pollution certificate (PUC)", False, False, False, False),
    # One-time in some states (Rajasthan: 7% of cost for a construction equipment vehicle), periodic in others.
    ("ROAD_TAX", "Road tax", True, False, False, False),
    ("FITNESS", "Fitness", False, False, False, False),
    ("PERMIT", "Permit", False, True, False, False),
    # By a competent person; the rule's interval sets how long one counts, whatever the report states.
    ("THOROUGH_EXAMINATION", "Thorough examination", True, False, True, False),
    ("LOAD_TEST", "Load test", True, False, True, False),
)

# --- The first rules (section 5.4): the baseline, for all of India, from 21 November 2025 -------------

FIRST_DAY = date(2025, 11, 21)
ROAD_PAPERS = ("REGISTRATION", "INSURANCE", "POLLUTION_UNDER_CONTROL", "ROAD_TAX")
ROAD_SOURCES = {
    "REGISTRATION": "Motor Vehicles Act 1988 ss.39 and 41; CMVR 1989 r.52; penalty s.192.",
    "INSURANCE": "Motor Vehicles Act 1988 s.146 (third party at least); penalty s.196.",
    "POLLUTION_UNDER_CONTROL": "CMVR 1989 r.115(7); penalty Motor Vehicles Act 1988 s.190(2).",
    "ROAD_TAX": "The state's Motor Vehicles Taxation Act, one-time or periodic by state and class.",
}
WHEELED_CRANE_NOTE = "A crane on wheels, on its own power, is a motor vehicle: the law is clear, so no 'not applicable'."
FIRST_YEAR_PUC_NOTE = (
    "'Not applicable' for at most 12 months: CMVR r.115(7) requires the certificate only from one year after "
    "first registration."
)
CRAWLER_NOTE = (
    "'Not applicable' allowed, with the reason: a crane not equipped to travel on public roads on its own "
    "power is very likely not a motor vehicle (CMVR r.2(ca), Explanation, G.S.R. 642(E) of 28 July 2000)."
)
OTHER_CLASS_NOTE = (
    "'Not applicable' allowed, with the reason: a tracked or towed machine, or one adapted for use only inside "
    "a plant, may not be a motor vehicle (Motor Vehicles Act 1988 s.2(28)). A wheeled one on its own power is."
)
TRANSPORT_SOURCES = {
    "FITNESS": "Motor Vehicles Act 1988 s.56; CMVR 1989 r.62; penalty s.192. Transport vehicles only.",
    "PERMIT": "Motor Vehicles Act 1988 s.66, covering the site's state; penalty s.192A. Transport vehicles only.",
}
TRANSPORT_NOTE = (
    "Applies when the registration in force says transport. A construction equipment vehicle registered as "
    "non-transport needs neither (CMVR r.2(ca), Explanation)."
)
EXAMINATION_SOURCE = (
    "PBL's rule, where the law is silent or unclear (owner, 27 September 2026, Q2): a thorough examination by a "
    "competent person every 12 months, as the old rules required (Factories Act s.29, BOCW Central Rules r.56, "
    "Dock Workers Regulations 1990 reg.41) and most states' surviving rules still do; no OSH Code s.18 "
    "standard has been published."
)
LOAD_TEST_SOURCE = (
    "PBL's rule, where the law is silent or unclear (owner, 27 September 2026, Q2): a load test by a competent "
    "person every 5 years, as BOCW Central Rules r.56 and Dock Workers Regulations 1990 reg.41 required."
)
TACKLE_EXAMINATION_SOURCE = (
    "PBL's rule (owner, 27 September 2026, Q2): each hook block and piece of tackle examined every 12 months, as "
    "BOCW Central Rules rr.61 and 70 (Form VII) and the factories register required."
)
SLING_SOURCE = (
    "PBL's rule (owner, 27 September 2026, Q2 and the conservative principle): slings every 6 months, as IS "
    "12735:1994 clause 5.3 says - stricter than the old rules' 12 months."
)
TACKLE_LOAD_TEST_SOURCE = "PBL's rule (owner, 27 September 2026, Q2): each hook block and piece of tackle load tested every 5 years, as BOCW Central Rules r.70 required."

# (kind, class, type, applies when, renew every months, basis, "not applicable", its most months, source, note)
Rule = tuple[str, str, str | None, str, int | None, str, str, int | None, str, str | None]


def _first_rules() -> list[Rule]:
    rules: list[Rule] = []
    for kind in ROAD_PAPERS:
        # Every crane: the law is clear for a wheeled crane; only the first-year PUC may be marked.
        if kind == "POLLUTION_UNDER_CONTROL":
            rules.append((kind, "CRANE", None, "ALWAYS", None, "STATUTORY", "ALLOWED", 12, ROAD_SOURCES[kind], FIRST_YEAR_PUC_NOTE))
        else:
            rules.append((kind, "CRANE", None, "ALWAYS", None, "STATUTORY", "NOT_ALLOWED", None, ROAD_SOURCES[kind], WHEELED_CRANE_NOTE))
        for crane_type in ("CRAWLER", "DERRICK"):
            rules.append((kind, "CRANE", crane_type, "ALWAYS", None, "STATUTORY", "ALLOWED", None, ROAD_SOURCES[kind], CRAWLER_NOTE))
        for class_code in ("AERIAL_WORK_PLATFORM", "FORKLIFT", "EXCAVATOR"):
            rules.append((kind, class_code, None, "ALWAYS", None, "STATUTORY", "ALLOWED", None, ROAD_SOURCES[kind], OTHER_CLASS_NOTE))
    for kind, source in TRANSPORT_SOURCES.items():
        for class_code in ("CRANE", "AERIAL_WORK_PLATFORM", "FORKLIFT", "EXCAVATOR"):
            rules.append((kind, class_code, None, "TRANSPORT_ONLY", None, "STATUTORY", "NOT_ALLOWED", None, source, TRANSPORT_NOTE))
    for class_code in ("CRANE", "AERIAL_WORK_PLATFORM", "FORKLIFT"):
        rules.append(("THOROUGH_EXAMINATION", class_code, None, "ALWAYS", 12, "PBL_RULE", "NOT_ALLOWED", None, EXAMINATION_SOURCE, None))
        rules.append(("LOAD_TEST", class_code, None, "ALWAYS", 60, "PBL_RULE", "NOT_ALLOWED", None, LOAD_TEST_SOURCE, None))
    for class_code in ("HOOK_BLOCK", "LIFTING_TACKLE"):
        rules.append(("THOROUGH_EXAMINATION", class_code, None, "ALWAYS", 12, "PBL_RULE", "NOT_ALLOWED", None, TACKLE_EXAMINATION_SOURCE, None))
        rules.append(("LOAD_TEST", class_code, None, "ALWAYS", 60, "PBL_RULE", "NOT_ALLOWED", None, TACKLE_LOAD_TEST_SOURCE, None))
    rules.append(("THOROUGH_EXAMINATION", "LIFTING_TACKLE", "SLING", "ALWAYS", 6, "PBL_RULE", "NOT_ALLOWED", None, SLING_SOURCE, None))
    return rules


ROLE_ADMIN = "ADMIN"
PERMISSION_SEED: dict[str, tuple[str, tuple[str, ...]]] = {
    # Admin only (owner, Q7): rules are law rather than fleet data, and the people half's rules will sit under
    # the same permission, so a compliance officer can be given it without the fleet's rights.
    "ELIGIBILITY_RULE_MANAGE": (
        "Add and end the rules that say which certificates each kind of machine needs, where, and how often.",
        (ROLE_ADMIN,),
    ),
}


def _non_blank(column: str, max_length: int, name: str, *, nullable: bool) -> sa.CheckConstraint:
    present = f"btrim({column}) <> '' AND char_length({column}) <= {max_length}"
    if nullable:
        return sa.CheckConstraint(f"CASE WHEN {column} IS NULL THEN TRUE ELSE {present} END", name=name)
    return sa.CheckConstraint(present, name=name)


def _withdrawal_check(table: str, status_column: str, withdrawn_code: str) -> sa.CheckConstraint:
    """A withdrawn record has its reason, who and when; any other has none of them. Each part is tested NOT NULL
    before anything else, since a CHECK passes on NULL (independent review of ERT-2, round 4)."""
    return sa.CheckConstraint(
        f"CASE WHEN {status_column} = '{withdrawn_code}' THEN withdrawn_reason IS NOT NULL AND btrim(withdrawn_reason) <> '' "
        "AND char_length(withdrawn_reason) <= 1000 AND withdrawn_by IS NOT NULL AND withdrawn_at IS NOT NULL "
        "ELSE withdrawn_reason IS NULL AND withdrawn_by IS NULL AND withdrawn_at IS NULL END",
        name=f"ck_{table}_withdrawal",
    )


def upgrade() -> None:
    _create_jurisdictions()
    _create_kinds()
    _create_rules()
    _create_certificates()
    _create_marks()
    _create_decisions()
    _seed_first_rules()
    _seed_permissions()


def _create_jurisdictions() -> None:
    op.create_table(
        JURISDICTION_TABLE,
        sa.Column("jurisdiction_code", sa.String(length=10), primary_key=True),
        sa.Column("jurisdiction_label", sa.Unicode(length=100), nullable=False),
        sa.Column("jurisdiction_kind_code", sa.String(length=20), nullable=False),
        sa.Column("gst_state_code", sa.String(length=2), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("gst_state_code", name="uq_eligibility_jurisdiction_gst_state_code"),
        sa.CheckConstraint(
            "jurisdiction_kind_code IN ('CENTRAL', 'STATE', 'UNION_TERRITORY')", name="ck_eligibility_jurisdiction_kind"
        ),
        # Central government sites have no GST state code; every state and territory has one.
        sa.CheckConstraint(
            "CASE WHEN jurisdiction_kind_code = 'CENTRAL' THEN gst_state_code IS NULL "
            "ELSE gst_state_code IS NOT NULL AND gst_state_code ~ '^[0-9]{2}$' END",
            name="ck_eligibility_jurisdiction_gst_state_code",
        ),
    )
    table = sa.table(
        JURISDICTION_TABLE,
        sa.column("jurisdiction_code", sa.String),
        sa.column("jurisdiction_label", sa.Unicode),
        sa.column("jurisdiction_kind_code", sa.String),
        sa.column("gst_state_code", sa.String),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        table,
        [
            {
                "jurisdiction_code": code,
                "jurisdiction_label": label,
                "jurisdiction_kind_code": kind,
                "gst_state_code": gst,
                "display_order": order,
            }
            for order, (code, label, kind, gst) in enumerate(JURISDICTIONS)
        ],
    )


def _create_kinds() -> None:
    op.create_table(
        KIND_TABLE,
        sa.Column("kind_code", sa.String(length=30), primary_key=True),
        sa.Column("kind_label", sa.Unicode(length=100), nullable=False),
        sa.Column("end_date_optional", sa.Boolean(), nullable=False),
        sa.Column("valid_in_required", sa.Boolean(), nullable=False),
        sa.Column("is_examination", sa.Boolean(), nullable=False),
        sa.Column("states_registration", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        # Targets of the composite keys that carry a kind's flags onto its certificates and rules.
        sa.UniqueConstraint(
            "kind_code", "end_date_optional", "valid_in_required", "states_registration", name="uq_eligibility_kind_certificate_flags"
        ),
        sa.UniqueConstraint("kind_code", "is_examination", name="uq_eligibility_kind_examination"),
    )
    table = sa.table(
        KIND_TABLE,
        sa.column("kind_code", sa.String),
        sa.column("kind_label", sa.Unicode),
        sa.column("end_date_optional", sa.Boolean),
        sa.column("valid_in_required", sa.Boolean),
        sa.column("is_examination", sa.Boolean),
        sa.column("states_registration", sa.Boolean),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(
        table,
        [
            {
                "kind_code": code,
                "kind_label": label,
                "end_date_optional": end_optional,
                "valid_in_required": valid_in,
                "is_examination": examination,
                "states_registration": registration,
                "display_order": order * 10,
            }
            for order, (code, label, end_optional, valid_in, examination, registration) in enumerate(KINDS, 1)
        ],
    )


def _create_rules() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        RULE_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_public_id", sa.String(length=36), nullable=False),
        sa.Column("kind_code", sa.String(length=30), nullable=False),
        sa.Column("kind_is_examination", sa.Boolean(), nullable=False),
        sa.Column("class_code", sa.String(length=50), nullable=False),
        sa.Column("type_code", sa.String(length=50), nullable=True),
        sa.Column("applies_when_code", sa.String(length=20), nullable=False),
        # Empty: the baseline for all of India, used where the site's own jurisdiction has no rule for the kind.
        sa.Column("jurisdiction_code", sa.String(length=10), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        # The last day it is in effect; empty until the rule is ended.
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("renew_every_months", sa.Integer(), nullable=True),
        sa.Column("basis_code", sa.String(length=20), nullable=False),
        sa.Column("lapse_code", sa.String(length=20), nullable=False),
        sa.Column("not_applicable_code", sa.String(length=20), nullable=False),
        sa.Column("not_applicable_max_months", sa.Integer(), nullable=True),
        sa.Column("source", sa.Unicode(length=1000), nullable=False),
        sa.Column("note", sa.Unicode(length=1000), nullable=True),
        sa.Column("create_request_key", sa.String(length=100), nullable=True),
        # Empty for the rules this migration loads.
        sa.Column("recorded_by", sa.String(length=36), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ended_by", sa.String(length=36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.Unicode(length=1000), nullable=True),
        sa.UniqueConstraint("rule_public_id", name="uq_eligibility_rule_public_id"),
        sa.UniqueConstraint("create_request_key", name="uq_eligibility_rule_create_request_key"),
        sa.ForeignKeyConstraint(
            ["kind_code", "kind_is_examination"],
            [f"{KIND_TABLE}.kind_code", f"{KIND_TABLE}.is_examination"],
            name="fk_eligibility_rule_kind",
        ),
        sa.ForeignKeyConstraint(["class_code"], [f"{CLASS_TABLE}.class_code"], name="fk_eligibility_rule_class"),
        # MATCH SIMPLE: a rule for every type of the class has no type to check.
        sa.ForeignKeyConstraint(
            ["class_code", "type_code"], [f"{TYPE_TABLE}.class_code", f"{TYPE_TABLE}.type_code"], name="fk_eligibility_rule_type"
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_code"], [f"{JURISDICTION_TABLE}.jurisdiction_code"], name="fk_eligibility_rule_jurisdiction"
        ),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_rule_recorded_by"),
        sa.ForeignKeyConstraint(["ended_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_rule_ended_by"),
        sa.CheckConstraint("applies_when_code IN ('ALWAYS', 'TRANSPORT_ONLY')", name="ck_eligibility_rule_applies_when"),
        # The registration decides whether the transport rules apply, so it is never itself transport-only.
        sa.CheckConstraint(
            "kind_code <> 'REGISTRATION' OR applies_when_code = 'ALWAYS'", name="ck_eligibility_rule_registration_always"
        ),
        # At central-government sites only the examinations follow IN's rules; road papers follow the site's state.
        sa.CheckConstraint(
            "jurisdiction_code IS DISTINCT FROM 'IN' OR kind_is_examination", name="ck_eligibility_rule_central_examinations_only"
        ),
        sa.CheckConstraint("basis_code IN ('STATUTORY', 'PBL_RULE')", name="ck_eligibility_rule_basis"),
        sa.CheckConstraint("lapse_code IN ('BLOCK', 'OVERRIDE', 'WARN', 'NOT_REQUIRED')", name="ck_eligibility_rule_lapse"),
        # The law is never overridden and never only a warning (ELA-001).
        sa.CheckConstraint(
            "basis_code <> 'STATUTORY' OR lapse_code IN ('BLOCK', 'NOT_REQUIRED')", name="ck_eligibility_rule_statutory_lapse"
        ),
        sa.CheckConstraint("not_applicable_code IN ('NOT_ALLOWED', 'ALLOWED')", name="ck_eligibility_rule_not_applicable"),
        # A limit on how long, only where "not applicable" is allowed; and nothing to mark where nothing is required.
        sa.CheckConstraint(
            "CASE WHEN not_applicable_max_months IS NULL THEN TRUE "
            "ELSE not_applicable_code = 'ALLOWED' AND not_applicable_max_months BETWEEN 1 AND 120 END",
            name="ck_eligibility_rule_not_applicable_months",
        ),
        sa.CheckConstraint(
            "lapse_code <> 'NOT_REQUIRED' OR not_applicable_code = 'NOT_ALLOWED'", name="ck_eligibility_rule_not_required_marks"
        ),
        # An interval only on an examination, and always on an examination that is required.
        sa.CheckConstraint(
            "CASE WHEN renew_every_months IS NULL THEN NOT kind_is_examination OR lapse_code = 'NOT_REQUIRED' "
            "ELSE kind_is_examination AND renew_every_months BETWEEN 1 AND 240 END",
            name="ck_eligibility_rule_renew_every",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from", name="ck_eligibility_rule_dates"
        ),
        sa.CheckConstraint(
            "CASE WHEN effective_to IS NULL THEN ended_by IS NULL AND ended_at IS NULL AND end_reason IS NULL "
            "ELSE ended_by IS NOT NULL AND ended_at IS NOT NULL AND end_reason IS NOT NULL AND btrim(end_reason) <> '' "
            "AND char_length(end_reason) <= 1000 END",
            name="ck_eligibility_rule_ending",
        ),
        _non_blank("source", 1000, "ck_eligibility_rule_source", nullable=False),
        _non_blank("note", 1000, "ck_eligibility_rule_note", nullable=True),
        _non_blank("create_request_key", 100, "ck_eligibility_rule_create_request_key", nullable=True),
    )
    # No two rules for the same kind, class, type, "applies when" and jurisdiction in effect on the same day.
    # The period is inclusive of both ends; an open end runs on.
    op.execute(
        f"""
        ALTER TABLE {RULE_TABLE} ADD CONSTRAINT ex_eligibility_rule_overlap EXCLUDE USING gist (
            kind_code WITH =,
            class_code WITH =,
            (COALESCE(type_code, '')) WITH =,
            applies_when_code WITH =,
            (COALESCE(jurisdiction_code, '')) WITH =,
            daterange(effective_from, effective_to, '[]') WITH &&
        )
        """
    )
    op.create_index("ix_eligibility_rule_choice", RULE_TABLE, ["kind_code", "class_code", "jurisdiction_code"])


def _create_certificates() -> None:
    op.create_table(
        CERTIFICATE_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_public_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        sa.Column("kind_code", sa.String(length=30), nullable=False),
        # The kind's flags, carried under the composite key below so the checks can read them.
        sa.Column("end_date_optional", sa.Boolean(), nullable=False),
        sa.Column("valid_in_required", sa.Boolean(), nullable=False),
        sa.Column("states_registration", sa.Boolean(), nullable=False),
        # As printed: the policy, registration, certificate or report number. Shown only with
        # EQUIPMENT_IDENTITY_READ (Q6).
        sa.Column("certificate_number", sa.Unicode(length=200), nullable=False),
        # The insurer, the registering authority, or the competent person with their recognition number.
        sa.Column("issued_by", sa.Unicode(length=200), nullable=False),
        # The day it was issued, or the day of the examination.
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        # A permit only: the state it covers, or IN for a national permit.
        sa.Column("valid_in_code", sa.String(length=10), nullable=True),
        # A registration only: as the certificate says.
        sa.Column("registered_as_code", sa.String(length=20), nullable=True),
        sa.Column("certificate_status_code", sa.String(length=20), nullable=False, server_default=sa.text("'RECORDED'")),
        sa.Column("create_request_key", sa.String(length=100), nullable=False),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_reason", sa.Unicode(length=1000), nullable=True),
        sa.Column("withdrawn_by", sa.String(length=36), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("certificate_public_id", name="uq_eligibility_certificate_public_id"),
        sa.UniqueConstraint("create_request_key", name="uq_eligibility_certificate_create_request_key"),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_eligibility_certificate_asset"
        ),
        sa.ForeignKeyConstraint(
            ["kind_code", "end_date_optional", "valid_in_required", "states_registration"],
            [
                f"{KIND_TABLE}.kind_code",
                f"{KIND_TABLE}.end_date_optional",
                f"{KIND_TABLE}.valid_in_required",
                f"{KIND_TABLE}.states_registration",
            ],
            name="fk_eligibility_certificate_kind",
        ),
        sa.ForeignKeyConstraint(
            ["valid_in_code"], [f"{JURISDICTION_TABLE}.jurisdiction_code"], name="fk_eligibility_certificate_valid_in"
        ),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_certificate_recorded_by"),
        sa.ForeignKeyConstraint(["withdrawn_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_certificate_withdrawn_by"),
        sa.CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from", name="ck_eligibility_certificate_dates"
        ),
        sa.CheckConstraint("valid_until IS NOT NULL OR end_date_optional", name="ck_eligibility_certificate_end"),
        sa.CheckConstraint("(valid_in_code IS NOT NULL) = valid_in_required", name="ck_eligibility_certificate_valid_in"),
        sa.CheckConstraint(
            "CASE WHEN states_registration THEN registered_as_code IS NOT NULL AND registered_as_code IN ('TRANSPORT', 'NON_TRANSPORT') "
            "ELSE registered_as_code IS NULL END",
            name="ck_eligibility_certificate_registered_as",
        ),
        sa.CheckConstraint(
            "certificate_status_code IN ('RECORDED', 'WITHDRAWN')", name="ck_eligibility_certificate_status"
        ),
        _withdrawal_check(CERTIFICATE_TABLE, "certificate_status_code", "WITHDRAWN"),
        _non_blank("certificate_number", 200, "ck_eligibility_certificate_number", nullable=False),
        _non_blank("issued_by", 200, "ck_eligibility_certificate_issued_by", nullable=False),
        _non_blank("create_request_key", 100, "ck_eligibility_certificate_create_request_key", nullable=False),
    )
    op.create_index("ix_eligibility_certificate_asset", CERTIFICATE_TABLE, ["equipment_asset_public_id", "kind_code"])


def _create_marks() -> None:
    op.create_table(
        MARK_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mark_public_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        sa.Column("kind_code", sa.String(length=30), nullable=False),
        # The rule in force that allowed it when it was recorded.
        sa.Column("allowed_by_rule_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Unicode(length=1000), nullable=False),
        # The last day it counts; empty where the rule sets no limit.
        sa.Column("until_date", sa.Date(), nullable=True),
        # The business day it was recorded (Asia/Kolkata), from which a rule's limit is counted.
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("mark_status_code", sa.String(length=20), nullable=False, server_default=sa.text("'IN_FORCE'")),
        sa.Column("create_request_key", sa.String(length=100), nullable=False),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_reason", sa.Unicode(length=1000), nullable=True),
        sa.Column("withdrawn_by", sa.String(length=36), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("mark_public_id", name="uq_eligibility_not_applicable_public_id"),
        sa.UniqueConstraint("create_request_key", name="uq_eligibility_not_applicable_create_request_key"),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_eligibility_not_applicable_asset"
        ),
        sa.ForeignKeyConstraint(["kind_code"], [f"{KIND_TABLE}.kind_code"], name="fk_eligibility_not_applicable_kind"),
        sa.ForeignKeyConstraint(["allowed_by_rule_id"], [f"{RULE_TABLE}.id"], name="fk_eligibility_not_applicable_rule"),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_not_applicable_recorded_by"),
        sa.ForeignKeyConstraint(["withdrawn_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_not_applicable_withdrawn_by"),
        sa.CheckConstraint("mark_status_code IN ('IN_FORCE', 'WITHDRAWN')", name="ck_eligibility_not_applicable_status"),
        sa.CheckConstraint("until_date IS NULL OR until_date >= recorded_on", name="ck_eligibility_not_applicable_until"),
        _withdrawal_check(MARK_TABLE, "mark_status_code", "WITHDRAWN"),
        _non_blank("reason", 1000, "ck_eligibility_not_applicable_reason", nullable=False),
        _non_blank("create_request_key", 100, "ck_eligibility_not_applicable_create_request_key", nullable=False),
    )
    # At most one mark in force for an asset and a kind.
    op.create_index(
        "uq_eligibility_not_applicable_in_force",
        MARK_TABLE,
        ["equipment_asset_public_id", "kind_code"],
        unique=True,
        postgresql_where=sa.text("mark_status_code = 'IN_FORCE'"),
    )


def _create_decisions() -> None:
    op.create_table(
        DECISION_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_public_id", sa.String(length=36), nullable=False),
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        sa.Column("asset_version", sa.Integer(), nullable=False),
        sa.Column("site_state_code", sa.String(length=10), nullable=False),
        sa.Column("central_government_site", sa.Boolean(), nullable=False),
        sa.Column("period_from", sa.Date(), nullable=False),
        # Empty: open-ended.
        sa.Column("period_to", sa.Date(), nullable=True),
        # The business day it was judged on (Asia/Kolkata), and when.
        sa.Column("evaluated_on", sa.Date(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        # What asked for it: 8A's requirement or assignment.
        sa.Column("requested_for_type", sa.String(length=50), nullable=True),
        sa.Column("requested_for_public_id", sa.String(length=36), nullable=True),
        sa.Column("overall_code", sa.String(length=30), nullable=False),
        # The day the earliest required cover or "not applicable" mark ends; empty when none ends, or when blocked.
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.UniqueConstraint("decision_public_id", name="uq_eligibility_decision_public_id"),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_eligibility_decision_asset"
        ),
        sa.ForeignKeyConstraint(
            ["site_state_code"], [f"{JURISDICTION_TABLE}.jurisdiction_code"], name="fk_eligibility_decision_site_state"
        ),
        sa.ForeignKeyConstraint(["requested_by"], [f"{USER_TABLE}.public_id"], name="fk_eligibility_decision_requested_by"),
        sa.CheckConstraint(
            "overall_code IN ('ELIGIBLE', 'WARNING', 'BLOCKED', 'OVERRIDE_REQUIRED')", name="ck_eligibility_decision_overall"
        ),
        sa.CheckConstraint("period_to IS NULL OR period_to >= period_from", name="ck_eligibility_decision_period"),
        sa.CheckConstraint("asset_version >= 1", name="ck_eligibility_decision_asset_version"),
        sa.CheckConstraint(
            "(requested_for_type IS NULL) = (requested_for_public_id IS NULL)", name="ck_eligibility_decision_requested_for"
        ),
    )
    op.create_index("ix_eligibility_decision_asset", DECISION_TABLE, ["equipment_asset_public_id"])
    op.create_table(
        RESULT_TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_id", sa.Integer(), nullable=False),
        sa.Column("result_number", sa.Integer(), nullable=False),
        # The asset of the unit the result is about: the machine, a fitted part, or the piece of kit.
        sa.Column("equipment_asset_public_id", sa.String(length=36), nullable=False),
        # Empty for the asset's own check (retired).
        sa.Column("kind_code", sa.String(length=30), nullable=True),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        # Where the rule came from; empty for the baseline.
        sa.Column("rule_jurisdiction_code", sa.String(length=10), nullable=True),
        sa.Column("certificate_id", sa.Integer(), nullable=True),
        sa.Column("mark_id", sa.Integer(), nullable=True),
        sa.Column("outcome_code", sa.String(length=30), nullable=False),
        sa.Column("lapse_code", sa.String(length=20), nullable=True),
        sa.Column("effect_code", sa.String(length=20), nullable=False),
        sa.Column("cover_ends_on", sa.Date(), nullable=True),
        sa.UniqueConstraint("decision_id", "result_number", name="uq_eligibility_decision_result_number"),
        sa.ForeignKeyConstraint(["decision_id"], [f"{DECISION_TABLE}.id"], name="fk_eligibility_decision_result_decision"),
        sa.ForeignKeyConstraint(
            ["equipment_asset_public_id"], [f"{ASSET_TABLE}.asset_public_id"], name="fk_eligibility_decision_result_asset"
        ),
        sa.ForeignKeyConstraint(["kind_code"], [f"{KIND_TABLE}.kind_code"], name="fk_eligibility_decision_result_kind"),
        sa.ForeignKeyConstraint(["rule_id"], [f"{RULE_TABLE}.id"], name="fk_eligibility_decision_result_rule"),
        sa.ForeignKeyConstraint(
            ["rule_jurisdiction_code"], [f"{JURISDICTION_TABLE}.jurisdiction_code"], name="fk_eligibility_decision_result_jurisdiction"
        ),
        sa.ForeignKeyConstraint(["certificate_id"], [f"{CERTIFICATE_TABLE}.id"], name="fk_eligibility_decision_result_certificate"),
        sa.ForeignKeyConstraint(["mark_id"], [f"{MARK_TABLE}.id"], name="fk_eligibility_decision_result_mark"),
        sa.CheckConstraint(
            "outcome_code IN ('VALID', 'RUNS_OUT_SOON', 'RUNS_OUT_IN_PERIOD', 'RUNS_OUT_BEFORE_START', 'RUN_OUT', "
            "'MISSING', 'COPY_MISSING', 'NOT_APPLICABLE', 'RETIRED')",
            name="ck_eligibility_decision_result_outcome",
        ),
        sa.CheckConstraint(
            "effect_code IN ('NONE', 'WARNING', 'OVERRIDE', 'BLOCK')", name="ck_eligibility_decision_result_effect"
        ),
        # The asset's own check has no kind and no rule; every other result has both.
        sa.CheckConstraint(
            "CASE WHEN outcome_code = 'RETIRED' THEN kind_code IS NULL AND rule_id IS NULL "
            "ELSE kind_code IS NOT NULL AND rule_id IS NOT NULL END",
            name="ck_eligibility_decision_result_subject",
        ),
    )
    op.create_index("ix_eligibility_decision_result_asset", RESULT_TABLE, ["equipment_asset_public_id"])


def _seed_first_rules() -> None:
    connection = op.get_bind()
    examinations = {code for code, _label, _end, _valid_in, examination, _registration in KINDS if examination}
    for kind, class_code, type_code, applies_when, months, basis, not_applicable, max_months, source, note in _first_rules():
        connection.execute(
            sa.text(
                f"""
                INSERT INTO {RULE_TABLE} (
                    rule_public_id, kind_code, kind_is_examination, class_code, type_code, applies_when_code,
                    jurisdiction_code, effective_from, renew_every_months, basis_code, lapse_code,
                    not_applicable_code, not_applicable_max_months, source, note
                ) VALUES (
                    :public_id, :kind, :examination, :class_code, :type_code, :applies_when,
                    NULL, :effective_from, :months, :basis, 'BLOCK',
                    :not_applicable, :max_months, :source, :note
                )
                """
            ),
            {
                "public_id": str(uuid4()),
                "kind": kind,
                "examination": kind in examinations,
                "class_code": class_code,
                "type_code": type_code,
                "applies_when": applies_when,
                "effective_from": FIRST_DAY,
                "months": months,
                "basis": basis,
                "not_applicable": not_applicable,
                "max_months": max_months,
                "source": source,
                "note": note,
            },
        )


def _seed_permissions() -> None:
    """Insert each permission row and its role grants, as 20260908_0036 to 0043 do."""
    connection = op.get_bind()
    for permission_code, (description, granted_role_codes) in PERMISSION_SEED.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO authz_permission (public_id, permission_code, description, is_active)
                VALUES (:public_id, :permission_code, :description, TRUE)
                """
            ),
            {"public_id": str(uuid4()), "permission_code": permission_code, "description": description},
        )
        permission_id = connection.execute(
            sa.text("SELECT id FROM authz_permission WHERE permission_code = :permission_code"),
            {"permission_code": permission_code},
        ).scalar_one()
        for role_code in granted_role_codes:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO authz_role_permission (public_id, role_code, permission_id, is_active)
                    VALUES (:public_id, :role_code, :permission_id, TRUE)
                    """
                ),
                {"public_id": str(uuid4()), "role_code": role_code, "permission_id": permission_id},
            )


def downgrade() -> None:
    """Remove the module's tables and its permission. The copies attached to certificates are Slice 9C documents
    in a table this revision did not change, with their files in the store; they are left as they are. The
    documents module of the revision below has no rights entry for them, so nobody can read them (it denies
    an unmapped record type)."""
    connection = op.get_bind()
    codes = list(PERMISSION_SEED)
    connection.execute(
        sa.text(
            "DELETE FROM authz_role_permission WHERE permission_id IN "
            "(SELECT id FROM authz_permission WHERE permission_code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(sa.text("DELETE FROM authz_permission WHERE permission_code = ANY(:codes)"), {"codes": codes})
    for table in (RESULT_TABLE, DECISION_TABLE, MARK_TABLE, CERTIFICATE_TABLE, RULE_TABLE, KIND_TABLE, JURISDICTION_TABLE):
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
