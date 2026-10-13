"""The module's error vocabulary, which routes.py maps to HTTP statuses."""

from __future__ import annotations


class AssignmentNotFoundError(LookupError):
    """404."""


class AssignmentValidationError(ValueError):
    """422: refused, with the reason in plain words."""


class AssignmentConflictError(ValueError):
    """409: someone changed it since it was read; a machine, piece or unit is taken; a warning was not accepted;
    or a request key was used for something else."""


class AssignmentForbiddenError(PermissionError):
    """403: the action needs a permission the caller does not hold (setting a billing cycle)."""
