"""Provider-neutral canonical HR / organisation reference CONTRACT.

This package holds PORTS and CANONICAL DTOs only. It deliberately contains no
provider, no persistence, no route and no adapter.

Why it is not inside `authorization/`: the HR / Organisation reference is not
an Authorization-owned capability. ADR-026, ADR-032 and `RMR-001` place
ownership with the Employee Master / HR-reference capability (Phase 1: Plum
basic facts plus a governed SharePoint-backed interim structured source,
composed behind an adapter; eventually a `NEW_SHARED_PLATFORM` master).
Placing the canonical port under `authorization/` would misrepresent that
ownership. See PF_1A_E2_A section 20, which records this as an engineering
layout decision with two defensible answers and requires the choice to be
recorded in the implementation handoff.

Nothing here may leak provider detail: no SharePoint List Item ID, no
SharePoint column name, no Plum field/table name, no raw provider timestamp,
no Source Binding record, no `provider_code`, and no employee name used as
identity (PF_1A_E2_A section 7).
"""
