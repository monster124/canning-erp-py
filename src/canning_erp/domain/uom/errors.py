"""UoM domain errors (parity with Go internal/domain/uom/converter.go)."""

from canning_erp.domain.errors import DomainError


class IncompatibleCategories(DomainError):
    """Cross-category conversion (e.g. kg to l) is physically meaningless."""

    code = "uom_incompatible_categories"


class UnitNotFound(DomainError):
    """Unit is missing from the (tenant) converter cache."""

    code = "uom_unit_not_found"


class NegativeQuantity(DomainError):
    """Quantity must be non-negative."""

    code = "uom_negative_quantity"
