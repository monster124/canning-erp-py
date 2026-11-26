"""Repository port for the inventory module.

Ported from Go ``internal/domain/inventory/repository.go``; implemented by
SQLAlchemy adapters in infrastructure (stage P5).
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from canning_erp.domain.inventory.documents import (
    BalanceFilter,
    CountLine,
    CountSheet,
    IssueDocument,
    IssueLine,
    ReceiptDocument,
    ReceiptLine,
    TransferDocument,
    TransferLine,
)
from canning_erp.domain.inventory.entities import (
    StockBalance,
    StockLot,
    StockMovement,
)
from canning_erp.domain.inventory.fefo import FEFOAllocation


class Session(Protocol):
    """Structural DB-session handle; implemented by infrastructure adapters."""


class InventoryRepository(ABC):
    """Port of the warehouse module."""

    # --- Receipt ---
    @abstractmethod
    async def create_receipt_doc(
        self, session: Session, doc: ReceiptDocument, lines: Sequence[ReceiptLine]
    ) -> None: ...

    @abstractmethod
    async def confirm_receipt(
        self, session: Session, doc_id: UUID, confirmed_by: str
    ) -> None: ...

    # --- Lots ---
    @abstractmethod
    async def get_lot_by_id(self, session: Session, lot_id: UUID) -> StockLot | None: ...

    @abstractmethod
    async def get_lots_for_fefo(
        self, session: Session, product_id: UUID, warehouse_id: UUID
    ) -> Sequence[StockLot]: ...

    @abstractmethod
    async def create_lot(self, session: Session, lot: StockLot) -> None: ...

    @abstractmethod
    async def update_lot_qty(
        self, session: Session, lot_id: UUID, delta: float, updated_by: str
    ) -> None: ...

    # --- Movements ---
    @abstractmethod
    async def insert_movement(self, session: Session, movement: StockMovement) -> None: ...

    # --- Balances ---
    @abstractmethod
    async def get_balance(
        self, session: Session, product_id: UUID, warehouse_id: UUID, location_id: UUID
    ) -> StockBalance | None: ...

    @abstractmethod
    async def list_balances(
        self, session: Session, balance_filter: BalanceFilter
    ) -> Sequence[StockBalance]: ...

    # --- Issue ---
    @abstractmethod
    async def create_issue_doc(
        self, session: Session, doc: IssueDocument, lines: Sequence[IssueLine]
    ) -> None: ...

    @abstractmethod
    async def confirm_issue(
        self,
        session: Session,
        doc_id: UUID,
        allocations: Sequence[FEFOAllocation],
        confirmed_by: str,
    ) -> None: ...

    # --- Transfer ---
    @abstractmethod
    async def create_transfer_doc(
        self, session: Session, doc: TransferDocument, lines: Sequence[TransferLine]
    ) -> None: ...

    @abstractmethod
    async def confirm_transfer(
        self, session: Session, doc_id: UUID, confirmed_by: str
    ) -> None: ...

    # --- Count ---
    @abstractmethod
    async def create_count_sheet(
        self, session: Session, sheet: CountSheet, lines: Sequence[CountLine]
    ) -> None: ...

    @abstractmethod
    async def update_count_line(
        self, session: Session, line_id: UUID, qty_counted: float, counted_by: str
    ) -> None: ...

    @abstractmethod
    async def confirm_count_sheet(
        self, session: Session, sheet_id: UUID, confirmed_by: str
    ) -> None: ...
