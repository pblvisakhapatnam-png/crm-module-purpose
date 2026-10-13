"""Authority-specific parameter evaluation.

PF-1A-E2-A section 13.

There is NO universal monetary schema: different authorities genuinely need
different parameter shapes. This module is an evaluator REGISTRY - each
`parameter_evaluator_type` has a typed, schema-validated `parameter_payload`
and a deterministic evaluation function over the business context's declared
facts.

The four types below are examples of the MECHANISM, not a promise of the
production catalogue.

NO EXECUTABLE EXPRESSION LANGUAGE. There is no eval, no exec, no user-authored
code, no script, no SQL, no lambda string, no regex-as-policy, no template
expansion and no other Turing-complete or injection-capable condition
mechanism anywhere in this module. Conditions are declarative DATA interpreted
by the registered, reviewed evaluator code below (attack surface 26).

THE DISTINCTION THAT MUST NOT BLUR (F-10.3-DC-01). A unit, currency or basis
INCOMPATIBILITY between the stored payload and the supplied fact is MALFORMED
EVALUATOR INPUT, not a comparison that came out false. It fails closed with
EVALUATOR_FACTS_INVALID, it is never coerced or converted implicitly, and it
is NEVER reported as EVALUATOR_CONDITION_NOT_SATISFIED.
EVALUATOR_CONDITION_NOT_SATISFIED requires that every required fact was
present, correctly typed AND unit/currency/basis-compatible, so the declared
comparison was actually performed and legitimately returned false.

BOUNDARY SEMANTICS ARE EXPLICIT. A payload naming a bound without stating its
inclusivity is malformed; "lower_limit"/"upper_limit" with implied inclusivity
is forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.modules.authorization.business_authority.contract import (
    EVALUATOR_CONDITION_NOT_SATISFIED,
    EVALUATOR_EXACT_VALUE_SET,
    EVALUATOR_FACTS_INVALID,
    EVALUATOR_NONE,
    EVALUATOR_NUMERIC_BAND,
    EVALUATOR_PAYLOAD_INVALID,
    EVALUATOR_PERCENTAGE_BAND,
    EVALUATOR_UNKNOWN,
)

_NUMERIC_TYPES = (int, float, Decimal)


@dataclass(frozen=True)
class EvaluatorResult:
    """The outcome of evaluating one rule's parameters.

    Three genuinely different answers, exactly as for scope:
      satisfied            the declared condition holds;
      not-satisfied        a WELL-FORMED evaluation that legitimately returned
                           false - ordinary nonqualification;
      defect               unknown type, malformed payload, or malformed
                           supplied facts - fail closed.
    """

    satisfied: bool
    evaluator_type: str | None = None
    nonqualification_reason: str | None = None
    defect_reason: str | None = None
    detail: str = ""
    decisive_comparison: str = ""

    @property
    def is_defect(self) -> bool:
        return self.defect_reason is not None


def _payload_invalid(evaluator_type: str, detail: str) -> EvaluatorResult:
    return EvaluatorResult(
        satisfied=False,
        evaluator_type=evaluator_type,
        defect_reason=EVALUATOR_PAYLOAD_INVALID,
        detail=detail,
    )


def _facts_invalid(evaluator_type: str, detail: str) -> EvaluatorResult:
    return EvaluatorResult(
        satisfied=False,
        evaluator_type=evaluator_type,
        defect_reason=EVALUATOR_FACTS_INVALID,
        detail=detail,
    )


def _not_satisfied(evaluator_type: str, comparison: str) -> EvaluatorResult:
    return EvaluatorResult(
        satisfied=False,
        evaluator_type=evaluator_type,
        nonqualification_reason=EVALUATOR_CONDITION_NOT_SATISFIED,
        detail="the declared condition was evaluated and legitimately not met",
        decisive_comparison=comparison,
    )


def _satisfied(evaluator_type: str, comparison: str) -> EvaluatorResult:
    return EvaluatorResult(
        satisfied=True, evaluator_type=evaluator_type, decisive_comparison=comparison
    )


def _is_number(value: Any) -> bool:
    # `bool` is a subclass of `int` in Python. A boolean is not an amount, and
    # silently accepting one would be an implicit coercion.
    return isinstance(value, _NUMERIC_TYPES) and not isinstance(value, bool)


def _read_bound(payload: dict[str, Any], bound: str) -> tuple[Any, Any, str | None]:
    """Read one bound and its MANDATORY explicit inclusivity flag."""

    value = payload.get(bound)
    inclusive_key = f"{bound}_inclusive"

    if value is None:
        if inclusive_key in payload:
            return None, None, f"{bound} is absent but {inclusive_key} is declared"
        return None, None, None

    if not _is_number(value):
        return None, None, f"{bound} is not a number"

    if inclusive_key not in payload:
        return None, None, f"{bound} is declared without its explicit {inclusive_key} flag"

    inclusive = payload[inclusive_key]
    if not isinstance(inclusive, bool):
        return None, None, f"{inclusive_key} is not an explicit boolean"

    return value, inclusive, None


def _evaluate_band(
    evaluator_type: str,
    payload: Any,
    facts: dict[str, Any],
    qualifier_key: str,
) -> EvaluatorResult:
    """Shared band evaluation for NUMERIC_BAND (unit) and PERCENTAGE_BAND (basis)."""

    if not isinstance(payload, dict):
        return _payload_invalid(evaluator_type, "parameter_payload is not an object")

    fact_name = payload.get("fact")
    if not isinstance(fact_name, str) or not fact_name:
        return _payload_invalid(evaluator_type, "parameter_payload names no business fact")

    declared_qualifier = payload.get(qualifier_key)
    if not isinstance(declared_qualifier, str) or not declared_qualifier:
        return _payload_invalid(
            evaluator_type, f"parameter_payload declares no explicit {qualifier_key}"
        )

    lower, lower_inclusive, lower_error = _read_bound(payload, "lower")
    if lower_error is not None:
        return _payload_invalid(evaluator_type, lower_error)
    upper, upper_inclusive, upper_error = _read_bound(payload, "upper")
    if upper_error is not None:
        return _payload_invalid(evaluator_type, upper_error)

    if lower is None and upper is None:
        return _payload_invalid(evaluator_type, "a band declares neither a lower nor an upper bound")

    if fact_name not in facts:
        return _facts_invalid(evaluator_type, f"required business fact {fact_name!r} is absent")

    fact = facts[fact_name]
    if not isinstance(fact, dict):
        return _facts_invalid(
            evaluator_type,
            f"business fact {fact_name!r} is not a declared value/{qualifier_key} pair",
        )

    fact_value = fact.get("value")
    if not _is_number(fact_value):
        return _facts_invalid(evaluator_type, f"business fact {fact_name!r} has no numeric value")

    fact_qualifier = fact.get(qualifier_key)
    if not isinstance(fact_qualifier, str) or not fact_qualifier:
        return _facts_invalid(
            evaluator_type, f"business fact {fact_name!r} declares no explicit {qualifier_key}"
        )

    if fact_qualifier != declared_qualifier:
        # MALFORMED INPUT, never a false comparison. Nothing is coerced or
        # converted implicitly (section 13, F-10.3-DC-01).
        return _facts_invalid(
            evaluator_type,
            f"business fact {fact_name!r} supplies {qualifier_key} {fact_qualifier!r} "
            f"but the payload declares {declared_qualifier!r}",
        )

    comparison = (
        f"{fact_name}={fact_value} {declared_qualifier}; "
        f"lower={lower} inclusive={lower_inclusive}; upper={upper} inclusive={upper_inclusive}"
    )

    if lower is not None:
        if lower_inclusive:
            if fact_value < lower:
                return _not_satisfied(evaluator_type, comparison)
        elif fact_value <= lower:
            return _not_satisfied(evaluator_type, comparison)

    if upper is not None:
        if upper_inclusive:
            if fact_value > upper:
                return _not_satisfied(evaluator_type, comparison)
        elif fact_value >= upper:
            return _not_satisfied(evaluator_type, comparison)

    return _satisfied(evaluator_type, comparison)


def _evaluate_none(payload: Any, facts: dict[str, Any]) -> EvaluatorResult:
    """NONE: no parameters; the rule is scope-only."""

    if payload not in (None, {}):
        return _payload_invalid(
            EVALUATOR_NONE, "a NONE evaluator must carry no parameter payload"
        )
    return _satisfied(EVALUATOR_NONE, "no parameter condition is declared")


def _evaluate_numeric_band(payload: Any, facts: dict[str, Any]) -> EvaluatorResult:
    return _evaluate_band(EVALUATOR_NUMERIC_BAND, payload, facts, "unit")


def _evaluate_percentage_band(payload: Any, facts: dict[str, Any]) -> EvaluatorResult:
    return _evaluate_band(EVALUATOR_PERCENTAGE_BAND, payload, facts, "basis")


def _evaluate_exact_value_set(payload: Any, facts: dict[str, Any]) -> EvaluatorResult:
    """EXACT_VALUE_SET: membership in an enumerated set of canonical values."""

    evaluator_type = EVALUATOR_EXACT_VALUE_SET

    if not isinstance(payload, dict):
        return _payload_invalid(evaluator_type, "parameter_payload is not an object")

    fact_name = payload.get("fact")
    if not isinstance(fact_name, str) or not fact_name:
        return _payload_invalid(evaluator_type, "parameter_payload names no business fact")

    values = payload.get("values")
    if not isinstance(values, (list, tuple)) or not values:
        return _payload_invalid(evaluator_type, "parameter_payload declares no non-empty value set")
    if not all(isinstance(value, str) for value in values):
        return _payload_invalid(evaluator_type, "the declared value set is not a set of canonical strings")

    if fact_name not in facts:
        return _facts_invalid(evaluator_type, f"required business fact {fact_name!r} is absent")

    fact = facts[fact_name]
    if not isinstance(fact, str):
        return _facts_invalid(
            evaluator_type, f"business fact {fact_name!r} is not a canonical string value"
        )

    comparison = f"{fact_name}={fact!r} in {sorted(values)!r}"
    if fact in values:
        return _satisfied(evaluator_type, comparison)
    return _not_satisfied(evaluator_type, comparison)


# The registry. Selection is by EXACT match on `parameter_evaluator_type` -
# never by prefix, fuzzy match or fallback - and is total over the registered
# types. An unregistered type fails closed with EVALUATOR_UNKNOWN; it is never
# treated as satisfied and never silently skipped (attack surface 27).
_REGISTRY = {
    EVALUATOR_NONE: _evaluate_none,
    EVALUATOR_NUMERIC_BAND: _evaluate_numeric_band,
    EVALUATOR_PERCENTAGE_BAND: _evaluate_percentage_band,
    EVALUATOR_EXACT_VALUE_SET: _evaluate_exact_value_set,
}


def evaluate(
    parameter_evaluator_type: str | None,
    parameter_payload: Any,
    declared_facts: dict[str, Any],
) -> EvaluatorResult:
    """Evaluate a rule's declared parameter condition against the supplied facts.

    Payload validation is AUTHORITATIVE HERE and runs at evaluation time
    against the published payload, regardless of what any store validated at
    write time.
    """

    evaluator = _REGISTRY.get(parameter_evaluator_type)  # type: ignore[arg-type]
    if evaluator is None:
        return EvaluatorResult(
            satisfied=False,
            evaluator_type=parameter_evaluator_type,
            defect_reason=EVALUATOR_UNKNOWN,
            detail=f"parameter_evaluator_type {parameter_evaluator_type!r} is not registered",
        )

    return evaluator(parameter_payload, declared_facts)
