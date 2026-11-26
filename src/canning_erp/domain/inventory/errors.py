"""Inventory domain errors (parity with Go internal/domain/inventory/errors.go)."""

from canning_erp.domain.errors import DomainError


class DocNotFound(DomainError):
    code = "doc_not_found"


class DocAlreadyConfirmed(DomainError):
    code = "doc_already_confirmed"


class DocAlreadyCancelled(DomainError):
    code = "doc_already_cancelled"


class LotNotFound(DomainError):
    code = "lot_not_found"


class LotBlocked(DomainError):
    code = "lot_blocked"


class InsufficientStock(DomainError):
    code = "insufficient_stock"


class InvalidQuantity(DomainError):
    code = "invalid_quantity"


class TransferSameLocation(DomainError):
    code = "transfer_same_location"


class FEFOInsufficientStock(DomainError):
    code = "fefo_insufficient_stock"


class FEFOAllLotsExpired(DomainError):
    code = "fefo_all_lots_expired"


class FEFOAllLotsBlocked(DomainError):
    code = "fefo_all_lots_blocked"


class FEFOLotExpired(DomainError):
    code = "fefo_lot_expired"


class FEFOLotBlocked(DomainError):
    code = "fefo_lot_blocked"


class FEFOLotInsufficient(DomainError):
    code = "fefo_lot_insufficient"


class FEFOLotNotFound(DomainError):
    code = "fefo_lot_not_found"
