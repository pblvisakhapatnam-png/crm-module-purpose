"""Holiday calendar database access (HOL-1). Its own three tables only.

Every write goes through the service, which holds the module's write lock: one lock for the whole calendar, because
it is kept by one or two people and a save replaces a year as a whole. A year and its holidays are read in one
statement, so a read never mixes two versions of a year (the Slice 7D Part 4 lesson, review round 2, F-05).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session
from app.shared.transactions import take_advisory_lock

YEAR_TABLE = "holiday_calendar_year"
HOLIDAY_TABLE = "holiday_calendar_holiday"
STATE_TABLE = "holiday_calendar_holiday_state"

_WRITE_LOCK_KEY = "holiday_calendar.write"


def take_write_lock(db: Session) -> None:
    take_advisory_lock(db, _WRITE_LOCK_KEY)


def _rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in db.execute(text(sql), params or {}).fetchall()]


# The states a holiday names, as a sorted list, read in the same statement as the holiday.
_STATE_CODES = (
    f"COALESCE((SELECT array_agg(s.jurisdiction_code ORDER BY s.jurisdiction_code) FROM {STATE_TABLE} s "
    "WHERE s.holiday_id = h.id), ARRAY[]::varchar[]) AS state_codes"
)

_YEAR_COLUMNS = """
    y.id AS year_id, y.year_public_id, y.calendar_year, y.year_version, y.complete_marked_by,
    marker.display_name AS complete_marked_by_display_name, y.complete_marked_at, y.updated_by,
    updater.display_name AS updated_by_display_name, y.updated_at
"""
_YEAR_JOINS = """
    LEFT JOIN app_user marker ON marker.public_id = y.complete_marked_by
    LEFT JOIN app_user updater ON updater.public_id = y.updated_by
"""
_YEAR_KEYS = (
    "year_id",
    "year_public_id",
    "calendar_year",
    "year_version",
    "complete_marked_by",
    "complete_marked_by_display_name",
    "complete_marked_at",
    "updated_by",
    "updated_by_display_name",
    "updated_at",
)
_HOLIDAY_KEYS = ("holiday_public_id", "holiday_date", "holiday_kind_code", "holiday_name", "applies_to_code", "state_codes")


def list_year_rows(db: Session) -> list[dict[str, Any]]:
    """Every year started, with how many holidays it holds, earliest first."""
    return _rows(
        db,
        f"""
        SELECT {_YEAR_COLUMNS},
               (SELECT count(*) FROM {HOLIDAY_TABLE} h WHERE h.year_id = y.id) AS holiday_count
        FROM {YEAR_TABLE} y
        {_YEAR_JOINS}
        ORDER BY y.calendar_year
        """,
    )


def year_snapshot(db: Session, *, calendar_year: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """A year and its holidays from one statement, holidays earliest first; (None, []) when it is not started."""
    rows = _rows(
        db,
        f"""
        SELECT {_YEAR_COLUMNS},
               h.holiday_public_id, h.holiday_date, h.holiday_kind_code, h.holiday_name, h.applies_to_code,
               {_STATE_CODES}
        FROM {YEAR_TABLE} y
        {_YEAR_JOINS}
        LEFT JOIN {HOLIDAY_TABLE} h ON h.year_id = y.id
        WHERE y.calendar_year = :calendar_year
        ORDER BY h.holiday_date, h.applies_to_code, h.holiday_name, h.id
        """,
        {"calendar_year": calendar_year},
    )
    if not rows:
        return None, []
    year = {key: rows[0][key] for key in _YEAR_KEYS}
    holidays = [{key: row[key] for key in _HOLIDAY_KEYS} for row in rows if row["holiday_public_id"] is not None]
    return year, holidays


def calendar_between(
    db: Session, *, first_day: date, last_day: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The years started among those from `first_day` to `last_day`, and their holidays on those days, from one
    statement: (years, holidays), each earliest first."""
    rows = _rows(
        db,
        f"""
        SELECT y.calendar_year, y.year_version, (y.complete_marked_at IS NOT NULL) AS is_complete,
               h.holiday_public_id, h.holiday_date, h.holiday_kind_code, h.holiday_name, h.applies_to_code,
               {_STATE_CODES}
        FROM {YEAR_TABLE} y
        LEFT JOIN {HOLIDAY_TABLE} h
               ON h.year_id = y.id AND h.holiday_date BETWEEN :first_day AND :last_day
        WHERE y.calendar_year BETWEEN :first_year AND :last_year
        ORDER BY y.calendar_year, h.holiday_date, h.applies_to_code, h.id
        """,
        {"first_day": first_day, "last_day": last_day, "first_year": first_day.year, "last_year": last_day.year},
    )
    years: dict[int, dict[str, Any]] = {}
    holidays: list[dict[str, Any]] = []
    for row in rows:
        years.setdefault(
            int(row["calendar_year"]),
            {"calendar_year": int(row["calendar_year"]), "year_version": int(row["year_version"]), "is_complete": bool(row["is_complete"])},
        )
        if row["holiday_public_id"] is not None:
            holidays.append({key: row[key] for key in _HOLIDAY_KEYS})
    return list(years.values()), holidays


def list_complete_years(db: Session, *, years: list[int]) -> set[int]:
    if not years:
        return set()
    statement = text(
        f"SELECT calendar_year FROM {YEAR_TABLE} WHERE calendar_year IN :years AND complete_marked_at IS NOT NULL"
    ).bindparams(bindparam("years", expanding=True))
    return {int(row[0]) for row in db.execute(statement, {"years": years}).fetchall()}


def insert_year(
    db: Session, *, public_id: str, calendar_year: int, marked_by: str | None, marked_at: datetime | None, user_public_id: str
) -> int:
    return int(
        db.execute(
            text(
                f"""
                INSERT INTO {YEAR_TABLE} (
                    year_public_id, calendar_year, year_version, complete_marked_by, complete_marked_at,
                    created_by, updated_by
                ) VALUES (:public_id, :calendar_year, 1, :marked_by, :marked_at, :user, :user)
                RETURNING id
                """
            ),
            {
                "public_id": public_id,
                "calendar_year": calendar_year,
                "marked_by": marked_by,
                "marked_at": marked_at,
                "user": user_public_id,
            },
        ).scalar_one()
    )


def update_year(
    db: Session,
    *,
    year_id: int,
    expected_version: int,
    marked_by: str | None,
    marked_at: datetime | None,
    user_public_id: str,
) -> int:
    return db.execute(
        text(
            f"""
            UPDATE {YEAR_TABLE}
            SET year_version = year_version + 1, complete_marked_by = :marked_by, complete_marked_at = :marked_at,
                updated_by = :user, updated_at = CURRENT_TIMESTAMP
            WHERE id = :year_id AND year_version = :expected_version
            """
        ),
        {
            "year_id": year_id,
            "expected_version": expected_version,
            "marked_by": marked_by,
            "marked_at": marked_at,
            "user": user_public_id,
        },
    ).rowcount


def delete_holidays(db: Session, *, year_id: int) -> None:
    db.execute(
        text(f"DELETE FROM {STATE_TABLE} WHERE holiday_id IN (SELECT id FROM {HOLIDAY_TABLE} WHERE year_id = :year_id)"),
        {"year_id": year_id},
    )
    db.execute(text(f"DELETE FROM {HOLIDAY_TABLE} WHERE year_id = :year_id"), {"year_id": year_id})


def insert_holiday(
    db: Session,
    *,
    public_id: str,
    year_id: int,
    calendar_year: int,
    holiday_date: date,
    kind_code: str,
    name: str,
    applies_to_code: str,
    state_codes: tuple[str, ...],
) -> None:
    holiday_id = int(
        db.execute(
            text(
                f"""
                INSERT INTO {HOLIDAY_TABLE} (
                    holiday_public_id, year_id, calendar_year, holiday_date, holiday_kind_code, holiday_name, applies_to_code
                ) VALUES (:public_id, :year_id, :calendar_year, :holiday_date, :kind_code, :name, :applies_to_code)
                RETURNING id
                """
            ),
            {
                "public_id": public_id,
                "year_id": year_id,
                "calendar_year": calendar_year,
                "holiday_date": holiday_date,
                "kind_code": kind_code,
                "name": name,
                "applies_to_code": applies_to_code,
            },
        ).scalar_one()
    )
    if state_codes:
        db.execute(
            text(
                f"INSERT INTO {STATE_TABLE} (holiday_id, holiday_date, jurisdiction_code) "
                "VALUES (:holiday_id, :holiday_date, :code)"
            ),
            [{"holiday_id": holiday_id, "holiday_date": holiday_date, "code": code} for code in state_codes],
        )
