"""Health/liveness endpoints (P0)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe: process is up and serving requests."""
    return {"status": "ok"}
