import uuid

from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

ACCOUNTS_URL = f"{API_PREFIX}/accounts"
NEW_ACCOUNT = {"name": "Checking", "currency": "EUR"}


async def test_account_crud(logged_in_client: AsyncClient) -> None:
    created = await logged_in_client.post(ACCOUNTS_URL, json=NEW_ACCOUNT)
    assert created.status_code == 201
    account = created.json()
    assert account["name"] == "Checking"
    assert account["currency"] == "EUR"

    fetched = await logged_in_client.get(f"{ACCOUNTS_URL}/{account['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == account

    listed = await logged_in_client.get(ACCOUNTS_URL)
    assert listed.status_code == 200
    assert listed.json()["items"] == [account]
    assert listed.json()["totalCount"] == 1

    deleted = await logged_in_client.delete(f"{ACCOUNTS_URL}/{account['id']}")
    assert deleted.status_code == 204
    missing = await logged_in_client.get(f"{ACCOUNTS_URL}/{account['id']}")
    assert missing.status_code == 404


async def test_duplicate_name_is_conflict(logged_in_client: AsyncClient) -> None:
    await logged_in_client.post(ACCOUNTS_URL, json=NEW_ACCOUNT)
    duplicate = await logged_in_client.post(ACCOUNTS_URL, json=NEW_ACCOUNT)
    assert duplicate.status_code == 409


async def test_bad_currency_is_rejected(logged_in_client: AsyncClient) -> None:
    response = await logged_in_client.post(
        ACCOUNTS_URL, json={"name": "Checking", "currency": "eur"}
    )
    assert response.status_code == 422


async def test_page_size_over_maximum_is_rejected(
    logged_in_client: AsyncClient,
) -> None:
    response = await logged_in_client.get(ACCOUNTS_URL, params={"page_size": 101})
    assert response.status_code == 422


async def test_other_user_gets_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    created = await logged_in_client.post(ACCOUNTS_URL, json=NEW_ACCOUNT)
    account_id = created.json()["id"]
    assert (
        await other_logged_in_client.get(f"{ACCOUNTS_URL}/{account_id}")
    ).status_code == 404
    assert (
        await other_logged_in_client.delete(f"{ACCOUNTS_URL}/{account_id}")
    ).status_code == 404
    assert (await other_logged_in_client.get(ACCOUNTS_URL)).json()["items"] == []


async def test_unknown_account_is_not_found(logged_in_client: AsyncClient) -> None:
    response = await logged_in_client.get(f"{ACCOUNTS_URL}/{uuid.uuid7()}")
    assert response.status_code == 404


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.get(ACCOUNTS_URL)
    assert response.status_code == 401
