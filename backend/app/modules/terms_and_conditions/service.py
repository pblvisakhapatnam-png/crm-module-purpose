from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.terms_and_conditions.contract import TC_CLAUSE_ALLOWED_BUSINESS_LINES
from app.modules.terms_and_conditions.repository import get_tc_clause_by_public_id, list_tc_clauses
from app.modules.terms_and_conditions.schemas import TermsAndConditionsClauseResponse


class TermsAndConditionsClauseNotFoundError(LookupError):
    pass


class TermsAndConditionsClauseValidationError(ValueError):
    pass


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_business_line(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None

    normalized = cleaned.upper().replace(" ", "_")
    aliases = {
        "EQUIPMENT_HIRING": "HIRING",
        "EQUIPMENT_HIRE": "HIRING",
        "HIRE": "HIRING",
    }
    normalized = aliases.get(normalized, normalized)

    if normalized not in TC_CLAUSE_ALLOWED_BUSINESS_LINES:
        raise TermsAndConditionsClauseValidationError(f"T&C business line is not supported: {value}")
    return normalized


def _normalize_category(value: str | None) -> str | None:
    cleaned = _clean_optional(value)
    return cleaned.lower() if cleaned else None


def list_terms_and_conditions_clauses(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    business_line: str | None = None,
    clause_category: str | None = None,
    active: bool | None = None,
    applies_to_header: bool | None = None,
    applies_to_line: bool | None = None,
    search: str | None = None,
) -> list[TermsAndConditionsClauseResponse]:
    return list_tc_clauses(
        db,
        limit=limit,
        offset=offset,
        business_line=_normalize_business_line(business_line),
        clause_category=_normalize_category(clause_category),
        active=active,
        applies_to_header=applies_to_header,
        applies_to_line=applies_to_line,
        search=_clean_optional(search),
    )


def get_terms_and_conditions_clause(db: Session, public_id: UUID) -> TermsAndConditionsClauseResponse:
    clause = get_tc_clause_by_public_id(db, str(public_id))
    if clause is None:
        raise TermsAndConditionsClauseNotFoundError("T&C clause not found.")
    return clause

