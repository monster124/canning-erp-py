"""Inventory entities: lots, movements, balances.

Ported from Go ``internal/domain/inventory/inventory.go``.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class MovementType(StrEnum):
    RECEIPT = "receipt"
    PRODUCTION_IN = "production_in"
    ISSUE = "issue"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ADJUSTMENT_IN = "adjustment_in"
    ADJUSTMENT_OUT = "adjustment_out"
    SCRAP = "scrap"
    RETURN_IN = "return_in"


class LotStatus(StrEnum):
    ACTIVE = "active"
    QUARANTINE = "quarantine"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    DEPLETED = "depleted"


@dataclass(slots=True)
class StockLot:
    """A stock lot: the atomic unit of warehouse accounting and FEFO."""

    product_id: UUID
    warehouse_id: UUID
    uom_id: UUID
    id: UUID = field(default_factory=uuid4)
    location_id: UUID = field(default_factory=uuid4)
    lot_number: str = ""
    qty_received: float = 0.0
    qty_available: float = 0.0
    qty_reserved: float = 0.0
    production_date: datetime | None = None
    expiry_date: datetime | None = None
    received_at: datetime = field(default_factory=datetime.now)
    supplier_id: UUID | None = None
    supplier_lot: str = ""
    status: LotStatus = LotStatus.ACTIVE
    quality_certificate: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    updated_by: str = ""


@dataclass(slots=True)
class StockMovement:
    """An immutable stock movement record (audit trail)."""

    movement_type: MovementType
    product_id: UUID
    uom_id: UUID
    quantity: float
    id: int = 0
    lot_id: UUID | None = None
    from_warehouse_id: UUID | None = None
    to_warehouse_id: UUID | None = None
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    document_id: UUID | None = None
    document_type: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = ""


@dataclass(slots=True)
class StockBalance:
    """Aggregated balance for product/warehouse/location/uom."""

    product_id: UUID
    warehouse_id: UUID
    location_id: UUID
    uom_id: UUID
    qty_on_hand: float = 0.0
    qty_reserved: float = 0.0
    qty_available: float = 0.0
    last_movement_at: datetime | None = None
