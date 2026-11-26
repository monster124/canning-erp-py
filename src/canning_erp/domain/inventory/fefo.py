"""FEFO allocation - pure domain logic (no I/O).

Ported from Go ``internal/domain/inventory/fefo.go`` and the pure core
``distributeFEFO`` of ``application/inventory/fefo_service.go``.

Invariant 1: allocations are recorded in the LOT's units (``lot.uom_id``);
the requested quantity is converted via ``conv`` with
``rate = convert(1, req_uom, lot_uom)``. ``SELECT ... FOR UPDATE`` and the
actual write-off live in the repository layer (stage P5); this function is
pure and deterministic.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from canning_erp.domain.inventory.entities import LotStatus, StockLot
from canning_erp.domain.inventory.errors import (
    FEFOAllLotsBlocked,
    FEFOAllLotsExpired,
    FEFOInsufficientStock,
)
from canning_erp.domain.uom.converter import Converter, round_qty
from canning_erp.domain.uom.errors import IncompatibleCategories


@dataclass(slots=True)
class FEFORequest:
    """Input for a FEFO allocation."""

    product_id: UUID
    warehouse_id: UUID
    quantity: float
    uom_id: UUID
    location_id: UUID | None = None
    lot_id: UUID | None = None  # explicit lot choice by the storekeeper
    allow_near_expiry: bool = False
    near_expiry_days: int = 0
    allow_expired: bool = False  # scrap operations only


@dataclass(slots=True)
class FEFOAllocation:
    """A single write-off portion from a specific lot (in LOT units)."""

    product_id: UUID
    lot_id: UUID
    lot_number: str
    quantity: float  # in lot.uom_id units, NOT request units
    uom_id: UUID  # the lot's UoM, NOT the request's
    expiry_date: datetime | None = None
    was_split: bool = False
    is_near_expiry: bool = False


@dataclass(slots=True)
class FEFOWarning:
    """Audit/alert metadata produced during allocation."""

    type: str  # skipped_expired | skipped_quarantine | near_expiry
    lot_id: UUID
    lot_number: str
    message: str
    expiry_date: datetime | None = None


@dataclass(slots=True)
class FEFOResult:
    allocations: list[FEFOAllocation] = field(default_factory=list)
    warnings: list[FEFOWarning] = field(default_factory=list)
    total_allocated: float = 0.0
    total_available: float = 0.0


def _fefo_sort_key(lot: StockLot) -> tuple[bool, datetime, datetime]:
    """expiry ASC NULLS LAST, then received_at ASC (SQL ORDER BY parity)."""
    if lot.expiry_date is None:
        return (True, datetime.max, lot.received_at)
    return (False, lot.expiry_date, lot.received_at)


def distribute_fefo(
    lots: Sequence[StockLot],
    req: FEFORequest,
    near_expiry_days: int,
    conv: Converter | None,
) -> FEFOResult:
    """Distribute ``req.quantity`` over ``lots`` FEFO-first.

    The 4-argument contract is fixed by the spec (invariant 1).
    ``conv`` may be ``None`` - then no conversion is performed and the
    request is treated in the lots' units (rate = 1).
    """
    result = FEFOResult()
    ordered = sorted(lots, key=_fefo_sort_key)

    rate = 1.0
    if conv is not None and ordered and req.uom_id != ordered[0].uom_id:
        if not conv.same_category(req.uom_id, ordered[0].uom_id):
            raise IncompatibleCategories("request uom != lot uom (kg->l not allowed)")
        rate = conv.convert(1, req.uom_id, ordered[0].uom_id)
        if rate <= 0:
            raise IncompatibleCategories(f"uom rate must be positive, got {rate}")

    remaining = req.quantity  # in REQUEST units
    now = datetime.now()
    near_threshold = now + timedelta(days=near_expiry_days)

    skipped_expired = 0
    skipped_blocked = 0

    for lot in ordered:
        result.total_available += lot.qty_available

        # --- Edge 1: expired lot ---
        if lot.expiry_date is not None and lot.expiry_date < now:
            if not req.allow_expired:
                skipped_expired += 1
                result.warnings.append(
                    FEFOWarning(
                        type="skipped_expired",
                        lot_id=lot.id,
                        lot_number=lot.lot_number,
                        message=(
                            f"lot {lot.lot_number} expired on "
                            f"{lot.expiry_date:%Y-%m-%d}, skipped"
                        ),
                        expiry_date=lot.expiry_date,
                    )
                )
                continue
            # allow_expired=True (scrap): write off with a warning
            result.warnings.append(
                FEFOWarning(
                    type="skipped_expired",
                    lot_id=lot.id,
                    lot_number=lot.lot_number,
                    message=(
                        f"lot {lot.lot_number} is expired "
                        f"({lot.expiry_date:%Y-%m-%d}), allocated for scrap"
                    ),
                    expiry_date=lot.expiry_date,
                )
            )

        # --- Edge 2: blocked / quarantine ---
        if lot.status in (LotStatus.QUARANTINE, LotStatus.BLOCKED):
            skipped_blocked += 1
            result.warnings.append(
                FEFOWarning(
                    type="skipped_quarantine",
                    lot_id=lot.id,
                    lot_number=lot.lot_number,
                    message=f"lot {lot.lot_number} is {lot.status.value}, skipped",
                )
            )
            continue

        # --- Edge 3: near expiry ---
        is_near = bool(
            lot.expiry_date is not None
            and lot.expiry_date < near_threshold
            and lot.expiry_date > now
        )
        if is_near and lot.expiry_date is not None:
            days_left = int((lot.expiry_date - now).total_seconds() // 86400)
            result.warnings.append(
                FEFOWarning(
                    type="near_expiry",
                    lot_id=lot.id,
                    lot_number=lot.lot_number,
                    message=(
                        f"lot {lot.lot_number} expires in {days_left} days "
                        f"({lot.expiry_date:%Y-%m-%d})"
                    ),
                    expiry_date=lot.expiry_date,
                )
            )
            if not req.allow_near_expiry:
                continue

        if remaining <= 0:
            break

        lot_avail_in_req = lot.qty_available / rate
        take = lot_avail_in_req
        was_split = False
        if take > remaining:
            take = remaining
            was_split = True
        if take <= 0:
            continue

        # Allocation is recorded in LOT units (invariant 1)
        result.allocations.append(
            FEFOAllocation(
                product_id=lot.product_id,
                lot_id=lot.id,
                lot_number=lot.lot_number,
                quantity=round_qty(take * rate),
                uom_id=lot.uom_id,
                expiry_date=lot.expiry_date,
                was_split=was_split,
                is_near_expiry=is_near,
            )
        )
        remaining -= take

    result.total_allocated = req.quantity - remaining

    # --- Edge 4: not enough stock ---
    if remaining > 0:
        if skipped_expired > 0 and skipped_expired == len(ordered):
            raise FEFOAllLotsExpired(
                f"all {len(ordered)} lots are expired for product {req.product_id}"
            )
        if skipped_blocked > 0 and skipped_blocked == len(ordered):
            raise FEFOAllLotsBlocked(
                f"all {len(ordered)} lots are blocked for product {req.product_id}"
            )
        raise FEFOInsufficientStock(
            f"insufficient stock: product {req.product_id}, "
            f"requested {req.quantity:.3f}, available {result.total_available:.3f}, "
            f"short by {remaining:.3f}"
        )

    return result
