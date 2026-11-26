"""Warehouse documents: receipt / issue / transfer / count.

Ported from Go ``internal/domain/inventory/documents.go``.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class DocStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ReceiptDocument:
    supplier_id: UUID
    warehouse_id: UUID
    id: UUID = field(default_factory=uuid4)
    doc_number: str = ""
    doc_date: datetime = field(default_factory=datetime.now)
    status: DocStatus = DocStatus.DRAFT
    supplier_doc_number: str = ""
    supplier_doc_date: datetime | None = None
    notes: str = ""
    created_by: str = ""
    updated_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class ReceiptLine:
    receipt_id: UUID
    product_id: UUID
    quantity: float
    uom_id: UUID
    lot_number: str
    location_id: UUID
    id: UUID = field(default_factory=uuid4)
    line_no: int = 0
    production_date: datetime | None = None
    expiry_date: datetime | None = None
    unit_cost: float | None = None
    notes: str = ""
    created_by: str = ""
    updated_by: str = ""


@dataclass(slots=True)
class IssueDocument:
    warehouse_id: UUID
    id: UUID = field(default_factory=uuid4)
    doc_number: str = ""
    doc_date: datetime = field(default_factory=datetime.now)
    status: DocStatus = DocStatus.DRAFT
    notes: str = ""
    created_by: str = ""
    updated_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class IssueLine:
    issue_id: UUID
    product_id: UUID
    quantity: float
    uom_id: UUID
    id: UUID = field(default_factory=uuid4)
    line_no: int = 0
    lot_id: UUID | None = None
    created_by: str = ""
    updated_by: str = ""


@dataclass(slots=True)
class TransferDocument:
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    id: UUID = field(default_factory=uuid4)
    doc_number: str = ""
    status: DocStatus = DocStatus.DRAFT
    notes: str = ""
    created_by: str = ""
    updated_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class TransferLine:
    transfer_id: UUID
    product_id: UUID
    lot_id: UUID
    quantity: float
    uom_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    id: UUID = field(default_factory=uuid4)
    line_no: int = 0


@dataclass(slots=True)
class CountSheet:
    warehouse_id: UUID
    id: UUID = field(default_factory=uuid4)
    doc_number: str = ""
    status: DocStatus = DocStatus.DRAFT
    notes: str = ""
    created_by: str = ""
    updated_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class CountLine:
    sheet_id: UUID
    product_id: UUID
    id: UUID = field(default_factory=uuid4)
    line_no: int = 0
    system_qty: float = 0.0
    counted_qty: float = 0.0


@dataclass(slots=True)
class BalanceFilter:
    warehouse_id: UUID | None = None
    location_id: UUID | None = None
    product_id: UUID | None = None
    only_positive: bool = False
    limit: int = 100
    offset: int = 0
