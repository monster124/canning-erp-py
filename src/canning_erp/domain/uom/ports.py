"""Ports for the UoM subsystem (implemented in infrastructure, stage P2)."""

from abc import ABC, abstractmethod
from uuid import UUID

from canning_erp.domain.uom.converter import Converter
from canning_erp.domain.uom.entities import ProductUOMs


class UomResolver(ABC):
    """Access to the per-tenant converter and product unit roles."""

    @abstractmethod
    async def converter(self) -> Converter:
        """Return a warmed-up converter for the current tenant."""

    @abstractmethod
    async def product_uoms(self, product_id: UUID) -> ProductUOMs:
        """Return base/inventory/procurement units of a product."""
