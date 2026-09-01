"""Domain exceptions. The API layer maps each to a stable HTTP status."""

from __future__ import annotations


class RevynError(Exception):
    """Base class for every expected failure raised by Revyn."""

    status_code = 400
    code = "revyn_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(RevynError):
    status_code = 404
    code = "not_found"


class ConflictError(RevynError):
    status_code = 409
    code = "conflict"


class InvalidTransitionError(ConflictError):
    code = "invalid_transition"


class PolicyViolationError(RevynError):
    status_code = 422
    code = "policy_violation"


class GatewayError(RevynError):
    status_code = 502
    code = "gateway_error"


class AmbiguousGatewayStateError(GatewayError):
    """Raised when a financial call did not resolve; verify before any retry."""

    code = "gateway_state_ambiguous"
