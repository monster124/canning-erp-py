"""Base domain error type.

Every domain module raises subclasses of :class:`DomainError`; the
interfaces layer maps them to HTTP statuses in one place (stage P4) so
that SQL texts / stack traces never leak to clients (invariant 9).
"""


class DomainError(Exception):
    """Base class for all domain errors."""

    #: Stable machine-readable code (used later for problem responses).
    code: str = "domain_error"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)
