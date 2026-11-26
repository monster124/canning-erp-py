"""Smoke tests for the HTTP interface (P0)."""

import httpx

from canning_erp.interfaces.http.app import create_app


async def test_health_returns_ok() -> None:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
