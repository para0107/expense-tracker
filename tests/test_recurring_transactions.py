from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

RECURRING_URL = f"{API_PREFIX}/recurring-transactions"
ACCOUNTS_URL = f"{API_PREFIX}/accounts"
CATEGORIES_URL = f"{API_PREFIX}/categories"


async def create_id(client: AsyncClient, url: str, body: dict) -> str:
    response = await client.post(url, json=body)
    assert response.status_code == 201
    return response.json()["id"]


def build_rule(account_id: str, **overrides: object) -> dict:
    return {
        "accountId": account_id,
        "amountMinor": -1500,
        "description": "Rent",
        "cadence": "MONTHLY",
        "startDate": "2026-01-01",
    } | overrides


async def test_create_list_and_delete(logged_in_client: AsyncClient) -> None:
    account_id = await create_id(
        logged_in_client, ACCOUNTS_URL, {"name": "Checking", "currency": "EUR"}
    )
    category_id = await create_id(logged_in_client, CATEGORIES_URL, {"name": "Home"})

    created = await logged_in_client.post(
        RECURRING_URL, json=build_rule(account_id, categoryId=category_id)
    )
    assert created.status_code == 201
    rule = created.json()
    assert rule["cadence"] == "MONTHLY"
    assert rule["categoryId"] == category_id
    assert rule["amountMinor"] == -1500

    listed = await logged_in_client.get(RECURRING_URL)
    assert listed.status_code == 200
    assert listed.json()["items"] == [rule]
    assert listed.json()["totalCount"] == 1

    url = f"{RECURRING_URL}/{rule['id']}"
    assert (await logged_in_client.delete(url)).status_code == 204
    assert (await logged_in_client.delete(url)).status_code == 404
    assert (await logged_in_client.get(RECURRING_URL)).json()["items"] == []


async def test_foreign_account_is_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    account_id = await create_id(
        logged_in_client, ACCOUNTS_URL, {"name": "Checking", "currency": "EUR"}
    )
    response = await other_logged_in_client.post(
        RECURRING_URL, json=build_rule(account_id)
    )
    assert response.status_code == 404


async def test_invalid_cadence_is_unprocessable(logged_in_client: AsyncClient) -> None:
    account_id = await create_id(
        logged_in_client, ACCOUNTS_URL, {"name": "Checking", "currency": "EUR"}
    )
    response = await logged_in_client.post(
        RECURRING_URL, json=build_rule(account_id, cadence="DAILY")
    )
    assert response.status_code == 422
