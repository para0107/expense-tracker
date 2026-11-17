from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX


async def test_health_reports_ok(client: AsyncClient):
    response = await client.get(f"{API_PREFIX}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
