"""Physical table, constraint and index names for the published authority store.

PF-1A-E2-B sections 4, 5.1 and 5.6.

THIS MODULE NAMES THINGS. IT DECIDES NOTHING.

Every semantic question - effectiveness, closure, activity, retraction
validity, correction precedence, overlap, ranking, scope, evaluator and
temporal semantics - belongs to the PF-1A-E2-A kernel and is not restated,
approximated or pre-validated anywhere in this package (E2-B 5.2, 5.6).

FOUR FAMILIES, THREE PHYSICAL ROLES EACH (5.1):

    stable identity table   one row per stable object. Identity only, never
                            versioned, never carrying business meaning.
    version table           one row per IMMUTABLE published version.
    retraction table        append-only retraction assertions for that family.

WHY A SEPARATE RETRACTION TABLE PER FAMILY rather than one polymorphic table:
section 5.6 requires a foreign key from a retraction row to the STABLE
IDENTITY of the object it retracts (fixture B2-02). One shared table would
need either a nullable foreign key per family plus a discriminator CHECK -
an extra structural constraint section 5.6 does not list, and section 5.7
warns that any unlisted constraint changes a fixture's class - or no usable
foreign key at all. Four single-target foreign keys keep the constraint set
exactly the one 5.6 enumerates.

NAMING (section 4). The Application/Login Role table is `role`. A Business
Authority Role is `authz_business_authority_role`: a DIFFERENT table, a
DIFFERENT identifier space, and there is deliberately no foreign key, join,
view, mapping table or code equality between the two.
"""

from __future__ import annotations

from typing import Final

from app.modules.authorization.business_authority.contract import (
    BUSINESS_AUTHORITY,
    BUSINESS_AUTHORITY_ASSIGNMENT,
    BUSINESS_AUTHORITY_ROLE,
    BUSINESS_AUTHORITY_RULE,
)

# ---------------------------------------------------------------------------
# Table names
# ---------------------------------------------------------------------------

BA_AUTHORITY_TABLE: Final = "authz_business_authority"
BA_AUTHORITY_VERSION_TABLE: Final = "authz_business_authority_version"
BA_AUTHORITY_RETRACTION_TABLE: Final = "authz_business_authority_retraction"

BA_ROLE_TABLE: Final = "authz_business_authority_role"
BA_ROLE_VERSION_TABLE: Final = "authz_business_authority_role_version"
BA_ROLE_RETRACTION_TABLE: Final = "authz_business_authority_role_retraction"

BA_RULE_TABLE: Final = "authz_business_authority_rule"
BA_RULE_VERSION_TABLE: Final = "authz_business_authority_rule_version"
BA_RULE_RETRACTION_TABLE: Final = "authz_business_authority_rule_retraction"

BA_ASSIGNMENT_TABLE: Final = "authz_business_authority_assignment"
BA_ASSIGNMENT_VERSION_TABLE: Final = "authz_business_authority_assignment_version"
BA_ASSIGNMENT_RETRACTION_TABLE: Final = "authz_business_authority_assignment_retraction"


class FamilyTables:
    """The three physical tables of one object family."""

    __slots__ = ("family", "stable", "version", "retraction")

    def __init__(self, family: str, stable: str, version: str, retraction: str) -> None:
        self.family = family
        self.stable = stable
        self.version = version
        self.retraction = retraction


# The ONE mapping from a provider-neutral object family to physical tables.
# Every repository read resolves its tables through this registry, so an
# unknown family is rejected explicitly instead of being interpolated into
# SQL (attack surface 25).
FAMILY_TABLES: Final[dict[str, FamilyTables]] = {
    BUSINESS_AUTHORITY: FamilyTables(
        BUSINESS_AUTHORITY,
        BA_AUTHORITY_TABLE,
        BA_AUTHORITY_VERSION_TABLE,
        BA_AUTHORITY_RETRACTION_TABLE,
    ),
    BUSINESS_AUTHORITY_ROLE: FamilyTables(
        BUSINESS_AUTHORITY_ROLE,
        BA_ROLE_TABLE,
        BA_ROLE_VERSION_TABLE,
        BA_ROLE_RETRACTION_TABLE,
    ),
    BUSINESS_AUTHORITY_RULE: FamilyTables(
        BUSINESS_AUTHORITY_RULE,
        BA_RULE_TABLE,
        BA_RULE_VERSION_TABLE,
        BA_RULE_RETRACTION_TABLE,
    ),
    BUSINESS_AUTHORITY_ASSIGNMENT: FamilyTables(
        BUSINESS_AUTHORITY_ASSIGNMENT,
        BA_ASSIGNMENT_TABLE,
        BA_ASSIGNMENT_VERSION_TABLE,
        BA_ASSIGNMENT_RETRACTION_TABLE,
    ),
}

ALL_STORE_TABLES: Final[tuple[str, ...]] = tuple(
    name
    for tables in FAMILY_TABLES.values()
    for name in (tables.stable, tables.version, tables.retraction)
)

# Child-before-parent order, for the deterministic test-fixture teardown that
# must leave no residual rows. There is deliberately no production delete
# path (acceptance criterion R).
STORE_TABLES_CHILD_FIRST: Final[tuple[str, ...]] = tuple(
    name
    for tables in FAMILY_TABLES.values()
    for name in (tables.retraction, tables.version)
) + tuple(tables.stable for tables in FAMILY_TABLES.values())

# ---------------------------------------------------------------------------
# Constraint and index names
# ---------------------------------------------------------------------------
# Abbreviated to `ba_` because PostgreSQL caps an identifier at 63 characters
# and the fully spelled table names leave no room. The TABLE names stay
# fully spelled, which is where section 4's legibility requirement applies.

CK_PUBLICATION_REFERENCE_TYPE: Final = "ck_ba_{short}_publication_reference_type"
CK_INTERVAL: Final = "ck_ba_{short}_version_interval"
CK_ASSIGNMENT_TARGET_XOR: Final = "ck_ba_assignment_version_target_xor"

UQ_STABLE_OBJECT_ID: Final = "uq_ba_{short}_object_id"
UQ_VERSION_IDENTITY: Final = "uq_ba_{short}_version_object_version"

FK_VERSION_PARENT: Final = "fk_ba_{short}_version_object_id"
FK_RETRACTION_PARENT: Final = "fk_ba_{short}_retraction_object_id"
FK_RULE_ROLE_REFERENCE: Final = "fk_ba_rule_version_role_reference"
FK_RULE_AUTHORITY_REFERENCE: Final = "fk_ba_rule_version_authority_reference"
FK_ASSIGNMENT_ROLE_REFERENCE: Final = "fk_ba_assignment_version_role_reference"

IX_AUTHORITY_CODE: Final = "ix_ba_authority_version_authority_code"
IX_RULE_AUTHORITY_REFERENCE: Final = "ix_ba_rule_version_authority_reference"
IX_ASSIGNMENT_ROLE_REFERENCE: Final = "ix_ba_assignment_version_role_reference"
IX_RETRACTION_OBJECT_ID: Final = "ix_ba_{short}_retraction_object_id"

# The per-family token used in the templates above.
FAMILY_SHORT_NAME: Final[dict[str, str]] = {
    BUSINESS_AUTHORITY: "authority",
    BUSINESS_AUTHORITY_ROLE: "role",
    BUSINESS_AUTHORITY_RULE: "rule",
    BUSINESS_AUTHORITY_ASSIGNMENT: "assignment",
}
