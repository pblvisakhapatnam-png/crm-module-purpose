"""PF-1A-E2-A - Business Authority resolution contract and pure domain kernel.

This subpackage answers exactly one question, deterministically and fail
closed (PF_1A_E2_A section 2):

    At a specified authoritative instant, does this authenticated application
    actor hold this Business Authority (identified by `authority_code`) for
    this business context, under the published authority configuration and the
    canonical HR/organisation state - and what immutable evidence proves why?

FOUR CONCEPTS THAT MUST NEVER BE COLLAPSED (PF_1A_E2_A section 4):

    1. Application / Login Role       the six transitional `role` table codes.
                                      Confer NO business authority, ever.
    2. Application Permission         the 31 PF-1A-E1 codes in
                                      `app.modules.authorization.contract`.
    3. Business Authority Role        a configurable business grouping. NOT the
                                      `role` table; its code space is separate.
    4. Business Authority             a named capability identified by
                                      `authority_code`.

Nothing in this subpackage imports an E1 role constant or an E1 permission
constant, and no Business Authority is ever derived, defaulted or inferred
from an Application/Login Role - including ADMIN (PF_1A_E2_A section 6).

The kernel is PURE: no database session, no SQL, no HTTP, no environment read,
no clock read, no framework concern. It is deterministic from the explicit
instant, the explicit request and the explicit port results (PF_1A_E2_A 10.3).
Only `resolve_current_authority` reads a clock, and it does so once
(PF_1A_E2_A 10.1, 11.1).

This package contains NO write path to published authority configuration. The
E2 authority world is read-only in production terms; governed change belongs
to PF-1A-E3 (PF_1A_E2_A section 5).
"""
