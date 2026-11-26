"""Unit tests for the UoM converter (invariant 2: category isolation).

Ported from Go ``internal/domain/uom/converter_test.go``.
"""

import threading
from uuid import uuid4

import pytest

from canning_erp.domain.uom.converter import Converter, round_qty
from canning_erp.domain.uom.entities import Unit
from canning_erp.domain.uom.errors import (
    IncompatibleCategories,
    NegativeQuantity,
    UnitNotFound,
)

CAT_MASS = uuid4()
CAT_VOLUME = uuid4()
CAT_COUNT = uuid4()

U_KG = Unit(uuid4(), CAT_MASS, "kg", 1.0)
U_TON = Unit(uuid4(), CAT_MASS, "ton", 1000.0)
U_G = Unit(uuid4(), CAT_MASS, "g", 0.001)
U_L = Unit(uuid4(), CAT_VOLUME, "l", 1.0)
U_ML = Unit(uuid4(), CAT_VOLUME, "ml", 0.001)
U_PCS = Unit(uuid4(), CAT_COUNT, "pcs", 1.0)
U_BOX = Unit(uuid4(), CAT_COUNT, "box", 12.0)
U_PALLET = Unit(uuid4(), CAT_COUNT, "pallet", 960.0)


def loaded_converter() -> Converter:
    conv = Converter()
    conv.load([U_KG, U_TON, U_G, U_L, U_ML, U_PCS, U_BOX, U_PALLET])
    return conv


@pytest.mark.parametrize(
    ("qty", "src", "dst", "expected"),
    [
        (1500, U_KG, U_TON, 1.5),
        (2.5, U_TON, U_KG, 2500),
        (0.5, U_KG, U_G, 500),
        (750, U_G, U_KG, 0.75),
        (0.001, U_TON, U_G, 1000),
        (1.25, U_L, U_ML, 1250),
        (750, U_ML, U_L, 0.75),
        (10, U_BOX, U_PCS, 120),
        (24, U_PCS, U_BOX, 2),
        (1, U_PALLET, U_PCS, 960),
        (1920, U_PCS, U_PALLET, 2),
        (123.456, U_KG, U_KG, 123.456),  # identity
        (0, U_KG, U_TON, 0),  # zero is valid
    ],
)
def test_convert_within_category(qty: float, src: Unit, dst: Unit, expected: float) -> None:
    conv = loaded_converter()
    assert conv.convert(qty, src.id, dst.id) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    ("qty", "src", "dst"),
    [
        (1, U_KG, U_L),
        (1, U_L, U_KG),
        (12, U_PCS, U_KG),
        (1, U_BOX, U_ML),
    ],
)
def test_convert_cross_category_forbidden(qty: float, src: Unit, dst: Unit) -> None:
    conv = loaded_converter()
    with pytest.raises(IncompatibleCategories):
        conv.convert(qty, src.id, dst.id)


def test_convert_negative_quantity() -> None:
    conv = loaded_converter()
    with pytest.raises(NegativeQuantity):
        conv.convert(-1, U_KG.id, U_TON.id)


@pytest.mark.parametrize(
    ("qty", "src", "dst", "expected"),
    [
        (100, U_G, U_KG, 0.1),
        (1, U_G, U_KG, 0.001),
        (0.0005, U_KG, U_G, 0.5),
        (1.0 / 3.0, U_BOX, U_PCS, 4),
        (4, U_PCS, U_BOX, 0.333),
    ],
)
def test_convert_rounding_half_up(qty: float, src: Unit, dst: Unit, expected: float) -> None:
    conv = loaded_converter()
    assert conv.convert(qty, src.id, dst.id) == pytest.approx(expected, abs=1e-9)


def test_round_qty_half_up_not_bankers() -> None:
    # 0.0005 -> 0.001 (half-up; banker's rounding would give 0.000)
    assert round_qty(0.0005) == 0.001
    assert round_qty(0.0015) == 0.002


def test_convert_unknown_units() -> None:
    conv = loaded_converter()
    unknown = Unit(uuid4(), CAT_MASS, "??", 1.0)
    with pytest.raises(UnitNotFound):
        conv.convert(1, unknown.id, U_KG.id)
    with pytest.raises(UnitNotFound):
        conv.convert(1, U_KG.id, unknown.id)


def test_converter_cache_lifecycle() -> None:
    conv = Converter()
    with pytest.raises(UnitNotFound):
        conv.convert(1, U_KG.id, U_TON.id)

    conv.load([U_KG, U_TON])
    assert conv.convert(1500, U_KG.id, U_TON.id) == 1.5

    conv.invalidate()
    with pytest.raises(UnitNotFound):
        conv.convert(1, U_KG.id, U_TON.id)

    # Reload with a CHANGED factor (uom_units upsert) - no stale cache
    updated_ton = Unit(U_TON.id, CAT_MASS, "ton", 2000.0)
    conv.load([U_KG, updated_ton])
    assert conv.convert(2000, U_KG.id, U_TON.id) == 1.0


def test_converter_concurrent_load_convert() -> None:
    conv = loaded_converter()
    errors: list[Exception] = []

    def writer() -> None:
        try:
            for _ in range(200):
                conv.load([U_KG, U_TON, U_L, U_ML, U_PCS, U_BOX])
        except Exception as exc:  # collected on purpose
            errors.append(exc)

    def reader() -> None:
        try:
            for _ in range(500):
                conv.convert(1500, U_KG.id, U_TON.id)
                conv.convert(12, U_PCS.id, U_BOX.id)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer)]
    threads += [threading.Thread(target=reader) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []


def test_must_convert_contract() -> None:
    conv = loaded_converter()
    assert conv.must_convert(1500, U_KG.id, U_TON.id) == 1.5
    with pytest.raises(IncompatibleCategories):
        conv.must_convert(1, U_KG.id, U_L.id)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (U_KG, U_TON, True),
        (U_KG, U_L, False),
        (U_ML, U_L, True),
        (U_PCS, U_PALLET, True),
        (U_BOX, U_KG, False),
    ],
)
def test_same_category(a: Unit, b: Unit, expected: bool) -> None:
    conv = loaded_converter()
    assert conv.same_category(a.id, b.id) is expected


def test_rate_fefo_contract() -> None:
    """FEFO uses rate = convert(1, req_uom, lot_uom) - formula contract."""
    conv = loaded_converter()
    rate = conv.convert(1, U_TON.id, U_KG.id)
    assert rate == 1000
    lot_avail_in_req = 150.0 / rate
    assert lot_avail_in_req == pytest.approx(0.15)
    assert round_qty(0.08 * rate) == 80.0
