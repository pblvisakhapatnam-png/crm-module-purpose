"""The currencies an amount may be recorded in, held in one place.

INR is the default and the operating currency (Q-08, ADR-023). The owner's decision of 4 October 2026 (TB1-600)
keeps the door open for work in neighbouring countries: an offer or an amendment may be recorded in one of the
currencies below, and nothing else. Add a currency here and in `frontend/src/components/currency.ts`, which offers
the same list on screen.

Amounts are never converted. A report totals each currency separately (`reports/service.py`).
"""

from __future__ import annotations

DEFAULT_CURRENCY = "INR"
OPERATING_CURRENCIES: tuple[str, ...] = (DEFAULT_CURRENCY, "USD", "GBP", "EUR")

UNSUPPORTED_CURRENCY_MESSAGE = f"Currency must be one of {', '.join(OPERATING_CURRENCIES)}."


def currency_code_key(value: str | None) -> str:
    """The code as two amounts are compared by: trimmed and upper-cased, INR when none is given - what
    `operating_currency` stores. A row saved before TB1-600 may still hold its code in another case."""
    return (value or DEFAULT_CURRENCY).strip().upper()


def operating_currency(value: str | None) -> str:
    """Return the code trimmed and upper-cased, INR when none is given.

    Raises ValueError with UNSUPPORTED_CURRENCY_MESSAGE for any code not on the list; each module turns that into
    its own validation error.
    """
    currency = currency_code_key(value)
    if currency not in OPERATING_CURRENCIES:
        raise ValueError(UNSUPPORTED_CURRENCY_MESSAGE)
    return currency
