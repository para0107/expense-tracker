from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

REPORT_URL = f"{API_PREFIX}/reports/monthly"
ACCOUNTS_URL = f"{API_PREFIX}/accounts"
CATEGORIES_URL = f"{API_PREFIX}/categories"
TRANSACTIONS_URL = f"{API_PREFIX}/transactions"
JANUARY = {"year": 2026, "month": 1}


async def create_id(client: AsyncClient, url: str, body: dict) -> str:
    response = await client.post(url, json=body)
    assert response.status_code == 201
    return response.json()["id"]


async def create_account_id(client: AsyncClient) -> str:
    return await create_id(
        client, ACCOUNTS_URL, {"name": "Checking", "currency": "EUR"}
    )


async def book(
    client: AsyncClient,
    account_id: str,
    amount_minor: int,
    description: str,
    booked_on: str = "2026-01-10",
    category_id: str | None = None,
) -> None:
    await create_id(
        client,
        TRANSACTIONS_URL,
        {
            "accountId": account_id,
            "categoryId": category_id,
            "amountMinor": amount_minor,
            "bookedOn": booked_on,
            "description": description,
        },
    )


async def test_monthly_report_numbers(logged_in_client: AsyncClient) -> None:
    account_id = await create_account_id(logged_in_client)
    food_id = await create_id(logged_in_client, CATEGORIES_URL, {"name": "Food"})
    await book(logged_in_client, account_id, 100000, "Salary")
    await book(logged_in_client, account_id, -3000, "Shop A", category_id=food_id)
    await book(logged_in_client, account_id, -2000, "Shop A", category_id=food_id)
    for index, amount_minor in enumerate([-100, -200, -300, -400, -500]):
        await book(logged_in_client, account_id, amount_minor, f"Item {index}")
    await book(logged_in_client, account_id, -9999, "Other month", "2026-02-01")

    response = await logged_in_client.get(REPORT_URL, params=JANUARY)
    assert response.status_code == 200
    report = response.json()
    assert report["incomeMinor"] == 100000
    assert report["expensesMinor"] == 6500
    assert report["netMinor"] == 93500
    assert report["categoryTotals"] == [
        {"categoryId": food_id, "categoryName": "Food", "expensesMinor": 5000},
        {"categoryId": None, "categoryName": None, "expensesMinor": 1500},
    ]
    assert report["topDescriptions"] == [
        {"description": "Shop A", "expensesMinor": 5000},
        {"description": "Item 4", "expensesMinor": 500},
        {"description": "Item 3", "expensesMinor": 400},
        {"description": "Item 2", "expensesMinor": 300},
        {"description": "Item 1", "expensesMinor": 200},
    ]


async def test_other_user_data_is_not_counted(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    account_id = await create_account_id(logged_in_client)
    await book(logged_in_client, account_id, -3000, "Private")

    report = (await other_logged_in_client.get(REPORT_URL, params=JANUARY)).json()
    assert report["incomeMinor"] == 0
    assert report["expensesMinor"] == 0
    assert report["categoryTotals"] == []
    assert report["topDescriptions"] == []


async def test_invalid_month_is_unprocessable(logged_in_client: AsyncClient) -> None:
    response = await logged_in_client.get(
        REPORT_URL, params={"year": 2026, "month": 13}
    )
    assert response.status_code == 422
