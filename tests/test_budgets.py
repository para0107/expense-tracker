from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

BUDGETS_URL = f"{API_PREFIX}/budgets"
ACCOUNTS_URL = f"{API_PREFIX}/accounts"
CATEGORIES_URL = f"{API_PREFIX}/categories"
TRANSACTIONS_URL = f"{API_PREFIX}/transactions"
LIMIT_MINOR = 10000


async def create_id(client: AsyncClient, url: str, body: dict) -> str:
    response = await client.post(url, json=body)
    assert response.status_code == 201
    return response.json()["id"]


async def create_category_id(client: AsyncClient) -> str:
    return await create_id(client, CATEGORIES_URL, {"name": "Food"})


async def create_budget(client: AsyncClient, category_id: str, month: int = 1):
    return await client.post(
        BUDGETS_URL,
        json={
            "categoryId": category_id,
            "year": 2026,
            "month": month,
            "limitMinor": LIMIT_MINOR,
        },
    )


async def book_expense(
    client: AsyncClient, category_id: str, amount_minor: int, booked_on: str
) -> None:
    account_id = await create_id(
        client, ACCOUNTS_URL, {"name": booked_on, "currency": "EUR"}
    )
    await create_id(
        client,
        TRANSACTIONS_URL,
        {
            "accountId": account_id,
            "categoryId": category_id,
            "amountMinor": amount_minor,
            "bookedOn": booked_on,
            "description": "Shopping",
        },
    )


async def get_statuses(client: AsyncClient, month: int = 1) -> list[dict]:
    response = await client.get(BUDGETS_URL, params={"year": 2026, "month": month})
    assert response.status_code == 200
    return response.json()


async def test_under_budget(logged_in_client: AsyncClient) -> None:
    category_id = await create_category_id(logged_in_client)
    assert (await create_budget(logged_in_client, category_id)).status_code == 201
    await book_expense(logged_in_client, category_id, -2500, "2026-01-31")
    await book_expense(logged_in_client, category_id, -9999, "2026-02-01")

    [status] = await get_statuses(logged_in_client)
    assert status["spentMinor"] == 2500
    assert status["remainingMinor"] == LIMIT_MINOR - 2500
    assert status["isExceeded"] is False


async def test_over_budget(logged_in_client: AsyncClient) -> None:
    category_id = await create_category_id(logged_in_client)
    await create_budget(logged_in_client, category_id)
    await book_expense(logged_in_client, category_id, -LIMIT_MINOR - 1, "2026-01-15")

    [status] = await get_statuses(logged_in_client)
    assert status["remainingMinor"] == -1
    assert status["isExceeded"] is True


async def test_duplicate_budget_is_conflict(logged_in_client: AsyncClient) -> None:
    category_id = await create_category_id(logged_in_client)
    await create_budget(logged_in_client, category_id)
    assert (await create_budget(logged_in_client, category_id)).status_code == 409


async def test_invalid_month_is_unprocessable(logged_in_client: AsyncClient) -> None:
    category_id = await create_category_id(logged_in_client)
    assert (
        await create_budget(logged_in_client, category_id, month=13)
    ).status_code == 422
    response = await logged_in_client.get(
        BUDGETS_URL, params={"year": 2026, "month": 0}
    )
    assert response.status_code == 422


async def test_delete_budget(logged_in_client: AsyncClient) -> None:
    category_id = await create_category_id(logged_in_client)
    created = await create_budget(logged_in_client, category_id)
    url = f"{BUDGETS_URL}/{created.json()['id']}"
    assert (await logged_in_client.delete(url)).status_code == 204
    assert (await logged_in_client.delete(url)).status_code == 404
    assert await get_statuses(logged_in_client) == []


async def test_other_user_is_isolated(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    category_id = await create_category_id(logged_in_client)
    created = await create_budget(logged_in_client, category_id)

    assert (await create_budget(other_logged_in_client, category_id)).status_code == 404
    assert await get_statuses(other_logged_in_client) == []
    url = f"{BUDGETS_URL}/{created.json()['id']}"
    assert (await other_logged_in_client.delete(url)).status_code == 404
    assert len(await get_statuses(logged_in_client)) == 1
