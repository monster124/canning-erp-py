"""UoM value objects (parity with Go internal/domain/uom)."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Unit:
    """A unit definition as loaded from ``uom_units``."""

    id: UUID
    category_id: UUID
    code: str
    factor: float  # factor_to_base within the unit's category


@dataclass(frozen=True, slots=True)
class ProductUOMs:
    """The three unit roles configured on a product.

    MRP and goods receipt reduce everything to ``inventory_uom_id``
    (invariant 2).
    """

    product_id: UUID
    base_uom_id: UUID
    inventory_uom_id: UUID
    procurement_uom_id: UUID | None = None
