"""UoM converter: factor-based conversion within one category.

Ported from Go ``internal/domain/uom/converter.go``.

Model: every unit has ``factor_to_base`` relative to the base unit of its
OWN category (mass->kg, volume->l, count->pcs, length->m):

    qty_in_target = qty * from_factor / to_factor

Cross-category conversion (kg -> l) is physically meaningless without
density and is forbidden: :class:`IncompatibleCategories` (invariant 2).
"""

import threading
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from canning_erp.domain.uom.entities import Unit
from canning_erp.domain.uom.errors import (
    IncompatibleCategories,
    NegativeQuantity,
    UnitNotFound,
)

#: Warehouse precision: NUMERIC(18,3). ALL conversion results are rounded
#: to 3 decimals BEFORE writing to the DB, otherwise the DB would round
#: itself and allocation sums would drift away from document totals.
#: Round-half-up (not banker's rounding): the warehouse accounting
#: standard, predictable for storekeepers.
DECIMALS = 3

_QUANT = Decimal("0.001")


def round_qty(value: float) -> float:
    """Round half-up to ``DECIMALS`` digits."""
    return float(Decimal(repr(value)).quantize(_QUANT, rounding=ROUND_HALF_UP))


class Converter:
    """Thread-safe unit converter with an in-memory factor cache."""

    def __init__(self) -> None:
        self._units: dict[UUID, Unit] = {}
        self._lock = threading.RLock()

    def load(self, units: list[Unit]) -> None:
        """Replace cached unit definitions (full reload from ``uom_units``)."""
        with self._lock:
            self._units = {u.id: u for u in units}

    def invalidate(self) -> None:
        """Drop the cache (next convert misses until reload)."""
        with self._lock:
            self._units = {}

    def _get(self, unit_id: UUID) -> Unit:
        with self._lock:
            unit = self._units.get(unit_id)
        if unit is None:
            raise UnitNotFound(f"uom unit {unit_id} not found in cache")
        return unit

    def convert(self, qty: float, source: UUID, target: UUID) -> float:
        """Convert ``qty`` from one unit to another within one category."""
        if qty < 0:
            raise NegativeQuantity("quantity must be non-negative")
        src = self._get(source)
        dst = self._get(target)
        if src.category_id != dst.category_id:
            raise IncompatibleCategories(
                "cannot convert between units of different categories"
            )
        return round_qty(qty * src.factor / dst.factor)

    def must_convert(self, qty: float, source: UUID, target: UUID) -> float:
        """Convert letting domain errors propagate (Go MustConvert parity)."""
        return self.convert(qty, source, target)

    def same_category(self, a: UUID, b: UUID) -> bool:
        """True when both units belong to the same category."""
        return self._get(a).category_id == self._get(b).category_id
