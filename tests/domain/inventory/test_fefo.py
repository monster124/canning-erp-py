"""Unit tests for pure FEFO allocation (invariants 1 and 2).

Ported from Go ``application/inventory/fefo_service_test.go`` (the
 table-driven core of distributeFEFO).
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from canning_erp.domain.inventory.entities import LotStatus, StockLot
from canning_erp.domain.inventory.errors import (
    FEFOAllLotsBlocked,
    FEFOAllLotsExpired,
    FEFOInsufficientStock,
)
from canning_erp.domain.inventory.fefo import FEFORequest, distribute_fefo
from canning_erp.domain.uom.converter import Converter
from canning_erp.domain.uom.entities import Unit
from canning_erp.domain.uom.errors import IncompatibleCategories

PRODUCT_ID = uuid4()
WH_ID = uuid4()
UOM_ID = uuid4()

TON = UUID("00000000-0000-0000-0000-0000000000a1")
KG = UUID("00000000-0000-0000-0000-0000000000b1")
LITER = UUID("00000000-0000-0000-0000-0000000000d1")
CAT_MASS = UUID("00000000-0000-0000-0000-0000000000e1")
CAT_VOLUME = UUID("00000000-0000-0000-0000-0000000000e2")

NOW = datetime.now()


def days(offset: int) -> datetime:
    return NOW + timedelta(days=offset)


def ago(days_back: int) -> datetime:
    return NOW - timedelta(days=days_back)


def mk_lot(
    lot_number: str,
    qty: float,
    expiry: datetime | None,
    received: datetime,
    status: LotStatus = LotStatus.ACTIVE,
    uom_id: UUID = UOM_ID,
) -> StockLot:
    return StockLot(
        product_id=PRODUCT_ID,
        warehouse_id=WH_ID,
        uom_id=uom_id,
        lot_number=lot_number,
        qty_received=qty,
        qty_available=qty,
        expiry_date=expiry,
        received_at=received,
        status=status,
    )


def mass_converter() -> Converter:
    conv = Converter()
    conv.load([
        Unit(KG, CAT_MASS, "kg", 1.0),
        Unit(TON, CAT_MASS, "ton", 1000.0),
        Unit(LITER, CAT_VOLUME, "l", 1.0),
    ])
    return conv


# lot spec: (lot_number, qty, expiry_offset_days | None, received_days_ago, status)
CASES = [
    # name, lots, req_qty, near_days, allow_expired, allow_near,
    # error, alloc_count, allocated, min_warnings
    ("single_lot_full_allocation",
     [("L-001", 100, 30, 5, LotStatus.ACTIVE)],
     50, 7, False, False, None, 1, 50.0, 0),
    ("single_lot_complete_depletion",
     [("L-001", 100, 30, 5, LotStatus.ACTIVE)],
     100, 7, False, False, None, 1, 100.0, 0),
    ("split_across_two_lots_fefo_order",
     [("L-001", 30, 10, 5, LotStatus.ACTIVE), ("L-002", 50, 60, 3, LotStatus.ACTIVE)],
     50, 7, False, False, None, 2, 50.0, 0),
    ("fefo_order_nearest_expiry_first",
     [("L-002", 100, 60, 10, LotStatus.ACTIVE), ("L-001", 100, 10, 5, LotStatus.ACTIVE)],
     50, 7, False, False, None, 1, 50.0, 0),
    ("insufficient_stock",
     [("L-001", 30, 30, 5, LotStatus.ACTIVE), ("L-002", 20, 60, 3, LotStatus.ACTIVE)],
     100, 7, False, False, FEFOInsufficientStock, 0, 0.0, 0),
    ("expired_lot_skipped",
     [("L-EXP", 100, -5, 30, LotStatus.ACTIVE), ("L-OK", 50, 30, 3, LotStatus.ACTIVE)],
     40, 7, False, False, None, 1, 40.0, 1),
    ("all_lots_expired",
     [("L-EXP1", 100, -5, 30, LotStatus.ACTIVE), ("L-EXP2", 50, -10, 40, LotStatus.ACTIVE)],
     40, 7, False, False, FEFOAllLotsExpired, 0, 0.0, 0),
    ("expired_lot_allowed_for_scrap",
     [("L-EXP", 100, -5, 30, LotStatus.ACTIVE)],
     40, 7, True, False, None, 1, 40.0, 1),
    ("quarantine_lot_skipped",
     [("L-Q", 100, 30, 5, LotStatus.QUARANTINE), ("L-OK", 50, 60, 3, LotStatus.ACTIVE)],
     40, 7, False, False, None, 1, 40.0, 1),
    ("near_expiry_warning_emitted",
     [("L-NEAR", 100, 3, 5, LotStatus.ACTIVE)],
     50, 7, False, True, None, 1, 50.0, 1),
    ("near_expiry_skipped_when_not_allowed",
     [("L-NEAR", 100, 3, 5, LotStatus.ACTIVE), ("L-OK", 50, 30, 3, LotStatus.ACTIVE)],
     40, 7, False, False, None, 1, 40.0, 1),
    ("no_expiry_lot_goes_last",
     [("L-NOEXP", 100, None, 5, LotStatus.ACTIVE), ("L-EXP30", 100, 30, 3, LotStatus.ACTIVE)],
     50, 7, False, False, None, 1, 50.0, 0),
    ("equal_expiry_fifo_by_received",
     [("L-002", 100, 30, 3, LotStatus.ACTIVE), ("L-001", 100, 30, 10, LotStatus.ACTIVE)],
     50, 7, False, False, None, 1, 50.0, 0),
    ("was_split_flag_set",
     [("L-001", 100, 30, 5, LotStatus.ACTIVE)],
     50, 7, False, False, None, 1, 50.0, 0),
    ("no_lots_available",
     [],
     50, 7, False, False, FEFOInsufficientStock, 0, 0.0, 0),
    ("multi_split_three_lots",
     [("L-001", 20, 10, 5, LotStatus.ACTIVE),
      ("L-002", 15, 20, 4, LotStatus.ACTIVE),
      ("L-003", 30, 60, 3, LotStatus.ACTIVE)],
     50, 7, False, False, None, 3, 50.0, 0),
    ("all_lots_blocked",
     [("L-B1", 100, 30, 5, LotStatus.BLOCKED), ("L-B2", 50, 60, 3, LotStatus.BLOCKED)],
     40, 7, False, False, FEFOAllLotsBlocked, 0, 0.0, 0),
]


@pytest.mark.parametrize(
    ("name", "lots_spec", "req_qty", "near_days", "allow_expired", "allow_near",
     "error", "alloc_count", "allocated", "min_warnings"),
    CASES,
)
def test_distribute_fefo_table(
    name: str,
    lots_spec: list[tuple[str, float, int | None, int, LotStatus]],
    req_qty: float,
    near_days: int,
    allow_expired: bool,
    allow_near: bool,
    error: type[Exception] | None,
    alloc_count: int,
    allocated: float,
    min_warnings: int,
) -> None:
    lots = [
        mk_lot(num, qty, days(off) if off is not None else None, ago(recv), status)
        for (num, qty, off, recv, status) in lots_spec
    ]
    req = FEFORequest(
        product_id=PRODUCT_ID,
        warehouse_id=WH_ID,
        quantity=req_qty,
        uom_id=UOM_ID,
        allow_expired=allow_expired,
        allow_near_expiry=allow_near,
        near_expiry_days=near_days,
    )

    if error is not None:
        with pytest.raises(error):
            distribute_fefo(lots, req, near_days, None)
        return

    result = distribute_fefo(lots, req, near_days, None)
    assert len(result.allocations) == alloc_count
    total = sum(a.quantity for a in result.allocations)
    assert total == pytest.approx(allocated, abs=1e-9)
    assert len(result.warnings) >= min_warnings


def test_order_nearest_expiry_first_from_unsorted_input() -> None:
    lots = [
        mk_lot("L-FAR", 100, days(90), ago(1)),
        mk_lot("L-NEAR", 100, days(5), ago(10)),
        mk_lot("L-MID", 100, days(30), ago(5)),
    ]
    req = FEFORequest(
        product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=50,
        uom_id=UOM_ID, near_expiry_days=3,
    )
    result = distribute_fefo(lots, req, 3, None)
    assert [a.lot_number for a in result.allocations] == ["L-NEAR"]


def test_equal_expiry_fifo_by_received() -> None:
    same = days(30)
    lots = [
        mk_lot("L-LATE", 100, same, ago(1)),
        mk_lot("L-EARLY", 100, same, ago(10)),
    ]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=50, uom_id=UOM_ID)
    result = distribute_fefo(lots, req, 7, None)
    assert result.allocations[0].lot_number == "L-EARLY"


def test_was_split_flag() -> None:
    lot = mk_lot("L-001", 100, days(30), NOW)

    req30 = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=30, uom_id=UOM_ID)
    r1 = distribute_fefo([lot], req30, 7, None)
    assert r1.allocations[0].was_split is True

    req100 = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=100, uom_id=UOM_ID)
    r2 = distribute_fefo([lot], req100, 7, None)
    assert r2.allocations[0].was_split is False


def test_no_expiry_lots_fifo() -> None:
    lots = [
        mk_lot("L-LATE", 100, None, ago(1)),
        mk_lot("L-EARLY", 100, None, ago(10)),
    ]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=50, uom_id=UOM_ID)
    result = distribute_fefo(lots, req, 7, None)
    assert result.allocations[0].lot_number == "L-EARLY"


# --- Conversion: request in ton, lots in kg (rate = 1000) ---


def test_conversion_ton_to_kg_single_lot() -> None:
    conv = mass_converter()
    lots = [mk_lot("L-KG", 5000, days(365), NOW, uom_id=KG)]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=2, uom_id=TON)

    result = distribute_fefo(lots, req, 7, conv)
    assert len(result.allocations) == 1
    alloc = result.allocations[0]
    # Allocation in LOT units: 2 ton x 1000 = 2000 kg
    assert alloc.quantity == pytest.approx(2000.0)
    assert alloc.uom_id == KG
    assert alloc.was_split is True  # 2000 < 5000 - lot is split


def test_conversion_ton_to_kg_multi_lot_split() -> None:
    conv = mass_converter()
    lots = [
        mk_lot("L-1", 1500, days(10), NOW, uom_id=KG),
        mk_lot("L-2", 5000, days(20), NOW, uom_id=KG),
    ]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=2, uom_id=TON)

    result = distribute_fefo(lots, req, 7, conv)
    assert [a.quantity for a in result.allocations] == [
        pytest.approx(1500.0),
        pytest.approx(500.0),
    ]
    assert result.allocations[0].was_split is False
    assert result.allocations[1].was_split is True


def test_conversion_incompatible_categories() -> None:
    conv = mass_converter()
    lots = [mk_lot("L-L", 5000, days(365), NOW, uom_id=LITER)]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=1, uom_id=TON)

    with pytest.raises(IncompatibleCategories):
        distribute_fefo(lots, req, 7, conv)


def test_conversion_allocation_uom_is_lot_uom() -> None:
    """Invariant 1: allocation uom_id is the LOT's uom, never the request's."""
    conv = mass_converter()
    lots = [mk_lot("L-KG", 5000, days(365), NOW, uom_id=KG)]
    req = FEFORequest(product_id=PRODUCT_ID, warehouse_id=WH_ID, quantity=1, uom_id=TON)

    result = distribute_fefo(lots, req, 7, conv)
    assert result.allocations[0].uom_id == KG
    assert result.total_allocated == pytest.approx(1.0)  # in request units
